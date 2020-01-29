# -*- coding: utf-8 -*-
"""
Tests for the L{cowsay} command.
"""

from stash.tests.stashtest import StashTestCase


class CowsayTests(StashTestCase):
    """
    Tests for L{cowsay}.
    """

    def test_help(self):
        """
        Test help output.
        """
        output = self.run_command("cowsay --help", exitcode=0)
        self.assertIn("cowsay", output)
        self.assertIn("--help", output)
        self.assertIn("usage:", output)

    def test_singleline_1(self):
        """
        Test for correct text in output.
        """
        output = self.run_command("cowsay test", exitcode=0)
        self.assertIn("test", output)
        self.assertNotIn("Hello, World!", output)
        self.assertEqual(output.count("<"), 1)
        self.assertEqual(output.count(">"), 1)

    def test_singleline_1(self):
        """
        Test for correct text in output.
        """
        output = self.run_command("cowsay Hello, World!", exitcode=0)
        self.assertIn("Hello, World!", output)
        self.assertNotIn("test", output)
        self.assertEqual(output.count("<"), 1)
        self.assertEqual(output.count(">"), 1)

    def test_stdin_read(self):
        """
        Test C{echo test | cowsay} printing C{test}.
        """
        output = self.run_command("echo test | cowsay", exitcode=0)
        self.assertIn("test", output)
        self.assertNotIn("Hello, World!", output)

    def test_stdin_ignore(self):
        """
        Test C{echo test | cowsay Hello, World!} printing C{Hello World!},
        """
        output = self.run_command("echo test | cowsay Hello, World!", exitcode=0)
        self.assertIn("Hello, World!", output)
        self.assertNotIn("test", output)

    def test_multiline_1(self):
        """
        Test for correct multiline output.
        """
        output = self.run_command("cowsay Hello,\\nWorld!", exitcode=0)
        self.assertIn("Hello,", output)
        self.assertIn("World!", output)
        self.assertNotIn("Hello,\nWorld!", output)  # text should be splitted allong the lines
        self.assertIn("/", output)
        self.assertIn("\\", output)
        self.assertNotIn("<", output)
        self.assertNotIn(">", output)

    def test_multiline_2(self):
        """
        Test for correct multiline output.
        """
        output = self.run_command("cowsay Hello,\\nWorld!\\nPython4Ever", exitcode=0)
        self.assertIn("Hello,", output)
        self.assertIn("World!", output)
        self.assertIn("Python4Ever", output)
        self.assertNotIn("Hello,\nWorld!\nPython4Ever", output)  # text should be splitted allong the lines
        self.assertIn("/", output)
        self.assertIn("\\", output)
        self.assertIn("|", output)
        self.assertNotIn("<", output)
        self.assertNotIn(">", output)
