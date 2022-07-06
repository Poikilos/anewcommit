#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  6 17:35:01 2022

@author: Jake "Poikilos" Gustafson
"""

import unittest
import sys
import os

import anewcommit
from anewcommit import (
    echo0,
    split_statement,
    parse_statement,
)

class TestParsing(unittest.TestCase):
    def test_split_statement(self):
        self.assertEqual(
            split_statement('use "Primary Site" as main'),
            ['use','Primary Site','as','main']
        )
        self.assertEqual(
            split_statement('use primary_site as main'),
            ['use','primary_site','as','main']
        )
    def test_parse_statement(self):
        subCmd = parse_statement('sub "Primary Site"')
        self.assertEqual(subCmd['command'], 'sub')
        self.assertEqual(subCmd['source'], 'Primary Site')
        self.assertTrue(subCmd.get('destination') is None)

        useCmd = parse_statement('use "Primary Site" as main')
        self.assertEqual(useCmd['command'], 'use')
        self.assertEqual(useCmd['source'], 'Primary Site')
        self.assertEqual(useCmd['destination'], 'main')

        exceptionIsGood = False
        try:
            parse_statement('foo main')
        except ValueError as ex:
            if ("foo" in str(ex)) and ("command" in str(ex)):
                exceptionIsGood = True
            else:
                echo0(
                    "parse_statement threw an exception but did not state that"
                    "the foo command is invalid."
                )
                raise ex
        if not exceptionIsGood:
            raise RuntimeError(
                "parse_statement should throw an exception and state that"
                "the foo command is bad."
            )
        else:
            echo0("parse_statement succeeded in blocking foo.")
