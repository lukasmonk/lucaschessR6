import datetime
import random
from typing import Any

from PySide6 import QtCore

import Code
import Code.SQL.Base as SQLBase
from Code.QT import QTMessages
from Code.SQL import UtilSQL
from Code.STS import STS
from Code.Translations import TrListas
from Code.Z import Util
from Code.Maps import Countries


class DBWorkMap(SQLBase.DBBase):
    list_raws: list[dict]

    def __init__(self, fichdb):
        self.trDic = {
            "mate": _("Mate"),
            "sts": _("STS"),
            "basic": _("Basic"),
            "easy": _("Easy"),
            "medium": _("Medium"),
            "hard": _("Hard"),
        }

        SQLBase.DBBase.__init__(self, fichdb)

        self.dicDB = UtilSQL.DictSQL(fichdb, tabla="CONFIG")
        self.tabla = "WORK"

        self.test_table()

        self.releer()

    def test_table(self):
        if not self.existeTabla(self.tabla):
            cursor = self.conexion.cursor()
            cursor.execute(
                "CREATE TABLE %s( ACTIVE INT, DCREATION TEXT, DEND TEXT, DONE TEXT, "
                "TIPO TEXT, MODEL TEXT, INFO TEXT, DATA BLOB);" % self.tabla
            )
            self.conexion.commit()
            cursor.close()

    def num_rows(self):
        return len(self.list_raws)

    def dato(self, row, key):
        return self.list_raws[row][key]

    def releer(self):
        cursor = self.conexion.cursor()
        cursor.execute(
            "SELECT ROWID, ACTIVE, DCREATION, DEND, DONE, TIPO, MODEL, INFO FROM %s ORDER BY -DCREATION;" % self.tabla
        )
        lista = cursor.fetchall()
        cursor.close()
        li = []
        for ROWID, ACTIVE, DCREATION, DEND, DONE, TIPO, MODEL, INFO in lista:
            d = {
                "ROWID": ROWID,
                "ACTIVE": "X" if ACTIVE else "",
                "DCREATION": DCREATION[: DCREATION.rindex(":")],
                "DEND": DEND[: DEND.rindex(":")] if DEND else "",
                "DONE": DONE,
                "TYPE": f"{self.trDic[TIPO]} - {self.trDic.get(MODEL, MODEL)}",
                "XTIPO": TIPO,
                "RESULT": INFO if INFO else "",
            }
            li.append(d)
        self.list_raws = li

    def data_activo(self):
        cursor = self.conexion.cursor()
        cursor.execute(
            f"SELECT ROWID, DCREATION, DEND, DONE, TIPO, MODEL, INFO, DATA FROM {self.tabla} WHERE ACTIVE=1;"
        )
        raw = cursor.fetchone()
        cursor.close()
        return raw

    def activa_rowid(self, row):
        rowid = self.list_raws[row]["ROWID"]
        cursor = self.conexion.cursor()
        cursor.execute(f"UPDATE {self.tabla} SET ACTIVE=0")
        self.conexion.commit()
        cursor.close()
        cursor = self.conexion.cursor()
        cursor.execute(f"UPDATE {self.tabla} SET ACTIVE=1 WHERE ROWID=?", (rowid,))
        self.conexion.commit()
        cursor.close()
        self.releer()

    def nuevo(self, w):
        cursor = self.conexion.cursor()
        cursor.execute(f"UPDATE {self.tabla} SET ACTIVE=0")
        self.conexion.commit()
        cursor.close()
        cursor = self.conexion.cursor()
        cursor.execute(
            f"INSERT INTO {self.tabla} (ACTIVE, DCREATION, DEND, DONE, TIPO, MODEL, DATA) VALUES(?,?,?,?,?,?,?);",
            (1, str(w.dcreation), "", w.done, w.tipo, w.model, w.save()),
        )
        self.conexion.commit()
        cursor.close()
        self.releer()

    def borra(self, rowid):
        cursor = self.conexion.cursor()
        cursor.execute(f"DELETE FROM {self.tabla} WHERE ROWID=?;", (rowid,))
        self.conexion.commit()
        cursor.close()
        self.releer()

    def save_work(self, workmap):
        rowid = [d["ROWID"] for d in self.list_raws if d["ACTIVE"]][0]

        dend = workmap.end_date()
        done = "%d/%d" % workmap.get_done()
        info = workmap.get_info()
        data = workmap.save()

        cursor = self.conexion.cursor()
        cursor.execute(
            f"UPDATE {self.tabla} SET DEND=?, DONE=?, INFO=?, DATA=? WHERE ROWID=?;",
            (dend, done, info, data, rowid),
        )
        self.conexion.commit()
        cursor.close()
        self.releer()

    def get_tipo(self):
        for d in self.list_raws:
            if d["ACTIVE"] == "X":
                return d["TYPE"]
        return ""


class WorkMap:
    ln_done: tuple
    ln_current: tuple
    ln_border: tuple
    ln_borderdone: tuple
    listaGrid: list
    widget: Any

    def __init__(self, mapa):
        self.mapa = mapa

        self.svg, self.lineasSVG = self.lee_svg()

        self.db = DBWorkMap(f"{Code.configuration.paths.folder_results()}/{mapa}.db")

        self.current = None
        self.aim = None

        self.tipo = None
        self.model = None
        self.rowid = None
        self.dcreation = None
        self.dend = None
        self.info = None
        self.done = None

        self.dic, self.dic_names = Countries.ld_countries(mapa)

        self.data_activo()

    def name_map(self):
        dic = TrListas.maps()
        return dic[self.mapa]

    def data_activo(self):
        raw = self.db.data_activo()
        if raw:
            (
                self.rowid,
                self.dcreation,
                self.dend,
                self.done,
                self.tipo,
                self.model,
                self.info,
                data,
            ) = raw
            self.restore(data)
            self.reset_list_grid()
        else:
            self.nuevo()
            self.data_activo()
            return

    def nuevo(self, tipo="mate", model="basic"):
        self.tipo = tipo
        self.model = model
        self.current = None

        if tipo == "sts":
            random.seed(model)
            self.gen_sts()
        else:
            self.gen_mate()
        self.dcreation = datetime.datetime.now()
        self.dend = ""
        self.info = ""
        self.done = "%d/%d" % self.get_done()
        self.db.nuevo(self)

    def lee_svg(self):
        svg = Code.path_resource("IntFiles", "Maps", f"{self.mapa}.svg")
        f = open(svg)
        lineas_svg = []
        for nlinea, linea in enumerate(f):
            linea = linea.strip()
            if linea.startswith("."):
                if linea == ".DONE":
                    self.ln_done = nlinea, linea
                elif linea == ".CURRENT":
                    self.ln_current = nlinea, linea
                elif linea == ".BORDER":
                    self.ln_border = nlinea, linea
                elif linea == ".BORDERDONE":
                    self.ln_borderdone = nlinea, linea
            lineas_svg.append(linea)
        f.close()
        return svg, lineas_svg

    def save(self):
        dic_w = {"CURRENT": self.current, "DIC": {iso: reg.save() for iso, reg in self.dic.items()}}
        return Util.var2zip(dic_w)

    def restore(self, xbin):
        dic_w = Util.zip2var(xbin)
        self.current = dic_w["CURRENT"]
        d = {}
        for iso, v in dic_w["DIC"].items():
            reg = Countries.RegWorkMap()
            reg.restore(v)
            d[iso] = reg
        self.dic = d

        self.reset_list_grid()

    def reset_list_grid(self):
        if self.current:
            li = [self.dic[iso] for iso in self.dic[self.current].border if iso in self.dic]
        else:
            li = [v for k, v in self.dic.items()]
        for alm in li:
            alm.name = self.dic[alm.iso].name
        self.listaGrid = sorted(li, key=lambda almt: almt.name)

    def set_widget(self, widget):
        self.widget = widget

    def reset_widget(self, focused_iso=None):
        lidone = []
        alm: Countries.RegWorkMap
        for iso, alm in self.dic.items():
            if alm.donePV:
                lidone.append(iso)
        if self.current:
            reg = self.dic[self.current]
            licurrent = [self.current]
            liborder = reg.border
            liborderdone = [iso for iso in liborder if iso in self.dic and self.dic[iso].donePV.strip()]
        else:
            licurrent = []
            liborder = []
            liborderdone = []

        lifocused = []
        if focused_iso:
            lifocused.append(focused_iso)

        def modif(rx, lista):
            # First expand associations
            expanded = set(lista)
            for _iso in lista:
                if _iso in self.dic:
                    for assoc_iso in self.dic[_iso].assoc:
                        expanded.add(assoc_iso)

            # Remove focused items to avoid CSS conflicts
            if focused_iso:
                to_remove = {focused_iso}
                if focused_iso in self.dic:
                    to_remove.update(self.dic[focused_iso].assoc)
                expanded = expanded - to_remove

            line, default = rx
            self.lineasSVG[line] = f".{',.'.join(expanded)}" if expanded else default

        modif(self.ln_done, lidone)
        modif(self.ln_current, licurrent)
        modif(self.ln_border, liborder)
        modif(self.ln_borderdone, liborderdone)
        x = "\n".join(self.lineasSVG)

        if lifocused:
            li_foc = []
            for xiso in lifocused:
                li_foc.append(xiso)
                if xiso in self.dic:
                    li_foc.extend(self.dic[xiso].assoc)
            selector = f".{',.'.join(li_foc)}"
            style_focused = f"\n{selector}\n{{\n fill: #32CD32;\n}}\n"
            x = x.replace("</style>", style_focused + "</style>")

        self.widget.load(QtCore.QByteArray(bytes(x, "utf-8")))

        if focused_iso is None:
            self.reset_list_grid()

    def num_rows(self):
        return len(self.listaGrid)

    def dato(self, row, column):
        if column == "TYPE":
            return "✅" if self.listaGrid[row].donePV else "🞅"
        else:
            return self.dic_names[self.listaGrid[row].iso]

    def set_aim_row(self, row):
        self.aim = self.listaGrid[row].iso
        si_hecho = self.iso_done(self.aim)
        if si_hecho:
            self.current = self.aim
        self.db.save_work(self)
        return si_hecho

    def get_aim(self):
        return self.dic[self.aim] if self.aim else None

    def iso_done(self, iso):
        return len(self.dic[iso].donePV) > 0

    def fen_aim(self):
        return self.dic[self.aim].fen

    def name_aim(self):
        return self.dic[self.aim].name

    def win_aim(self, window, pv):
        reg = self.dic[self.aim]
        reg.donePV = pv
        self.current = self.aim
        si_end = False
        if not self.dend:
            si_end = True
            for iso, reg in self.dic.items():
                if not reg.donePV:
                    si_end = False
                    break
            if si_end:
                self.dend = datetime.datetime.now()
        self.info = self.calc_info()
        self.db.save_work(self)
        if si_end:
            mensaje = f"{_('Congratulations, goal achieved')}<br><br>{_('Finished')}: {self.name_map()}"
            QTMessages.message_result_win(window, mensaje)
        return si_end

    def calc_info(self):
        info = ""
        if self.tipo == "sts":
            sump = sumt = 0
            for iso, alm in self.dic.items():
                if alm.donePV:
                    sump += alm.puntos
                    sumt += alm.total
            porc = sump * 100.0 / sumt if sumt else 0.0
            info = "%d/%d (%0.02f%%)" % (sump, sumt, porc)
        elif self.tipo == "mate":
            sum_m = sum_u = 0
            for iso, alm in self.dic.items():
                if alm.donePV:
                    sum_u += len(alm.donePV.split(" ")) // 2 + 1
                    sum_m += alm.mate
            porc = sum_m * 100.0 / sum_u if sum_u else 0.0
            info = "%d/%d (%0.02f%%)" % (sum_u, sum_m, porc)
        return info

    def name_current(self):
        return self.dic[self.current].name if self.current else ""

    def total(self):
        return len(self.dic)

    def get_done(self):
        h = 0
        t = 0
        for k, v in self.dic.items():
            if v.donePV:
                h += 1
            t += 1
        return h, t

    def is_terminated(self):
        h, t = self.get_done()
        return h == t

    def get_info(self):
        return self.info

    def get_tipo(self):
        return self.tipo

    def creation_date(self):
        c = str(self.dcreation)
        return c[: c.rindex(":")]

    def end_date(self):
        return str(self.dend) if self.dend else ""

    def activa_rowid(self, row):
        self.db.activa_rowid(row)
        self.data_activo()

    def gen_sts(self):
        groups = STS.Groups()

        st = set()
        ngroup = 0
        ngroups = len(groups)
        li_groups = groups.lista
        random.shuffle(li_groups)
        for iso, alm in self.dic.items():
            g = li_groups[ngroup]
            pos = random.randint(0, 99)
            while (ngroup, pos) in st:
                pos = random.randint(0, 99)
            st.add((ngroup, pos))

            elem = g.element(pos)
            alm.fen = elem.fen
            alm.dicResults = elem.dic_results
            alm.donePV = ""
            alm.strGroup = g.name

            ngroup += 1
            if ngroup == ngroups:
                ngroup = 0

    def gen_mate(self):
        dic_mates = {}
        for mate in range(1, 8):
            fich = Code.path_resource("Trainings", "Checkmates in GM games", "Mate in %d.fns" % mate)
            with open(fich) as f:
                li = []
                for linea in f:
                    linea = linea.strip()
                    if linea:
                        li1 = linea.split("|")
                        fen = li1[0]
                        pgn = li1[3]
                        li1 = pgn.split("[")[:-1]
                        dic = {}
                        for x in li1:
                            if '"' in x:
                                r = x.split('"')[1].replace(".?", "").replace("?", "")
                                if r:
                                    k = x.split('"')[0].strip()
                                    dic[k] = r
                        g = dic.get
                        txt = f"<b>{g('White', '')}-{g('Black', '')}</b><br>"
                        txt += f"{g('Event', '')}/{g('Site', '')}/{g('Date', '')}".strip("/")
                        li.append(f"{fen}|{txt}")
            dic_mates[mate] = li
        if self.model == "basic":
            prob7 = {
                15: (70, 20, 10, 0, 0, 0, 0),
                16: (50, 30, 20, 0, 0, 0, 0),
                17: (30, 30, 20, 20, 0, 0, 0),
                18: (10, 20, 40, 20, 10, 0, 0),
                19: (0, 10, 40, 30, 10, 10, 0),
                20: (0, 10, 30, 30, 20, 10, 0),
                21: (0, 0, 10, 20, 30, 30, 10),
                22: (0, 0, 0, 20, 30, 30, 20),
                23: (0, 0, 0, 10, 20, 40, 30),
                24: (0, 0, 0, 10, 10, 40, 40),
                25: (0, 0, 0, 0, 10, 40, 50),
                26: (0, 0, 0, 0, 10, 30, 60),
                27: (0, 0, 0, 0, 0, 30, 70),
            }

            def level_elo(elo):
                elo //= 100
                lit = []
                for n, xt in enumerate(prob7[elo]):
                    if xt:
                        lit.extend([n + 1] * xt)
                return random.choice(lit)

            for iso, alm in self.dic.items():
                mate = level_elo(alm.elo)
                alm.fen = random.choice(dic_mates[mate])
                alm.donePV = ""
                alm.mate = mate
        else:
            d = {"easy": (1, 2), "medium": (2, 5), "hard": (4, 7)}
            from_sq, to_sq = d[self.model]
            st = set()
            for iso, alm in self.dic.items():
                mate = random.randint(from_sq, to_sq)
                li = dic_mates[mate]
                fen = random.choice(li)
                while fen in st:
                    fen = random.choice(li)
                alm.fen = fen
                alm.donePV = ""
                alm.mate = mate
                st.add(fen)
