# -*- coding: utf-8 -*-
"""
This module keeps track of the current MountManager.
This can not be done in stashutils.mount_manager, because this would create some import problems.

@var MANAGER: the current mount manager or None.
Please use L{get_manager} and L{set_manager} instead of modyfying this
variable directly.
@type MANAGER: L{stashutils.mount_manager.MountManager} or L{None}
"""

# global: current mount manager

MANAGER = None


def get_manager():
    """
    Return the current mount manager.
    
    Use the function instead of the constant to prevent import problems.
    
    @return: the current mount manager.
    @rtype: L{stashutils.mount_manager.MountManager} or L{None}
    """
    return MANAGER


def set_manager(manager):
    """
    Sets the current mount manager.
    
    @param manager: mount manager to set
    @type manager: L{stashutils.mount_manager.MountManager} or L{None}
    """
    global MANAGER
    MANAGER = manager
