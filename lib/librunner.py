"""module for running a script in a specific python version"""
import os
import sys
import ctypes
import objc_util
import base64
import pickle
import threading
import select
import time

from stash.system.shio import ShIO
from stash.system.shiowrapper import ShStdinWrapper


# TODO:
# - RPC to _stash (if possible)
# - killing mechanism

EXE_DIR = os.path.dirname(sys.executable)
OLD_PY2_FRAMEWORK = "PythonistaKit"
NEW_PY2_FRAMEWORK = "Py2Kit"

CODE_TEMPLATE = """#Py3 preperation template
def log(msg):  # before import so that we can notify about the imports
	'''debug help function'''
	lp = {lp}
	if lp is None:
		return
	with open(lp, "a") as l:
		l.write(msg)
	return

log("=====================\\n")
log("title: {t}\\n")
log("importing modules...\\n")

import os
import sys
import pickle
import base64
import traceback
import threading

log("Modules imported, defining vars...\\n")

CWD = "{cwd}"
CODE = base64.b64decode("{b64c}")  # use b64 to prevent syntax errors
STDIN_FD = {stdin}
STDOUT_FD = {stdout}
STDERR_FD = {stderr}
ARGV = {argv}

log("Vars defined, opening I/O...\\n")

# prepare I/O
sys.stdin = open(STDIN_FD, "r")
sys.stdout = open(STDOUT_FD, "w")
sys.stderr = open(STDERR_FD, "w")

log("I/O opened, preparing OS environment...\\n")

# prepare env, cwd ...
os.chdir(CWD)

log("OS environment prepared, preparing scope...\\n")

# prepare scope
c_globals = pickle.loads(base64.b64decode("{globals}"))
c_locals = pickle.loads(base64.b64decode("{locals}"))

log("Scope prepared, setting argv...\\n")
sys.argv = ARGV

log("Everything setup. Starting thread...\\n")

# execute
def run(code, c_globals, c_locals):
	'''executes the script'''
	log("Executing...\\n")
	try:
		exec(code, c_globals, c_locals)
		log("Exec success.\\n")
	except Exception as e:
		# only print traceback, so we can close sys.std*
		log("Showing error...\\n")
		traceback.print_exc(file=sys.stderr)
	finally:
		log("Closing I/O...\\n")
		sys.stdin.close()
		sys.stdout.close()
		sys.stderr.close()
	log("Done.\\n")
thr = threading.Thread(target=run, args=(CODE, c_globals, c_locals))
thr.daemon = False
thr.start()
"""

def get_dll(version):
	"""returns a PyDLL for a specific python version"""
	if version == 2:
		for name in (OLD_PY2_FRAMEWORK, NEW_PY2_FRAMEWORK):
			path = os.path.join(EXE_DIR, "Frameworks", name + ".framework", name)
			if os.path.exists(path):
				return ctypes.PyDLL(path)
		raise RuntimeError("Could not load any Python 2 Framework!")
	elif version == 3:
		return ctypes.pythonapi
	else:
		raise ValueError("Unknown Python version: '{v}'!".format(v=version))


# @objc_util.on_main_thread
def exec_string(dll, s):
	"""execute a string with the dll"""
	state = dll.PyGILState_Ensure()
	dll.PyRun_SimpleString(s)
	dll.PyGILState_Release(state)

def exec_string_with_new_io(dll, s, cwd=None, globals={}, locals={}, argv=None, lp=None, lt="?"):
	"""executes string s using dll and return stdin, stdout, stderr"""
	if cwd is None:
		cwd = os.getcwd()
	inr, inw = os.pipe()
	outr, outw = os.pipe()
	excr, excw = os.pipe()
	stdin = os.fdopen(inw, "w")
	stdout = os.fdopen(outr, "r")
	stderr = os.fdopen(excr, "r")
	filled_t = CODE_TEMPLATE.format(
		b64c=base64.b64encode(s),
		cwd=cwd,
		stdin=inr,
		stdout=outw,
		stderr=excw,
		globals=base64.b64encode(pickle.dumps(globals)),
		locals=base64.b64encode(pickle.dumps(locals)),
		lp=repr(lp),  # eval(repr(obj)) == obj
		t=lt,
		argv=repr(argv if argv is not None else sys.argv),
		)
	thr = threading.Thread(target=exec_string, args=(dll, filled_t), name="Py3/Py2 Crossrunner")
	thr.daemon = False
	thr.start()
	return stdin, stdout, stderr


def exec_string_with_io(dll, s, ins, outs, errs, *args, **kwargs):
	"""Like exec_string_with_new_io, but uses specified std*. Blocking."""
	i, o, e = exec_string_with_new_io(dll, s, *args, **kwargs)
	try:
		relay_data(((e, errs), (o, outs), (ins, i)), loop=0.2)
	finally:
		close_files(i, o, e)


def close_files(*args):
	"""closes all files"""
	for arg in args:
		try:
			if isinstance(arg, (int, long)):
				os.close(arg)
			else:
				arg.close()
		except:
			pass

def can_read(f):
	"""check if f contains data which can be read"""
	if isinstance(f, (int, long)) or hasattr(f, "fileno"):
		return (f in select.select([f], [], [], 0)[0])
	elif isinstance(f, ShIO):
		return True  # f.can_read()
	elif isinstance(f, ShStdinWrapper):
		thr = threading.current_thread()
		sin = thr.state.sys_stdin
		return can_read(sin)
	else:
		raise ValueError("Cant check {f}".format(f=repr(f)))


def relay_data(files, loop, buffersize=4096):
	"""Transfers data from one file to another file.
'files' should be a sequence of (readfile, writefile),
where readfile is the file to be read from and writerile the file which
will be written to.
'loop' defines the loop behavior of the function.
If loop is False, only read and write okce for each pair of files.
If loop is an integer of float, sleep this time between each loop.
"""
	files = list(files)
	while True:
		if len(files) == 0:
			break
		for rf, wf in files:
			if hasattr(wf, "fileno"):
				fd = wf.fileno()
				try:
					os.fstat(fd)
				except OSError:
					files.remove((rf, wf))
					break
			else:
				fd = None
			if can_read(rf):
				if hasattr(rf, "read_no_block"):
					may_remove = False
					data = rf.read_no_block(buffersize)
				else:
					may_remove = True
					data = rf.read(buffersize)
				if (data == "") and may_remove:
					files.remove((rf, wf))
				else:
					if fd is not None:
						try:
							n = os.write(fd, data)
						except OSError:
							files.remove((rf, wf))
							break
						else:
							if (n == 0) and (len(data) != 0):
								# closed pipe
								files.remove((rf, wf))
								break
					else:
						wf.write(data)
		if loop in (False, None):
			break
		else:
			time.sleep(loop)


def _test():
	# test code. status message are UPPERCASE to see test starts/end easier
	lp = os.path.abspath("./librunnerlog.log")
	dll3 = get_dll(3)
	# 1. syntax error print
	sys.stdout.write("STARTING SYNTAX ERROR TEST PY3...\n")
	i, o, e = exec_string_with_new_io(
		dll3,
		"print 'this should be an error in py3'",
		lp=lp,
		lt="PY3 Syntax error test"
		)
	sys.stdout.write("READING STDOUT (expected empty)...\n")
	sys.stdout.write(o.read(2048)+"\n")
	time.sleep(0.5)
	sys.stdout.write("READING STDERR (expected traceback)...\n")
	sys.stdout.write(e.read(4096)+"\n")
	time.sleep(0.5)
	sys.stdout.write("CLOSING I/O...\n")
	close_files(i, o, e)
	sys.stdout.write("\nSYNTAX ERROR TEST FINISHED\n")
	time.sleep(1)
	# raise Exception("Breaking here")  # uncomment this to see that the above test is working
	# 2. echo test
	sys.stdout.write("STARTING ECHO TEST...\n")
	i, o, e = exec_string_with_new_io(
		dll3,
		"""print("echo test start")
i = input('Hello, what is your name? ')
u = i.uppercase()
print(u)
print("echo test end")
""",
		lp=lp,
		lt="PY3 echo test",
		)
	sys.stdout.write("READING STDOUT (expected prompt)...\n")
	#sys.stdout.write(o.read(2048)+"\n")
	time.sleep(0.5)
	sys.stdout.write("READING STDERR (expected empty)...\n")
	sys.stdout.write(e.read(4096)+"\n")
	time.sleep(0.5)
	sys.stdout.write("PLEASE ENTER A STRING TO SEND TO STDIN:\n")
	il = sys.stdin.readline()
	sys.stdout.write("SENDING DATA TO STDIN...\n")
	i.write(il)
	time.sleep(0.5)
	sys.stdout.write("READING STDOUT (expected uppercase input)...\n")
	sys.stdout.write(o.read(4096))
	time.sleep(0.5)
	sys.stdout.write("CLOSING I/O...\n")
	close_files(i, o, e)
	sys.stdout.write("\nECHO TEST FINISHED\n")


if __name__ == "__main__":
	_test()