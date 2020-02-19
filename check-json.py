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


def lint_json(path):
    try:
        with open(path) as json_file:
            data = json.load(json_file)
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


t = "/home/owner/git/anewcommit/conf.d/linux-minetest-kit/settings.json"
if len(sys.argv) < 2:
    print("[check-json.py] You did not supply any arguments.")
    if os.path.isfile(t):
        lint_json(t)

for i in range(1, len(sys.argv)):
    lint_json(sys.argv[i])
