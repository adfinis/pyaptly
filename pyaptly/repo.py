"""Create repos in aptly."""

import logging

from . import command, state_reader, util

lg = logging.getLogger(__name__)


def repo(cfg, args):
    """Create repository commands, orders and executes them.

    :param  cfg: The configuration toml as dict
    :type   cfg: dict
    :param args: The command-line arguments read with :py:mod:`argparse`
    :type  args: namespace
    """
    lg.debug("Repositories to create: %s", cfg["repo"])

    repo_cmds = {
        "create": repo_cmd_create,
    }

    cmd_repo = repo_cmds[args.task]

    if args.repo_name == "all":
        commands = [
            cmd_repo(cfg, repo_name, repo_conf)
            for repo_name, repo_conf in cfg["repo"].items()
        ]

        for cmd in command.Command.order_commands(
            commands, state_reader.state_reader().has_dependency
        ):
            cmd.execute()

    else:
        if args.repo_name in cfg["repo"]:
            commands = [cmd_repo(cfg, args.repo_name, cfg["repo"][args.repo_name])]
            for cmd in command.Command.order_commands(
                commands, state_reader.state_reader().has_dependency
            ):
                cmd.execute()
        else:
            raise ValueError(
                "Requested publish is not defined in config file: %s" % (args.repo_name)
            )


def repo_cmd_create(cfg, repo_name, repo_config):
    """Create a repo create command to be ordered and executed later.

    :param         cfg: pyaptly config
    :type          cfg: dict
    :param   repo_name: Name of the repo to create
    :type    repo_name: str
    :param repo_config: Configuration of the repo from the toml file.
    :type  repo_config: dict
    """
    if repo_name in state_reader.state_reader().repos():  # pragma: no cover
        # Nothing to do, repo already created
        return

    repo_cmd = ["aptly", "repo"]
    options = []
    endpoint_args = ["create", repo_name]

    for conf, conf_value in repo_config.items():
        if conf == "architectures":
            options.append(
                "-architectures=%s" % ",".join(util.unit_or_list_to_list(conf_value))
            )
        elif conf == "component":
            components = util.unit_or_list_to_list(conf_value)
            options.append("-component=%s" % ",".join(components))
        elif conf == "comment":  # pragma: no cover
            options.append("-comment=%s" % conf_value)
        elif conf == "distribution":
            options.append("-distribution=%s" % conf_value)
        else:  # pragma: no cover
            raise ValueError(
                "Don't know how to handle repo config entry %s in %s"
                % (
                    conf,
                    repo_name,
                )
            )

    return command.Command(repo_cmd + options + endpoint_args)
