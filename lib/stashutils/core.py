# -*- coding: utf-8 -*-
"""
Core utilities for StaSh-scripts.
"""
import threading
import imp
import os

from stash.system import shthreads


def get_stash():
    """
    Returns the currently active StaSh-instance.
    
    Returns None if it can not be found.
    This is useful for modules.
    
    :return: the current StaSh instance or None
    :rtype: L{stash.core.StaSh} or L{None}
    """
    if "_stash" in globals():
        return globals()["_stash"]
    for thr in threading.enumerate():
        if isinstance(thr, shthreads.ShBaseThread):
            ct = thr
            while not ct.is_top_level():
                ct = ct.parent
            return ct.parent.stash
    return None


def load_from_dir(dirpath, varname):
    """
    Returns a list of all variables named 'varname' in .py files in a directofy 'dirname'.
    
    @param dirpath: path to search/load
    @type dirpath: L{str}
    @param varname: name of variables to search
    @type varname: L{str}
    @return: a list of values of these variables
    @rtype: L{list}
    """
    if not os.path.isdir(dirpath):
        return []
    ret = []
    for fn in os.listdir(dirpath):
        fp = os.path.join(dirpath, fn)
        if not os.path.isfile(fp):
            continue
        with open(fp, "r") as fin:
            mod = imp.load_source(fn[:fn.index(".")], fp, fin)
        if not hasattr(mod, varname):
            continue
        else:
            ret.append(getattr(mod, varname))
    return ret
