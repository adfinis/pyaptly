"""Create and update mirrors in aptly."""
import logging

from . import state_reader, util

lg = logging.getLogger(__name__)


def add_gpg_keys(mirror_config):
    """Use the gpg to download and add gpg keys needed to create mirrors.

    :param  mirror_config: The configuration yml as dict
    :type   mirror_config: dict
    """
    keyserver = mirror_config.get("keyserver")
    if not keyserver:
        keyserver = util.get_default_keyserver()
    keys_urls = {}
    if "gpg-keys" in mirror_config:
        keys = util.unit_or_list_to_list(mirror_config["gpg-keys"])
        if "gpg-urls" in mirror_config:
            urls = util.unit_or_list_to_list(mirror_config["gpg-urls"])
            urls_len = len(urls)
            for x in range(len(keys)):
                if x < urls_len:
                    url = urls[x]
                else:  # pragma: no cover
                    url = None
                keys_urls[keys[x]] = url
        else:
            for key in keys:
                keys_urls[key] = None

    for key in keys_urls.keys():
        if key in state_reader.state.gpg_keys:
            continue
        try:
            key_command = [
                "gpg",
                "--no-default-keyring",
                "--keyring",
                "trustedkeys.gpg",
                "--keyserver",
                keyserver,
                "--recv-keys",
                key,
            ]
            lg.debug("Adding gpg key with call: %s", key_command)
            util.run_command(key_command, check=True)
        except util.CalledProcessError:  # pragma: no cover
            url = keys_urls[key]
            if url:
                key_shell = (
                    "curl %s | "
                    "gpg --no-default-keyring --keyring trustedkeys.gpg "
                    "--import"
                ) % url
                util.run_command(["bash", "-c", key_shell], check=True)
            else:
                raise
    state_reader.state.read_gpg()


def mirror(cfg, args):
    """Create mirror commands, orders and executes them.

    :param  cfg: The configuration yml as dict
    :type   cfg: dict
    :param args: The command-line arguments read with :py:mod:`argparse`
    :type  args: namespace
    """
    lg.debug("Mirrors to create: %s", cfg["mirror"])

    mirror_cmds = {
        "create": cmd_mirror_create,
        "update": cmd_mirror_update,
    }

    cmd_mirror = mirror_cmds[args.task]

    if args.mirror_name == "all":
        for mirror_name, mirror_config in cfg["mirror"].items():
            cmd_mirror(cfg, mirror_name, mirror_config)
    else:
        if args.mirror_name in cfg["mirror"]:
            cmd_mirror(cfg, args.mirror_name, cfg["mirror"][args.mirror_name])
        else:
            raise ValueError(
                "Requested mirror is not defined in config file: %s"
                % (args.mirror_name)
            )


def cmd_mirror_create(cfg, mirror_name, mirror_config):
    """Create a mirror create command to be ordered and executed later.

    :param           cfg: The configuration yml as dict
    :type            cfg: dict
    :param   mirror_name: Name of the mirror to create
    :type    mirror_name: str
    :param mirror_config: Configuration of the snapshot from the yml file.
    :type  mirror_config: dict
    """
    if mirror_name in state_reader.state.mirrors:  # pragma: no cover
        return

    add_gpg_keys(mirror_config)
    aptly_cmd = ["aptly", "mirror", "create"]

    if "sources" in mirror_config and mirror_config["sources"]:
        aptly_cmd.append("-with-sources")
    else:
        aptly_cmd.append("-with-sources=false")

    if "udeb" in mirror_config and mirror_config["udeb"]:
        aptly_cmd.append("-with-udebs")

    if "architectures" in mirror_config:
        aptly_cmd.append(
            "-architectures={0}".format(
                ",".join(util.unit_or_list_to_list(mirror_config["architectures"]))
            )
        )

    aptly_cmd.append(mirror_name)
    aptly_cmd.append(mirror_config["archive"])
    aptly_cmd.append(mirror_config["distribution"])
    aptly_cmd.extend(util.unit_or_list_to_list(mirror_config["components"]))

    lg.debug("Running command: %s", " ".join(aptly_cmd))
    util.run_command(aptly_cmd, check=True)


def cmd_mirror_update(cfg, mirror_name, mirror_config):
    """Create a mirror update command to be ordered and executed later.

    :param           cfg: pyaptly config
    :type            cfg: dict
    :param   mirror_name: Name of the mirror to create
    :type    mirror_name: str
    :param mirror_config: Configuration of the snapshot from the yml file.
    :type  mirror_config: dict
    """
    if mirror_name not in state_reader.state.mirrors:  # pragma: no cover
        raise Exception("Mirror not created yet")
    add_gpg_keys(mirror_config)
    aptly_cmd = ["aptly", "mirror", "update"]
    if "max-tries" in mirror_config:
        aptly_cmd.append("-max-tries=%d" % mirror_config["max-tries"])

    aptly_cmd.append(mirror_name)
    lg.debug("Running command: %s", " ".join(aptly_cmd))
    util.run_command(aptly_cmd, check=True)
