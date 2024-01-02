"""Test mirror functionality."""
import logging

import pytest

import pyaptly
from pyaptly import util


@pytest.mark.parametrize("config", ["mirror-extra.toml"], indirect=True)
def test_mirror_create(environment, config, caplog):
    """Test if creating mirrors works."""
    config_file, config_dict = config

    caplog.set_level(logging.DEBUG)
    pyaptly.main(["-c", config_file, "mirror", "create"])
    keys_added = []
    for rec in caplog.records:
        for arg in rec.args:
            if isinstance(arg, list):
                if arg[0] == "gpg":
                    keys_added.append(arg[7])
    assert len(keys_added) > 0
    assert len(keys_added) == len(set(keys_added)), "Key multiple times added"

    expect = set(config_dict["mirror"].keys())
    state = pyaptly.SystemStateReader()
    state.read()
    assert state.mirrors == expect


@pytest.mark.parametrize("config", ["mirror-basic.toml"], indirect=True)
def test_mirror_update(environment, config):
    """Test if updating mirrors works."""
    config_file, config_dict = config
    do_mirror_update(config_file)


def do_mirror_update(config_file):
    """Test if updating mirrors works."""
    args = ["-c", config_file, "mirror", "create"]
    state = pyaptly.SystemStateReader()
    state.read()
    assert "fakerepo01" not in state.mirrors
    pyaptly.main(args)
    state.read()
    assert "fakerepo01" in state.mirrors
    args[3] = "update"
    pyaptly.main(args)
    args = [
        "aptly",
        "mirror",
        "show",
        "fakerepo01",
    ]
    result = util.run(args, stdout=util.PIPE, check=True)
    aptly_state = util.parse_aptly_show_command(result.stdout)
    assert aptly_state["number of packages"] == "2"
