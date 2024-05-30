"""PyAptly automates the creation and managment of aptly mirrors and snapshots.

Configuration is based on toml input files.
"""

import os


def init_hypothesis():
    """Initialize hypothesis profile if hypothesis is available."""
    try:  # pragma: no cover
        if "HYPOTHESIS_PROFILE" in os.environ and os.environ["HYPOTHESIS_PROFILE"]:
            from hypothesis import settings

            settings.register_profile("ci", settings(max_examples=500))
            settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))
    except (ImportError, AttributeError):  # pragma: no cover
        pass


init_hypothesis()
