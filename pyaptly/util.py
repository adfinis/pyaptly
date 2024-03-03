"""Basic function like running processes and logging."""

import logging
import subprocess
from pathlib import Path
from subprocess import DEVNULL, PIPE, CalledProcessError  # noqa: F401
from typing import Optional, Sequence

_DEFAULT_KEYSERVER: str = "hkps://keys.openpgp.org"
_PYTEST_KEYSERVER: Optional[str] = None

_DEBUG = False
_PYTEST_DEBUG = False

RESULT_LOG = """
Command call
args:       {args}
returncode: {returncode}
stdout:     '{stdout}'
stderr:     '{stderr}'
""".strip()
_indent = " " * 13

logger = logging.getLogger(__name__)


def unit_or_list_to_list(thingy):
    """Ensure that a yml entry is always a list.

    Used to allow lists and single units in the yml file.

    :param thingy: The data to ensure it is a list
    :type  thingy: list, tuple or other
    """
    if isinstance(thingy, list) or isinstance(thingy, tuple):
        return list(thingy)
    else:
        return [thingy]


def get_default_keyserver():
    """Get default keyseerver."""
    if _PYTEST_KEYSERVER:
        return _PYTEST_KEYSERVER
    else:
        return _DEFAULT_KEYSERVER


def is_debug_mode():
    """Check if we are in debug mode."""
    return _DEBUG or _PYTEST_DEBUG


def run_command(cmd_args: Sequence[str | Path], *, decode: bool = True, **kwargs):
    """Instrumented subprocess.run for easier debugging.

    By default this run command will add `encoding="UTF-8"` to kwargs. Disable
    with `decode=False`.
    """
    debug = is_debug_mode()
    added_stdout = False
    added_stderr = False
    if debug:
        if "stdout" not in kwargs:
            kwargs["stdout"] = PIPE
            added_stdout = True
        if "stderr" not in kwargs:
            kwargs["stderr"] = PIPE
            added_stderr = True
    result = None
    if decode and "encoding" not in kwargs:
        kwargs["encoding"] = "UTF-8"
    try:
        result = subprocess.run(cmd_args, **kwargs)
    finally:
        if debug and result:
            log_run_result(result)
            # Do not change returned result by debug mode
            if added_stdout:
                delattr(result, "stdout")
            if added_stderr:
                delattr(result, "stderr")
    return result


def indent_out(output: bytes | str) -> str:
    """Indent command output for nicer logging-messages.

    It will convert bytes to strings if need or display the result as bytes if
    decoding fails.
    """
    output = output.strip()
    if not output:
        return ""
    indented = False
    if hasattr(output, "decode"):
        try:
            output = output.decode(encoding="UTF-8")
            lines = output.splitlines()
            result = [lines[0]]
            for line in lines[1:]:
                result.append(f"{_indent}{line}")
            indented = True
        except UnicodeDecodeError:
            pass

    if not indented:
        lines = output.splitlines()
        result = [str(lines[0])]
        for line in lines[1:]:
            result.append(f"{_indent}{str(line)}")
    return "\n".join(result)


def log_run_result(result: subprocess.CompletedProcess):
    """Log a CompletedProcess result log debug."""
    msg = RESULT_LOG.format(
        args=result.args,
        returncode=result.returncode,
        stdout=indent_out(result.stdout),
        stderr=indent_out(result.stderr),
    )
    logger.debug(msg)


def parse_aptly_show_command(show: str) -> dict[str, str]:
    """Parse an aptly show command."""
    result = {}
    for line in show.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.lower()
            result[key] = value.strip()
    return result
