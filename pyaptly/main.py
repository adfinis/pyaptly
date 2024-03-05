"""Aptly mirror/snapshot managment automation."""
import argparse
import logging
import sys

import tomli

from . import command, mirror, publish, repo, snapshot, state_reader

_logging_setup = False


lg = logging.getLogger(__name__)


def main(argv=None):
    """Define parsers and executes commands.

    :param argv: Arguments usually taken from sys.argv
    :type  argv: list
    """
    global _logging_setup
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
    root = logging.getLogger()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    if not _logging_setup:  # noqa
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        root.addHandler(handler)
        handler.setLevel(logging.CRITICAL)
        if args.debug:
            root.setLevel(logging.DEBUG)
            handler.setLevel(logging.DEBUG)
    if args.pretend:
        command.Command.pretend_mode = True
    else:
        command.Command.pretend_mode = False

        _logging_setup = True  # noqa
    lg.debug("Args: %s", vars(args))

    with open(args.config, "rb") as f:
        cfg = tomli.load(f)
    state_reader.state.read()

    # run function for selected subparser
    args.func(cfg, args)


if __name__ == "__main__":  # pragma: no cover
    main()
