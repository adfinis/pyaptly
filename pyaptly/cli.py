from pathlib import Path

import click

# I decided it is a good pattern to do lazy imports in the cli module. I had to
# do this in a few other CLIs for startup performance.


@click.group()
@click.option(
    "-d/-nd",
    "--debug/--no-debug",
    type=bool,
    default=False,
    help="Add default values to fields if missing",
)
def cli(debug):
    from pyaptly import util

    util._DEBUG = debug


@cli.command(help="run legacy command parser")
def legacy():
    from pyaptly import main

    main()


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
        exists=None,
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
def yaml_to_toml(yaml_path, toml_path, add_defaults):
    from pyaptly import config_file

    config_file.yaml_to_toml(
        yaml_path,
        toml_path,
        add_defaults=add_defaults,
    )
