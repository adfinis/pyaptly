"""Test the util.py module."""

from datetime import datetime

import pytest

from .. import snapshot, util

EXPECT = """stdout:     'first
               second'"""


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
    assert "-> 1" in caplog.messages[0]
    caplog.clear()
    util.run_command(["sh", "-c", "printf 'first\nsecond'"], decode=decode)
    assert EXPECT in caplog.messages[0]


@pytest.mark.parametrize("freeze", ["2014-10-10 10:10:10"], indirect=True)
def test_freeze(freeze):
    """Test if setting freeze params works."""
    assert str(datetime.now()) == "2014-10-10 10:10:10"


def test_snapshot_spec_as_dict():
    """Test various snapshot formats for snapshot_spec_to_name()."""
    snap_string = "snapshot-foo"
    snap_dict = {"name": "foo"}

    cfg: dict = {
        "snapshot": {
            "foo": {},
        }
    }

    assert snapshot.snapshot_spec_to_name(cfg, snap_string) == snap_string
    assert snapshot.snapshot_spec_to_name(cfg, snap_dict) == "foo"


def test_get_default_keyserver():
    """Test getting default keyserver."""
    assert util.get_default_keyserver() == util._DEFAULT_KEYSERVER
