"""
UI base classes.

The UI implementations should subclass these classes.
For a guide for this, see the porting guide.
"""
import ast
import logging
import time

import six

from ..shcommon import K_CC, K_CD, K_HUP, K_HDN, K_LEFT, K_RIGHT, K_CU, K_TAB, K_HIST, K_CZ, K_KB


class ShBaseUI(object):
    """
    Baseclass for the main UI.
    
    This class is responsible for general UI behaviour and encompasses
    the terminal.
    
    @ivar stash: parent StaSh instance
    @type stash : L{stash.core.StaSh}
    @ivar debug: if True, log debug informations
    @type debug: L{bool}
    @ivar debug_terminal: debug flag for the terminal
    @type debug_terminal: L{bool}
    @ivar logger: the logger for the UI
    @type logger: L{logging.Logger}
    @ivar terminal: the terminal. This is not set in this class, but must
    be set by the subclasses
    @type terminal: L{ShBaseTerminal}
    @ivar BUFFER_MAX: max size of buffer
    @type BUFFER_MAX: L{int}
    @ivar TEXT_FONT: the text font to use, as (name, site)
    @type TEXT_FONT: L{tuple} of (L{int}, L{int})
    @ivar BUTTON_FONT: the font to use for buttons
    @type BUTTON_FONT: L{tuple} of (L{int}, L{int})
    @ivar vk_symbols: chars for the virtual keyrow
    @type vk_symbols: L{str}
    """
    def __init__(self, stash, debug=False, debug_terminal=False):
        """
        @param stash: parent StaSh instance
        @type stash : L{stash.core.StaSh}
        @param debug: if True, log debug informations
        @type debug: L{bool}
        @param debug_terminal: debug flag for the terminal
        @type debug_terminal: L{bool}
        """
        self.stash = stash
        self.debug = debug
        self.debug_terminal = debug_terminal
        self.logger = logging.getLogger('StaSh.UI')
        
        self.BUFFER_MAX = stash.config.getint('display', 'BUFFER_MAX')
        self.TEXT_FONT = ('Menlo-Regular', stash.config.get('display', 'TEXT_FONT_SIZE'))
        self.BUTTON_FONT = ('Menlo-Regular', stash.config.getint('display', 'BUTTON_FONT_SIZE'))
        self.vk_symbols = stash.config.get('display', 'VK_SYMBOLS')
    
    def show(self):
        """
        Show the UI.
        """
        raise NotImplementedError()
    
    def close(self):
        """
        Close the UI. You should also call self.on_exit().
        """
        raise NotImplementedError()
    
    def on_exit(self):
        """
        This method should be called when the UI will be closed.
        """
        # delegate task to the core
        self.stash.on_exit()
    
    # ================== key commands ========================
    
    def dummyAction(self):
        """
        Do nothing.
        """
        pass

    def controlCAction(self):
        self.stash.ui.vk_tapped(K_CC)

    def controlDAction(self):
        self.vk_tapped(K_CD)

    def controlPAction(self):
        self.vk_tapped(K_HUP)

    def controlNAction(self):
        self.vk_tapped(K_HDN)

    def controlKAction(self):
        self.stash.mini_buffer.feed(self.stash.mini_buffer.RANGE_CURSOR_TO_END, '')

    def controlUAction(self):
        self.vk_tapped(K_CU)

    def controlAAction(self):  # Move cursor to beginning of the input
        self.stash.mini_buffer.set_cursor(0)

    def controlEAction(self):  # Move cursor to end of the input
        self.stash.mini_buffer.set_cursor(0, whence=2)

    def controlWAction(self):  # delete one word backwards
        self.stash.mini_buffer.delete_word(self.selected_range)

    def controlLAction(self):  # delete one word backwards
        self.stash.stream.feed(u'\u009bc%s' % self.stash.runtime.get_prompt(), no_wait=True)

    def controlZAction(self):
        self.stash.runtime.push_to_background()

    def arrowUpAction(self):
        self.vk_tapped(K_HUP)

    def arrowDownAction(self):
        self.vk_tapped(K_HDN)

    def arrowLeftAction(self):
        # self.stash.mini_buffer.set_cursor(-1, whence=1)
        self.vk_tapped(K_LEFT)

    def arrowRightAction(self):
        # self.stash.mini_buffer.set_cursor(1, whence=1)
        self.vk_tapped(K_RIGHT)
    
    def vk_tapped(self, vk):
        """
        Called when a key was pressed.
        
        @param vk: the pressed key
        @type vk: L{int}
        """
        if self.debug:
            self.logger.debug("vk_tapped({vk})".format(vk=vk))
        if vk == K_TAB:  # Tab completion
            rng = self.terminal.selected_range
            # Valid cursor positions are only when non-selection and after the modifiable position
            if rng[0] == rng[1] and rng[0] >= self.stash.main_screen.x_modifiable:
                self.stash.mini_buffer.feed(rng, '\t')

        elif vk == K_HIST:
            self.history_present(self.stash.runtime.history)

        elif vk == K_HUP:
            self.stash.runtime.history.up()

        elif vk == K_HDN:
            self.stash.runtime.history.down()
        
        elif vk == K_LEFT:
            self.stash.mini_buffer.set_cursor(-1, whence=1)
        
        elif vk == K_RIGHT:
            self.stash.mini_buffer.set_cursor(1, whence=1)

        elif vk == K_CD:
            if self.stash.runtime.child_thread:
                self.stash.mini_buffer.feed(self.stash.mini_buffer.RANGE_BUFFER_END, '\0')

        elif vk == K_CC:
            if not self.stash.runtime.child_thread:
                self.stash.write_message('no thread to terminate\n')
                self.stash.io.write(self.stash.runtime.get_prompt())

            else:  # ctrl-c terminates the entire stack of threads
                self.stash.runtime.child_thread.kill()  # this recursively kill any nested child threads
                time.sleep(0.5)  # wait a moment for the thread to terminate

        elif vk == K_CZ:
            self.stash.runtime.push_to_background()

        elif vk == K_KB:
            if self.terminal.is_editing:
                self.terminal.end_editing()
            else:
                self.terminal.begin_editing()

        elif vk == K_CU:
            self.stash.mini_buffer.feed(self.stash.mini_buffer.RANGE_MODIFIABLE_CHARS, '')
    
    # ================== history functions =====================
    
    def history_present(self, history):
        """
        Present the history.
        
        @param history: history to present
        @type history: L{stash.system.shhistory.ShHistory}
        """
        raise NotImplementedError()
    
    def history_selected(self, line, idx):
        """
        This should be called when a history line was selected.
        
        @param line: selected line
        @type line: L{str}
        @param idx: index of selected line
        @type idx: L{int}
        """
        # Save the unfinished line user is typing before showing entries from history
        if self.stash.runtime.history.idx == -1:
            self.stash.runtime.history.templine = self.stash.mini_buffer.modifiable_string.rstrip()
        self.stash.mini_buffer.feed(None, line)
        self.stash.runtime.history.idx = idx


class ShBaseTerminal(object):
    """
    This is the base class for the multiline text used for both in- and output.
    Implementations of the terminal should call the stash.useractionproxy.* methods as appropiate.
    
    @ivar stash: parent StaSh instance
    @type stash: L{stash.core.StaSh}
    @ivar parent: the parent ShBaseUI
    @type parent: L{ShBaseUI}
    @ivar debug: if True, log debug informations
    @type debug: L{bool}
    @ivar tv_delegate: delegate for textview events
    @ivar cursor_synced: whether the terminal cursor position is in sync with main screen
    @type cursor_synced: L{bool}
    @ivar font_size: size of font to use ofr the text
    @type font_size: L{int}
    @ivar text_color: color of the text (rgb tuple)
    @type text_color: L{tuple} of (L{float}, L{float}, L{float})
    @ivar tint_color: color for highlights
    @type tint_color: L{tuple} of (L{float}, L{float}, L{float})
    @ivar indicator_style: style for indicators
    @type indicator_style: L{str}
    """
    
    def __init__(self, stash, parent):
        """
        @param stash: parent StaSh instance
        @type stash: L{stash.core.StaSh}
        @param parent: the parent ShBaseUI
        @type parent: L{ShBaseUI}
        """
        self.stash = stash
        self.parent = parent
        self.debug = self.parent.debug_terminal
        self.logger = logging.getLogger('StaSh.Terminal')
        
        self.stash.terminal = self
        
        self.tv_delegate = ShTerminalDelegate(self.stash, self, debug=self.debug)
        
        # whether the terminal cursor position is in sync with main screen
        self.cursor_synced = False
        
        self.background_color = ast.literal_eval(stash.config.get('display', 'BACKGROUND_COLOR'))
        self.font_size = stash.config.getint('display', 'TEXT_FONT_SIZE')
        self.text_color = ast.literal_eval(stash.config.get('display', 'TEXT_COLOR'))
        self.tint_color = ast.literal_eval(stash.config.get('display', 'TINT_COLOR'))

        self.indicator_style = stash.config.get('display', 'INDICATOR_STYLE')
    
    @property
    def text(self):
        """
        The text of the terminal.
        
        @return: the text of the terminal
        @rtype: L{six.text_type}
        """
        raise NotImplementedError()
    
    @text.setter
    def text(self, value):
        """
        Set the text of the terminal.
        
        @param text: the text to set
        @type text: L{six.text_type}
        """
        assert isinstance(value, six.text_type)
        raise NotImplementedError()
        
    @property
    def text_length(self):
        """
        The length of the text.
        
        @return: the length of the text
        @rtype: L{int}
        """
        return len(self.text)  # default implementation
    
    @property
    def selected_range(self):
        """
        The selected range.
        
        @return: the text selection as a tuple of (startindex, endindex)
        @rtype: L{tuple} of (L{int}, L{int})
        """
        raise NotImplementedError()

    @selected_range.setter
    def selected_range(self, rng):
        """
        Set the cursor selection range.
        
        Note it checks the current range first and
        only change it if the new range is different. This is to avoid setting
        unwanted cursor_synced flag. Without the check, the cursor is repositioned
        with the same range, this turn on the cursor_synced flag BUT will NOT trigger
        the did_change_selection event (which is paired to cancel the cursor_synced
        flag).
        
        B{Important:} set self.cursor_synced = False if the above mentioned conditions are true
        
        @param rng: the text selection as a tuple of (startindex, endindex)
        @type rng: L{tuple} of (L{int}, L{int})
        """
        raise NotImplementedError()
    
    def scroll_to_end(self):
        """
        Scroll to the end of the text.
        """
        raise NotImplementedError()
    
    def set_focus(self):
        """
        Set the focus to the UI.
        This means that user keyboard inputs should be send to the terminal.
        """
        raise NotImplementedError()
    
    def lose_focus(self):
        """
        Lose the focus.
        """
        self.end_editing()
    
    def get_wh(self):
        """
        Return the number of columns and rows.
        
        @return: number of columns and rows.
        @rtype: tuple of (int, int)
        """
        raise NotImplementedError()


class ShTerminalDelegate(object):
    """
    The Delegate for the terminal.
    
    This will be called from the ShUserActionProxy.
    The terminal should call the stash.useractionproxy.* methods instead.
    See U{http://omz-software.com/pythonista/docs/ios/ui.html#textview}.
    
    @ivar stash: parent StaSh instance
    @type stash: L{stash.core.StaSh}
    @ivar terminal: the associated terminal
    @type terminal: L{ShBaseTerminal}
    @ivar debug: if True, log debug informations
    @type debug: L{bool}
    @ivar mini_buffer: StaSh's mini buffer
    @type mini_buffer: L{stash.system.shstreams.ShMiniBuffer}
    @ivar main_screen: StaSh's main screen
    @type main_screen: L{stash.system.shscreens.ShSequentialScreen}
    @ivar logger: the delegate's logger
    @type logger: L{logging.Logger}
    """
    def __init__(self, stash, terminal, debug=False):
        """
        @param stash: parent StaSh instance
        @type stash: L{stash.core.StaSh}
        @param terminal: the associated terminal
        @type terminal: L{ShBaseTerminal}
        @param debug: if True, log debug informations
        @type debug: L{bool}
        """
        self.stash = stash
        self.terminal = terminal
        self.debug = debug
        self.mini_buffer = self.stash.mini_buffer
        self.main_screen = self.stash.main_screen
        self.logger = logging.getLogger('StaSh.TerminalDelegate')

    def textview_did_begin_editing(self, tv):
        """
        See pythonista's UI documentation.
        """
        self.terminal.is_editing = True

    def textview_did_end_editing(self, tv):
        """
        See pythonista's UI documentation.
        """
        self.terminal.is_editing = False

    def textview_should_change(self, tv, rng, replacement):
        """
        See pythonista's UI documentation.
        """
        self.mini_buffer.feed(rng, replacement)
        return False  # always false

    def textview_did_change(self, tv):
        """
        See pythonista's UI documentation.
        
        The code is a fix to a possible UI system bug:
        Some key-combos that delete texts, e.g. alt-delete, cmd-delete, from external
        keyboard do not trigger textview_should_change event. So following checks
        are added to ensure consistency between in-memory and actual UI.
        """
        rng = self.terminal.selected_range
        main_screen_text = self.main_screen.text
        terminal_text = self.terminal.text
        x_modifiable = self.main_screen.x_modifiable
        if rng[0] == rng[1] and main_screen_text[rng[0]:] != terminal_text[rng[0]:]:
            if rng[0] >= x_modifiable:
                self.mini_buffer.feed(None, main_screen_text[x_modifiable:rng[0]] + terminal_text[rng[0]:])
                self.mini_buffer.set_cursor(-len(terminal_text[rng[0]:]), whence=2)
            else:
                s = terminal_text[rng[0]:]
                self.main_screen.intact_right_bound = rng[0]  # mark the buffer to be re-rendered
                # If the trailing string is shorter than the modifiable chars,
                # this means there are valid deletion for the modifiable chars
                # and we should keep it.
                if len(s) < len(self.mini_buffer.modifiable_string):
                    self.mini_buffer.feed(None, s)
                    self.mini_buffer.set_cursor(0, whence=0)
                else:  # nothing should be deleted
                    self.mini_buffer.set_cursor(0, whence=2)

    def textview_did_change_selection(self, tv):
        """
        See pythonista's UI documentation.
        
        This callback was used to provide approximated support for H-Up/Dn
        shortcuts from an external keyboard. It is no longer necessary as
        proper external keyboard support is now possible with objc_util.
        """

        # If cursor is in sync already, as a result of renderer call, flag it
        # to False for future checking.
        if self.terminal.cursor_synced:
            self.terminal.cursor_synced = False
        else:
            # Sync the cursor position on terminal to main screen
            # Mainly used for when user touches and changes the terminal cursor position.
            self.mini_buffer.sync_cursor(self.terminal.selected_range)


class ShBaseSequentialRenderer(object):
    """
    A base class for a specific renderer for `ShSequentialScreen`.
    
    It does its job by
    building texts from the in-memory screen and insert them to the
    terminal.
    
    @cvar FG_COLORS: mapping of fg color names to colors
    @type FG_COLORS: L{dict} of L{str} -> ?
    @cvar BG_COLORS: mapping of bg color names to colors
    @type BG_COLORS: L{dict} of L{str} -> ?

    @ivar stash: the StaSh instance
    @type stash: L{stash.core.StaSh}
    @ivar screen: In memory screen
    @type screen: L{stash.system.shscreens.ShSequentialScreen}
    @ivar terminal: The real terminal
    @type terminal: L{ShBaseTerminal}
    @ivar debug: if True, log debug informations
    @type debug: L{bool}
    """
    FG_COLORS = {
        "default": None,
    }
    BG_COLORS = {
        "default": None,
    }
    
    def __init__(self, stash, screen, terminal, debug=False):
        """
        @param stash: the StaSh instance
        @type stash: L{stash.core.StaSh}
        @param screen: In memory screen
        @type screen: L{stash.system.shscreens.ShSequentialScreen}
        @param terminal: The real terminal
        @type terminal: L{ShBaseTerminal}
        @param debug: if True, log debug informations
        @type debug: L{bool}
        """
        self.stash = stash
        self.screen = screen
        self.terminal = terminal
        self.debug = debug
        self.logger = logging.getLogger('StaSh.SequentialRenderer')

        # update default colors to match terminal
        self.FG_COLORS["default"] = self.FG_COLORS.get(self.terminal.text_color, self.FG_COLORS["default"])
        self.BG_COLORS["default"] = self.BG_COLORS.get(self.terminal.background_color, self.BG_COLORS["default"])

    
    def render(self, no_wait=False):
        """
        Render the screen buffer to the terminal.
        
        @param no_wait: Immediately render the screen without delay.
        @type no_wait: bool
        """
        raise NotImplementedError()
