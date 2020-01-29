# -*- coding: utf-8 -*-
"""
Tests for the L{sha256sum} command.
"""

import os

from stash.tests.stashtest import StashTestCase


class Sha256sumTests(StashTestCase):
    """
    Tests for the L{sha256sum} command.
    """

    def setUp(self):
        self.cwd = self.get_data_path()
        StashTestCase.setUp(self)

    def test_help(self):
        """
        Test C{sha256sum --help}.
        """
        output = self.run_command("sha256sum --help", exitcode=0)
        # check for code words in output
        self.assertIn("sha256sum", output)
        self.assertIn("-h", output)
        self.assertIn("-c", output)

    def test_filehash(self):
        """
        Tests the hashes of the files in C{data/}.
        """
        fp = self.get_data_path()
        for fn in os.listdir(fp):
            if "." in fn:
                # file used for something else
                continue
            expected_hash = fn
            fullp = os.path.join(fp, fn)
            output = self.run_command("sha256sum " + fullp, exitcode=0)
            result = output.split(" ")[0]
            self.assertEqual(result, expected_hash)

    def test_checkhash(self):
        """
        Test C{sha256sum -c}.
        """
        output = self.run_command("sha256sum -c results.sha256sum", exitcode=0)
        self.assertIn("Pass", output)
        self.assertNotIn("Fail", output)

    def test_checkhash_fail(self):
        """
        Test the failure of C{sha256sum -c} with invalid data.
        """
        output = self.run_command("sha256sum -c wrong_results.sha256sum", exitcode=1)
        self.assertIn("Pass", output)  # some files should have the correct hash
        self.assertIn("Fail", output)

    def test_hash_stdin_implicit(self):
        """
        Test hashing of stdin without arg.
        """
        output = self.run_command("echo test | sha256sum", exitcode=0).replace("\n", "")
        expected = "f2ca1bb6c7e907d06dafe4687e579fce76b37e4e93b7605022da52e6ccc26fd2"
        self.assertEqual(output, expected)

    def test_hash_stdin_explicit(self):
        """
        Test hashing of stdin with C{-} argument.
        """
        output = self.run_command("echo test | sha256sum -", exitcode=0).replace("\n", "")
        expected = "f2ca1bb6c7e907d06dafe4687e579fce76b37e4e93b7605022da52e6ccc26fd2"
        self.assertEqual(output, expected)
