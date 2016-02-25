"""Testing testing helper functions"""
import subprocess

from pyaptly import Command, SystemStateReader, call_output


def test_call_output_error():
    """Test if call_output raises errors correctly"""
    args = [
        'bash',
        '-c',
        'exit 42',
    ]
    error = False
    try:
        call_output(args)
    except subprocess.CalledProcessError as e:
        assert e.returncode == 42
        error = True
    assert error


def test_command_dependency_fail():
    """Test if bad dependencies fail correctly."""
    a = Command(['ls'])
    error = False
    try:
        a.require("turbo", "banana")
    except AssertionError:
        error = True
    assert error


def test_dependency_callback_file():
    """Test if bad dependencies fail correctly."""
    state = SystemStateReader()
    try:
        state.has_dependency(['turbo', 'banana'])
    except ValueError as e:
        assert "Unknown dependency" in e.args[0]
        error = True
    assert error
