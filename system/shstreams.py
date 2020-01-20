# coding: utf-8
"""
Streams are channels taking input and talking to in-memory screen.

There are two streams. One for User Input on Physical terminal. The other is
for accepting outputs from running scripts.
"""
import logging
import re

import six

# noinspection PyPep8Naming
from .shcommon import Control as ctrl, Escape as esc, PY3


class ShMiniBuffer(object):
    """
    This class process user inputs (as opposed to running scripts I/O). It is
    called by the UI delegate to process the text_view_should_change event.
    
    @cvar RANGE_BUFFER_END: a symbolic constant.
    @type RANGE_BUFFER_END: L{str}
    @cvar RANGE_MODIFIABLE_CHARS: a symbolic constant.
    @type RANGE_MODIFIABLE_CHARS: L{str}
    @cvar RANGE_CURSOR_TO_END: a symbolic constant.
    @type RANGE_CURSOR_TO_END: L{str}
    
    @ivar stash: the parent StaSh instance
    @type stash: L{stash.core.StaSh}
    @ivar main_screen: StaSh's main screen
    @type main_screen: L{stash.system.shscreens.ShSequentialScreen}
    @ivar debug: if True, log debug information
    @type debug: L{bool}
    @ivar logger: the logger of this minibuffer
    @type logger: L{logging.Logger}
    @ivar chars: buffer that holds incoming chars from user
    @type chars: L{str}
    @ivar runtime_callback:
    @type runtime_callback: callable
    @ivar cbreak: cbreak mode, process char by char. NOT IMPLEMENTED
    @type cbreak: L{bool}
    """

    RANGE_BUFFER_END = 'RANGE_BUFFER_END'
    RANGE_MODIFIABLE_CHARS = 'RANGE_MODIFIABLE_CHARS'
    RANGE_CURSOR_TO_END = 'RANGE_CURSOR_TO_END'

    def __init__(self, stash, main_screen, debug=False):
        """
        @param stash: the parent StaSh instance
        @type stash: L{stash.core.StaSh}
        @param main_screen: StaSh's main screen
        @type main_screen: L{stash.system.shscreens.ShSequentialScreen}
        @param debug: if True, log debug information
        @type debug: L{bool}
        """
        self.stash = stash

        self.main_screen = main_screen
        self.debug = debug
        self.logger = logging.getLogger('StaSh.MiniBuffer')

        self.chars = ''  # buffer that holds incoming chars from user
        self.runtime_callback = None
        # TODO: cbreak mode, process char by char. NOT IMPLEMENTED
        self.cbreak = False

        self._pattern_word_split = re.compile(r'[^\W]+\W*')

    @property
    def x_modifiable(self):
        """
        The index where chars start to be modifiable. Modifiable chars are
        those input text that can still be edited by users. Any characters
        before a linebreak is not modifiable.
        
        @return: The index where chars start to be modifiable.
        @rtype: L{int}
        """
        idx = self.chars.rfind('\n')
        return idx + 1 if idx != -1 else 0

    @property
    def modifiable_string(self):
        """
        The modifiable characters.
        
        @return: modifiable characters
        @rtype: L{str}
        """
        return self.chars[self.x_modifiable:]

    @modifiable_string.setter
    def modifiable_string(self, value):
        """
        Set the modifiable characters.
        
        @param value: New value for the modifiable chars
        @type value: L{str}
        """
        self.chars = self.chars[:self.x_modifiable] + value

    def feed(self, rng, replacement):
        """
        Directly called by a TextView delegate to replace existing chars
        in given range with the given new chars.

        @param  rng: the range of selected chars
        @type rng: L{tuple} of (L{int}, L{int}) or L{None} or L{str}
        @param replacement: new chars
        @type replacement: str
        """

        if rng is None or rng == self.RANGE_MODIFIABLE_CHARS:
            rng_adjusted = (self.x_modifiable, len(self.chars))
        elif rng == self.RANGE_BUFFER_END:
            rng_adjusted = (len(self.chars), len(self.chars))
        elif rng == self.RANGE_CURSOR_TO_END:
            rng_adjusted = self._adjust_range((self.main_screen.cursor_xs, self.main_screen.text_length))
        else:
            # Convert and adjust the range relative to the input buffer
            rng_adjusted = self._adjust_range(rng)

        # Lock the main_screen for modification
        with self.main_screen.acquire_lock():
            self._ensure_main_screen_consistency()

            # Delete contents of selected range first
            if rng_adjusted[0] != rng_adjusted[1]:
                if self.debug:
                    self.logger.debug('DELETING {!r} (chars: {!r})'.format(rng_adjusted, self.chars))
                self.chars = self.chars[:rng_adjusted[0]] + self.chars[rng_adjusted[1]:]
                replace_rng = (rng_adjusted[0] - self.x_modifiable, rng_adjusted[1] - self.x_modifiable)
                self.main_screen.replace_in_range(replace_rng, '', relative_to_x_modifiable=True)
        # Lock is now released

        if replacement == '':  # pure deletion
            self.stash.renderer.render(no_wait=True)

        elif replacement == '\t':  # TODO: Separate tab manager

            # When no foreground script is running, default tab handler is to auto-complete commands
            tab_handler = (
                self.stash.completer.complete if not self.stash.runtime.child_thread else self.stash.external_tab_handler
            )

            if callable(tab_handler):
                incomplete = self.chars[self.x_modifiable:rng_adjusted[0]]
                try:
                    completed, possibilities = tab_handler(incomplete)

                    if completed != incomplete:
                        with self.main_screen.acquire_lock():
                            self.modifiable_string = completed + self.chars[rng_adjusted[0]:]
                            self.main_screen.modifiable_string = self.modifiable_string
                            self.main_screen.cursor_x = self.main_screen.x_modifiable + len(completed)

                    elif len(possibilities) > 0:  # TODO: handle max possibilities checking
                        # Run through stream feed to allow attributed texts to be processed
                        self.stash.stream.feed(
                            u'\n%s\n%s' % ('  '.join(possibilities),
                                           self.stash.runtime.get_prompt()),
                            render_it=False  # do not render to avoid dead lock on UI thread
                        )
                        with self.main_screen.acquire_lock():
                            self.main_screen.modifiable_string = self.modifiable_string
                            self.main_screen.cursor_x = self.main_screen.x_modifiable + len(incomplete)

                    else:  # no completion can be achieved
                        with self.main_screen.acquire_lock():
                            self.main_screen.modifiable_string = self.modifiable_string
                            self.main_screen.cursor_x = self.main_screen.x_modifiable + len(incomplete)

                except Exception as e:  # TODO: better error handling
                    self.stash.stream.feed(
                        u'\nauto-completion error: %s\n%s' % (repr(e),
                                                              self.stash.runtime.get_prompt()),
                        render_it=False
                    )
                    with self.main_screen.acquire_lock():
                        self.main_screen.modifiable_string = self.modifiable_string
                        self.main_screen.cursor_x = self.main_screen.x_modifiable + len(incomplete)

                self.stash.renderer.render(no_wait=True)
            else:
                # TODO: simply add the tab character or show a warning?
                pass  # do nothing for now

        else:  # process line by line
            # TODO: Ideally the input should be processed by character. But it is slow.
            x = rng_adjusted[0]  # The location where character to be inserted
            for rpln in replacement.splitlines(True):

                # Lock the main_screen for modification
                with self.main_screen.acquire_lock():
                    self._ensure_main_screen_consistency()

                    # Update the mini buffer and the main_screen buffer
                    if rpln.endswith('\n'):  # LF is always added to the end of the line
                        if len(rpln) > 1:  # not a pure return char
                            self.main_screen.replace_in_range(
                                (x - self.x_modifiable,
                                 x - self.x_modifiable),
                                rpln[:-1],
                                relative_to_x_modifiable=True
                            )
                        self.main_screen.replace_in_range(None, u'\n', relative_to_x_modifiable=False)
                        self.chars = self.chars[:x] + rpln[:-1] + self.chars[x:] + '\n'
                    else:
                        # Do not send NULL char to main screen, it crashes the app
                        if rpln != '\0':
                            self.main_screen.replace_in_range(
                                (x - self.x_modifiable,
                                 x - self.x_modifiable),
                                rpln,
                                relative_to_x_modifiable=True
                            )
                        self.chars = self.chars[:x] + rpln + self.chars[x:]
                # Lock is now released

                # After the first line, the range should now always be at the end
                x = len(self.chars)

                # Render after every line
                self.stash.renderer.render(no_wait=True)

            # If complete lines or EOF are available, push them to IO buffer and notify
            # runtime for script running if no script is currently running.
            idx_lf = max(self.chars.rfind('\n'), self.chars.rfind('\0'))
            if idx_lf != -1:
                self.stash.io.push(self.chars[:idx_lf + 1])
                self.chars = self.chars[idx_lf + 1:]  # keep size of chars under control
                if self.runtime_callback is not None:
                    # When a script is running, all input are considered directed
                    # to the running script.
                    callback, self.runtime_callback = self.runtime_callback, None
                    callback()

    def set_cursor(self, offset, whence=0):
        """
        Set cursor within the modifiable range.
        
        @param offset:
        @type offset: L{int}
        @param whence: relative to what
        
        Possible values:
        
        C{1}: from current position
        
        C{2}: from the end
        
        other: default from start
        
        @type whence: L{int}
        """
        # Lock the main_screen for modification
        with self.main_screen.acquire_lock():
            self._ensure_main_screen_consistency()

            modifiable_xs, modifiable_xe = self.main_screen.modifiable_range

            if whence == 1:  # current position
                new_cursor_x = self.main_screen.cursor_xs + offset
            elif whence == 2:  # from the end
                new_cursor_x = modifiable_xe + offset
            else:  # default from start
                new_cursor_x = modifiable_xs + offset

            if new_cursor_x < modifiable_xs:
                new_cursor_x = modifiable_xs
            elif new_cursor_x > modifiable_xe:
                new_cursor_x = modifiable_xe

            # Ensure the cursor position is within the modifiable range
            self.main_screen.cursor_x = new_cursor_x

        self.stash.renderer.render(no_wait=True)

    def sync_cursor(self, selected_range):
        """
        Enforce the main screen cursor position to be the same as what it
        is shown on the terminal (TextView).
        
        This is mainly used for when
        user touch and change the cursor position/selection.
        
        @param selected_range: the current selected range to sync.
        @type seleced_range: L{tuple} of (L{int}, L{int})
        """
        with self.main_screen.acquire_lock(blocking=False) as locked:
            if locked:
                self.main_screen.cursor_xs, self.main_screen.cursor_xe = selected_range
            # If lock cannot be required, it means other threads are updating the screen.
            # So there is no need to sync the cursor (as it will be changed by other
            # threads anyway).

    def delete_word(self, rng):
        """
        Delete characters in the specified range.
        
        This method ensures that only the modifiable part of the range
        will be deleted.
        
        @param rng: range to delete
        @type rng: L{tuple} of (L{int}, L{int})
        """
        if rng[0] != rng[1]:  # do nothing if there is any selection
            return

        modifiable_string = self.modifiable_string  # nothing to be deleted
        if len(self.modifiable_string) == 0:
            return

        rng_adjusted = self._adjust_range(rng)
        deletable_chars = modifiable_string[:rng_adjusted[0]]
        left_chars = ''.join(self._pattern_word_split.findall(deletable_chars)[:-1])
        self.modifiable_string = left_chars + modifiable_string[rng_adjusted[0]:]
        self.main_screen.modifiable_string = self.modifiable_string
        self.set_cursor(len(left_chars))

        self.stash.renderer.render(no_wait=True)

    def _adjust_range(self, rng):
        """
        Convert the incoming range (by user) to values relative to the
        input buffer text. Also enforce the modifiable bound.

        @param rng: range of selected text
        @type rng: L{tuple} of (L{int}, L{int})
        @return: Adjusted range
        @rtype: L{tuple} of (L{int}, L{int})
        """
        terminal = self.stash.terminal
        tv_text = terminal.text  # existing text from the terminal
        length = len(self.chars)  # length of the existing input buffer

        # If the modifiable chars are different from the trailing chars on terminal,
        # this means additional output has been put on the terminal
        # after the event. In this case, simply set the range at the end of
        # the existing input buffer.
        modifiable_string = self.modifiable_string
        lm = len(modifiable_string)
        if lm == 0:
            trailing = u""
        else:
            trailing = tv_text[-lm:]
        if self.debug:
            self.logger.debug("modifiable string: {!r}; length: {!r}; trailing: {!r}".format(modifiable_string, length, trailing))
        assert len(trailing) == len(modifiable_string), len(trailing) - len(modifiable_string)
        if modifiable_string != '' and trailing != modifiable_string:
            xs_adjusted = xe_adjusted = length
        else:
            xs, xe = rng
            # The start location is converted using it offset to the end of the
            # terminal text.
            xs_adjusted = length - (len(tv_text) - xs)
            if xs_adjusted < self.x_modifiable:
                # the selection is invalid because it starts beyond the modifiable input buffer
                xs_adjusted = xe_adjusted = length
            else:
                xe_adjusted = xs_adjusted + (xe - xs)

        return xs_adjusted, xe_adjusted

    def _ensure_main_screen_consistency(self):
        # If the main screen's modifiable character is different from the input
        # buffer, it means more output has been put onto the main screen after
        # last update from the mini buffer. So the modifiable_string need to be
        # reset at the new x_modifiable location.
        # NOTE this must be called inside a main screen locking session
        if self.modifiable_string != self.main_screen.modifiable_string:
            if self.debug:
                self.logger.debug(
                    'Inconsistent mini_buffer [%s] main_screen [%s]' %
                    (self.modifiable_string,
                     self.main_screen.modifiable_string)
                )
            self.main_screen.modifiable_string = self.modifiable_string

    def config_runtime_callback(self, callback):
        """
        Set the runtime callback.
        
        :param callback: the new runtime callback
        :type callback: callable
        """
        self.runtime_callback = callback


class ShStream(object):
    """
    This class is used to process I/O from running scripts (as opposed to user input).

    A stream is a state machine that parses a stream of characters
    and dispatches events based on what it sees.
    
    @cvar basic: the control sequences, which don't require any arguments
    @type basic: L{dict} of L{str} -> L{str}
    @cvar csi: CSI escape sequences
    @type csi: L{dict} of L{str} -> L{str}
    @cvar STATE_STREAM: symbolic constant for state machine
    @type STATE_STREAM: L{int}
    @cvar STATE_ESCAPE: symbolic constant for state machine
    @type STATE_ESCAPE: L{int}
    @cvar STATE_ARGUMENTS: symbolic constant for state machine
    @type STATE_ARGUMENTS: L{int}
    
    @ivar consume_handlers: handlers for consuming the input
    @type consume_handlers: L{tuple} of (callable, ...)
    @ivar stash: the parent StaSh instance
    @type stash: L{stash.core.StaSh}
    @ivar main_screen: StaSh's main screen
    @type main_screen: L{stash.system.shscreens.ShSequentialScreen}
    @ivar debug: if True, log debug informations
    @type debug: L{bool}
    @ivar logger: this streams logger
    @type logger: L{logging.Logger}
    @ivar state: the current state
    @type state: one of the STATE_* constants
    @ivar params: arguments for current CSI sequence
    @type params: L{list} of L{int}
    @ivar current: current CSI sequence
    @type current: L{str}
    """

    #: Control sequences, which don't require any arguments
    basic = {
        ctrl.BS: 'backspace',
        ctrl.CR: 'carriage_return',
    }

    #: CSI escape sequences -- ``CSI P1;P2;...;Pn <fn>``.
    csi = {
        esc.RIS: 'reset',
        esc.DCH: 'delete_characters',
        esc.EL: 'erase_in_line',
        esc.SGR: 'select_graphic_rendition',
    }

    STATE_STREAM = 0
    STATE_ESCAPE = 1
    STATE_ARGUMENTS = 2

    def __init__(self, stash, main_screen, debug=False):
        """
        @param stash: the parent StaSh instance
        @type stash: L{stash.core.StaSh}
        @param main_screen: StaSh's main screen
        @type main_screen: L{stash.system.shscreens.ShSequentialScreen}
        @param debug: if True, log debug informations
        @type debug: L{bool}
        """

        self.consume_handlers = (self._stream, self._escape, self._arguments)

        self.stash = stash
        self.main_screen = main_screen
        self.debug = debug
        self.logger = logging.getLogger('StaSh.Stream')

        self.reset()

    # noinspection PyAttributeOutsideInit
    def reset(self):
        """Reset state to ``"stream"`` and empty parameter attributes."""
        self.state = self.STATE_STREAM
        self.params = []
        self.current = ''

    def consume(self, char):
        """
        Consumes a single string character and advance the state as
        necessary.

        @param char: a character to consume.
        @type char: L{str}
        """
        try:
            self.consume_handlers[self.state](char)
        except Exception as e:  # TODO: better error handling
            self.reset()

    def feed(self, chars, render_it=True, no_wait=False):
        """
        Consumes a string and advance the state as necessary.

        @param chars: a string to feed from.
        @type chars: L{str}
        """
        # To avoid the \xc2 deadlock from bytes string
        if not isinstance(chars, six.text_type):
            chars = chars.decode('utf-8', errors='ignore')

        with self.main_screen.acquire_lock():
            for char in chars:
                self.consume(char)

        if render_it:
            self.stash.renderer.render(no_wait=no_wait)

    def dispatch(self, event, *args, **kwargs):
        """
        Dispatches an event.

        If any of the attached listeners throws an exception, the
        subsequent callbacks will be aborted.

        @param event: event to dispatch.
        @type event: str
        @param args: arguments to pass to event handlers.
        @type args: L{list}
        """

        # noinspection PyCallingNonCallable
        try:
            handler = getattr(self.main_screen, event)
            handler(*args)
        except AttributeError:
            pass

        if kwargs.get('reset', True):
            self.reset()

    def _stream(self, char):
        """
        Processes a character when in the default ``"stream"`` state.
        
        @param char: character to process
        @type char: L{str}
        """
        if char in self.basic:
            self.dispatch(self.basic[char])

        elif char not in (ctrl.NUL, ctrl.DEL, ctrl.ESC, ctrl.CSI):
            self.dispatch('draw', char, reset=False)

        elif char == ctrl.ESC:
            self.state = self.STATE_ESCAPE

        elif char == ctrl.CSI:
            self.state = self.STATE_ARGUMENTS

    def _escape(self, char):
        """
        Handles characters seen when in an escape sequence.
        
        @param char: character to process
        @type char: L{str}
        """
        if char == '[':
            self.state = self.STATE_ARGUMENTS
        else:  # TODO: all other escapes are ignored
            self.dispatch('draw', char)

    def _arguments(self, char):
        """
        Parses arguments of a CSI sequence.

        All parameters are unsigned, positive decimal integers, with
        the most significant digit sent first. Any parameter greater
        than 9999 is set to 9999. If you do not specify a value, a 0
        value is assumed.
        
        @param char: character to process
        @type char: L{str}
        """
        if char.isdigit():
            self.current += char
        else:
            self.params.append(min(int(self.current or 0), 9999))
            if char == ';':  # multiple parameters
                self.current = ''
            else:
                self.dispatch(self.csi[char], *self.params)
