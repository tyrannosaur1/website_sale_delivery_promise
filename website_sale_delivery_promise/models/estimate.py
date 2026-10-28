# -*- coding: utf-8 -*-
"""Date arithmetic behind the delivery promise.

Everything in this module is a pure function of its arguments. ``estimate_date``
never reads the clock, the database or the website configuration: the caller
passes ``now`` **already converted to the website timezone**, which is the only
way the boundary cases in ``tests/test_estimate.py`` can be pinned.

Timezone note: the conversion belongs to the caller on purpose. A shop in UTC+8
that computes "now" in UTC sees 07:30 when the shop clock says 15:30, so an
order placed after a 14:00 cut-off would be promised one day too early; the
mistake is invisible in the arithmetic and only shows up on the calendar.
"""
from datetime import datetime, time, timedelta

ALL_WEEKDAYS = frozenset((1, 2, 3, 4, 5, 6, 7))
WEEKDAY_NAMES = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
MONTH_NAMES = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

# How far forward the search may walk before giving up. Every day of the year
# being closed is a configuration mistake, not a delivery date; the caller gets
# a plain calendar offset instead of an endless loop.
_HORIZON_DAYS = 4000


def cutoff_minutes(cutoff):
    """Cut-off expressed in minutes after midnight.

    Accepts a float hour (``14``, ``14.5``), a ``datetime.time`` or ``None``.
    A value of 24 hours or more means "no cut-off": every order of the day is
    still prepared today. The bound is inclusive -- an order placed at exactly
    the cut-off minute is on time.
    """
    if isinstance(cutoff, time):
        return cutoff.hour * 60 + cutoff.minute
    if cutoff is None:
        return 24 * 60
    minutes = int(round(float(cutoff) * 60))
    if minutes <= 0:
        return 0
    return min(minutes, 24 * 60)


def minute_of_day(moment):
    """Minutes elapsed since midnight, seconds included as a fraction."""
    return moment.hour * 60 + moment.minute + moment.second / 60.0 \
        + moment.microsecond / 60000000.0


def _as_date(value):
    return value.date() if isinstance(value, datetime) else value


def is_open_day(day, working_days, holidays):
    """Whether goods can be prepared on ``day``."""
    if day in holidays:
        return False
    # An empty set of working days is read as "every day": a merchant who
    # unticked every box asked for no restriction, not for an infinite promise.
    return not working_days or day.isoweekday() in working_days


def _walk(start, working_days, holidays, steps):
    """The ``steps``-th open day strictly after ``start``.

    ``steps == 0`` returns ``start`` unchanged, so the caller can use one helper
    both to find the preparation day and to add the transit days.
    """
    if steps <= 0:
        return start
    day = start
    remaining = steps
    guard = _HORIZON_DAYS
    while remaining:
        if guard <= 0:
            return start + timedelta(days=steps)
        day += timedelta(days=1)
        guard -= 1
        if is_open_day(day, working_days, holidays):
            remaining -= 1
    return day


def estimate_date(now, ships_in_days=0, cutoff=14.0, working_days=None,
                  holidays=(), extra_days=0):
    """Promised delivery date for an order placed at ``now``.

    :param now: naive ``datetime`` in the *website* timezone.
    :param ships_in_days: preparation days; 0 means same-day dispatch, a
        negative value is read as 0.
    :param cutoff: daily cut-off in hours (see ``cutoff_minutes``).
    :param working_days: ISO weekdays (1 = Monday) the shop prepares goods.
        ``None`` or empty means every day.
    :param holidays: dates the shop is closed, whatever the weekday.
    :param extra_days: transit days for the destination country, added on top
        of the preparation days and then walked over closed days.

    The preparation day is today when the shop is open and the order is placed
    on or before the cut-off, otherwise the next open day. The delivery date is
    then that many open days later, so a Friday order placed after the cut-off
    with one preparation day lands on Tuesday, not on Saturday.
    """
    work = frozenset(int(day) for day in (working_days or ())) or ALL_WEEKDAYS
    closed = frozenset(_as_date(day) for day in (holidays or ()))
    today = _as_date(now)

    on_time = minute_of_day(now) <= cutoff_minutes(cutoff)
    if on_time and is_open_day(today, work, closed):
        dispatch = today
    else:
        dispatch = _walk(today, work, closed, 1)

    days = max(int(ships_in_days or 0), 0) + max(int(extra_days or 0), 0)
    return _walk(dispatch, work, closed, days)


def format_date(day):
    """``Fri, 30 Oct`` -- built from tables, not from ``strftime``.

    ``strftime`` follows the process locale, so the same order would read
    "Fri, 30 Oct" on one server and "vie., 30 oct." on another. The promise is
    a customer-facing date, so it is spelled out here and translated through
    the usual catalogue.
    """
    return '%s, %02d %s' % (WEEKDAY_NAMES[day.weekday()], day.day,
                            MONTH_NAMES[day.month - 1])


def format_countdown(minutes):
    """``3h 12m`` / ``42m`` -- the time left before the cut-off."""
    total = max(int(minutes), 0)
    if total >= 60:
        return '%dh %02dm' % (total // 60, total % 60)
    return '%dm' % total


def format_countdown_seconds(seconds):
    """``3h 12m`` / ``42m`` from a number of seconds left.

    The browser ticks once a second, so the moving value is a duration in
    seconds. Truncating to whole minutes first keeps the first paint identical
    to ``format_countdown(cutoff - now)``; the front-end copy in
    static/src/js/delivery_promise.js mirrors this arithmetic, which is why the
    rounding lives here and not in the template.
    """
    return format_countdown(max(int(seconds), 0) // 60)
