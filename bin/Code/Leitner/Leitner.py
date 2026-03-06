import datetime
import math
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import Code
from Code import Util
from Code.SQL import UtilSQL


def round_prob(value: float) -> int:
    lower = math.floor(value)
    upper = math.ceil(value)
    if lower == upper:
        return max(lower, 1)
    probability = value - lower
    return max(upper if random.random() < probability else lower, 1)


def distribute_exponentially(n, minimo, factor_caida):
    total = 100

    if n <= 0:
        return []

    # 2. Cálculo de base: Reservamos el mínimo y calculamos pesos
    total_variable = total - (n * minimo)

    # Usamos una comprensión de lista para los pesos
    pesos = [math.exp(-factor_caida * i) for i in range(n)]
    suma_pesos = sum(pesos)

    # 3. Reparto inicial con redondeo hacia abajo (floor) a 2 decimales
    # Esto evita pasarnos del total antes del ajuste final
    reparto = []
    for p in pesos:
        proporcion = (p / suma_pesos) * total_variable
        # Usamos 2 decimales, pero truncando o redondeando con cuidado
        valor = round(proporcion + minimo, 2)
        reparto.append(valor)

    # 4. Ajuste de precisión quirúrgico
    diferencia = round(total - sum(reparto), 2)
    reparto[1] += diferencia  # se lo damos a la caja 1

    return reparto


@dataclass
class FNSFileTraining:
    path: str = ""
    num_fns: int = 0
    from_fns: int = 1
    to_fns: int = 0

    def save(self) -> dict:
        return {
            "path": self.path,
            "num_fns": self.num_fns,
            "from_fns": self.from_fns,
            "to_fns": self.to_fns,
        }

    def restore(self, dic):
        self.path = dic["path"]
        self.num_fns = dic["num_fns"]
        self.from_fns = dic["from_fns"]
        self.to_fns = dic["to_fns"]


@dataclass
class LeitnerReg:
    line: str = ""
    reg_id: str = ""
    in_box: int = 0
    last_session: int = 0
    right: int = 0
    wrong: int = 0
    date_win: Optional[datetime.datetime] = None

    def save(self):
        dic = {
            "line": self.line,
            "reg_id": self.reg_id,
            "in_box": self.in_box,
            "last_session": self.last_session,
            "right": self.right,
            "wrong": self.wrong,
            "date_win": self.date_win
        }
        return dic

    def restore(self, dic: dict):
        self.line = dic["line"]
        self.reg_id = dic["reg_id"]
        self.in_box = dic["in_box"]
        self.last_session = dic["last_session"]
        self.right = dic["right"]
        self.wrong = dic["wrong"]
        self.date_win = dic["date_win"]

    def zap(self):
        self.last_session = 0
        self.in_box = 0
        self.date_win = None
        self.right = 0
        self.wrong = 0


class Leitner:
    def __init__(self, elems_session: int = 30, min_elems_session: int = 10, num_boxes: int = 5):
        self.huella = Util.huella()
        self.reference = ""
        self.source_files: List[FNSFileTraining] = []
        self.elems_session = elems_session
        self.min_elems_session = min_elems_session
        self.random_order = True
        self.num_boxes = num_boxes
        self.win_box = num_boxes + 1
        self.current_num_session = 0
        self.dic_regs = {}
        self.current_ids_session = []
        self.init_date = None
        self.end_date = None
        # num_boxes + 1, box 0 = elementos a repartir
        self.percentages = [100] + distribute_exponentially(num_boxes, 7, 1.)

    def new_session(self) -> bool:
        if self.is_the_end():
            return False
        if self.init_date is None:
            self.init_date = datetime.datetime.now()

        self.current_num_session += 1
        self.current_ids_session = []

        def get(box: int, x_all_possible: bool):
            desde_num = len(self.current_ids_session)
            if x_all_possible:
                max_to_get = self.elems_session - desde_num
            else:
                max_to_get = round_prob(self.elems_session * self.percentages[box] / 100)
                max_to_get = min(max_to_get, self.elems_session - desde_num)
            if max_to_get <= 0:
                return

            x_reg: LeitnerReg
            for x_reg in self.dic_regs.values():
                if x_reg.in_box == box:
                    if (x_reg.last_session + box) <= self.current_num_session:
                        if x_reg.reg_id not in self.current_ids_session:
                            self.current_ids_session.append(x_reg.reg_id)
                        if (len(self.current_ids_session) - desde_num) == max_to_get:
                            return

        def pending():
            return self.elems_session - len(self.current_ids_session)

        # Boxes 1-5 are looked at first, so that there is preference in meeting deadlines.
        # First, look at those that correspond to the percentage.
        for all_possible in (False, True):
            for num_box in range(1, self.num_boxes + 1):
                get(num_box, all_possible)
                if not pending():
                    break
            if not pending():
                break

        # If positions are missing, look at those that have not been tried.
        if pending():
            get(0, True)

        # If the minimum is not reached, the winnings are used.
        if len(self.current_ids_session) < self.min_elems_session:
            reg: LeitnerReg
            li = [reg for reg in self.dic_regs.values() if reg.in_box == self.win_box]
            li.sort(key=lambda reg1: reg1.date_win)  # the oldest ones won first

            for reg in li:
                if reg.reg_id not in self.current_ids_session:
                    self.current_ids_session.append(reg.reg_id)
                if len(self.current_ids_session) == self.min_elems_session:
                    break

        # They are all awarded as chosen in this session.
        for reg_id in self.current_ids_session:
            xreg = self.dic_regs[reg_id]
            xreg.last_session = self.current_num_session

        if self.random_order:
            random.shuffle(self.current_ids_session)

        return True

    def check_session(self) -> bool:
        # Check the session and return if new session has been created
        if not self.is_the_end():
            if len(self.current_ids_session) == 0:
                self.new_session()
                return True
        return False

    def assign_result(self, reg_id: str, success: bool) -> int:
        # assigna a nueva caja
        reg: LeitnerReg = self.dic_regs[reg_id]
        if success:
            reg.right += 1
            if reg.in_box == 0:  # Those tried for the first time go to box 2.
                reg.in_box = 2
            elif reg.in_box != self.win_box:  # The fillings are already in the box.
                reg.in_box += 1  # Go up to the next box
                if reg.in_box == self.win_box:
                    reg.date_win = datetime.datetime.now()
        else:
            reg.wrong += 1
            if reg.in_box == self.win_box:
                reg.in_box = self.num_boxes  # if it is used for filling, at the end it goes to the last box
                reg.date_win = None
            else:
                reg.in_box = 1  # Errors to box 1 by default
        return reg.in_box

    def is_the_end(self) -> bool:
        if self.end_date is None:
            # The system ends when everyone is the win-box.
            for reg in self.dic_regs.values():
                if reg.in_box != self.win_box:
                    return False
            self.end_date = datetime.datetime.now()
        return True

    def new_reg(self, line):
        reg = LeitnerReg(line=line, reg_id=Util.huella())
        self.dic_regs[reg.reg_id] = reg

    def save(self):
        dic = {
            "elems_session": self.elems_session,
            "min_elems_session": self.min_elems_session,
            "random_order": self.random_order,
            "num_boxes": self.num_boxes,
            "current_num_session": self.current_num_session,
            "current_ids_session": self.current_ids_session,
            "init_date": self.init_date,
            "end_date": self.end_date,
            "percentages": self.percentages,
            "li_regs": [reg.save() for reg in self.dic_regs.values()],
            "li_source_files": [fns.save() for fns in self.source_files],
            "reference": self.reference,
        }
        return dic

    def restore(self, dic: dict):
        # Backward compatible defaults
        self.reference = dic.get("reference", "")
        self.source_files = dic.get("source_files", [])

        self.elems_session = dic.get("elems_session", 30)
        self.min_elems_session = dic.get("min_elems_session", 10)
        self.random_order = dic.get("random_order", True)
        self.num_boxes = dic.get("num_boxes", 5)
        self.win_box = self.num_boxes + 1
        self.current_num_session = dic.get("current_num_session", 0)
        self.current_ids_session = dic.get("current_ids_session", [])
        self.init_date = dic.get("init_date", datetime.datetime.now())
        self.end_date = dic.get("end_date", None)
        self.percentages = dic.get("percentages", [100] + distribute_exponentially(self.num_boxes, 7, 1.))
        li_regs = dic.get("li_regs", [])
        self.dic_regs = {}
        for dic_reg in li_regs:
            reg = LeitnerReg()
            reg.restore(dic_reg)
            self.dic_regs[reg.reg_id] = reg

        self.source_files = []
        li_source_files = dic["li_source_files"]
        for dic in li_source_files:
            fns = FNSFileTraining()
            fns.restore(dic)
            self.source_files.append(fns)

    def zap(self):
        self.current_num_session = 0
        self.current_ids_session = set()  # Usar set para evitar duplicados
        self.init_date = None
        self.end_date = None
        for reg in self.dic_regs.values():
            reg.zap()

    def clone(self):
        clon = Leitner()
        clon.restore(self.save())
        return clon

    def add_file(self, path_fns: str, num_fns):
        fns = FNSFileTraining(path_fns, num_fns, 1, num_fns)
        self.source_files.append(fns)

    def num_puzzles(self):
        return sum(fns.to_fns - fns.from_fns + 1 for fns in self.source_files)

    def add_puzzles(self):
        self.dic_regs = {}
        fns: FNSFileTraining
        for fns in self.source_files:
            with Util.OpenCodec(fns.path, "rt") as f:
                pos = 0
                for line in f:
                    line = line.strip()
                    if line.count("|") >= 2:
                        pos += 1
                        if fns.from_fns <= pos <= fns.to_fns:
                            self.new_reg(line)
        if self.random_order:
            items = list(self.dic_regs.items())
            random.shuffle(items)
            self.dic_regs = dict(items)

    def box_contents(self) -> list:
        # contents per box of total items
        li = [0] * (self.win_box + 1)
        for reg in self.dic_regs.values():
            li[reg.in_box] += 1
        return li

    def box_session(self) -> list:
        # list with the items per box that will be used in the active session
        li = [0] * (self.win_box + 1)
        for reg_id in self.current_ids_session:
            li[self.dic_regs[reg_id].in_box] += 1
        return li


class LeitnerDB(UtilSQL.ListSQL):
    def __init__(self):
        db_path = Code.configuration.paths.file_leitner()
        super().__init__(db_path, is_reversed=True)
        self.cache2 = {}

    def get_leitner(self, pos: int) -> Optional[Leitner]:
        if pos in self.cache2:
            return self.cache2[pos]
        dic = self.__getitem__(pos)
        if dic is None:
            return None
        leitner = Leitner()
        leitner.restore(dic)
        self.cache2[pos] = leitner
        return leitner

    def set_leitner(self, pos: int, leitner: Leitner):
        self.cache2[pos] = leitner
        self.__setitem__(pos, leitner.save())

    def add_leitner(self, leitner: Leitner):
        self.append(leitner.save(), with_cache=True)
        self.cache2 = {}

    def rem_leitner(self, pos: int):
        self.__delitem__(pos)
        self.cache2 = {}


class FnsAnalyzer:
    def __init__(self):
        self.root_paths = []

    def add_folder(self, path: str):
        self.root_paths.append(Path(path))

    @staticmethod
    def _check_file(file_path: Path) -> bool:
        """Verifica si el archivo es válido (concurrente)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.count('|') > 1:
                        return True
        except Exception:
            pass
        return False

    def _scan(self, directory: Path) -> list:
        """Escanea recursivamente."""
        content = []

        # Archivos en la carpeta actual
        for file in directory.glob("*.fns"):
            if self._check_file(file):
                content.append(file)

        # Subcarpetas
        for subdir in directory.iterdir():
            if subdir.is_dir():
                sub_content = self._scan(subdir)
                if sub_content:
                    content.append({subdir.name: sub_content})
        return content

    def get_dictionary(self) -> dict:
        """Lanza el escaneo de cada root-folder en hilos separados."""
        results = {}

        # Usamos un Pool de hilos para procesar las carpetas raíz en paralelo
        with ThreadPoolExecutor() as executor:
            # Mapeamos cada ruta a la función de escaneo
            future_to_path = {executor.submit(self._scan, p): p for p in self.root_paths if p.exists()}

            for future in future_to_path:
                path = future_to_path[future]
                tree = future.result()
                if tree:
                    results[path.name] = tree

        return results


# if __name__ == '__main__':
#     import time
#
#     t = time.time()
#     lt = Leitner(elems_session=20, min_elems_session=10, num_boxes=5)
#     for x in range(300):
#         lt.new_reg("line")
#     xdic_regs = lt.dic_regs
#
#     while not lt.is_the_end():
#         if not lt.new_session():
#             break  # No hay más cartas disponibles que cumplan el criterio
#
#         status = [0] * (lt.num_boxes + 2)
#         for rid in lt.current_ids_session:
#             status[xdic_regs[rid].in_box] += 1
#         print(f"Sesión {lt.current_num_session} | Cajas: {status} | {sum(status)}")
#         # Copia de la lista para iterar
#         session_ids = list(lt.current_ids_session)
#         for regid in session_ids:
#             # Simular éxito/fallo
#             xbox = lt.dic_regs[regid].in_box
#             if xbox < lt.win_box:
#                 lt.assign_result(regid, random.random() > 0.2)
#             else:
#                 lt.assign_result(regid, random.random() > 0.005)
#
#         # Monitorización
#         status = [0] * (lt.num_boxes + 2)
#         for r in xdic_regs.values():
#             status[r.in_box] += 1
#
#         print(f"Sesión {lt.current_num_session} | Cajas: {status}")
#
#     print(time.time() - t)
