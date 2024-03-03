"""Contains shared types. A seperate file prevents cyclic dependencies."""

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:  # pragma: no cover
    from . import command

SnapshotCommand = Callable[[dict, str, dict], list["command.Command"]]
