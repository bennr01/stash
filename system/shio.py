# coding: utf-8
"""
This module contains file-like I/O for the user input.
"""

import logging
import time
from collections import deque


class ShIO(object):
    """
    The ShIO object is the read/write interface to users and running scripts.
    It acts as a staging area so that the UI Delegate calls can return without
    waiting for user read/write (no blocking on main thread).
    
    @ivar stash: the associated stash instance
    @type stash: L{stash.core.StaSh}
    @ivar debug: if True, log debug informations
    @type debug: str
    @ivar logger: the logger for I/O
    @type logger: L{logging.Logger}
    @ivar tell_pos: the current position in the 'file'
    @type tell_pos: L{int}
    @ivar chunk_size: max number of chars to feed to the stream at once
    @type chunk_size: L{int}
    @ivar holdback: if the buffer is empty, wait this time to reduce CPU usage.
    @type holdback: L{int} or L{float}
    @ivar encoding: encoding to use
    @type encoding: L{str}
    """

    def __init__(self, stash, debug=False):
        """
        @param stash: the associated stash instance
        @type stash: L{stash.core.StaSh}
        @param debug: if True, log debug informations
        @type debug: L{str}
        """
        self.stash = stash
        self.debug = debug
        self.logger = logging.getLogger('StaSh.IO')
        self.tell_pos = 0
        # The input buffer, push from the Left end, read from the right end
        self._buffer = deque()
        self.chunk_size = 4096
        # When buffer is empty, hold back for certain before read again
        # This is to lower the cpu usage of the reading thread so it does
        # not affect the UI thread by noticeable amount
        self.holdback = 0.2

        self.encoding = 'utf8'

    def push(self, s):
        """
        Push a char to the buffer. It can then be read using L{ShIO.read}.
        
        @param s: string to push onto the buffer
        @type s: L{str}
        """
        self._buffer.extendleft(s)

    # Following methods to provide file like object interface
    @property
    def closed(self):
        """
        Return True if this 'file' is closed.
        
        @return: whether this 'file' is closed or not. Always False.
        @rtype: L{bool}
        """
        return False

    def isatty(self):
        """
        Return True if this 'file' is a TTY.
        
        @return: whether this 'file' is a TTY. Always True.
        @rtype: L{bool}
        """
        return True

    def close(self):
        """
        This IO object cannot be closed.
        """
        pass

    def seek(self, offset):
        """
        Seek of stdout is not the real seek as file, it seems merely set
        the current posotion as the given parameter.
        
        @param offset: seek the given position
        @type offset: L{int}
        """
        self.tell_pos = offset

    def tell(self):
        """
        Return the current position in this 'file'.
        
        @return: the tell position
        @rtype: L{int}
        """
        return self.tell_pos

    def truncate(self, size=None):
        """
        Do nothing.
        """
        pass

    def read(self, size=-1):
        """
        Read input from the user.
        
        @param size: max number of chars to read
        @type size: L{int}
        @return: the user input
        @rtype: L{str}
        """
        size = size if size != 0 else 1

        if size == -1:
            return ''.join(self._buffer.pop() for _ in len(self._buffer))

        else:
            ret = []
            while len(ret) < size:
                try:
                    ret.append(self._buffer.pop())
                except IndexError:
                    # Wait briefly when the buffer is empty to avoid taxing the CPU
                    time.sleep(self.holdback)

            return ''.join(ret)

    def readline(self, size=-1):
        """
        Read a line from the user.
        
        @param size: not used.
        @type size: L{int}
        @return: the user input
        @rtype: L{str}
        """
        ret = []
        while True:
            try:
                ret.append(self._buffer.pop())
                if ret[-1] in ['\n', '\0']:
                    break
            except IndexError:
                time.sleep(self.holdback)

        if ret[-1] == '\0':
            del ret[-1]

        line = ''.join(ret)
        # localized history for running scripts
        # TODO: Adding to history for read as well?
        self.stash.runtime.history.add(line)

        return line

    def readlines(self, size=-1):
        """
        Read lines from the user.
        
        @param size: max number of chars to read.
        @type size: L{int}
        @return: the user input
        @rtype: L{list} of L{str}
        """
        ret = []
        while True:
            try:
                ret.append(self._buffer.pop())
                if ret[-1] == '\0':
                    break
            except IndexError:
                time.sleep(self.holdback)

        ret = ''.join(ret[:-1])  # do not include the EOF

        if size != -1:
            ret = ret[:size]

        for line in ret.splitlines():
            self.stash.runtime.history.add(line)

        return ret.splitlines(True)

    def read1(self):
        """
        Put MiniBuffer in cbreak mode to process character by character.
        
        Normally the MiniBuffer only sends out its reading after a LF.
        With this method, MiniBuffer sends out its reading after every
        single char.
        The caller is responsible for break out this reading explicitly.
        """
        # TODO: Currently not supported by ShMiniBuffer
        try:
            self.stash.mini_buffer.cbreak = True
            while True:
                try:
                    yield self._buffer.pop()
                except IndexError:
                    time.sleep(self.holdback)

        finally:
            self.stash.mini_buffer.cbreak = False

    def readline_no_block(self):
        """
        Read lines from the buffer but does NOT wait till lines to be completed.
        
        If no complete line can be read, just return with None.
        This is useful for runtime to process multiple commands from user. The
        generator form also helps the program to keep reading and processing
        user command when a program is running at the same time.
        @return: str:
        """
        ret = []
        while True:
            try:
                ret.append(self._buffer.pop())
                if ret[-1] == '\n':
                    yield ''.join(ret)
                    ret = []
            except IndexError:
                self._buffer.extend(ret)
                break

    def write(self, s, no_wait=False):
        """
        Write a string to the output.
        
        @param s: string to write
        @type s: L{str}
        @param no_wait: passed to L{stash.system.shstreams.ShStream.feed}
        @type no_wait: L{bool}
        """
        if len(s) == 0:  # skip empty string
            return
        idx = 0
        while True:
            self.stash.stream.feed(s[idx:idx + self.chunk_size], no_wait=no_wait)  # main screen only
            idx += self.chunk_size
            if idx >= len(s):
                break

    def writelines(self, s_list):
        """
        Write a list of lines to the output.
        
        @param s_list: list of strings to write
        @type s_list: L{list} of L{str}
        """
        self.write(''.join(s_list))

    def flush(self):
        """
        No-op
        """
        pass
