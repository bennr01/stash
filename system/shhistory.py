#-*- coding: utf-8 -*-
"""
StaSh input history.
"""
from io import open
import json

from .shcommon import ShEventNotFound


class ShHistory(object):
    """
    This class is responsible for the input history.
    
    @ivar stash: the associated StaSh instance
    @type stash: L{stash.core.StaSh}
    @ivar allow_double: if False, do not save the same line twice in a row
    @type allow_double: L{str}
    @var hide_whitespace: if True, do not save lines starting with a space
    @type hide_whitespace: L{bool}
    @var ipython_style_history_search: if True, enable an ipython-style history search
    @type ipython_style_history_search: bool
    @var maxsize: max number of lines each subhistory is allowed to have.
    @type maxsize: L{int}
    @ivar templine: a currently stashed line if the user is browsing the history
    @type templine: L{str}
    @ivar idx: the current history index
    @type idx: L{int}
    
    @cvar ENCODING: encoding to store history in.
    @type ENCODING: L{str}
    @cvar DEFAULT: default section of history to store
    @type DEFAULT: L{str}
    """

    ENCODING = "utf-8"
    DEFAULT = "_default"

    def __init__(self, stash):
        """
        @param stash: the StaSh core
        @type stash: L{stash.core.StaSh}
        """
        self.stash = stash
        self._histories = {}
        self._current = self.DEFAULT
        self.allow_double = self.stash.config.getboolean("history", "allow_double_lines")
        self.hide_whitespace = self.stash.config.getboolean("history", "hide_whitespace_lines")
        self.ipython_style_history_search = self.stash.config.getboolean('history', 'ipython_style_history_search')
        self.maxsize = self.stash.config.getint("history", "maxsize")
        self.templine = ""
        self.idx = -1

    @classmethod
    def load(cls, path, stash):
        """
        Load the history from a path.
        
        @param path: path to load from.
        @type path: L{str}
        @param stash: the StaSh core
        @type stash: L{stash.core.StaSh}
        @return: the history loaded from the file
        @rtype: ShHistory
        """
        shh = cls(stash)
        try:
            with open(path, "r", encoding=cls.ENCODING) as fin:
                h = json.loads(u"" + fin.read())
        except ValueError:
            h = {"StaSh.runtime": cls.load_old_format(path)}
        shh._histories = h
        return shh

    @classmethod
    def load_old_format(cls, path):
        """
        Load the content of an old-style history.
        
        @param path: path to load from
        @type path: L{str}
        @return: the lines loaded from the file
        @rtype: L{list} of L{str}
        """
        with open(path, "r", encoding=cls.ENCODING) as fin:
            lines = [line.strip() for line in fin.readlines()]
        return lines

    def save(self, path):
        """
        Save the history to a path.
        
        @param path: path to save to.
        @type path: L{str}
        """
        with open(path, "w", encoding=self.ENCODING) as fout:
            s = json.dumps(self._histories)
            fout.write(u"" + s)  # ensure unicode

    def clear(self, target=None):
        """
        Clear the history
        
        @param target: history to clear or None for current
        @type target: L{str} or L{None}
        """
        if target is None:
            target = self._current
        if target in self._histories:
            del self._histories[target]

    def clear_all(self):
        """
        Clear all histories.
        """
        self._histories = {}

    def swap(self, target):
        """
        Swap the history to the target history.
        
        @param target: identifier to get the history for
        @type target: L{str} or L{None}
        """
        self._current = target

    def add(self, line, always=False):
        """
        Add a line to the history.
        
        @param line: line to add to history
        @type line: L{str}
        @param always: always add this line, regardless of config
        @type always: L{bool}
        """
        if self._current not in self._histories:
            self._histories[self._current] = []
        stripped = line.strip()
        last_line = (self._histories[self._current][-1] if len(self._histories[self._current]) > 0 else None)
        if not always:
            # check if this line should be added
            if stripped == last_line and not self.allow_double:
                # prevent double lines
                return
            if line.startswith(" ") and self.hide_whitespace:
                # hide lines starting with a whitespace
                return
        self._histories[self._current].append(stripped)
        # ensure maxsize
        while len(self._histories[self._current]) > max(0, self.maxsize):
            self._histories[self._current].pop(0)

        # reset index
        self.reset_idx()

    def getlist(self):
        """
        Return a list of the current history.
        
        @return: list of current history entries
        @rtype: L{list} of L{str}
        """
        if self._current not in self._histories:
            self._histories[self._current] = []
        return self._histories[self._current][::-1]

    def search(self, tok):
        """
        Search the history.
        
        @param tok:
        @type tok:
        @return: last entry in history matching the search
        @rtype: L{str}
        @raises: L{stash.system.shcommon.ShEventNotFound}
        """
        history = self.getlist()
        search_string = tok[1:]
        if search_string == '':
            return ''
        if search_string == '!':
            return history[0]
        try:
            idx = int(search_string)
            try:
                return history[::-1][idx]
            except IndexError:
                raise ShEventNotFound(tok)
        except ValueError:
            for entry in history:
                if entry.startswith(search_string):
                    return entry
            raise ShEventNotFound(tok)

    def reset_idx(self):
        """
        Reset the index of the current position in the history
        """
        self.idx = -1

    def up(self):
        """
        Move upwards in the history.
        """
        # Save the unfinished line user is typing before showing entries from history
        history = self.getlist()
        if self.idx == -1:
            self.templine = self.stash.mini_buffer.modifiable_string.rstrip()

        self.idx += 1
        if self.idx >= len(history):
            self.idx = len(history) - 1

        else:
            entry = history[self.idx]
            # If move up away from an unfinished input line, try search history for
            # a line starts with the unfinished line
            if self.idx == 0 and self.ipython_style_history_search:
                for idx, hs in enumerate(history):
                    if hs.startswith(self.templine):
                        entry = hs
                        self.idx = idx
                        break

            self.stash.mini_buffer.feed(None, entry)

    def down(self):
        """
        Move downwqrds in the history
        """
        history = self.getlist()
        self.idx -= 1
        if self.idx < -1:
            self.idx = -1

        else:
            if self.idx == -1:
                entry = self.templine
            else:
                entry = history[self.idx]

            self.stash.mini_buffer.feed(None, entry)
