"""Test snapshot functionality."""
import pytest

from .. import main, state_reader, util


@pytest.mark.parametrize("config", ["snapshot.toml"], indirect=True)
def test_snapshot_create_basic(config, snapshot_create):
    """Test if snapshot create works."""
    assert (
        set(["fakerepo01-20121010T0000Z", "fakerepo02-20121006T0000Z"])
        == snapshot_create.snapshots
    )


@pytest.mark.parametrize("config", ["snapshot.toml"], indirect=True)
@pytest.mark.parametrize("exists", [True, False])
def test_snapshot_create(mirror_update, config, exists):
    """Test if creating an (in)existent snapshot raises an (no) error."""
    mirror = "asdfasdf-%T"
    if exists:
        mirror = "fakerepo01-%T"
    args = ["-c", config, "snapshot", "create", mirror]
    error = False
    try:
        main.main(args)
    except ValueError:
        error = True
    assert error != exists


@pytest.mark.parametrize("config", ["snapshot-current.toml"], indirect=True)
def test_snapshot_create_rotating(mirror_update, config):
    """Test if rotating snapshot create works."""
    args = ["-c", config, "snapshot", "create"]
    main.main(args)
    state = state_reader.SystemStateReader()
    state.read()
    assert set(
        [
            "fake-current",
            "fakerepo01-current",
            "fakerepo02-current",
        ]
    ).issubset(state.snapshots)


@pytest.mark.parametrize("config", ["snapshot-current.toml"], indirect=True)
def test_snapshot_update_rotating(snapshot_update_rotating):
    """Test snapshot update rotating."""
    pass


@pytest.mark.parametrize("config", ["snapshot-current.toml"], indirect=True)
def test_snapshot_update_threetimes_rotating(snapshot_update_rotating, config, freeze):
    """Test if rotating snapshot update works."""
    freeze.move_to("2012-10-11 10:10:10")
    args = [
        "-c",
        config,
        "snapshot",
        "update",
    ]
    main.main(args)
    state = state_reader.SystemStateReader()
    state.read()
    assert set(
        [
            "fake-current",
            "fakerepo01-current-rotated-20121010T1010Z",
            "fakerepo02-current-rotated-20121010T1010Z",
            "fakerepo01-current-rotated-20121011T1010Z",
            "fakerepo02-current-rotated-20121011T1010Z",
        ]
    ).issubset(state.snapshots)
    expected = {
        "fake-current": set(["fakerepo01-current", "fakerepo02-current"]),
        "fake-current-rotated-20121010T1010Z": set(
            [
                "fakerepo01-current-rotated-20121010T1010Z",
                "fakerepo02-current-rotated-20121010T1010Z",
            ]
        ),
        "fake-current-rotated-20121011T1010Z": set(
            [
                "fakerepo01-current-rotated-20121011T1010Z",
                "fakerepo02-current-rotated-20121011T1010Z",
            ]
        ),
        "fakerepo01-current": set([]),
        "fakerepo01-current-rotated-20121010T1010Z": set([]),
        "fakerepo01-current-rotated-20121011T1010Z": set([]),
        "fakerepo02-current": set([]),
        "fakerepo02-current-rotated-20121010T1010Z": set([]),
        "fakerepo02-current-rotated-20121011T1010Z": set([]),
    }
    assert state.snapshot_map == expected

    freeze.move_to("2012-10-12 10:10:10")
    args = [
        "-c",
        config,
        "snapshot",
        "update",
    ]
    main.main(args)
    state = state_reader.SystemStateReader()
    state.read()
    assert set(
        [
            "fake-current",
            "fakerepo01-current-rotated-20121011T1010Z",
            "fakerepo02-current-rotated-20121011T1010Z",
            "fakerepo01-current-rotated-20121012T1010Z",
            "fakerepo02-current-rotated-20121012T1010Z",
        ]
    ).issubset(state.snapshots)
    expected = {
        "fake-current": set(["fakerepo01-current", "fakerepo02-current"]),
        "fake-current-rotated-20121010T1010Z": set(
            [
                "fakerepo01-current-rotated-20121010T1010Z",
                "fakerepo02-current-rotated-20121010T1010Z",
            ]
        ),
        "fake-current-rotated-20121011T1010Z": set(
            [
                "fakerepo01-current-rotated-20121011T1010Z",
                "fakerepo02-current-rotated-20121011T1010Z",
            ]
        ),
        "fake-current-rotated-20121012T1010Z": set(
            [
                "fakerepo01-current-rotated-20121012T1010Z",
                "fakerepo02-current-rotated-20121012T1010Z",
            ]
        ),
        "fakerepo01-current": set([]),
        "fakerepo01-current-rotated-20121010T1010Z": set([]),
        "fakerepo01-current-rotated-20121011T1010Z": set([]),
        "fakerepo01-current-rotated-20121012T1010Z": set([]),
        "fakerepo02-current": set([]),
        "fakerepo02-current-rotated-20121010T1010Z": set([]),
        "fakerepo02-current-rotated-20121011T1010Z": set([]),
        "fakerepo02-current-rotated-20121012T1010Z": set([]),
    }
    assert state.snapshot_map == expected


@pytest.mark.parametrize("config", ["snapshot-repo.toml"], indirect=True)
def test_snapshot_create_repo(config, repo_create):
    """Test if repo snapshot create works."""
    args = ["-c", config, "snapshot", "create"]
    main.main(args)
    state = state_reader.SystemStateReader()
    state.read()
    assert set(["centrify-latest"]).issubset(state.snapshots)
    return state


@pytest.mark.parametrize("config", ["snapshot-merge.toml"], indirect=True)
def test_snapshot_create_merge(config, snapshot_create):
    """Test if snapshot merge create works."""
    assert (
        set(
            [
                "fakerepo01-20121010T0000Z",
                "fakerepo02-20121006T0000Z",
                "superfake-20121010T0000Z",
            ]
        )
        == snapshot_create.snapshots
    )
    expect = {
        "fakerepo01-20121010T0000Z": set([]),
        "fakerepo02-20121006T0000Z": set([]),
        "superfake-20121010T0000Z": set(
            ["fakerepo01-20121010T0000Z", "fakerepo02-20121006T0000Z"]
        ),
    }
    assert expect == snapshot_create.snapshot_map


@pytest.mark.parametrize("config", ["snapshot-filter.toml"], indirect=True)
def test_snapshot_create_filter(config, snapshot_create):
    """Test if snapshot filter create works."""
    result = util.run_command(
        ["aptly", "snapshot", "search", "filterfake01-20121010T0000Z", "Name (% *)"],
        stdout=util.PIPE,
    )
    state = [x.strip() for x in result.stdout.split("\n") if x]
    expect = ["libhello_0.1-1_amd64"]
    assert state == expect
