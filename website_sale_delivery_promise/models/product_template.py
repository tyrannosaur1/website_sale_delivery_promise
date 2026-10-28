# -*- coding: utf-8 -*-
"""Product-level preparation time and the product page payload."""
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ships_in_days = fields.Integer(
        string='Ships in (days)', default=-1,
        help='Working days needed to prepare this product before it leaves the '
             'warehouse. 0 means it ships the same day. Leave -1 (the default) to '
             'follow the Sales Lead Time of the product; the delivery promise then '
             'moves with the lead time instead of drifting away from it.')

    def _dps_effective_ships_in_days(self):
        """Preparation days actually used, ``sale_delay`` when not overridden."""
        self.ensure_one()
        if self.ships_in_days is not None and self.ships_in_days >= 0:
            return self.ships_in_days
        return max(int(round(self.sale_delay or 0)), 0)

    @api.model
    def _dps_current_website(self):
        """Current website across versions (see ``website._dps_current``)."""
        return self.env['website']._dps_current()

    def _dps_promise_available(self):
        """Cheap check used to skip the block before computing anything.

        It only reads the website toggle, so a product page of a shop that has
        the promise switched off costs no extra queries.
        """
        self.ensure_one()
        website = self._dps_current_website()
        return bool(website and website.delivery_promise_enabled)

    def _dps_promise_payload(self, country=None, now=None):
        """Promise for this product, or ``{}`` when it must not be shown."""
        self.ensure_one()
        website = self._dps_current_website()
        if not website or not website.delivery_promise_enabled:
            return {}
        return website._dps_payload(self._dps_effective_ships_in_days(), country, now)
