"""Publish snapshots in aptly."""
import datetime
import logging
import re

from . import command, date_tools, snapshot, state_reader, util

lg = logging.getLogger(__name__)


def publish(cfg, args):
    """Create publish commands, orders and executes them.

    :param  cfg: The configuration yml as dict
    :type   cfg: dict
    :param args: The command-line arguments read with :py:mod:`argparse`
    :type  args: namespace
    """
    lg.debug("Publishes to create / update: %s", cfg["publish"])

    # aptly publish snapshot -components ... -architectures ... -distribution
    # ... -origin Ubuntu trusty-stable ubuntu/stable

    publish_cmds = {
        "create": publish_cmd_create,
        "update": publish_cmd_update,
    }

    cmd_publish = publish_cmds[args.task]

    if args.publish_name == "all":
        commands = [
            cmd_publish(cfg, publish_name, publish_conf_entry)
            for publish_name, publish_conf in cfg["publish"].items()
            for publish_conf_entry in publish_conf
            if publish_conf_entry.get("automatic-update", "false") is True
        ]

        for cmd in command.Command.order_commands(
            commands, state_reader.state.has_dependency
        ):
            cmd.execute()

    else:
        if args.publish_name in cfg["publish"]:
            commands = [
                cmd_publish(cfg, args.publish_name, publish_conf_entry)
                for publish_conf_entry in cfg["publish"][args.publish_name]
            ]
            for cmd in command.Command.order_commands(
                commands, state_reader.state.has_dependency
            ):
                cmd.execute()
        else:
            raise ValueError(
                "Requested publish is not defined in config file: %s"
                % (args.publish_name)
            )


def publish_cmd_update(cfg, publish_name, publish_config, ignore_existing=False):
    """Create a publish command with its dependencies.

    To be ordered and executed later.

    :param            cfg: pyaptly config
    :type             cfg: dict
    :param   publish_name: Name of the publish to update
    :type    publish_name: str
    :param publish_config: Configuration of the publish from the yml file.
    :type  publish_config: dict
    """
    publish_cmd = ["aptly", "publish"]
    options = []
    args = [publish_config["distribution"], publish_name]

    if "skip-contents" in publish_config and publish_config["skip-contents"]:
        options.append("-skip-contents=true")

    if "repo" in publish_config:
        publish_cmd.append("update")
        return command.Command(publish_cmd + options + args)

    publish_fullname = "%s %s" % (publish_name, publish_config["distribution"])
    current_snapshots = state_reader.state.publish_map[publish_fullname]
    if "snapshots" in publish_config:
        snapshots_config = publish_config["snapshots"]
        new_snapshots = [
            snapshot.snapshot_spec_to_name(cfg, snap) for snap in snapshots_config
        ]
    elif "publish" in publish_config:
        conf_value = publish_config["publish"]
        snapshots_config = []
        ref_publish_name, distribution = conf_value.split(" ")
        for publish in cfg["publish"][ref_publish_name]:
            if publish["distribution"] == distribution:
                snapshots_config.extend(publish["snapshots"])
                break
        new_snapshots = list(state_reader.state.publish_map[conf_value])
    else:  # pragma: no cover
        raise ValueError(
            "No snapshot references configured in publish %s" % publish_name
        )

    if set(new_snapshots) == set(current_snapshots) and not ignore_existing:
        # Already pointing to the newest snapshot, nothing to do
        return
    components = util.unit_or_list_to_list(publish_config["components"])

    for snap in snapshots_config:
        # snap may be a plain name or a dict..
        if hasattr(snap, "items"):
            # Dict mode - only here can we even have an archive option
            archive = snap.get("archive-on-update", None)

            if archive:
                # Replace any timestamp placeholder with the current
                # date/time.  Note that this is NOT rounded, as we want to
                # know exactly when the archival happened.
                archive = archive.replace(
                    "%T", date_tools.format_timestamp(datetime.datetime.now())
                )
                if archive in state_reader.state.snapshots:  # pragma: no cover
                    continue
                prefix_to_search = re.sub("%T$", "", snap["name"])

                current_snapshot = [
                    snap_name
                    for snap_name in sorted(current_snapshots, key=lambda x: -len(x))
                    if snap_name.startswith(prefix_to_search)
                ][0]

                snapshot.clone_snapshot(current_snapshot, archive).execute()

    publish_cmd.append("switch")
    options.append("-component=%s" % ",".join(components))

    if "skip-contents" in publish_config and publish_config["skip-contents"]:
        options.append("-skip-contents=true")

    return command.Command(publish_cmd + options + args + new_snapshots)


def publish_cmd_create(cfg, publish_name, publish_config, ignore_existing=False):
    """Create a publish command with its dependencies.

    To be ordered and executed later.

    :param            cfg: pyaptly config
    :type             cfg: dict
    :param   publish_name: Name of the publish to create
    :type    publish_name: str
    :param publish_config: Configuration of the publish from the yml file.
    :type  publish_config: dict
    """
    publish_fullname = "%s %s" % (publish_name, publish_config["distribution"])
    if publish_fullname in state_reader.state.publishes and not ignore_existing:
        # Nothing to do, publish already created
        return

    publish_cmd = ["aptly", "publish"]
    options = []
    source_args = []
    endpoint_args = [publish_name]

    has_source = False
    num_sources = 0

    for conf, conf_value in publish_config.items():
        if conf == "skip-contents":
            if conf_value:
                options.append("-skip-contents=true")
        elif conf == "architectures":  # pragma: no cover
            options.append(
                "-architectures=%s" % ",".join(util.unit_or_list_to_list(conf_value))
            )
        elif conf == "components":
            components = util.unit_or_list_to_list(conf_value)
            options.append("-component=%s" % ",".join(components))
        elif conf == "label":  # pragma: no cover
            options.append("-label=%s" % conf_value)
        elif conf == "origin":  # pragma: no cover
            options.append("-origin=%s" % conf_value)

        elif conf == "distribution":
            options.append("-distribution=%s" % conf_value)

        elif conf == "gpg-key":
            options.append("-gpg-key=%s" % conf_value)
        elif conf == "automatic-update":
            # Ignored here
            pass
        elif conf == "snapshots":
            if has_source:  # pragma: no cover
                raise ValueError(
                    "Multiple sources for publish %s %s"
                    % (publish_name, publish_config)
                )
            has_source = True
            snapshots = util.unit_or_list_to_list(conf_value)
            source_args.append("snapshot")
            source_args.extend(
                [
                    snapshot.snapshot_spec_to_name(cfg, conf_value)
                    for conf_value in snapshots
                ]
            )

            num_sources = len(snapshots)

        elif conf == "repo":
            if has_source:  # pragma: no cover
                raise ValueError(
                    "Multiple sources for publish %s %s"
                    % (publish_name, publish_config)
                )
            has_source = True
            source_args = ["repo", conf_value]
            num_sources = 1
        elif conf == "publish":
            if has_source:  # pragma: no cover
                raise ValueError(
                    "Multiple sources for publish %s %s"
                    % (publish_name, publish_config)
                )
            has_source = True
            conf_value = " ".join(conf_value.split("/"))
            source_args.append("snapshot")
            try:
                sources = state_reader.state.publish_map[conf_value]
            except KeyError:
                lg.critical(
                    (
                        "Creating %s has been deferred, please call publish "
                        "create again"
                    )
                    % publish_name
                )
                return
            source_args.extend(sources)
            num_sources = len(sources)
        else:  # pragma: no cover
            raise ValueError(
                "Don't know how to handle publish config entry %s in %s"
                % (
                    conf,
                    publish_name,
                )
            )
    assert has_source
    assert len(components) == num_sources

    return command.Command(publish_cmd + options + source_args + endpoint_args)
