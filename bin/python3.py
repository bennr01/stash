"""
Simulates a console call to python [-m module][-c cmd] [file] [args]

Used for running standard library python modules such as:
SimpleHTTPServer, unittest and .py files.

Can also be used to run a script in the background, such as a server, with the bash character & at the end.
usage:
    python3
    python3 -m module_name [args]
    python3 -c command
    python3 python_file.py [args]
"""

import sys
import argparse
import os
import imp


CONSOLE_SCRIPT = """
import builtins
import code
locals = {
        '__name__': '__main__',
        '__doc__': None,
        '__package__': None,
        '__debug__': True,
        '__builtins__': builtins,  # yes, __builtins__
        # '_stash': _stash,
    }
code.interact(local=locals)
"""

_stash = globals()["_stash"]

args = sys.argv[1:]

passing_h = False
if '-h' in args and len(args) > 1:
    args.remove('-h')
    passing_h = True

ap = argparse.ArgumentParser()

group = ap.add_mutually_exclusive_group()
group.add_argument('-m', '--module',
                   action='store', default=None,
                   help='run module')
group.add_argument('-c', '--cmd',
                   action='store', default=None,
                   help='program passed in as string (terminates option list)')

ap.add_argument('args_to_pass',
                metavar='[file] args_to_pass',
                default=[],
                nargs=argparse.REMAINDER,
                help='Python script and arguments')

ns = ap.parse_args(args)
if passing_h:
    ns.args_to_pass.append('-h')


default_args = {
    "dll": _stash.librunner.get_dll(3),
    "ins": sys.stdin,
    "outs": sys.stdout,
    "errs": sys.stderr,
    "cwd": os.getcwd(),
    "globals": {},
    "locals": {},
    "argv": ns.args_to_pass,
    "lp": None, #"./librunnerlog.log",
    "lt": "python3",
}

if ns.module:
    argv = [ns.module] + ns.args_to_pass
    default_args["s"] = "import imp\nexec(imp.find_module('{m}')[0].read())".format(m=ns.module)
    default_args["argv"] = argv
    default_args["lt"] = ns.module
    _stash.librunner.exec_string_with_io(**default_args)
    sys.exit(0)

elif ns.cmd:
    default_args["s"] = ns.cmd
    _stash.librunner.exec_string_with_io(**default_args)
    sys.exit(0)

else:
    if ns.args_to_pass:
        argv = ns.args_to_pass
        try:
            with open(argv[0], "rU") as fin:
                c = fin.read()
            default_args["s"] = c
            default_args["argv"] = argv
            _stash.librunner.exec_string_with_io(**default_args)
        except Exception as e:
            print('Error: ' + str(e))
    else:
        default_args["s"] = CONSOLE_SCRIPT
        # default_args["locals"] = {"_stash": _stash}
        _stash.librunner.exec_string_with_io(**default_args)