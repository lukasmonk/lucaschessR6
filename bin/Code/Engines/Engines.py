import os
import os.path
import sqlite3
import subprocess
import threading

import Code
from Code.Base.Constantes import BOOK_BEST_MOVE, ENG_EXTERNAL, MULTIPV_BYDEFAULT, MULTIPV_MAXIMIZE
from Code.QT import QTDialogs
from Code.SQL import UtilSQL
from Code.Z import Util


class Engine:
    uci_options_sqlite = "uci_options.sqlite"

    def __init__(self, alias="", autor="", version="", url="", path_exe="", args=None):
        # self.key = key
        self.key = alias
        self._name = None
        self.autor = autor
        self.args = [] if args is None else args
        self.version = version
        self._li_changed_options = []
        self.multiPV = 0
        self.maxMultiPV = 0
        self.siDebug = False
        self.nomDebug = None
        self.parent_external = None
        self.url = url
        self.path_exe = Util.relative_path(path_exe) if path_exe else ""
        self.path_exe = Util.bug_path(self.path_exe)
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

    @property
    def li_changed_options(self):
        return self._li_changed_options

    @li_changed_options.setter
    def li_changed_options(self, li):
        self._li_changed_options = li

    def get_changed_options(self):
        self._clean_elo()
        return self._li_changed_options

    def _clean_elo(self):
        pos_limit = -1
        pos_elo = -1

        for pos, (name, value) in enumerate(self._li_changed_options):
            if name == "UCI_LimitStrength" and value == "true":
                pos_limit = pos
            elif name == "UCI_Elo":
                pos_elo = pos

        if pos_limit == -1 and pos_elo > -1:
            del self._li_changed_options[pos_elo]
        elif pos_elo == -1 and pos_limit > -1:
            for op in self.li_uci_options():
                if op.name == "UCI_Elo":
                    self._li_changed_options.append(("UCI_Elo", op.default))
                    break

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
            try:
                if conf_parent := Code.configuration.engines.dic_engines().get(self.parent_external):
                    self.path_exe = conf_parent.path_exe
                    self.path_exe = Util.bug_path(self.path_exe)
            except AttributeError:
                pass
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
            name = self.key
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
        self.nomDebug = f"{self.key}-{txt}"

    def reset_uci_options(self):
        li_uci_options = self.li_uci_options()
        for op in li_uci_options:
            op.valor = op.default
        self._li_changed_options = []

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
                    is_changed = valor != str(op.default).lower()
                elif op.tipo == "spin":
                    try:
                        valor = int(valor)
                    except AttributeError:
                        valor = int(op.default)
                    is_changed = valor != int(op.default)
                else:
                    valor = str(valor)
                    is_changed = valor != str(op.default)
                op.valor = valor
                break

        for pos, (xcomando, xvalor) in enumerate(self._li_changed_options):
            if xcomando == name:
                if is_changed:
                    self._li_changed_options[pos] = (name, valor)
                else:
                    del self._li_changed_options[pos]
                return
        if is_changed:
            self._li_changed_options.append((name, valor))

    def set_multipv(self, num, maximo):
        self.multiPV = int(num) if num else 1
        self.maxMultiPV = int(maximo) if maximo else 1

    def set_multipv_var(self, xmultipv: str | int):
        if xmultipv == MULTIPV_MAXIMIZE:
            self.multiPV = self.maxMultiPV
        elif xmultipv == MULTIPV_BYDEFAULT:
            multi_pv = min(self.maxMultiPV, 10)
            multi_pv = next(
                (int(valor) for comando, valor in self._li_changed_options if comando == "MultiPV"),
                max(multi_pv, self.multiPV),
            )
            self.multiPV = multi_pv

        else:
            self.multiPV = int(xmultipv)
            self.multiPV = min(self.multiPV, self.maxMultiPV)
        if self.multiPV < 1:
            self.multiPV = self.maxMultiPV

    def can_be_tutor_analyzer(self):
        return self.maxMultiPV >= 4 and not self.is_maia()

    def can_be_supertutor(self):
        return self.maxMultiPV >= 218 and not self.is_maia()

    def is_maia(self):
        return self.key.startswith("maia-")

    def level_maia(self):
        try:
            level = int(self.key[5:])
        except ValueError:
            level = 0
        return level

    def remove_log(self, fich):
        Util.remove_file(Util.opj(os.path.dirname(self.path_exe), fich))

    @property
    def name(self):
        if self._name:
            return self._name
        alias = Util.primera_mayuscula(self.key)
        if not alias.endswith(self.version):
            alias += f" {self.version}"
        return alias

    @name.setter
    def name(self, value):
        self._name = value

    def ejecutable(self):
        self.path_exe = Util.bug_path(self.path_exe)
        return self.path_exe

    def remove_uci_options(self):
        if self.type == ENG_EXTERNAL:
            path_uci_options = os.path.join(Code.configuration.paths.folder_config(), self.uci_options_sqlite)
            with UtilSQL.DictTextSQL(path_uci_options) as dbuci:
                del dbuci[self.key_engine()]

    def key_engine(self):
        if self.type != ENG_EXTERNAL:
            return "maia" if self.key.startswith("maia-") else self.key
        stat = os.stat(self.path_exe)
        return f"{os.path.basename(self.path_exe)}_{stat.st_size}_{stat.st_mtime}"

    def read_uci_options(self):
        if self.type == ENG_EXTERNAL:
            path_uci_options = os.path.join(Code.configuration.paths.folder_config(), self.uci_options_sqlite)
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
                    try:
                        dbuci[key] = "\n".join(lines)
                    except sqlite3.IntegrityError:
                        pass

                else:
                    # Cache engines that do not answer over a pipe, otherwise they
                    # would be re-probed (subprocess) on every single startup.
                    try:
                        dbuci[key] = ""
                    except sqlite3.IntegrityError:
                        pass
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

        for comando, valor in self._li_changed_options:
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
            self.key = li[0]
            self.version = li[-1] if len(li) > 0 else self.key
            self.key = self.key
            self._name = self.id_name

    def li_uci_options_editable(self):
        return [op for op in self.li_uci_options() if op.tipo != "button"]

    def has_multipv(self):
        return next(
            (op.maximo > 3 for op in self.li_uci_options_editable() if op.name == "MultiPV"),
            False,
        )

    def current_multipv(self):
        return next(
            (int(op.valor) for op in self.li_uci_options_editable() if op.name == "MultiPV"),
            self.multiPV,
        )

    def xhash(self):
        return hash(self.key + self.key)

    def list_to_show(self, wowner):
        li: list = [f"{_('Name')} = {self.name}", f"{_('Key')} = {self.key}"]
        if self.key != self.key:
            li.append(f"{_('Alias')} = {self.key}")
        li.append(f"{self.path_exe}")
        if dic_options := {uci.name: uci.valor for uci in self.li_uci_options() if uci.valor}:
            li_opt = []
            li_opt.extend(f"{name} = {valor}" for name, valor in dic_options.items())
            li.append((_("Options"), li_opt))
        if self.multiPV:
            li.append(f"{_('Number of variations evaluated by the engine (MultiPV)')} = {self.multiPV}")

        if self.max_depth or self.max_time or self.nodes:
            li_limits = []
            if self.max_depth:
                li_limits.append(f"{_('Fixed depth')} = {self.max_depth}")
            if self.max_time:
                li_limits.append(f"{_('Fixed time in seconds')} = {self.max_time:.01f}")
            if self.nodes:
                li_limits.append(f"{_('Fixed nodes')} = {self.nodes}")
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

        # if self.name.lower() == "ponder":
        #     return False

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
                nm = n.removeprefix("-")
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
                        c += f" {x}"
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

        elif self.tipo == "check" or self.tipo == "button":
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


def _run_uci_command(path_exe: str) -> str | None:
    path_exe = os.path.abspath(path_exe)
    if not os.path.isfile(path_exe):
        return None

    size = Util.filesize(path_exe)
    timeout = max(10, size * 10 // 5000000)
    direxe = os.path.dirname(path_exe)

    if Util.is_windows():
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        env = None
    else:
        startupinfo = None
        ld_library = os.environ.get("LD_LIBRARY_PATH", "")
        parts = [p for p in ld_library.split(":") if p]
        parts.insert(0, os.path.abspath(direxe))
        lib_path = os.path.join(direxe, "lib")
        if os.path.isdir(lib_path):
            parts.insert(0, os.path.abspath(lib_path))

        env = {**os.environ, "LD_LIBRARY_PATH": ":".join(parts)}
        if "PATH" in env:
            env["PATH"] = f"{direxe}:{env['PATH']}"

    try:
        proc = subprocess.Popen(
            [path_exe],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=direxe,
            env=env,
            startupinfo=startupinfo,
            bufsize=1
        )

        uci_lines = []

        # Temporizador para forzar el cierre del proceso si supera el timeout
        timer = threading.Timer(timeout, proc.kill)
        timer.start()

        try:
            # 1. Enviar solo 'uci'
            proc.stdin.write("uci\n")
            proc.stdin.flush()

            # 2. Leer stdout hasta recibir 'uciok'
            while True:
                line = proc.stdout.readline()
                if not line:
                    break

                line = line.strip()
                if line == "uciok":
                    break
                if line.startswith(("id ", "option ")):
                    uci_lines.append(line)

            # 3. Decirle al motor que cierre amigablemente
            proc.stdin.write("quit\n")
            proc.stdin.flush()
            proc.communicate(timeout=2)

        finally:
            # Cancelar el temporizador si terminó a tiempo
            timer.cancel()
            if proc.poll() is None:
                proc.kill()

        return "\n".join(uci_lines) if uci_lines else None

    except (subprocess.SubprocessError, OSError):
        return None


def is_valid_engine(path_exe) -> bool:
    return _run_uci_command(path_exe) is not None


def get_uci_options(path_exe) -> list | None:
    buffer = _run_uci_command(path_exe)
    return buffer.splitlines() if buffer else None


def list_depths_to_cb() -> list[tuple[str, str]]:
    return [(_("By default"), "PD"), (_("Maximum"), "MX")] + [
        (str(x), str(x)) for x in list(range(1, 16)) + [20, 30, 40, 50, 75, 100, 150, 200]
    ]
