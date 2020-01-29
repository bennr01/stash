# -*- coding: utf-8 -*-
"""
Tests for the L{ping} command.

For unknown reasons, some of these tests fail outsideo of iOS
"""

import time
import unittest

from stash.tests.stashtest import StashTestCase, requires_network


class PingTests(StashTestCase):
    """
    Tests for the L{ping} command.
    """

    def test_help(self):
        """
        Test C{ping --help}.
        """
        output = self.run_command("ping --help", exitcode=0)
        self.assertIn("ping", output)
        self.assertIn("-h", output)
        self.assertIn("--help", output)
        self.assertIn("-c", output)
        self.assertIn("--count", output)
        self.assertIn("-W", output)
        self.assertIn("--timeout", output)

    @unittest.expectedFailure
    @requires_network
    def test_ping_normal(self):
        """
        Test C{ping <ip>}.
        """
        target = "8.8.8.8"
        output = self.run_command("ping " + target, exitcode=0)
        self.assertIn("got ping in " + target, output)
        self.assertNotIn("failed", output)

    @unittest.expectedFailure
    @requires_network
    def test_count(self):
        """
        Test C{ping <target> --count <n>}.
        """
        target = "8.8.8.8"
        for n in (1, 3, 5):
            output = self.run_command("ping " + target + " --count " + str(n), exitcode=0)
            self.assertIn("got ping in " + target, output)
            self.assertNotIn("failed", output)
            c = output.count("got ping in")
            self.assertEqaual(n, c)

    @unittest.expectedFailure
    @requires_network
    def test_interval(self):
        """
        Test C{ping <target> --interval <n>}.
        """
        target = "8.8.8.8"
        c = 3
        for t in (1, 5, 10):
            st = time.time()
            output = self.run_command("ping " + target + " --count " + str(c) + " --interval " + str(t), exitcode=0)
            et = time.time()
            dt = et - st
            self.assertIn("got ping in " + target, output)
            self.assertNotIn("failed", output)
            n = output.count("got ping in")
            self.assertEqaual(n, c)
            mintime = c * t
            maxtime = c * t + 5
            self.assertGreaterEqual(dt, mintime)
            self.assertLessEqual(dt, maxtime)

    @unittest.expectedFailure
    @unittest.skip("Test not implemented")
    def test_timeout():
        """
        Test C{ping <target> --timeout <t>}.
        
        B{Not implemented!}
        """
        # no idea how to implement a test for this case
        raise NotImplementedError
