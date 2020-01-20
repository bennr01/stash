# coding: utf-8
"""
The wrappers dispatch io requests based on current thread.

If the thread is an instance of ShBaseThread, the io should be dispatched to ShIO.
Otherwise, it should be dispatched to regular sys io.

@ivar stdinWrapper: the wrapper arround L{sys.stdin}
@type stdinWrapper: L{ShStdinWrapper}
@ivar stdoutWrapper: the wrapper arround L{sys.stdout}
@type stdoutWrapper: L{ShStdoutWrapper}
@ivar stderrWrapper: the wrapper arround L{sys.stderr}
@type stderrWrapper: L{ShStderrWrapper}
"""

import sys
import threading

from .shcommon import _SYS_STDIN, _SYS_STDOUT, _SYS_STDERR
from .shthreads import ShBaseThread


class ShStdinWrapper(object):
    """
    Wrapper for L{sys.stdin}
    """
    def __getattribute__(self, item):
        thread = threading.currentThread()

        if isinstance(thread, ShBaseThread):
            return getattr(thread.state.sys_stdin, item)
        else:
            return getattr(_SYS_STDIN, item)


class ShStdoutWrapper(object):
    """
    Wrapper for L{sys.stdout}
    """
    def __getattribute__(self, item):
        thread = threading.currentThread()

        if isinstance(thread, ShBaseThread):
            return getattr(thread.state.sys_stdout, item)
        else:
            return getattr(_SYS_STDOUT, item)


class ShStderrWrapper(object):
    """
    Wrapper for L{sys.stderr}
    """
    def __getattribute__(self, item):
        thread = threading.currentThread()

        if isinstance(thread, ShBaseThread):
            return getattr(thread.state.sys_stderr, item)
        else:
            return getattr(_SYS_STDERR, item)


stdinWrapper = ShStdinWrapper()
stdoutWrapper = ShStdoutWrapper()
stderrWrapper = ShStderrWrapper()


def enable():
    """
    Enable the I/O wrappers.
    """
    sys.stdin = stdinWrapper
    sys.stdout = stdoutWrapper
    sys.stderr = stderrWrapper


def disable():
    """
    Disable the I/O wrappers.
    """
    sys.stdin = _SYS_STDIN
    sys.stdout = _SYS_STDOUT
    sys.stderr = _SYS_STDERR
