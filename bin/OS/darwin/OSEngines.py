import os
import stat

import FasterCode

from Code.Base.Constantes import ENG_INTERNAL
from Code.Engines import Engines
from Code.Z import Util


def read_engines(folder_engines):
    dic_engines = {}

    def mas(clave, autor, version, url, exe, elo, folder=None, nodes_compatible=None):
        if folder is None:
            folder = clave
        path_exe = Util.opj(folder_engines, folder, exe)
        engine = Engines.Engine(
            clave,
            autor,
            version,
            url,
            path_exe,
        )
        if not os.access(path_exe, os.X_OK):
            try:
                os.chmod(path_exe, os.stat(path_exe).st_mode | stat.S_IXUSR)
            except OSError:
                pass
        engine.set_type(ENG_INTERNAL)
        engine.elo = elo
        engine.set_uci_option("Log", "false")
        engine.set_uci_option("Ponder", "false")
        engine.set_uci_option("Hash", "16")
        engine.set_uci_option("Threads", "1")
        dic_engines[clave] = engine
        if nodes_compatible is not None:
            engine.set_nodes_compatible(nodes_compatible)
        return engine

    cm = mas(
        "stockfish",
        "Tord Romstad, Marco Costalba, Joona Kiiski",
        "18",
        "https://stockfishchess.org/",
        "stockfish-18-arm64",
        3700,
    )
    cm.set_uci_option("Hash", "64")
    cm.set_uci_option("Threads", "2")
    cm.set_multipv(10, 256)

    mas("irina", "Lucas Monge", "0.20", "https://github.com/lukasmonk/irina", "irina", 1500)
    mas("eguzki", "Lucas Monge", "1.0", "", "eguzki", 1500)
    mas("eguzkilore", "Lucas Monge", "1.0", "", "eguzkilore", 1000)

    return dic_engines


def li_engines_fixed_elo() -> tuple:
    return (
        ("stockfish", 1400, 3100),
        ("irina", 900, 1800),
        ("eguzki", 1000, 2700),
    )
