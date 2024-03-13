"""Create and update snapshots in aptly."""

import datetime
import logging
from typing import Optional

from . import command, date_tools, publish, state_reader, types

lg = logging.getLogger(__name__)

back_reference_map = {
    "current": 0,
    "previous": 1,
}


def snapshot(cfg, args):
    """Create snapshot commands, orders and executes them.

    :param  cfg: The configuration toml as dict
    :type   cfg: dict
    :param args: The command-line arguments read with :py:mod:`argparse`
    :type  args: namespace
    """
    lg.debug("Snapshots to create: %s", cfg["snapshot"].keys())

    cmd_snapshot: types.SnapshotCommand = cmd_snapshot_update
    if args.task == "create":
        cmd_snapshot = cmd_snapshot_create

    if args.snapshot_name == "all":
        commands = [
            cmd
            for snapshot_name, snapshot_config in cfg["snapshot"].items()
            for cmd in cmd_snapshot(cfg, snapshot_name, snapshot_config)
        ]

        if args.debug:  # pragma: no cover
            dot_file = "/tmp/commands.dot"
            with open(dot_file, "w", encoding="UTF-8") as fh_dot:
                fh_dot.write(command.Command.command_list_to_digraph(commands))
            lg.info("Wrote command dependency tree graph to %s", dot_file)

        if len(commands) > 0:
            for cmd in command.Command.order_commands(
                commands, state_reader.state.has_dependency
            ):
                cmd.execute()

    else:
        if args.snapshot_name in cfg["snapshot"]:
            commands = cmd_snapshot(
                cfg, args.snapshot_name, cfg["snapshot"][args.snapshot_name]
            )

            if len(commands) > 0:
                for cmd in command.Command.order_commands(
                    commands, state_reader.state.has_dependency
                ):
                    cmd.execute()

        else:
            raise ValueError(
                "Requested snapshot is not defined in config file: %s"
                % (args.snapshot_name)
            )


def snapshot_spec_to_name(cfg, snapshot):
    """Convert a given snapshot short spec to a name.

    A short spec is a value that may either be a string or a dict.

    If it's a string, everything is fine and we just use that as
    a snapshot name.

    However if it's a dict, we assume it has the following keys:

     * name: template for the snapshot
     * timestamp: information on how to generate the timestamp.

    For further information regarding the timestamp's data structure,
    consult the documentation of expand_timestamped_name().

    :param      cfg: Complete yaml config
    :type       cfg: dict
    :param snapshot: Config of the snapshot
    :type  snapshot: dict
    """
    delta = datetime.timedelta(seconds=1)
    if hasattr(snapshot, "items"):
        name = snapshot["name"]
        if "timestamp" not in snapshot:
            return name

        ts = snapshot["timestamp"]
        back_ref = back_reference_map.get(ts)
        if back_ref is None:
            back_ref = int(ts)
        reference = cfg["snapshot"][name]

        timestamp = datetime.datetime.now()
        for _ in range(back_ref + 1):
            timestamp = date_tools.round_timestamp(reference["timestamp"], timestamp)
            timestamp -= delta

        timestamp += delta
        return name.replace("%T", date_tools.format_timestamp(timestamp))
    else:  # pragma: no cover
        return snapshot


def dependents_of_snapshot(snapshot_name):
    """Yield a flat list of dependents from the current state_reader.state.

    :rtype: generator
    """
    for dependent in state_reader.state.snapshot_map.get(snapshot_name, []):
        yield dependent
        # TODO I fixed a bug, but there is no test. We do not test recursive dependants
        yield from dependents_of_snapshot(dependent)


def rotate_snapshot(cfg, snapshot_name):
    """Create a command to rotate a snapshot.

    In order to be able to update a current publish.

    :param           cfg: pyaptly config
    :type            cfg: dict
    :param snapshot_name: the snapshot to rotate
    :type  snapshot_name: str
    """
    rotated_name = cfg["snapshot"][snapshot_name].get(
        "rotate_via",
        "%s-rotated-%s"
        % (snapshot_name, date_tools.format_timestamp(datetime.datetime.now())),
    )

    # First, verify that our snapshot environment is in a sane state_reader.state.
    # Fixing the environment is not currently our task.

    if rotated_name in state_reader.state.snapshots:  # pragma: no cover
        raise Exception(
            "Cannot update snapshot %s - rotated name %s already exists"
            % (snapshot_name, rotated_name)
        )

    cmd = command.Command(["aptly", "snapshot", "rename", snapshot_name, rotated_name])

    cmd.provide("virtual", rotated_name)
    return cmd


def cmd_snapshot_update(
    cfg: dict, snapshot_name: str, snapshot_config: dict
) -> list[command.Command]:
    """Create commands to update all rotating snapshots.

    :param             cfg: pyaptly config
    :type              cfg: dict
    :param   snapshot_name: Name of the snapshot to update/rotate
    :type    snapshot_name: str
    :param snapshot_config: Configuration of the snapshot from the toml file.
    :type  snapshot_config: dict
    """
    # To update a snapshot, we need to do roughly the following steps:
    # 1) Rename the current snapshot and all snapshots that depend on it
    # 2) Create new version of the snapshot and all snapshots that depend on it
    # 3) Recreate all renamed snapshots
    # 4) Update / switch-over publishes
    # 5) Remove the rotated temporary snapshots

    if "%T" in snapshot_name:  # pragma: no cover
        # Timestamped snapshots are never rotated by design.
        return []

    affected_snapshots = [snapshot_name]
    affected_snapshots.extend(list(dependents_of_snapshot(snapshot_name)))

    # TODO: rotated snapshots should be identified by configuration option, not
    # just by "not being timestamped

    rename_cmds = [rotate_snapshot(cfg, snap) for snap in affected_snapshots]

    # The "intermediate" command causes the state reader to refresh.  At the
    # same time, it provides a collection point for dependency handling.
    intermediate = command.FunctionCommand(state_reader.state.read)
    intermediate.provide("virtual", "all-snapshots-rotated")

    for cmd in rename_cmds:
        # Ensure that our "intermediate" pseudo command comes after all
        # the rename commands, by ensuring it depends on all their "virtual"
        # provided items.
        cmd_vprovides = [
            provide for ptype, provide in cmd.get_provides() if ptype == "virtual"
        ]
        for provide in cmd_vprovides:
            intermediate.require("virtual", provide)

    # Same as before - create a focal point to "collect" dependencies
    # after the snapshots have been rebuilt. Also reload state once again
    intermediate2 = command.FunctionCommand(state_reader.state.read)
    intermediate2.provide("virtual", "all-snapshots-rebuilt")

    create_cmds = []
    for _ in affected_snapshots:
        # Well.. there's normally just one, but since we need interface
        # consistency, cmd_snapshot_create() returns a list. And since it
        # returns a list, we may just as well future-proof it and loop instead
        # of assuming it's going to be a single entry (and fail horribly if
        # this assumption changes in the future).
        for create_cmd in cmd_snapshot_create(
            cfg, snapshot_name, cfg["snapshot"][snapshot_name], ignore_existing=True
        ):
            # enforce cmd to run after the refresh, and thus also
            # after all the renames
            create_cmd.require("virtual", "all-snapshots-rotated")

            # Evil hack - we must do the dependencies ourselves, to avoid
            # getting a circular graph
            create_cmd._requires = set(
                [
                    (type_, req)
                    for type_, req in create_cmd._requires
                    if type_ != "snapshot"
                ]
            )

            create_cmd.provide("virtual", "readyness-for-%s" % snapshot_name)
            for follower in dependents_of_snapshot(snapshot_name):
                create_cmd.require("virtual", "readyness-for-%s" % follower)

            # "Focal point" - make intermediate2 run after all the commands
            # that re-create the snapshots
            create_cmd.provide("virtual", "rebuilt-%s" % snapshot_name)
            intermediate2.require("virtual", "rebuilt-%s" % snapshot_name)

            create_cmds.append(create_cmd)

    # At this point, snapshots have been renamed, then recreated.
    # After each of the steps, the system state has been re-read.
    # So now, we're left with updating the publishes.

    def is_publish_affected(name, publish_info):
        if (
            "%s %s" % (name, publish_info["distribution"])
            in state_reader.state.publishes
        ):
            try:
                for snap in publish_info["snapshots"]:
                    snap_name = snapshot_spec_to_name(cfg, snap)
                    if snap_name in affected_snapshots:
                        return True
            except KeyError:  # pragma: no cover
                lg.debug(
                    (
                        "publish_info endpoint %s is not affected because it has no "
                        "snapshots defined"
                    )
                    % name
                )
                return False
        return False

    if "publish" in cfg:
        all_publish_commands = [
            publish.publish_cmd_update(
                cfg, publish_name, publish_conf_entry, ignore_existing=True
            )
            for publish_name, publish_conf in cfg["publish"].items()
            for publish_conf_entry in publish_conf
            if publish_conf_entry.get("automatic-update", "false") is True
            if is_publish_affected(publish_name, publish_conf_entry)
        ]
    else:
        all_publish_commands = []

    republish_cmds = [c for c in all_publish_commands if c]

    # Ensure that the republish commands run AFTER the snapshots are rebuilt
    for cmd in republish_cmds:
        cmd.require("virtual", "all-snapshots-rebuilt")

    # TODO:
    # - We need to cleanup all the rotated snapshots after the publishes are
    #   rebuilt
    # - Filter publishes, so only the non-timestamped publishes are rebuilt

    return rename_cmds + create_cmds + republish_cmds + [intermediate, intermediate2]


def cmd_snapshot_create(
    cfg: dict,
    snapshot_name: str,
    snapshot_config: dict,
    ignore_existing: Optional[bool] = False,
) -> list[command.Command]:
    """Create a snapshot create command to be ordered and executed later.

    :param             cfg: pyaptly config
    :type              cfg: dict
    :param   snapshot_name: Name of the snapshot to create
    :type    snapshot_name: str
    :param snapshot_config: Configuration of the snapshot from the toml file.
    :type  snapshot_config: dict
    :param ignore_existing: Optional, defaults to False. If set to True, still
                            return a command object even if the requested
                            snapshot already exists
    :type  ignore_existing: dict

    :rtype: command.Command
    """
    # TODO: extract possible timestamp component
    # and generate *actual* snapshot name

    snapshot_name = date_tools.expand_timestamped_name(snapshot_name, snapshot_config)

    if snapshot_name in state_reader.state.snapshots and not ignore_existing:
        return []

    default_aptly_cmd = ["aptly", "snapshot", "create"]
    default_aptly_cmd.append(snapshot_name)
    default_aptly_cmd.append("from")

    if "mirror" in snapshot_config:
        cmd = command.Command(default_aptly_cmd + ["mirror", snapshot_config["mirror"]])
        cmd.provide("snapshot", snapshot_name)
        cmd.require("mirror", snapshot_config["mirror"])
        return [cmd]

    elif "repo" in snapshot_config:
        cmd = command.Command(default_aptly_cmd + ["repo", snapshot_config["repo"]])
        cmd.provide("snapshot", snapshot_name)
        cmd.require("repo", snapshot_config["repo"])
        return [cmd]

    elif "filter" in snapshot_config:
        cmd = command.Command(
            [
                "aptly",
                "snapshot",
                "filter",
                snapshot_spec_to_name(cfg, snapshot_config["filter"]["source"]),
                snapshot_name,
                snapshot_config["filter"]["query"],
            ]
        )
        cmd.provide("snapshot", snapshot_name)
        cmd.require(
            "snapshot", snapshot_spec_to_name(cfg, snapshot_config["filter"]["source"])
        )
        return [cmd]

    elif "merge" in snapshot_config:
        cmd = command.Command(
            [
                "aptly",
                "snapshot",
                "merge",
                snapshot_name,
            ]
        )
        cmd.provide("snapshot", snapshot_name)

        for source in snapshot_config["merge"]:
            source_name = snapshot_spec_to_name(cfg, source)
            cmd.append(source_name)
            cmd.require("snapshot", source_name)

        return [cmd]

    else:  # pragma: no cover
        raise ValueError(
            "Don't know how to handle snapshot config: %s" % (snapshot_config)
        )


def clone_snapshot(origin, destination):
    """Create a clone snapshot command with dependencies.

    To be ordered and executed later.

    :param      origin: The snapshot to clone
    :type       origin: str
    :param destination: The new name of the snapshot
    :type  destination: str
    """
    cmd = command.Command(["aptly", "snapshot", "merge", destination, origin])
    cmd.provide("snapshot", destination)
    cmd.require("snapshot", origin)
    return cmd
