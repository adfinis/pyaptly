"""Testing testing helper functions."""
from .. import command, state_reader


def test_command_dependency_fail():
    """Test if bad dependencies fail correctly."""
    a = command.Command(["ls"])
    error = False
    try:
        a.require("turbo", "banana")
    except AssertionError:
        error = True
    assert error


def test_dependency_callback_file():
    """Test if bad dependencies fail correctly."""
    state = state_reader.SystemStateReader()
    try:
        state.has_dependency(["turbo", "banana"])
    except ValueError as e:
        assert "Unknown dependency" in e.args[0]
        error = True
    assert error
