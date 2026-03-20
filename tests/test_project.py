#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import unittest

if __name__ == "__main__":
    TESTS_DIR = os.path.dirname(__file__)
    REPO_DIR = os.path.dirname(TESTS_DIR)
    sys.path.insert(0, REPO_DIR)

import anewcommit
from anewcommit import (
    echo0,
    set_verbosity,
    ANCProject,
    DEFAULT_VERSION_VERB,
)

myDir = os.path.dirname(os.path.abspath(__file__))
test_data = os.path.join(myDir, "data")


class TestProject(unittest.TestCase):
    def testRanges(self):
        project = ANCProject()

        project._actions = [
            {
                'luid': "1",
                'verb': DEFAULT_VERSION_VERB,
                'path': os.path.join(test_data, "project", "1")
            },
            {
                'luid': "2",
                'verb': DEFAULT_VERSION_VERB,
                'path': os.path.join(test_data, "project", "2")
            },
            {
                'luid': "3",
                'verb': "pre_process",
            },
            {
                'luid': "4",
                'verb': DEFAULT_VERSION_VERB,
                'path': os.path.join(test_data, "project", "4")
            },
            {
                'luid': "5",
                'verb': "post_process",
            },
            {
                'luid': "6",
                'verb': DEFAULT_VERSION_VERB,
                'path': os.path.join(test_data, "project", "6")
            },
            {
                'luid': "7",
                'verb': DEFAULT_VERSION_VERB,
                'path': os.path.join(test_data, "project", "7")
            },
        ]
        ranges = project.get_ranges()
        self.assertEqual(len(ranges), 5)
        self.assertEqual(ranges[0], [0])
        self.assertEqual(ranges[1], [1])
        self.assertEqual(ranges[2], [2, 3, 4])
        self.assertEqual(ranges[3], [5])
        self.assertEqual(ranges[4], [6])


if __name__ == "__main__":
    unittest.main()
