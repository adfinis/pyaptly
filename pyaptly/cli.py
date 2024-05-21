"""python-click based command line interface for pyaptly."""

import logging
import sys
from pathlib import Path
from subprocess import CalledProcessError

import click

lg = logging.getLogger(__name__)


def entry_point():
    """Fix args then call click."""
    # TODO this makes the legacy command more usable. remove legacy commands when
    # we are out of beta
    argv = list(sys.argv)
    len_argv = len(argv)
    if len_argv > 0 and argv[0].endswith("pyaptly"):
        if len_argv > 2 and argv[1] == "legacy" and argv[2] != "--":
            argv = argv[:2] + ["--"] + argv[2:]

    try:
        cli.main(argv[1:])
    except CalledProcessError:
        pass  # already logged
    except Exception as e:
        from . import util

        path = util.write_traceback()
        tb = f"Wrote traceback to: {path}"
        msg = " ".join([str(x) for x in e.args])
        lg.error(f"{msg}\n               {tb}")


# I want to release the new cli interface with 2.0, so we do not repeat breaking changes.
# But changing all functions that use argparse, means also changing all the tests, which
# (ab)use the argparse interface. So we currently fake that interface, so we can roll-out
# the new interface early.
# TODO: remove this, once argparse is gone
class FakeArgs:
    """Helper for compatiblity."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# I decided it is a good pattern to do lazy imports in the cli module. I had to
# do this in a few other CLIs for startup performance.


@click.group()
def cli():
    """Show basic command group."""
    pass


# TODO legacy is here to be able to do early alpha and get feedback from users.
# remove when there is full replacement.
@cli.command(help="run legacy command parser")
@click.argument("passthrough", nargs=-1)
def legacy(passthrough):
    """Run legacy pyaptly cli."""
    from . import main

    main.main(argv=passthrough)


@cli.command()
@click.option("--info/--no-info", "-i/-ni", default=False, type=bool)
@click.option("--debug/--no-debug", "-d/-nd", default=False, type=bool)
@click.option(
    "--pretend/--no-pretend",
    "-p/-np",
    default=False,
    type=bool,
    help="Do not change anything",
)
@click.argument("config", type=click.Path(file_okay=True, dir_okay=False, exists=True))
@click.argument("task", type=click.Choice(["create"]))
@click.option("--repo-name", "-n", default="all", type=str, help='default: "all"')
def repo(**kwargs):
    """Create aptly repos."""
    from . import main, repo

    fake_args = FakeArgs(**kwargs)
    main.setup_logger(fake_args)
    cfg = main.prepare(fake_args)
    repo.repo(cfg, args=fake_args)


@cli.command()
@click.option("--info/--no-info", "-i/-ni", default=False, type=bool)
@click.option("--debug/--no-debug", "-d/-nd", default=False, type=bool)
@click.option(
    "--pretend/--no-pretend",
    "-p/-np",
    default=False,
    type=bool,
    help="Do not change anything",
)
@click.argument("config", type=click.Path(file_okay=True, dir_okay=False, exists=True))
@click.argument("task", type=click.Choice(["create", "update"]))
@click.option("--mirror-name", "-n", default="all", type=str, help='default: "all"')
def mirror(**kwargs):
    """Manage aptly mirrors."""
    from . import main, mirror

    fake_args = FakeArgs(**kwargs)
    main.setup_logger(fake_args)
    cfg = main.prepare(fake_args)
    mirror.mirror(cfg, args=fake_args)


@cli.command()
@click.option("--info/--no-info", "-i/-ni", default=False, type=bool)
@click.option("--debug/--no-debug", "-d/-nd", default=False, type=bool)
@click.option(
    "--pretend/--no-pretend",
    "-p/-np",
    default=False,
    type=bool,
    help="Do not change anything",
)
@click.argument("config", type=click.Path(file_okay=True, dir_okay=False, exists=True))
@click.argument("task", type=click.Choice(["create", "update"]))
@click.option("--snapshot-name", "-n", default="all", type=str, help='default: "all"')
def snapshot(**kwargs):
    """Manage aptly snapshots."""
    from . import main, snapshot

    fake_args = FakeArgs(**kwargs)
    main.setup_logger(fake_args)
    cfg = main.prepare(fake_args)
    snapshot.snapshot(cfg, args=fake_args)


@cli.command()
@click.option("--info/--no-info", "-i/-ni", default=False, type=bool)
@click.option("--debug/--no-debug", "-d/-nd", default=False, type=bool)
@click.option(
    "--pretend/--no-pretend",
    "-p/-np",
    default=False,
    type=bool,
    help="Do not change anything",
)
@click.argument("config", type=click.Path(file_okay=True, dir_okay=False, exists=True))
@click.argument("task", type=click.Choice(["create", "update"]))
@click.option("--publish-name", "-n", default="all", type=str, help='default: "all"')
def publish(**kwargs):
    """Manage aptly publishs."""
    from . import main, publish

    fake_args = FakeArgs(**kwargs)
    main.setup_logger(fake_args)
    cfg = main.prepare(fake_args)
    publish.publish(cfg, args=fake_args)


@cli.command(help="convert yaml- to toml-comfig")
@click.argument(
    "yaml_path",
    type=click.Path(
        file_okay=True,
        dir_okay=False,
        exists=True,
        readable=True,
        path_type=Path,
    ),
)
@click.argument(
    "toml_path",
    type=click.Path(
        file_okay=True,
        dir_okay=False,
        exists=False,
        writable=True,
        path_type=Path,
    ),
)
@click.option(
    "-a/-na",
    "--add-defaults/--no-add-defaults",
    type=bool,
    default=False,
    help="Add default values to fields if missing",
)
def yaml_to_toml(yaml_path: Path, toml_path: Path, add_defaults: bool):
    """Convert pyaptly config files from yaml to toml."""
    from . import config_file

    config_file.yaml_to_toml(
        yaml_path,
        toml_path,
        add_defaults=add_defaults,
    )
