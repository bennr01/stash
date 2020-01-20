# coding: utf-8
"""
The runtime manages states and the execution of commands.
"""

import io
import os
import sys
import platform
import logging
import threading
import functools
import traceback
import tempfile

from six import StringIO, text_type, binary_type, PY3
try:
    file
except NameError:
    from io import IOBase as file

import pyparsing as pp

# Detecting environments
try:
    from objc_util import on_main_thread
except ImportError:
    from .dummyobjc_util import on_main_thread

from .shcommon import ShBadSubstitution, ShInternalError, ShIsDirectory, \
    ShFileNotFound, ShEventNotFound, ShNotExecutable
# noinspection PyProtectedMember
from .shcommon import _STASH_ROOT, _STASH_HISTORY_FILE, _SYS_STDOUT, _SYS_STDERR
from .shcommon import is_binary_file, _STASH_EXTENSION_BIN_PATH
from .shparsers import ShPipeSequence
from .shthreads import ShBaseThread, ShTracedThread, ShCtypesThread, ShState, ShWorkerRegistry
from .shhistory import ShHistory

# Default .stashrc file
_DEFAULT_RC = r"""BIN_PATH=~/Documents/bin:{bin_ext}:$BIN_PATH
SELFUPDATE_TARGET=master
PYTHONPATH=$STASH_ROOT/lib:$PYTHONPATH
alias env='printenv'
alias help='man'
alias la='ls -a'
alias ll='ls -la'
alias copy='pbcopy'
alias paste='pbpaste'
alias unmount='umount'
""".format(
    bin_ext=_STASH_EXTENSION_BIN_PATH,
)


class ShRuntime(object):
    """
    Runtime class responsible for parsing and executing commands.
    
    @ivar stash: the parent StaSh instance.
    @type stash: L{stash.core.StaSh}
    @ivar parser: the parser
    @type parser: L{stash.system.shparsers.ShParser}
    @ivar expander: the expander
    @type expander: L{stash.system.shparsers.ShExpander}
    @ivar debug: if True, log debug information
    @type debug: L{bool}
    @ivar logger: the logger of the runtime
    @type logger: L{logging.Logger}
    @ivar state: the global state
    @type state: L{stash.system.shthreads.ShState}
    @ivar child_thread: current foreground child thread
    @type child_thread: L{stash.system.shthreads.ShBaseThread} or L{None}
    @ivar worker_registry: the worker registry
    @type worker_registry: L{stash.system.shthreads.ShWorkerRegistry}
    @ivar rcfile: path to the resource file
    @type rcfile: L{str}
    @ivar historyfile: path to the history file
    @type historyfile: L{str}
    @ivar py_traceback: if True, show the full traceback when an exception occurs
    @type py_traceback: L{bool}
    @ivar py_pdb: if True, start the debugger when an exception occurs
    @type py_pdb: L{bool}
    @ivar input_encoding_utf8: This is one of the greatest unsolved mysteries of StaSh
    @type input_encoding_utf8: py_pdb: L{bool}
    @ivar ShThread: the thread class to use for workers.
    @type ShThread: a subclass of L{stash.system.shthreads.ShBaseThread}
    @ivar colored_errors: if True, show colored error messages
    @type colored_errors: L{bool}
    @ivar history: the history manager object
    @type history: L{stash.system.shhistory.ShHistory}
    """

    def __init__(self, stash, parser, expander, no_historyfile=False, debug=False):
        """
        @param stash: the parent StaSh instance.
        @type stash: L{stash.core.StaSh}
        @param parser: the parser
        @type parser: L{stash.system.shparsers.ShParser}
        @param expander: the expander
        @type expander: L{stash.system.shparsers.ShExpander}
        @param no_historyfile: if True, do not use a history file.
        @type no_historyfile: L{bool}
        @param debug: if True, log debug information
        @type debug: L{bool}
        """
        self.stash = stash
        self.parser = parser
        self.expander = expander
        self.debug = debug
        self.logger = logging.getLogger('StaSh.Runtime')

        self.state = ShState(
            environ=dict(
                os.environ,
                HOME2=os.path.join(os.environ['HOME'],
                                   'Documents'),
                STASH_ROOT=_STASH_ROOT,
                STASH_PY_VERSION=platform.python_version(),
                BIN_PATH=os.path.join(_STASH_ROOT,
                                      'bin'),
                # Must have a placeholder because it is needed before _DEFAULT_RC is loaded
                PROMPT=r'[\W]$ ',
                PYTHONISTA_ROOT=os.path.dirname(sys.executable),
                TMPDIR=os.environ.get("TMPDIR", tempfile.gettempdir()),
            ),
            sys_stdin=self.stash.io,
            sys_stdout=self.stash.io,
            sys_stderr=self.stash.io,
        )
        self.child_thread = None
        self.worker_registry = ShWorkerRegistry()

        config = stash.config
        self.rcfile = os.path.join(_STASH_ROOT, config.get('system', 'rcfile'))
        self.historyfile = os.path.join(_STASH_ROOT, _STASH_HISTORY_FILE)

        self.py_traceback = config.getint('system', 'py_traceback')
        self.py_pdb = config.getint('system', 'py_pdb')
        self.input_encoding_utf8 = config.getint('system', 'input_encoding_utf8')
        self.ShThread = {
            'traced': ShTracedThread,
            'ctypes': ShCtypesThread
        }.get(config.get('system',
                         'thread_type'),
              ShCtypesThread)
        self.colored_errors = config.getboolean("style", "colored_errors")

        # load history from last session
        if not no_historyfile:
            try:
                self.history = ShHistory.load(self.historyfile, self.stash)
            except IOError:
                self.history = ShHistory(self.stash)
        else:
            self.history = ShHistory(self.stash)
        self.history.swap("StaSh.runtime")

    def load_rcfile(self, no_rcfile=False):
        """
        Load the default RC and the normal resource file.
        
        The RC to load if 'no_rcfile' is nonzero is specified in L{rcfile}.
        
        @param no_rcfile: do not load the non-default RC file.
        @type no_rcfile: L{bool}
        """
        self.stash(_DEFAULT_RC.splitlines(), persistent_level=1, add_to_history=False, add_new_inp_line=False)

        if not no_rcfile and os.path.exists(self.rcfile) and os.path.isfile(self.rcfile):
            try:
                with io.open(self.rcfile, encoding="utf-8") as ins:
                    self.stash(ins.readlines(), persistent_level=1, add_to_history=False, add_new_inp_line=False)
            except IOError:
                self.stash.write_error_message('%s: error reading rcfile\n' % self.rcfile)

    def write_error_message(self, stream, msg, prefix=None, log=True):
        """
        Write/print an error message to stream.
        
        @param stream: file to write to or None
        @type stream: L{stash.system.shio.ShIO} or L{file} or L{None}
        @param msg: error message to write
        @type msg: L{str}
        @param log: if true, log message
        @type log: L{bool}
        """
        if prefix is None:
            prefix = "stash: "
        if self.debug and log:
            self.logger.debug(prefix + msg)
        if stream is None:
            self.stash.write_message(msg, error=True, prefix=prefix)
        elif stream is self.stash.io:
            if self.colored_errors:
                stream.write(self.stash.text_color(prefix + msg, "red"))
            else:
                stream.write(prefix + msg)
        else:
            stream.write(prefix + msg)

    def find_script_file(self, filename):
        """
        Locate the scriptfile for the given filename/commandname.
        
        @param filename: name of file/command to locate
        @type filename: L{str}
        @return: path to the filename
        @rtype: L{str}
        @raises: L{stash.system.shcommon.ShIsDirectory}
        @raises: L{stash.system.shcommon.ShFileNotFound}
        """
        _, current_state = self.get_current_worker_and_state()

        dir_match_found = False
        # direct match of the filename, e.g. full path, relative path etc.
        for fname in (filename, filename + '.py', filename + '.sh'):
            if os.path.exists(fname):
                if os.path.isdir(fname):
                    dir_match_found = True
                else:
                    return fname

        # Match for commands in current dir and BIN_PATH
        # Effectively, current dir is always the first in BIN_PATH
        for path in ['.'] + current_state.environ_get('BIN_PATH').split(':'):
            path = os.path.abspath(os.path.expanduser(path))
            if os.path.exists(path):
                for f in os.listdir(path):
                    if f == filename or f == filename + '.py' or f == filename + '.sh':
                        if os.path.isdir(f):
                            dir_match_found = True
                        else:
                            return os.path.join(path, f)
        if dir_match_found:
            raise ShIsDirectory('%s: is a directory' % filename)
        else:
            raise ShFileNotFound('%s: command not found' % filename)

    def get_all_script_names(self):
        """
        Find all known scrip names / commands.
        
        This function is used by the completer, whitespaces in names are escaped.
        
        @return: a list of all possible commands.
        @rtype: L{list} of L{str}
        """
        _, current_state = self.get_current_worker_and_state()
        all_names = []
        for path in ['.'] + current_state.environ_get('BIN_PATH').split(':'):
            path = os.path.expanduser(path)
            if os.path.exists(path):
                for f in os.listdir(path):
                    if not os.path.isdir(f) and (f.endswith('.py') or f.endswith('.sh')):
                        all_names.append(f.replace(' ', '\\ '))
        return all_names

    def run(
            self,
            input_=None,
            final_ins=None,
            final_outs=None,
            final_errs=None,
            add_to_history=None,
            add_new_inp_line=None,
            persistent_level=0,
            is_background=False,
            environ={},
            cwd=None
    ):
        """
        This is the entry point for running shell commands.

        @param input_: Input to execute. Defaults to L{stash.core.StaSh.io} (read from console).
        @type input_: L{str} or L{list} of L{str} or L{stash.system.shio.ShIO} or L{stash.system.shparsers.ShPipeSequence}
        @param final_ins: stdin for command
        @type final_ins: L{io.IOBase} or L{None}
        @param final_outs: stdout for command
        @type final_outs: L{io.IOBase} or L{None}
        @param final_errs: stderr for command
        @type final_errs: L{io.IOBase} or L{None}
        @param add_to_history: if True, add command to history.
        @type add_to_history: L{bool}
        @param add_new_inp_line: write a new input prompt after the script finishes.
        @type add_new_inp_line: L{bool} or L{None}
        
        @param persistent_level:
        The persistent level dictates how variables from child shell
        shall be carried over to the parent shell.
        
        Possible values are:
        
        C{0}: No persistent at all (shell script is by default in this mode)
        
        
        C{1}: Full persistent. Parent's variables will be the same as child's
        (User command from terminal is in this mode).
        
        C{2}: Semi persistent. Any more future children will have starting
        variables as the current child's ending variables. (__call__
        interface is by default in this mode).
        
        @type persistent_level: L{int}
        @param environ: environment variables for script
        @type environ L{dict}
        @param cwd: CWD for command to run in
        @type cwd: L{str} or L{None}
        @return: the worker used to run the command.
        @rtype: L{stash.system.shthreads.ShBaseThread}
        """

        # By default read from the terminal
        if input_ is None:
            input_ = self.stash.io

        # noinspection PyDocstring
        def fn():
            current_worker, _ = self.get_current_worker_and_state()
            is_top = current_worker.is_top_level()

            try:
                if isinstance(input_, ShPipeSequence):
                    self.run_pipe_sequence(
                        input_,
                        final_ins=final_ins,
                        final_outs=final_outs,
                        final_errs=final_errs,
                        environ=environ,
                        cwd=cwd
                    )

                else:
                    if type(input_) is list:
                        lines = input_
                    elif input_ == self.stash.io:
                        lines = self.stash.io.readline_no_block()
                    else:
                        lines = input_.splitlines()

                    for line in lines:
                        # Ignore empty lines
                        if line.strip() == '':
                            continue

                        # Parse and expand the line (note this function returns a generator object)
                        expanded = self.expander.expand(line)
                        # The first member is the history expanded form and number of pipe_sequence
                        newline, n_pipe_sequences = next(expanded)
                        # Only add history entry if:
                        #   1. It is explicitly required
                        #   2. It is the first layer thread directly spawned by the main thread
                        #      and not explicitly required to not add
                        if (add_to_history is None and is_top) or add_to_history:
                            self.history.add(line)  # add non-expanded form to history

                        if is_top:
                            self.history.swap(newline.split(" ")[0] if newline != "" else "")

                        try:
                            # Subsequent members are actual commands
                            for _ in range(n_pipe_sequences):
                                pipe_sequence = next(expanded)
                                if pipe_sequence.in_background:
                                    # For background command, separate worker is created
                                    self.run(
                                        pipe_sequence,
                                        final_ins=final_ins,
                                        final_outs=final_outs,
                                        final_errs=final_errs,
                                        persistent_level=0,
                                        is_background=True,
                                        environ=environ,
                                        cwd=cwd
                                    )
                                else:
                                    self.run_pipe_sequence(
                                        pipe_sequence,
                                        final_ins=final_ins,
                                        final_outs=final_outs,
                                        final_errs=final_errs,
                                        environ=environ,
                                        cwd=cwd
                                    )
                        finally:
                            if is_top:
                                self.history.swap("StaSh.runtime")

            except pp.ParseException as e:
                if self.debug:
                    self.logger.debug('ParseException: %s\n' % repr(e))
                msg = 'syntax error: at char %d: %s\n' % (e.loc, e.pstr)
                self.write_error_message(final_errs, msg)

            except ShEventNotFound as e:
                if self.debug:
                    self.logger.debug('%s\n' % repr(e))
                msg = '%s: event not found\n' % e.args[0]
                self.write_error_message(final_errs, msg)

            except ShBadSubstitution as e:
                if self.debug:
                    self.logger.debug('%s\n' % repr(e))
                msg = '%s\n' % e.args[0]
                self.write_error_message(final_errs, msg)

            except ShInternalError as e:
                if self.debug:
                    self.logger.debug('%s\n' % repr(e))
                msg = '%s\n' % e.args[0]
                self.write_error_message(final_errs, msg)

            except IOError as e:
                if self.debug:
                    self.logger.debug('IOError: %s\n' % repr(e))
                msg = '%s: %s\n' % (e.filename, e.strerror)
                self.write_error_message(final_errs, msg)

            except KeyboardInterrupt as e:
                msg = '^C\nKeyboardInterrupt: %s\n' % e.args[0]
                self.write_error_message(final_errs, msg)

            # This catch all exception handler is to handle errors outside of
            # run_pipe_sequence. The traceback print is mainly for debugging
            # the shell itself as opposed to the running script (handled inside
            # exec_py_file)
            except Exception as e:
                etype, evalue, tb = sys.exc_info()
                if self.debug:
                    self.logger.debug('Exception: %s\n' % repr(e))
                msg = '%s\n' % repr(e)
                self.write_error_message(final_errs, msg)
                if self.py_traceback or self.py_pdb:
                    # traceback.print_exception(etype, evalue, tb, file=(final_errs if final_errs is not None else None))
                    lines = traceback.format_exception(etype, evalue, tb)
                    self.write_error_message(self.stash.text_color("".join(lines), "red"), prefix="")

            finally:
                # Housekeeping for the thread, e.g. remove itself from registry
                current_worker.cleanup()

                # Prompt is now ready for more user input for commands to run,
                # if new input line is explicitly specified or when the worker
                # thread's parent is the runtime itself and new input line is
                # not explicitly suppressed
                if add_new_inp_line or (is_top and add_new_inp_line is not False):
                    self.script_will_end()

                # Saves its state to parent or if persistent is required
                if not current_worker.is_background:
                    current_worker.parent.state.persist_child(current_worker.state, persistent_level=persistent_level)

        # Get the parent thread
        parent_thread = threading.currentThread()

        # UI thread is substituted by runtime
        if not isinstance(parent_thread, ShBaseThread):
            parent_thread = self

        child_thread = self.ShThread(
            self.worker_registry,
            parent_thread,
            input_,
            target=fn,
            is_background=is_background,
            environ=environ,
            cwd=cwd
        )
        child_thread.start()

        return child_thread

    def script_will_end(self):
        """
        Called after a script finishes exection.
        
        Write a new prompt and reset handlers.
        """
        self.stash.io.write(self.get_prompt(), no_wait=True)
        # Config the mini buffer so that user commands can be processed
        self.stash.mini_buffer.config_runtime_callback(functools.partial(self.run, persistent_level=1))
        # Reset any possible external tab handler setting
        self.stash.external_tab_handler = None

    def run_pipe_sequence(self, pipe_sequence, final_ins=None, final_outs=None, final_errs=None, environ={}, cwd=None):
        """
        Run a L{stash.system.shparsers.ShPipeSequence}.
        
        A pipe sequence is a linked sequence of commands.
        
        @param pipe_sequence: pipe sequence to run
        @type pipe_sequence: L{stash.system.shparsers.ShPipeSequence}
        @type final_ins: L{io.IOBase} or L{None}
        @param final_outs: stdout for command
        @type final_outs: L{io.IOBase} or L{None}
        @param final_errs: stderr for command
        @type final_errs: L{io.IOBase} or L{None}
        @param environ: environment variables for script
        @type environ L{dict}
        @param cwd: CWD for command to run in
        @type cwd: L{str} or L{None}
        
        @raises: L{stash.system.shcommon.ShNotExecutable}
        """
        if self.debug:
            self.logger.debug(str(pipe_sequence))

        _, current_state = self.get_current_worker_and_state()

        n_simple_commands = len(pipe_sequence.lst)

        prev_outs = None
        for idx, simple_command in enumerate(pipe_sequence.lst):

            # The temporary_environ needs to be reset for each simple command
            # i.e. A=42 script1 | script2
            # The value of A should not be carried to script2
            current_state.temporary_environ = {}
            for assignment in simple_command.assignments:
                current_state.temporary_environ[assignment.identifier] = assignment.value

            # Only update the worker's env for pure assignments
            if simple_command.cmd_word == '' and idx == 0 and n_simple_commands == 1:
                current_state.environ.update(current_state.temporary_environ)
                current_state.temporary_environ = {}

            if prev_outs:
                # If previous output has gone to a file, we use a dummy empty string as ins
                ins = StringIO() if type(prev_outs) == file else prev_outs
            else:
                ins = final_ins or current_state.sys_stdin__

            outs = current_state.sys_stdout__
            errs = current_state.sys_stderr__

            if simple_command.io_redirect:
                # Truncate file or append to file
                mode = 'w' if simple_command.io_redirect.operator == '>' else 'a'
                # For simplicity, stdout redirect works for stderr as well.
                # Note this is different from a real shell.
                if simple_command.io_redirect.filename == '&3':
                    outs = _SYS_STDOUT
                    errs = _SYS_STDERR
                else:
                    errs = outs = open(simple_command.io_redirect.filename, mode)

            elif idx < n_simple_commands - 1:  # before the last piped command
                outs = StringIO()

            else:
                if final_outs:
                    outs = final_outs
                if final_errs:
                    errs = final_errs

            if self.debug:
                self.logger.debug('io %s %s\n' % (ins, outs))

            try:
                if simple_command.cmd_word != '':
                    script_file = self.find_script_file(simple_command.cmd_word)

                    if self.debug:
                        self.logger.debug('script is %s\n' % script_file)

                    if self.input_encoding_utf8:
                        # Python 2 is not fully unicode compatible. Some modules (e.g. runpy)
                        # insist for ASCII arguments. The encoding here helps eliminates possible
                        # errors caused by unicode arguments.
                        simple_command_args = [arg.encode('utf-8') for arg in simple_command.args]
                    else:
                        simple_command_args = simple_command.args

                    if script_file.endswith('.py'):
                        self.exec_py_file(script_file, simple_command_args, ins, outs, errs)

                    elif is_binary_file(script_file):
                        raise ShNotExecutable(script_file)

                    else:
                        self.exec_sh_file(script_file, simple_command_args, ins, outs, errs)

                else:
                    current_state.return_value = 0

                if current_state.return_value != 0:
                    break  # break out of the pipe_sequence, but NOT pipe_sequence list

                if isinstance(outs, StringIO):
                    outs.seek(0)  # rewind for next command in the pipe sequence

                prev_outs = outs

            # This catch all exception is for when the exception is raised
            # outside of the actual command execution, i.e. exec_py_file
            # exec_sh_file, e.g. command not found, not executable etc.
            except ShFileNotFound as e:
                err_msg = '%s\n' % e.args[0]
                if self.debug:
                    self.logger.debug(err_msg)

                self.write_error_message(final_errs, err_msg)
                # set exit code to 127
                current_state.return_value = 127
                break  # break out of the pipe_sequence, but NOT pipe_sequence list

            except Exception as e:
                err_msg = '%s\n' % e.args[0]
                if self.debug:
                    self.logger.debug(err_msg)
                self.write_error_message(final_errs, err_msg)
                break  # break out of the pipe_sequence, but NOT pipe_sequence list

            finally:
                if isinstance(outs, file) and not isinstance(outs, StringIO):
                    # StringIO is subclass of IOBase in py3 but not in py2
                    outs.close()
                if isinstance(ins, StringIO):  # release the string buffer
                    ins.close()

    def exec_py_file(self, filename, args=None, ins=None, outs=None, errs=None):
        """
        Execute a python file.
        
        @param filename: path of file to execute.
        @type filename: L{str}
        @param args: args to pass to script
        @type args: L{list} of L{str} or L{None}
        @type ins: L{io.IOBase} or L{None}
        @param outs: stdout for command
        @type outs: L{io.IOBase} or L{None}
        @param errs: stderr for command
        @type errs: L{io.IOBase} or L{None}
        """

        _, current_state = self.get_current_worker_and_state()

        if ins:
            current_state.sys_stdin = ins

        if outs:
            current_state.sys_stdout = outs

        if errs:
            current_state.sys_stderr = errs

        file_path = os.path.relpath(filename)
        namespace = dict(locals(), **globals())
        namespace['__name__'] = '__main__'
        namespace['__file__'] = os.path.abspath(file_path)
        namespace['_stash'] = self.stash

        saved_sys_argv = sys.argv[:]
        # First argument is the script name
        argv = [os.path.basename(filename)] + (args or [])

        argv = self.encode_argv(argv)
        sys.argv = argv

        # Set current os environ to the threading environ
        saved_os_environ = os.environ
        os.environ = dict(current_state.environ)
        # Honor any leading vars, e.g. A=42 echo $A
        os.environ.update(current_state.temporary_environ)

        # This needs to be done after environ due to possible leading PYTHONPATH var
        saved_sys_path = sys.path
        sys.path = current_state.sys_path[:]
        self.handle_PYTHONPATH()  # Make sure PYTHONPATH is honored

        try:
            with io.open(file_path, "rb", newline=None) as f:
                content = f.read()
                code = compile(content, file_path, "exec", dont_inherit=True)
                exec (code, namespace, namespace)

            current_state.return_value = 0

        except SystemExit as e:
            current_state.return_value = e.code

        except Exception as e:
            current_state.return_value = 1

            etype, evalue, tb = sys.exc_info()
            err_msg = '%s: %s\n' % (repr(etype), evalue)
            self.write_error_message(errs, err_msg)

            if self.py_traceback or self.py_pdb:
                lines = traceback.format_exception(etype, evalue, tb)
                self.write_error_message(errs, "".join(lines), prefix="")
                if self.py_pdb:
                    import pdb
                    pdb.post_mortem(tb)

        finally:
            # Thread specific vars are not modified, e.g. current_state.environ is unchanged.
            # This means the vars cannot be changed inside a python script. It can only be
            # done through shell command, e.g. NEW_VAR=42
            sys.argv = saved_sys_argv
            sys.path = saved_sys_path
            os.environ = saved_os_environ

    def exec_sh_file(self, filename, args=None, ins=None, outs=None, errs=None, add_to_history=None):
        """
        Execute a shell file.
        
        @param filename: path of file to execute.
        @type filename: L{str}
        @param args: args to pass to script
        @type args: L{list} of L{str} or L{None}
        @type ins: L{io.IOBase} or L{None}
        @param outs: stdout for command
        @type outs: L{io.IOBase} or L{None}
        @param errs: stderr for command
        @type errs: L{io.IOBase} or L{None}
        @param add_to_history: if True, add commands to history
        @type add_to_history: L{bool} or L{None}
        """

        _, current_state = self.get_current_worker_and_state()

        if args is None:
            args = []
        args = self.encode_argv(args)

        for i, arg in enumerate([filename] + args):
            current_state.temporary_environ[str(i)] = arg
        current_state.temporary_environ['#'] = len(args)
        current_state.temporary_environ['@'] = '\t'.join(args)

        # Enclosing variables will be merged to environ when creating new thread
        try:
            # read the file in textmode.
            with io.open(filename, "r", newline=None) as fins:
                child_worker = self.run(
                    fins.readlines(),
                    final_ins=ins,
                    final_outs=outs,
                    final_errs=errs,
                    add_to_history=add_to_history,
                    add_new_inp_line=False,
                    persistent_level=0
                )
                child_worker.join()

            current_state.return_value = child_worker.state.return_value

        except IOError as e:
            emsg = '%s: %s\n' % (e.filename, e.strerror)
            self.write_error_message(errs, emsg)
            current_state.return_value = 1

        except:
            emsg = '%s: error while executing shell script\n' % filename
            self.write_error_message(errs, emsg)
            current_state.return_value = 2

    def encode_argv(self, argv):
        """
        Convert an argv list into the appropiate string type depending
        on the currently used python version.
        
        @param argv: list of arguments to encode/convert
        @type argv: list of L{str}
        @return: list of the encoded arguments
        @rtype: L{list} of L{str}
        """
        if PY3:
            # we need unicode argv
            argv = [c if isinstance(c, text_type) else c.decode("utf-8") for c in argv]
        else:
            # we need bytestring argv
            argv = [c if isinstance(c, binary_type) else c.encode("utf-8") for c in argv]
        return argv

    def get_prompt(self):
        """
        Get the prompt string. Fill with current working directory if required.
        
        @return: the prompt
        @rtype: L{str}
        """
        _, current_state = self.get_current_worker_and_state()

        prompt = current_state.environ_get('PROMPT')
        if prompt.find('\\W') != -1 or prompt.find('\\w') != -1:
            curdir = os.getcwd().replace(current_state.environ_get('HOME'), '~')
            prompt = prompt.replace('\\w', curdir)
            prompt = prompt.replace('\\W', curdir if os.path.dirname(curdir) == '~' else os.path.basename(curdir))

        return self.stash.text_color(prompt, 'smoke')

    def push_to_background(self):
        """
        Push the current job into the background and return to the shell.
        """
        if self.child_thread:
            self.stash.write_message('pushing current job to background ...\n')
            self.child_thread.set_background()
            self.script_will_end()
        else:
            self.stash.write_message('no running foreground job\n')
            self.stash.io.write(self.stash.runtime.get_prompt())

    @on_main_thread
    def push_to_foreground(self, worker):
        """
        Push the specified worker to the foreground.
        
        @param worker: worker to push to the foreground
        @type worker: L{stash.system.shthreads.ShBaseThread}
        """
        worker.set_background(False)
        self.stash.mini_buffer.config_runtime_callback(None)
        self.stash.write_message('job {} is now running in foreground ...'.format(worker.job_id))

    def save_history(self):
        """
        Save the history
        """
        try:
            self.history.save(self.historyfile)
        except IOError:
            pass

    def get_current_worker_and_state(self):
        """
        Get the current thread and its associated state.
        
        @return: the current thread and its associated state
        @rtype: L{tuple} of (L{stash.system.shthreads.ShBaseThread}, L{stash.system.shthreads.ShState})
        """
        current_worker = threading.currentThread()
        if isinstance(current_worker, ShBaseThread):
            return current_worker, current_worker.state
        else:  # UI thread uses runtime for its state
            return None, self.state

    @staticmethod
    def handle_PYTHONPATH():
        """
        Add any user set python paths right after the dot or at the beginning
        if dot is not in the paths.
        """
        python_path = os.environ.get('PYTHONPATH', None)  # atomic access for check and retrieval

        if python_path:
            try:
                idxdot = sys.path.index('.') + 1
            except ValueError:
                idxdot = 0
            # Insert in the reversed order so idxdot does not need to change
            for pth in reversed(python_path.split(':')):
                if pth == '':
                    continue
                pth = os.path.expanduser(pth)
                if pth not in sys.path:
                    sys.path.insert(idxdot, pth)
