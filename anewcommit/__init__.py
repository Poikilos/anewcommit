#!/usr/bin/env python
from __future__ import print_function

import sys
import os

verbose = False
for argI in range(1, len(sys.argv)):
    arg = sys.argv[argI]
    if arg.startswith("--"):
        if arg == "--debug":
            verbose = True
        elif arg == "--verbose":
            verbose = True


def error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def debug(*args, **kwargs):
    if not verbose:
        return
    print(*args, file=sys.stderr, **kwargs)


def get_verbose():
    return verbose

def set_verbose(enable_verbose):
    global verbose
    if (enable_verbose is not True) and (enable_verbose is not False):
        vMsg = enable_verbose
        if isinstance(vMsg, str):
            vMsg = '"{}"'.format(vMsg)
        raise ValueError(
            "enable_verbose must be True or False not {}."
            "".format(vMsg)
        )
    verbose = enable_verbose


trues = ["on", "true", "yes", "1"]


def is_truthy(v):
    if v is None:
        return False
    elif v is True:
        return True
    elif v is False:
        return False
    elif isinstance(v, str):
        if v_lower in trues:
            return True
    elif isinstance(v, int):
        if v != 0:
            return True
    elif isinstance(v, float):
        if v != 0:
            return True
    return False


def extract(src_file, new_parent_dir, auto_sub=True,
            auto_sub_name=None):
    """
    Extract any known archive file type to a specified directory.

    Sequential arguments:
    src_file -- Extract this archive file.
    new_parent_dir -- Place the extracted files into this directory
        (after temp directory).

    Keyword arguments:
    auto_sub -- Automatically create a subdirectory only if there is
        more than one item directly under the root of the archive. If
        False, extract as-is to new_parent_dir (even if that results in
        a subdirectory that is the name of the original directory).
    auto_sub_name -- If auto_sub is true, rename the extracted or
        created directory to the value of this string.
    """
    raise NotImplementedError("There is nothing implemented here yet.")


MODES = [
    'delete_then_add',
    'overlay',
]

last_luid = -1


def gen_luid():
    global last_luid
    last_luid += 1
    return str(last_luid)


def _new_process(luid=None):
    '''
    Keyword arguments:
    luid -- If None, generate a LUID (a locally-unique ID). The value
        must be a node ID that is unique within the scope of the
        project file, for any use such as by gui component dictionaries.
        There is one luid for each action, so there may be multiple
        named widgets in the group. If a unique id is necessary for
        every widget in your widget system, you can use `luid + "." +
        key` for the key where key is the key in the action dictionary.
    '''
    if luid is None:
        luid = gen_luid()
    return {
        'luid': luid,
        'verb': 'no_op',
        'commit': False,  # Change this to True if verb changes.
    }


def new_version(path, mode='delete_then_add', luid=None, name=None):
    '''
    Keyword arguments:
    luid -- If None, generate a LUID. See _new_process for more info.
    name -- Tag the subversion. If None, name is set to the leaf of the
        path.
    '''
    action = _new_process(luid=luid)
    if mode not in MODES:
        raise ValueError("Mode must be one of: {}".format(MODES))

    action['path'] = path
    action['mode'] = mode  # The mode only applies to 'get_version'.
    action['verb'] = 'get_version'
    action['commit'] = True
    if name is None:
        action['name'] = os.path.split(path)[1]
    else:
        action['name'] = name
    return action


VERBS = [
    'pre_process',
    'post_process',
    'no_op',
]

# The special verb is get_version, and is added via add_version.

VERBS_HELP = {
    'pre_process': 'Make changes to the next version before a commit.',
    'post_process': 'Make changes to the previous version.',
    'no_op': 'Do not modify the previous version.',
}


def new_pre_process(luid=None):
    '''
    A pre-process verb affects the next version in the list of actions.

    Keyword arguments:
    luid -- If None, generate a LUID. See _new_process for more info.
    '''
    action = _new_process()
    action['verb'] = 'pre_process'
    action['commit'] = True
    if luid is None:
        luid = gen_luid()
    return action


def new_post_process(luid=None):
    '''
    A post-process action affects the previous version in the list of
    actions. For example, renaming directories or files as a separate
    commit may make committing the next version more clean.

    Keyword arguments:
    luid -- If None, generate a LUID. See _new_process for more info.
    '''
    action = _new_process()
    action['verb'] = 'post_process'
    action['commit'] = True
    return action


class ANCProject:
    '''
    Manage a list of version directories.

    Public Properties:
    project_dir -- The metadata for the various version directories will
        be stored here.
    actions -- This is a list of actions to take, such as pre-processing
        or post-processing a version.
    '''
    default_settings = {}

    def __init__(self):
        self.project_dir = None
        self.actions = []

    def add_transition(self, verb):
        '''
        Sequential arguments:
        verb -- Set operation string from the OPS table to decide what
            to do between versions.
        '''
        action = None
        if verb == "pre_process":
            action = new_pre_process()
        elif verb == "post_process":
            action = new_post_process()
        elif verb == "no_op":
            action = _new_process()
        else:
            raise ValueError(
                "The verb is unknown: {}"
                "".format(verb)
            )
        self.actions.append(action)
        return action

    def add_version(self, path, mode='delete_then_add'):
        '''
        Sequential arguments:
        path -- This is a path to a version.
        '''
        action = new_version(path, mode=mode)
        # ^ new_version raises ValueError if the mode is invalid.
        self.actions.append(action)
        return action

    def to_dict(self):
        return {
            'project_dir': self.project_dir,
            'actions': self.actions,
        }


def main():
    pass


if __name__ == "__main__":
    error("Import this module into your program to use it.")
    main()
