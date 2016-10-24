"""Dateround tests"""

import datetime
import os.path
import sys

from . import (date_round_daily, date_round_weekly, iso_to_gregorian,  # noqa
               snapshot_spec_to_name, test, time_delta_helper, time_remove_tz)

_test_base = os.path.dirname(
    os.path.abspath(__file__)
).encode("UTF-8")


if not sys.version_info < (2, 7):  # pragma: no cover
    from hypothesis import given  # noqa
    from hypothesis.extra.datetime import datetimes, times  # noqa
    from hypothesis.strategies import integers  # noqa


if sys.version_info < (2, 7):  # pragma: no cover
    import mock
    given = mock.MagicMock()  # noqa
    datetimes = mock.MagicMock()  # noqa
    times = mock.MagicMock()  # noqa
    integers = mock.MagicMock()  # noqa


@test.hypothesis_min_ver
@given(datetimes())
def test_is_to_gregorian(date):  # pragma: no cover
    """Test if a roundtrip of isoclander() -> iso_to_gregorian() is correct"""
    iso_tuple = date.isocalendar()
    new_date  = iso_to_gregorian(*iso_tuple)
    assert date.year  == new_date.year
    assert date.month == new_date.month
    assert date.day   == new_date.day


@test.hypothesis_min_ver
@given(
    datetimes(min_year=2),
    integers(min_value=1, max_value=7),
    times())
def test_round_weekly(date, day_of_week, time):  # pragma: no cover
    """Test if the round function rounds the expected delta"""
    time            = time_remove_tz(time)
    round_date      = date_round_weekly(date, day_of_week, time)
    date_time       = datetime.time(
        hour        = date.hour,
        minute      = date.minute,
        second      = date.second,
        microsecond = date.microsecond,
    )
    # double round
    assert round_date == date_round_weekly(round_date, day_of_week, time)
    if round_date == date:  # pragma: no cover
        # Find tz problems
        assert date_time == time
        assert round_date.isoweekday() == day_of_week
    else:
        # Always round down
        assert round_date < date
        # Never round more than 7 days
        assert date - round_date < datetime.timedelta(days=7)
        # Check if rounded on given time and day
        assert round_date.hour         == time.hour
        assert round_date.minute       == time.minute
        assert round_date.second       == time.second
        assert round_date.microsecond  == time.microsecond
        assert round_date.isoweekday() == day_of_week
        # Expected delta
        date_delta = date - round_date
        date_day_time_delta = (
            time_delta_helper(date_time) +
            datetime.timedelta(days=date.weekday())
        )
        given_day_time_delta = (
            time_delta_helper(time) +
            datetime.timedelta(days=day_of_week - 1)
        )
        delta = date_day_time_delta - given_day_time_delta
        if date_day_time_delta > given_day_time_delta:
            assert date_delta == delta
        else:
            # Wrap the week
            delta += datetime.timedelta(days=7)
            assert date_delta == delta


def test_weekly_examples():
    """Test if the round function rounds at the given day and time"""
    date        = datetime.datetime(
        year    = 2015,
        month   = 11,
        day     = 3,
        hour    = 22,
        minute  = 59,
    )
    time        = datetime.time(
        hour    = 23,
        minute  = 0
    )
    day_of_week = 2
    rounded = date_round_weekly(date, day_of_week, time)
    assert datetime.datetime(2015, 10, 27, 23, 0) == rounded
    date        = datetime.datetime(
        year    = 2015,
        month   = 11,
        day     = 3,
        hour    = 23,
        minute  = 1,
    )
    rounded = date_round_weekly(date, day_of_week, time)
    assert datetime.datetime(2015, 11, 3, 23, 0) == rounded


@test.hypothesis_min_ver
@given(datetimes(), times())
def test_round_daily(date, time):  # pragma: no cover
    """Test if the round function rounds the expected delta"""
    time            = time_remove_tz(time)
    round_date      = date_round_daily(date, time)
    date_time       = datetime.time(
        hour        = date.hour,
        minute      = date.minute,
        second      = date.second,
        microsecond = date.microsecond,
    )
    # double round
    assert round_date == date_round_daily(round_date, time)
    if round_date == date:  # pragma: no cover
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


def test_daily_examples():
    """Test if the round function rounds at the given time"""
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
    date       = datetime.datetime(
        year   = 2015,
        month  = 10,
        day    = 1,
        hour   = 10,
        minute = 59,
    )
    rounded = date_round_daily(date, time)
    assert datetime.datetime(2015, 9, 30, 11, 0) == rounded
    date       = datetime.datetime(
        year   = 2015,
        month  = 10,
        day    = 1,
        hour   = 11,
        minute = 1,
    )
    rounded = date_round_daily(date, time)
    assert datetime.datetime(2015, 10, 1, 11, 0) == rounded


def test_snapshot_spec_to_name():
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish-previous.yml",
    )) as (tyml, config):

        snaps = tyml['snapshot']['superfake-%T']['merge']

        rounded1 = snapshot_spec_to_name(tyml, snaps[0])
        rounded2 = snapshot_spec_to_name(tyml, snaps[1])

        assert rounded1 == 'fakerepo01-20121009T0000Z'
        assert rounded2 == 'fakerepo02-20121006T0000Z'
