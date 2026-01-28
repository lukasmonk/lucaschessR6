import sqlite3
import time

from PySide6 import QtCore, QtWidgets

import Code
from Code.Z import ControlPGN, CPU, TimeControl, Util
from Code.Base import Game, Move
from Code.Base.Constantes import (
    BLACK,
    INFINITE,
    RESULT_DRAW,
    RESULT_WIN_BLACK,
    RESULT_WIN_WHITE,
    ST_PAUSE,
    ST_PLAYING,
    ST_WAITING,
    TERMINATION_ADJUDICATION,
    TERMINATION_ENGINE_MALFUNCTION,
    TERMINATION_UNKNOWN,
    TERMINATION_WIN_ON_TIME,
    WHITE,
)
from Code.Board import Board
from Code.Engines import (
    EngineManagerPlay,
    EngineRun,
    ListEngineManagers,
)
from Code.MainWindow import WAnalysisBar
from Code.QT import Colocacion, Columnas, Controles, Delegados, Grid, Iconos, QTDialogs, QTUtils, ScreenUtils
from Code.Sound import Sound


class Worker(QtWidgets.QWidget):
    tc_white: TimeControl.TimeControl
    tc_black: TimeControl.TimeControl
    grid_pgn: Grid.Grid
    lb_player: dict
    lb_clock: dict
    lb_rotulo2: Controles.LB
    lb_rotulo3: Controles.LB
    seconds_per_move: int
    max_seconds: int
    xmatch = None
    manager_arbiter = None
    next_control: int
    dic_engine_managers: dict

    def __init__(self, run_worker):
        QtWidgets.QWidget.__init__(self)

        Code.list_engine_managers = ListEngineManagers.ListEngineManagers()
        Code.list_engine_managers.check_active_logs()

        self.run_worker = run_worker

        self.setWindowTitle(f'{run_worker.name} - {_("Worker")}')
        self.setWindowIcon(Iconos.League())

        self.tb = QTDialogs.LCTB(self, icon_size=24)

        conf_board = Code.configuration.config_board(run_worker.key_video, 36)
        self.board = Board.Board(self, conf_board)
        self.board.draw_window()
        Delegados.genera_pm(self.board.pieces)

        ct = self.board.config_board
        self.antiguoAnchoPieza = ct.width_piece()

        # Analysis Bar
        self.analysis_bar = WAnalysisBar.AnalysisBar(self, self.board)
        self.key_vars = "RUN_WORKERS"
        dic = Code.configuration.read_variables(self.key_vars)
        activated = dic.get("ANALYSIS_BAR", Code.configuration.x_analyzer_activate_ab)
        self.analysis_bar.activate(activated)

        self.configuration = Code.configuration
        self.game = Game.Game()
        self.pgn = ControlPGN.ControlPGN(self)
        ly_pgn = self.crea_bloque_informacion()

        self.is_closed = False
        self.state = None
        self.current_side = WHITE

        ly_ab_board = Colocacion.H().control(self.analysis_bar).control(self.board)
        ly_tt = Colocacion.V().control(self.tb).otro(ly_ab_board)

        layout = Colocacion.H().otro(ly_tt).otro(ly_pgn).relleno().margen(3)
        self.setLayout(layout)

        self.cpu = CPU.CPU(self)

        self.pon_estado(ST_WAITING)

    def pon_estado(self, state):
        self.state = state
        self.pon_toolbar(state)

    def pon_toolbar(self, state):
        li_acciones = [(_("Cancel"), Iconos.Cancelar(), self.cancel_match), None]
        if state == ST_PLAYING:
            li_acciones.extend(
                [
                    (_("Pause"), Iconos.Pause(), self.pausa),
                    None,
                    (_("Adjudication"), Iconos.EndGame(), self.adjudication),
                    None,
                ]
            )
        elif state == ST_PAUSE:
            li_acciones.extend(
                [
                    (_("Continue"), Iconos.Continue(), self.seguir),
                    None,
                    (_("Adjudication"), Iconos.EndGame(), self.adjudication),
                    None,
                ]
            )
        li_acciones.append((_("Config"), Iconos.Configurar(), self.configurar))
        li_acciones.append(None)
        self.tb.reset(li_acciones)

    def crea_bloque_informacion(self):
        configuration = Code.configuration
        n_ancho_pgn = configuration.x_pgn_width
        n_ancho_color = (n_ancho_pgn - 52 - 24) // 2
        n_ancho_labels = max(int((n_ancho_pgn - 3) // 2), 140)
        # # Pgn
        o_columnas = Columnas.ListaColumnas()
        o_columnas.nueva("NUMBER", _("N."), 52, align_center=True)
        with_figurines = configuration.x_pgn_withfigurines
        o_columnas.nueva(
            "WHITE",
            _("White"),
            n_ancho_color,
            edicion=Delegados.EtiquetaPGN(True if with_figurines else None),
        )
        o_columnas.nueva(
            "BLACK",
            _("Black"),
            n_ancho_color,
            edicion=Delegados.EtiquetaPGN(False if with_figurines else None),
        )
        self.grid_pgn = Grid.Grid(self, o_columnas, is_column_header_movable=False)
        self.grid_pgn.setMinimumWidth(n_ancho_pgn)
        self.grid_pgn.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.grid_pgn.font_type(puntos=configuration.x_pgn_fontpoints)
        self.grid_pgn.set_height_row(configuration.x_pgn_rowheight)

        # # Blancas y negras
        f = Controles.FontType(puntos=configuration.x_sizefont_players, peso=75)
        self.lb_player = {}
        for side in (WHITE, BLACK):
            self.lb_player[side] = Controles.LB(self).relative_width(n_ancho_labels)
            self.lb_player[side].align_center().set_font(f).set_wrap()
            self.lb_player[side].setFrameStyle(QtWidgets.QFrame.Shape.Box | QtWidgets.QFrame.Shadow.Raised)

        self.configuration.set_property(self.lb_player[WHITE], "white")
        self.configuration.set_property(self.lb_player[BLACK], "black")

        # Relojes
        f = Controles.FontType("Arial Black", puntos=26, peso=75)

        self.lb_clock = {}
        for side in (WHITE, BLACK):
            self.lb_clock[side] = Controles.LB(self, "00:00").set_font(f).align_center().minimum_width(n_ancho_labels)
            self.lb_clock[side].setFrameStyle(QtWidgets.QFrame.Shape.Box | QtWidgets.QFrame.Shadow.Raised)
            self.configuration.set_property(self.lb_clock[side], "clock")

        # Rotulos de informacion
        f = Controles.FontType(puntos=configuration.x_pgn_fontpoints)
        self.lb_rotulo2 = Controles.LB(self).set_wrap()
        self.lb_rotulo2.setStyleSheet("border: 1px solid gray;")
        self.lb_rotulo3 = Controles.LB(self).set_wrap().set_fixed_lines(2).set_font(f).align(top=True)
        self.lb_rotulo2.set_text("")
        self.lb_rotulo2.hide()

        # Layout
        ly_color = Colocacion.G()
        ly_color.controlc(self.lb_player[WHITE], 0, 0).controlc(self.lb_player[BLACK], 0, 1)
        ly_color.controlc(self.lb_clock[WHITE], 1, 0).controlc(self.lb_clock[BLACK], 1, 1)

        # Abajo
        ly_abajo = Colocacion.V()
        ly_abajo.control(self.lb_rotulo3)

        ly_v = (
            Colocacion.V()
            .otro(ly_color)
            .control(self.grid_pgn)
            .control(self.lb_rotulo2)
            .control(self.lb_rotulo3)
            .margen(3)
        )

        return ly_v

    def grid_num_datos(self, grid):
        return self.pgn.num_rows()

    def configurar(self):
        menu = QTDialogs.LCMenu(self)
        activated = self.analysis_bar.activated
        menu.opcion("analysis_bar", _("Analysis Bar"), is_checked=activated)
        resp = menu.lanza()
        if resp == "analysis_bar":
            activated = not activated
            self.analysis_bar.activate(activated)

            dic = Code.configuration.read_variables(self.key_vars)
            if activated == Code.configuration.x_analyzer_activate_ab:
                activated = None
            dic["ANALYSIS_BAR"] = activated
            Code.configuration.write_variables(self.key_vars, dic)

    def grid_right_button(self, grid, row, col, modif):
        self.configurar()

    def crea_arbiter(self):
        engine = Code.configuration.engines.search(self.run_worker.move_evaluator)

        run_engine_params = EngineRun.RunEngineParams()
        run_engine_params.update(engine, int(self.run_worker.arbiter_time * 1000), 0, 0, 1)

        engine_manager = EngineManagerPlay.EngineManagerPlay(engine, run_engine_params)
        return engine_manager

    def looking_for_work(self):
        try:
            self.xmatch = self.run_worker.get_other_match()
        except sqlite3.IntegrityError:
            self.xmatch = None
        if self.xmatch is None:
            self.finalize()
            return
        self.procesa_match()
        if not self.is_closed:
            self.looking_for_work()

    def procesa_match(self):
        self.pon_estado(ST_PLAYING)

        # Cerramos los motores anteriores si los hay
        Code.list_engine_managers.close_all()

        if self.run_worker.arbiter_active:
            self.manager_arbiter = self.crea_arbiter()
        else:
            self.manager_arbiter = None

        if self.run_worker.draw_range == 0 and self.run_worker.resign == 0:
            self.next_control = INFINITE
        else:
            self.next_control = 21

        max_minute, self.seconds_per_move = self.run_worker.time_engine_engine
        self.max_seconds = max_minute * 60

        # abrimos motores
        rival = {
            WHITE: self.run_worker.engine_white,
            BLACK: self.run_worker.engine_black,
        }
        for side in (WHITE, BLACK):
            self.lb_player[side].set_text(rival[side].name)

        self.dic_engine_managers = {}

        for side in (WHITE, BLACK):
            engine = rival[side]
            run_engine_params = EngineRun.RunEngineParams()
            run_engine_params.update_from_engine(engine)
            engine_manager = EngineManagerPlay.EngineManagerPlay(engine, run_engine_params)

            if self.run_worker.book_path:
                engine_manager.set_book(
                    self.run_worker.book_path, self.run_worker.book_rr, 5, self.run_worker.book_depth
                )
            else:
                bk = engine.book
                if bk and bk in "*-":
                    bk = None
                if bk:
                    engine_manager.set_book(bk, engine.book_rr, 5, engine.book_max_plies)
            self.dic_engine_managers[side] = engine_manager

        if self.run_worker.initial_fen:
            self.game = Game.Game(fen=self.run_worker.initial_fen)
        else:
            self.game = Game.Game()

        self.pgn.game = self.game

        self.tc_white = TimeControl.TimeControl(self, self.game, WHITE)
        self.tc_white.config_clock(self.max_seconds, self.seconds_per_move, 0, 0)
        self.tc_white.set_labels()
        self.tc_black = TimeControl.TimeControl(self, self.game, BLACK)
        self.tc_black.config_clock(self.max_seconds, self.seconds_per_move, 0, 0)
        self.tc_black.set_labels()

        h_max = 0
        for side in (WHITE, BLACK):
            h = self.lb_player[side].height()
            if h > h_max:
                h_max = h
        for side in (WHITE, BLACK):
            self.lb_player[side].fixed_height(h_max)

        time_control = f"{int(self.max_seconds)}"
        if self.seconds_per_move:
            time_control += "+%d" % self.seconds_per_move
        self.game.set_tag("TimeControl", time_control)

        self.board.disable_all()
        self.board.set_position(self.game.last_position)
        self.grid_pgn.refresh()

        while self.state == ST_PAUSE or self.play_next_move():
            if self.state == ST_PAUSE:
                QTUtils.refresh_gui()
                time.sleep(0.1)
            if self.is_closed:
                break
        for side in (WHITE, BLACK):
            self.dic_engine_managers[side].close()

        if not self.is_closed:
            if self.game_finished():
                self.save_game_done()

    def save_game_done(self):
        self.game.set_tag("Site", Code.lucas_chess)
        self.game.set_tag("Event", self.run_worker.name)
        self.run_worker.add_tags_game(self.game)

        hoy = Util.today()
        self.game.set_tag("Date", "%d.%02d.%02d" % (hoy.year, hoy.month, hoy.day))

        engine_white = self.dic_engine_managers[WHITE].engine
        engine_black = self.dic_engine_managers[BLACK].engine
        self.game.set_tag("White", engine_white.name)
        self.game.set_tag("Black", engine_black.name)
        if engine_white.elo:
            self.game.set_tag("WhiteElo", engine_white.elo)
        if engine_black.elo:
            self.game.set_tag("BlackElo", engine_black.elo)

        self.game.set_extend_tags()
        self.game.sort_tags()

        self.run_worker.put_match_done(self.game)

    def finalize(self):
        self.is_closed = True

        self.analysis_bar.activate(False)
        Code.list_engine_managers.close_all()
        self.close()
        QtWidgets.QApplication.quit()

    def cancel_match(self):
        self.is_closed = True
        Code.list_engine_managers.close_all()
        self.run_worker.cancel_match()
        self.finalize()

    def closeEvent(self, event):
        self.cancel_match()
        self.finalize()

    def pausa(self):
        self.pause_clock(self.current_side)
        self.pon_estado(ST_PAUSE)

    def seguir(self):
        self.start_clock(self.current_side)
        self.pon_estado(ST_PLAYING)

    def adjudication(self):
        self.pon_estado(ST_PAUSE)
        QTUtils.refresh_gui()
        menu = QTDialogs.LCMenu(self)
        menu.opcion(RESULT_DRAW, RESULT_DRAW, Iconos.Tablas())
        menu.separador()
        menu.opcion(RESULT_WIN_WHITE, RESULT_WIN_WHITE, Iconos.Blancas())
        menu.separador()
        menu.opcion(RESULT_WIN_BLACK, RESULT_WIN_BLACK, Iconos.Negras())
        resp = menu.lanza()
        if resp is not None:
            self.game.set_termination(TERMINATION_ADJUDICATION, resp)
            self.save_game_done()
            self.looking_for_work()

    def set_clock(self):
        if self.is_closed or self.game_finished():
            return False
        is_white = self.current_side == WHITE
        tc = self.tc_white if is_white else self.tc_black
        tc.set_labels()
        if tc.time_is_consumed():
            self.game.set_termination_time(is_white)
            return False

        QTUtils.refresh_gui()
        return True

    def start_clock(self, is_white):
        tc = self.tc_white if is_white else self.tc_black
        tc.start()

    def stop_clock(self, is_white):
        tc = self.tc_white if is_white else self.tc_black
        secs = tc.stop()
        tc.set_labels()
        return secs

    def pause_clock(self, is_white):
        tc = self.tc_white if is_white else self.tc_black
        tc.pause()
        tc.set_labels()

    def restart_clock(self, is_white):
        tc = self.tc_white if is_white else self.tc_black
        tc.restart()
        tc.set_labels()

    def set_clock_label(self, side, tm, tm2):
        if tm2 is not None:
            tm += f"<br><FONT SIZE=\"-4\">{tm2}"
        self.lb_clock[side].set_text(tm)

    def set_clock_white(self, tm, tm2):
        self.set_clock_label(WHITE, tm, tm2)

    def set_clock_black(self, tm, tm2):
        self.set_clock_label(BLACK, tm, tm2)

    def add_move(self, move):
        show_opening = self.game.pending_opening
        self.game.add_move(move)

        if show_opening:
            opening = self.game.opening
            if opening:
                nom_opening = opening.tr_name
                if opening.eco:
                    nom_opening += f" ({opening.eco})"
                self.lb_rotulo2.set_text(nom_opening)
                self.lb_rotulo2.show()
        else:
            self.lb_rotulo2.hide()

        self.board.remove_movables()
        self.board.put_arrow_sc(move.from_sq, move.to_sq)
        self.grid_pgn.refresh()
        self.grid_pgn.gobottom(2 if self.game.last_position.is_white else 1)

        self.refresh()

    def refresh(self):
        self.board.escena.update()
        self.update()
        QTUtils.refresh_gui()

    def game_finished(self):
        return self.game.termination != TERMINATION_UNKNOWN

    def show_pv(self, pv, n_arrows):
        if not pv:
            return True
        self.board.remove_arrows()
        tipo = "mt"
        opacity = 100
        pv = pv.strip()
        while "  " in pv:
            pv = pv.replace("  ", " ")
        lipv = pv.split(" ")
        npv = len(lipv)
        nbloques = min(npv, n_arrows)
        salto = (80 - 15) * 2 / (nbloques - 1) if nbloques > 1 else 0
        cambio = max(30, salto)

        for n in range(nbloques):
            pv = lipv[n]
            self.board.show_arrow_mov(pv[:2], pv[2:4], tipo, opacity=opacity / 100)
            if n % 2 == 1:
                opacity -= cambio
                cambio = salto
            tipo = "ms" if tipo == "mt" else "mt"
        return True

    def play_next_move(self):
        if self.check_is_finished():
            return False

        self.current_side = is_white = self.game.is_white()

        self.board.set_side_indicator(is_white)

        engine_manager: EngineManagerPlay.EngineManagerPlay = self.dic_engine_managers[is_white]
        if self.analysis_bar.activated:
            self.analysis_bar.set_game(self.game)

        engine_manager.run_engine_params.update_var_time(
            self.tc_white.pending_time, self.tc_black.pending_time, self.seconds_per_move
        )

        self.start_clock(is_white)
        rm = engine_manager.play(game=self.game, dispacher=self.gui_dispatch)
        if self.state == ST_PAUSE:
            self.board.remove_movables()
            return True
        time_seconds = self.stop_clock(is_white)
        clock_seconds = self.tc_white.pending_time if is_white else self.tc_black.pending_time
        if rm is None:
            self.sudden_end(is_white)
            return True

        from_sq = rm.from_sq
        to_sq = rm.to_sq
        promotion = rm.promotion

        ok, mens, move = Move.get_game_move(self.game, self.game.last_position, from_sq, to_sq, promotion)
        if not move:
            self.sudden_end(is_white)
            return True

        if engine_manager.mrm:
            move.analysis = engine_manager.mrm.clone(), 0
            move.del_nags()

        if time_seconds:
            move.set_time_ms(time_seconds * 1000.0)
        if clock_seconds:
            move.set_clock_ms(clock_seconds * 1000.0)
        self.add_move(move)
        self.move_the_pieces(move.list_piece_moves)
        self.sound(move)

        return True

    def sound(self, move):
        if self.configuration.x_sound_tournements:
            if not Code.runSound:
                run_sound = Sound.RunSound()
            else:
                run_sound = Code.runSound
            if self.configuration.x_sound_move:
                run_sound.play_list(move.sounds_list())
            if self.configuration.x_sound_beep:
                run_sound.play_beep()

    def sudden_end(self, is_white):
        result = RESULT_WIN_BLACK if is_white else RESULT_WIN_WHITE
        self.game.set_termination(TERMINATION_ENGINE_MALFUNCTION, result)

    def grid_dato(self, grid, row, obj_column):
        control_pgn = self.pgn

        col = obj_column.key
        if col == "NUMBER":
            return control_pgn.dato(row, col)

        move = control_pgn.only_move(row, col)
        if move is None:
            return ""

        color = None
        info = ""
        indicador_inicial = None

        st_nags = set()

        if move.analysis:
            mrm, pos = move.analysis
            rm = mrm.li_rm[pos]
            mate = rm.mate
            si_w = move.position_before.is_white
            if mate:
                if mate == 1:
                    info = ""
                else:
                    if not si_w:
                        mate = -mate
                    info = "M%+d" % mate
            else:
                pts = rm.puntos
                if not si_w:
                    pts = -pts
                info = f"{float(pts / 100.0):+0.2f}"

            nag, color_nag = mrm.set_nag_color(rm)
            st_nags.add(nag)

        if move.in_the_opening:
            indicador_inicial = "R"

        pgn = move.pgn_figurines() if self.configuration.x_pgn_withfigurines else move.pgn_translated()

        return pgn, color, info, indicador_inicial, st_nags

    def gui_dispatch(self, rm):
        if self.is_closed or self.state != ST_PLAYING:
            return False
        if rm.pv:
            p = Game.Game(self.game.last_position)
            p.read_pv(rm.pv)
            rm.is_white = self.game.last_position.is_white
            txt = f"<b>[{rm.name}]</b> ({rm.abbrev_text()}) {p.pgn_translated()}"
            self.lb_rotulo3.set_text(txt)
            self.show_pv(rm.pv, 1)
        return self.set_clock()

    def clocks_finished(self):
        if self.tc_white.time_is_consumed():
            self.game.set_termination(TERMINATION_WIN_ON_TIME, RESULT_WIN_BLACK)
            return True
        if self.tc_black.time_is_consumed():
            self.game.set_termination(TERMINATION_WIN_ON_TIME, RESULT_WIN_WHITE)
            return True
        return False

    def check_is_finished(self):
        if self.clocks_finished():
            return True

        if self.state != ST_PLAYING or self.is_closed or self.game_finished() or self.game.is_finished():
            self.game.set_result()
            return True

        self.next_control -= 1
        if self.next_control > 0:
            return False

        self.next_control = 1

        num_moves = len(self.game)

        last_move = self.game.last_jg()
        if not last_move.analysis:
            return False
        mrm, pos = last_move.analysis
        rm_ult = mrm.li_rm[pos]
        ant_move = self.game.move(-2)
        if not ant_move.analysis:
            return False
        mrm, pos = ant_move.analysis
        rm_ant = mrm.li_rm[pos]

        p_ult = rm_ult.centipawns_abs()
        p_ant = -rm_ant.centipawns_abs()

        def arbiter_score():
            rm = self.manager_arbiter.play_game(self.game)
            self.next_control = 10
            return rm.centipawns_abs()

        # Draw
        dr = self.run_worker.draw_range
        dmp = self.run_worker.draw_min_ply
        if dmp and dr > 0 and num_moves >= dmp and (abs(p_ult) <= dr and abs(p_ant) <= dr):
            p_tut = arbiter_score() if self.manager_arbiter else 0
            if abs(p_tut) <= dr:
                self.game.set_termination(TERMINATION_ADJUDICATION, RESULT_DRAW)
                return True
            return False

        # Resign
        rs = self.run_worker.resign
        if 0 < rs <= abs(p_ult) or 0 < rs <= abs(p_ant):
            p_tut = arbiter_score() if self.manager_arbiter else rs  # si no hay manager que pase el control
            if abs(p_tut) >= rs:
                is_white = self.game.last_position.is_white
                if p_tut > 0:
                    result = RESULT_WIN_WHITE if is_white else RESULT_WIN_BLACK
                else:
                    result = RESULT_WIN_BLACK if is_white else RESULT_WIN_WHITE
                self.game.set_termination(TERMINATION_ADJUDICATION, result)
                return True

        return False

    def move_the_pieces(self, li_movs):
        if self.run_worker.slow_pieces:

            rapidez = self.configuration.pieces_speed_porc()
            cpu = self.cpu
            cpu.reset()
            seconds = None

            # primero los movimientos
            for movim in li_movs:
                if movim[0] == "m":
                    if seconds is None:
                        from_sq, to_sq = movim[1], movim[2]
                        dc = ord(from_sq[0]) - ord(to_sq[0])
                        df = int(from_sq[1]) - int(to_sq[1])
                        # Maxima distancia = 9.9 ( 9,89... sqrt(7**2+7**2)) = 4 seconds
                        dist = (dc**2 + df**2) ** 0.5
                        seconds = 4.0 * dist / (9.9 * rapidez)
                    cpu.move_piece(movim[1], movim[2], is_exclusive=False, seconds=seconds)

            if seconds is None:
                seconds = 1.0

            # segundo los borrados
            for movim in li_movs:
                if movim[0] == "b":
                    n = cpu.wait(seconds * 0.80 / rapidez)
                    cpu.remove_piece(movim[1], father=n)

            # tercero los cambios
            for movim in li_movs:
                if movim[0] == "c":
                    cpu.change_piece(movim[1], movim[2], is_exclusive=True)

            cpu.run_linear()

        else:
            for movim in li_movs:
                if movim[0] == "b":
                    self.board.remove_piece(movim[1])
                elif movim[0] == "m":
                    self.board.move_piece(movim[1], movim[2])
                elif movim[0] == "c":
                    self.board.change_piece(movim[1], movim[2])

    def changeEvent(self, event: QtCore.QEvent):
        QtWidgets.QWidget.changeEvent(self, event)
        if event.type() != QtCore.QEvent.Type.WindowStateChange:
            return

        nue = ScreenUtils.EstadoWindow(self.windowState())
        ant = ScreenUtils.EstadoWindow(event.oldState())

        ct = self.board.config_board

        if nue.fullscreen:
            self.board.siF11 = True
            self.antiguoAnchoPieza = 1000 if ant.maximizado else ct.width_piece()
            self.board.maximize_size(True)
        else:
            if ant.fullscreen:
                self.tb.show()
                self.board.normal_size(self.antiguoAnchoPieza)
                self.adjust_size()
                if self.antiguoAnchoPieza == 1000:
                    self.setWindowState(QtCore.Qt.WindowState.WindowMaximized)
            elif nue.maximizado:
                self.antiguoAnchoPieza = ct.width_piece()
                self.board.maximize_size(False)
            elif ant.maximizado:
                if not self.antiguoAnchoPieza or self.antiguoAnchoPieza == 1000:
                    self.antiguoAnchoPieza = self.board.calc_width_mx_piece()
                self.board.normal_size(self.antiguoAnchoPieza)
                self.adjust_size()

    def adjust_size(self):
        ScreenUtils.shrink(self)
