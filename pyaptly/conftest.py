"""pytest conftest."""

import json
import logging
import os
import tempfile
from pathlib import Path

import pytest
import toml
import yaml

aptly_conf = Path.home().absolute() / ".aptly.conf"
test_base = Path(__file__).absolute().parent / "tests"


@pytest.fixture()
def debug_mode():
    """Enable debug mode, set log-level and log run() commands."""
    from pyaptly import util

    level = logging.root.getEffectiveLevel()

    try:
        util._PYTEST_DEBUG = True
        logging.root.setLevel(logging.DEBUG)

        yield
    finally:
        util._PYTEST_DEBUG = False
        logging.root.setLevel(level)


@pytest.fixture()
def test_path():
    """Return test_base as test_path to find assets for testing."""
    yield test_base


@pytest.fixture()
def environment(debug_mode):
    """Get a test environment.

    - An aptly config and directory
    - An gnupg directory
    - web-server and key-server are always running in the docker-container
    """
    tempdir_obj = tempfile.TemporaryDirectory()
    tempdir = Path(tempdir_obj.name).absolute()

    aptly = tempdir / "aptly"
    aptly.mkdir(parents=True)
    config = {"rootDir": str(aptly)}
    if aptly_conf.exists():  # pragma: no cover
        aptly_conf.unlink()
    with aptly_conf.open("w") as f:
        json.dump(config, f)

    gnupg = tempdir / "gnugp"
    gnupg.mkdir(parents=True)
    os.chown(gnupg, 0, 0)
    gnupg.chmod(0o700)
    os.environ["GNUPGHOME"] = str(gnupg)

    try:
        yield
    finally:
        tempdir_obj.cleanup()
        aptly_conf.unlink()


@pytest.fixture()
def config(request):
    """Get a config.

    Can be configured with:

    ```python
    @pytest.mark.parametrize("config", ["mirror-extra.toml"], indirect=True)
    def test_mirror_create(environment, config, caplog):
    ...
    ```
    """
    config_file = test_base / request.param
    with config_file.open("r", encoding="UTF-8") as f:
        config = toml.load(f)
    # TODO: remove yaml conversion
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="UTF-8", delete=False) as f:
            yaml.dump(config, f)
        yield f.name, config
    finally:
        Path(f.name).unlink()
