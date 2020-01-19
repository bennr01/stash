#!python2
# -*- coding: utf-8 -*-
"""Rewrite docstrings to use @param foo: style docstrings"""
import os
import argparse
import re

try:
    from .common import get_stash_dir
except (ImportError, ValueError):
    from common import get_stash_dir


def is_doc_line(s):
    """
    Check if the given line is a doc line.
    @param s: line to check
    @type s: str
    @return: whether the given line is a docstring line or not
    @rtype:  bool
    """
    return re.match(".*:(param|type|return|rtype|attr|raises).*:", s)


def rewrite_all_docstrings(p, recursive=False, ignore_nonpy=False):
    """
    Rewrite all files in a directory.
    @param p: path to directory
    @type p: str
    @param recursive: whether to descend into subdirectories or not
    @type recursive: bool
    @param ignore_nonpy: skip files not ending with .py
    @type ignore_nonpy: bool
    """
    for fn in os.listdir(p):
        fp = os.path.join(p, fn)
        if os.path.isdir(fp):
            if recursive:
                rewrite_all_docstrings(fp, recursive=recursive, ignore_nonpy=ignore_nonpy)
        else:
            if (not fn.endswith(".py") and ignore_nonpy):
                # skip
                continue
            rewrite_file_docstrings(fp)


def rewrite_file_docstrings(p):
    """
    Rewrite the docstrings in a file.
    @param p: path to the file
    @type p: str
    """
    with open(p, "r") as fin:
        lines = fin.readlines()
    with open(p, "w") as fout:
        for line in lines:
            if is_doc_line(line):
                nl = rewrite_docline(line)
                print("Rewrite '{}' -> '{}'".format(line.replace("\n", ""), nl.replace("\n", "")))
                fout.write(nl)
            else:
                fout.write(line)


def rewrite_docline(line):
    """
    Rewrite a line in a docstring.
    @param line: line to rewrite
    @type line: str
    @return: the rewriten line
    @rtype: str
    """
    return line.replace(":", "@", 1)


def main():
    """the main function"""
    parser = argparse.ArgumentParser(description="Rewrite docstrings")
    parser.add_argument("-p", "--path", action="store", help="path to file(s), defaults to StaSh root")
    parser.add_argument("-r", "--recursive", action="store_true", help="descend into subdirectories")
    parser.add_argument("--py-only", dest="pyonly", action="store_true", help="ignore non .py files")

    ns = parser.parse_args()

    if ns.path is not None:
        path = ns.path
    else:
        path = get_stash_dir()

    rewrite_all_docstrings(path, recursive=ns.recursive, ignore_nonpy=ns.pyonly)


if __name__ == "__main__":
    main()
