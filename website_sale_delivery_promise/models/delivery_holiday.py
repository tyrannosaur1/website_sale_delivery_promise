# -*- coding: utf-8 -*-
from odoo import fields, models


class WebsiteDeliveryHoliday(models.Model):
    _name = 'website.delivery.holiday'
    _description = 'Delivery Holiday'
    _order = 'date'

    website_id = fields.Many2one(
        'website', string='Website', required=True, ondelete='cascade', index=True)
    date = fields.Date(
        string='Date', required=True,
        help='A day the shop does not prepare or ship orders, whatever the weekday.')
    name = fields.Char(
        string='Reason', required=True,
        help='Shown in the back end only, e.g. "National Day" or "Stock count".')

    _sql_constraints = [
        ('website_date_unique', 'unique(website_id, date)',
         'This website already has a holiday on that date.'),
    ]
