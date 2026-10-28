# -*- coding: utf-8 -*-
from odoo import fields, models


class WebsiteDeliveryCountryExtra(models.Model):
    _name = 'website.delivery.country.extra'
    _description = 'Delivery Extra Days per Country'
    _order = 'country_id'

    website_id = fields.Many2one(
        'website', string='Website', required=True, ondelete='cascade', index=True)
    country_id = fields.Many2one(
        'res.country', string='Country', required=True,
        help='Destination country the extra transit days apply to.')
    extra_days = fields.Integer(
        string='Extra days', default=0,
        help='Transit days added on top of the product preparation time for this '
             'destination. They are counted in working days, so a Saturday is never '
             'part of the three days a remote destination adds.')

    _sql_constraints = [
        ('website_country_unique', 'unique(website_id, country_id)',
         'This website already has extra days for that country.'),
    ]
