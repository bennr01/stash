"""tests for the git command."""
import os
import tempfile
import unittest

from stash.tests.stashtest import StashTestCase, requires_network


class GitTests(StashTestCase):
    """Tests for the git command."""
    def setUp(self):
        """setup the tests"""
        self.cwd = os.path.join(tempfile.gettempdir(), "gittest")
        if not os.path.exists(self.cwd):
            os.makedirs(self.cwd)
        StashTestCase.setUp(self)
        self.empty_cwd()
    
    def empty_cwd(self):
        """delete everything in self.cwd)."""
        self.run_command("rm -r " + os.path.join(self.cwd, "*"))  # ignore exitcode in case it was already empty
        self.run_command("rm -r .git")
    
    def test_git_status_fail_in_empty(self):
        """ensure 'git status' fails in an empty directory."""
        # we need this for other tests
        dirname = "git_status_empty_fail"
        # create a new directory
        if os.path.exists(dirname):
            self.run_command("rm " + dirname, exitcode=0)
        self.run_command("mkdir " + dirname, exitcode=0)
        self.cd(dirname)
        # check that the new directory does not contain a .git directory
        files = os.listdir(".")
        self.assertNotIn(".git", files)
        # check that git status exits with 1
        self.run_command("git status", exitcode=1)
    
    def test_git_init_cwd(self):
        """test 'git init'."""
        reponame = "init_cwd_test"
        # create a new directory for the repo and cd into it
        if os.path.exists(reponame):
            self.run_command("rm " + reponame, exitcode=0)
        self.run_command("mkdir " + reponame, exitcode=0)
        self.cd(reponame)
        # check that the new directory does not already contain a .git directory
        files = os.listdir(".")
        self.assertNotIn(".git", files)
        # init repo
        self.run_command("git init", exitcode=0)
        # check that .git exists
        files = os.listdir(".")
        self.assertIn(".git", files)
        # check that git status exits with 0
        self.run_command("git status", exitcode=0)
    
    def test_git_init_path(self):
        """test 'git init <path>'."""
        reponame = "init_path_test"
        # create a new directory for the repo and cd into it
        if os.path.exists(reponame):
            self.run_command("rm " + reponame, exitcode=0)
        self.run_command("mkdir " + reponame, exitcode=0)
        self.cd(reponame)
        # check that the new directory does not already contain a .git directory
        files = os.listdir(".")
        self.assertNotIn(".git", files)
        # cd out
        self.cd("..")
        # init repo
        self.run_command("git init " + reponame, exitcode=0)
         # check that .git was not created in cwd
        files = os.listdir(".")
        self.assertNotIn(".git", files)
        # cd into repo
        self.cd(reponame)
        # check that .git exists
        files = os.listdir(".")
        self.assertIn(".git", files)
        # check that git status exits with 0
        self.run_command("git status", exitcode=0)
    
    def test_git_init_path_wo_mkdir(self):
        """test 'git init <path>' with nonexistent path."""
        reponame = "init_path_wo_mkdir_test"
        # init repo
        self.run_command("git init " + reponame, exitcode=0)
         # check that .git was not created in cwd
        files = os.listdir(".")
        self.assertNotIn(".git", files)
        # cd into repo
        self.cd(reponame)
        # check that .git exists
        files = os.listdir(".")
        self.assertIn(".git", files)
        # check that git status exits with 0
        self.run_command("git status", exitcode=0)
    
    @unittest.expectedFailure  # some trouble with github closing the connection immediately
    @requires_network
    def test_git_clone_http(self):
        """test git clone on a HTTP target"""
        remote = "http://github.com/ywangd/stash.git"
        target = "stash"
        # ensure there is no old target directory
        files = os.listdir(".")
        self.assertNotIn(target, files)
        # clone
        self.run_command("git clone " + remote, exitcode=0)
        # test
        self.cd(target)
        files = os.listdir(".")
        self.assertIn(".git", files)
        self.run_command("git status", exitcode=0)
    
    @requires_network
    def test_git_clone_https(self):
        """test git clone on a HTTPS target"""
        remote = "https://github.com/ywangd/stash.git"
        target = "stash"
        # ensure there is no old target directory
        files = os.listdir(".")
        self.assertNotIn(target, files)
        # clone
        self.run_command("git clone " + remote, exitcode=0)
        # test
        self.cd(target)
        files = os.listdir(".")
        self.assertIn(".git", files)
        self.run_command("git status", exitcode=0)
    
    @requires_network
    def test_git_clone_https_custom_target(self):
        """test git clone on a HTTPS target"""
        remote = "https://github.com/ywangd/stash.git"
        target = "testclone"
        # ensure there is no old target directory
        files = os.listdir(".")
        self.assertNotIn(target, files)
        # clone
        self.run_command("git clone " + remote + " " + target, exitcode=0)
        # test
        self.cd(target)
        files = os.listdir(".")
        self.assertIn(".git", files)
        self.run_command("git status", exitcode=0)
    
    # TODO: tests for git clone on ssh
    