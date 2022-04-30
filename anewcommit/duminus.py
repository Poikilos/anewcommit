#!/usr/bin/env python
'''
Get statistics on folders.
'''
from __future__ import print_function
import sys
import os
import platform
import json
from datetime import (
    datetime,
    timezone,
)

ARGS = []
ARGS_BOOL = []


def error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def push_times(fileInfo, subPath):
    # fileInfo = results[path]
    sub_path_mtime = datetime.fromtimestamp(
        os.path.getmtime(subPath),
        tz=timezone.utc
    )

    # fileInfo['size'] += fileSizeK
    first_mtime = fileInfo.get('first_mtime')
    last_mtime = fileInfo.get('last_mtime')
    if ((first_mtime is None) or (sub_path_mtime < first_mtime)):
        fileInfo['first_mtime'] = sub_path_mtime
    if ((last_mtime is None) or (sub_path_mtime > last_mtime)):
        fileInfo['last_mtime'] = sub_path_mtime

fileInfoPropNames = ['size', 'first_mtime', 'last_mtime']

def du(path, subs, options, parentGitIgnoreLines):
    '''
    Specify a list of directories (subs) or a single directory
    (paths) and get the disk usage. The results will
    automatically ignore any files in .gitignore in the
    main directory, or in an override .gitignore in any
    subdirectory.
    - Only directories (not files) will be returned with totals
      except for any file path that is in options['paths'].
    - Each entry in paths must be an absolute path.
    '''
    results = {}
    # results['order'] = []
    if subs is None:
        if path is None:
            raise ValueError(
                "du requires either a path or subs."
            )
        if not os.path.isdir(path):
            raise ValueError(
                "The path \"{}\" is not a directory."
                "".format(path)
            )
        subs = os.listdir(path)
    elif path is not None:
        raise ValueError(
            "You must specify a path to use as"
            " a file or as a directory to traverse,"
            " or a list of subs, not both."
        )
    gitIgnoreLines = parentGitIgnoreLines
    if path is not None:
        tryIgnore = os.path.join(path, ".gitignore")
        if os.path.isfile(tryIgnore):
            gitIgnoreLines = []
            with open(tryIgnore, 'r') as ins:
                for rawL in ins:
                    line = rawL.strip()
                    if line.startswith("#"):
                        continue
                    if len(line) == 0:
                        continue
                    gitIgnoreLines.append(line)
    path_mtime = None
    if path is not None:
        if results.get(path) is None:
            results[path] = {}
        if results[path].get('size') is None:
            results[path]['size'] = 0

        path_mtime = datetime.fromtimestamp(
            os.path.getmtime(path),
            tz=timezone.utc
        )

        '''
        if results[path].get('last_mtime') is None:
            # results[path]['last_mtime'] = None
            results[path]['last_mtime'] = sys.float_info.min
            # ^ It starts low so the first value found overrides it.
            # results[path]['last_mtime'] = path_mtime
        if results[path].get('first_mtime') is None:
            # results[path]['first_mtime'] = None
            results[path]['first_mtime'] = sys.float_info.max
            # ^ It starts high so first value found overrides it.
            # results[path]['first_mtime'] = path_mtime
        '''
        # Only set to path_mtime at end if nothing was found.
    for sub in subs:
        subPath = sub
        if path is not None:
            subPath = os.path.join(path, sub)
        else:
            if not os.path.exists(sub):
                raise ValueError(
                    "Error: sub \"{}\" doesn't exist."
                    "".format(sub)
                )
        if os.path.islink(subPath):
            error("* ignoring symlink \"{}\"".format(subPath))
            continue
        if os.path.isfile(subPath):
            try:
                fileSize = os.path.getsize(subPath)
                # ^ Raises OSError if file doesn't exist or is inaccessible
            except OSError as ex:
                error(str(ex))
                return None
            fileSizeK = float(fileSize) / 1024.0
            # fileSizeK = int(fileSize / 1024)
            if subPath in options['paths']:
                if results.get(subPath) is None:
                    results[subPath] = {}
                results[subPath]['size'] = fileSizeK
            else:
                if path is None:
                    raise RuntimeError(
                        "The path is None but the file \"{}\" is not"
                        " in the specified paths (This should never"
                        " happen, since only specified subs should"
                        " end up here without a parent)."
                        "".format(path)
                    )
            if path is not None:
                results[path]['size'] += fileSizeK
                push_times(results[path], subPath)
            '''
            else:
                results['order'].append(subPath)
            '''
        else:
            childResults = du(subPath, None, options, gitIgnoreLines)
            if path is not None:
                # This is ok since du can only affect subPath not path:
                childSizeF = childResults[subPath]['size']
                results[path]['size'] += round(childSizeF)
            for k, v in childResults.items():
                if results.get(k) is not None:
                    raise RuntimeError("\"{}\" was already traversed."
                                       "".format(k))
                results[k] = v
                # ^ k can never be path, so this can't affect this depth
                #   (The exception can never happen if code is correct,
                #   perhaps unless a user specifies the same path twice
                #   or a path and directory containing it).
            '''
            if path is not None:
                for k in childResults['order']:
                    # Only count the next deeper tier; otherwise
                    # subs will get counted twice.
                    results[path]['size'] += childResults[k]['size']
            else:
                results['order'].append(subPath)
            '''
    if path is not None:
        results[path]['size'] = round(results[path]['size'])
        if results[path].get('last_mtime') is None:
            results[path]['last_mtime'] = path_mtime
        if results[path].get('first_mtime') is None:
            results[path]['first_mtime'] = path_mtime

    return results


def main():
    root = None
    options = {}
    forwardedArgs = []
    setName = None
    paths = []
    for argI in range(1, len(sys.argv)):
        arg = sys.argv[argI]
        if setName is not None:
            options[setName] = arg
            setName = None
        elif arg.startswith("-"):
            if arg in ARGS:
                if arg in ARGS_BOOL:
                    options[arg] = True
                else:
                    setName = arg
            else:
                forwardedArgs.append(arg)
        else:
            if not os.path.exists(arg):
                error("Error: \"{}\" does not exist."
                      "".format(arg))
                exit(1)
            # paths.append(os.path.abspath(arg))
            paths.append(arg)
    if setName is not None:
        error("You must provide a value after {}"
              "".format(setName))
        exit(1)
    '''
    if platform.system() == "Windows":
        if len(forwardedArgs) > 0:
            error("Unknown arguments aren't possible"
                  "to forward on OS without"
                  " the du command: {}"
                  "".format(forwardedArgs))
    '''
    if len(forwardedArgs) > 0:
        error("Unknown arguments aren't implemented: {}"
              "".format(forwardedArgs))

    error("forwardedArgs: {}".format(forwardedArgs))
    error("options: {}".format(options))
    if len(paths) == 0:
        # path = os.path.abspath(".")
        path = "."
        error("* You didn't specify a path,"
              " so results will be for: \"{}\""
              "".format(path))
        paths.append(path)
    options['paths'] = paths
    # ^ Store this separately since only files specified are
    #   returned individually by du (otherwise, only
    #   directories are obtained)
    results = du(None, paths, options, None)
    error("results:")
    print(json.dumps(results, indent=2, default=str))
    # ^ default=str prevents:
    #   "TypeError: Object of type datetime is not JSON serializable"


if __name__ == "__main__":
    main()
