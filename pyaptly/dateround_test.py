"""Dateround tests"""

import datetime
from . import (
    date_round_daily, time_remove_tz, time_delta_helper, iso_to_gregorian
)
from hypothesis import given
from hypothesis.extra.datetime import datetimes, times


@given(datetimes())
def test_is_to_gregorian(date):
    iso_tuple = date.isocalendar()
    new_date  = iso_to_gregorian(*iso_tuple)
    assert date.year  == new_date.year
    assert date.month == new_date.month
    assert date.day   == new_date.day


@given(datetimes(), times())
def test_round_daily_diff(date, time):
    time            = time_remove_tz(time)
    round_date      = date_round_daily(date, time)
    date_time       = datetime.time(
        hour        = date.hour,
        minute      = date.minute,
        second      = date.second,
        microsecond = date.microsecond,
    )
    if round_date == date:
        # Find tz problems
        assert date_time == time
    else:
        # Always round down
        assert round_date < date
        # Never round more than 24 hours
        assert date - round_date < datetime.timedelta(hours=24)
        # Check if rounded on given time
        assert round_date.hour        == time.hour
        assert round_date.minute      == time.minute
        assert round_date.second      == time.second
        assert round_date.microsecond == time.microsecond
        # Expected delta
        date_delta = date - round_date
        time_delta = time_delta_helper(date_time) - time_delta_helper(time)
        if date_time > time:
            assert date_delta == time_delta
        else:
            # Wrap the day
            time_delta += datetime.timedelta(days=1)
            assert date_delta == time_delta


def test_examples():
    date       = datetime.datetime(
        year   = 2015,
        month  = 10,
        day    = 1,
        hour   = 12,
        minute = 34,
    )
    time       = datetime.time(
        hour   = 23,
        minute = 00
    )
    rounded = date_round_daily(date, time)
    assert datetime.datetime(2015, 9, 30, 23, 0) == rounded
    time       = datetime.time(
        hour   = 11,
        minute = 00
    )
    rounded = date_round_daily(date, time)
    assert datetime.datetime(2015, 10, 1, 11, 0) == rounded
