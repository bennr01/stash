# coding=utf-8
"""
Killable threads
"""
import os
import sys
import threading
import weakref
import ctypes
from collections import OrderedDict

from .shcommon import M_64, _SYS_STDOUT, python_capi

_STATE_STR_TEMPLATE = """enclosed_cwd: {}
aliases: {}
sys.stidin: {}
sys.stdout: {}
sys.stderr: {}
temporary_environ: {}
environ: {}
"""


class ShState(object):
    """
    State of a current worker thread
    
    @ivar aliases: the aliases defined in the worker thread.
    @type aliases: L{dict} of L{str}->L{str}
    @ivar environ: environment variables of the worker thread
    @type environ: L{dict} of L{str} -> L{str}
    @ivar enclosed_cwd: cwd of the worker thread
    @type enclosed_cwd: L{str}
    @ivar sys_stdin: stdin of worker
    @type sys_stdin: L{io.IOBase}
    @ivar sys_stdout: stdout of worker
    @type sys_stdout: L{io.IOBase}
    @ivar sys_stderr: stderr of worker
    @type sys_stderr: L{io.IOBase}
    @ivar sys_stdin__: original stdin of worker
    @type sys_stdin__: L{io.IOBase}
    @ivar sys_stdout__: original stdout of worker
    @type sys_stdout__: L{io.IOBase}
    @ivar sys_stderr__: original stderr of worker
    @type sys_stderr__: L{io.IOBase}
    @ivar sys_path: L{sys.path} of the worker
    @type sys_path: L{list} of L{str}
    @ivar temporary_environ:
    @type temporary_environ: L{dict} of L{str} -> L{str}
    @ivar enclosing_aliases:
    @type enclosing_aliases: L{dict} of L{str} -> L{str}
    @ivar enclosing_environ:
    @type enclosing_environ: L{dict} of L{str} -> L{str}
    @ivar enclosing_cwd:
    @type enclsoing_cwd: L{str}
    """

    def __init__(
            self,
            aliases=None,
            environ=None,
            enclosed_cwd=None,
            sys_stdin=None,
            sys_stdout=None,
            sys_stderr=None,
            sys_path=None
    ):
        """
        @param aliases: the aliases defined in the worker thread.
        @type aliases: L{dict} of L{str}->L{str}
        @param environ: environment variables of the worker thread
        @type environ: L{dict} of L{str} -> L{str}
        @param enclosed_cwd: cwd of the worker thread
        @type enclosed_cwd: L{str}
        @param sys_stdin: stdin of worker
        @type sys_stdin: L{io.IOBase}
        @param sys_stdout: stdout of worker
        @type sys_stdout: L{io.IOBase}
        @param sys_stderr: stderr of worker
        @type sys_stderr: L{io.IOBase}
        @param sys_path: L{sys.path} of the worker
        @type sys_path: L{list} of L{str}
        """
        self.aliases = aliases or {}
        self.environ = environ or {}
        self.enclosed_cwd = enclosed_cwd

        self.sys_stdin__ = self.sys_stdin = sys_stdin or sys.stdin
        self.sys_stdout__ = self.sys_stdout = sys_stdout or sys.stdout
        self.sys_stderr__ = self.sys_stderr = sys_stderr or sys.stderr
        self.sys_path = sys_path or sys.path[:]

        self.temporary_environ = {}

        self.enclosing_aliases = None
        self.enclosing_environ = None
        self.enclosing_cwd = None

    def __str__(self):
        s = _STATE_STR_TEMPLATE.format(
            self.enclosed_cwd,
            self.aliases,
            self.sys_stdin,
            self.sys_stdout,
            self.sys_stderr,
            self.temporary_environ,
            self.environ
        )
        return s

    @property
    def return_value(self):
        """
        The exitcode of this thread.
        
        @return: the exitcode of this thread. Defaults to 0.
        @rtype: L{int}
        """
        return self.environ.get('?', 0)

    @return_value.setter
    def return_value(self, value):
        """
        The exitcode of this thread.
        
        @param value: new exitcode
        @type value: L{int}
        """
        self.environ['?'] = value

    def environ_get(self, name):
        """
        Get a value from the environment.
        
        @param name: name to get.
        @type name: L{str}
        @return: the value
        @rtype: L{str}
        """
        return self.environ[name]

    def environ_set(self, name, value):
        """
        Set a value of the environment.
        
        @param name: name to get.
        @type name: L{str}
        @param value: the value
        @type value: L{str}
        """
        self.environ[name] = value

    def persist_child(self, child_state, persistent_level=0):
        """
        This is used to carry child shell state to its parent shell.
        
        @param child_state: Child state
        @type child_state: L{ShState}
        @param persistent_level:
        The persistent level dictates how variables from child worker
        shall be carried over to the parent shell/worker.
        
        Possible values are:
        
        C{0}: No persistent at all (shell script is by default in this mode)
        
        
        C{1}: Full persistent. Parent's variables will be the same as child's
        (User command from terminal is in this mode).
        
        C{2}: Semi persistent. Any more future children will have starting
        variables as the current child's ending variables. (__call__
        interface is by default in this mode).
        
        @type persistent_level: L{int}
        """
        if persistent_level == 0:
            # restore old state
            if os.getcwd() != child_state.enclosed_cwd:
                os.chdir(child_state.enclosed_cwd)
                # TODO: return status?

        elif persistent_level == 1:
            # update state
            self.aliases = dict(child_state.aliases)
            self.enclosing_aliases = child_state.aliases
            self.enclosed_cwd = self.enclosing_cwd = os.getcwd()
            self.environ = dict(child_state.environ)
            self.enclosing_environ = child_state.environ
            self.sys_path = child_state.sys_path[:]

        elif persistent_level == 2:
            # ensure future children will have child state
            self.enclosing_aliases = child_state.aliases
            self.enclosing_environ = child_state.environ
            self.enclosing_cwd = os.getcwd()
            # TODO: return status?
            if self.enclosed_cwd is not None:
                os.chdir(self.enclosed_cwd)

    @staticmethod
    def new_from_parent(parent_state):
        """
        Create new state from parent state. Parent's enclosing environ are merged as
        part of child's environ
        
        @param parent_state: Parent state
        @type parent_state: L{ShState}
        @return: the new state
        @rtye: L{ShState}
        """

        if parent_state.enclosing_aliases:
            aliases = parent_state.enclosing_aliases
        else:
            aliases = dict(parent_state.aliases)

        if parent_state.enclosing_environ:
            environ = parent_state.enclosing_environ
        else:
            environ = dict(parent_state.environ)
            environ.update(parent_state.temporary_environ)

        if parent_state.enclosing_cwd:
            os.chdir(parent_state.enclosing_cwd)

        return ShState(
            aliases=aliases,
            environ=environ,
            enclosed_cwd=os.getcwd(),
            sys_stdin=parent_state.sys_stdin__,
            sys_stdout=parent_state.sys_stdout__,
            sys_stderr=parent_state.sys_stderr__,
            sys_path=parent_state.sys_path[:]
        )


class ShWorkerRegistry(object):
    """
    Bookkeeping for all worker threads (both foreground and background).
    This is useful to provide an overview of all running threads.
    
    @ivar registry: a dict mapping the worker IDs to the workers
    @type registry: L{collections.OrderedDict} of L{int} -> L{ShBaseThread}
    """

    def __init__(self):
        self.registry = OrderedDict()
        self._count = 1
        self._lock = threading.Lock()

    def __repr__(self):
        ret = []
        for job_id, thread in self.registry.items():
            ret.append('{:>5d}  {}'.format(job_id, thread))
        return '\n'.join(ret)

    def __iter__(self):
        return self.registry.values().__iter__()

    def __len__(self):
        return len(self.registry)

    def __contains__(self, item):
        return item in self.registry

    def _get_job_id(self):
        try:
            self._lock.acquire()
            job_id = self._count
            self._count += 1
            return job_id
        finally:
            self._lock.release()

    def add_worker(self, worker):
        """
        Add a worker to the registry and set the job ID of the worker.
        
        @param worker: worker to add
        @type worker: L{ShBaseThread}
        """
        worker.job_id = self._get_job_id()
        self.registry[worker.job_id] = worker

    def remove_worker(self, worker):
        """
        Remove a previously added worker from this registry.
        
        @param worker: worker to remove
        @type worker: L{ShBaseThread}
        """
        self.registry.pop(worker.job_id)

    def get_worker(self, job_id):
        """
        Get the worker with the specified job ID.
        
        @param job_id: id of worker to get
        @type job_id: L{int}
        @return: the worker or L{None}
        @rtype: L{ShBaseThread} or L{None}
        """
        return self.registry.get(job_id, None)

    def get_first_bg_worker(self):
        """
        Return the first worker running in background.
        
        @return: a worker running in background or L{None}
        @rtype: L{ShBaseThread} or L{None}
        """
        for worker in self.registry.values():
            if worker.is_background:
                return worker
        else:
            return None

    def purge(self):
        """
        Kill all registered thread and clear the entire registry
        """
        for worker in self.registry.values():
            worker.kill()
            # The worker removes itself from the registry when killed.


class ShBaseThread(threading.Thread):
    """
    The basic Thread class provides life cycle management.
    
    @cvar CREATED: symbolic constant indicating the state of this thread.
    @type CREATED: L{int}
    @cvar STARTED: symbolic constant indicating the state of this thread.
    @type STARTED: L{int}
    @cvar STOPPED: symbolic constant indicating the state of this thread.
    @type STOPPED: L{int}
    
    @ivar registry: the registry responsible for managing this worker
    @type registry: L{ShWorkerRegistry}
    @ivar job_id: the job ID of this worker (None if not yet set)
    @type job_id: L{int} or L{None}
    @ivar command: the command that this thread runs
    @type command: L{str}
    @ivar parent: the parent worker or runtime
    @type parent: L{ShBaseThread} or L{stash.system.shruntime.ShRuntime}
    @ivar state: the state of this thread.
    @type state: L{ShState}
    @ivar killed: if True, this thread has been killed.
    @type killed: L{bool}
    @ivar killer: the job ID of the killer of this thread. Defaults to 0
    @type killer: L{int}
    @param child_thread: current foreground child thread
    @type child_thread: L{ShBaseThread} or L{None}
    """

    CREATED = 1
    STARTED = 2
    STOPPED = 3

    def __init__(self, registry, parent, command, target=None, is_background=False, environ={}, cwd=None):
        """
        @param registry: the registry responsible for managing this worker
        @type registry: L{ShWorkerRegistry}
        @param command: the command that this thread runs
        @type command: L{str}
        @param parent: the parent worker or runtime
        @type parent: L{ShBaseThread} or L{stash.system.shruntime.ShRuntime}
        @param target: function to execute
        @type target: callable
        @param is_background: if True, switch to background
        @type is_background: L{bool}
        @param name: the name of this thread.
        @type name: L{str}
        @param environ: environment variables of this worker
        @type environ: L{dict} of L{str} -> L{str}
        @param cwd: CWD of this worker
        @type cwd: L{str}
        """
        super(ShBaseThread, self).__init__(group=None, target=target, name='_shthread', args=(), kwargs=None)

        # Registry management
        self.registry = weakref.proxy(registry)
        self.job_id = None  # to be set by the registry
        registry.add_worker(self)

        # The command that the thread runs
        if command.__class__.__name__ == 'ShIO':
            self.command = ''.join(command._buffer)[::-1].strip()
        else:
            self.command = command

        self.parent = weakref.proxy(parent)

        # Set up the state based on parent's state
        self.state = ShState.new_from_parent(parent.state)
        self.state.environ.update(environ)
        if cwd is not None:
            self.state.enclosed_cwd = cwd
            os.chdir(cwd)

        self.killed = False
        self.killer = 0
        self.child_thread = None

        self.set_background(is_background)

    def __repr__(self):
        command_str = str(self.command)
        return '[{}] {} {}'.format(
            self.job_id,
            {
                self.CREATED: 'Created',
                self.STARTED: 'Started',
                self.STOPPED: 'Stopped'
            }[self.status()],
            command_str[:20] + ('...' if len(command_str) > 20 else '')
        )

    def status(self):
        """
        Status of the thread. Created, Started or Stopped.
        
        
        @return: the status (started/stopped/created) of this thread
        @rtype: one of the symbolic constants (L{int})
        """
        
        # STATES
        # isAlive() | self.ident  | Meaning
        # ----------+-------------+--------
        # False     |     None    | created
        # False     | not None    | stopped
        # True      |     None    | impossible
        # True      | not None    | running
        
        if self.isAlive():
            return self.STARTED
        elif (not self.is_alive()) and (self.ident is not None):
            return self.STOPPED
        else:
            return self.CREATED

    def set_background(self, is_background=True):
        """
        Push this thread into the background or into the foreground.
        
        @param is_background: if True, push into background. If false, 
        push into foreground
        @type is_background: L{bool}
        """
        self.is_background = is_background
        if is_background:
            if self.parent.child_thread is self:
                self.parent.child_thread = None
        else:
            assert self.parent.child_thread is None, 'parent must have no existing child thread'
            self.parent.child_thread = self

    def is_top_level(self):
        """
        Whether or not the thread is directly under the runtime, aka top level.
        A top level thread has the runtime as its parent
        
        @return: whether this is a toplevel worker or not
        @rtype: L{bool}
        """
        return not isinstance(self.parent, ShBaseThread) and not self.is_background

    def cleanup(self):
        """
        End of life cycle management by remove itself from registry and unlink
        it self from parent if exists.
        """
        self.registry.remove_worker(self)
        if not self.is_background:
            assert self.parent.child_thread is self
            self.parent.child_thread = None

    def on_kill(self):
        """
        This should be called when a thread was killed.
        Calling this method will set self.killer to the job_id of the current Thread.
        """
        ct = threading.current_thread()
        if not isinstance(ct, ShBaseThread):
            self.killer = 0
        else:
            self.killer = ct.job_id


# noinspection PyAttributeOutsideInit
class ShTracedThread(ShBaseThread):
    """
    Killable thread implementation with trace.
    
    This works with almost every python version, but it has performance
    drawbacks.
    """

    def __init__(self, registry, parent, command, target=None, is_background=False, environ={}, cwd=None):
        super(ShTracedThread,
              self).__init__(
                  registry,
                  parent,
                  command,
                  target=target,
                  is_background=is_background,
                  environ=environ,
                  cwd=cwd
              )

    def start(self):
        """Start the thread."""
        self.__run_backup = self.run
        self.run = self.__run  # Force the Thread to install our trace.
        threading.Thread.start(self)

    def __run(self):
        """Hacked run function, which installs the trace."""
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, why, arg):
        """
        Function for the globaltrace.
        
        We use this function for the L{kill}() mechanism.
        
        @param frame: current stack frame
        @type frame: L{types.FrameType}
        @param why: reason for the call of this method/function.
        @type why: L{str}
        @param arg: depends on the event type
        @type arg: depends on the event type
        @return: a function to use for tracing the new scope or None
        @rtype: L{types.MethodType} or L{types.FunctionType} or L{None}
        """
        return self.localtrace if why == 'call' else None

    def localtrace(self, frame, why, arg):
        """
        Function for the localtrace.
        
        We use this function for the L{kill}() mechanism.
        
        @param frame: current stack frame
        @type frame: L{types.FrameType}
        @param why: reason for the call of this method/function.
        @type why: L{str}
        @param arg: depends on the event type
        @type arg: depends on the event type
        @return: a function to use for tracing the new scope or None
        @rtype: L{types.MethodType} or L{types.FunctionType} or L{None}
        @raises: L{KeyboardInterrupt}
        """
        if self.killed:
            if why == 'line':
                if self.child_thread:
                    self.child_thread.kill()
                raise KeyboardInterrupt()
        return self.localtrace

    def kill(self):
        """
        Kill this thread.
        """
        if not self.killed:
            self.killed = True
            self.on_kill()


class ShCtypesThread(ShBaseThread):
    """
    A thread class that supports raising exception in the thread from
    another thread (with ctypes).
    
    This thread type has supperior performance compared to L{ShTracedThread},
    but suffers from compatibility problems.
    """

    def __init__(self, registry, parent, command, target=None, is_background=False, environ={}, cwd=None):
        super(ShCtypesThread,
              self).__init__(
                  registry,
                  parent,
                  command,
                  target=target,
                  is_background=is_background,
                  environ=environ,
                  cwd=cwd
              )

    def _async_raise(self):
        """
        Raises a KeyboardInterrupt in this thread.
        
        @raises: L{ValueError}
        @raises: L{SystemError}
        """
        tid = self.ident
        res = python_capi.PyThreadState_SetAsyncExc(ctypes.c_long(tid) if M_64 else tid, ctypes.py_object(KeyboardInterrupt))
        if res == 0:
            raise ValueError("invalid thread id")
        elif res != 1:
            # "if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"
            python_capi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), 0)
            raise SystemError("PyThreadState_SetAsyncExc failed")

        return res

    def kill(self):
        """
        Kill this thread.
        """
        if not self.killed:
            self.killed = True
            if self.child_thread:
                self.child_thread.kill()
            try:
                res = self._async_raise()
            except (ValueError, SystemError):
                self.killed = False
            else:
                self.on_kill()
