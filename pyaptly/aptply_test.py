"""Testing pyaptly"""
import contextlib
import logging
import os

import testfixtures

from pyaptly import SystemStateReader, main

from . import test

try:
    import unittest.mock as mock
except ImportError:
    import mock


_test_base = os.path.dirname(
    os.path.abspath(__file__)
)


def mock_subprocess():
    """Mock subprocess that no commands are executed"""
    return contextlib.nested(
        mock.patch("subprocess.check_call"),
        mock.patch("pyaptly.call_output"),
    )


def test_debug():
    """Test if debug is enabled with -d"""
    with mock_subprocess() as (_, gpg):
        gpg.side_effect = lambda _: ("", "")
        args = [
            '-d',
            '-c',
            os.path.join(_test_base, 'test01.yml'),
            'mirror',
            'create'
        ]
        main(args)
        assert logging.getLogger().level == logging.DEBUG


def test_mirror_create():
    """Test if createing mirrors works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            "mirror.yml",
    )) as (tyml, config):
        args = [
            '-d',
            '-c',
            config,
            'mirror',
            'create'
        ]
        keys_added = []
        with testfixtures.LogCapture() as l:
            main(args)
            for rec in l.records:
                for arg in rec.args:
                    if isinstance(arg, list):
                        if arg[0] == "gpg":
                            keys_added.append(arg[7])
        assert len(keys_added) > 0
        assert len(keys_added) == len(set(keys_added)), (
            "Key multiple times added"
        )

        expect = set(tyml['mirror'].keys())
        state = SystemStateReader()
        state.read()
        assert state.mirrors == expect


def test_mirror_update():
    """Test if updating mirrors works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            "mirror-no-google.yml",
    )) as (tyml, config):
        args = [
            '-d',
            '-c',
            config,
            'mirror',
            'create'
        ]
        state = SystemStateReader()
        state.read()
        assert "fakerepo01" not in state.mirrors
        main(args)
        state.read()
        assert "fakerepo01" in state.mirrors
        args[4] = 'update'
        main(args)
        args = [
            'aptly',
            'mirror',
            'show',
        ]
        args01 = list(args)
        args01.append("fakerepo01")
        aptly_state = test.execute_and_parse_show_cmd(args01)
        assert aptly_state['number of packages'] == "2"


def test_snapshot_create_basic():
    """Test if snapshot create works."""
    test_mirror_update()
