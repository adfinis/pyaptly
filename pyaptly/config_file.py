"""Handling pyaptly config-files."""

# TODO: remove this as soon as most people have converted their config.

from pathlib import Path

import tomli
import yaml

from pyaptly import tomli_w


def yaml_to_toml(yaml_path: Path, toml_path: Path, *, add_defaults: bool = False):
    """Convert pyaptly config files from yaml to toml.

    Setting `add_defaults=True` will set common default during conversion.
    """
    with yaml_path.open("r", encoding="UTF-8") as yf:
        with toml_path.open("wb") as tf:
            config = yaml.safe_load(yf)
            if add_defaults:
                add_default_to_config(config)
            tomli_w.dump(config, tf)


def toml_to_toml(in_path: Path, toml_path: Path, *, add_defaults: bool = False):
    """Convert pyaptly config files from toml to toml.

    Setting `add_defaults=True` will set common default during conversion.
    """
    with in_path.open("rb") as nf:
        with toml_path.open("wb") as tf:
            config = tomli.load(nf)
            if add_defaults:
                add_default_to_config(config)
            tomli_w.dump(config, tf)


def add_default_to_config(config):
    """Set common default in config if the fields are missing."""
    if "mirror" in config:
        for mirror in config["mirror"].values():
            if "components" not in mirror:
                mirror["components"] = "main"
            if "distribution" not in mirror:
                mirror["distribution"] = "main"
    if "publish" in config:
        for publish in config["publish"].values():
            for item in publish:
                if "components" not in item:
                    item["components"] = "main"
                if "distribution" not in item:
                    item["distribution"] = "main"
