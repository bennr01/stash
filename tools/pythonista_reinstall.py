# -*- coding: utf-8 -*-
"""
This tool will uninstall StaSh from pythonista and then download&run
L{getstash}.py

When running this script, the user will be prompted for the install
target.
"""

import os
import shutil
import tempfile

import requests
import six


def get_stash_dir():
    """
    Return the StaSh directory in pythonista.
    
    @return: path to the StaSh directory
    @rtype: L{str}
    """
    return os.path.join(os.path.expanduser("~"), "Documents", "site-packages", "stash")


def remove_stash():
    """
    Remove StaSh.
    """
    shutil.rmtree(get_stash_dir())


def install_stash(repo="ywangd", branch="master"):
    """
    Insall StaSh.
    
    This functions downloads and exectues L{getstash}.
    
    @param repo: name of github repository owner to download StaSh from
    @type repo: L{str}
    @param branch: name of github branch to download StaSh from
    @type branch: L{str}
    """
    if not "TMPDIR" in os.environ:
        os.environ["TMPDIR"] = tempfile.gettempdir()
    ns = {"_owner": repo, "_br": branch}
    exec(requests.get("https://bit.ly/get-stash").content, ns, ns)


def parse_gh_target(s):
    """
    Parse a github target string.
    
    @param s: string to parse
    @type s: L{str}
    @return: the github target as a tuple of (repo_owner, branch)
    @rtype: L{tuple} of (L{str}, L{str})
    """
    if s == "":
        return "ywangd", "master"
    s = s.replace("/", ":")
    if ":" not in s:
        s = "ywangd:" + s
    repo, branch = s.split(":")
    return repo, branch


def main():
    """
    The main function.
    """
    ts = six.moves.input("New target (repo:branch, empty for default): ")
    t = parse_gh_target(ts)
    if os.path.exists(get_stash_dir()):
        remove_stash()
    install_stash(*t)


if __name__ == "__main__":
    main()
