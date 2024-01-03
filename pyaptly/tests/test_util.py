"""Test the util.py module."""
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
                util.run(["/bin/cat", test_path / "bad-unicode.bin"], decode=decode)
        else:
            util.run(["/bin/cat", test_path / "bad-unicode.bin"], decode=decode)
            assert "stdout:     'b'he\\xffllo''" in caplog.messages[0]
    else:
        util.run(["sh", "-c", "printf hello"], decode=decode)
    caplog.clear()
    util.run(["sh", "-c", "printf error 1>&2; false"], decode=decode)
    assert "stderr:     'error'" in caplog.messages[0]
    assert "returncode: 1" in caplog.messages[0]
    caplog.clear()
    util.run(["sh", "-c", "printf 'first\nsecond'"], decode=decode)
    assert EXPECT in caplog.messages[0]
