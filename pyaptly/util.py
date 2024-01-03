"""Basic function like running processes and logging."""

import logging
import subprocess
from subprocess import DEVNULL, PIPE  # noqa: F401
from typing import Union

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


def is_debug_mode():
    """Check if we are in debug mode."""
    return _DEBUG or _PYTEST_DEBUG


def run(cmd_args: list[str], *, decode: bool = True, **kwargs):
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


def indent_out(output: Union[bytes, str]) -> str:
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
