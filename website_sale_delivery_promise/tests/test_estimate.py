# -*- coding: utf-8 -*-
"""The date table.

`estimate_date` is the only place a promise date is decided, and it never looks
at the clock: one wrong day here shows up as a plausible date on the product page
and nobody notices until a customer complains. The table below pins one row per
way the date can move, so a one-day error anywhere in the logic breaks at least
one row.
"""
from datetime import date, datetime, time

from odoo.tests.common import TransactionCase

from odoo.addons.website_sale_delivery_promise.models.estimate import (
    cutoff_minutes,
    estimate_date,
    format_countdown,
    format_date,
    minute_of_day,
)

MON_FRI = frozenset((1, 2, 3, 4, 5))
# October 2026: 26th is a Monday, 30th a Friday, 31st a Saturday.
# December 2026: 31st is a Thursday, 1 January 2027 a Friday, 4 January a Monday.

CASES = [
    # -- the cut-off, to the minute -------------------------------------------
    ('one_minute_before_cutoff', datetime(2026, 10, 26, 13, 59), 0, 14.0, MON_FRI, (), 0,
     date(2026, 10, 26)),
    ('exactly_on_cutoff_is_on_time', datetime(2026, 10, 26, 14, 0), 0, 14.0, MON_FRI, (), 0,
     date(2026, 10, 26)),
    ('one_minute_after_cutoff', datetime(2026, 10, 26, 14, 1), 0, 14.0, MON_FRI, (), 0,
     date(2026, 10, 27)),
    ('after_cutoff_with_one_day', datetime(2026, 10, 26, 14, 1), 1, 14.0, MON_FRI, (), 0,
     date(2026, 10, 28)),
    ('before_cutoff_with_one_day', datetime(2026, 10, 26, 13, 59), 1, 14.0, MON_FRI, (), 0,
     date(2026, 10, 27)),
    # -- Friday afternoon and the weekend -------------------------------------
    ('friday_before_cutoff', datetime(2026, 10, 30, 13, 59), 0, 14.0, MON_FRI, (), 0,
     date(2026, 10, 30)),
    ('friday_on_cutoff', datetime(2026, 10, 30, 14, 0), 0, 14.0, MON_FRI, (), 0,
     date(2026, 10, 30)),
    ('friday_after_cutoff_goes_to_monday', datetime(2026, 10, 30, 14, 1), 0, 14.0, MON_FRI, (),
     0, date(2026, 11, 2)),
    ('friday_after_cutoff_one_day', datetime(2026, 10, 30, 14, 1), 1, 14.0, MON_FRI, (), 0,
     date(2026, 11, 3)),
    ('friday_after_cutoff_two_days', datetime(2026, 10, 30, 14, 1), 2, 14.0, MON_FRI, (), 0,
     date(2026, 11, 4)),
    ('saturday_is_skipped', datetime(2026, 10, 31, 10, 0), 0, 14.0, MON_FRI, (), 0,
     date(2026, 11, 2)),
    ('sunday_with_one_day', datetime(2026, 11, 1, 10, 0), 1, 14.0, MON_FRI, (), 0,
     date(2026, 11, 3)),
    # -- holidays -------------------------------------------------------------
    ('holiday_on_the_preparation_day', datetime(2026, 10, 26, 13, 59), 1, 14.0, MON_FRI,
     (date(2026, 10, 27),), 0, date(2026, 10, 28)),
    ('holiday_chain_skips_both_days', datetime(2026, 10, 26, 13, 59), 3, 14.0, MON_FRI,
     (date(2026, 10, 27), date(2026, 10, 28)), 0, date(2026, 11, 2)),
    ('holiday_on_a_saturday_changes_nothing', datetime(2026, 10, 30, 13, 59), 0, 14.0,
     MON_FRI, (date(2026, 10, 31),), 0, date(2026, 10, 30)),
    ('today_is_a_holiday', datetime(2026, 10, 26, 10, 0), 0, 14.0, MON_FRI,
     (date(2026, 10, 26),), 0, date(2026, 10, 27)),
    ('friday_after_cutoff_with_monday_holiday', datetime(2026, 10, 30, 15, 0), 0, 14.0,
     MON_FRI, (date(2026, 11, 2),), 0, date(2026, 11, 3)),
    # -- year boundary --------------------------------------------------------
    ('new_year_eve_after_cutoff', datetime(2026, 12, 31, 15, 0), 0, 14.0, MON_FRI, (), 0,
     date(2027, 1, 1)),
    ('new_year_eve_with_new_year_holiday', datetime(2026, 12, 31, 15, 0), 0, 14.0, MON_FRI,
     (date(2027, 1, 1),), 0, date(2027, 1, 4)),
    # -- country surcharge ----------------------------------------------------
    ('country_extra_days_stack', datetime(2026, 10, 26, 13, 59), 1, 14.0, MON_FRI, (), 2,
     date(2026, 10, 29)),
    ('country_extra_days_walk_over_the_weekend', datetime(2026, 10, 29, 13, 59), 0, 14.0,
     MON_FRI, (), 2, date(2026, 11, 2)),
    ('country_extra_days_respect_holidays', datetime(2026, 10, 26, 13, 59), 0, 14.0, MON_FRI,
     (date(2026, 10, 27),), 2, date(2026, 10, 29)),
    # -- ships_in_days edges --------------------------------------------------
    ('negative_ships_in_days_is_zero', datetime(2026, 10, 26, 13, 59), -1, 14.0, MON_FRI, (),
     0, date(2026, 10, 26)),
    ('forty_five_working_days', datetime(2026, 10, 26, 13, 59), 45, 14.0, MON_FRI, (), 0,
     date(2026, 12, 28)),
    # -- working week and cut-off configuration -------------------------------
    ('seven_day_week_delivers_on_saturday', datetime(2026, 10, 31, 10, 0), 0, 14.0,
     frozenset(range(1, 8)), (), 0, date(2026, 10, 31)),
    ('sunday_only_shop_skips_saturday', datetime(2026, 10, 31, 10, 0), 0, 14.0,
     frozenset((7,)), (), 0, date(2026, 11, 1)),
    ('no_cutoff_still_ships_today', datetime(2026, 10, 26, 23, 59), 0, 24.0, MON_FRI, (), 0,
     date(2026, 10, 26)),
    ('midnight_cutoff_is_already_passed', datetime(2026, 10, 26, 23, 59), 0, 0.0, MON_FRI, (),
     0, date(2026, 10, 27)),
    ('empty_working_week_means_every_day', datetime(2026, 10, 26, 13, 59), 0, 14.0,
     frozenset(), (), 0, date(2026, 10, 26)),
    ('half_hour_cutoff', datetime(2026, 10, 26, 14, 29), 0, 14.5, MON_FRI, (), 0,
     date(2026, 10, 26)),
    ('half_hour_cutoff_passed', datetime(2026, 10, 26, 14, 31), 0, 14.5, MON_FRI, (), 0,
     date(2026, 10, 27)),
]


class TestEstimateDate(TransactionCase):

    def test_boundary_table(self):
        for label, now, ships, cutoff, working, holidays, extra, expected in CASES:
            with self.subTest(label):
                self.assertEqual(
                    estimate_date(now, ships, cutoff, working, holidays, extra),
                    expected, label)

    def test_the_clock_is_never_read(self):
        """A 2020 order must land in 2020, whatever today is.

        If ``estimate_date`` called ``datetime.now()`` internally, this row would
        return the day the suite happens to run on.
        """
        self.assertEqual(
            estimate_date(datetime(2020, 1, 6, 9, 0), 0, 14.0, MON_FRI),
            date(2020, 1, 6))

    def test_cutoff_accepts_a_time_object(self):
        self.assertEqual(cutoff_minutes(time(14, 30)), 870)
        self.assertEqual(cutoff_minutes(14.5), 870)
        self.assertEqual(cutoff_minutes(0), 0)
        self.assertEqual(cutoff_minutes(25), 24 * 60)
        self.assertEqual(cutoff_minutes(None), 24 * 60)

    def test_minute_of_day_keeps_the_seconds(self):
        self.assertEqual(minute_of_day(datetime(2026, 10, 26, 14, 0)), 840.0)
        self.assertAlmostEqual(minute_of_day(datetime(2026, 10, 26, 14, 0, 30)), 840.5)

    def test_format_date_is_locale_independent(self):
        self.assertEqual(format_date(date(2026, 10, 30)), 'Fri, 30 Oct')
        self.assertEqual(format_date(date(2027, 1, 4)), 'Mon, 04 Jan')

    def test_format_countdown(self):
        self.assertEqual(format_countdown(194), '3h 14m')
        self.assertEqual(format_countdown(59), '59m')
        self.assertEqual(format_countdown(60), '1h 00m')
        self.assertEqual(format_countdown(-5), '0m')
