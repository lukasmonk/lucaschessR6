import os
import os.path

from PySide6 import QtCore

import Code
from Code import Util
from Code.Base.Constantes import BOOK_BEST_MOVE, ENG_EXTERNAL
from Code.QT import QTDialogs
from Code.SQL import UtilSQL


class Engine:
    uci_options_sqlite = "uci_options.sqlite"

    def __init__(self, alias="", autor="", version="", url="", path_exe="", args=None):
        # self.alias = key
        self.alias = alias
        self._name = None
        self.autor = autor
        self.args = [] if args is None else args
        self.version = version
        self.liUCI = []
        self.multiPV = 0
        self.maxMultiPV = 0
        self.siDebug = False
        self.nomDebug = None
        self.parent_external = None
        self.url = url
        self.path_exe = Util.relative_path(path_exe) if path_exe else ""
        self.elo = 0
        self.id_info = ""
        self.max_depth = 0
        self.max_time = 0  # Seconds
        self.nodes = 0
        self.min_fixed_depth = 0
        self.id_name = alias
        self.id_author = autor
        self.book = None
        self.book_max_plies = 0
        self.book_rr = BOOK_BEST_MOVE
        self.emulate_movetime = False
        self.nodes_compatible = None

        self.menu = alias
        self.type = ENG_EXTERNAL
        # self.fixed_depth = None

        self._li_uci_options = None

    def set_nodes_compatible(self, ok):
        self.nodes_compatible = ok

    def set_nodes(self, nodes):
        self.nodes = nodes

    def set_type(self, tp):
        self.type = tp

    def set_nodes_maia(self, level):
        """Devuelve el número de nodos para el motor Maia según su nivel."""
        if not Code.configuration.x_maia_nodes_exponential:
            self.nodes = 1
        else:
            dic_nodes = {
                1100: 1,
                1200: 2,
                1300: 5,
                1400: 12,
                1500: 30,
                1600: 60,
                1700: 130,
                1800: 300,
                1900: 450,
                2200: 800,
            }
            self.nodes = dic_nodes.get(level, 1)

    def set_min_fixed_depth(self, min_depth):
        self.min_fixed_depth = min_depth

    def is_nodes_compatible(self):
        return self.is_type_external() if self.nodes_compatible is None else self.nodes_compatible

    def save(self):
        return Util.save_obj_pickle(
            self,
            li_exclude=[
                "ICON",
            ],
        )

    def restore(self, txt, is_extern=False):
        Util.restore_obj_pickle(self, txt)
        if is_extern:
            self.set_extern()
        if self.parent_external:
            conf_parent = Code.configuration.engines.dic_engines().get(self.parent_external)
            if conf_parent:
                self.path_exe = conf_parent.path_exe
        previous = os.path.abspath(os.curdir)
        try:
            self.read_uci_options()
            return True
        except Exception:
            os.chdir(previous)
            return False

    def exists(self):
        return os.path.isfile(self.path_exe)

    def set_extern(self):
        self.type = ENG_EXTERNAL

    def is_type_external(self):
        return self.type == ENG_EXTERNAL

    def nombre_ext(self, ext_with_symbol=True):
        name = self.name
        if self.is_type_external():
            name = self.alias
            if ext_with_symbol:
                name += " 📡"

        return name

    def clone(self):
        eng = Engine()
        eng.restore(self.save())
        return eng

    def argumentos(self):
        return self.args

    def debug(self, txt):
        self.siDebug = True
        self.nomDebug = self.alias + "-" + txt

    def reset_uci_options(self):
        li_uci_options = self.li_uci_options()
        for op in li_uci_options:
            op.valor = op.default
        self.liUCI = []

    def change_uci_default(self, name, default):
        li_uci_options = self.li_uci_options()
        for op in li_uci_options:
            if op.name == name:
                op.default = default

    def set_uci_option(self, name, valor):
        li_uci_options = self.li_uci_options()
        is_changed = False
        for op in li_uci_options:
            if op.name == name:
                if op.tipo == "check":
                    valor = str(valor).lower()
                    if valor not in ("true", "false"):
                        valor = "false"
                op.valor = valor
                if op.default != valor:
                    if isinstance(op.default, int):
                        if isinstance(op.default, int) or (isinstance(op.default, str) and valor.isdigit()):
                            is_changed = op.default != int(valor)
                        else:
                            is_changed = True
                    else:
                        is_changed = True
                    break
        for pos, (xcomando, xvalor) in enumerate(self.liUCI):
            if xcomando == name:
                if is_changed:
                    self.liUCI[pos] = (name, valor)
                else:
                    del self.liUCI[pos]
                return
        if is_changed:
            self.liUCI.append((name, valor))

    def set_multipv(self, num, maximo):
        self.multiPV = int(num) if num else 1
        self.maxMultiPV = int(maximo) if maximo else 1

    def set_multipv_var(self, xmultipv: str | int):
        if xmultipv == "PD":
            multi_pv = min(self.maxMultiPV, 10)
            multi_pv = max(multi_pv, self.multiPV)
            for comando, valor in self.liUCI:
                if comando == "MultiPV":
                    multi_pv = int(valor)
                    break
            self.multiPV = multi_pv

        elif xmultipv == "MX":
            self.multiPV = self.maxMultiPV
        else:
            self.multiPV = int(xmultipv)
            if self.multiPV > self.maxMultiPV:
                self.multiPV = self.maxMultiPV
        if self.multiPV < 1:
            self.multiPV = self.maxMultiPV

    def can_be_tutor_analyzer(self):
        return self.maxMultiPV >= 4 and not self.is_maia()

    def can_be_supertutor(self):
        return self.maxMultiPV >= 218 and not self.is_maia()

    def is_maia(self):
        return self.alias.startswith("maia-")

    def level_maia(self):
        try:
            level = int(self.alias[5:])
        except ValueError:
            level = 0
        return level

    def remove_log(self, fich):
        Util.remove_file(Util.opj(os.path.dirname(self.path_exe), fich))

    @property
    def name(self):
        if self._name:
            return self._name
        alias = Util.primera_mayuscula(self.alias)
        if not alias.endswith(self.version):
            alias += f" {self.version}"
        return alias

    @name.setter
    def name(self, value):
        self._name = value

    def ejecutable(self):
        return self.path_exe

    def remove_uci_options(self):
        if self.type == ENG_EXTERNAL:
            path_uci_options = os.path.join(Code.configuration.paths.folder_config, self.uci_options_sqlite)
            with UtilSQL.DictTextSQL(path_uci_options) as dbuci:
                del dbuci[self.key_engine()]

    def key_engine(self):
        if self.type == ENG_EXTERNAL:
            stat = os.stat(self.path_exe)
            return f"{os.path.basename(self.path_exe)}_{stat.st_size}_{stat.st_mtime}"
        else:
            return "maia" if self.alias.startswith("maia") else self.alias

    def read_uci_options(self):
        if self.type == ENG_EXTERNAL:
            path_uci_options = os.path.join(Code.configuration.paths.folder_config, self.uci_options_sqlite)
        else:
            path_uci_options = os.path.join(Code.folder_os, self.uci_options_sqlite)

        with UtilSQL.DictTextSQL(path_uci_options) as dbuci:
            key = self.key_engine()
            if key in dbuci:
                clines = dbuci[key]
                lines = clines.split("\n")
            else:
                lines = get_uci_options(self.path_exe)
                if lines:
                    dbuci[key] = "\n".join(lines)
                else:
                    lines = []  # Ensure lines is always an iterable

        self._li_uci_options = []
        dc_op = {}

        for line in lines:
            line = line.strip()
            if line.startswith("id name"):
                self.id_name = line[8:]
                if not self.name:
                    self._name = self.id_name
            elif line.startswith("id author"):
                self.id_author = line[10:]
            elif line.startswith("option name "):
                op = OpcionUCI()
                if op.lee(line):
                    self._li_uci_options.append(op)
                    dc_op[op.name] = op
                    if op.name == "MultiPV":
                        self.set_multipv(op.default, op.maximo)

        for comando, valor in self.liUCI:
            if comando in dc_op:
                op = dc_op[comando]
                op.valor = valor
                if op.name == "MultiPV":
                    self.set_multipv(valor, op.maximo)

        return self._li_uci_options

    def li_uci_options(self):
        if self._li_uci_options is None:
            self.read_uci_options()
        return self._li_uci_options

    def assign_name(self):
        if self.id_name:
            li = self.id_name.split(" ")
            self.alias = li[0]
            self.version = li[-1] if len(li) > 0 else self.alias
            self.alias = self.alias
            self._name = self.id_name

    def li_uci_options_editable(self):
        return [op for op in self.li_uci_options() if op.tipo != "button"]

    def has_multipv(self):
        for op in self.li_uci_options_editable():
            if op.name == "MultiPV":
                return op.maximo > 3
        return False

    def current_multipv(self):
        for op in self.li_uci_options_editable():
            if op.name == "MultiPV":
                return int(op.valor)
        return self.multiPV

    def list_uci_changed(self):
        return self.liUCI

    def xhash(self):
        return hash(self.alias + self.alias)

    def list_to_show(self, wowner):
        li: list = [f'{_("Name")} = {self.name}', f'{_("Key")} = {self.alias}']
        if self.alias != self.alias:
            li.append(f'{_("Alias")} = {self.alias}')
        li.append(f'{self.path_exe}')
        dic_options = {uci.name: uci.valor for uci in self.li_uci_options() if uci.valor}
        if dic_options:
            li_opt = []
            for name, valor in dic_options.items():
                li_opt.append(f"{name} = {valor}")
            li.append((_("Options"), li_opt))
        if self.multiPV:
            li.append(f'{_("Number of variations evaluated by the engine (MultiPV)")} = {self.multiPV}')

        if self.max_depth or self.max_time or self.nodes:
            li_limits = []
            if self.max_depth:
                li_limits.append(f'{_("Fixed depth")} = {self.max_depth}')
            if self.max_time:
                li_limits.append(f'{_("Fixed time in seconds")} = {self.max_time:.01f}')
            if self.nodes:
                li_limits.append(f'{_("Fixed nodes")} = {self.nodes}')
            li.append((_("Limits of engine thinking"), li_limits))
        menu = QTDialogs.LCMenuRondo(wowner)
        for opt in li:
            menu.separador()
            if type(opt) is str:
                menu.opcion(None, opt)
            else:
                label, li_opt = opt
                submenu = menu.submenu(label)
                for op in li_opt:
                    submenu.separador()
                    submenu.opcion(None, op)
        menu.lanza()


class OpcionUCI:
    name = ""
    tipo = ""
    default = ""
    valor = ""
    minimo = 0
    maximo = 0
    li_vars = []

    def __str__(self):
        return "Name:%s - Type:%s - Default:%s - Value:%s - Min:%d - Max:%d - Vars:%s" % (
            self.name,
            self.tipo,
            self.default,
            self.valor,
            self.minimo,
            self.maximo,
            str(self.li_vars),
        )

    def lee(self, txt):
        while "  " in txt:
            txt = txt.replace("  ", " ")

        n = txt.find("type")
        if (n < 10) or ("chess960" in txt.lower()):
            return False

        self.name = txt[11:n].strip()

        if self.name.lower() == "ponder":
            return False

        li = txt[n:].split(" ")
        self.tipo = li[1]

        if self.tipo == "spin":
            resp = self.lee_spin(li)

        elif self.tipo == "check":
            resp = self.lee_check(li)

        elif self.tipo == "combo":
            resp = self.lee_combo(li)

        elif self.tipo == "string":
            resp = self.lee_string(li)

        elif self.tipo == "button":
            resp = True

        else:
            resp = False

        if resp:
            self.valor = self.default

        return resp

    def lee_spin(self, li):
        if len(li) >= 8:
            for x in [2, 4, 6]:
                n = li[x + 1]
                nm = n[1:] if n.startswith("-") else n
                if not nm.isdigit():
                    return False
                n = int(n)
                cl = li[x].lower()
                if cl == "default":
                    self.default = n
                elif cl == "min":
                    self.minimo = n
                elif cl == "max":
                    self.maximo = n
            return True
        else:
            return False

    def lee_check(self, li):
        if len(li) == 4 and li[2] == "default":
            self.default = li[3]
            return True
        else:
            return False

    def lee_string(self, li):
        # UCI protocol: option name <name> type string default <value>
        # value can contain spaces
        try:
            idx_default = li.index("default")
            if idx_default < len(li) - 1:
                self.default = " ".join(li[idx_default + 1:])
                if self.default == "<empty>":
                    self.default = ""
            else:
                self.default = ""
            return True
        except ValueError:
            return False

    def lee_combo(self, li):
        self.li_vars = []
        self.default = ""
        is_default = False
        nvar = -1
        for x in li[2:]:
            if x == "var":
                is_default = False
                nvar += 1
                self.li_vars.append("")
            elif x == "default":
                is_default = True
            else:
                if is_default:
                    if self.default:
                        self.default += " "
                    self.default += x
                else:
                    c = self.li_vars[nvar]
                    if c:
                        c += " " + x
                    else:
                        c = x
                    self.li_vars[nvar] = c

        return self.default and (self.default in self.li_vars)

    def restore_dic(self, dic):
        self.tipo = dic["tipo"]
        self.name = dic["name"]
        self.default = dic["default"]
        self.valor = dic["valor"]

        if self.tipo == "spin":
            self.minimo = dic["minimo"]
            self.maximo = dic["maximo"]

        elif self.tipo == "combo":
            self.li_vars = dic["li_vars"]

    def save_dic(self):
        dic = {
            "tipo": self.tipo,
            "name": self.name,
            "default": self.default,
            "valor": self.valor,
            "minimo": self.minimo,
            "maximo": self.maximo,
            "li_vars": self.li_vars,
        }
        return dic

    def label_default(self):
        if self.tipo == "spin":
            return "%d:%d-%d" % (self.default, self.minimo, self.maximo)

        elif self.tipo == "check":
            return str(self.default).lower()

        elif self.tipo == "button":
            return str(self.default).lower()

        elif self.tipo == "combo":
            return self.default
        return ""


def engine_from_txt(pk_txt):
    engine = Engine()
    engine.restore(pk_txt)
    return engine


def read_engine_uci(exe, args=None):
    path_exe = Util.relative_path(exe)
    if not os.path.isfile(path_exe):
        return None
    if not is_valid_engine(path_exe):
        return None
    if args is None:
        args = []
    engine = Engine(path_exe=path_exe, args=args)
    engine.read_uci_options()
    engine.assign_name()
    return engine


def _run_uci_command(path_exe) -> str | None:
    if not os.path.isfile(path_exe):
        return None

    process = QtCore.QProcess()
    process.setProgram(path_exe)
    process.setArguments([])
    process.setWorkingDirectory(os.path.dirname(path_exe))
    process.start()

    if not process.waitForStarted(2000):
        return None

    process.write(b"uci\n")

    buffer = ""
    ok = False
    for __ in range(30):
        if process.waitForReadyRead(100):
            chunk = process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
            buffer += chunk
            if "uciok" in buffer:
                ok = True
                break
        if process.state() == QtCore.QProcess.ProcessState.NotRunning:
            break

    process.kill()
    process.waitForFinished(200)
    return buffer if ok else None


def is_valid_engine(path_exe) -> bool:
    return _run_uci_command(path_exe) is not None


def get_uci_options(path_exe) -> list | None:
    buffer = _run_uci_command(path_exe)
    return buffer.splitlines() if buffer else None
