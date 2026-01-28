import subprocess
import sys

from Code.Z import Util


def run_lucas(*args):
    li = []
    if sys.argv[0].endswith(".py"):
        li.append(sys.executable)
        li.append("LucasR.py")
    else:
        if Util.is_windows():
            li.append("python.exe")
            li.append("LucasR.pyc")
        else:
            li.append("./LucasR")
    li.extend(args)
    return subprocess.Popen(li)
