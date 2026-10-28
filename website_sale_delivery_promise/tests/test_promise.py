# -*- coding: utf-8 -*-
"""The promise as the shop builds it: product, cart, checkout, order."""
from datetime import date, datetime

from odoo.tests.common import TransactionCase


class TestDeliveryPromise(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site = cls.env['website'].search([], limit=1)
        cls.site.write({
            'delivery_promise_enabled': True,
            'delivery_cutoff_hour': 14.0,
            'delivery_tz': 'UTC',
            'delivery_open_mon': True,
            'delivery_open_tue': True,
            'delivery_open_wed': True,
            'delivery_open_thu': True,
            'delivery_open_fri': True,
            'delivery_open_sat': False,
            'delivery_open_sun': False,
            'delivery_holiday_ids': [(5, 0, 0)],
            'delivery_country_extra_ids': [(5, 0, 0)],
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Promise Buyer', 'country_id': cls.env.ref('base.us').id})
        cls.monday_before_cutoff = datetime(2026, 10, 26, 13, 59)

    def _product(self, **vals):
        values = {
            'name': 'Promise Product', 'type': 'consu', 'list_price': 10.0,
            'sale_ok': True, 'sale_delay': 0.0,
        }
        values.update(vals)
        return self.env['product.template'].create(values)

    def _order(self, products):
        """One sale order per product, with the website of the test."""
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'website_id': self.site.id,
            'order_line': [(0, 0, {'product_id': product.product_variant_id.id,
                                   'product_uom_qty': 1, 'price_unit': 10.0})
                           for product in products],
        })

    # ------------------------------------------------------------------
    # Product
    # ------------------------------------------------------------------
    def test_product_follows_the_sales_lead_time(self):
        product = self._product(sale_delay=3.0)
        self.assertEqual(product.ships_in_days, -1)
        self.assertEqual(product._dps_effective_ships_in_days(), 3)

    def test_product_zero_overrides_the_lead_time(self):
        product = self._product(sale_delay=3.0, ships_in_days=0)
        self.assertEqual(product._dps_effective_ships_in_days(), 0)
        payload = product._dps_promise_payload(now=self.monday_before_cutoff)
        self.assertEqual(payload['date'], date(2026, 10, 26))

    def test_negative_ships_in_days_ships_today(self):
        product = self._product(ships_in_days=-7)
        payload = product._dps_promise_payload(now=self.monday_before_cutoff)
        self.assertEqual(payload['date'], date(2026, 10, 26))
        self.assertEqual(payload['ships_in_days'], 0)

    def test_product_payload_text(self):
        product = self._product(ships_in_days=0)
        payload = product._dps_promise_payload(
            now=datetime(2026, 10, 26, 11, 46))
        self.assertEqual(payload['text'],
                         'Order within 2h 14m, delivered by Mon, 26 Oct')

    def test_past_cutoff_text_drops_the_countdown(self):
        product = self._product(ships_in_days=0)
        payload = product._dps_promise_payload(now=datetime(2026, 10, 26, 15, 0))
        self.assertEqual(payload['text'], 'Order now, delivered by Tue, 27 Oct')
        self.assertFalse(payload['countdown'])

    def test_holiday_pushes_the_product_date(self):
        self.env['website.delivery.holiday'].create({
            'website_id': self.site.id, 'date': date(2026, 10, 27),
            'name': 'Stock count'})
        product = self._product(ships_in_days=1)
        payload = product._dps_promise_payload(now=self.monday_before_cutoff)
        self.assertEqual(payload['date'], date(2026, 10, 28))

    def test_country_extra_days_are_added(self):
        self.env['website.delivery.country.extra'].create({
            'website_id': self.site.id, 'country_id': self.env.ref('base.us').id,
            'extra_days': 2})
        product = self._product(ships_in_days=1)
        payload = product._dps_promise_payload(
            country=self.env.ref('base.us'), now=self.monday_before_cutoff)
        self.assertEqual(payload['date'], date(2026, 10, 29))
        self.assertEqual(payload['extra_days'], 2)

    def test_saturday_order_moves_to_monday(self):
        product = self._product(ships_in_days=0)
        payload = product._dps_promise_payload(now=datetime(2026, 10, 31, 10, 0))
        self.assertEqual(payload['date'], date(2026, 11, 2))

    # ------------------------------------------------------------------
    # Timezone
    # ------------------------------------------------------------------
    def test_timezone_moves_the_cutoff(self):
        """07:30 UTC is 15:30 in a UTC+8 shop: past the 14:00 cut-off.

        The same instant, read in UTC, is before the cut-off. A promise computed
        in UTC would therefore be one day short for every order placed after
        16:00 local time.
        """
        product = self._product(ships_in_days=0)
        now = datetime(2026, 10, 26, 7, 30)
        self.site.delivery_tz = 'UTC'
        self.assertEqual(product._dps_promise_payload(now=now)['date'],
                         date(2026, 10, 26))
        self.site.delivery_tz = 'Asia/Shanghai'
        payload = product._dps_promise_payload(now=now)
        self.assertEqual(payload['date'], date(2026, 10, 27))

    # ------------------------------------------------------------------
    # Cart and checkout
    # ------------------------------------------------------------------
    def test_cart_takes_the_slowest_line(self):
        fast = self._product(ships_in_days=0, name='Fast')
        slow = self._product(ships_in_days=5, name='Slow')
        order = self._order([fast, slow])
        self.assertEqual(order._dps_promise_ships_in_days(), 5)
        payload = order._dps_promise_payload(now=self.monday_before_cutoff)
        # Monday + 5 working days, not Monday + 0 + 5 counted from two lines.
        self.assertEqual(payload['date'], date(2026, 11, 2))
        self.assertEqual(payload['ships_in_days'], 5)

    def test_cart_uses_the_delivery_country(self):
        self.env['website.delivery.country.extra'].create({
            'website_id': self.site.id, 'country_id': self.env.ref('base.us').id,
            'extra_days': 2})
        product = self._product(ships_in_days=0)
        order = self._order([product])
        payload = order._dps_promise_payload(now=self.monday_before_cutoff)
        self.assertEqual(payload['date'], date(2026, 10, 28))
        self.assertEqual(payload['extra_days'], 2)

    def test_empty_cart_has_no_promise(self):
        order = self._order([])
        self.assertEqual(order._dps_promise_payload(now=self.monday_before_cutoff), {})

    # ------------------------------------------------------------------
    # Negative control
    # ------------------------------------------------------------------
    def test_disabled_website_shows_nothing(self):
        product = self._product(ships_in_days=0)
        order = self._order([product])
        self.assertTrue(product._dps_promise_payload(now=self.monday_before_cutoff))
        self.site.delivery_promise_enabled = False
        self.assertFalse(product._dps_promise_available())
        self.assertEqual(product._dps_promise_payload(now=self.monday_before_cutoff), {})
        self.assertEqual(order._dps_promise_payload(now=self.monday_before_cutoff), {})

    # ------------------------------------------------------------------
    # Commitment date
    # ------------------------------------------------------------------
    def test_commitment_date_is_stamped_from_the_order_moment(self):
        product = self._product(ships_in_days=0)
        order = self._order([product])
        # Friday 13:00 UTC, before the 14:00 cut-off: the promise is Friday noon.
        order._dps_stamp_commitment_date(now=datetime(2026, 10, 30, 13, 0))
        self.assertEqual(order.commitment_date, datetime(2026, 10, 30, 12, 0))

    def test_confirm_stamps_the_commitment_date(self):
        """The hook is wired: confirming writes a date, at noon in the shop tz.

        The date itself comes from ``estimate_date`` and is pinned by the table;
        what is checked here is that a website order gets the stamp at all, and
        that it is stored at 12:00 (the website runs on UTC in this test).
        """
        product = self._product(ships_in_days=0)
        order = self._order([product])
        order.action_confirm()
        self.assertTrue(order.commitment_date)
        self.assertEqual(order.commitment_date.hour, 12)
        self.assertEqual(order.commitment_date.minute, 0)

    def test_confirm_keeps_a_merchant_commitment_date(self):
        product = self._product(ships_in_days=0)
        order = self._order([product])
        order.commitment_date = datetime(2026, 11, 10, 9, 0)
        order.action_confirm()
        self.assertEqual(order.commitment_date, datetime(2026, 11, 10, 9, 0))

    def test_order_without_website_gets_no_commitment_date(self):
        product = self._product(ships_in_days=0)
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {'product_id': product.product_variant_id.id,
                                   'product_uom_qty': 1, 'price_unit': 10.0})],
        })
        order.action_confirm()
        self.assertFalse(order.commitment_date)
