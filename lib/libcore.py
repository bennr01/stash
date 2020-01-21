# -*- coding: utf-8 -*-
"""
Various utility functions shared by commands.
"""

import os
import fileinput

try:
    unicode
except NameError:
    unicode = str


def collapseuser(path):
    """
    Reverse of os.path.expanduser.
    
    Return path relative to ~, if uch representation is meaningful.
    If path is not ~ or a subdirectory, the absolute path will be
    returned.
    
    @param path: path to collapse
    @type path: L{six.text_type}
    @return: the collapsed path
    @rtype: L{six.text_type}
    """
    path = os.path.abspath(unicode(path))
    home = os.path.expanduser("~")
    if os.path.exists(os.path.expanduser("~/Pythonista.app")):
        althome = os.path.dirname(os.path.realpath(os.path.expanduser("~/Pythonista.app")))
    else:
        althome = home

    if path.startswith(home):
        collapsed = os.path.relpath(path, home)
    elif path.startswith(althome):
        collapsed = os.path.relpath(path, althome)
    else:
        collapsed = path

    return "~" if collapsed == "." else os.path.join("~", collapsed)


def get_lan_ip():
    """
    Return the IP in the LAN network.
    
    @return: the ip
    @rtype: L{str} or L{None}
    """
    try:
        from objc_util import ObjCClass
        NSHost = ObjCClass('NSHost')
        addresses = []
        for address in NSHost.currentHost().addresses():
            address = str(address)
            if 48 <= ord(address[0]) <= 57 and address != '127.0.0.1':
                addresses.append(address)
        return '   '.join(addresses)

    except ImportError:
        return ''


def input_stream(files=()):
    """
    Handles input files similar to fileinput.
    
    The advantage of this function is it recovers from errors if one
    file is invalid and proceed with the next file
    
    @param files: files to read
    @type files: L{list} or L{tuple} of L{io.IOBase}
    @return: a generator yield a tuple of (line or None, filename, lineno)
    @rtype: L{types.GeneratorType} yielding L{tuple} of (L{str} or L{None},
    L{str}, L{int} or L{Exception})
    """
    fileinput.close()
    try:
        if not files:
            for line in fileinput.input(files):
                yield line, '', fileinput.filelineno()

        else:
            while files:
                thefile = files.pop(0)
                try:
                    for line in fileinput.input(thefile):
                        yield line, fileinput.filename(), fileinput.filelineno()
                except IOError as e:
                    yield None, fileinput.filename(), e
    finally:
        fileinput.close()


def sizeof_fmt(num, base=1024, suffix="iB"):
    """
    Return a human readable string describing the size of something.
    
    @param num: the number in machine-readable form
    @type num: L{int}
    @param base: base of each unit (e.g. 1024 for KiB -> MiB)
    @type base: L{int}
    @param suffix: suffix to add. By default, this is "iB". It is skipped on the first unit.
    @type suffix: L{str}
    @return: the humand readable size
    @rtype: L{str}
    """
    use_suffix = False  # skip suffix on first element
    for unit in ['B', 'K', 'M', 'G']:
        if use_suffix:
            unit += suffix
        else:
            use_suffix = True
        if num < base:
            return "%3.1f%s" % (num, unit)
        num /= float(base)
    return "%3.1f%s" % (num, 'Ti')
