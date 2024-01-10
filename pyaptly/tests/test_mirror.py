"""Test mirror functionality."""
import pytest

import pyaptly


@pytest.mark.parametrize("config", ["mirror-extra.toml"], indirect=True)
def test_mirror_create(environment, config, caplog):
    """Test if creating mirrors works."""
    pyaptly.main(["-c", config, "mirror", "create"])
    keys_added = []
    for rec in caplog.records:
        for arg in rec.args:
            if isinstance(arg, list):
                if arg[0] == "gpg":
                    keys_added.append(arg[7])
    assert len(keys_added) > 0
    assert len(keys_added) == len(set(keys_added)), "Key multiple times added"

    state = pyaptly.SystemStateReader()
    state.read()
    assert state.mirrors == {"fakerepo03"}


@pytest.mark.parametrize("config", ["mirror-basic.toml"], indirect=True)
def test_mirror_update(mirror_update):
    """Test if updating mirrors works."""
    pass


@pytest.mark.parametrize("config", ["mirror-basic.toml"], indirect=True)
def test_mirror_update_inexistent(config, mirror_update):
    """Test if updating an inexistent mirror causes an error."""
    args = ["-c", config, "mirror", "update", "asdfasdf"]
    error = False
    try:
        pyaptly.main(args)
    except ValueError:
        error = True
    assert error


@pytest.mark.parametrize("config", ["mirror-basic.toml"], indirect=True)
def test_mirror_update_single(config, mirror_update):
    """Test if updating a single mirror works."""
    args = ["-c", config, "mirror", "update", "fakerepo01"]
    pyaptly.main(args)
