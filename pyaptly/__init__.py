"""PyAptly automates the creation and managment of aptly mirrors and snapshots.

Configuration is based on toml input files.
"""

from pyaptly.legacy import SystemStateReader, main  # type: ignore  # TODO  # noqa: F401
