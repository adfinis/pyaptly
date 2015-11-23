"""Tools for testing pyaptly"""

import os

import yaml


def read_yml(file_):
    """Read and merge a yml file"""
    directory = os.path.dirname(file_)
    with open(file_) as f:
        main_yml = dict(yaml.load(f.read()))
    merges = []
    if "merge" in main_yml:
        for merge_path in main_yml['merge']:
            path = os.path.join(
                directory,
                merge_path,
            )
            merges.append(read_yml(path))
        del main_yml['merge']
    for merge_struct in merges:
        main_yml = merge(main_yml, merge_struct)
    return main_yml


def merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        d = dict(a)
        d.update(dict(((k, merge(a.get(k, None), b[k])) for k in b)))
        for k, v in d.items():
            if v == "None":
                del d[k]
        return d
    return b
