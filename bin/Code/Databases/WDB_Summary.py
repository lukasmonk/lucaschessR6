from typing import Any, List

from PySide6 import QtCore, QtWidgets

import Code
from Code.Base import Game
from Code.Databases import WDB_Analysis
from Code.Openings import OpeningsStd
from Code.QT import Colocacion, Columnas, Controles, Delegados, FormLayout, Grid, Iconos, QTDialogs, QTMessages


class WSummary(QtWidgets.QWidget):
    reccount: int
    allmoves: bool

    def __init__(self, procesador, wb_database, db_games, with_moves=True):
        QtWidgets.QWidget.__init__(self)

        self.wb_database = wb_database

        self.db_games = db_games  # <--set_db_games
        self.infoMove = None  # <-- set_info_move
        self.wmoves = None  # <-- setwmoves
        self.liMoves = []
        self.with_moves = with_moves
        self.procesador = procesador
        self.configuration = Code.configuration
        self.foreground = Code.dic_qcolors["SUMMARY_FOREGROUND"]

        self.wdb_analysis = WDB_Analysis.WDBAnalisis(self)

        self.read_config()

        self.aperturasStd = OpeningsStd.ap

        self.with_figurines = self.configuration.x_pgn_withfigurines

        self.pv_base = ""

        self.orden = ["games", False]

        self.lbName = (
            Controles.LB(self, "")
            .set_wrap()
            .align_center()
            .set_foreground_backgound("white", "#4E5A65")
            .set_font_type(puntos=10 if with_moves else 16)
        )
        if not with_moves:
            self.lbName.hide()

        # Grid
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("number", _("N."), 35, align_center=True)
        self.delegadoMove = Delegados.EtiquetaPGN(True if self.with_figurines else None)
        o_columns.nueva("move", _("Move"), 60, edicion=self.delegadoMove)
        o_columns.nueva("analysis", _("Analysis"), 60, align_right=True)
        o_columns.nueva("games", _("Games"), 70, align_right=True)
        o_columns.nueva("pgames", f"% {_('Games')}", 70, align_right=True)
        o_columns.nueva("win", _("Win"), 70, align_right=True)
        o_columns.nueva("draw", _("Draw"), 70, align_right=True)
        o_columns.nueva("lost", _("Loss"), 70, align_right=True)
        o_columns.nueva("pwin", f"% {_('Win')}", 60, align_right=True)
        o_columns.nueva("pdraw", f"% {_('Draw')}", 60, align_right=True)
        o_columns.nueva("plost", f"% {_('Loss')}", 60, align_right=True)
        o_columns.nueva("pdrawwin", f"% {_('W+D')}", 60, align_right=True)
        o_columns.nueva("pdrawlost", f"% {_('L+D')}", 60, align_right=True)

        self.grid = Grid.Grid(self, o_columns, xid="summary", complete_row_select=True)
        self.grid.set_height_row(self.configuration.x_pgn_rowheight)
        self.grid.font_type(puntos=self.configuration.x_pgn_fontpoints)

        # ToolBar
        self.tb = QTDialogs.LCTB(self, with_text=not self.with_moves)
        self.tb.new(_("Close"), Iconos.MainMenu(), wb_database.tw_terminar)
        self.tb.new(_("Basic position"), Iconos.Inicio(), self.start)
        self.tb.new(_("Previous"), Iconos.AnteriorF(), self.anterior, sep=False)
        self.tb.new(_("Next"), Iconos.SiguienteF(), self.siguiente)
        self.tb.new(_("Analyze"), Iconos.Analizar(), self.analizar)
        self.tb.new(_("Rebuild"), Iconos.Reindexar(), self.reindexar)
        self.tb.new(_("Config"), Iconos.Configurar(), self.config)
        if self.with_moves:
            self.tb.vertical()

        layout = Colocacion.V().control(self.lbName)
        if not self.with_moves:
            layout.control(self.tb)
        layout.control(self.grid)
        if self.with_moves:
            layout = Colocacion.H().control(self.tb).otro(layout)

        layout.margen(1)

        self.setLayout(layout)

    def close_db(self):
        if self.wdb_analysis:
            self.wdb_analysis.close()
            self.wdb_analysis = None

    def grid_doubleclick_header(self, _grid, obj_column):
        key = obj_column.key

        if key == "analysis":

            def func(dic):
                return dic["analysis"].centipawns_abs() if dic["analysis"] else -9999999

        elif key == "move":

            def func(dic):
                return dic["move"].upper()

        else:

            def func(dic):
                return dic[key]

        tot = self.liMoves[-1]
        li = sorted(self.liMoves[:-1], key=func)

        orden, mas = self.orden
        if orden == key:
            mas = not mas
        else:
            mas = key == "move"
        if not mas:
            li.reverse()
        self.orden = key, mas
        li.append(tot)
        self.liMoves = li
        self.grid.refresh()

    def set_db_games(self, db_games):
        self.db_games = db_games

    def focusInEvent(self, event):
        self.wb_database.ultFocus = self

    def set_info_move(self, info_move):
        self.infoMove = info_move

    def setwmoves(self, wmoves):
        self.wmoves = wmoves

    def grid_num_datos(self, _grid):
        return len(self.liMoves)

    def grid_tecla_control(self, _grid, k, _is_shift, _is_control, _is_alt):
        if k in (
            QtCore.Qt.Key.Key_Enter,
            QtCore.Qt.Key.Key_Return,
            QtCore.Qt.Key.Key_Right,
        ):
            self.siguiente()
        elif k == QtCore.Qt.Key.Key_Left:
            self.anterior()
        else:
            return True  # que siga con el resto de teclas
        return False

    def grid_dato(self, _grid, nfila, ocol):
        key = ocol.key

        # Last=Totals
        if self.is_row_with_totals(nfila):
            if key in ("number", "analysis", "pgames"):
                return ""
            elif key == "move":
                return _("Total")

        if self.liMoves[nfila]["games"] == 0 and key not in (
            "number",
            "analysis",
            "move",
        ):
            return ""
        v = self.liMoves[nfila][key]
        if key.startswith("p"):
            return f"{v:.01f} %"
        elif key == "analysis":
            return v.abbrev_text_base() if v else ""
        elif key == "number":
            if self.with_figurines:
                self.delegadoMove.setWhite("..." not in v)
            return v
        else:
            return str(v)

    def row_position(self, nrow):
        dic: dict = self.liMoves[nrow]
        li = [[k, dic[k]] for k in ("win", "draw", "lost")]
        li = sorted(li, key=lambda x: x[1], reverse=True)
        d = {}
        prev = 0
        ant = li[0][1]
        total = 0
        for cl, v in li:
            if v < ant:
                prev += 1
            d[cl] = prev
            ant = v
            total += v
        if total == 0:
            d["win"] = d["draw"] = d["lost"] = -1
        return d

    def grid_color_fondo(self, _grid, nfila, ocol):
        key = ocol.key
        if self.is_row_with_totals(nfila) and key not in ("number", "analysis"):
            return Code.dic_qcolors["SUMMARY_TOTAL"]
        if key in ("pwin", "pdraw", "plost"):
            dic = self.row_position(nfila)
            n = dic[key[1:]]
            if n == 0:
                return Code.dic_qcolors["SUMMARY_WIN"]
            if n == 2:
                return Code.dic_qcolors["SUMMARY_LOST"]
        return None

    def grid_color_texto(self, _grid, nfila, ocol):
        if self.foreground:
            key = ocol.key
            if self.is_row_with_totals(nfila) or key in ("pwin", "pdraw", "plost"):
                return self.foreground
        return None

    @staticmethod
    def pop_pv(pv):
        if pv:
            rb = pv.rfind(" ")
            if rb == -1:
                pv = ""
            else:
                pv = pv[:rb]
        return pv

    def analizar(self):
        self.wdb_analysis.menu(self.pv_base)
        self.update_pv(self.pv_base)

    def start(self):
        self.update_pv("")
        self.change_infomove()

    def anterior(self):
        if self.pv_base:
            pv = self.pop_pv(self.pv_base)

            self.update_pv(pv)
            self.change_infomove()

    def redo_current(self):
        recno = self.grid.recno()
        if recno >= 0:
            dic: dict = self.liMoves[recno]
            if "pv" in dic:
                pv = dic["pv"]
                if pv:
                    li = pv.split(" ")
                    pv = " ".join(li[:-1])
                self.update_pv(pv)
                self.change_infomove()

    def siguiente(self):
        recno = self.grid.recno()
        if recno >= 0:
            dic: dict = self.liMoves[recno]
            if "pv" in dic:
                pv = dic["pv"]
                if pv.count(" ") > 0:
                    pv = f"{self.pv_base} {dic['pvmove']}"
                self.update_pv(pv)
                self.change_infomove()

    def reindexar(self):
        return self.reindexar_question(self.db_games.depth_stat(), True)

    def reindexar_question(self, depth, question):
        if not self.db_games.has_result_field():
            QTMessages.message_error(self, _("This database does not have a RESULT field"))
            return None

        if question or self.wb_database.is_temporary:

            li_gen: List[tuple[Any, Any]] = [
                (None, None),
                (None, _("Select the number of half-moves <br> for each game to be considered")),
                (None, None),
            ]

            config = FormLayout.Spinbox(_("Depth"), 0, 999, 50)
            li_gen.append((config, self.db_games.depth_stat()))

            resultado = FormLayout.fedit(li_gen, title=_("Rebuild"), parent=self, icon=Iconos.Reindexar())
            if resultado is None:
                return None

            accion, li_resp = resultado

            depth = li_resp[0]

        self.reccount = 0

        bp_tmp = QTMessages.ProgressBarWithTime(self, _("Rebuilding"))
        bp_tmp.mostrar()

        def dispatch(recno, reccount):
            if reccount != self.reccount:
                self.reccount = reccount
                bp_tmp.set_total(reccount)
            bp_tmp.pon(recno)
            return not bp_tmp.is_canceled()

        self.db_games.rebuild_stat(dispatch, depth)
        bp_tmp.cerrar()
        self.start()

        return None

    def active_move(self):
        recno = self.grid.recno()
        if recno >= 0:
            return self.liMoves[recno]
        else:
            return None

    def is_row_with_totals(self, nfila):
        return nfila == len(self.liMoves) - 1

    def isnt_row_with_totals(self, nfila):
        return nfila < len(self.liMoves) - 1

    def grid_doble_click(self, _grid, fil, _col):
        if self.isnt_row_with_totals(fil):
            self.siguiente()

    def grid_update(self):
        nfila = self.grid.recno()
        if nfila > -1:
            self.grid_cambiado_registro(None, nfila, None)

    def actualiza(self):
        mov_actual = self.infoMove.movActual
        pv_base = self.pop_pv(mov_actual.allPV())
        self.update_pv(pv_base)
        if mov_actual:
            pv = mov_actual.allPV()
            for n in range(len(self.liMoves) - 1):
                if self.liMoves[n]["pv"] == pv:
                    self.grid.goto(n, 0)
                    return

    def update_pv(self, pv_base):
        self.pv_base = pv_base
        if not pv_base:
            pv_mirar = ""
        else:
            pv_mirar = self.pv_base

        dic_analisis = {}
        analysis_mrm = self.wdb_analysis.mrm(pv_mirar)
        if analysis_mrm:
            for rm in analysis_mrm.li_rm:
                dic_analisis[rm.movimiento()] = rm
        self.liMoves = self.db_games.get_summary(pv_mirar, dic_analisis, self.with_figurines, self.allmoves)

        self.grid.refresh()
        self.grid.gotop()

    def reset(self):
        self.update_pv(None)
        self.grid.refresh()
        self.grid.gotop()

    def grid_cambiado_registro(self, _grid, _row, _col):
        if self.grid.hasFocus() or self.hasFocus():
            self.change_infomove()

    def change_infomove(self):
        row = self.grid.recno()
        if row >= 0 and self.isnt_row_with_totals(row):
            pv = self.liMoves[row]["pv"]
            p = Game.Game()
            p.read_pv(pv)
            p.is_finished()
            p.assign_opening()
            self.infoMove.game_mode(p, 9999)
            self.setFocus()
            self.grid.setFocus()

    # def showActiveName(self, name):
    # Llamado de WBG_Games -> setNameToolbar
    # self.lbName.set_text(_("Opening explorer of %s") % name)

    def read_config(self):
        dic_config = self.configuration.read_variables("DBSUMMARY")
        if not dic_config:
            dic_config = {"allmoves": False}
        self.allmoves = dic_config["allmoves"]
        return dic_config

    # def grabaConfig(self):
    #     dic_config = {"allmoves": self.allmoves}
    #     self.configuration.write_variables("DBSUMMARY", dic_config)
    #     self.configuration.graba()

    def config(self):
        menu = QTDialogs.LCMenu(self)
        menu.opcion("allmoves", _("Show all moves"), is_checked=self.allmoves)
        resp = menu.lanza()
        if resp is None:
            return
        self.allmoves = not self.allmoves

        self.update_pv(self.pv_base)


class WSummaryBase(QtWidgets.QWidget):
    pv_base: str

    def __init__(self, procesador, db_stat):
        QtWidgets.QWidget.__init__(self)

        self.db_stat = db_stat
        self.liMoves = []
        self.procesador = procesador
        self.configuration = Code.configuration
        self.foreground = Code.dic_qcolors["SUMMARY_FOREGROUND"]

        self.with_figurines = self.configuration.x_pgn_withfigurines

        self.orden = ["games", False]

        # Grid
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("number", _("N."), 35, align_center=True)
        self.delegadoMove = Delegados.EtiquetaPGN(True if self.with_figurines else None)
        o_columns.nueva("move", _("Move"), 60, edicion=self.delegadoMove)
        o_columns.nueva("games", _("Games"), 70, align_right=True)
        o_columns.nueva("pgames", f"% {_('Games')}", 70, align_right=True, align_center=True)
        o_columns.nueva("win", _("Win"), 70, align_right=True)
        o_columns.nueva("draw", _("Draw"), 70, align_right=True)
        o_columns.nueva("lost", _("Loss"), 70, align_right=True)
        o_columns.nueva("pwin", f"% {_('Win')}", 60, align_right=True)
        o_columns.nueva("pdraw", f"% {_('Draw')}", 60, align_right=True)
        o_columns.nueva("plost", f"% {_('Loss')}", 60, align_right=True)
        o_columns.nueva("pdrawwin", f"% {_('W+D')}", 60, align_right=True)
        o_columns.nueva("pdrawlost", f"% {_('L+D')}", 60, align_right=True)

        self.grid = Grid.Grid(self, o_columns, xid="summarybase", complete_row_select=True)

        layout = Colocacion.V()
        layout.control(self.grid)
        layout.margen(1)

        self.setLayout(layout)

    def grid_doubleclick_header(self, _grid, obj_column):
        key = obj_column.key

        if key == "move":

            def func(dic):
                return dic["move"].upper()

        else:

            def func(dic):
                return dic[key]

        tot = self.liMoves[-1]
        li = sorted(self.liMoves[:-1], key=func)

        orden, mas = self.orden
        if orden == key:
            mas = not mas
        else:
            mas = key == "move"
        if not mas:
            li.reverse()
        self.orden = key, mas
        li.append(tot)
        self.liMoves = li
        self.grid.refresh()

    def grid_num_datos(self, _grid):
        return len(self.liMoves)

    def grid_dato(self, _grid, nfila, ocol):
        key = ocol.key

        # Last=Totals
        if self.is_row_with_totals(nfila):
            if key in ("number", "pgames"):
                return ""
            elif key == "move":
                return _("Total")

        if self.liMoves[nfila]["games"] == 0 and key not in ("number", "move"):
            return ""
        v = self.liMoves[nfila][key]
        if key.startswith("p"):
            return f"{v:.01f} %"
        elif key == "number":
            if self.with_figurines:
                self.delegadoMove.setWhite("..." not in v)
            return v
        else:
            return str(v)

    def row_position(self, nfila):
        dic: dict = self.liMoves[nfila]
        li = [[k, dic[k]] for k in ("win", "draw", "lost")]
        li = sorted(li, key=lambda x: x[1], reverse=True)
        d = {}
        prev = 0
        ant = li[0][1]
        total = 0
        for cl, v in li:
            if v < ant:
                prev += 1
            d[cl] = prev
            ant = v
            total += v
        if total == 0:
            d["win"] = d["draw"] = d["lost"] = -1
        return d

    def grid_color_fondo(self, _grid, nfila, ocol):
        key = ocol.key
        if self.is_row_with_totals(nfila) and key not in ("number", "analysis"):
            return Code.dic_qcolors["SUMMARY_TOTAL"]
        if key in ("pwin", "pdraw", "plost"):
            dic = self.row_position(nfila)
            n = dic[key[1:]]
            if n == 0:
                return Code.dic_qcolors["SUMMARY_WIN"]
            if n == 2:
                return Code.dic_qcolors["SUMMARY_LOST"]
        return None

    def grid_color_texto(self, _grid, nfila, ocol):
        if self.foreground:
            key = ocol.key
            if self.is_row_with_totals(nfila) or key in ("pwin", "pdraw", "plost"):
                return self.foreground
        return None

    def is_row_with_totals(self, nfila):
        return nfila == len(self.liMoves) - 1

    def isnt_row_with_totals(self, nfila):
        return nfila < len(self.liMoves) - 1

    def update_pv(self, pv_base):
        self.pv_base = pv_base
        if not pv_base:
            pv_mirar = ""
        else:
            pv_mirar = self.pv_base

        self.liMoves = self.db_stat.get_summary(pv_mirar, {}, self.with_figurines, False)

        self.grid.refresh()
        self.grid.gotop()

    def grid_right_button(self, _grid, row, _column, _modificadores):
        if self.is_row_with_totals(row):
            return
        alm = self.liMoves[row]["rec"]
        if not alm or not hasattr(alm, "LIALMS") or len(alm.LIALMS) < 2:
            return

        menu = QTDialogs.LCMenu(self)
        rondo = QTDialogs.rondo_puntos()
        for ralm in alm.LIALMS:
            menu.opcion(ralm, Game.pv_pgn(None, ralm.PV), rondo.otro())
            menu.separador()
        resp = menu.lanza()
        if resp:
            self.update_pv(resp.PV)

    def grid_tecla_control(self, _grid, k, _is_shift, _is_control, _is_alt):
        if k in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return):
            self.siguiente()

    def grid_doble_click(self, _grid, _fil, _col):
        self.siguiente()

    def siguiente(self):
        recno = self.grid.recno()
        if recno >= 0 and self.isnt_row_with_totals(recno):
            dic = self.liMoves[recno]
            if "pv" in dic:
                pv = dic["pv"]
                if pv.count(" ") > 0:
                    pv = f"{self.pv_base} {dic['pvmove']}"
                self.update_pv(pv)
