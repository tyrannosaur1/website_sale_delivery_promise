# -*- coding: utf-8 -*-
import re
from datetime import datetime
from unittest.mock import patch

from odoo import fields
from odoo.tests import HttpCase

# Monday 26 October 2026, 11:46 UTC: 2h 14m before the 14:00 cut-off. The clock
# is frozen for these two tests so the page is asked for the same deadline on
# every run, whatever time the suite happens to start at.
BEFORE_CUTOFF = datetime(2026, 10, 26, 11, 46)
AFTER_CUTOFF = datetime(2026, 10, 26, 15, 0)


class TestDeliveryPromisePages(HttpCase):
    """The block has to appear on a real product page, not only in a dict.

    The product page is cached by the core; the promise depends on the clock, so
    this test also proves the t-nocache hole is in the right place: a page whose
    text is frozen in the cache would still render on the first request and only
    be wrong later, which no unit test would catch.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env['website'].search([], limit=1)
        cls.site.write({
            'delivery_promise_enabled': True,
            'delivery_cutoff_hour': 14.0,
            'delivery_tz': 'UTC',
            'delivery_open_sat': False,
            'delivery_open_sun': False,
        })
        cls.product = cls.env['product.template'].create({
            'name': 'Promise Mug',
            'type': 'consu',
            'list_price': 10.0,
            'sale_ok': True,
            'is_published': True,
            'ships_in_days': 0,
        })

    def _product_page(self):
        url = self.product.website_url
        self.assertTrue(url, 'the product must be published to have a URL')
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        return response.text

    def test_product_page_shows_the_promise(self):
        page = self._product_page()
        self.assertIn('o_dps_text', page)
        self.assertIn('delivered by', page)

    def test_product_page_without_the_promise(self):
        self.site.delivery_promise_enabled = False
        page = self._product_page()
        self.assertNotIn('o_dps_text', page)
        self.assertNotIn('delivered by', page)

    def _attr(self, page, name):
        match = re.search(r'%s="([^"]*)"' % name, page)
        self.assertTrue(match, '%s is missing from the page' % name)
        return match.group(1)

    def test_page_carries_the_cutoff_and_the_remaining_time(self):
        """The markup ships the deadline, not only the sentence.

        A sentence alone is what goes stale in an open tab: the absolute
        instant and the seconds left at render time are what the front end
        needs to keep counting without reading the visitor's clock.
        """
        with patch.object(fields.Datetime, 'now', return_value=BEFORE_CUTOFF):
            page = self._product_page()
        self.assertEqual(self._attr(page, 'data-dps-cutoff'),
                         '2026-10-26T14:00:00Z')
        self.assertEqual(self._attr(page, 'data-dps-seconds'), '8040')
        self.assertEqual(self._attr(page, 'data-dps-expired'),
                         'Order now, delivered by Mon, 26 Oct')
        self.assertIn('<span class="o_dps_countdown">2h 14m</span>', page)
        self.assertIn('Order within ', page)
        self.assertIn(', delivered by Mon, 26 Oct', page)

    def test_page_rendered_after_the_cutoff_has_no_countdown(self):
        """Past the cut-off the page is the expired promise and nothing else.

        No attributes and no countdown element means the script has nothing to
        find: one is not left running against a deadline that has gone.
        """
        with patch.object(fields.Datetime, 'now', return_value=AFTER_CUTOFF):
            page = self._product_page()
        self.assertIn('Order now, delivered by Tue, 27 Oct', page)
        self.assertNotIn('o_dps_countdown', page)
        self.assertNotIn('data-dps-seconds', page)
        self.assertNotIn('data-dps-cutoff', page)
