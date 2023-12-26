import logging

import pytest

import pyaptly


@pytest.mark.parametrize("config", ["publish.toml"], indirect=True)
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
