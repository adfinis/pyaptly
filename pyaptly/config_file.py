"""Handling pyaptly config-files."""

from pathlib import Path

import tomli_w
import yaml


def yaml_to_toml(yaml_path: Path, toml_path: Path, *, add_defaults: bool = False):
    """
    Convert pyaptly config files from YAML to TOML format.

    The conversion process reads a configuration from the file located at `yaml_path`,
    converts it to TOML format, and writes the result to the file specified by
    `toml_path`. If `add_defaults` is set to True, common defaults are applied during
    the conversion.
    """
    with yaml_path.open("r", encoding="UTF-8") as yf:
        with toml_path.open("wb") as tf:
            config = yaml.safe_load(yf)
            if add_defaults:
                add_default_to_config(config)
            tomli_w.dump(config, tf)


def add_default_to_config(config: dict):
    """
    Set common defaults in `config` if the fields are missing.

    This function checks for missing 'components' and 'distribution' fields under both
    'mirror' and 'publish' sections of the configuration. If these fields are missing,
    it sets them to 'main'.
    """
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
