"""Testing pyaptly"""
import contextlib
import logging
import os

from pyaptly import main

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
        gpg.side_effect = lambda _: ""
        args = [
            '-d',
            '-c',
            os.path.join(_test_base, 'test01.yml'),
            'mirror',
            'create'
        ]
        main(args)
        assert logging.getLogger().level == logging.DEBUG
