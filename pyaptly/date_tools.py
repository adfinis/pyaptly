"""Tools to convert and round dates."""
import datetime


def iso_first_week_start(iso_year, tzinfo=None):
    """Return the gregorian calendar date of the first day of the given ISO year.

    :param iso_year: Year to find the date of the first week.
    :type  iso_year: int
    """
    fourth_jan = datetime.datetime(iso_year, 1, 4, tzinfo=tzinfo)
    delta = datetime.timedelta(fourth_jan.isoweekday() - 1)
    return fourth_jan - delta


def iso_to_gregorian(iso_year, iso_week, iso_day, tzinfo=None):
    """Gregorian calendar date for the given ISO year, week and day.

    :param iso_year: ISO year
    :type  iso_year: int
    :param iso_week: ISO week
    :type  iso_week: int
    :param  iso_day: ISO day
    :type   iso_day: int
    """
    year_start = iso_first_week_start(iso_year, tzinfo)
    return year_start + datetime.timedelta(days=iso_day - 1, weeks=iso_week - 1)


def time_remove_tz(time):
    """Convert a `datetime.time` to `datetime.time` to without tzinfo.

    :param time: Time to convert
    :type  time: :py:class:`datetime.time`
    :rtype:      :py:class:`datetime.time`
    """
    return datetime.time(
        hour=time.hour,
        minute=time.minute,
        second=time.second,
        microsecond=time.microsecond,
    )


def time_delta_helper(time):  # pragma: no cover
    """Convert a `datetime.time` to `datetime.datetime` to calculate deltas.

    :param time: Time to convert
    :type  time: :py:class:`datetime.time`
    :rtype:      :py:class:`datetime.datetime`
    """
    return datetime.datetime(
        year=2000,
        month=1,
        day=1,
        hour=time.hour,
        minute=time.minute,
        second=time.second,
        microsecond=time.microsecond,
        tzinfo=time.tzinfo,
    )


def date_round_weekly(date, day_of_week=1, time=None):
    """Round datetime back (floor) to a given the of the week.

    THIS FUNCTION IGNORES THE TZINFO OF TIME and assumes it is the same tz as
    the date.

    :param        date: Datetime object to round
    :type         date: :py:class:`datetime.datetime`
    :param day_of_week: ISO day of week: monday is 1 and sunday is 7
    :type  day_of_week: int
    :param        time: Roundpoint in the day (tzinfo ignored)
    :type         time: :py:class:`datetime.time`
    :rtype:             :py:class:`datetime.datetime`
    """
    if time:
        time = time_remove_tz(time)
    else:  # pragma: no cover
        time = datetime.time(hour=0, minute=0)

    delta = datetime.timedelta(
        days=day_of_week - 1,
        hours=time.hour,
        minutes=time.minute,
        seconds=time.second,
        microseconds=time.microsecond,
    )
    raster_date = date - delta
    iso = raster_date.isocalendar()
    rounded_date = iso_to_gregorian(iso[0], iso[1], 1, date.tzinfo)
    return rounded_date + delta


def date_round_daily(date, time=None):
    """Round datetime to day back (floor) to the roundpoint (time) in the day.

    THIS FUNCTION IGNORES THE TZINFO OF TIME and assumes it is the same tz as
    the date.

    :param date: Datetime object to round
    :type  date: :py:class:`datetime.datetime`
    :param time: Roundpoint in the day (tzinfo ignored)
    :type  time: :py:class:`datetime.time`
    :rtype:      :py:class:`datetime.datetime`
    """
    if time:
        time = time_remove_tz(time)
    else:  # pragma: no cover
        time = datetime.time(hour=0, minute=0)
    delta = datetime.timedelta(
        hours=time.hour,
        minutes=time.minute,
        seconds=time.second,
        microseconds=time.microsecond,
    )
    raster_date = date - delta
    rounded_date = datetime.datetime(
        year=raster_date.year,
        month=raster_date.month,
        day=raster_date.day,
        tzinfo=raster_date.tzinfo,
    )
    return rounded_date + delta


def expand_timestamped_name(name, timestamp_config, date=None):
    """Expand a timestamped name using round_timestamp.

    :param timestamp_config: Contains the recurrence specification for the
                             timestamp. See :func:`round_timestamp`
    :type  timestamp_config: dict
    :param             date: The date to expand the timestamp with.
    :type              date: :py:class:`datetime.datetime`
    """
    if "%T" not in name:
        return name
    timestamp = round_timestamp(timestamp_config, date)
    return name.replace("%T", timestamp.strftime("%Y%m%dT%H%MZ"))


def round_timestamp(timestamp_config, date=None):
    """Round the given name by adding a timestamp.

    The contents of the timestamp is configured by the given timestamp_config
    dict, which MUST contain a "time" key, and MAY contain a "repeat-weekly"
    key.

    If the key "repeat-weekly" is given, it is expected to contain a
    three-letter weekday name (mon, tue, thu, ...). The "time" key is expected
    to be a 24 hour HH:MM time specification.

    Timestamps are rounded down to the nearest time as specified (which may be
    on the previous day. If repeat-weekly is specified, it is rounded down
    (back in time) to the given weekday.)

    The name parameter may be a simple string. If it contains the marker "%T",
    then this placeholder will be replaced by the timestamp. If it does NOT
    contain that marker, then nothing happens (and the timestamp_config is not
    evaluated at all)

    If a datetime object is given as third parameter, then it is used to
    generate the timestamp. If it is omitted, the current date/time is used.

    Example:
    >>> expand_timestamped_name(
    ...     'foo-%T',
    ...     {'timestamp': {'time': '00:00'}},
    ...     datetime.datetime(2015,10,7, 15,30)  # A Wednesday
    ... )
    'foo-20151007T0000Z'

    >>> expand_timestamped_name(
    ...     'foo-%T',
    ...     {'timestamp': {'time': '00:00', 'repeat-weekly': 'mon'}},
    ...     datetime.datetime(2015,10,8, 15,30)  # A Thursday
    ... )
    'foo-20151005T0000Z'

    >>> expand_timestamped_name(
    ...     'foo',  # No %T placeholder, timestamp info is ignored
    ...     {'timestamp': {'time': '00:00', 'repeat-weekly': 'mon'}},
    ...     datetime.datetime(2015,10,8, 15,30)
    ... )
    'foo'

    :param timestamp_config: Contains the recurrence specification for the
                             timestamp.
    :type  timestamp_config: dict
    :param             date: The date to expand the timestamp with.
    :type              date: :py:class:`datetime.datetime`
    """
    timestamp_info = timestamp_config.get("timestamp", timestamp_config)
    config_time = timestamp_info.get("time", "FAIL")
    if config_time == "FAIL":  # pragma: no cover
        raise ValueError(
            "Timestamp config has no valid time entry: %s" % str(timestamp_config)
        )

    config_repeat_weekly = timestamp_info.get("repeat-weekly", None)

    hour, minute = [int(x) for x in config_time.split(":")][:2]

    if date is None:
        date = datetime.datetime.now()

    if config_repeat_weekly is not None:
        day_of_week = day_of_week_map.get(config_repeat_weekly.lower())

        timestamp = date_round_weekly(
            date, day_of_week, datetime.time(hour=hour, minute=minute)
        )
    else:
        timestamp = date_round_daily(date, datetime.time(hour=hour, minute=minute))
    return timestamp


def format_timestamp(timestamp):
    """Wrap for strftime, to ensure we're all using the same format.

    :param timestamp: The timestamp to format
    :type  timestamp: :py:class:`datetime.datetime`
    """
    return timestamp.strftime("%Y%m%dT%H%MZ")


day_of_week_map = {
    "mon": 1,
    "tue": 2,
    "wed": 3,
    "thu": 4,
    "fri": 5,
    "sat": 6,
    "sun": 7,
}
