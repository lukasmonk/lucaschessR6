import builtins
import functools
import sys
import time
import traceback

DEBUG_ENGINES = False
DEBUG_ENGINES_SEND = DEBUG_ENGINES

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
        if isinstance(cl, (str, int, float, bool, type(None))):
            sys.stdout.write(str(cl))
        else:
            sys.stdout.write(cl)

        if n < lx:
            sys.stdout.write(" ")


def prln(*x, color=None):
    if color and color in COLORS:
        sys.stdout.write(COLORS[color])

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


def printf(*txt):
    with open("stack.txt", "at", encoding="utf-8") as q:
        for t in txt:
            q.write(str(t) + " ")
        q.write("\n")


class Timer:
    def __init__(self, label="Timer"):
        self.label = label
        self.start = 0

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        elapsed = time.time() - self.start
        prln(f"[{self.label}] Elapsed: {elapsed:.4f}s", color="cyan")


def timeit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.time() - start
            prln(f"[{func.__name__}] Executed in {elapsed:.4f}s", color="cyan")

    return wrapper


setattr(builtins, "stack", stack)
