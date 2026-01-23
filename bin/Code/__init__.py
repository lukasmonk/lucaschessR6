import os
import ssl
import sys
from typing import Optional

from Code.Z import Util, Debug

Util.randomize()

current_dir = os.path.abspath(os.path.realpath(os.path.dirname(sys.argv[0])))
if current_dir:
    os.chdir(current_dir)

lucas_chess: Optional[str] = None  # asignado en Translate

platform = "windows" if sys.platform == "win32" else "linux"

folder_code_os = Util.opj(current_dir, "Code", "OS", platform)
sys.path.insert(0, folder_code_os)
sys.path.insert(0, os.path.realpath(os.curdir))

folder_root = os.path.realpath("..")
folder_resources = Util.opj(folder_root, "Resources")


def path_resource(*lista):
    p = folder_resources
    for x in lista:
        p = Util.opj(p, x)
    return os.path.realpath(p)


folder_os = path_resource("OS", platform)
folder_engines = Util.opj(folder_os, "Engines")

if not os.environ.get("PYTHONHTTPSVERIFY", "") and getattr(ssl, "_create_unverified_context", None):
    ssl._create_default_https_context = getattr(ssl, "_create_unverified_context")

configuration = None
procesador = None

all_pieces = None

tbook = path_resource("Openings", "GMopenings.bin")
tbookPTZ = path_resource("Openings", "fics15.bin")
tbookI = path_resource("Openings", "irina.bin")
manager_tutor = None

font_mono = "Courier New" if Util.is_windows() else "Mono"

list_engine_managers = None

mate_en_dos = 180805

runSound = None

translations = None

analysis_eval = None

eboard = None

dic_colors: Optional[dict] = None
dic_qcolors: Optional[dict] = None

dic_markers: dict = {}

themes = None

main_window = None

garbage_collector = None

engines_has_been_checked = False

web = "https://lucaschess.pythonanywhere.com"
blog = "https://lucaschess.blogspot.com"
github = "https://github.com/lukasmonk/lucaschessR2"


def get_themes():
    global themes
    if themes is None:
        from Code.Themes import Themes

        themes = Themes.Themes()
    return themes


def relative_root(path):
    # Used only for titles/labels
    try:
        path = os.path.normpath(os.path.abspath(path))
        rel = os.path.relpath(path, folder_root)
        if not rel.startswith(".."):
            path = rel
    except ValueError:
        pass

    return path


BASE_VERSION = "C"
VERSION = "R 6.0.0.3"

if __debug__:

    Debug.prln("Modo debug activado", color="green")
    if Debug.DEBUG_ENGINES:
        Debug.prln("Modo debug engine", color="red")
    if Debug.DEBUG_ENGINES_SEND:
        Debug.prln("Modo debug engine send", color="blue")
