# -*- coding: utf-8 -*-
"""Cart and checkout promise, and the commitment date it leaves on the order."""
from datetime import datetime, time

import pytz

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _dps_promise_lines(self):
        self.ensure_one()
        return self.order_line.filtered(
            lambda line: line.product_id and not line.display_type)

    def _dps_promise_ships_in_days(self):
        """Longest preparation time in the cart, not the sum of them.

        A cart with a same-day item and a five-day item leaves the warehouse
        when the five-day item is ready: adding the two would promise a date
        the shop cannot keep.
        """
        self.ensure_one()
        days = [line.product_id.product_tmpl_id._dps_effective_ships_in_days()
                for line in self._dps_promise_lines()]
        return max(days) if days else 0

    def _dps_promise_country(self):
        """Destination country: the delivery address, else the customer's."""
        self.ensure_one()
        return self.partner_shipping_id.country_id or self.partner_id.country_id

    def _dps_promise_payload(self, now=None):
        self.ensure_one()
        website = self.website_id or self.env['website']._dps_current()
        if not website or not website.delivery_promise_enabled:
            return {}
        if not self._dps_promise_lines():
            return {}
        payload = website._dps_payload(
            self._dps_promise_ships_in_days(), self._dps_promise_country(), now)
        payload['order'] = self
        return payload

    def _dps_stamp_commitment_date(self, now=None):
        """Write the promise on the order as its commitment date.

        Only when the order belongs to a website and the field is still empty:
        a date the merchant typed by hand is the merchant's decision and is
        never overwritten. The date is stored at 12:00 in the website timezone,
        far enough from midnight that a daylight-saving shift cannot move it to
        the day before. ``now`` is injectable so the stamping can be pinned in a
        test without waiting for a given weekday.
        """
        for order in self:
            if not order.website_id or order.commitment_date:
                continue
            moment = now if now is not None else order.date_order
            payload = order._dps_promise_payload(now=moment)
            if not payload:
                continue
            local = datetime.combine(payload['date'], time(12, 0))
            order.commitment_date = order.website_id._dps_timezone().localize(local) \
                .astimezone(pytz.utc).replace(tzinfo=None)

    def action_confirm(self):
        """Stamp the promise once the quotation becomes an order.

        Confirmation rewrites ``date_order`` to the confirmation instant, so the
        promise is taken from the order as it stands afterwards: a cart left open
        for three days must not be promised the date it was created on.
        """
        result = super().action_confirm()
        self._dps_stamp_commitment_date()
        return result
