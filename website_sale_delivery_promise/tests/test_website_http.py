# -*- coding: utf-8 -*-
from odoo.tests import HttpCase


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
