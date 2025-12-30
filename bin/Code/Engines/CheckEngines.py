import os
import platform
import shutil

import Code
from Code import Util
from Code.Engines import Engines
from Code.QT import QTMessages

STOCKFISH_KEY = "STOCKFISH17.1"


def check_stockfish(window, check_again):
    conf_stockfish = Code.configuration.engines.dic_engines()["stockfish"]

    dic = Code.configuration.read_variables(STOCKFISH_KEY)
    if "NAME" in dic:
        conf_stockfish.name = dic["NAME"]
        if not check_again:
            return True

    seek = "64" if platform.machine().endswith("64") else "32"
    Code.procesador.close_engines()

    folder = os.path.dirname(conf_stockfish.path_exe)

    path_versions = Util.opj(folder, "versions.txt")
    lista = []
    with open(path_versions, "rt") as f:
        for linea in f:
            linea = linea.strip()
            if seek in linea:
                lista.append(linea)

    # Se guarda el primero, por si el resto no son validos, y no se muestra el mensaje mas veces
    conf_stockfish.name = lista[0].replace(".exe", "")
    Code.configuration.write_variables(STOCKFISH_KEY, {"NAME": conf_stockfish.name})

    mensaje = _("Selecting the best stockfish version for your CPU")
    with QTMessages.one_moment_please(window, mensaje) as um:
        for file_engine in lista[1:]:  # el primero no lo miramos
            path_engine = Util.opj(folder, file_engine)
            if Engines.is_valid_engine(path_engine):
                correct = file_engine
                um.label(mensaje + "\n" + file_engine)
                path_engine = conf_stockfish.path_exe
                Util.remove_file(path_engine)
                path_correct = Util.opj(folder, correct)
                shutil.copy(path_correct, path_engine)

                conf_stockfish.name = correct.replace(".exe", "")
                Code.configuration.write_variables(STOCKFISH_KEY, {"NAME": conf_stockfish.name})
            else:
                break
    return True


def check_engines(window):
    if not Code.engines_has_been_checked:  # Just check it once.
        check_stockfish(window, False)
        Code.engines_has_been_checked = True


def current_stockfish():
    dic = Code.configuration.read_variables(STOCKFISH_KEY)
    return dic.get("NAME", "stockfish")
