# -*- coding: utf-8 -*-
"""
Common functions shared between the various tools.
"""
import os


def get_stash_dir():
    """
    Returns the StaSh root directory, detected from this file.
    
    @return: the StaSh root directory
    @rtype: L{str}
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    """
    The main function.
    
    This method will call the various functions defined in this module
    to test them.
    """
    print("StaSh root directory: {}".format(get_stash_dir()))


if __name__ == "__main__":
    main()
