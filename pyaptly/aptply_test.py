"""Testing pyaptly"""
import logging
import os

from pyaptly import main

try:
    import unittest.mock as mock
except ImportError:
    import mock


_test_base = os.path.dirname(
    os.path.abspath(__file__)
)


def mock_subprocess():
    """Mock subprocess that no commands are executed"""
    return mock.patch("subprocess.check_call")


def test_debug():
    """Test if debug is enabled with -d"""
    with mock_subprocess():
        args = [
            '-d',
            '-c',
            os.path.join(_test_base, 'test01.yml'),
            'mirror',
            'create'
        ]
        main(args)
        assert logging.getLogger().level == logging.DEBUG


def test_mirrors():
    """Test if mirrors are created as defined in the yaml file"""
    with mock_subprocess() as cc:
        args = [
            '-c',
            os.path.join(_test_base, 'test01.yml'),
            'mirror',
            'create'
        ]
        main(args)
        assert logging.getLogger().level == logging.CRITICAL
        arglist = [list(a) for a in cc.call_args_list]
        # import pprint
        # pprint.pprint(arglist, width=1)
        expected = [
            [(['aptly',
               'mirror',
               'create',
               '-with-sources',
               '-with-udebs',
               '-architectures=amd64,i386',
               'trusty-updates',
               'http://ch.archive.ubuntu.com/ubuntu/',
               'trusty-updates',
               'main',
               'multiverse',
               'restricted',
               'universe'],),
             {}],
            [(['aptly',
               'mirror',
               'create',
               '-with-sources',
               '-with-udebs',
               '-architectures=amd64,i386',
               'trusty-backports',
               'http://ch.archive.ubuntu.com/ubuntu/',
               'trusty-backports',
               'main',
               'multiverse',
               'restricted',
               'universe'],),
             {}],
            [(['aptly',
               'mirror',
               'create',
               '-with-sources',
               '-with-udebs',
               '-architectures=amd64,i386',
               'trusty',
               'http://ch.archive.ubuntu.com/ubuntu/',
               'trusty',
               'main',
               'multiverse',
               'restricted',
               'universe'],),
             {}]
        ]
        assert arglist == expected


def test_one_mirror():
    """Test if mirror is created as defined in the yaml file"""
    with mock_subprocess() as cc:
        args = [
            '-c',
            os.path.join(_test_base, 'test01.yml'),
            'mirror',
            'create',
            'trusty-backports',
        ]
        main(args)
        assert logging.getLogger().level == logging.CRITICAL
        arglist = [list(a) for a in cc.call_args_list]
        # import pprint
        # pprint.pprint(arglist, width=1)
        expected = [
            [(['aptly',
               'mirror',
               'create',
               '-with-sources',
               '-with-udebs',
               '-architectures=amd64,i386',
               'trusty-backports',
               'http://ch.archive.ubuntu.com/ubuntu/',
               'trusty-backports',
               'main',
               'multiverse',
               'restricted',
               'universe'],),
             {}],
        ]
        assert arglist == expected


def test_undef_mirror():
    """Test if ValueError is risen on undef mirror"""
    with mock_subprocess():
        args = [
            '-c',
            os.path.join(_test_base, 'test01.yml'),
            'mirror',
            'create',
            'asdfasdfjlkasjd',
        ]
        value_error = False
        try:
            main(args)
        except ValueError:
            value_error = True
        assert value_error


def test_snapshots():
    """Test if snapshots are created as defined in the yaml file"""
    with mock_subprocess() as cc:
        args = [
            '-c',
            os.path.join(_test_base, 'test01.yml'),
            'snapshot',
            'create'
        ]
        main(args)
        arglist = [list(a) for a in cc.call_args_list]
        # import pprint
        # pprint.pprint(arglist, width=1)
        expected = [
            [(['aptly',
               'snapshot',
               'create',
               'trusty-latest',
               'from',
               'mirror',
               'trusty-updates'],),
             {}],
            [(['aptly',
               'snapshot',
               'create',
               'trusty-backports-latest',
               'from',
               'mirror',
               'trusty-backports'],),
             {}],
            [(['aptly',
               'snapshot',
               'create',
               'my-repo-latest',
               'from',
               'repo',
               'my-repo'],),
             {}],
        ]
        assert arglist == expected


def test_one_snapshot():
    """Test if the snapshot is created as defined in the yaml file"""
    with mock_subprocess() as cc:
        args = [
            '-c',
            os.path.join(_test_base, 'test01.yml'),
            'snapshot',
            'create',
            'trusty-latest',
        ]
        main(args)
        arglist = [list(a) for a in cc.call_args_list]
        # import pprint
        # pprint.pprint(arglist, width=1)
        expected = [
            [(['aptly',
               'snapshot',
               'create',
               'trusty-latest',
               'from',
               'mirror',
               'trusty-updates'],),
             {}],
        ]
        assert arglist == expected


def test_undef_snapshot():
    """Test if ValueError is risen on undefined snapshot"""
    with mock_subprocess():
        args = [
            '-c',
            os.path.join(_test_base, 'test01.yml'),
            'snapshot',
            'create',
            'asdlfkjasldkjf',
        ]
        value_error = False
        try:
            main(args)
        except ValueError:
            value_error = True
        assert value_error
