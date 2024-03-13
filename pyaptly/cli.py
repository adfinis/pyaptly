"""python-click based command line interface for pyaptly."""

import sys
from pathlib import Path

import click

# I decided it is a good pattern to do lazy imports in the cli module. I had to
# do this in a few other CLIs for startup performance.


# TODO this makes the legacy command more usable. remove and set the entry point
# back to `pyaptly = 'pyaptly.cli:cli'
def entry_point():
    """Fix args then call click."""
    argv = list(sys.argv)
    len_argv = len(argv)
    if len_argv > 0 and argv[0].endswith("pyaptly"):
        if len_argv > 2 and argv[1] == "legacy" and argv[2] != "--":
            argv = argv[:2] + ["--"] + argv[2:]
    cli.main(argv[1:])


@click.group()
@click.option(
    "-d/-nd",
    "--debug/--no-debug",
    type=bool,
    default=False,
    help="Add default values to fields if missing",
)
def cli(debug: bool):
    """Show basic command group."""
    from pyaptly import util

    util._DEBUG = debug


# TODO legacy is here to be able to do early alpha and get feedback from users.
# remove when there is full replacement.
@cli.command(help="run legacy command parser")
@click.argument("passthrough", nargs=-1)
def legacy(passthrough):
    """Run legacy pyaptly cli."""
    from . import main

    main.main(argv=passthrough)


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
