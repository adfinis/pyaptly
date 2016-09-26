"""Testing pyaptly"""
import contextlib
import logging
import os

import freezegun
import testfixtures

from pyaptly import (Command, SystemStateReader, call_output, main,
                     snapshot_spec_to_name)

from . import test

try:
    import unittest.mock as mock
except ImportError:  # pragma: no cover
    import mock


_test_base = os.path.dirname(
    os.path.abspath(__file__)
).encode("UTF-8")


@contextlib.contextmanager
def mock_subprocess():
    """Mock subprocess that no commands are executed"""
    call = mock.patch("subprocess.check_call")
    output = mock.patch("pyaptly.call_output")
    yield (call.start(), output.start())
    call.stop()
    output.stop()


def test_debug():
    """Test if debug is enabled with -d"""
    with mock_subprocess() as (_, gpg):
        gpg.side_effect = lambda _: ("", "")
        args = [
            '-d',
            '-c',
            os.path.join(_test_base, b'test01.yml').decode("UTF-8"),
            'mirror',
            'create'
        ]
        main(args)
        assert logging.getLogger().level == logging.DEBUG


def test_pretend():
    """Test if pretend is enabled with -p"""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish.yml",
    )) as (tyml, config):
        do_snapshot_create(config)
        args = [
            '-p',
            '-c',
            config,
            'publish',
            'create',
            'fakerepo01',
        ]
        main(args)
        state = SystemStateReader()
        state.read()
        assert set() == state.publishes
        assert {} == state.publish_map
        assert Command.pretend_mode


def test_mirror_create():
    """Test if createing mirrors works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"mirror-google.yml",
    )) as (tyml, config):
        args = [
            '-c',
            config,
            'mirror',
            'create'
        ]
        keys_added = []
        with testfixtures.LogCapture() as l:
            main(args)
            for rec in l.records:
                for arg in rec.args:
                    if isinstance(arg, list):
                        if arg[0] == "gpg":
                            keys_added.append(arg[7])
        assert len(keys_added) > 0
        assert len(keys_added) == len(set(keys_added)), (
            "Key multiple times added"
        )

        expect = set(tyml['mirror'].keys())
        state = SystemStateReader()
        state.read()
        assert state.mirrors == expect


def do_mirror_update(config):
    """Test if updating mirrors works."""
    args = [
        '-c',
        config,
        'mirror',
        'create'
    ]
    state = SystemStateReader()
    state.read()
    assert "fakerepo01" not in state.mirrors
    main(args)
    state.read()
    assert "fakerepo01" in state.mirrors
    args[3] = 'update'
    main(args)
    args = [
        'aptly',
        'mirror',
        'show',
    ]
    args01 = list(args)
    args01.append("fakerepo01")
    aptly_state = test.execute_and_parse_show_cmd(args01)
    assert aptly_state['number of packages'] == "2"


def test_mirror_update():
    """Test if updating mirrors works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"mirror-no-google.yml",
    )) as (tyml, config):
        do_mirror_update(config)


def test_mirror_update_inexistent():
    """Test if updating an inexistent mirror causes an error."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"mirror-no-google.yml",
    )) as (tyml, config):
        do_mirror_update(config)
        args = [
            '-c',
            config,
            'mirror',
            'update',
            'asdfasdf'
        ]
        error = False
        try:
            main(args)
        except ValueError:
            error = True
        assert error


def test_mirror_update_single():
    """Test if updating a single mirror works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"mirror-no-google.yml",
    )) as (tyml, config):
        do_mirror_update(config)
        args = [
            '-c',
            config,
            'mirror',
            'update',
            'fakerepo01'
        ]
        main(args)


def do_snapshot_create(config):
    """Test if createing snapshots works"""
    do_mirror_update(config)
    args = [
        '-c',
        config,
        'snapshot',
        'create'
    ]
    main(args)
    state = SystemStateReader()
    state.read()
    assert set(
        ['fakerepo01-20121010T0000Z', 'fakerepo02-20121006T0000Z']
    ).issubset(state.snapshots)
    return state


def test_snapshot_create_inexistent():
    """Test if creating an inexistent snapshot raises an error."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"snapshot.yml",
    )) as (tyml, config):
        do_mirror_update(config)
        args = [
            '-c',
            config,
            'snapshot',
            'create',
            'asdfasdf-%T',
        ]
        error = False
        try:
            main(args)
        except ValueError:
            error = True
        assert error


def test_snapshot_create_single():
    """Test if single snapshot create works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"snapshot.yml",
    )) as (tyml, config):
        do_mirror_update(config)
        args = [
            '-c',
            config,
            'snapshot',
            'create',
            'fakerepo01-%T',
        ]
        main(args)
        state = SystemStateReader()
        state.read()
        assert set(
            ['fakerepo01-20121010T0000Z']
        ).issubset(state.snapshots)


def test_snapshot_create_rotating():
    """Test if rotating snapshot create works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"snapshot-current.yml",
    )) as (tyml, config):
        do_mirror_update(config)
        args = [
            '-c',
            config,
            'snapshot',
            'create',
        ]
        main(args)
        state = SystemStateReader()
        state.read()
        assert set(
            [
                'fake-current',
                'fakerepo01-current',
                'fakerepo02-current',
            ]
        ).issubset(state.snapshots)


def test_snapshot_update_rotating():
    """Test if rotating snapshot update works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"snapshot-current.yml",
    )) as (tyml, config):
        do_snapshot_update_rotating(config)


def test_snapshot_update_twice_rotating():
    """Test if rotating snapshot update works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"snapshot-current.yml",
    )) as (tyml, config):
        do_snapshot_update_rotating(config)
        with freezegun.freeze_time("2012-11-10 10:10:10"):
            args = [
                '-c',
                config,
                'snapshot',
                'update',
            ]
            main(args)
            state = SystemStateReader()
            state.read()
            assert set(
                [
                    'fake-current',
                    'fakerepo01-current-rotated-20121010T1010Z',
                    'fakerepo02-current-rotated-20121010T1010Z',
                    'fakerepo01-current-rotated-20121110T1010Z',
                    'fakerepo02-current-rotated-20121110T1010Z',
                ]
            ).issubset(state.snapshots)
            expected = {
                u'fake-current': set([
                    u'fakerepo01-current', u'fakerepo02-current'
                ]),
                u'fake-current-rotated-20121010T1010Z': set([
                    u'fakerepo01-current',
                    u'fakerepo02-current'
                ]),
                u'fake-current-rotated-20121110T1010Z': set([
                    u'fakerepo01-current',
                    u'fakerepo02-current'
                ]),
                u'fakerepo01-current': set([]),
                u'fakerepo01-current-rotated-20121010T1010Z': set([]),
                u'fakerepo01-current-rotated-20121110T1010Z': set([]),
                u'fakerepo02-current': set([]),
                u'fakerepo02-current-rotated-20121010T1010Z': set([]),
                u'fakerepo02-current-rotated-20121110T1010Z': set([])
            }
            assert state.snapshot_map == expected


def do_snapshot_update_rotating(config):
    """Helper for rotating snapshot tests"""
    do_mirror_update(config)
    args = [
        '-c',
        config,
        'snapshot',
        'create',
    ]
    main(args)
    state = SystemStateReader()
    state.read()
    assert set(
        [
            'fake-current',
            'fakerepo01-current',
            'fakerepo02-current',
        ]
    ).issubset(state.snapshots)
    args = [
        '-c',
        config,
        'snapshot',
        'update',
    ]
    main(args)
    state.read()
    assert set(
        [
            'fake-current',
            'fakerepo01-current-rotated-20121010T1010Z',
            'fakerepo02-current-rotated-20121010T1010Z',
        ]
    ).issubset(state.snapshots)
    expected = {
        u'fake-current': set([
            u'fakerepo01-current', u'fakerepo02-current'
        ]),
        u'fake-current-rotated-20121010T1010Z': set([
            u'fakerepo01-current',
            u'fakerepo02-current'
        ]),
        u'fakerepo01-current': set([]),
        u'fakerepo01-current-rotated-20121010T1010Z': set([]),
        u'fakerepo02-current': set([]),
        u'fakerepo02-current-rotated-20121010T1010Z': set([]),
    }
    assert state.snapshot_map == expected


def test_snapshot_create_basic():
    """Test if snapshot create works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"snapshot.yml",
    )) as (tyml, config):
        state = do_snapshot_create(config)
        assert set(
            ['fakerepo01-20121010T0000Z', 'fakerepo02-20121006T0000Z']
        ) == state.snapshots


def test_snapshot_create_repo():
    """Test if repo snapshot create works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"snapshot_repo.yml",
    )) as (tyml, config):
        do_repo_create(config)
        args = [
            '-c',
            config,
            'snapshot',
            'create'
        ]
        main(args)
        state = SystemStateReader()
        state.read()
        assert set(
            ['centrify-latest']
        ).issubset(state.snapshots)
        return state


def test_snapshot_create_merge():
    """Test if snapshot merge create works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"snapshot_merge.yml",
    )) as (tyml, config):
        state = do_snapshot_create(config)
        assert set(
            [
                'fakerepo01-20121010T0000Z',
                'fakerepo02-20121006T0000Z',
                'superfake-20121010T0000Z'
            ]
        ) == state.snapshots
        expect = {
            'fakerepo01-20121010T0000Z': set([]),
            'fakerepo02-20121006T0000Z': set([]),
            'superfake-20121010T0000Z': set([
                'fakerepo01-20121010T0000Z',
                'fakerepo02-20121006T0000Z'
            ])
        }
        assert expect == state.snapshot_map


def test_snapshot_create_filter():
    """Test if snapshot filter create works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"snapshot_filter.yml",
    )) as (tyml, config):
        do_snapshot_create(config)
        data, _ = call_output([
            'aptly',
            'snapshot',
            'search',
            'filterfake01-20121010T0000Z',
            'Name (% *)'
        ])
        state = [x.strip() for x in data.split('\n') if x]
        expect = ['libhello_0.1-1_amd64']
        assert state == expect


def do_publish_create(config):
    """Test if creating publishes works."""
    do_snapshot_create(config)
    args = [
        '-c',
        config,
        'publish',
        'create'
    ]
    main(args)
    state = SystemStateReader()
    state.read()
    assert set(
        ['fakerepo02 main', 'fakerepo01 main']
    ) == state.publishes
    expect = {
        'fakerepo02 main': set(['fakerepo02-20121006T0000Z']),
        'fakerepo01 main': set(['fakerepo01-20121010T0000Z'])
    }
    assert expect == state.publish_map


def do_publish_create_rotating(config):
    """Test if creating publishes works."""
    do_snapshot_update_rotating(config)
    args = [
        '-c',
        config,
        'publish',
        'create'
    ]
    main(args)
    state = SystemStateReader()
    state.read()
    assert set([
        'fakerepo01/current stable',
        'fake/current stable',
        'fakerepo02/current stable',
    ]) == state.publishes
    expect = {
        u'fake/current stable': set([u'fake-current']),
        u'fakerepo01/current stable': set([u'fakerepo01-current']),
        u'fakerepo02/current stable': set([u'fakerepo02-current'])
    }
    assert expect == state.publish_map


def test_publish_create_single():
    """Test if creating a single publish works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish.yml",
    )) as (tyml, config):
        do_snapshot_create(config)
        args = [
            '-c',
            config,
            'publish',
            'create',
            'fakerepo01',
        ]
        main(args)
        state = SystemStateReader()
        state.read()
        assert set(
            ['fakerepo01 main']
        ) == state.publishes
        expect = {
            'fakerepo01 main': set(['fakerepo01-20121010T0000Z'])
        }
        assert expect == state.publish_map


def test_publish_create_inexistent():
    """Test if creating inexistent publish raises an error."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish.yml",
    )) as (tyml, config):
        do_snapshot_create(config)
        args = [
            '-c',
            config,
            'publish',
            'create',
            'asdfasdf',
        ]
        error = False
        try:
            main(args)
        except ValueError:
            error = True
        assert error


def test_publish_create_repo():
    """Test if creating repo publishes works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish_repo.yml",
    )) as (tyml, config):
        do_repo_create(config)
        args = [
            '-c',
            config,
            'publish',
            'create',
        ]
        main(args)
        args = [
            '-c',
            config,
            'publish',
            'update',
        ]
        main(args)
        state = SystemStateReader()
        state.read()
        assert set(
            ['centrify latest']
        ) == state.publishes
        assert {'centrify latest': set([])} == state.publish_map


def test_publish_create_basic():
    """Test if creating publishes works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish.yml",
    )) as (tyml, config):
        do_publish_create(config)


def test_publish_update_rotating():
    """Test if update rotating publishes works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish-current.yml",
    )) as (tyml, config):
        do_publish_create_rotating(config)
        with freezegun.freeze_time("2012-10-11 10:10:10"):
            args = [
                '-c',
                config,
                'publish',
                'update',
            ]
            main(args)
            state = SystemStateReader()
            state.read()
            expect = {
                u'fake/current stable': set([u'fake-current']),
                u'fakerepo01/current stable': set([u'fakerepo01-current']),
                u'fakerepo02/current stable': set([u'fakerepo02-current'])
            }
            assert expect == state.publish_map


def test_publish_snapshot_update_rotating():
    """Test if update rotating publishes via snapshot works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish-current.yml",
    )) as (tyml, config):
        do_publish_create_rotating(config)
        with freezegun.freeze_time("2012-10-11 10:10:10"):
            args = [
                '-c',
                config,
                'snapshot',
                'update',
            ]
            main(args)
            state = SystemStateReader()
            state.read()
            expect = {
                u'fake/current stable': set([u'fake-current']),
                u'fakerepo01/current stable': set([u'fakerepo01-current']),
                u'fakerepo02/current stable': set([u'fakerepo02-current'])
            }
            assert expect == state.publish_map


def test_publish_create_rotating():
    """Test if creating rotating publishes works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish-current.yml",
    )) as (tyml, config):
        do_publish_create_rotating(config)


def do_publish_create_republish(config):
    """Test if creating republishes works."""
    with testfixtures.LogCapture() as l:
        do_publish_create(config)
        found = False
        for rec in l.records:
            if rec.levelname == "CRITICAL":
                if "has been deferred" in rec.msg:
                    found = True
        assert found
    args = [
        '-c',
        config,
        'publish',
        'create',
    ]
    main(args)
    state = SystemStateReader()
    state.read()
    assert 'fakerepo01-stable main' in state.publishes


def test_publish_create_republish():
    """Test if creating republishes works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish_publish.yml",
    )) as (tyml, config):
        do_publish_create_republish(config)


def test_publish_update_republish():
    """Test if update republishes works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish_publish.yml",
    )) as (tyml, config):
        do_publish_create_republish(config)
        with freezegun.freeze_time("2012-10-11 10:10:10"):
            args = [
                '-c',
                config,
                'snapshot',
                'create',
            ]
            main(args)
            args = [
                '-c',
                config,
                'publish',
                'update',
            ]
            main(args)
        state = SystemStateReader()
        state.read()
        assert 'fakerepo01-stable main' in state.publishes
        # As you see fakerepo01-stable main points to the old snapshot
        # this is theoretically not correct, but it will be fixed with
        # the next call to publish update. Since we use this from a hourly cron
        # job it is no problem.
        # This can't be easily fixed and would need a rewrite of the
        # dependencies engine.
        expect = {
            'fakerepo01-stable main': set(['fakerepo01-20121010T0000Z']),
            'fakerepo02 main': set(['fakerepo02-20121006T0000Z']),
            'fakerepo01 main': set(['fakerepo01-20121011T0000Z'])
        }
        assert expect == state.publish_map


def test_publish_updating_basic():
    """Test if updating publishes works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"publish.yml",
    )) as (tyml, config):
        do_publish_create(config)
        with freezegun.freeze_time("2012-10-11 10:10:10"):
            args = [
                '-c',
                config,
                'snapshot',
                'create'
            ]
            main(args)
            args = [
                '-c',
                config,
                'publish',
                'update'
            ]
            main(args)
            state = SystemStateReader()
            state.read()
            expect = set([
                'archived-fakerepo01-20121011T1010Z',
                'fakerepo01-20121011T0000Z',
                'fakerepo02-20121006T0000Z',
                'fakerepo01-20121010T0000Z',
            ])
            assert expect == state.snapshots
            expect = {
                'fakerepo02 main': set(['fakerepo02-20121006T0000Z']),
                'fakerepo01 main': set(['fakerepo01-20121011T0000Z'])
            }
            assert expect == state.publish_map


def do_repo_create(config):
    """Test if creating repositories works."""
    args = [
        '-c',
        config,
        'repo',
        'create'
    ]
    main(args)
    state = SystemStateReader()
    state.read()
    call_output([
        'aptly',
        'repo',
        'add',
        'centrify',
        'vagrant/hellome_0.1-1_amd64.deb'
    ])
    assert set(['centrify']) == state.repos


def test_repo_create_single():
    """Test if creating a single repo works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"repo.yml",
    )) as (tyml, config):
        args = [
            '-c',
            config,
            'repo',
            'create',
            'centrify',
        ]
        main(args)
        state = SystemStateReader()
        state.read()
        assert set(['centrify']) == state.repos


def test_repo_create_inexistent():
    """Test if creating an inexistent repo causes an error."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"repo.yml",
    )) as (tyml, config):
        args = [
            '-c',
            config,
            'repo',
            'create',
            'asdfasdf',
        ]
        error = False
        try:
            main(args)
        except ValueError:
            error = True
        assert error


def test_repo_create_basic():
    """Test if creating repositories works."""
    with test.clean_and_config(os.path.join(
            _test_base,
            b"repo.yml",
    )) as (tyml, config):
        do_repo_create(config)


def test_snapshot_spec_as_dict():
    "Test various snapshot formats for snapshot_spec_to_name()"

    snap_string = 'snapshot-foo'
    snap_dict = {
        'name': 'foo'
    }

    cfg = {
        'snapshot': {
            'foo': {},
        }
    }

    assert snapshot_spec_to_name(cfg, snap_string) == snap_string
    assert snapshot_spec_to_name(cfg, snap_dict) == 'foo'
