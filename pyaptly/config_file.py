from pathlib import Path

import toml
import yaml


def yaml_to_toml(yaml_path: Path, toml_path: Path, *, add_defaults: bool = False):
    with yaml_path.open("r", encoding="UTF-8") as yf:
        with toml_path.open("w", encoding="UTF-8") as tf:
            config = yaml.safe_load(yf)
            if add_defaults:
                add_dehfault_to_config(config)
            toml.dump(config, tf)


def add_dehfault_to_config(config):
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
