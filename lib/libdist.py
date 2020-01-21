"""
OS/device specific interfaces.

@var IN_PYTHONISTA: True if running in Pythonista.
@type IN_PYTHONISTA: L{bool}
@var ON_TRAVIS: True if running on Travis CI.
@type ON_TRAVIS: L{bool}

@var SITE_PACKAGES_FOLDER: path to the directoy in which pip will
install modules into.
@type SITE_PACKAGES_FOLDER: L{str}
@var SITE_PACKAGES_FOLDER_6: like L{SITE_PACKAGES_FOLDER}, but shared
between py2 and py3.
@type SITE_PACKAGES_FOLDER_6: L{str}
@var BUNDLED_MODULES: list of bundled modules. L{pip} will skip
installing these modules/packages.
@type BUNDLED_MODULES: L{list} of L{str}
"""
import os
import sys

import six


IN_PYTHONISTA = sys.executable.find('Pythonista') >= 0
ON_TRAVIS = "TRAVIS" in os.environ


# ========================== PYTHONISTA =======================
if IN_PYTHONISTA:
    
    # ------------- clipboard --------------
    import clipboard
    
    def clipboard_get():
        """
        Get the clipboard content.
        
        @return: clipboard content
        @rtype: L{six.text_type}
        """
        return clipboard.get()
    
    def clipboard_set(s):
        """
        Set the clipboard content.
        
        @param s: string to set
        @type s: L{six.text_type}
        """
        # TODO: non-unicode support
        assert isinstance(s, six.text_type)
        clipboard.set(s)
    
    # -------------- pip ----------------------
    
    if six.PY3:
        SITE_PACKAGES_DIR_NAME = "site-packages-3"
    else:
        SITE_PACKAGES_DIR_NAME = "site-packages-2"
    SITE_PACKAGES_DIR_NAME_6 = "site-packages"
    SITE_PACKAGES_FOLDER = os.path.expanduser('~/Documents/{}'.format(SITE_PACKAGES_DIR_NAME))
    SITE_PACKAGES_FOLDER_6 = os.path.expanduser('~/Documents/{}'.format(SITE_PACKAGES_DIR_NAME_6))
    
    BUNDLED_MODULES = [
        'bottle',
        'beautifulsoup4',
        'pycrypto',
        'py-dateutil',
        'dropbox',
        'ecdsa',
        'evernote',
        'Faker',
        'feedparser',
        'flask',
        'html2text',
        'html5lib',
        'httplib2',
        'itsdangerous',
        'jedi',
        'jinja2',
        'markdown',
        'markdown2',
        'matplotlib',
        'mechanize',
        'midiutil',
        'mpmath',
        'numpy',
        'oauth2',
        'paramiko',
        'parsedatetime',
        'Pillow',
        'pycparser',
        'pyflakes',
        'pygments',
        'pyparsing',
        'PyPDF2',
        'pytz',
        'qrcode',
        'reportlab',
        'requests',
        'simpy',
        'six',
        'sqlalchemy',
        'pysqlite',
        'sympy',
        'thrift',
        'werkzeug',
        'wsgiref',
        'pisa',
        'xmltodict',
        'PyYAML',
    ]
    
    # -------------- open in / quicklook ----------------------
    import console
    from objc_util import on_main_thread
    
    @on_main_thread
    def open_in(path):
        """
        Open a file in another application.
        If possible, let the user decide the application
        
        @param path: path to file
        @type path: L{str}
        """
        console.open_in(path)
    
    @on_main_thread
    def quicklook(path):
        """
        Show a preview of the file.
        
        @param path: path to file
        @type path: L{str}
        """
        console.quicklook(path)
        
# ======================== DEFAULT / PC / travis =========================
else:
    
    # ------------- clipboard --------------
    # travis is a variation of PC
    if not ON_TRAVIS:
        # use pyperclip
        import pyperclip
        
        def clipboard_get():
            """
            Get the clipboard content.
            
            @return: clipboard content
            @rtype: L{six.text_type}
            """
            return pyperclip.paste()
        
        def clipboard_set(s):
            """
            Set the clipboard content.
            
            @param s: string to set
            @type s: L{six.text_type}
            """
            # TODO: non-unicode support
            assert isinstance(s, six.text_type)
            pyperclip.copy(s)
    else:
        # use fake implementation
        global _CLIPBOARD; _CLIPBOARD = u""
        
        def clipboard_get():
            """
            Get the clipboard content.
            
            @return: clipboard content
            @rtype: L{six.text_type}
            """
            return _CLIPBOARD
        
        def clipboard_set(s):
            """
            Set the clipboard content.
            
            @param s: string to set
            @type s: L{six.text_type}
            """
            global _CLIPBOARD
            assert isinstance(s, six.text_type)
            _CLIPBOARD = s
        
    
    # -------------- pip ----------------------
    import site
    
    try:
        SITE_PACKAGES_FOLDER = site.getsitepackages()[0]
    except AttributeError:
        # site.getsitepackages() unavalaible in virtualenv
        import stash
        SITE_PACKAGES_FOLDER = os.path.dirname(stash.__path__[0])
    SITE_PACKAGES_FOLDER_6 = None
    
    BUNDLED_MODULES = [
        'six',
    ]
    
    # -------------- open in / quicklook ----------------------
    import webbrowser
    
    def open_in(path):
        """
        Open a file in another application.
        If possible, let the user decide the application
        
        @param path: path to file
        @type path: L{str}
        """
        webbrowser.open(path, new=1)
    
    def quicklook(path):
        """
        Show a preview of the file.
        
        @param path: path to file
        @type path: L{str}
        """
        webbrowser.open(path, new=1)
