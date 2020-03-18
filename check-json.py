#!/usr/bin/env python
"""
Provide json filename(s) as parameter(s)
Parse any JSON Exceptions to provide JSON linting functionality.
"""
# name=$1
# echo "* checking '$name'..."
# pycodestyle-3 $name
import json
import sys
# import re
import os
path = ""
trues = ["true", "yes", "on", "1"]


def get_between(haystack, starter, ender):
    """
    Find text between a start flag and end flag. Get the location of the
    desired substring and the location of the entire
    field separately.

    Example:
    If starter is "line " and ender is " " and haystack contains
    "line 1 ", then the result is a dict where:
    result_i and result_end define a slice of haystack that is equal to
    "value" string in the returned dict, and field_i and field_end are
    the slice values for the entire field including starter and ender.
    - If haystack does not contain starter ender after it, then the
      return will have None for the value of "value".
    """
    result_i = None
    result_end = None
    field_i = None
    field_end = None
    value = None
    field_i = haystack.find(starter)
    if field_i > -1:
        result_end = haystack.find(ender, field_i + len(starter))
        if result_end > 0:
            result_i = field_i + len(starter)
            field_end = result_end + len(ender)
            value = haystack[result_i:result_end]
    return {
        "result_i": result_i,
        "result_end": result_end,
        "field_i": field_i,
        "field_end": field_end,
        "value": value
    }


def lint_json(path, quiet_if_valid=False):
    try:
        with open(path) as json_file:
            data = json.load(json_file)
            if not quiet_if_valid:
                print("\"{}\" is valid JSON.".format(path))
    except json.decoder.JSONDecodeError as e:
        # str(e) is something like:
        # Expecting ',' delimiter: line 9 column 5 (char 207)
        e_s = str(e)
        # line_match = re.search("(?<=\b: line \s)(\w+)", e_s)
        # if line_match:
        #     INFO: line_match.group(0) is "line "
        #     print(line_match)
        # ^ See <https://stackoverflow.com/questions/546220/
        # how-to-match-the-first-word-after-an-expression-with-regex>
        line = -1
        column = -1
        results = {}
        parts = {
            "line": {
                "starter": ": line ",
                "ender": " "
            },
            "column": {
                "starter": " column ",
                "ender": " "
            }
        }
        error_end = None
        for k, part in parts.items():
            match = get_between(e_s, part["starter"], part["ender"])
            if match["value"] is not None:
                if k == "line":
                    line = int(match["value"])
                    error_end = match["field_i"]
                elif k == "column":
                    column = int(match["value"])
                else:
                    raise RuntimeError("Field '{}' is not"
                                       " implemented.".format(k))
        msg = e_s
        if error_end is not None:
            msg = e_s[:error_end]
        print("{}:{}:{}: {}".format(path, line, column, msg))


def to_bool(s):
    if s is True:
        return True
    elif s is False:
        return False
    elif s == 0:
        return False
    elif s == 1:
        return True
    elif s.lower() in trues:
        return True
    return False


def main():
    settings = {}
    if len(sys.argv) < 2:
        print("[check-json.py] You did not supply any arguments.")
    settings["quiet_if_valid"] = False
    bools = ["quiet_if_valid"]
    paths = []
    name = None
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]
        if arg.startswith("--"):
            arg_s = arg[2:]  # skip "--"
            sign_i = arg_s.find("=")
            if sign_i == 0:
                raise ValueError("There is an unexpected '=' at the start of an argument")
            elif sign_i > 0:
                name = arg_s[:sign_i]
                v = arg_s[sign_i+1:]
                if name in bools:
                    v = to_bool(v)
                settings[name] = v
                name = None  # don't wait for a value in a following arg
        else:
            if name != None:
                v = arg
                if name in bools:
                    v = to_bool(v)
                settings[name] = v
                name = None
            else:
                paths.append(arg)
    # print("settings: " + str(settings))
    for path in paths:
        lint_json(path, quiet_if_valid=settings["quiet_if_valid"])


if __name__ == "__main__":
    main()
