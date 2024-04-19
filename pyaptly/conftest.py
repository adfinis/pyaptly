"""pytest conftest."""

import json
import logging
import os
import tempfile
from pathlib import Path

import freezegun
import pytest

from pyaptly import main, state_reader, util

aptly_conf = Path.home().absolute() / ".aptly.conf"
test_base = Path(__file__).absolute().parent / "tests"
setup_base = Path("/setup")


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
    util._PYTEST_KEYSERVER = "hkp://127.0.0.1:8080"

    try:
        yield
    finally:
        util._PYTEST_KEYSERVER = None
        tempdir_obj.cleanup()
        aptly_conf.unlink()


@pytest.fixture()
def test_key_03(environment):
    """Get test gpg-key number 3."""
    util.run_command(["gpg", "--import", setup_base / "test03.key"], check=True)
    util.run_command(["gpg", "--import", setup_base / "test03.pub"], check=True)


@pytest.fixture()
def freeze(request):
    """Freeze to datetime.

    Can be configured with:

    ```python
    @pytest.mark.parametrize("freeze", ["2012-10-10 10:10:10"], indirect=True)
    def test_snapshot_create_basic(environment, config, freeze):
    ...
    ```
    """
    if hasattr(request, "param"):
        freeze = request.param
    else:
        freeze = "2012-10-10 10:10:10"
    with freezegun.freeze_time(freeze) as ft:
        yield ft


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
    yield str(test_base / request.param)


@pytest.fixture()
def mirror_update(environment, config):
    """Test if updating mirrors works."""
    args = ["-c", config, "mirror", "create"]
    state = state_reader.SystemStateReader()
    assert "fakerepo01" not in state.mirrors()
    main.main(args)
    assert "fakerepo01" in state.mirrors()
    args[3] = "update"
    main.main(args)
    args = [
        "aptly",
        "mirror",
        "show",
        "fakerepo01",
    ]
    result = util.run_command(args, stdout=util.PIPE, check=True)
    aptly_state = util.parse_aptly_show_command(result.stdout)
    assert aptly_state["number of packages"] == "2"


@pytest.fixture()
def snapshot_create(config, mirror_update, freeze):
    """Test if createing snapshots works."""
    args = ["-c", config, "snapshot", "create"]
    main.main(args)
    state = state_reader.SystemStateReader()
    assert set(["fakerepo01-20121010T0000Z", "fakerepo02-20121006T0000Z"]).issubset(
        state.snapshots()
    )
    yield state


@pytest.fixture()
def snapshot_update_rotating(config, mirror_update, freeze):
    """Rotate snapshots."""
    args = [
        "-c",
        config,
        "snapshot",
        "create",
    ]
    main.main(args)
    state = state_reader.SystemStateReader()
    assert set(
        [
            "fake-current",
            "fakerepo01-current",
            "fakerepo02-current",
        ]
    ).issubset(state.snapshots())
    args = [
        "-c",
        config,
        "snapshot",
        "update",
    ]
    main.main(args)
    assert set(
        [
            "fake-current",
            "fakerepo01-current-rotated-20121010T1010Z",
            "fakerepo02-current-rotated-20121010T1010Z",
        ]
    ).issubset(state.snapshots())
    expected = {
        "fake-current": set(["fakerepo01-current", "fakerepo02-current"]),
        "fake-current-rotated-20121010T1010Z": set(
            [
                "fakerepo01-current-rotated-20121010T1010Z",
                "fakerepo02-current-rotated-20121010T1010Z",
            ]
        ),
        "fakerepo01-current": set([]),
        "fakerepo01-current-rotated-20121010T1010Z": set([]),
        "fakerepo02-current": set([]),
        "fakerepo02-current-rotated-20121010T1010Z": set([]),
    }
    assert state.snapshot_map() == expected


@pytest.fixture()
def repo_create(environment, config, test_key_03):
    """Test if creating repositories works."""
    args = ["-c", config, "repo", "create"]
    main.main(args)
    state = state_reader.SystemStateReader()
    util.run_command(
        [
            "aptly",
            "repo",
            "add",
            "centrify",
            "/source/compose/setup/hellome_0.1-1_amd64.deb",
        ]
    )
    assert set(["centrify"]) == state.repos()


@pytest.fixture()
def publish_create(config, snapshot_create, test_key_03):
    """Test if creating publishes works."""
    args = ["-c", config, "publish", "create"]
    main.main(args)
    state = state_reader.SystemStateReader()
    assert set(["fakerepo02 main", "fakerepo01 main"]) == state.publishes()
    expect = {
        "fakerepo02 main": set(["fakerepo02-20121006T0000Z"]),
        "fakerepo01 main": set(["fakerepo01-20121010T0000Z"]),
    }
    assert expect == state.publish_map()


@pytest.fixture()
def publish_create_rotating(config, snapshot_update_rotating, test_key_03):
    """Test if creating publishes works."""
    args = ["-c", config, "publish", "create"]
    main.main(args)
    state = state_reader.SystemStateReader()
    assert (
        set(
            [
                "fakerepo01/current stable",
                "fake/current stable",
                "fakerepo02/current stable",
            ]
        )
        == state.publishes()
    )
    expect = {
        "fake/current stable": set(["fake-current"]),
        "fakerepo01/current stable": set(["fakerepo01-current"]),
        "fakerepo02/current stable": set(["fakerepo02-current"]),
    }
    assert expect == state.publish_map()


@pytest.fixture()
def publish_create_republish(config, publish_create, caplog):
    """Test if creating republishes works."""
    found = False
    for rec in caplog.records:
        if rec.levelname == "CRITICAL":
            if "has been deferred" in rec.msg:
                found = True
    assert found
    args = [
        "-c",
        config,
        "publish",
        "create",
    ]
    main.main(args)
    state = state_reader.SystemStateReader()
    assert "fakerepo01-stable main" in state.publishes()
