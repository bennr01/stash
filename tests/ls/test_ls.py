# -*- coding: utf-8 -*-
"""
Tests for the L{ls} command.
"""

import os

from stash.tests.stashtest import StashTestCase


class LsTests(StashTestCase):
    """
    Tests for the L{ls} command.
    """

    def setUp(self):
        self.cwd = self.get_data_path()
        StashTestCase.setUp(self)

    def test_ls_cwd(self):
        """
        Test L{ls} of data/ sibling dir without specified path.
        """
        output = self.run_command("ls", exitcode=0)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertNotIn(".hidden", output)

    def test_ls_abspath(self):
        """
        Test L{ls} of data/ sibling dir with specified absolute path.
        """
        output = self.run_command("ls " + self.get_data_path(), exitcode=0)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertNotIn(".hidden", output)

    def test_ls_relpath_1(self):
        """
        Test L{ls} of data/ sibling dir with specified relative path C{'.'}.
        """
        output = self.run_command("ls .", exitcode=0)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertNotIn(".hidden", output)

    def test_ls_relpath_2(self):
        """
        Test L{ls} of data/ sibling dir with specified relative path C{'../data/'}.
        """
        output = self.run_command("ls ../data/", exitcode=0)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertNotIn(".hidden", output)

    def test_hidden(self):
        """
        Test L{ls} behavior with hidden dotfiles.
        """
        # 1. test ignoring
        output = self.run_command("ls", exitcode=0)
        self.assertNotIn(".hidden", output)
        # 2. test -a
        output = self.run_command("ls -a", exitcode=0)
        self.assertIn(".hidden", output)
        self.assertIn(".", output)
        self.assertIn("..", output)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)

    def test_ls_filename(self):
        """
        Test C{ls file1.txt file2.txt} showing C{file1.txt file2.txt}.
        """
        output = self.run_command("ls file1.txt file2.txt", exitcode=0)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertNotIn("otherfile.txt", output)

    def test_oneline(self):
        """
        Test C{ls -1}.
        """
        output = self.run_command("ls -1", exitcode=0)
        self.assertIn("file1.txt\n", output)
        self.assertIn("file2.txt\n", output)
        self.assertIn("otherfile.txt\n", output)
        self.assertNotIn(".hidden", output)

    def test_long(self):
        """
        Test C{ls -l}.
        """
        output = self.run_command("ls -l", exitcode=0)
        # we cant test the complete output, but we can still test for
        # filename existence and exitcode
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertIn("otherfile.txt", output)
        self.assertNotIn(".hidden", output)

    def test_la(self):
        """
        Test the C{la} alias for C{ls -a}
        """
        output = self.run_command("la", exitcode=0)
        self.assertIn(".hidden", output)
        self.assertIn(".", output)
        self.assertIn("..", output)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)

    def test_ll(self):
        """
        Test the C{ll} alias for C{ls -l}
        s"""
        output = self.run_command("ll", exitcode=0)
        # we cant test the complete output, but we can still test for
        # filename existence and exitcode
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertIn("otherfile.txt", output)
        self.assertIn(".hidden", output)
