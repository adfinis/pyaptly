"""Aptly mirror/snapshot managment automation."""
import argparse
import logging
import subprocess
import sys

import yaml


def get_logger():
    """Get the logger.

    :rtype: logging.Logger"""
    return logging.getLogger("pyaptly")

lg = get_logger()


def call_output(args, input_=None):
    p = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    output, err = p.communicate(input_)
    if p.returncode != 0:
        raise subprocess.CalledProcessError(
            p.returncode,
            args,
        )
    return output


class SystemStateReader(object):
    def __init__(self):
        self.gpg_keys  = set()
        self.mirrors   = set()
        self.snapshots = set()

    def read(self):
        self.read_gpg()
        self.read_mirror()
        self.read_snapshot()

    def read_gpg(self):
        self.gpg_keys = set()
        data = call_output([
            "gpg",
            "--no-default-keyring",
            "--keyring", "trustedkeys.gpg",
            "--list-keys",
            "--with-colons"
        ])
        lg.debug('GPG returned: %s', data)
        for line in data.split("\n"):
            field = line.split(":")
            if field[0] == "pub":
                key = field[4]
                key_short = key[8:]
                self.gpg_keys.add(key)
                self.gpg_keys.add(key_short)

    def read_mirror(self):
        self.mirrors = set()
        self.read_aptly_list("mirror", self.mirrors)

    def read_snapshot(self):
        self.snapshots = set()
        self.read_aptly_list("snapshot", self.snapshots)

    def read_aptly_list(self, type_, list_):
        data = call_output([
            "aptly", type_, "list", "-raw"
        ])
        lg.debug('Aptly returned %s: %s', type_, data)
        for line in data.split("\n"):
            list_.add(line.strip())


state = SystemStateReader()


def main(argv=None):
    """Called by command-line, defines parsers and executes commands"""
    if not argv:  # pragma: no cover
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Manage aptly')
    parser.add_argument(
        '--config',
        '-c',
        help='Yaml config file defining mirrors and snapshots',
        type=str
    )
    parser.add_argument(
        '--debug',
        '-d',
        help='Enable debug output',
        action='store_true',
    )
    subparsers = parser.add_subparsers()
    mirror_parser = subparsers.add_parser(
        'mirror',
        help='manage aptly mirrors'
    )
    mirror_parser.set_defaults(func=mirror)
    mirror_parser.add_argument(
        'task',
        type=str,
        choices=['create', 'drop', 'update']
    )
    mirror_parser.add_argument(
        'mirror_name',
        type=str,
        nargs='?',
        default='all'
    )
    snapshot_parser = subparsers.add_parser(
        'snapshot',
        help='manage aptly snapshots'
    )
    snapshot_parser.set_defaults(func=snapshot)
    snapshot_parser.add_argument('task', type=str, choices=['create', 'drop'])
    snapshot_parser.add_argument(
        'snapshot_name',
        type=str,
        nargs='?',
        default='all'
    )
    # TODO implement this
    # publish_parser = subparsers.add_parser(
    #     'publish',
    #     help='manage aptly publish endpoints'
    # )

    args = parser.parse_args(argv)
    root = logging.getLogger()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(logging.CRITICAL)
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    lg.debug("Args: %s", vars(args))

    with open(args.config, 'r') as cfgfile:
        cfg = yaml.load(cfgfile)
    state.read()

    # run function for selected subparser
    args.func(cfg, args)


def snapshot(cfg, args):
    """Creates snapshots"""
    lg.debug("Snapshots to create: %s", (cfg['snapshot']))

    cmd_snapshot = snapshot_cmds[args.task]

    if args.snapshot_name == "all":
        for snapshot_name, snapshot_config in cfg['snapshot'].items():
            cmd_snapshot(snapshot_name, snapshot_config)
    else:
        if args.snapshot_name in cfg['snapshot']:
            cmd_snapshot(
                args.snapshot_name,
                cfg['snapshot'][args.snapshot_name]
            )
        else:
            raise ValueError(
                "Requested snapshot is not defined in config file: %s" % (
                    args.snapshot_name
                )
            )


def cmd_snapshot_create(snapshot_name, snapshot_config):
    """Call the aptly snapshot command"""
    if snapshot_name in state.snapshots:
        return
    aptly_cmd = ['aptly', 'snapshot', 'create']
    aptly_cmd.append(snapshot_name)
    aptly_cmd.append('from')
    if 'mirror' in snapshot_config:
        aptly_cmd.extend(['mirror', snapshot_config['mirror']])
    elif 'repo' in snapshot_config:
        aptly_cmd.extend(['repo', snapshot_config['repo']])
    lg.debug('Running command: %s', ' '.join(aptly_cmd))
    subprocess.check_call(aptly_cmd)


def mirror(cfg, args):
    """Creates mirrors"""
    lg.debug("Mirrors to create: %s", cfg['mirror'])

    cmd_mirror = mirror_cmds[args.task]

    if args.mirror_name == "all":
        for mirror_name, mirror_config in cfg['mirror'].items():
            cmd_mirror(mirror_name, mirror_config)
    else:
        if args.mirror_name in cfg['mirror']:
            cmd_mirror(
                args.mirror_name,
                cfg['mirror'][args.mirror_name]
            )
        else:
            raise ValueError(
                "Requested mirror is not defined in config file: %s" % (
                    args.mirror_name
                )
            )


def add_gpg_keys(mirror_config):
    if 'gpg-keys' in mirror_config:
        keys = mirror_config['gpg-keys']
        keys_urls = {}
        if 'gpg-urls' in mirror_config:
            urls = mirror_config['gpg-urls']
            urls_len = len(urls)
            for x in range(len(keys)):
                if x < urls_len:
                    url = urls[x]
                else:
                    url = None
                keys_urls[keys[x]] = url
        else:
            for key in keys:
                keys_urls[key] = None

    for key in keys_urls.keys():
        if key in state.gpg_keys:
            continue
        try:
            key_command = [
                "gpg",
                "--no-default-keyring",
                "--keyring",
                "trustedkeys.gpg",
                "--keyserver",
                "pool.sks-keyservers.net",
                "--recv-keys",
                key
            ]
            subprocess.check_call(key_command)
        except subprocess.CalledProcessError:
            url = keys_urls[key]
            if url:
                key_command = (
                    "wget -q -O - %s | "
                    "gpg --no-default-keyring "
                    "--keyring trustedkeys.gpg --import"
                ) % url
                subprocess.check_call(['bash', '-c', key_command])
            else:
                raise


def cmd_mirror_create(mirror_name, mirror_config):
    """Call the aptly mirror command"""
    if mirror_name in state.mirrors:
        return
    add_gpg_keys(mirror_config)
    aptly_cmd = ['aptly', 'mirror', 'create']
    if 'sources' in mirror_config and mirror_config['sources']:
        aptly_cmd.append('-with-sources')
    if 'udeb' in mirror_config and mirror_config['udeb']:
        aptly_cmd.append('-with-udebs')
    if 'architectures' in mirror_config:
        aptly_cmd.append('-architectures={0}'.format(
            ','.join(mirror_config['architectures'])
        ))
    aptly_cmd.append(mirror_name)
    aptly_cmd.append(mirror_config['archive'])
    aptly_cmd.append(mirror_config['distribution'])
    for component in mirror_config['components']:
        aptly_cmd.append(component)
    lg.debug('Running command: %s', ' '.join(aptly_cmd))
    subprocess.check_call(aptly_cmd)


def cmd_mirror_update(mirror_name, mirror_config):
    """Call the aptly mirror command"""
    if mirror_name not in state.mirrors:
        raise Exception("Mirror not created yet")
    add_gpg_keys(mirror_config)
    aptly_cmd = ['aptly', 'mirror', 'update']
    aptly_cmd.append(mirror_name)
    lg.debug('Running command: %s', ' '.join(aptly_cmd))
    subprocess.check_call(aptly_cmd)

mirror_cmds = {
    'create': cmd_mirror_create,
    'update': cmd_mirror_update,
}

snapshot_cmds = {
    'create': cmd_snapshot_create,
}

if __name__ == '__main__':  # pragma: no cover
    main()
