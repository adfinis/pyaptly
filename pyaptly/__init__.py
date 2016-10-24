#!/usr/bin/env python2
"""Aptly mirror/snapshot managment automation."""
import argparse
import codecs
import collections
import datetime
import logging
import os
import re
import subprocess
import sys

import freeze
import six
import yaml

_logging_setup = False

if six.PY2:
    environb = os.environ  # pragma: no cover
else:
    environb = os.environb  # pragma: no cover


def init_hypothesis():
    """Initialize hypothesis profile if hypothesis is available"""
    try:  # pragma: no cover:w
        if b'HYPOTHESIS_PROFILE' in environb:
            from hypothesis import Settings
            Settings.register_profile("ci", Settings(
                max_examples=10000
            ))
            Settings.load_profile(os.getenv(u'HYPOTHESIS_PROFILE', 'default'))
    except (ImportError, AttributeError):  # pragma: no cover
        pass


def get_logger():
    """Get the logger.

    :rtype: logging.Logger"""
    return logging.getLogger("pyaptly")

lg = get_logger()
init_hypothesis()


def iso_first_week_start(iso_year, tzinfo=None):
    """The gregorian calendar date of the first day of the given ISO year

    :param iso_year: Year to find the date of the first week.
    :type  iso_year: int"""
    fourth_jan = datetime.datetime(iso_year, 1, 4, tzinfo=tzinfo)
    delta = datetime.timedelta(fourth_jan.isoweekday() - 1)
    return fourth_jan - delta


def iso_to_gregorian(iso_year, iso_week, iso_day, tzinfo=None):
    """Gregorian calendar date for the given ISO year, week and day

    :param iso_year: ISO year
    :type  iso_year: int
    :param iso_week: ISO week
    :type  iso_week: int
    :param  iso_day: ISO day
    :type   iso_day: int"""
    year_start = iso_first_week_start(iso_year, tzinfo)
    return year_start + datetime.timedelta(
        days=iso_day - 1,
        weeks=iso_week - 1
    )


def time_remove_tz(time):
    """Convert a :py:class`datetime.time` to :py:class`datetime.time` to
    without tzinfo.

    :param time: Time to convert
    :type  time: :py:class:`datetime.time`
    :rtype:      :py:class:`datetime.time`
    """
    return datetime.time(
        hour        = time.hour,
        minute      = time.minute,
        second      = time.second,
        microsecond = time.microsecond,
    )


def time_delta_helper(time):  # pragma: no cover
    """Convert a :py:class`datetime.time` to :py:class`datetime.datetime` to
    calculate deltas

    :param time: Time to convert
    :type  time: :py:class:`datetime.time`
    :rtype:      :py:class:`datetime.datetime`
    """
    return datetime.datetime(
        year        = 2000,
        month       = 1,
        day         = 1,
        hour        = time.hour,
        minute      = time.minute,
        second      = time.second,
        microsecond = time.microsecond,
        tzinfo      = time.tzinfo,
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
    :rtype:             :py:class:`datetime.datetime`"""
    if time:
        time         = time_remove_tz(time)
    else:  # pragma: no cover
        time         = datetime.time(hour=0, minute=0)

    delta            = datetime.timedelta(
        days         = day_of_week - 1,
        hours        = time.hour,
        minutes      = time.minute,
        seconds      = time.second,
        microseconds = time.microsecond,
    )
    raster_date  = date - delta
    iso = raster_date.isocalendar()
    rounded_date = iso_to_gregorian(iso[0], iso[1], 1, date.tzinfo)
    return rounded_date + delta


def date_round_daily(date, time=None):
    """Round datetime to day back (floor) to the roundpoint (time) in the day

    THIS FUNCTION IGNORES THE TZINFO OF TIME and assumes it is the same tz as
    the date.

    :param date: Datetime object to round
    :type  date: :py:class:`datetime.datetime`
    :param time: Roundpoint in the day (tzinfo ignored)
    :type  time: :py:class:`datetime.time`
    :rtype:      :py:class:`datetime.datetime`"""
    if time:
        time         = time_remove_tz(time)
    else:  # pragma: no cover
        time         = datetime.time(hour=0, minute=0)
    delta            = datetime.timedelta(
        hours        = time.hour,
        minutes      = time.minute,
        seconds      = time.second,
        microseconds = time.microsecond,
    )
    raster_date  = date - delta
    rounded_date = datetime.datetime(
        year     = raster_date.year,
        month    = raster_date.month,
        day      = raster_date.day,
        tzinfo   = raster_date.tzinfo
    )
    return rounded_date + delta


def call_output(args, input_=None):
    """Call command and return output.

    :param   args: Command to execute
    :type    args: list
    :param input_: Input to command
    :type  input_: bytes
    """
    p = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    output, err = p.communicate(input_)
    if p.returncode != 0:
        raise subprocess.CalledProcessError(
            p.returncode,
            args,
        )
    return (output.decode("UTF-8"), err.decode("UTF-8"))


class Command(object):
    """Repesents a system command and is used to resolve dependencies between
    such commands.

    :param cmd: The command as list, one item per argument
    :type  cmd: list
    """

    pretend_mode = False

    def __init__(self, cmd):
        self.cmd = cmd
        self._requires = set()
        self._provides = set()
        self._finished = None
        self._known_dependency_types = (
            'snapshot', 'mirror', 'repo', 'publish', 'virtual'
        )

    def get_provides(self):  # pragma: no cover
        """Return all provides of this command.

        :rtype: set()"""
        return self._provides

    def append(self, argument):
        """Append additional arguments to the command.

        :param argument: String argument to append
        :type  argument: str"""
        assert str(argument) == argument
        self.cmd.append(argument)

    def require(self, type_, identifier):
        """Require a dependency for this command.

        :param      type_: Type or category of the dependency ie. snapshot
        :type       type_: str
        :param identifier: Identifier of the dependency for example name of a
                           snapshot
        :type  identifier: usually str
        """
        assert type_ in (
            self._known_dependency_types +
            ('any', ) +
            SystemStateReader.known_dependency_types
        )
        self._requires.add((type_, str(identifier)))

    def provide(self, type_, identifier):
        """Provide a dependency for this command.

        :param      type_: Type or category of the dependency ie. snapshot
        :type       type_: str
        :param identifier: Identifier of the dependency for example name of a
                           snapshot
        :type  identifier: usually str
        """
        assert type_ in self._known_dependency_types
        self._provides.add((type_, str(identifier)))

    def execute(self):
        """Execute the command. Return the return value of the command.

        :rtype: integer"""
        if self._finished is not None:  # pragma: no cover
            return self._finished

        if not Command.pretend_mode:
            lg.debug('Running command: %s', ' '.join(self.cmd))
            self._finished = subprocess.check_call(self.cmd)
        else:
            lg.info('Pretending to run command: %s', ' '.join(self.cmd))

        return self._finished

    def repr_cmd(self):
        """Return repr of the command.

        :rtype: str"""
        return repr(self.cmd)

    def __hash__(self):
        """Hash of the command.

        :rtype: integer"""
        return freeze.recursive_hash(
            (self.cmd, self._requires, self._provides)
        )

    def __eq__(self, other):
        """Equalitity based on the hash, might collide... hmm"""
        return self.__hash__() == other.__hash__()

    def __repr__(self):
        return "Command<%s requires %s, provides %s>\n" % (
            self.repr_cmd(),
            ", ".join([repr(x) for x in self._requires]),
            ", ".join([repr(x) for x in self._provides]),
        )

    @staticmethod
    def command_list_to_digraph(commands):  # pragma: no cover
        """Generate dot source for a digraph - suitable for generating
        diagrams.

        The requires and provides from the commands build nodes, the commands
        themselves act as connectors.

        :param  commands: The commands to draw a diagram with
        :type   commands: list
        """

        nodes = set()
        edges = set()

        def result_node(type_, name):
            """Get the dot representation of a result node."""
            return (
                '"%s %s" [shape=ellipse]' % (type_, name),
                '"%s %s"'                 % (type_, name),
            )

        def cmd_node(command):
            """Get the dot representation of a command node."""
            return (
                '"%s" [shape=box]' % command.repr_cmd(),
                '"%s"'             % command.repr_cmd(),
            )

        for cmd in commands:
            if cmd is None:
                continue

            cmd_spec, cmd_identifier = cmd_node(cmd)
            nodes.add(cmd_spec)

            for type_, name in cmd._requires:
                spec, identifier = result_node(type_, name)
                nodes.add(spec)
                edges.add((identifier, cmd_identifier))

            for type_, name in cmd._provides:
                spec, identifier = result_node(type_, name)
                nodes.add(spec)
                edges.add((cmd_identifier, identifier))

        template = """
            digraph {
                %s;
                %s;
            }
        """
        return template % (
            ";\n".join(nodes),
            ";\n".join(['%s -> %s' % edge for edge in edges])
        )

    @staticmethod
    def order_commands(commands, has_dependency_cb=lambda x: False):
        """Order the commands according to the dependencies they
        provide/require.

        :param          commands: The commands to order
        :type           commands: list
        :param has_dependency_cb: Optional callback the resolve external
                                  dependencies
        :type  has_dependency_cb: function"""

        commands = set([c for c in commands if c is not None])

        lg.debug('Ordering commands: %s', [
            str(cmd) for cmd in commands
        ])

        have_requirements = collections.defaultdict(lambda: 0)
        required_number   = collections.defaultdict(lambda: 0)
        scheduled  = []

        for cmd in commands:
            for provide in cmd._provides:
                required_number[provide] += 1

        something_changed = True
        while something_changed:
            something_changed = False

            for cmd in commands:
                if cmd in scheduled:
                    continue

                can_schedule = True
                for req in cmd._requires:
                    if have_requirements[req] < required_number[req]:
                        lg.debug(
                            "%s: dependency %s not fulfilled, "
                            "checking aptly state" % (cmd, req)
                        )
                        # No command providing our dependency.. Let's see if
                        # it's already otherwise fulfilled
                        if not has_dependency_cb(req):
                            lg.debug(
                                "%s: dependency %s not "
                                "in aptly state either" % (cmd, req)
                            )
                            can_schedule = False
                            # Break out of the requirements loop, as the
                            # command cannot be scheduled anyway.
                            break

                if can_schedule:
                    lg.debug(
                        "%s: all dependencies fulfilled" % cmd
                    )
                    scheduled.append(cmd)
                    for provide in cmd._provides:
                        have_requirements[provide] += 1

                    something_changed = True

        unresolved = [
            cmd
            for cmd in commands
            if cmd not in scheduled
        ]

        if len(unresolved) > 0:  # pragma: no cover
            raise ValueError('Commands with unresolved deps: %s' % [
                str(cmd) for cmd in unresolved
            ])

        # Just one last verification before we commence
        scheduled_set = set([cmd for cmd in scheduled])
        incoming_set  = set([cmd for cmd in commands])
        assert incoming_set == scheduled_set

        lg.info('Reordered commands: %s', [
            str(cmd) for cmd in scheduled
        ])

        return scheduled


class FunctionCommand(Command):
    """Repesents a function command and is used to resolve dependencies between
    such commands. This command executes the given function. \*args and
    \*\*kwargs are passed through.

    :param func: The function to execute
    :type  func: callable
    """

    def __init__(self, func, *args, **kwargs):
        super(FunctionCommand, self).__init__(None)

        assert hasattr(func, '__call__')
        self.cmd    = func
        self.args   = args
        self.kwargs = kwargs

    def __hash__(self):
        return freeze.recursive_hash(
            (
                id(self.cmd),
                self.args,
                self.kwargs,
                self._requires,
                self._provides
            )
        )

    def execute(self):
        """Execute the command. (Call the function)."""
        if self._finished is not None:  # pragma: no cover
            return self._finished

        if not Command.pretend_mode:
            lg.debug(
                'Running code: %s(args=%s, kwargs=%s)',
                self.cmd.__name__,
                repr(self.args),
                repr(self.kwargs),
            )

            self.cmd(*self.args, **self.kwargs)

            self._finished = True
        else:  # pragma: no cover
            lg.info(
                'Pretending to run code: %s(args=%s, kwargs=%s)',
                self.repr_cmd(),
                repr(self.args),
                repr(self.kwargs),
            )

        return self._finished

    def repr_cmd(self):
        """Return repr of the command.

        :rtype: str"""
        # We need to "id" ourselves here so that multiple commands that call a
        # function with the same name won't be shown as being equal.
        return '%s|%s' % (self.cmd.__name__, id(self))

    def __repr__(self):
        return "FunctionCommand<%s requires %s, provides %s>\n" % (
            self.repr_cmd(),
            ", ".join([repr(x) for x in self._requires]),
            ", ".join([repr(x) for x in self._provides]),
        )


class SystemStateReader(object):
    """Reads the state from aptly and gpg to find out what operations have to
    be performed to reach the state defined in the yml config-file.
    """
    known_dependency_types = (
        'repo', 'snapshot', 'mirror', 'gpg_key'
    )

    def __init__(self):
        self.gpg_keys     = set()
        self.mirrors      = set()
        self.repos        = set()
        self.snapshots    = set()
        self.snapshot_map = {}
        self.publishes    = set()
        self.publish_map  = {}

    def read(self):
        """Reads all available system states."""
        self.read_gpg()
        self.read_repos()
        self.read_mirror()
        self.read_snapshot()
        self.read_snapshot_map()
        self.read_publishes()
        self.read_publish_map()

    def read_gpg(self):
        """Read all trusted keys in gpg."""
        self.gpg_keys = set()
        data, _ = call_output([
            "gpg",
            "--no-default-keyring",
            "--keyring", "trustedkeys.gpg",
            "--list-keys",
            "--with-colons"
        ])
        lg.debug('GPG returned: %s', data)
        for line in data.split("\n"):
            field = line.split(":")
            if field[0] in ("pub", "sub"):
                key = field[4]
                key_short = key[8:]
                self.gpg_keys.add(key)
                self.gpg_keys.add(key_short)

    def read_publish_map(self):
        """Create a publish map. publish -> snapshots"""
        self.publish_map = {}
        data, _ = call_output([
            "aptly", "publish", "list"
        ])

        for publish in self.publishes:
            self.publish_map[publish] = set()
            re_snap = re.compile(
                r"^\s*\*\s+%s/%s " %
                tuple(publish.split(" "))
            )
            for line in data.split("\n"):
                if re_snap.match(line):
                    for snapshot in self.snapshots:
                        if re.match(".*\[%s\]" % snapshot, line):
                            self.publish_map[publish].add(snapshot)
        lg.debug('Joined snapshots and publishes: %s', self.publish_map)

    def read_snapshot_map(self):
        """Create a snapshot map. snapshot -> snapshots. This is also called
        merge-tree."""
        self.snapshot_map = {}
        data, _ = call_output([
            "aptly", "snapshot", "list"
        ])

        re_snap = re.compile(r"^\s*\*\s+\[([\w\d-]+)\]")

        for line in data.split("\n"):
            match = re_snap.match(line)
            if match:
                snapshot_outer = match.group(1)
                if snapshot_outer not in self.snapshot_map:
                    self.snapshot_map[snapshot_outer] = set()

                sources_match = re.match(
                    ".*Merged from sources:[\s']*(.*)'", line)
                if sources_match:
                    sources = re.split(r"[ ,']+", sources_match.group(1))
                    self.snapshot_map[snapshot_outer].update(sources)

        lg.debug(
            'Joined snapshots with self(snapshots): %s',
            self.snapshot_map
        )

    def read_publishes(self):
        """Read all available publishes."""
        self.publishes = set()
        self.read_aptly_list("publish", self.publishes)

    def read_repos(self):
        """Read all available repos."""
        self.repos = set()
        self.read_aptly_list("repo", self.repos)

    def read_mirror(self):
        """Read all available mirrors."""
        self.mirrors = set()
        self.read_aptly_list("mirror", self.mirrors)

    def read_snapshot(self):
        """Read all available snapshots."""
        self.snapshots = set()
        self.read_aptly_list("snapshot", self.snapshots)

    def read_aptly_list(self, type_, list_):
        """Generic method to read lists from aptly.

        :param type_: The type of list to read ie. snapshot
        :type  type_: str
        :param list_: Read into this list
        :param list_: list"""
        data, _ = call_output([
            "aptly", type_, "list", "-raw"
        ])
        lg.debug('Aptly returned %s: %s', type_, data)
        for line in data.split("\n"):
            clean_line = line.strip()
            if clean_line:
                list_.add(clean_line)

    def has_dependency(self, dependency):
        """Check system state dependencies.

        :param dependency: The dependency to check
        :type  dependency: list"""
        type_, name = dependency

        if type_ == 'repo':  # pragma: no cover
            return name in self.repos
        if type_ == 'mirror':  # pragma: no cover
            return name in self.mirrors
        elif type_ == 'snapshot':
            return name in self.snapshots  # pragma: no cover
        elif type_ == 'gpg_key':  # pragma: no cover
            return name in self.gpg_keys  # Not needed ATM
        elif type_ == 'virtual':
            # virtual dependencies can never be resolved by the
            # system state reader - they are used for internal
            # ordering only
            return False
        else:
            raise ValueError(
                "Unknown dependency to resolve: %s" % str(dependency)
            )


state = SystemStateReader()


def main(argv=None):
    """Called by command-line, defines parsers and executes commands.

    :param argv: Arguments usually taken from sys.argv
    :type  argv: list"""
    global _logging_setup
    if not argv:  # pragma: no cover
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Manage aptly')
    parser.add_argument(
        '--config',
        '-c',
        help='Yaml config file defining mirrors and snapshots',
        type=str,
        required=True
    )
    parser.add_argument(
        '--debug',
        '-d',
        help='Enable debug output',
        action='store_true',
    )
    parser.add_argument(
        '--pretend',
        '-p',
        help='Do not do anything, just print out what WOULD be done',
        action='store_true',
    )
    subparsers = parser.add_subparsers()
    mirror_parser = subparsers.add_parser(
        'mirror',
        help='manage aptly mirrors'
    )
    mirror_parser.set_defaults(func=mirror)
    mirror_parser.add_argument(
        'task',
        type=str,
        choices=['create', 'update']
    )
    mirror_parser.add_argument(
        'mirror_name',
        type=str,
        nargs='?',
        default='all'
    )
    snap_parser = subparsers.add_parser(
        'snapshot',
        help='manage aptly snapshots'
    )
    snap_parser.set_defaults(func=snapshot)
    snap_parser.add_argument('task', type=str, choices=['create', 'update'])
    snap_parser.add_argument(
        'snapshot_name',
        type=str,
        nargs='?',
        default='all'
    )
    publish_parser = subparsers.add_parser(
        'publish',
        help='manage aptly publish endpoints'
    )
    publish_parser.set_defaults(func=publish)
    publish_parser.add_argument('task', type=str, choices=['create', 'update'])
    publish_parser.add_argument(
        'publish_name',
        type=str,
        nargs='?',
        default='all'
    )
    repo_parser = subparsers.add_parser(
        'repo',
        help='manage aptly repositories'
    )
    repo_parser.set_defaults(func=repo)
    repo_parser.add_argument('task', type=str, choices=['create'])
    repo_parser.add_argument(
        'repo_name',
        type=str,
        nargs='?',
        default='all'
    )

    args = parser.parse_args(argv)
    root = logging.getLogger()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    if not _logging_setup:  # noqa
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        root.addHandler(handler)
        handler.setLevel(logging.CRITICAL)
        if args.debug:
            root.setLevel(logging.DEBUG)
            handler.setLevel(logging.DEBUG)
    if args.pretend:
        Command.pretend_mode = True
    else:
        Command.pretend_mode = False

        _logging_setup = True  # noqa
    lg.debug("Args: %s", vars(args))

    with codecs.open(args.config, 'r', encoding="UTF-8") as cfgfile:
        cfg = yaml.load(cfgfile)
    state.read()

    # run function for selected subparser
    args.func(cfg, args)

day_of_week_map = {
    'mon': 1,
    'tue': 2,
    'wed': 3,
    'thu': 4,
    'fri': 5,
    'sat': 6,
    'sun': 7,
}


def expand_timestamped_name(name, timestamp_config, date=None):
    """Expand a timestamped name using round_timestamp.

    :param timestamp_config: Contains the recurrence specification for the
                             timestamp. See :func:`round_timestamp`
    :type  timestamp_config: dict
    :param             date: The date to expand the timestamp with.
    :type              date: :py:class:`datetime.datetime`"""
    if '%T' not in name:
        return name
    timestamp = round_timestamp(timestamp_config, date)
    return name.replace('%T', timestamp.strftime('%Y%m%dT%H%MZ'))


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
    timestamp_info = timestamp_config.get('timestamp', timestamp_config)
    config_time    = timestamp_info.get('time', 'FAIL')
    if config_time == 'FAIL':  # pragma: no cover
        raise ValueError(
            "Timestamp config has no valid time entry: %s" %
            str(timestamp_config)
        )

    config_repeat_weekly = timestamp_info.get('repeat-weekly', None)

    hour, minute = [int(x) for x in config_time.split(':')][:2]

    if date is None:
        date = datetime.datetime.now()

    if config_repeat_weekly is not None:
        day_of_week = day_of_week_map.get(config_repeat_weekly.lower())

        timestamp = date_round_weekly(
            date,
            day_of_week,
            datetime.time(hour=hour, minute=minute)
        )
    else:
        timestamp = date_round_daily(
            date,
            datetime.time(hour=hour, minute=minute)
        )
    return timestamp


def unit_or_list_to_list(thingy):
    """Ensures that a yml entry is always a list. Used to allow lists and
    single units in the yml file.

    :param thingy: The data to ensure it is a list
    :type  thingy: list, tuple or other"""
    if isinstance(thingy, list) or isinstance(thingy, tuple):
        return list(thingy)
    else:
        return [thingy]


def publish_cmd_create(cfg,
                       publish_name,
                       publish_config,
                       ignore_existing=False):
    """Creates a publish command with its dependencies to be ordered and
    executed later.

    :param            cfg: pyaptly config
    :type             cfg: dict
    :param   publish_name: Name of the publish to create
    :type    publish_name: str
    :param publish_config: Configuration of the publish from the yml file.
    :type  publish_config: dict"""
    publish_fullname = '%s %s' % (publish_name, publish_config['distribution'])
    if publish_fullname in state.publishes and not ignore_existing:
        # Nothing to do, publish already created
        return

    publish_cmd   = ['aptly', 'publish']
    options       = []
    source_args   = []
    endpoint_args = [
        publish_name
    ]

    has_source = False
    num_sources = 0

    for conf, conf_value in publish_config.items():

        if conf == 'skip-contents':
            if conf_value:
                options.append('-skip-contents=true')
        elif conf == 'architectures':  # pragma: no cover
            options.append(
                '-architectures=%s' %
                ','.join(unit_or_list_to_list(conf_value))
            )
        elif conf == 'components':
            components = unit_or_list_to_list(conf_value)
            options.append(
                '-component=%s' % ','.join(components)
            )
        elif conf == 'label':  # pragma: no cover
            options.append(
                '-label=%s' % conf_value
            )
        elif conf == 'origin':  # pragma: no cover
            options.append('-origin=%s' % conf_value)

        elif conf == 'distribution':
            options.append('-distribution=%s' % conf_value)

        elif conf == 'gpg-key':
            options.append('-gpg-key=%s' % conf_value)
        elif conf == 'automatic-update':
            # Ignored here
            pass
        elif conf == 'snapshots':
            if has_source:  # pragma: no cover
                raise ValueError(
                    "Multiple sources for publish %s %s" % (
                        publish_name,
                        publish_config
                    )
                )
            has_source = True
            snapshots = unit_or_list_to_list(conf_value)
            source_args.append('snapshot')
            source_args.extend([
                snapshot_spec_to_name(cfg, conf_value)
                for conf_value
                in snapshots
            ])

            num_sources = len(snapshots)

        elif conf == 'repo':
            if has_source:  # pragma: no cover
                raise ValueError(
                    "Multiple sources for publish %s %s" % (
                        publish_name,
                        publish_config
                    )
                )
            has_source = True
            source_args = [
                'repo',
                conf_value
            ]
            num_sources = 1
        elif conf == 'publish':
            if has_source:  # pragma: no cover
                raise ValueError(
                    "Multiple sources for publish %s %s" % (
                        publish_name,
                        publish_config
                    )
                )
            has_source = True
            conf_value = " ".join(conf_value.split("/"))
            source_args.append('snapshot')
            try:
                sources = state.publish_map[conf_value]
            except KeyError:
                lg.critical((
                    "Creating %s has been deferred, please call publish "
                    "create again"
                ) % publish_name)
                return
            source_args.extend(sources)
            num_sources = len(sources)
        else:  # pragma: no cover
            raise ValueError(
                "Don't know how to handle publish config entry %s in %s" % (
                    conf,
                    publish_name,
                )
            )
    assert has_source
    assert len(components) == num_sources

    return Command(publish_cmd + options + source_args + endpoint_args)


def clone_snapshot(origin, destination):
    """Creates a clone snapshot command with dependencies to be ordered and
    executed later.

    :param      origin: The snapshot to clone
    :type       origin: str
    :param destination: The new name of the snapshot
    :type  destination: str"""
    cmd = Command([
        'aptly',
        'snapshot',
        'merge',
        destination,
        origin
    ])
    cmd.provide('snapshot', destination)
    cmd.require('snapshot', origin)
    return cmd


def publish_cmd_update(cfg,
                       publish_name,
                       publish_config,
                       ignore_existing=False):
    """Creates a publish command with its dependencies to be ordered and
    executed later.

    :param            cfg: pyaptly config
    :type             cfg: dict
    :param   publish_name: Name of the publish to update
    :type    publish_name: str
    :param publish_config: Configuration of the publish from the yml file.
    :type  publish_config: dict"""

    publish_cmd = ['aptly', 'publish']
    options     = []
    args        = [publish_config['distribution'], publish_name]

    if 'skip-contents' in publish_config and publish_config['skip-contents']:
        options.append('-skip-contents=true')

    if 'repo' in publish_config:
        publish_cmd.append('update')
        return Command(publish_cmd + options + args)

    publish_fullname = '%s %s' % (publish_name, publish_config['distribution'])
    current_snapshots = state.publish_map[publish_fullname]
    if 'snapshots' in publish_config:
        snapshots_config  = publish_config['snapshots']
        new_snapshots     = [
            snapshot_spec_to_name(cfg, snap)
            for snap
            in snapshots_config
        ]
    elif 'publish' in publish_config:
        conf_value       = publish_config['publish']
        snapshots_config = []
        ref_publish_name, distribution     = conf_value.split(" ")
        for publish in cfg['publish'][ref_publish_name]:
            if publish['distribution'] == distribution:
                snapshots_config.extend(publish['snapshots'])
                break
        new_snapshots = list(state.publish_map[conf_value])
    else:  # pragma: no cover
        raise ValueError(
            "No snapshot references configured in publish %s" % publish_name
        )

    if set(new_snapshots) == set(current_snapshots) and not ignore_existing:
        # Already pointing to the newest snapshot, nothing to do
        return
    components = unit_or_list_to_list(publish_config['components'])

    for snap in snapshots_config:
        # snap may be a plain name or a dict..
        if hasattr(snap, 'items'):
            # Dict mode - only here can we even have an archive option
            archive = snap.get('archive-on-update', None)

            if archive:
                # Replace any timestamp placeholder with the current
                # date/time.  Note that this is NOT rounded, as we want to
                # know exactly when the archival happened.
                archive = archive.replace(
                    '%T',
                    format_timestamp(datetime.datetime.now())
                )
                if archive in state.snapshots:  # pragma: no cover
                    continue
                prefix_to_search = re.sub('%T$', '', snap['name'])

                current_snapshot = [
                    snap_name
                    for snap_name
                    in sorted(current_snapshots, key=lambda x: -len(x))
                    if snap_name.startswith(prefix_to_search)
                ][0]

                clone_snapshot(current_snapshot, archive).execute()

    publish_cmd.append('switch')
    options.append('-component=%s' % ','.join(components))

    if 'skip-contents' in publish_config and publish_config['skip-contents']:
        options.append('-skip-contents=true')

    return Command(publish_cmd + options + args + new_snapshots)


def repo_cmd_create(cfg, repo_name, repo_config):
    """Create a repo create command to be ordered and executed later.

    :param         cfg: pyaptly config
    :type          cfg: dict
    :param   repo_name: Name of the repo to create
    :type    repo_name: str
    :param repo_config: Configuration of the repo from the yml file.
    :type  repo_config: dict"""

    if repo_name in state.repos:  # pragma: no cover
        # Nothing to do, repo already created
        return

    repo_cmd      = ['aptly', 'repo']
    options       = []
    endpoint_args = ['create', repo_name]

    for conf, conf_value in repo_config.items():
        if conf == 'architectures':
            options.append(
                '-architectures=%s' %
                ','.join(unit_or_list_to_list(conf_value))
            )
        elif conf == 'component':
            components = unit_or_list_to_list(conf_value)
            options.append(
                '-component=%s' % ','.join(components)
            )
        elif conf == 'comment':  # pragma: no cover
            options.append(
                '-comment=%s' % conf_value
            )
        elif conf == 'distribution':
            options.append('-distribution=%s' % conf_value)
        else:  # pragma: no cover
            raise ValueError(
                "Don't know how to handle repo config entry %s in %s" % (
                    conf,
                    repo_name,
                )
            )

    return Command(repo_cmd + options + endpoint_args)


def repo(cfg, args):
    """Creates repository commands, orders and executes them.

    :param  cfg: The configuration yml as dict
    :type   cfg: dict
    :param args: The command-line arguments read with :py:mod:`argparse`
    :type  args: namespace"""
    lg.debug("Repositories to create: %s", cfg['repo'])

    repo_cmds = {
        'create': repo_cmd_create,
    }

    cmd_repo = repo_cmds[args.task]

    if args.repo_name == "all":
        commands = [
            cmd_repo(cfg, repo_name, repo_conf)
            for repo_name, repo_conf in cfg['repo'].items()
        ]

        for cmd in Command.order_commands(commands, state.has_dependency):
            cmd.execute()

    else:
        if args.repo_name in cfg['repo']:
            commands = [
                cmd_repo(
                    cfg,
                    args.repo_name,
                    cfg['repo'][args.repo_name]
                )
            ]
            for cmd in Command.order_commands(commands, state.has_dependency):
                cmd.execute()
        else:
            raise ValueError(
                "Requested publish is not defined in config file: %s" % (
                    args.repo_name
                )
            )


def publish(cfg, args):
    """Creates publish commands, orders and executes them.

    :param  cfg: The configuration yml as dict
    :type   cfg: dict
    :param args: The command-line arguments read with :py:mod:`argparse`
    :type  args: namespace"""
    lg.debug("Publishes to create / update: %s", cfg['publish'])

    # aptly publish snapshot -components ... -architectures ... -distribution
    # ... -origin Ubuntu trusty-stable ubuntu/stable

    publish_cmds = {
        'create': publish_cmd_create,
        'update': publish_cmd_update,
    }

    cmd_publish = publish_cmds[args.task]

    if args.publish_name == "all":
        commands = [
            cmd_publish(cfg, publish_name, publish_conf_entry)
            for publish_name, publish_conf in cfg['publish'].items()
            for publish_conf_entry in publish_conf
            if publish_conf_entry.get('automatic-update', 'false') is True
        ]

        for cmd in Command.order_commands(commands, state.has_dependency):
            cmd.execute()

    else:
        if args.publish_name in cfg['publish']:
            commands = [
                cmd_publish(
                    cfg,
                    args.publish_name,
                    publish_conf_entry
                )
                for publish_conf_entry
                in cfg['publish'][args.publish_name]
            ]
            for cmd in Command.order_commands(commands, state.has_dependency):
                cmd.execute()
        else:
            raise ValueError(
                "Requested publish is not defined in config file: %s" % (
                    args.publish_name
                )
            )


def snapshot(cfg, args):
    """Creates snapshot commands, orders and executes them.

    :param  cfg: The configuration yml as dict
    :type   cfg: dict
    :param args: The command-line arguments read with :py:mod:`argparse`
    :type  args: namespace"""
    lg.debug("Snapshots to create: %s", cfg['snapshot'].keys())

    snapshot_cmds = {
        'create': cmd_snapshot_create,
        'update': cmd_snapshot_update,
    }

    cmd_snapshot = snapshot_cmds[args.task]

    if args.snapshot_name == "all":
        commands = [
            cmd
            for snapshot_name, snapshot_config in cfg['snapshot'].items()
            for cmd in cmd_snapshot(cfg, snapshot_name, snapshot_config)
        ]

        if args.debug:  # pragma: no cover
            dot_file = "/tmp/commands.dot"
            with codecs.open(dot_file, 'w', "UTF-8") as fh_dot:
                fh_dot.write(Command.command_list_to_digraph(commands))
            lg.info('Wrote command dependency tree graph to %s', dot_file)

        if len(commands) > 0:
            for cmd in Command.order_commands(commands,
                                              state.has_dependency):
                cmd.execute()

    else:
        if args.snapshot_name in cfg['snapshot']:
            commands = cmd_snapshot(
                cfg,
                args.snapshot_name,
                cfg['snapshot'][args.snapshot_name]
            )

            if len(commands) > 0:
                for cmd in Command.order_commands(commands,
                                                  state.has_dependency):
                    cmd.execute()

        else:
            raise ValueError(
                "Requested snapshot is not defined in config file: %s" % (
                    args.snapshot_name
                )
            )


def format_timestamp(timestamp):
    """Wrapper for strftime, to ensure we're all using the same format.

    :param timestamp: The timestamp to format
    :type  timestamp: :py:class:`datetime.datetime`"""
    return timestamp.strftime('%Y%m%dT%H%MZ')


back_reference_map = {
    "current":  0,
    "previous": 1,
}


def snapshot_spec_to_name(cfg, snapshot):
    """Converts a given snapshot short spec to a name.

    A short spec is a value that may either be a string or a dict.

    If it's a string, everything is fine and we just use that as
    a snapshot name.

    However if it's a dict, we assume it has the following keys:

     * name: template for the snapshot
     * timestamp: information on how to generate the timestamp.

    For further information regarding the timestamp's data structure,
    consult the documentation of expand_timestamped_name().

    :param      cfg: Complete yaml config
    :type       cfg: dict
    :param snapshot: Config of the snapshot
    :type  snapshot: dict
    """
    delta = datetime.timedelta(seconds=1)
    if hasattr(snapshot, 'items'):
        name      = snapshot['name']
        if 'timestamp' not in snapshot:
            return name

        ts        = snapshot['timestamp']
        back_ref  = back_reference_map.get(ts)
        if back_ref is None:
            back_ref = int(ts)
        reference = cfg['snapshot'][name]

        timestamp = datetime.datetime.now()
        for _ in range(back_ref + 1):
            timestamp = round_timestamp(reference["timestamp"], timestamp)
            timestamp -= delta

        timestamp += delta
        return name.replace('%T', format_timestamp(timestamp))
    else:  # pragma: no cover
        return snapshot


def dependents_of_snapshot(snapshot_name):
    """Yield a flat list of dependents from the current state.

    :rtype: generator"""
    for dependent in state.snapshot_map.get(snapshot_name, []):
        yield dependent
        for sub in dependents_of_snapshot(dependent):  # pragma: no cover
            yield dependent


def rotate_snapshot(cfg, snapshot_name):
    """Creates a command to rotate a snapshot in order to be able to update a
    current publish.

    :param           cfg: pyaptly config
    :type            cfg: dict
    :param snapshot_name: the snapshot to rotate
    :type  snapshot_name: str"""
    rotated_name = cfg['snapshot'][snapshot_name].get(
        'rotate_via', '%s-rotated-%s' % (
            snapshot_name,
            format_timestamp(datetime.datetime.now())
        )
    )

    # First, verify that our snapshot environment is in a sane state.
    # Fixing the environment is not currently our task.

    if rotated_name in state.snapshots:  # pragma: no cover
        raise Exception(
            "Cannot update snapshot %s - rotated name %s already exists" % (
                snapshot_name, rotated_name
            )
        )

    cmd = Command([
        'aptly', 'snapshot', 'rename', snapshot_name, rotated_name
    ])

    cmd.provide('virtual', rotated_name)
    return cmd


def cmd_snapshot_update(cfg, snapshot_name, snapshot_config):
    """Create commands to update all rotating snapshots.

    :param             cfg: pyaptly config
    :type              cfg: dict
    :param   snapshot_name: Name of the snapshot to update/rotate
    :type    snapshot_name: str
    :param snapshot_config: Configuration of the snapshot from the yml file.
    :type  snapshot_config: dict"""

    # To update a snapshot, we need to do roughly the following steps:
    # 1) Rename the current snapshot and all snapshots that depend on it
    # 2) Create new version of the snapshot and all snapshots that depend on it
    # 3) Recreate all renamed snapshots
    # 4) Update / switch-over publishes
    # 5) Remove the rotated temporary snapshots

    if '%T' in snapshot_name:  # pragma: no cover
        # Timestamped snapshots are never rotated by design.
        return []

    affected_snapshots = [snapshot_name]
    affected_snapshots.extend(list(dependents_of_snapshot(snapshot_name)))

    # TODO: rotated snapshots should be identified by configuration option, not
    # just by "not being timestamped

    rename_cmds = [
        rotate_snapshot(cfg, snap)
        for snap
        in affected_snapshots
    ]

    # The "intermediate" command causes the state reader to refresh.  At the
    # same time, it provides a collection point for dependency handling.
    intermediate = FunctionCommand(state.read)
    intermediate.provide('virtual', 'all-snapshots-rotated')

    for cmd in rename_cmds:
        # Ensure that our "intermediate" pseudo command comes after all
        # the rename commands, by ensuring it depends on all their "virtual"
        # provided items.
        cmd_vprovides = [
            provide
            for ptype, provide
            in cmd.get_provides()
            if ptype == 'virtual'
        ]
        for provide in cmd_vprovides:
            intermediate.require('virtual', provide)

    # Same as before - create a focal point to "collect" dependencies
    # after the snapshots have been rebuilt. Also reload state once again
    intermediate2 = FunctionCommand(state.read)
    intermediate2.provide('virtual', 'all-snapshots-rebuilt')

    create_cmds = []
    for snap in affected_snapshots:

        # Well.. there's normally just one, but since we need interface
        # consistency, cmd_snapshot_create() returns a list. And since it
        # returns a list, we may just as well future-proof it and loop instead
        # of assuming it's going to be a single entry (and fail horribly if
        # this assumption changes in the future).
        for create_cmd in cmd_snapshot_create(cfg,
                                              snapshot_name,
                                              cfg['snapshot'][snapshot_name],
                                              ignore_existing=True):

            # enforce cmd to run after the refresh, and thus also
            # after all the renames
            create_cmd.require('virtual', 'all-snapshots-rotated')

            # Evil hack - we must do the dependencies ourselves, to avoid
            # getting a circular graph
            create_cmd._requires = set([
                (type_, req)
                for type_, req
                in create_cmd._requires
                if type_ != 'snapshot'
            ])

            create_cmd.provide('virtual', 'readyness-for-%s' % snapshot_name)
            for follower in dependents_of_snapshot(snapshot_name):
                create_cmd.require('virtual', 'readyness-for-%s' % follower)

            # "Focal point" - make intermediate2 run after all the commands
            # that re-create the snapshots
            create_cmd.provide('virtual', 'rebuilt-%s' % snapshot_name)
            intermediate2.require('virtual', 'rebuilt-%s' % snapshot_name)

            create_cmds.append(create_cmd)

    # At this point, snapshots have been renamed, then recreated.
    # After each of the steps, the system state has been re-read.
    # So now, we're left with updating the publishes.

    def is_publish_affected(name, publish):
        if "%s %s" % (
                name,
                publish['distribution']
        ) in state.publishes:
            try:
                for snap in publish['snapshots']:
                    snap_name = snapshot_spec_to_name(cfg, snap)
                    if snap_name in affected_snapshots:
                        return True
            except KeyError:  # pragma: no cover
                lg.debug((
                    "Publish endpoint %s is not affected because it has no "
                    "snapshots defined"
                ) % name)
                return False
        return False

    if 'publish' in cfg:
        all_publish_commands = [
            publish_cmd_update(cfg,
                               publish_name,
                               publish_conf_entry,
                               ignore_existing=True)
            for publish_name, publish_conf in cfg['publish'].items()
            for publish_conf_entry in publish_conf
            if publish_conf_entry.get('automatic-update', 'false') is True
            if is_publish_affected(publish_name, publish_conf_entry)
        ]
    else:
        all_publish_commands = []

    republish_cmds = [
        c
        for c
        in all_publish_commands
        if c
    ]

    # Ensure that the republish commands run AFTER the snapshots are rebuilt
    for cmd in republish_cmds:
        cmd.require('virtual', 'all-snapshots-rebuilt')

    # TODO:
    # - We need to cleanup all the rotated snapshots after the publishes are
    #   rebuilt
    # - Filter publishes, so only the non-timestamped publishes are rebuilt

    return (
        rename_cmds +
        create_cmds +
        republish_cmds +
        [intermediate, intermediate2]
    )


def cmd_snapshot_create(cfg,
                        snapshot_name,
                        snapshot_config,
                        ignore_existing=False):
    """Create a snapshot create command to be ordered and executed later.

    :param             cfg: pyaptly config
    :type              cfg: dict
    :param   snapshot_name: Name of the snapshot to create
    :type    snapshot_name: str
    :param snapshot_config: Configuration of the snapshot from the yml file.
    :type  snapshot_config: dict
    :param ignore_existing: Optional, defaults to False. If set to True, still
                            return a command object even if the requested
                            snapshot already exists
    :type  ignore_existing: dict

    :rtype: Command
    """

    # TODO: extract possible timestamp component
    # and generate *actual* snapshot name

    snapshot_name = expand_timestamped_name(
        snapshot_name, snapshot_config
    )

    if snapshot_name in state.snapshots and not ignore_existing:
        return []

    default_aptly_cmd = ['aptly', 'snapshot', 'create']
    default_aptly_cmd.append(snapshot_name)
    default_aptly_cmd.append('from')

    if 'mirror' in snapshot_config:
        cmd = Command(
            default_aptly_cmd + ['mirror', snapshot_config['mirror']]
        )
        cmd.provide('snapshot', snapshot_name)
        cmd.require('mirror', snapshot_config['mirror'])
        return [cmd]

    elif 'repo' in snapshot_config:
        cmd = Command(default_aptly_cmd + ['repo', snapshot_config['repo']])
        cmd.provide('snapshot', snapshot_name)
        cmd.require('repo',     snapshot_config['repo'])
        return [cmd]

    elif 'filter' in snapshot_config:
        cmd = Command([
            'aptly',
            'snapshot',
            'filter',
            snapshot_spec_to_name(cfg, snapshot_config['filter']['source']),
            snapshot_name,
            snapshot_config['filter']['query'],
        ])
        cmd.provide('snapshot', snapshot_name)
        cmd.require(
            'snapshot',
            snapshot_spec_to_name(cfg, snapshot_config['filter']['source'])
        )
        return [cmd]

    elif 'merge' in snapshot_config:
        cmd = Command([
            'aptly',
            'snapshot',
            'merge',
            snapshot_name,
        ])
        cmd.provide('snapshot', snapshot_name)

        for source in snapshot_config['merge']:
            source_name = snapshot_spec_to_name(cfg, source)
            cmd.append(source_name)
            cmd.require('snapshot', source_name)

        return [cmd]

    else:  # pragma: no cover
        raise ValueError(
            "Don't know how to handle snapshot config" % (
                snapshot_config
            )
        )


def mirror(cfg, args):
    """Creates mirror commands, orders and executes them.

    :param  cfg: The configuration yml as dict
    :type   cfg: dict
    :param args: The command-line arguments read with :py:mod:`argparse`
    :type  args: namespace"""
    lg.debug("Mirrors to create: %s", cfg['mirror'])

    mirror_cmds = {
        'create': cmd_mirror_create,
        'update': cmd_mirror_update,
    }

    cmd_mirror = mirror_cmds[args.task]

    if args.mirror_name == "all":
        for mirror_name, mirror_config in cfg['mirror'].items():
            cmd_mirror(cfg, mirror_name, mirror_config)
    else:
        if args.mirror_name in cfg['mirror']:
            cmd_mirror(
                cfg,
                args.mirror_name,
                cfg['mirror'][args.mirror_name]
            )
        else:
            raise ValueError(
                "Requested mirror is not defined in config file: %s" % (
                    args.mirror_name
                )
            )


def add_gpg_keys(mirror_config):
    """Uses the gpg command-line to download and add gpg keys needed to create
    mirrors.

    :param  mirror_config: The configuration yml as dict
    :type   mirror_config: dict
    """
    keys_urls = {}
    if 'gpg-keys' in mirror_config:
        keys = unit_or_list_to_list(mirror_config['gpg-keys'])
        if 'gpg-urls' in mirror_config:
            urls = unit_or_list_to_list(mirror_config['gpg-urls'])
            urls_len = len(urls)
            for x in range(len(keys)):
                if x < urls_len:
                    url = urls[x]
                else:  # pragma: no cover
                    url = None
                keys_urls[keys[x]] = url
        else:
            for key in keys:
                keys_urls[key] = None

    for key in keys_urls.keys():
        if key in state.gpg_keys:
            continue
        try:
            key_command = [
                "gpg",
                "--no-default-keyring",
                "--keyring",
                "trustedkeys.gpg",
                "--keyserver",
                "pool.sks-keyservers.net",
                "--recv-keys",
                key
            ]
            lg.debug("Adding gpg key with call: %s", key_command)
            subprocess.check_call(key_command)
        except subprocess.CalledProcessError:  # pragma: no cover
            url = keys_urls[key]
            if url:
                key_command = (
                    "wget -q -O - %s | "
                    "gpg --no-default-keyring "
                    "--keyring trustedkeys.gpg --import"
                ) % url
                subprocess.check_call(['bash', '-c', key_command])
            else:
                raise
    state.read_gpg()


def cmd_mirror_create(cfg, mirror_name, mirror_config):
    """Create a mirror create command to be ordered and executed later.

    :param           cfg: The configuration yml as dict
    :type            cfg: dict
    :param   mirror_name: Name of the mirror to create
    :type    mirror_name: str
    :param mirror_config: Configuration of the snapshot from the yml file.
    :type  mirror_config: dict"""

    if mirror_name in state.mirrors:  # pragma: no cover
        return

    add_gpg_keys(mirror_config)
    aptly_cmd = ['aptly', 'mirror', 'create']

    if 'sources' in mirror_config and mirror_config['sources']:
        aptly_cmd.append('-with-sources')
    else:
        aptly_cmd.append('-with-sources=false')

    if 'udeb' in mirror_config and mirror_config['udeb']:
        aptly_cmd.append('-with-udebs')

    if 'architectures' in mirror_config:
        aptly_cmd.append('-architectures={0}'.format(
            ','.join(unit_or_list_to_list(mirror_config['architectures']))
        ))

    aptly_cmd.append(mirror_name)
    aptly_cmd.append(mirror_config['archive'])
    aptly_cmd.append(mirror_config['distribution'])
    aptly_cmd.extend(unit_or_list_to_list(mirror_config['components']))

    lg.debug('Running command: %s', ' '.join(aptly_cmd))
    subprocess.check_call(aptly_cmd)


def cmd_mirror_update(cfg, mirror_name, mirror_config):
    """Create a mirror update command to be ordered and executed later.

    :param           cfg: pyaptly config
    :type            cfg: dict
    :param   mirror_name: Name of the mirror to create
    :type    mirror_name: str
    :param mirror_config: Configuration of the snapshot from the yml file.
    :type  mirror_config: dict"""
    if mirror_name not in state.mirrors:  # pragma: no cover
        raise Exception("Mirror not created yet")
    add_gpg_keys(mirror_config)
    aptly_cmd = ['aptly', 'mirror', 'update']
    aptly_cmd.append(mirror_name)
    lg.debug('Running command: %s', ' '.join(aptly_cmd))
    subprocess.check_call(aptly_cmd)

if __name__ == '__main__':  # pragma: no cover
    main()
