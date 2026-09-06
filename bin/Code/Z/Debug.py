import builtins
import functools
import inspect
import os
import sys
import time
import traceback
from datetime import datetime

from Code.Z import Util

DEBUG_ENGINES_ALL = False
DEBUG_ENGINES = False or DEBUG_ENGINES_ALL
DEBUG_ENGINES_SEND = False or DEBUG_ENGINES_ALL

COLORS = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "reset": "\033[0m",
}


def pr(*x):
    lx = len(x) - 1
    for n, cl in enumerate(x):
        sys.stdout.write(str(cl))

        if n < lx:
            sys.stdout.write(" ")


def prln(*x, color=None):
    if color and color in COLORS:
        sys.stdout.write(COLORS[color])

    dt = datetime.fromtimestamp(time.time())
    decimas = dt.microsecond // 100000
    resultado = f"{dt.strftime('%H:%M:%S')}.{decimas} "
    pr(resultado)

    pr(*x)

    if color and color in COLORS:
        sys.stdout.write(COLORS["reset"])

    sys.stdout.write("\n")
    return True


def stack():
    prln("=" * 100)
    for line in traceback.format_stack()[:-1]:
        prln(line.strip())
    prln("=" * 100)


def stack0(txt=None):
    frame = inspect.stack()[2]
    archivo = frame.filename
    linea = frame.lineno
    funcion = frame.function
    prln(f"Llamado desde: función '{funcion}' en {archivo}, línea {linea}, {txt or ''!s}")


def printf(*txt):
    with open("stack.txt", "at", encoding="utf-8") as q:
        q.writelines(f"{t!s} " for t in txt)
        q.write("\n")


class Timer:
    def __init__(self, label="Timer"):
        self.label = label
        self.start = 0

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        elapsed = time.monotonic() - self.start
        prln(f"[{self.label}] Elapsed: {elapsed:.4f}s", color="cyan")


def timeit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - start
            prln(f"[{func.__name__}] Executed in {elapsed:.4f}s", color="cyan")

    return wrapper


builtins.stack = stack
builtins.stack0 = stack0
builtins.prln = prln


class LogDebug:
    def __init__(self, logname):
        self.logname = os.path.abspath(logname)

    def write(self, buf):
        if buf.startswith("Traceback"):
            buf = f"{Util.today()}\n{buf}"
        with open(self.logname, "at") as ferr:
            ferr.write(buf)
        pr(buf)

    def writeln(self, buf):
        with open(self.logname, "at") as ferr:
            ferr.write(f"{buf}\n")
        prln(buf)

    def flush(self):
        pass  # To remove error 120 at exit
