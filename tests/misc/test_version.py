# -*- coding: utf-8 -*-
"""
Tests for the L{version} command.
"""

import platform

from stash.tests.stashtest import StashTestCase


class VersionTests(StashTestCase):
    """
    Tests for the L{version} command.
    """

    def test_keys(self):
        """
        Ensure keys like C{core.py} are in the output of L{version}.
        """
        output = self.run_command("version", exitcode=0)
        self.assertIn("StaSh", output)
        self.assertIn("Python", output)
        self.assertIn("UI", output)
        self.assertIn("root", output)
        self.assertIn("core.py", output)
        # skip iOS version because we run the tests on linux (i think)
        self.assertIn("Platform", output)
        self.assertIn("SELFUPDATE_TARGET", output)
        self.assertIn("BIN_PATH", output)
        self.assertIn("PYTHONPATH", output)
        self.assertIn("Loaded libraries", output)

    def test_correct_py_version(self):
        """
        Test that the correct python version will be reported.
        """
        output = self.run_command("version", exitcode=0)
        self.assertIn(platform.python_version(), output)

    def test_correct_stash_version(self):
        """
        Test that the correct stash version will be reported.
        """
        output = self.run_command("version", exitcode=0)
        self.assertIn(self.stash.__version__, output)
