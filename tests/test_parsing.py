#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  6 17:35:01 2022

@author: Jake "Poikilos" Gustafson
"""

from collections import OrderedDict
import os
import sys
import unittest

TESTS_DIR = os.path.dirname(__file__)
REPO_DIR = os.path.dirname(TESTS_DIR)

if __name__ == "__main__":
    sys.path.insert(0, REPO_DIR)

# import anewcommit  # noqa: E402
from anewcommit import (  # noqa: E402
    echo0,
    partial_format,
    split_format_chunks,
    split_statement,
    parse_statement,
    split_root,
    split_subs,
    get_format_keys,
    unformat,
)


class TestParsing(unittest.TestCase):
    def test_split_statement(self):
        self.assertEqual(
            split_statement('use "Primary Site" as main'),
            ["use", 'Primary Site', "as", "main"]
        )
        self.assertEqual(
            split_statement('use primary_site as main'),
            ["use", 'primary_site', "as", "main"]
        )
    def test_parse_statement(self):
        # 'sub' is deprecated
        # subCmd = parse_statement('sub "Primary Site"')
        # self.assertEqual(subCmd['keyword'], "sub")
        # self.assertEqual(subCmd['source'], "Primary Site")
        # self.assertTrue(subCmd.get('destination') is None)

        # Use "Primary Site" subfolder as program named "main":
        useCmd = parse_statement('use "Primary Site" as main')
        self.assertEqual(useCmd['keyword'], "use")
        self.assertEqual(useCmd['source'], "Primary Site")
        self.assertEqual(useCmd['destination'], "main")

        # Use root of source as program named "main":
        useCmd = parse_statement('use as main')
        self.assertEqual(useCmd['keyword'], "use")
        self.assertNotIn('source', useCmd)  # No source (implies ".")
        self.assertEqual(useCmd['destination'], "main")

        exceptionIsGood = False
        try:
            parse_statement("foo main")
        except ValueError as ex:
            if ("foo" in str(ex)) and ("keyword" in str(ex)):
                exceptionIsGood = True
            else:
                echo0(
                    "parse_statement threw an exception but did not state that"
                    "the foo keyword is invalid."
                )
                raise ex
        if not exceptionIsGood:
            raise RuntimeError(
                "parse_statement should throw an exception and state that"
                "the foo keyword is bad."
            )
        else:
            echo0("parse_statement succeeded in blocking foo.")

    def test_split_root(self):
        self.assertEqual(split_root("abc/def/ghi"), ["abc", "def/ghi"])
        self.assertEqual(split_root("/abc/def/ghi"), ["/abc", "def/ghi"])
        self.assertEqual(split_root("/abc"), ["/abc", ""])
        self.assertEqual(split_root("abc"), ["abc", ""])

    def test_split_subs(self):
        self.assertEqual(split_subs("a/b/c"), ["a", "b", "c"])
        self.assertEqual(split_subs("/a/b/c"), ["/a", "b", "c"])
        self.assertEqual(split_subs("a/b"), ["a", "b"])
        self.assertEqual(split_subs("/a/b"), ["/a", "b"])
        self.assertEqual(split_subs("a"), ["a"])
        self.assertEqual(split_subs("/a"), ["/a"])

    def test_get_format_keys(self):
        keys = get_format_keys("Hello {a}, the {abc} is {def}.")
        self.assertEqual(keys, ["a", "abc", "def"])
        keys = get_format_keys("Hello {a}, the {abc} is {def}")
        self.assertEqual(keys, ["a", "abc", "def"])
        keys = get_format_keys("{a}, the {abc} is {def}")
        self.assertEqual(keys, ["a", "abc", "def"])
        keys = get_format_keys("{a}{abc}{def}")
        self.assertEqual(keys, ["a", "abc", "def"])
        formatB = b"Hello {a}, the {abc} is {def}."
        keys = get_format_keys(formatB)
        self.assertEqual(keys, [b"a", b"abc", b"def"])

    def test_split_format_chunks(self):
        keys = split_format_chunks("Hello {a}, the {abc} is {def}.")
        self.assertEqual(keys, ["Hello ", "{a}", ", the ", "{abc}", " is ", "{def}", "."])
        keys = split_format_chunks("Hello {a}, the {abc} is {def}")
        self.assertEqual(keys, ["Hello ", "{a}", ", the ", "{abc}", " is ", "{def}"])
        keys = split_format_chunks("{a}, the {abc} is {def}")
        self.assertEqual(keys, ["{a}", ", the ", "{abc}", " is ", "{def}"])
        keys = split_format_chunks("{a}{abc}{def}")
        self.assertEqual(keys, ["{a}", "{abc}", "{def}"])
        formatB = b"Hello {a}, the {abc} is {def}."
        keys = split_format_chunks(formatB)
        self.assertEqual(keys, [b"Hello ", b"{a}", b", the ", b"{abc}", b" is ", b"{def}", b"."])

    def test_unformat(self):
        fmt = "Hello {a}, the {abc} is {def}."
        sentence = "Hello Jim, the dilithium is low."
        d = unformat(sentence, fmt)
        for key in d:
            assert isinstance(key, str)
        goodD = OrderedDict()
        # Add parts separately since order isn't guaranteed in Python 2
        #   for the keyword argument constructor of OrderedDict:
        goodD['a'] = "Jim"
        goodD['abc'] = "dilithium"
        goodD['def'] = "low"
        self.assertEqual(d, goodD)

        formatB = fmt.encode('utf-8')
        sentenceB = sentence.encode('utf-8')
        d = unformat(sentenceB, formatB)
        for key in d:
            # Must be str even if values are bytes/bytearray!
            assert isinstance(key, str)
        goodD = OrderedDict()
        # Add parts separately since order isn't guaranteed in Python 2
        #   for the keyword argument constructor of OrderedDict:
        goodD['a'] = b"Jim"
        goodD['abc'] = b"dilithium"
        goodD['def'] = b"low"
        self.assertEqual(d, goodD)

        sentenceB = b"mysql://user1:password1@host.example.com/db1"
        formatB = b"mysql://{user}:{password}@{host}/{db}"
        goodD = OrderedDict()
        goodD['user'] = b"user1"
        goodD['password'] = b"password1"
        goodD['host'] = b"host.example.com"
        goodD['db'] = b"db1"
        d = unformat(sentenceB, formatB)
        self.assertEqual(d, goodD)

    def test_partial_format(self):
        formatB = b"mysql://{user}:{password}@{host}/{db}"
        goodD = OrderedDict()
        goodD['user'] = b"user1"
        goodD['password'] = b"password1"
        goodD['host'] = b"host.example.com"
        goodD['db'] = b"db1"
        formatted = partial_format(formatB, goodD)
        self.assertEqual(formatted,
                         b"mysql://user1:password1@host.example.com/db1")


if __name__ == "__main__":
    unittest.main()
