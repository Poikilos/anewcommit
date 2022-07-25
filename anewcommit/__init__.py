#!/usr/bin/env python
from __future__ import print_function

import sys
import os
import platform
import subprocess
import json
from datetime import datetime, timezone
import pathlib
from io import StringIO
import csv

my_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(my_dir)
repos_dir = os.path.dirname(repo_dir)
try_repo_dir = os.path.join(repos_dir, "pycodetool")
if os.path.isdir(try_repo_dir):
    sys.path.insert(0, try_repo_dir)

from pycodetool.parsing import (
    find_unquoted_not_commented,
    explode_unquoted,
)

python_mr = sys.version_info[0]

verbosity = 0
for argI in range(1, len(sys.argv)):
    arg = sys.argv[argI]
    if arg.startswith("--"):
        if arg == "--verbose":
            verbosity = 1
        elif arg == "--debug":
            verbosity = 2


def echo0(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def echo1(*args, **kwargs):
    if verbosity < 1:
        return
    print(*args, file=sys.stderr, **kwargs)


def echo2(*args, **kwargs):
    if verbosity < 2:
        return
    print(*args, file=sys.stderr, **kwargs)


def s2or3(s):
    if python_mr < 3:
        if type(s).__name__ == "unicode":
            # ^ such as a string returned by json.load*
            #   using Python 2
            return str(s)
    return s

def get_verbosity():
    return verbosity


def set_verbosity(verbosity_level):
    global verbosity
    max_verbosity = 3
    verbosities = list(range(max_verbosity+1))
    if verbosity_level is True:
        verbosity_level = 1
    elif verbosity_level is False:
        verbosity_level = 0
    if verbosity_level not in verbosities:
        vMsg = verbosity_level
        if isinstance(vMsg, str):
            vMsg = '"{}"'.format(vMsg)
        raise ValueError(
            "verbosity_level must be 0 to {} not {}."
            "".format(max_verbosity, vMsg)
        )
    verbosity = verbosity_level

profile = os.environ.get('HOME')
if platform.system() == "Windows":
    profile = os.environ.get('USERPROFILE')

trues = ["on", "true", "yes", "1"]


def is_truthy(v):
    if v is None:
        return False
    elif v is True:
        return True
    elif v is False:
        return False
    elif isinstance(v, str):
        if v.lower() in trues:
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

default_ignores = ["Thumbs.db", ".DS_Store", "error_log", "temp"]

def newest_file_dt_in(parent, too_new_dt=None, level=0,
                      ignores=default_ignores):
    '''
    Get the datetime of the latest file in parent recursively.

    Keyword arguments:
    too_new_dt -- skip files with a datetime >= too_new_dt if not None.
    level -- Determine the directory depth for debugging use only (doesn't
        affect results).

    Returns:
    a tuple (path, datetime)
    '''
    if too_new_dt is not None:
        if too_new_dt.tzinfo is None:
            raise ValueError("The datetime is timezone-naive.")
    path = None
    newest_dt = None
    for sub in os.listdir(parent):
        subPath = os.path.join(parent, sub)
        if os.path.islink(subPath):
            continue
        if sub in ignores:
            continue
        if subPath in ignores:
            continue
        mdt = None
        m_path = None
        if os.path.isfile(subPath):
            # mtime = os.path.getmtime(subPath)
            mtime = pathlib.Path(subPath).stat().st_mtime
            # ^ pathlib stat best cross-platform way according to
            #   <pynative.com/python-file-creation-modification-datetime/>
            m_path = subPath
            mdt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        elif os.path.isdir(subPath):
            m_path, mdt = newest_file_dt_in(
                subPath,
                too_new_dt=too_new_dt,
                level=level+1,
                ignores=ignores,
            )
        if mdt is None:
            # It must be an empty directory, or file dates are >= too_new_dt
            continue
        if (too_new_dt is None) or (mdt < too_new_dt):
            if (newest_dt is None) or (mdt > newest_dt):
                newest_dt = mdt
                path = m_path
    if newest_dt is None:
        if level == 0:
            echo0("- no date < {} could be found in {}"
                  "".format(too_new_dt, subPath))
    return path, newest_dt

def open_file(path):
    # based on <https://stackoverflow.com/a/16204023/4541104>:
    if platform.system() == "Windows":
        os.startfile(path)  # only exists on Windows
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def split_statement(statement):
    '''
    Split a string of multiple arguments (respecting quotes) into a list.
    '''
    ins = StringIO(statement)
    reader = csv.reader(ins, delimiter=" ")
    parts = None
    for row in reader:
        if parts is not None:
            RuntimeError("The statement must be only one line: '''\n{}\n'''"
                         "".format(statement))
        parts = row
    for i in range(len(parts)):
        if parts[i].startswith('"') and parts[i].endswith('"'):
            parts[i] = parts[i][1:-1]
        elif parts[i].startswith("'") and parts[i].endswith("'"):
            parts[i] = parts[i][1:-1]
    return parts


def parse_statement(statement):
    result = {}
    parts = split_statement(statement)
    if len(parts) > 0:
        result['command'] = parts[0]
    else:
        raise ValueError('The command "{}" is blank'.format(statement))
    if parts[0] == "sub":
        if len(parts) != 2:
            raise ValueError(
                "The {} command has {} argument(s) but should have 1:"
                " (source)"
                "".format(statement, len(parts)-1)
            )
        result['source'] = parts[1]
    elif parts[0] == "use":
        if (len(parts) == 4) and (parts[2] == "as"):
            # use <source> as <destination>
            result['source'] = parts[1]
            result['destination'] = parts[3]
        elif (len(parts) == 3) and (parts[1] == "as"):
            # The whole thing is the sourse in a "use as" statement like
            # use as <destination>
            result['destination'] = parts[2]
        else:
            raise ValueError(
                'The {} command has {} argument(s) but should have 2 or 3:'
                ' (source, "as", destination)'
                ' or ("as", destination)'
                ''.format(statement, len(parts)-1)
            )
    else:
        raise ValueError(
            'The command "{}" is unknown in statement "{}"'
            ''.format(parts[0], statement)
        )
    return result


def statement_to_caption(command_dict):
    if not isinstance(command_dict, dict):
        raise ValueError(
            "You must provide the command such as from parse_statement()"
        )

    text = command_dict.get('destination')
    if text is None:
        text = command_dict.get('source')
    if text is None:
        text = command_dict.get('command')
    return text


MODES = [
    'delete_then_add',
    'overlay',
]

last_luid_i = -1
used_luids = set()


def use_luid(luid):
    global last_luid_i
    used_luids.add(luid)
    luid_i = int(luid)  # saved as string, so convert to int
    if luid_i > last_luid_i:
        last_luid_i = luid_i


def gen_luid():
    global last_luid_i
    last_luid_i += 1
    new_luid = str(last_luid_i)
    used_luids.add(new_luid)
    return new_luid


def find_param(haystack, needle, min_param=0, max_param=-1, fs=",",
               quotes="\"'", inline_comment_marks=["//", "#"]):
    '''
    Find the param in a function call.

    This function requires find_unquoted_not_commented and
    explode_unquoted from the parsing submodule of Poikilos' pycodetool.

    Keyword arguments:
    fs -- field separator
    quotes -- what quotes are allowed
    '''
    paren1_i = find_unquoted_not_commented(haystack, "(")
    if paren1_i < 0:
        return paren1_i
    start = paren1_i + 1
    paren2_i = find_unquoted_not_commented(haystack, ")", start=start)

    return -1


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
        'command': ""
    }


VERSION_VERBS = [
    'get_version',
]
DEFAULT_VERSION_VERB = VERSION_VERBS[0]

TRANSITION_VERBS = [
    'pre_process',
    'post_process',
    'no_op',
    'for_every_source',
]

# The special verb is get_version, and is added via add_version.

VERBS_HELP = {
    'pre_process': 'Make changes to the next version before a commit.',
    'post_process': 'Make changes to the previous version.',
    'no_op': 'Do not modify the previous version.',
}


def new_version(path, mode='delete_then_add', luid=None, name=None):
    '''
    Keyword arguments:
    luid -- If None, generate a LUID. See _new_process for more info.
    name -- Set the visible name (Used as commit summary if this source is
        committed). If None, the name will be generated as the leaf of the
        path.
    '''
    action = _new_process(luid=luid)
    if mode not in MODES:
        raise ValueError("Mode must be one of: {}".format(MODES))

    action['path'] = path
    action['mode'] = mode  # The mode only applies to 'get_version'.
    action['verb'] = DEFAULT_VERSION_VERB
    action['commit'] = True
    if name is None:
        action['name'] = os.path.split(path)[1]
    else:
        action['name'] = name
    return action


def new_pre_process(luid=None):
    '''
    A pre-process verb affects the next version in the list of _actions.

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
    _actions. For example, renaming directories or files as a separate
    commit may make committing the next version more clean.

    Keyword arguments:
    luid -- If None, generate a LUID. See _new_process for more info.
    '''
    action = _new_process()
    action['verb'] = 'post_process'
    action['commit'] = True
    return action


def substep_to_str(ss):
    name = None
    if (len(ss) > 2) and (len(ss) < 3) and isinstance(ss[1], int):
        name = ss[2].get('path')
    else:
        # If len(ss) is 3, it is a swap operation (2 luid params)
        name = str(ss)
    if name is not None:
        name = os.path.split(name)[1]
    return name


class ANCProject:
    '''
    Manage a list of version directories.

    Public Properties:
    project_dir -- The metadata for the various version directories will
        be stored here.
    path -- This is the explicit path to a project file, usually
        "anewcommit.json" in project_dir.
    _actions -- This is a list of _actions to take, such as pre-processing
        or post-processing a version.
    '''
    default_settings = {}

    def __init__(self):
        self.path = None
        self.project_dir = None
        self._actions = []
        self.remove_redo = False  # Remove redo after undo.
        self.clear_undo()
        self.data = {
            'actions': self._actions,
        }
        self.auto_save = True

    def clear_undo(self):
        self._undo_steps = []
        self._undo_step_i = -1

    def clear(self):
        self.clear_undo()
        del self._actions[:]
        # self.data['actions'] = self._actions
        # TODO: if self.auto_save: self.save()

    def has_undo(self):
        if len(self._undo_steps) < 1:
            return False
        return self._undo_step_i >= 0

    def has_redo(self):
        return self._undo_step_i+1 < len(self._undo_steps)

    def _add_undo_step(self, step):
        '''
        Add a dictionary that describes how to undo what was just done.
        '''
        step_i = self._undo_step_i
        if self.remove_redo:
            if len(self._undo_steps) > (self._undo_step_i+1):
                self._undo_steps = self._undo_steps[:self._undo_step_i+1]
        if self._undo_step_i == (len(self._undo_steps)-1):
            self._undo_steps.append(step)
            self._undo_step_i += 1
        elif self._undo_step_i < (len(self._undo_steps)-1):
            self._undo_steps.insert(self._undo_step_i+1, step)
            self._undo_step_i += 1
        else:
            return False, ("The undo step[{}]={} is not within range (len={})"
                           "".format(self._undo_step_i,
                                     self._undo_steps[self._undo_step_i],
                                     len(self._undo_steps)))
        echo1("* _add_undo_step({}) at {}".format(step, step_i))
        msg = None
        if not self.has_undo():
            msg = ("There is no undo after adding an undo step at {}"
                   "".format(step_i))
            echo0("  * "+msg)
        return True, msg

    def undo(self, redo=False):
        '''
        A substep
        is a command in the form of a list, and a step is a list of
        lists (commands).

        Returns:
        a list of luids that were affected.
        '''
        results = {}
        results['added'] = []
        results['removed'] = []
        results['swapped'] = []
        results['swapped_luids'] = []
        do_s = "redo" if redo else "undo"
        step_i = self._undo_step_i
        if redo:
            step_i += 1
            if step_i >= len(self._undo_steps):
                return None, "There is nothing to {}.".format(do_s)
        if step_i < 0:
            return None, "There is nothing to {}.".format(do_s)
        step = self._undo_steps[step_i]
        echo1("  * {} step: {}".format(do_s, step))
        redo_step = []
        for ss in step:
            redo_ss = None
            if ss[0] == "remove":
                redo_ss = self.remove(ss[1], add_undo_step=False)
                results['removed'].append(ss[1])
            elif ss[0] == "insert":
                redo_ss = self.insert(ss[1], ss[2], add_undo_step=False)
                results['added'].append(ss[1])
            elif ss[0] == "swap":
                redo_ss = self.swap(ss[1], ss[2], add_undo_step=False)
                results['swapped'].append(ss[1])
                results['swapped'].append(ss[2])
            elif ss[0] == "swap_where_luid":
                redo_ss = self.swap(ss[1], ss[2], add_undo_step=False)
                results['swapped_luids'].append(ss[1])
                results['swapped_luids'].append(ss[2])
            else:
                return results, ("Error: {} {} isn't implemented."
                                 "".format(do_s, ss))
            if redo_ss is not None:
                redo_step.append(redo_ss)
        if redo:
            self._undo_steps[self._undo_step_i] = redo_step
            self._undo_step_i += 1
        else:
            self._undo_steps[self._undo_step_i] = redo_step
            echo1("- Added redo_step:")
            for ss in redo_step:
                echo1("  - {}".format(substep_to_str(ss)))
            # ^ Add a redo step only during undo.
            self._undo_step_i -= 1
        return results, None

    def append_action(self, action, do_save=True):
        self._actions.append(action)
        self._add_undo_step([
            ['remove', len(self._actions)-1],
        ])
        if do_save:
            self.save()

    def add_transition(self, verb, do_save=True):
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
        self.append_action(action, do_save=do_save)
        return action

    def add_version(self, path, mode='delete_then_add', do_save=True,
                    name=None):
        '''
        Sequential arguments:
        path -- This is a path to a version.

        Keyword arguments:
        mode -- Specify how to add the data to the repo.
        do_save -- Save immediately.
        name -- Set the name (See new_version documentation).
        '''
        action = new_version(path, mode=mode, name=name)
        # ^ new_version raises ValueError if the mode is invalid.
        self.append_action(action, do_save=do_save)
        return action

    def insert_statement_where(self, luid, statement, direction=-1):
        '''
        Convert a statement to an action and insert it at the luid.

        Keyword arguments:
        direction -- if -1, to pre_process, if 1, post_process.
        '''
        action = _new_process()
        if direction == -1:
            action['verb'] = 'pre_process'
        elif direction == -1:
            action['verb'] = 'post_process'
        else:
            raise ValueError("The direction must be -1 or 1.")

        if action['verb'] not in TRANSITION_VERBS:
            raise ValueError("The verb must be one of {} not {}"
                             "".format(TRANSITION_VERBS, action['verb']))

        return self.insert_where('luid', luid, action,
                                 direction=direction)

    def append_statement_where(self, luid, statement, force=False):
        '''
        Keyword arguments:
        force -- Add it even it is already in the list
            (not yet implemented).

        Returns:
        True if added, otherwise false.
        '''
        parse_statement(statement)  # call this to validate/raise exception
        i = self._find_where('luid', luid)
        if self._actions[i].get('statements') is None:
            self._actions[i]['statements'] = []
        if statement not in self._actions[i]['statements']:
            self._actions[i]['statements'].append(statement)
            self.save()
            return True
        return False

    def remove_statement_where(self, luid, statement, force=False):
        '''
        Returns:
        True if removed, otherwise false.
        '''
        args = split_statement(statement)
        if len(args) < 2:
            raise ValueError(
                'The statement "{}" does not resolve to >=2 parts: {}'
                ''.format(statement, args)
            )
        i = self._find_where('luid', luid)
        if self._actions[i].get('statements') is None:
            self._actions[i]['statements'] = []
        if statement in self._actions[i]['statements']:
            self._actions[i]['statements'].remove(statement)
            self.save()
            return True
        return False


    def _find_where(self, name, value):
        for i in range(len(self._actions)):
            if self._actions[i].get(name) == value:
                return i
        return -1

    def get_affected(self, near_index):
        '''
        Get a tuple (version index, range), where *version index* is near_index
        or the index of the version it affects, and *range* is the entire range
        of indices affecting the version that the index represents or affects.
        '''
        # prev_luid = None
        # version_luid = None  # The luid of the affected version.
        # next_luid = None
        # prev_i = None
        # next_i = None
        version_i = None  # The index of the affected version.
        near_action = self._actions[near_index]
        if near_action['verb'] in VERSION_VERBS:
            version_i = near_index
        ranges = self.get_ranges()
        # affected_range_i = None
        affected_range = None
        for range_i in range(len(ranges)):
            r = ranges[range_i]
            if near_index in r:
                # affected_range_i = range_i
                affected_range = r
        if version_i is None:
            for i in affected_range:
                if self._actions[i]['verb'] in VERSION_VERBS:
                    version_i = i
                    break
        return version_i, affected_range

    def get_ranges(self):
        '''
        Get each group of actions by version.
        '''
        ranges = []
        this_range = []
        ENDERS = VERSION_VERBS + ['pre_process']
        version_i = None
        for i in range(0, len(self._actions)):
            action = self._actions[i]
            if version_i is None:
                if action['verb'] in VERSION_VERBS:
                    version_i = i
                elif action['verb'] == 'post_process':
                    raise ValueError(
                        "{} occurs before a version"
                        "".format(action['verb'])
                    )
            else:
                if action['verb'] in ENDERS:
                    if len(this_range) > 0:
                        ranges.append(this_range)
                        this_range = []
                        version_i = None
                        if action['verb'] in VERSION_VERBS:
                            version_i = i
            this_range.append(i)

        if len(this_range) > 0:
            ranges.append(this_range)

        totals = {}
        for rI in range(len(ranges)):
            for i in ranges[rI]:
                key = str(rI)
                count = totals.get(key)
                if count is None:
                    count = 0
                if self._actions[i]['verb'] in VERSION_VERBS:
                    count += 1
                totals[key] = count
                if count > 1:
                    echo0("ENDERS={}".format(ENDERS))
                    echo0("ranges={}".format(ranges))
                    raise RuntimeError(
                        "The data wasn't grouped correctly. The action set has"
                        " more than one version."
                    )

        return ranges

    def get_action(self, luid):
        i = self._find_where('luid', luid)
        if i > -1:
            return self._actions[i]
        return None

    def _use_all_luids(self):
        bad_indices = []
        for i in range(len(self._actions)):
            action = self._actions[i]
            if action['luid'] in used_luids:
                bad_indices.append(i)
            use_luid(action['luid'])
        return bad_indices

    def load(self, path):
        with open(path, 'r') as ins:
            try:
                self.data = json.load(ins)
                self.path = path
                self._actions = self.data['actions']
                for action in self._actions:
                    for k,v in action.items():
                        action[k] = s2or3(v)
                bad_indices = self._use_all_luids()
                msg = None
                for i in bad_indices:
                    new_luid = gen_luid()
                    if msg is None:
                        msg = ""
                    msg += ("* replacing duplicate luid in {}"
                            " with {}"
                            "".format(self._actions[i], new_luid))
                    self._actions[i]['luid'] = new_luid
                self.project_dir = self.data.get('project_dir')
                if self.project_dir is None:
                    self.project_dir = os.path.dirname(path)
                return True, msg
            except ValueError as ex:  # Python 2 JSON decode error
                return False, str(ex)
            # except json.JSONDecodeError as ex:  # Python 3
            #     # json.JSONDecodeError never happens since
            #     # ValueError is its ancestor class.
            #     return False, str(ex)
        return False, "unknown error"

    def save(self):
        if self.path is None:
            if self.project_dir is None:
                raise RuntimeError("The project dir or path must be set.")
            self.path = os.path.join(self.project_dir, "anewcommit.json")
        with open(self.path, 'w') as outs:
            json.dump(self.data, outs, indent=2, sort_keys=True)
        echo1('* wrote "{}"'.format(self.path))
        return True

    def remove(self, index, add_undo_step=True):
        action = self._actions.pop(index)
        echo1("* removed [{}]: {}".format(index, action))
        echo1("  len {}".format(len(self._actions)))
        if self.auto_save:
            self.save()
        undo_substep = [
            "insert",
            index,
            action,
        ]
        if add_undo_step:
            self._add_undo_step([undo_substep])
        return undo_substep

    def insert(self, index, action, add_undo_step=True):
        '''
        Sequential arguments:
        index -- This is an index in self._actions (usually NOT the same as
            self._actions[index].luid).
        action -- Insert this action dictionary.

        Keyword arguments:
        add_undo_step -- This should only be False if an undo/redo is doing the
            step, or there is some particular internal reason not to record a
            step.

        Returns:
        an undo substep which can be appended to a step. A substep
        is a command in the form of a list, and a step is a list of
        lists (commands).
        '''
        if index > len(self._actions):
            raise IndexError("The index {} is beyond len {}"
                             "".format(index, len(self._actions)))
        # ^ insert at >=len actually works, so ensure the number is sane.
        self._actions.insert(index, action)
        echo1("* inserted [{}]: {}".format(index, action))
        echo1("  len {}".format(len(self._actions)))
        undo_substep = [
            "remove",
            index
        ]
        if add_undo_step:
            self._add_undo_step([undo_substep])
        if self.auto_save:
            self.save()
        return undo_substep

    def swap(self, index, other_index, add_undo_step=True):
        '''
        Keyword arguments:
        add_undo_step -- This should only be False if an undo/redo is doing the
            step, or there is some particular internal reason not to record a
            step.
        '''
        tmp_action = self._actions[index]
        self._actions[index] = self._actions[other_index]
        self._actions[other_index] = tmp_action
        undo_substep = [
            "swap",
            index,
            other_index,
        ]
        if add_undo_step:
            self._add_undo_step([undo_substep])
        if self.auto_save:
            self.save()
        return undo_substep

    def swap_where_luid(self, luid, other_luid, add_undo_step=True):
        '''
        Keyword arguments:
        add_undo_step -- This should only be False if an undo/redo is doing the
            step, or there is some particular internal reason not to record a
            step.
        '''
        index = self._find_where('luid', luid)
        other_index = self._find_where('luid', other_luid)
        if index < 0:
            raise ValueError("There is no '{}' {}".format('luid', luid))
        if other_index < 0:
            raise ValueError("There is no '{}' {}".format('luid', other_luid))

        tmp_action = self._actions[index]
        self._actions[index] = self._actions[other_index]
        self._actions[other_index] = tmp_action
        undo_substep = [
            "swap_where_luid",
            luid,
            other_luid,
        ]
        if add_undo_step:
            self._add_undo_step([undo_substep])
        if self.auto_save:
            self.save()


    def insert_where(self, name, value, action, direction=-1):
        '''
        Sequential arguments:
        luid -- Insert before this luid.
        action -- Insert this action dictionary.

        Keyword arguments:
        direction -- -1 to insert before the match, 1 to insert afterward
            (or after all related post-processing steps if any).
        '''
        newI = self._find_where(name, value)
        if direction == -1:
            pass  # newI is the index of the luid in this case.
        elif direction == 1:
            at_i, at_range = self.get_affected(newI)
            newI = at_range[-1] + 1  # +1 so it is *after* any post_processes
        else:
            raise ValueError("The direction must be -1 or 1.")

        if newI < 0:
            raise ValueError("There is no '{}' {}".format(name, value))
        return self.insert(newI, action)

    def insert_where_luid(self, luid, action, direction=-1):
        return self.insert_where('luid', luid, action,
                                 direction=direction)

    def remove_where(self, name, value):
        '''
        Sequential arguments:
        luid -- Insert before this luid.
        '''
        newI = self._find_where(name, value)
        if newI < 0:
            raise ValueError("There is no '{}' {}".format(name, value))
        return self.remove(newI)

    def remove_where_luid(self, luid):
        return self.remove_where('luid', luid)

    def set_commit(self, luid, on):
        '''
        Turn the commit option of the version or process off or on.
        '''
        action = self.get_action(luid)
        echo0("NotYetImplemented: set_commit('{}', {})"
              "".format(luid, on))

    def set_verb(self, luid, verb):
        action = self.get_action(luid)
        current_verb = None
        current_verb = action['verb']
        if current_verb in VERSION_VERBS:
            raise ValueError(
                "The verb is {} so it can't change."
                "The action parameters aren't same as for other"
                " TRANSITION_VERBS."
                "".format(current_verb)
            )
        echo0("NotYetImplemented: set_verb('{}', {})"
              "".format(luid, verb))

    def to_dict(self):
        return {
            'project_dir': self.project_dir,
            'actions': self._actions,
        }


def main():
    pass


if __name__ == "__main__":
    echo0("Import this module into your program to use it.")
    main()
