"""Aptly mirror/snapshot managment automation."""

import argparse
import logging
import sys
from pathlib import Path

from . import command, custom_logger, mirror, publish, repo, snapshot, util

_logging_setup = False


lg = logging.getLogger(__name__)


def setup_logger(args):
    """Setup the logger."""
    global _logging_setup
    root = logging.getLogger()
    formatter = custom_logger.CustomFormatter()
    if not _logging_setup:  # noqa
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        root.addHandler(handler)
        root.setLevel(logging.WARNING)
        handler.setLevel(logging.WARNING)
        if args.info:
            root.setLevel(logging.INFO)
            handler.setLevel(logging.INFO)
        if args.debug:
            root.setLevel(logging.DEBUG)
            handler.setLevel(logging.DEBUG)
        _logging_setup = True  # noqa


def prepare(args):
    """Set pretend mode, read config and load state."""
    command.Command.pretend_mode = args.pretend

    path = Path(args.config)
    with open(args.config, "rb") as f:
        if path.suffix == ".toml":
            import tomli

            cfg = tomli.load(f)
        elif path.suffix == ".json":
            import json

            cfg = json.load(f)
        elif path.suffix in (".yaml", ".yml"):
            import yaml

            cfg = yaml.safe_load(f)
            lg.warn(
                "NOTE: yaml has beed deprecated and will be remove on the next major release."
            )
        else:
            util.exit_with_error(f"unknown config file extension: {path.suffix}")
    return cfg


def main(argv=None):
    """Define parsers and executes commands.

    :param argv: Arguments usually taken from sys.argv
    :type  argv: list
    """
    if not argv:  # pragma: no cover
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description="Manage aptly")
    parser.add_argument(
        "--config",
        "-c",
        help="Yaml config file defining mirrors and snapshots",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--debug",
        "-d",
        help="Enable debug output",
        action="store_true",
    )
    parser.add_argument(
        "--info",
        "-i",
        help="Enable info output (show executed commands)",
        action="store_true",
    )
    parser.add_argument(
        "--pretend",
        "-p",
        help="Do not do anything, just print out what WOULD be done",
        action="store_true",
    )
    subparsers = parser.add_subparsers()
    mirror_parser = subparsers.add_parser("mirror", help="manage aptly mirrors")
    mirror_parser.set_defaults(func=mirror.mirror)
    mirror_parser.add_argument("task", type=str, choices=["create", "update"])
    mirror_parser.add_argument("mirror_name", type=str, nargs="?", default="all")
    snap_parser = subparsers.add_parser("snapshot", help="manage aptly snapshots")
    snap_parser.set_defaults(func=snapshot.snapshot)
    snap_parser.add_argument("task", type=str, choices=["create", "update"])
    snap_parser.add_argument("snapshot_name", type=str, nargs="?", default="all")
    publish_parser = subparsers.add_parser(
        "publish", help="manage aptly publish endpoints"
    )
    publish_parser.set_defaults(func=publish.publish)
    publish_parser.add_argument("task", type=str, choices=["create", "update"])
    publish_parser.add_argument("publish_name", type=str, nargs="?", default="all")
    repo_parser = subparsers.add_parser("repo", help="manage aptly repositories")
    repo_parser.set_defaults(func=repo.repo)
    repo_parser.add_argument("task", type=str, choices=["create"])
    repo_parser.add_argument("repo_name", type=str, nargs="?", default="all")

    args = parser.parse_args(argv)
    setup_logger(args)
    cfg = prepare(args)

    # run function for selected subparser
    args.func(cfg, args)


if __name__ == "__main__":  # pragma: no cover
    main()
