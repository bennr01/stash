"""tests for the git command."""
import os
import tempfile

from stash.tests.stashtest import StashTestCase


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
        self.run_command("cd " + dirname, exitcode=0)
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
        self.run_command("cd " + reponame, exitcode=0)
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
        self.run_command("cd " + reponame, exitcode=0)
        # check that the new directory does not already contain a .git directory
        files = os.listdir(".")
        self.assertNotIn(".git", files)
        # cd out
        self.run_command("cd ..", exitcode=0)
        # init repo
        self.run_command("git init " + reponame, exitcode=0)
         # check that .git was not created in cwd
        files = os.listdir(".")
        self.assertNotIn(".git", files)
        # cd into repo
        self.run_command("cd " + reponame, exitcode=0)
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
        self.run_command("cd " + reponame, exitcode=0)
        # check that .git exists
        files = os.listdir(".")
        self.assertIn(".git", files)
        # check that git status exits with 0
        self.run_command("git status", exitcode=0)