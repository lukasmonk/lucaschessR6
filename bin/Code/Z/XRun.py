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
            li.append("LucasR.exe")
        else:
            li.append("./LucasR")
    li.extend(args)

    if Util.is_windows():
        cmd_string = " ".join(f'"{x}"' for x in li)
        return subprocess.Popen(cmd_string, shell=True)
    else:
        return subprocess.Popen(li)


# def run_lucas0(*args):
#     li = []
#     if sys.argv[0].endswith(".py"):
#         li.append(sys.executable)
#         li.append("LucasR.py")
#     else:
#         if Util.is_windows():
#             cmd = f'start "" "LucasR.exe"'
#
#             if args:
#                 cmd += " " + " ".join(f'"{a}"' for a in args)
#
#             return subprocess.Popen(cmd, shell=True)
#         else:
#             li.append("./LucasR")
#     li.extend(args)
#     return subprocess.Popen(li)
