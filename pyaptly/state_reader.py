"""The state reader helps to find the delta between current and target state."""

import logging
import re

from . import util

lg = logging.getLogger(__name__)


class SystemStateReader(object):
    """
    Read the state from aptly and gpg.

    To find out what operations have to be performed to reach the state defined
    in the toml config-file.
    """

    known_dependency_types = ("repo", "snapshot", "mirror", "gpg_key")

    def __init__(self):
        """
        Initialize the SystemStateReader.

        With empty sets and dictionaries for tracking GPG keys, mirrors,
        repositories, snapshots, and publishes, as well as mappings for
        snapshots and publishes.
        """
        self.gpg_keys = set()
        self.mirrors = set()
        self.repos = set()
        self.snapshots = set()
        self.snapshot_map = {}
        self.publishes = set()
        self.publish_map = {}

    def _extract_sources(self, data):
        """
        Extract sources from `data`.

        `data` needs to be in the following format:

        Name: test-snap
        Description: some description
        Sources:
          test-snap-base [snapshot]
        """
        entered_sources = False
        sources = []
        for line in data.split("\n"):
            # source line need to start with two spaces
            if entered_sources and line[0:2] != "  ":
                break

            if entered_sources:
                sources.append(line)

            if line == "Sources:":
                entered_sources = True

        return sources

    def read(self):
        """
        Read all available system states.

        This method sequentially reads the current system states for GPG keys,
        repositories, mirrors, snapshots, snapshot mappings, publishes, and
        publish mappings by invoking the respective read methods for each
        entity.
        """
        self.read_gpg()
        self.read_repos()
        self.read_mirror()
        self.read_snapshot()
        self.read_snapshot_map()
        self.read_publishes()
        self.read_publish_map()

    def read_gpg(self):
        """
        Read all trusted keys in gpg.

        This method populates 'self.gpg_keys' with the set of all trusted GPG
        keys found.
        """
        self.gpg_keys = set()
        cmd = [
            "gpg",
            "--no-default-keyring",
            "--keyring",
            "trustedkeys.gpg",
            "--list-keys",
            "--with-colons",
        ]
        result = util.run_command(cmd, stdout=util.PIPE, check=True)
        for line in result.stdout.split("\n"):
            field = line.split(":")
            if field[0] in ("pub", "sub"):
                key = field[4]
                key_short = key[8:]
                self.gpg_keys.add(key)
                self.gpg_keys.add(key_short)

    def read_publish_map(self):
        """
        Create a mapping of publishes to snapshots.

        This method constructs a dictionary where each key is a publish entity,
        and its value is a set of snapshots associated with that publish. This
        mapping is stored in 'self.publish_map'.
        """
        self.publish_map = {}
        # match example:  main: test-snapshot [snapshot]
        re_snap = re.compile(r"\s+[\w\d-]+\:\s([\w\d-]+)\s\[snapshot\]")
        for publish in self.publishes:
            prefix, dist = publish.split(" ")
            cmd = ["aptly", "publish", "show", dist, prefix]
            result = util.run_command(cmd, stdout=util.PIPE, check=True)
            sources = self._extract_sources(result.stdout)
            matches = [re_snap.match(source) for source in sources]
            snapshots = [match.group(1) for match in matches if match]
            self.publish_map[publish] = set(snapshots)

        lg.debug("Joined snapshots and publishes: %s", self.publish_map)

    def read_snapshot_map(self):
        """
        Create a mapping of snapshots to their source snapshots.

        This method populates 'self.snapshot_map' with a mapping where each key
        is a snapshot and its value is a set of snapshots that are sources of
        the given snapshot.
        """
        self.snapshot_map = {}
        # match example:  test-snapshot [snapshot]
        re_snap = re.compile(r"\s+([\w\d-]+)\s\[snapshot\]")
        for snapshot_outer in self.snapshots:
            cmd = ["aptly", "snapshot", "show", snapshot_outer]

            result = util.run_command(cmd, stdout=util.PIPE, check=True)
            sources = self._extract_sources(result.stdout)
            matches = [re_snap.match(source) for source in sources]
            snapshots = [match.group(1) for match in matches if match]
            self.snapshot_map[snapshot_outer] = set(snapshots)

        lg.debug("Joined snapshots with self(snapshots): %s", self.snapshot_map)

    def read_publishes(self):
        """Read all available publishes and store them in 'self.publishes'."""
        self.publishes = set()
        self.read_aptly_list("publish", self.publishes)

    def read_repos(self):
        """Read all available repos and store them in 'self.repos'."""
        self.repos = set()
        self.read_aptly_list("repo", self.repos)

    def read_mirror(self):
        """Read all available mirrors and store them in 'self.mirrors'."""
        self.mirrors = set()
        self.read_aptly_list("mirror", self.mirrors)

    def read_snapshot(self):
        """Read all available snapshots and store them in 'self.snapshots'."""
        self.snapshots = set()
        self.read_aptly_list("snapshot", self.snapshots)

    def read_aptly_list(self, type_, list_):
        """
        Read lists from aptly and populate `list_` with the results.

        The type of list to read, such as 'snapshot', is specified by `type_`.
        The results are added to the set provided in `list_`.
        """
        cmd = ["aptly", type_, "list", "-raw"]
        result = util.run_command(cmd, stdout=util.PIPE, check=True)
        for line in result.stdout.split("\n"):
            clean_line = line.strip()
            if clean_line:
                list_.add(clean_line)

    def has_dependency(self, dependency):
        """
        Check system state dependencies.

        Determines if the specified `dependency` exists within the system's
        current state. The `dependency` should be a list where the first element
        is the type of dependency (e.g., 'repo', 'mirror', 'snapshot',
        'gpg_key', 'virtual') and the second element is the name of the
        dependency.
        """
        type_, name = dependency

        if type_ == "repo":  # pragma: no cover
            return name in self.repos
        if type_ == "mirror":  # pragma: no cover
            return name in self.mirrors
        elif type_ == "snapshot":
            return name in self.snapshots  # pragma: no cover
        elif type_ == "gpg_key":  # pragma: no cover
            return name in self.gpg_keys  # Not needed ATM
        elif type_ == "virtual":
            # virtual dependencies can never be resolved by the
            # system state reader - they are used for internal
            # ordering only
            return False
        else:
            raise ValueError("Unknown dependency to resolve: %s" % str(dependency))


_state_reader: SystemStateReader | None = None


def state_reader():
    """
    Provides a singleton instance of `SystemStateReader`.

    This function ensures that only one instance of `SystemStateReader` is
    created and returned upon each call, implementing the singleton pattern.
    """
    global _state_reader
    if not _state_reader:
        _state_reader = SystemStateReader()
    return _state_reader
