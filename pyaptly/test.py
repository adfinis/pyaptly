# type: ignore  # TODO
# flake8: noqa  # TODO

"""Tools for testing pyaptly"""

import codecs
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import freezegun
import pytest
import six
import yaml

import pyaptly.legacy as pyaptly

aptly_conf = Path.home().absolute() / ".aptly.conf"

hypothesis_min_ver = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7"
)

if six.PY2:  # pragma: no cover
    environb = os.environ
else:
    environb = os.environb  # pragma: no cover


def read_yml(file_):
    """Read and merge a yml file.

    :param file_: file to read
    :type  file_: str"""
    directory = os.path.dirname(file_)
    with codecs.open(file_, encoding="UTF-8") as f:
        main_yml = dict(yaml.safe_load(f.read()))
    merges = []
    if "merge" in main_yml:
        for merge_path in main_yml["merge"]:
            path = os.path.join(
                directory,
                merge_path.encode("UTF-8"),
            )
            merges.append(read_yml(path))
        del main_yml["merge"]
    for merge_struct in merges:
        main_yml = merge(main_yml, merge_struct)
    return main_yml


def merge(a, b):
    """Merge two dicts.

    :param a: dict a
    :type  a: dict
    :param b: dict b
    :type  b: dict
    :rtype:   dict
    """
    if isinstance(a, dict) and isinstance(b, dict):
        d = dict(a)
        d.update(dict(((k, merge(a.get(k, None), b[k])) for k in b)))
        for k, v in list(d.items()):
            if v == "None":
                del d[k]
        return d
    return b


def execute_and_parse_show_cmd(args):  # pragma: no cover
    """Executes and parses a aptly show command.

    :param args: Command to execute
    :type  args: list
    """
    result = {}
    show, _ = pyaptly.call_output(args)
    for line in show.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.lower()
            result[key] = value.strip()
    return result


def create_config(test_input):
    """Returns path to pyaptly config from test input.

    Test input should be minimal and extended/tranformed in create_config.

    :param test_input: Test input read from test-yml.
    :type  test_input: dict
    :rtype:            (dict, str)
    """
    input_ = read_yml(test_input)
    if "mirror" in input_:
        for mirror in input_["mirror"].values():
            if "components" not in mirror:
                mirror["components"] = "main"
            if "distribution" not in mirror:
                mirror["distribution"] = "main"
    if "publish" in input_:  # pragma: no cover
        for publish in input_["publish"].values():
            for item in publish:
                if "components" not in item:
                    item["components"] = "main"
                if "distribution" not in item:
                    item["distribution"] = "main"
    try:
        file_ = codecs.getwriter("UTF-8")(tempfile.NamedTemporaryFile(delete=False))
        yaml.dump(input_, file_)
    finally:
        file_.close()
    return (input_, file_.name)


@contextlib.contextmanager
def clean_and_config(test_input, freeze="2012-10-10 10:10:10", sign=False):
    """Remove aptly file and create a input config file to run pyaptly with.

    Test input should be minimal and extended/tranformed in create_config.
    """
    tempdir_obj = tempfile.TemporaryDirectory()
    tempdir = Path(tempdir_obj.name).absolute()

    aptly = tempdir / "aptly"
    aptly.mkdir(parents=True)
    config = {"rootDir": str(aptly)}
    if aptly_conf.exists():  # pragma: no cover
        aptly_conf.unlink()
    with aptly_conf.open("w") as f:
        json.dump(config, f)

    gnupg = tempdir / "gnugp"
    gnupg.mkdir(parents=True)
    os.chown(gnupg, 0, 0)
    gnupg.chmod(0o700)
    environb[b"GNUPGHOME"] = str(gnupg).encode("UTF-8")

    if sign:  # pragma: no cover
        setup = Path("/setup")
        subprocess.run(["gpg", "--import", setup / "test03.pub"], check=True)
        subprocess.run(["gpg", "--import", setup / "test03.key"], check=True)

    input_, file_ = create_config(test_input)
    try:
        with freezegun.freeze_time(freeze):
            yield (input_, file_)
    finally:
        tempdir_obj.cleanup()
        aptly_conf.unlink()
