"""The state reader helps to find the delta between current and target state."""

import logging
import re

from . import util

lg = logging.getLogger(__name__)


class SystemStateReader(object):
    """Reads the state from aptly and gpg.

    To find out what operations have to be performed to reach the state defined
    in the toml config-file.
    """

    known_dependency_types = ("repo", "snapshot", "mirror", "gpg_key")

    def _extract_sources(self, data):
        """Extract sources from data.

        Data needs to be in following format:
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

    def gpg_keys(self):
        """Read all trusted keys in gp and cache in lru_cache."""
        gpg_keys = set()
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
                gpg_keys.add(key)
                gpg_keys.add(key_short)
        return gpg_keys

    def publish_map(self):
        publish_map = {}
        re_snap = re.compile(r"\s+[\w\d-]+\:\s([\w\d-]+)\s\[snapshot\]")
        for publish in self.publishes():
            prefix, dist = publish.split(" ")
            cmd = ["aptly", "publish", "show", dist, prefix]
            result = util.run_command(cmd, stdout=util.PIPE, check=True)
            sources = self._extract_sources(result.stdout)
            matches = [re_snap.match(source) for source in sources]
            snapshots = [match.group(1) for match in matches if match]
            publish_map[publish] = set(snapshots)

        lg.debug("Joined snapshots and publishes: %s", publish_map)
        return publish_map

    def snapshot_map(self):
        snapshot_map = {}
        # match example:  test-snapshot [snapshot]
        re_snap = re.compile(r"\s+([\w\d-]+)\s\[snapshot\]")
        for snapshot_outer in self.snapshots():
            cmd = ["aptly", "snapshot", "show", snapshot_outer]

            result = util.run_command(cmd, stdout=util.PIPE, check=True)
            sources = self._extract_sources(result.stdout)
            matches = [re_snap.match(source) for source in sources]
            snapshots = [match.group(1) for match in matches if match]
            snapshot_map[snapshot_outer] = set(snapshots)

        lg.debug("Joined snapshots with self(snapshots): %s", snapshot_map)
        return snapshot_map

    def publishes(self):
        """Read all available publishes and cache in lru_cache"""
        return self.read_aptly_list("publish")

    def repos(self):
        """Read all available repo and cache in lru_cache."""
        return self.read_aptly_list("repo")

    def mirrors(self):
        """Read all available mirror and cache in lru_cache."""
        return self.read_aptly_list("mirror")

    def snapshots(self):
        """Read all available snapshot and cache in lru_cache."""
        return self.read_aptly_list("snapshot")

    def read_aptly_list(self, type_):
        """Read lists from aptly.

        :param type_: The type of list to read ie. snapshot
        :type  type_: str
        :param list_: Read into this list
        :param list_: list
        """
        cmd = ["aptly", type_, "list", "-raw"]
        set_ = set()
        result = util.run_command(cmd, stdout=util.PIPE, check=True)
        for line in result.stdout.split("\n"):
            clean_line = line.strip()
            if clean_line:
                set_.add(clean_line)
        return set_

    def has_dependency(self, dependency):
        """Check system state dependencies.

        :param dependency: The dependency to check
        :type  dependency: list
        """
        type_, name = dependency

        if type_ == "repo":  # pragma: no cover
            return name in self.repos()
        if type_ == "mirror":  # pragma: no cover
            return name in self.mirrors()
        elif type_ == "snapshot":
            return name in self.snapshots()  # pragma: no cover
        elif type_ == "gpg_key":  # pragma: no cover
            return name in self.gpg_keys()  # Not needed ATM
        elif type_ == "virtual":
            # virtual dependencies can never be resolved by the
            # system state reader - they are used for internal
            # ordering only
            return False
        else:
            raise ValueError("Unknown dependency to resolve: %s" % str(dependency))


_state_reader: SystemStateReader | None = None


def state_reader():
    global _state_reader
    if not _state_reader:
        _state_reader = SystemStateReader()
    return _state_reader
