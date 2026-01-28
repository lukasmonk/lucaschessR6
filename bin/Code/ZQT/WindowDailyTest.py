import os.path
import random
import time
from dataclasses import dataclass
from typing import List


import Code
from Code.Analysis import Analysis
from Code.Base import Game, Move, Position
from Code.Base.Constantes import MULTIPV_MAXIMIZE
from Code.Board import Board
from Code.Engines import EngineManagerAnalysis, EngineResponse
from Code.QT import (
    Colocacion,
    Columnas,
    Controles,
    FormLayout,
    Grid,
    Iconos,
    LCDialog,
    QTDialogs,
    QTMessages,
    ScreenUtils,
)
from Code.QT import (
    Delegados,
)
from Code.SQL import UtilSQL
from Code.Z import Util
from Code.ZQT import WindowPotencia


class WDailyTestBase(LCDialog.LCDialog):
    li_histo: list

    def __init__(self, procesador):

        LCDialog.LCDialog.__init__(
            self,
            procesador.main_window,
            _("Your daily test"),
            Iconos.DailyTest(),
            "nivelBase1",
        )

        self.procesador = procesador
        self.configuration = Code.configuration

        self.historico = UtilSQL.DictSQL(self.configuration.paths.file_daily_test())
        self.calc_li_histo()

        self.engine, self.seconds, self.pruebas, self.fns = self.read_parameters()

        # Historico
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("FECHA", _("Date"), 120, align_center=True)
        o_columns.nueva("MPUNTOS", _("Average centipawns lost"), 180, align_center=True)
        o_columns.nueva("MTIEMPOS", _("Average time (seconds)"), 180, align_center=True)
        o_columns.nueva("ENGINE", _("Engine"), 120, align_center=True)
        o_columns.nueva("SEGUNDOS", _("Second(s)"), 80, align_center=True)
        o_columns.nueva("PRUEBAS", _("N. of tests"), 80, align_center=True)
        o_columns.nueva("FNS", _("File"), 150, align_center=True)
        self.ghistorico = Grid.Grid(self, o_columns, complete_row_select=True, select_multiple=True)
        self.ghistorico.setMinimumWidth(self.ghistorico.width_columns_displayables() + 20)

        # Tool bar
        li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.finalize),
            None,
            (_("Start"), Iconos.Empezar(), self.empezar),
            None,
            (_("Configuration"), Iconos.Opciones(), self.configurar),
            None,
            (_("Remove"), Iconos.Borrar(), self.borrar),
            None,
        )
        tb = QTDialogs.LCTB(self, li_acciones)

        # Colocamos
        ly = Colocacion.V().control(tb).control(self.ghistorico).margen(3)

        self.setLayout(ly)

        self.register_grid(self.ghistorico)
        self.restore_video()

    def read_parameters(self):
        param = UtilSQL.DictSQL(self.configuration.paths.file_daily_test(), tabla="parametros")
        name_engine = param.get("ENGINE", self.configuration.analyzer_default)
        seconds = param.get("SEGUNDOS", 7)
        pruebas = param.get("PRUEBAS", 5)
        fns = param.get("FNS", "")
        param.close()

        return name_engine, seconds, pruebas, fns

    def grid_num_datos(self, grid):
        return len(self.li_histo)

    def grid_dato(self, grid, row, obj_column):
        col = obj_column.key
        key = self.li_histo[row]
        reg = self.historico[key]
        if col == "FECHA":
            fecha = reg[col]
            return Util.local_date_time(fecha)
        elif col == "MPUNTOS":
            mpuntos = reg["MPUNTOS"]
            return f"{mpuntos:0.2f}"
        elif col == "MTIEMPOS":
            mtiempos = reg["MTIEMPOS"]
            return f"{mtiempos:0.2f}"
        elif col == "ENGINE":
            return reg["ENGINE"]
        elif col == "SEGUNDOS":
            vtime = int(reg["TIEMPOJUGADA"] / 1000)
            return f"{vtime}"
        elif col == "PRUEBAS":
            nfens = len(reg["LIFENS"])
            return f"{nfens}"
        elif col == "FNS":
            fns = reg.get("FNS", None)
            if fns:
                return os.path.basename(fns)
            else:
                return _("By default")
        return None

    def calc_li_histo(self):
        self.li_histo = self.historico.keys(si_ordenados=True, si_reverse=True)

    def closeEvent(self, event):  # Cierre con X
        self.cerrar()

    def cerrar(self):
        self.save_video()
        self.historico.close()

    def finalize(self):
        self.cerrar()
        self.reject()

    def configurar(self):
        # Datos
        li_gen = [(None, None)]

        # # Motor
        mt = self.configuration.tutor_default if self.engine is None else self.engine

        li_combo = [mt]
        for name, key in self.configuration.engines.list_name_alias_multipv10():
            li_combo.append((key, name))

        li_gen.append((f"{_('Engine')}:", li_combo))

        # # Segundos a pensar el tutor
        config = FormLayout.Spinbox(_("Duration of engine analysis (secs)"), 1, 99, 50)
        li_gen.append((config, self.seconds))

        # Pruebas
        config = FormLayout.Spinbox(_("N. of tests"), 1, 40, 40)
        li_gen.append((config, self.pruebas))

        # Fichero
        config = FormLayout.Fichero(
            _("File"),
            f"{_('List of FENs')} (*.fns);;{_('File')} PGN (*.pgn)",
            False,
            minimum_width=280,
        )
        li_gen.append((config, self.fns))

        # Editamos
        resultado = FormLayout.fedit(li_gen, title=_("Configuration"), parent=self, icon=Iconos.Opciones())
        if resultado:
            accion, li_resp = resultado
            self.engine = li_resp[0]
            self.seconds = li_resp[1]
            self.pruebas = li_resp[2]
            self.fns = li_resp[3]

            param = UtilSQL.DictSQL(self.configuration.paths.file_daily_test(), tabla="parametros")
            param["ENGINE"] = self.engine
            param["SEGUNDOS"] = self.seconds
            param["PRUEBAS"] = self.pruebas
            param["FNS"] = self.fns
            param.close()

    def borrar(self):
        li = self.ghistorico.list_selected_recnos()
        if len(li) > 0:
            if QTMessages.pregunta(self, _("Do you want to delete all selected records?")):
                with QTMessages.one_moment_please(self):
                    for row in li:
                        key = self.li_histo[row]
                        del self.historico[key]
                    self.historico.pack()
                    self.calc_li_histo()
                self.ghistorico.refresh()

    def empezar(self):
        li_r = []
        if self.fns and Util.exist_file(self.fns):
            fns = self.fns.lower()
            li = []
            if fns.endswith(".pgn"):
                with open(fns, "rt") as f:
                    for linea in f:
                        if linea.startswith("[FEN "):
                            li.append(linea[6:].split('"')[0])
            else:  # se supone que es un file de fens
                with open(fns, "rt") as f:
                    for linea in f:
                        linea = linea.strip()
                        if "|" in linea:
                            linea = linea.split("|")[0]
                        if (
                                linea[0].isalnum()
                                and linea[-1].isdigit()
                                and ((" w " in linea) or (" b " in linea))
                                and linea.count("/") == 7
                        ):
                            li.append(linea)
            if len(li) >= self.pruebas:
                li_r = random.sample(li, self.pruebas)
            else:
                self.fns = ""

        if not li_r:
            li_r = WindowPotencia.lee_varias_lineas_mfn(self.pruebas)

        # liR = liFens
        w = WDailyTest(self, li_r, self.engine, self.seconds, self.fns)
        w.exec()
        self.calc_li_histo()
        self.ghistorico.refresh()


@dataclass()
class DataMovement:
    pos: int
    pgn: str
    result: str
    loss: int
    selected: bool


class WDailyTest(LCDialog.LCDialog):
    manager_analysis: EngineManagerAnalysis.EngineManagerAnalysis
    li_data: List[DataMovement]

    def __init__(self, owner, li_fens, name_engine, seconds, fns):

        super(WDailyTest, self).__init__(owner, _("Your daily test"), Iconos.DailyTest(), "nivel")

        self.procesador = owner.procesador
        self.configuration = Code.configuration

        if name_engine.startswith("*"):
            name_engine = name_engine[1:]
        engine = self.configuration.engines.search_tutor(name_engine)
        self.manager_analysis = self.procesador.create_manager_analysis(engine, seconds * 1000, 0, 0, MULTIPV_MAXIMIZE)

        self.historico = owner.historico

        self.with_figurines = self.configuration.x_pgn_withfigurines

        # Board
        config_board = self.configuration.config_board("LEVEL", 48)

        self.liFens = li_fens
        self.nFens = len(self.liFens)
        self.juego = 0
        self.li_puntos = []
        self.li_pv = []
        self.li_tiempos = []
        self.fns = fns
        self.li_data = []

        self.move_done = None

        self.board = Board.Board(self, config_board)
        self.board.draw_window()
        self.board.set_dispatcher(self.player_has_moved_dispatcher)

        # Rotulos informacion
        self.lbColor = Controles.LB(self, "")
        self.lbJuego = Controles.LB(self, "").align_center()
        self.lbJuego.setStyleSheet("border: 2px solid lightgray; border-radius: 8px;")

        with_col = (Code.configuration.x_pgn_width - 52 - 12) // 2
        o_columns = Columnas.ListaColumnas()
        self.delegado_pgn = Delegados.EtiquetaPGN(None, si_indicador_inicial=False)
        o_columns.nueva("POS", _('N.'), 40, align_center=True)
        o_columns.nueva("MOVEMENT", _('Movements'), with_col, align_center=True, edicion=self.delegado_pgn)
        o_columns.nueva("LOSS", "🔻", 60, align_center=True)
        self.wrm = Grid.Grid(self, o_columns, complete_row_select=True)
        n_with = self.wrm.width_columns_displayables() + 20
        self.wrm.setFixedWidth(n_with)

        # Tool bar
        li_acciones = (
            # ( _( "Start" ), Iconos.Empezar(), "empezar" ),None,
            (_("Analysis"), Iconos.Tutor(), "analizar"),
            (_("Cancel"), Iconos.Cancelar(), "cancelar"),
            (_("Continue"), Iconos.Pelicula_Seguir(), "seguir"),
            (_("Resign"), Iconos.Abandonar(), "abandonar"),
        )
        self.tb = Controles.TB(self, li_acciones)

        ly_bm = Colocacion.H().control(self.board).control(self.wrm)
        ly_dt = Colocacion.H().control(self.lbColor).control(self.lbJuego)
        ly_tb = Colocacion.H().control(self.tb).otro(ly_dt)
        ly = Colocacion.V().otro(ly_tb).otro(ly_bm)

        self.setLayout(ly)

        self.position = Position.Position()
        self.restore_video()

        self.wrm.hide()
        self.play_next_move()

    def grid_num_datos(self, grid):
        return len(self.li_data)

    def grid_dato(self, grid, row, obj_column):
        data: DataMovement = self.li_data[row]
        col = obj_column.key
        if col == "MOVEMENT":
            return data.pgn, self.is_white, data.result, None, None
        elif col == "POS":
            return str(data.pos)
        elif col == "LOSS":
            return str(-data.loss)
        return None

    def grid_bold(self, _grid, row, obj_col):
        data: DataMovement = self.li_data[row]
        return data.selected

    def grid_color_fondo(self, _grid, row, obj_col):
        data: DataMovement = self.li_data[row]
        if data.selected and obj_col.key == "POS":
            return Code.dic_qcolors["PGN_SELBACKGROUND"]
        return None

    def finalize(self):
        self.manager_analysis.close()
        self.save_video()
        self.reject()

    def process_toolbar(self):
        accion = self.sender().key
        if accion == "abandonar":
            if QTMessages.pregunta(self, _("Do you want to resign?")):
                self.finalize()
        elif accion == "cancelar":
            if QTMessages.pregunta(self, _("Are you sure you want to cancel?")):
                self.finalize()
        elif accion in "finalize":
            self.finalize()
        elif accion == "empezar":
            self.play_next_move()
        elif accion == "seguir":
            self.play_next_move()
        elif accion == "analizar":
            self.analizar()

    def pon_toolbar(self, li_acciones):
        self.tb.clear()
        for k in li_acciones:
            self.tb.dic_toolbar[k].setVisible(True)
            self.tb.dic_toolbar[k].setEnabled(True)
            self.tb.addAction(self.tb.dic_toolbar[k])

        self.tb.li_acciones = li_acciones
        self.tb.update()

    def play_next_move(self):
        self.wrm.hide()
        ScreenUtils.shrink(self)
        self.pon_toolbar(["abandonar"])

        if self.juego == self.nFens:
            self.finish_the_test()
            return

        fen = self.liFens[self.juego]
        self.juego += 1

        cp = self.position

        cp.read_fen(fen)

        self.is_white = is_white = cp.is_white
        color_player, color_rival = _("White"), _("Black")
        k_player, q_player, k_rival, q_rival = "K", "Q", "k", "q"
        if not is_white:
            color_player, color_rival = color_rival, color_player
            k_player, q_player, k_rival, q_rival = k_rival, q_rival, k_player, q_player

        mens = f"<h2>{color_player}</h2>"

        if cp.castles:

            def get_castle(ck, cq):
                castle = ""
                if ck in cp.castles:
                    castle += "O-O"
                if cq in cp.castles:
                    if castle:
                        castle += ",  "
                    castle += "O-O-O"
                return castle

            enr = get_castle(k_player, q_player)
            if enr:
                mens += f"<br>{color_player} : {enr}"
            enr = get_castle(k_rival, q_rival)
            if enr:
                mens += f"<br>{color_rival} : {enr}"
        if cp.en_passant != "-":
            mens += f"<br>{_('En passant')} : {cp.en_passant}"

        self.lbJuego.set_text(f"<h1>{self.juego}/{self.nFens}</h1>")

        self.lbColor.set_text(mens)

        self.continue_human()
        self.initial_time = time.time()

    def finish_the_test(self):
        self.stop_human()
        self.manager_analysis.close()

        t = 0
        for x in self.li_puntos:
            t += x
        mpuntos = t * 1.0 / self.nFens

        t = 0.0
        for x in self.li_tiempos:
            t += x
        mtiempos = t * 1.0 / self.nFens

        hoy = Util.today()
        fecha = f"{hoy.year}{hoy.month:02d}{hoy.day:02d}{hoy.hour:02d}{hoy.minute:02d}"
        datos = {
            "FECHA": hoy,
            "ENGINE": self.manager_analysis.engine.key,
            "TIEMPOJUGADA": self.manager_analysis.run_engine_params.fixed_ms,
            "LIFENS": self.liFens,
            "LIPV": self.li_pv,
            "MPUNTOS": mpuntos,
            "MTIEMPOS": mtiempos,
            "FNS": self.fns,
        }

        self.historico[fecha] = datos

        self.lbColor.set_text("")
        self.lbJuego.set_text("")
        self.wrm.hide()

        mens = f"<h3>{_('Average centipawns lost')} : {mpuntos:.2f}</h3><h3>{_('Average time (seconds)')} : {mtiempos:.2f}</h3>"
        QTMessages.message(self, mens, titulo=_("Result"))

        self.accept()

    def stop_human(self):
        self.board.disable_all()

    def continue_human(self):
        si_w = self.position.is_white
        self.board.set_position(self.position)
        self.board.set_side_bottom(si_w)
        self.board.set_side_indicator(si_w)
        self.board.activate_side(si_w)

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        self.stop_human()

        movimiento = from_sq + to_sq

        # Peon coronando
        if not promotion and self.position.pawn_can_promote(from_sq, to_sq):
            promotion = self.board.pawn_promoting(self.position.is_white)
        if promotion:
            movimiento += promotion

        game = Game.Game(first_position=self.position)
        ok, mens, self.move_done = Move.get_game_move(game, self.position, from_sq, to_sq, promotion)
        if ok:
            game.add_move(self.move_done)
            self.board.set_position(self.move_done.position)
            self.board.put_arrow_sc(from_sq, to_sq)
            self.calc_time_score()
        else:
            self.continue_human()

    def calc_time_score(self):
        vtime = time.time() - self.initial_time

        with QTMessages.analizando(self):
            self.mrm, pos = self.manager_analysis.analyze_move(self.move_done.game, 0, None)
            self.move_done.analysis = self.mrm, pos

        pv = self.move_done.movimiento()
        pv = pv.lower()

        minimo = self.mrm.li_rm[0].centipawns_abs()
        current_loss = 0
        self.li_data = []
        pos = 0
        previo = None
        current_pos = 0
        rm: EngineResponse.EngineResponse
        for rm in self.mrm.li_rm:
            pts = rm.centipawns_abs()
            if pts != previo:
                pos += 1
                previo = pts
            loss = minimo - pts
            mv = rm.movimiento().lower()
            selected = mv == pv
            if self.with_figurines:
                pgn = self.position.pgn(rm.from_sq, rm.to_sq, rm.promotion)
            else:
                pgn = self.position.pgn_translated(rm.from_sq, rm.to_sq, rm.promotion)
            if selected:
                current_pos = len(self.li_data)
                current_loss = loss
            self.li_data.append(DataMovement(pos, pgn, rm.abbrev_text_base(), loss, selected))

        if self.with_figurines:
            self.delegado_pgn.setWhite(self.is_white)
        self.wrm.show()
        self.wrm.refresh()
        self.wrm.goto(current_pos, 0)
        self.li_pv.append(pv)
        self.li_puntos.append(current_loss)
        self.li_tiempos.append(vtime)

        self.lbColor.set_text("")
        self.pon_toolbar(["seguir", "cancelar", "analizar"])

    def analizar(self):
        Analysis.show_analysis(
            self.manager_analysis,
            self.move_done,
            self.position.is_white,
            1,
            main_window=self,
            must_save=False,
        )


def daily_test(procesador):
    w = WDailyTestBase(procesador)
    w.exec()
