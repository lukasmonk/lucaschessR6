import base64
import collections
import datetime
import glob
import hashlib
import os
import pickle
import random
import shutil
import stat
import subprocess
import sys
import time
import urllib.request
import uuid
import zlib
from pathlib import Path
from shutil import which
from typing import Optional, Union, List, Tuple, Any

import psutil
from charset_normalizer import from_bytes


def md5_lc(x: str) -> int:
    return int.from_bytes(hashlib.md5(x.encode()).digest(), "big") & 0xFFFFFFFFFFFFFFF


class Log:
    def __init__(self, logname: Union[str, Path]):
        self.logname = Path(logname).absolute()

    def write(self, buf: str) -> None:
        if buf.startswith("Traceback"):
            import Code
            buf = f"{Code.VERSION}-{today()}\n{buf}"
        with self.logname.open("at", encoding="utf-8") as ferr:
            ferr.write(buf)

    def writeln(self, buf: str) -> None:
        self.write(f"{buf}\n")

    def flush(self) -> None:
        pass  # To remove error 120 at exit


def remove_file(file: Union[str, Path]) -> bool:
    try:
        Path(file).unlink(missing_ok=True)
    except Exception:
        pass
    return not Path(file).is_file()


def remove_folder_files(folder: Union[str, Path]) -> bool:
    folder_path = Path(folder)
    try:
        for entry in folder_path.iterdir():
            if entry.is_file():
                entry.unlink(missing_ok=True)
        folder_path.rmdir()
    except Exception:
        pass
    return not folder_path.is_dir()


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_windows() -> bool:
    return sys.platform == "win32"


def create_folder(folder: Union[str, Path]) -> bool:
    folder_path = Path(folder)
    try:
        folder_path.mkdir()
        if is_linux():
            folder_path.chmod(
                stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
            )
        return True
    except Exception:
        return False


def check_folders(folder: Union[str, Path]) -> bool:
    folder_path = Path(folder)
    if folder_path:
        if not folder_path.is_dir():
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                if is_linux():
                    folder_path.chmod(
                        stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
                    )
            except Exception:
                return False
    return True


def check_folders_filepath(filepath: Union[str, Path]) -> None:
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)


def same_path(path1: Union[str, Path], path2: Union[str, Path]) -> bool:
    return Path(path1).absolute() == Path(path2).absolute()


def norm_path(path: Union[str, Path]) -> Path:
    return Path(path).absolute()


def filesize(file: Union[str, Path]) -> int:
    try:
        return Path(file).stat().st_size
    except (FileNotFoundError, OSError):
        return -1


def exist_file(file: Union[str, Path]) -> bool:
    return Path(file).is_file() if file else False


def exist_folder(folder: Union[str, Path]) -> bool:
    return Path(folder).is_dir() if folder else False


def file_copy(origin: Union[str, Path], destino: Union[str, Path]) -> bool:
    origin_path = Path(origin)
    destino_path = Path(destino)
    if origin_path.is_file():
        destino_path.unlink(missing_ok=True)
        shutil.copy2(origin_path, destino_path)
        return True
    return False


def file_next(folder: Union[str, Path], base: str, ext: str) -> Path:
    folder_path = Path(folder)
    n = 1
    while True:
        path_file = folder_path / f"{base}{n}.{ext}"
        if not path_file.is_file():
            return path_file
        n += 1


def rename_file(origin: Union[str, Path], destination: Union[str, Path]) -> bool:
    origin_path = Path(origin).absolute()
    destination_path = Path(destination).absolute()

    if not origin_path.is_file():
        return False
    if origin_path == destination_path:
        return True

    # Handle case-insensitive filesystems
    if origin_path.name.lower() == destination_path.name.lower() and origin_path.parent == destination_path.parent:
        origin_path.rename(destination_path)
        return True

    destination_path.unlink(missing_ok=True)
    shutil.move(origin_path, destination_path)
    return True


def temporary_file(path_temp: Union[str, Path], ext: str) -> Path:
    temp_folder = Path(path_temp)
    temp_folder.mkdir(parents=True, exist_ok=True)
    while True:
        fich = temp_folder / f"{random.randint(1, sys.maxsize)}.{ext}"
        if not fich.is_file():
            return fich


def list_vars_values(obj: Any, li_exclude: Optional[List[str]] = None) -> List[Tuple[str, Any]]:
    if li_exclude is None:
        li_exclude = []

    li_vars = []

    inst_dict = obj.__dict__
    cls = obj.__class__

    for name, value in inst_dict.items():
        if name in li_exclude:
            continue

        # 1. Si el atributo existe también en la clase, podría ser descriptor/property
        cls_attr = cls.__dict__.get(name)

        # 2. Excluir properties, métodos, funciones y descriptores
        if isinstance(cls_attr, property):
            continue
        if callable(cls_attr):
            continue
        if hasattr(cls_attr, "__get__") or hasattr(cls_attr, "__set__") or hasattr(cls_attr, "__delete__"):
            continue

        # 3. VERIFICAR si el valor de la variable es pickleable
        try:
            # Intenta serializar el valor. Si falla, lanza PicklingError (o a veces TypeError)
            pickle.dumps(value, protocol=4)
            # Si tiene éxito, es una variable pura y pickleable
            li_vars.append((name, value))
        except (pickle.PicklingError, TypeError):
            # El objeto (e.g., un widget de PySide6) no es serializable. Lo excluímos.
            pass

    return li_vars


def restore_list_vars_values(obj: Any, li_vars_values: List[Tuple[str, Any]]) -> None:
    for name, value in li_vars_values:
        if hasattr(obj, name):
            setattr(obj, name, value)


def save_obj_pickle(obj: Any, li_exclude: Optional[List[str]] = None) -> bytes:
    li_vars_values = list_vars_values(obj, li_exclude)
    dic = {var: value for var, value in li_vars_values}
    return pickle.dumps(dic, protocol=4)


def restore_obj_pickle(obj: Any, js_txt: bytes) -> None:
    dic = pickle.loads(js_txt)
    for k, v in dic.items():
        if hasattr(obj, k):
            setattr(obj, k, v)


def ini_dic(file: Union[str, Path]) -> dict:
    dic = {}
    file_path = Path(file)
    if file_path.is_file():
        with file_path.open("rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    continue
                if line:
                    n = line.find("=")
                    if n:
                        key = line[:n].strip()
                        value = line[n + 1:].strip()
                        dic[key] = value
    return dic


def today() -> datetime.datetime:
    return datetime.datetime.now()


def huella() -> str:
    """
    Genera un identificador único basado en timestamp y UUID.

    Returns:
        str: Identificador único de 24 caracteres base64 sin padding.

    Nota:
        - Combina timestamp actual (8 bytes) + UUID v4 (16 bytes)
        - Proporciona alta unicidad incluso con llamadas concurrentes
        - El timestamp asegura ordenamiento cronológico parcial
        - UUID garantiza unicidad espacial/global
    """
    unique_part = uuid.uuid4().bytes
    time_part = int(time.time()).to_bytes(8, byteorder='big')
    combined = time_part + unique_part
    return base64.urlsafe_b64encode(combined).decode().replace("=", "")


def save_pickle(fich: Union[str, Path], obj: Any) -> bool:
    file_path = Path(fich)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("wb") as q:
        q.write(pickle.dumps(obj, protocol=4))
    return True


def restore_pickle(fich: Union[str, Path], default: Any = None) -> Any:
    file_path = Path(fich)
    if file_path.is_file():
        try:
            with file_path.open("rb") as f:
                return pickle.loads(f.read())
        except Exception:
            pass
    return default


def urlretrieve(url: str, fich: Union[str, Path]) -> bool:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            the_page = response.read()
            if the_page:
                file_path = Path(fich)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with file_path.open("wb") as q:
                    q.write(the_page)
                    return True
            return False
    except Exception:
        return False


def var2zip(var: Any) -> bytes:
    varp = pickle.dumps(var, protocol=4)
    return zlib.compress(varp, 5)


def zip2var(blob: Optional[bytes]) -> Any:
    if blob is None:
        return None
    try:
        varp = zlib.decompress(blob)
        return pickle.loads(varp)
    except Exception:
        return None


def zip2var_change_import(blob: Optional[bytes], li_replace: List[Tuple[str, str]]) -> Any:
    if blob is None:
        return None
    try:
        varp = zlib.decompress(blob)
    except:
        return None
    try:
        return pickle.loads(varp)
    except:
        try:
            for replace_from, replace_to in li_replace:
                varp = varp.replace(replace_from, replace_to)
            return pickle.loads(varp)
        except:
            return None


class Record:
    pass


def var2txt(var):
    return pickle.dumps(var, protocol=4)


def txt2var(txt):
    return pickle.loads(txt)


def dtos(f):
    return "%04d%02d%02d" % (f.year, f.month, f.day)


def stod(txt):
    if txt and len(txt) == 8 and txt.isdigit():
        return datetime.date(int(txt[:4]), int(txt[4:6]), int(txt[6:]))
    return None


def dtosext(f):
    return "%04d%02d%02d%02d%02d%02d" % (
        f.year,
        f.month,
        f.day,
        f.hour,
        f.minute,
        f.second,
    )


def dtostr_hm(f):
    return "%04d.%02d.%02d %02d:%02d" % (f.year, f.month, f.day, f.hour, f.minute)


def stodext(txt):
    if txt and len(txt) == 14 and txt.isdigit():
        return datetime.datetime(
            int(txt[:4]),
            int(txt[4:6]),
            int(txt[6:8]),
            int(txt[8:10]),
            int(txt[10:12]),
            int(txt[12:]),
        )
    return None


def primera_mayuscula(txt):
    return txt[0].upper() + txt[1:].lower() if len(txt) > 0 else ""


def primeras_mayusculas(txt):
    return " ".join([primera_mayuscula(x) for x in txt.split(" ")])


def ini2dic(file):
    dic_base = collections.OrderedDict()

    if os.path.isfile(file):

        with open(file, "rt", encoding="utf-8", errors="ignore") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#"):
                    if linea.startswith("["):
                        key = linea[1:-1]
                        dic = collections.OrderedDict()
                        dic_base[key] = dic
                    else:
                        n = linea.find("=")
                        if n > 0:
                            clave1 = linea[:n].strip()
                            valor = linea[n + 1:].strip()
                            dic[clave1] = valor

    return dic_base


def dic2ini(file, dic):
    with open(file, "wt", encoding="utf-8", errors="ignore") as f:
        for k in dic:
            f.write(f"[{k}]\n")
            for key in dic[k]:
                f.write(f"{key}={dic[k][key]}\n")


def ini_base2dic(file, rfind_equal=False):
    dic = {}

    if os.path.isfile(file):

        with open(file, "rt", encoding="utf-8", errors="ignore") as f:
            for linea in f:
                linea = linea.strip()
                if linea.startswith("#"):
                    continue
                if linea:
                    n = linea.rfind("=") if rfind_equal else linea.find("=")
                    if n:
                        key = linea[:n].strip()
                        valor = linea[n + 1:].strip()
                        dic[key] = valor

    return dic


def dic2ini_base(file, dic):
    with open(file, "wt", encoding="utf-8", errors="ignore") as f:
        for k, v in dic.items():
            f.write(f"{k}={v}\n")


def secs2str(s):
    m = s // 60
    s = s % 60
    h = m // 60
    m = m % 60
    return "%02d:%02d:%02d" % (h, m, s)


class ListaNumerosImpresion:
    def __init__(self, txt):
        # Formas
        # 1. <num>            1, <num>, 0
        #   2. <num>-           2, <num>, 0
        #   3. <num>-<num>      3, <num>,<num>
        #   4. -<num>           4, <num>, 0
        self.lista = []
        if txt:
            txt = txt.replace("--", "-").replace(",,", ",").replace(" ", "")

            for bloque in txt.split(","):

                if bloque.startswith("-"):
                    num = bloque[1:]
                    if num.isdigit():
                        self.lista.append((4, int(num)))

                elif bloque.endswith("-"):
                    num = bloque[:-1]
                    if num.isdigit():
                        self.lista.append((2, int(num)))

                elif "-" in bloque:
                    li = bloque.split("-")
                    if len(li) == 2:
                        num1, num2 = li
                        if num1.isdigit() and num2.isdigit():
                            i1 = int(num1)
                            i2 = int(num2)
                            if i1 <= i2:
                                self.lista.append((3, i1, i2))

                elif bloque.isdigit():
                    self.lista.append((1, int(bloque)))

    def if_in_list(self, pos):
        if not self.lista:
            return True

        for patron in self.lista:
            modo = patron[0]
            i1 = patron[1]
            if modo == 1:
                if pos == i1:
                    return True
            elif modo == 2:
                if pos >= i1:
                    return True
            elif modo == 3:
                i2 = patron[2]
                if i1 <= pos <= i2:
                    return True
            elif modo == 4:
                if pos <= i1:
                    return True

        return False

    def selected(self, lista):
        return [x for x in lista if self.if_in_list(x)]


class SymbolDict:
    def __init__(self, dic=None):
        self._dic = {}
        self._keys = []
        if dic:
            for k, v in dic.items():
                self.__setitem__(k, v)

    def __contains__(self, key):
        return key.upper() in self._dic

    def __len__(self):
        return len(self._keys)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._keys[key]
        return self._dic[key.upper()]

    def __setitem__(self, key, valor):
        clu = key.upper()
        if clu not in self._dic:
            self._keys.append(key)
        self._dic[clu] = valor

    def get(self, key, default=None):
        clu = key.upper()
        if clu not in self._dic:
            return default
        return self.__getitem__(key)

    def items(self):
        for k in self._keys:
            yield k, self.__getitem__(k)

    def keys(self):
        return self._keys[:]

    def __str__(self):
        x = ""
        for t in self._keys:
            x += f"[{t}]=[{self.__getitem__(t)!s}]\n"
        return x.strip()


class Rondo:
    def __init__(self, *lista):
        self.pos = -1
        self.lista = lista
        self.tope = len(self.lista)

    def shuffle(self):
        li = list(self.lista)
        random.shuffle(li)
        self.lista = li

    def otro(self):
        self.pos += 1
        if self.pos == self.tope:
            self.pos = 0
        return self.lista[self.pos]

    def reset(self):
        self.pos = -1


def valid_filename(name):
    name = name.strip()
    nom = []
    for x in name:
        if x in '\\:/|?*^%><(),;"' or ord(x) < 32:
            x = "_"
        nom.append(x)
    name = "".join(nom)
    li_invalid = [
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ]
    if name.upper() in li_invalid:
        name = f"__{name}__"
    if "." in name:
        if name[: name.find(".")].upper() in li_invalid:
            name = f"__{name}__"
    return name


def datefile(pathfile):
    try:
        mtime = os.path.getmtime(pathfile)
        return datetime.datetime.fromtimestamp(mtime)
    except:
        return None


def fide_elo(elo_jugador, elo_rival, resultado):
    if resultado == +1:
        resultado = 1.0
    elif resultado == 0:
        resultado = 0.5
    else:
        resultado = 0.0
    if elo_jugador <= 1200:
        k = 40.0
    elif elo_jugador <= 2100:
        k = 32.0
    elif elo_rival < 2400:
        k = 24.0
    else:
        k = 16.0
    probabilidad = 1.0 / (1.0 + (10.0 ** ((elo_rival - elo_jugador) / 400.0)))
    return int(k * (resultado - probabilidad))


date_format = ["%Y.%m.%d"]


def local_date(date):
    return date.strftime(date_format[0])


def local_date_time(date):
    return "%s %02d:%02d" % (date.strftime(date_format[0]), date.hour, date.minute)


def listfiles(*lista):
    f = lista[0]
    if len(lista) > 1:
        for x in lista[1:]:
            f = opj(f, x)
    return glob.glob(f)


def listdir(txt):
    return os.scandir(txt)


class OpenCodec:
    def __init__(self, path, modo=None):
        with open(path, "rb") as f:
            results = from_bytes(f.read(1024))
            best_guess = results.best()
            if best_guess is not None:
                encoding = best_guess.encoding
            else:
                encoding = 'utf-8'
        if modo is None:
            modo = "rt"
        self.f = open(path, modo, encoding=encoding, errors="ignore")

    def __enter__(self):
        return self.f

    def __exit__(self, xtype, value, traceback):
        self.f.close()


def bytes_encoding(btxt: bytes) -> str:
    results = from_bytes(btxt)
    best_guess = results.best()
    if best_guess is not None:
        encoding = best_guess.encoding
    else:
        encoding = 'utf-8'
    return encoding


def bytes_str_codec(btxt: bytes) -> tuple:
    codec = bytes_encoding(btxt)
    return btxt.decode(codec), codec


def file_encoding(fich, chunk=30000):
    with open(fich, "rb") as f:
        bt = f.read(chunk)
        if 195 in bt:
            return "utf-8"
        encoding = bytes_encoding(bt)
        if encoding == "ascii":
            encoding = "latin-1"
        return encoding


class Decode:
    def __init__(self, codec=None):
        self.codec = "utf-8" if codec is None else codec

    def read_file(self, file):
        self.codec = file_encoding(file)

    def decode(self, xbytes):
        try:
            resp = xbytes.decode(self.codec, "ignore")
        except:
            codec = bytes_encoding(xbytes)
            resp = xbytes.decode(codec, "ignore")
        return resp


def path_split(path):
    path = os.path.realpath(path)
    return path.split(os.sep)


def relative_path(*args):
    n_args = len(args)
    if n_args == 1:
        path = args[0]
    else:
        path = opj(args[0], args[1])
        if n_args > 2:
            for x in range(2, n_args):
                path = opj(path, args[x])
    try:
        path = os.path.abspath(path)
        rel = os.path.relpath(path)
        if not rel.startswith(".."):
            path = rel
    except ValueError:
        pass

    return path


def filename_unique(destination: str):
    if os.path.isfile(destination):
        n = destination.rfind(".")
        if n == -1:
            ext = ""
        else:
            ext = destination[n:]
            destination = destination[:n]
        n = 1
        if destination.endswith("-1"):
            destination = destination[:-2]
            n = 2
        while True:
            fich = destination + "-%d%s" % (n, ext)
            n += 1
            if not os.path.isfile(fich):
                return fich
    return destination


def memory_python():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss


def unique_list(lista):
    st = set()
    li = []
    for x in lista:
        if x not in st:
            li.append(x)
            st.add(x)
    return li


def div_list(xlist, max_group):
    nlist = len(xlist)
    xfrom = 0
    li_groups = []
    while xfrom < nlist:
        li_groups.append(xlist[xfrom: xfrom + max_group])
        xfrom += max_group
    return li_groups


def cpu_count():
    return psutil.cpu_count()


def opj(*elem) -> str:
    p = Path(*elem)
    return str(p)


def fen_fen64(fen):
    fen = fen.split(" ")[0]
    li = []
    for line in fen.split("/"):
        ln = []
        for c in line:
            if c.isdigit():
                ln.append(" " * int(c))
            else:
                ln.append(c)
        li.append("".join(ln))
    return "".join(li)


def randomize():
    random.seed(int.from_bytes(os.urandom(4), 'little'))


def file_crc(ruta_archivo):
    crc = 0
    with open(ruta_archivo, 'rb') as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            crc = zlib.crc32(chunk, crc)
    return crc & 0xFFFFFFFF


def startfile(path: Union[str, Path]) -> bool:
    try:
        path_obj = Path(path).absolute()
        if is_windows():
            os.startfile(str(path_obj))
        else:  # Linux
            opener = None

            if path_obj.is_dir():
                desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
                if "kde" in desktop and which("dolphin"):
                    opener = "dolphin"
                elif "gnome" in desktop and which("nautilus"):
                    opener = "nautilus"
                elif which("xdg-open"):
                    opener = "xdg-open"
            elif which("xdg-open"):
                opener = "xdg-open"

            if not opener:
                return False

            env = os.environ.copy()
            env.pop("LD_LIBRARY_PATH", None)
            env['DISPLAY'] = os.getenv('DISPLAY', ':0')
            env['DBUS_SESSION_BUS_ADDRESS'] = os.getenv(
                'DBUS_SESSION_BUS_ADDRESS', f'unix:path=/run/user/{os.getuid()}/bus'
            )
            env['HOME'] = os.getenv('HOME', str(Path.home()))

            subprocess.Popen(
                [opener, str(path_obj)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return True
    except Exception:
        return False


def clamp(n: Union[int, float], smallest: Union[int, float], largest: Union[int, float]) -> Union[int, float]:
    return max(smallest, min(n, largest))


def close_app():
    os._exit(0)