"""Tools for testing pyaptly"""

import codecs
import contextlib
import os
import shutil
import subprocess
import sys
import tempfile

import freezegun
import pytest
import six
import yaml

import pyaptly

hypothesis_min_ver = pytest.mark.skipif(
    sys.version_info < (2, 7),
    reason="requires python2.7"
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
        main_yml = dict(yaml.load(f.read()))
    merges = []
    if "merge" in main_yml:
        for merge_path in main_yml['merge']:
            path = os.path.join(
                directory,
                merge_path.encode("UTF-8"),
            )
            merges.append(read_yml(path))
        del main_yml['merge']
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


def execute_and_parse_show_cmd(args):
    """Executes and parses a aptly show command.

    :param args: Command to execute
    :type  args: list
    """
    result = {}
    show, _ = pyaptly.call_output(args)
    for line in show.split('\n'):
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
    if 'mirror' in input_:
        for mirror in input_['mirror'].values():
            if 'components' not in mirror:
                mirror['components'] = "main"
            if 'distribution' not in mirror:
                mirror['distribution'] = "main"
    if 'publish' in input_:
        for publish in input_['publish'].values():
            for item in publish:
                if 'components' not in item:
                    item['components'] = "main"
                if 'distribution' not in item:
                    item['distribution'] = "main"
    try:
        file_ = codecs.getwriter("UTF-8")(
            tempfile.NamedTemporaryFile(delete=False)
        )
        yaml.dump(input_, file_)
    finally:
        file_.close()
    return (input_, file_.name)


@contextlib.contextmanager
def clean_and_config(test_input, freeze="2012-10-10 10:10:10"):
    """Remove aptly file and create a input config file to run pyaptly with.

    Test input should be minimal and extended/tranformed in create_config.

    :param test_input: Path to test data input file
    :type  test_input: str
    :param     freeze: ISO8601 date string used to set the date/time for the
                       test
    :param     freeze: str
    :rtype:            (dict, str)
    """
    old_home = environb[b'HOME']
    if b"pyaptly" not in old_home and b"vagrant" not in old_home:  # pragma: no cover  # noqa
        raise ValueError(
            "Not safe to test here. Either you haven't set HOME to the "
            "repository path %s. Or you havn't checked out the repository "
            "as pyaptly." % os.path.abspath('.')
        )
    file_ = None
    new_home = None
    try:
        new_home = os.path.join(old_home, b".work")
        try:
            shutil.rmtree(new_home)
        except OSError:  # pragma: no cover
            pass
        os.mkdir(new_home)
        environb[b'HOME'] = new_home
        with freezegun.freeze_time(freeze):
            try:
                shutil.rmtree("%s/.aptly" % new_home.decode("UTF-8"))
            except OSError:  # pragma: no cover
                pass
            try:
                shutil.rmtree("%s/.gnupg" % new_home.decode("UTF-8"))
            except OSError:  # pragma: no cover
                pass
            try:
                os.unlink('%s/.gnupg/S.gpg-agent' % old_home.decode("UTF-8"))
            except OSError:
                pass
            shutil.copytree(
                "%s/.gnupg/" % old_home.decode("UTF-8"),
                "%s/.gnupg" % new_home.decode("UTF-8")
            )
            input_, file_ = create_config(test_input)
            try:
                subprocess.check_call([
                    b'gpg',
                    b'--keyring',
                    b'trustedkeys.gpg',
                    b'--batch',
                    b'--yes',
                    b'--delete-key',
                    b'7FAC5991',
                ])
            except subprocess.CalledProcessError:  # pragma: no cover
                pass
            yield (input_, file_)
    finally:
        environb[b'HOME'] = old_home
        if file_:
            os.unlink(file_)
        if new_home:
            shutil.rmtree(new_home)
