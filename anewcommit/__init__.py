#!/usr/bin/env python

import sys

def error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

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
        There is one luid for each step, so there may be multiple
        named widgets in the group. If a unique id is necessary for
        every widget in your widget system, you can use `luid + "." +
        key` for the key where key is the key in the step dictionary.
    '''
    if luid is None:
        luid = gen_luid()
    return {
        'luid': luid,
        'action': 'no_op',
        'commit': False,  # Change this to True if action changes.
    }


def new_version(path, mode='delete_then_add', luid=None):
    '''
    Keyword arguments:
    luid -- If None, generate a LUID. See _new_process for more info.
    '''
    step = _new_process(luid=luid)
    if mode not in MODES:
        raise ValueError("Mode must be one of: {}".format(MODES))

    step['path'] = path
    step['mode'] = mode  # The mode only applies to 'get_version'.
    step['action'] = 'get_version'
    step['commit'] = True
    return step


ACTIONS = [
    'pre_process',
    'post_process',
    'no_op',
]

# The special action is get_version, and is added via add_version.

ACTIONS_HELP = {
    'pre_process': 'Make changes to the next version before a commit.',
    'post_process': 'Make changes to the previous version.',
    'no_op': 'Do not modify the previous version.',
}


def new_pre_process(luid=None):
    '''
    A pre-process action affects the next version in the list of steps.

    Keyword arguments:
    luid -- If None, generate a LUID. See _new_process for more info.
    '''
    step = _new_process()
    step['action'] = 'pre_process'
    step['commit'] = True
    if luid is None:
        luid = gen_luid()
    return step


def new_post_process(luid=None):
    '''
    A post-process action affects the previous version in the list of
    steps. For example, renaming directories or files as a separate
    commit may make committing the next version more clean.

    Keyword arguments:
    luid -- If None, generate a LUID. See _new_process for more info.
    '''
    step = _new_process()
    step['action'] = 'post_process'
    step['commit'] = True
    return step


class ANCProject:
    '''
    Manage a list of version directories.

    Public Properties:
    project_dir -- The metadata for the various version directories will
        be stored here.
    steps -- This is a list of actions to take, such as pre-processing
        or post-processing a version.
    '''
    default_settings = {}

    def __init__(self):
        self.project_dir = None
        self.steps = []

    def add_transition(self, action):
        '''
        Sequential arguments:
        action -- Set operation string from the OPS table to decide what
            to do between versions.
        '''
        step = None
        if action == "pre_process":
            step = new_pre_process()
        elif action == "post_process":
            step = new_post_process()
        elif action == "no_op":
            step = _new_process()
        else:
            raise ValueError(
                "The action is unknown: {}"
                "".format(action)
            )
        self.steps.append(step)
        return step

    def add_version(self, path, mode='delete_then_add'):
        '''
        Sequential arguments:
        path -- This is a path to a version.
        '''
        step = new_version(path, mode=mode)
        # ^ new_version raises ValueError if the mode is invalid.
        self.steps.append(step)
        return step

    def to_dict(self):
        return {
            'project_dir': self.project_dir,
            'steps': self.steps,
        }


def main():
    pass


if __name__ == "__main__":
    error("Import this module into your program to use it.")
    main()
