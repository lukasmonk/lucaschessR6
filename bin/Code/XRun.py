import subprocess
import sys

from Code import Util


def run_lucas(*args):
    li = []
    if sys.argv[0].endswith(".py"):
        li.append(sys.executable)
        li.append("LucasR.py")
    else:
        li.append("LucasR.exe" if Util.is_windows() else "./LucasR")
    li.extend(args)
    return subprocess.Popen(li)
