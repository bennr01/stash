# coding: utf-8
'''
Manipulate the action (wrench) menu of the pythonista app.

Example:

add_action('/stash/launch_stash.py', 'monitor')

save_defaults() # so it is stored for next launch

 '''

# This module was created by jsbain. Thanks for sharing it!

from objc_util import *
NSUserDefaults = ObjCClass('NSUserDefaults')


def add_action(scriptName, iconName='python', iconColor='', title=''):
    '''
    Adds an editor action.
    
    Call save_defaults() to store defaults
    
    @param scriptName: name of script to add. It should start with a
    C{"/"} (e.g C{"/launch_stash.py"})
    @type scriptName: L{str}
    @param iconName: The name of the icon to use without leading prefix,
    or trailing size.  i.e alert instead of iob:alert_256
    @type iconName: L{str}
    @param iconColor: A web style hex string, eg aa00ff for the icon color
    @type iconColor: L{str}
    @param title: is the alternative title
    @type title: L{str}
    ')'''
    defaults = NSUserDefaults.standardUserDefaults()
    kwargs = locals()
    entry = {
        key: kwargs[key]
        for key in ('scriptName',
                    'iconName',
                    'iconColor',
                    'title',
                    'arguments')
        if key in kwargs and kwargs[key]
    }
    editoractions = get_actions()
    editoractions.append(ns(entry))
    defaults.setObject_forKey_(editoractions, 'EditorActionInfos')


def remove_action(scriptName):
    '''
    Remove all instances of a given scriptname.
    
    Call save_defaults() to store for next session
    
    @param scriptName: name of scripts to remove
    @type scriptName: L{str}
    '''
    defaults = NSUserDefaults.standardUserDefaults()
    editoractions = get_actions()
    [editoractions.remove(x) for x in editoractions if str(x['scriptName']) == scriptName]
    defaults.setObject_forKey_(editoractions, 'EditorActionInfos')


def remove_action_at_index(index):
    '''
    Remove action at index.
    
    Call save_defaults() to save result.
    
    @param index: index to remove
    @type index: L{int}
    '''
    defaults = NSUserDefaults.standardUserDefaults()
    editoractions = get_actions()
    del editoractions[index]
    defaults.setObject_forKey_(editoractions, 'EditorActionInfos')


def get_defaults_dict():
    '''
    Return NSdictionary of defaults
    '''
    defaults = NSUserDefaults.standardUserDefaults()
    return defaults.dictionaryRepresentation()


def get_actions():
    '''
    Return action list
    
    @return: the action list
    @rtype: L{list}
    '''
    defaults = NSUserDefaults.standardUserDefaults()
    return list(defaults.arrayForKey_('EditorActionInfos') or ())


def save_defaults():
    '''
    Save current set of defaults
    '''
    defaults = NSUserDefaults.standardUserDefaults()
    NSUserDefaults.setStandardUserDefaults_(defaults)
