# -*- coding: utf-8 -*-
"""
Tests for the L{echo} command.
"""

from unittest import expectedFailure

from stash.tests.stashtest import StashTestCase


class EchoTests(StashTestCase):
    """
    Tests for the L{echo} command.
    """

    def do_echo(self, s):
        """
        Echo a string and return the echoed output.
        
        @param s: string to echo
        @type s: L{str}
        @return s: output of echo command
        @rtype: L{str}
        """
        return self.run_command("echo " + s, exitcode=0)

    def test_simple(self):
        """
        Test C{echo test}.
        """
        o = self.do_echo("test")
        self.assertEqual(o, "test\n")

    def test_multi(self):
        """
        Test C{echo test1 test2 test}.
        """
        o = self.do_echo("test1 test2 test3")
        self.assertEqual(o, "test1 test2 test3\n")

    def test_help_ignore(self):
        """
        Test that C{-h} and C{--help} will be ignored by echo.
        """
        ho = self.do_echo("-h")
        self.assertEqual(ho, "-h\n")
        helpo = self.do_echo("--help")
        self.assertEqual(helpo, "--help\n")

    def test_empty(self):
        """
        Test the behavior without arguments.
        """
        output = self.run_command("echo", exitcode=0)
        self.assertEqual(output, "\n")

    @expectedFailure
    def test_non_ascii(self):
        """
        Test L{echo} with non-ascii characters.
        """
        output = self.do_echo(u"Non-Ascii: äöüß end")
        self.assertEqual(output, u"Non-Ascii: äöüß end\n")
