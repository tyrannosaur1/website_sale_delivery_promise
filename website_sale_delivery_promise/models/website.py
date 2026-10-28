# -*- coding: utf-8 -*-
"""Website configuration and the payload every front-end block renders."""
import pytz

from odoo import _, api, fields, models

from .estimate import (
    cutoff_minutes,
    estimate_date,
    format_countdown,
    format_date,
    is_open_day,
    minute_of_day,
)

# The cut-off, the working week, the holidays and the country surcharges are all
# per website: a shop that closes on Friday evening and a shop that closes on
# Sunday cannot share one promise.
_TZ_SELECTION = [(name, name) for name in pytz.common_timezones]


def _default_tz(env):
    return env.company.partner_id.tz or 'UTC'


class Website(models.Model):
    _inherit = 'website'

    delivery_promise_enabled = fields.Boolean(
        string='Show the delivery promise', default=True,
        help='Display "Order within ..., delivered by ..." on the product page, in '
             'the cart and at checkout.')
    delivery_cutoff_hour = fields.Float(
        string='Daily cut-off (hour)', default=14.0, digits=(2, 2),
        help='Hour of the day, in the timezone below, after which an order is '
             'prepared the next working day. 14.5 means 14:30. Set 24 to remove the '
             'cut-off entirely.')

    delivery_open_mon = fields.Boolean(string='Monday', default=True)
    delivery_open_tue = fields.Boolean(string='Tuesday', default=True)
    delivery_open_wed = fields.Boolean(string='Wednesday', default=True)
    delivery_open_thu = fields.Boolean(string='Thursday', default=True)
    delivery_open_fri = fields.Boolean(string='Friday', default=True)
    delivery_open_sat = fields.Boolean(string='Saturday', default=False)
    delivery_open_sun = fields.Boolean(string='Sunday', default=False)

    delivery_tz = fields.Selection(
        selection=_TZ_SELECTION, string='Promise timezone',
        default=lambda self: _default_tz(self.env), required=True,
        help='Timezone the cut-off is read in. A promise computed in UTC for a shop '
             'in UTC+8 is one day short for every order placed after 16:00 local.')

    delivery_holiday_ids = fields.One2many(
        'website.delivery.holiday', 'website_id', string='Holidays')
    delivery_country_extra_ids = fields.One2many(
        'website.delivery.country.extra', 'website_id',
        string='Extra days per country')

    # ------------------------------------------------------------------
    # Configuration readers
    # ------------------------------------------------------------------
    @api.model
    def _dps_current(self):
        """The website serving the current request, across versions.

        ``website.get_current_website()`` is gone in Odoo 20 in favour of
        ``request.env.website``; this helper is the only place that knows it.
        Outside a request both paths fall back to the first website, which is
        what the back end and the tests want.
        """
        if hasattr(self.env, 'website') and self.env.website:
            return self.env.website
        if hasattr(self, 'get_current_website'):
            return self.get_current_website()
        return self.search([], limit=1)

    def _dps_open_days(self):
        """ISO weekdays (1 = Monday) the shop prepares orders."""
        self.ensure_one()
        days = set()
        for index, name in enumerate(('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'),
                                     start=1):
            if self['delivery_open_%s' % name]:
                days.add(index)
        return frozenset(days)

    def _dps_holiday_dates(self):
        """Closed days of this website, readable by the public user.

        The product page computes its promise as the visitor, who has no ACL on
        the configuration models; the holiday list is shop configuration, not
        customer data, so it is read with ``sudo`` instead of granting the
        public group access to the back-end menus.
        """
        self.ensure_one()
        return frozenset(self.sudo().delivery_holiday_ids.mapped('date'))

    def _dps_extra_days(self, country):
        """Transit days added for a destination country (0 when not configured)."""
        self.ensure_one()
        if not country:
            return 0
        extra = self.sudo().delivery_country_extra_ids.filtered(
            lambda line: line.country_id == country)[:1]
        return max(extra.extra_days or 0, 0)

    def _dps_timezone(self):
        self.ensure_one()
        try:
            return pytz.timezone(self.delivery_tz or 'UTC')
        except pytz.UnknownTimeZoneError:
            return pytz.utc

    def _dps_local(self, moment=None):
        """Naive ``datetime`` of ``moment`` in the promise timezone.

        ``moment`` is a *UTC* datetime (naive, as Odoo stores them, or aware);
        ``None`` means the current instant. Nothing downstream converts a
        timezone again: ``estimate_date`` only ever sees local wall time.
        """
        if moment is None:
            moment = fields.Datetime.now()
        if moment.tzinfo is None:
            moment = pytz.utc.localize(moment)
        return moment.astimezone(self._dps_timezone()).replace(tzinfo=None)

    # ------------------------------------------------------------------
    # Payload
    # ------------------------------------------------------------------
    def _dps_payload(self, ships_in_days, country=None, now=None):
        """Everything the front end prints for one promise.

        ``now`` is a UTC datetime; tests pass it explicitly, the front end does
        not, so the promise follows the shop clock rather than the server one.
        Returns ``{}`` when the promise is switched off for the website.
        """
        self.ensure_one()
        if not self.delivery_promise_enabled:
            return {}
        local = self._dps_local(now)
        work = self._dps_open_days()
        closed = self._dps_holiday_dates()
        extra = self._dps_extra_days(country)
        day = estimate_date(local, ships_in_days, self.delivery_cutoff_hour,
                            work, closed, extra)
        left = cutoff_minutes(self.delivery_cutoff_hour) - minute_of_day(local)
        counting = bool(left > 0 and is_open_day(local.date(), work, closed))
        date_text = format_date(day)
        if counting:
            text = _('Order within %(left)s, delivered by %(date)s',
                     left=format_countdown(left), date=date_text)
        else:
            text = _('Order now, delivered by %(date)s', date=date_text)
        return {
            'date': day,
            'date_text': date_text,
            'text': text,
            'countdown': format_countdown(left) if counting else False,
            'ships_in_days': max(int(ships_in_days or 0), 0),
            'extra_days': extra,
        }
