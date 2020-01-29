# -*- coding: utf-8 -*-
"""
Tests for the L{cat} command.
"""
import os
from unittest import expectedFailure

from stash.tests.stashtest import StashTestCase


class CatTests(StashTestCase):
    """
    Tests for the L{cat} command.
    """

    def setUp(self):
        self.cwd = self.get_data_path()
        StashTestCase.setUp(self)

    def read_data_file(self, fn):
        """
        Returns the content of the file C{fn} in the data sibling dir.
        
        @param fn: path of file to read, relative to the data/ sibling
        dir
        @type fn: L{str}
        @return: the content of thje file
        @rtype: L{str}
        """
        fp = os.path.join(self.get_data_path(), fn)
        with open(fp, "r") as fin:
            content = fin.read()
        return content

    def test_help(self):
        """
        Test C{cat --help}.
        """
        output = self.run_command("cat --help", exitcode=0)
        self.assertIn("cat", output)
        self.assertIn("-h", output)
        self.assertIn("--help", output)
        self.assertIn("files", output)

    def test_cat_file(self):
        """
        Test C{cat <somefile>}.
        """
        output = self.run_command("cat somefile.txt", exitcode=0)
        expected = self.read_data_file("somefile.txt")
        self.assertEqual(output, expected)

    def test_cat_multi_files(self):
        """
        Test C{cat <somefile> <otherfile>}.
        """
        output = self.run_command("cat somefile.txt otherfile.txt", exitcode=0)
        expected = self.read_data_file("somefile.txt") + self.read_data_file("otherfile.txt")
        self.assertEqual(output, expected)

    def test_cat_stdin(self):
        """
        Test C{cat <somefile> | cat -}.
        """
        # we test 'cat <someifle>' in a seperate test, so we can use it here
        output = self.run_command("cat somefile.txt | cat -", exitcode=0)
        expected = self.read_data_file("somefile.txt")
        self.assertEqual(output, expected)

    def test_cat_nonexistent(self):
        """
        Test C{cat <some file which does not exist>}.
        """
        output = self.run_command("cat invalid.txt", exitcode=1)
        self.assertIn("cat: ", output)
        self.assertIn("No such file or directory: ", output)
        self.assertIn("invalid.txt", output)

    def test_cat_nonascii(self):
        """
        Test C{cat <some file containing non-ascii characters.>}.
        """
        output = self.run_command("cat nonascii.txt", exitcode=0).replace("\n", "")
        self.assertEqual(output, u"äöüß")
