"""Test the util.py module."""
from datetime import datetime

import pytest

from .. import util

EXPECT = """
stdout:     'first
             second'
""".strip()


@pytest.mark.parametrize("decode", [True, False])
@pytest.mark.parametrize("unicode_error", [True, False])
def test_run(test_path, debug_mode, caplog, decode, unicode_error):
    """Testing the instrumented run function."""
    if unicode_error:
        if decode:
            with pytest.raises(UnicodeDecodeError):
                util.run_command(
                    ["/bin/cat", test_path / "bad-unicode.bin"], decode=decode
                )
        else:
            util.run_command(["/bin/cat", test_path / "bad-unicode.bin"], decode=decode)
            assert "stdout:     'b'he\\xffllo''" in caplog.messages[0]
    else:
        util.run_command(["sh", "-c", "printf hello"], decode=decode)
    caplog.clear()
    util.run_command(["sh", "-c", "printf error 1>&2; false"], decode=decode)
    assert "stderr:     'error'" in caplog.messages[0]
    assert "returncode: 1" in caplog.messages[0]
    caplog.clear()
    util.run_command(["sh", "-c", "printf 'first\nsecond'"], decode=decode)
    assert EXPECT in caplog.messages[0]


@pytest.mark.parametrize("freeze", ["2014-10-10 10:10:10"], indirect=True)
def test_freeze(freeze):
    """Test if setting freeze params works."""
    assert str(datetime.now()) == "2014-10-10 10:10:10"
