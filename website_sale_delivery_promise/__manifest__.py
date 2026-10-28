# -*- coding: utf-8 -*-
{
    'name': 'Delivery Promise for the Website',
    'version': '18.0.1.0.0',
    'summary': 'Tell shoppers when the order will arrive, from the cut-off, the '
               'working week, the holidays and the destination country.',
    'description': """
Delivery Promise for the Website
================================

"Order within 3h 12m, delivered by Fri, 30 Oct" on the product page, in the cart
and at checkout, computed from the shop's own calendar instead of a fixed text.

* Daily cut-off per website: an order placed after it is prepared the next
  working day, one minute before it is still shipped today.
* Working week per website: the days goods are prepared. Saturday and Sunday are
  closed by default, and a shop that closes on Friday evening is one tick away.
* Holidays: a list of closed days per website, skipped exactly like a weekend,
  including chains of consecutive days and a holiday that falls on a Saturday.
* Extra transit days per destination country, added on top of the preparation
  time of the slowest item in the cart and walked over closed days.
* Preparation time per product: a number of working days, 0 for same-day
  dispatch, or "follow the Sales Lead Time" so the promise never drifts away from
  the lead time the rest of the company uses.
* The cart promises the date of its slowest line, not the sum of the lines: a
  same-day item does not delay a five-day item, and it does not accelerate it.
* At checkout the destination country is known, so its extra days are included.
  The promise is written on the order as its commitment date when the order is
  confirmed and the field is still empty; a date typed by the merchant is never
  overwritten.

Timezone
--------

The cut-off is read in the website's own timezone, not in UTC. A shop in UTC+8
that compares the cut-off with the server clock sees 07:30 when the shop clock
says 15:30, and would promise a date one day too early for every order placed
after 16:00 local time. Set the timezone next to the cut-off in the website
settings; the default is the company's.

The date arithmetic is a pure function of the moment it is given, so the
boundary cases (one minute either side of the cut-off, a Friday order, a holiday
chain, 31 December) are covered by a table of tests rather than by waiting for
the right weekday.
""",
    'author': 'ModForge',
    'license': 'OPL-1',
    'category': 'Website/Website',
    'depends': ['website_sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_views.xml',
        'views/website_views.xml',
        'views/product_views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_delivery_promise/static/src/js/delivery_promise.js',
            'website_sale_delivery_promise/static/src/css/delivery_promise.css',
        ],
    },
    'installable': True,
    'application': False,
    'price': 39.0,
    'currency': 'USD',
}
