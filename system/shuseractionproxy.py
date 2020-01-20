# coding: utf-8
"""
The proxy is used to centralize handler dispatching for user actions
such as type, touch, swipe, key press.

@var NULL_RESPONDER: a responder doing nothing.
@type NULL_RESPONDER: L{ShNullResponder}
"""
from contextlib import contextmanager


class ShNullResponder(object):
    """
    A responder doing nothing.
    """
    def handle(self, *args, **kwargs):
        """
        No-Op
        """
        pass

    def __call__(self, *args, **kwargs):
        pass

    def __getattribute__(self, item):
        return object.__getattribute__(self, 'handle')

    def __getitem__(self, item):
        return object.__getattribute__(self, 'handle')


NULL_RESPONDER = ShNullResponder()


# noinspection PyAttributeOutsideInit,PyDocstring
class ShUserActionProxy(object):
    """
    This proxy object provides a central place to register handlers for
    any user actions trigger from the UI including typing, touching,
    tap, etc. A centralized object makes it easier to substitute default
    handlers by user-defined functions in command script, e.g. ssh.

    @ivar stash: parent StaSh instance
    @type stash: L{stash.core.StaSh}
    @ivar tv_delegate: delegate/handler for textview events
    @ivar sv_delegate: delegate/handler for scrollview events.
    """

    def __init__(self, stash):
        """
        @param stash: parent StaSh instance
        @type stash: L{stash.core.StaSh}
        """
        self.stash = stash
        self.reset()

        # TextView delegate
        class _TVDelegate(object):
            @staticmethod
            def textview_did_begin_editing(sender):
                self.tv_responder.textview_did_begin_editing(sender)

            @staticmethod
            def textview_did_end_editing(sender):
                self.tv_responder.textview_did_end_editing(sender)

            @staticmethod
            def textview_should_change(sender, rng, replacement):
                return self.tv_responder.textview_should_change(sender, rng, replacement)

            @staticmethod
            def textview_did_change(sender):
                self.tv_responder.textview_did_change(sender)

            @staticmethod
            def textview_did_change_selection(sender):
                self.tv_responder.textview_did_change_selection(sender)

        # Virtual key row swipe gesture
        class _SVDelegate(object):
            @staticmethod
            def scrollview_did_scroll(sender):
                if self.sv_responder:
                    self.sv_responder.scrollview_did_scroll(sender)
                else:
                    sender.superview.scrollview_did_scroll(sender)

        self.tv_delegate = _TVDelegate()
        self.sv_delegate = _SVDelegate()

    # The properties are used for late binding as the various components
    # may not be ready when this class is initialized
    @property
    def vk_responder(self):
        """
        Virtual keyrow handler.
        
        @return: the responder for virtual keyrow events
        @rtype: callable.
        """
        return self._vk_responder or self.stash.ui.vk_tapped

    @vk_responder.setter
    def vk_responder(self, value):
        self._vk_responder = value

    @property
    def tv_responder(self):
        """
        TextView handler.
        
        @return: the responder for textview events
        @rtype: callable.
        """
        return self._tv_responder or self.stash.terminal.tv_delegate

    @tv_responder.setter
    def tv_responder(self, value):
        self._tv_responder = value

    @property
    def kc_responder(self):
        """
        keyboard handler.
        
        @return: the responder for virtual keyrow events
        @rtype: callable.
        """
        return self._kc_responder or self.stash.terminal.kc_pressed

    @kc_responder.setter
    def kc_responder(self, value):
        self._kc_responder = value

    @contextmanager
    def config(self, vk_responder=False, tv_responder=False, sv_responder=False, kc_responder=False):
        """
        A context manager for using context-based responders/handlers.
        
        @param vk_responder: responder for virtual keyrow events
        @type tv_responder: callable
        @param tv_responder: responder for textview events
        @type vk_responder: callable
        @param tv_responder: responder for scrollview events
        @type tv_responder: callable
        @return: a context manager
        @rtype: a context manager
        """

        try:
            self._vk_responder = NULL_RESPONDER if vk_responder is False else vk_responder
            self._tv_responder = NULL_RESPONDER if tv_responder is False else tv_responder
            self.sv_responder = NULL_RESPONDER if sv_responder is False else sv_responder
            self.kc_responder = NULL_RESPONDER if kc_responder is False else kc_responder
            yield
        finally:
            self.reset()

    def reset(self):
        self._vk_responder = None
        self._tv_responder = None
        self.sv_responder = None
        self._kc_responder = None  # for keyCommands

    # --------------------- Proxy ---------------------
    # Buttons
    def vk_tapped(self, sender):
        """
        Called when a virtual key was pressed.
        
        @param sender: the sender of this event
        @type sender:
        """
        self.vk_responder(sender)

    # Keyboard shortcuts
    def kc_pressed(self, key, modifierFlags):
        """
        Called when a keyboard shortcut was used.
        
        @param key: the pressed key
        @param modifierFlags: modifier flags (e.g. ctrl)
        """
        self.kc_responder(key, modifierFlags)
