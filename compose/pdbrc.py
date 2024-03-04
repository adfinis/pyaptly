import atexit
import os
import pdb
import readline

history_file = os.path.expanduser("~/.pdb_history")


def save_history(history_file=history_file):
    readline.write_history_file(history_file)


if os.path.exists(history_file):
    readline.read_history_file(history_file)

atexit.register(save_history)


class Config(pdb.DefaultConfig):
    sticky_by_default = True
