import json
import os
import tempfile
from pathlib import Path

import pytest
import toml
import yaml

aptly_conf = Path.home().absolute() / ".aptly.conf"
test_base = Path(__file__).absolute().parent / "tests"


@pytest.fixture()
def environment():
    tempdir_obj = tempfile.TemporaryDirectory()
    tempdir = Path(tempdir_obj.name).absolute()

    aptly = tempdir / "aptly"
    aptly.mkdir(parents=True)
    config = {"rootDir": str(aptly)}
    if aptly_conf.exists():
        aptly_conf.unlink()
    with aptly_conf.open("w") as f:
        json.dump(config, f)

    gnupg = tempdir / "gnugp"
    gnupg.mkdir(parents=True)
    os.chown(gnupg, 0, 0)
    gnupg.chmod(0o700)
    os.environ["GNUPGHOME"] = str(gnupg)

    try:
        yield
    finally:
        tempdir_obj.cleanup()
        aptly_conf.unlink()


@pytest.fixture()
def config(request):
    config_file = test_base / request.param
    with config_file.open("r", encoding="UTF-8") as f:
        config = toml.load(f)
    # TODO: remove yaml conversion
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="UTF-8", delete=False) as f:
            yaml.dump(config, f)
        yield f.name, config
    finally:
        Path(f.name).unlink()
