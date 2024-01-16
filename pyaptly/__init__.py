"""PyAptly automates the creation and managment of aptly mirrors and snapshots.

Configuration is based on toml input files.
"""

from pyaptly.legacy import (  # type: ignore  # TODO  # noqa: F401
    Command,
    SystemStateReader,
    main,
)
