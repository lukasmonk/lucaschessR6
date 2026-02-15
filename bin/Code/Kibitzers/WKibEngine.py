import sys
from typing import Optional

from PySide6 import QtCore

from Code.Z import Util
from Code.Base import Game, Move, Position
from Code.Base.Constantes import KIB_BEFORE_MOVE
from Code.Engines import EngineRun
from Code.Kibitzers import Kibitzers, WindowKibitzers, WKibCommon
from Code.QT import Colocacion, Columnas, Controles, Delegados, Grid, Iconos, QTMessages, QTUtils, ScreenUtils


class WKibEngine(WKibCommon.WKibCommon):
    engine_name: str
    run_engine_params: EngineRun.RunEngineParams
    engine_run: Optional[EngineRun.EngineRun]

    def __init__(self, cpu):
        WKibCommon.WKibCommon.__init__(self, cpu, Iconos.Kibitzer())

        self.is_candidates = cpu.tipo == Kibitzers.KIB_CANDIDATES or cpu.tipo == Kibitzers.KIB_THREATS

        if cpu.tipo == Kibitzers.KIB_BESTMOVE:
            rotulo = _("Best move")
        elif cpu.tipo == Kibitzers.KIB_THREATS:
            rotulo = _("Threats")
        else:
            rotulo = _("Alternatives")

        delegado = Delegados.EtiquetaPOS(True, with_lines=False, siFondo=True) if self.with_figurines else None
        delegado_pgn = Delegados.LinePGN() if self.with_figurines else None

        self.color_done = ScreenUtils.qt_color_rgb(231, 244, 254)

        o_columns = Columnas.ListaColumnas()
        configuration = self.cpu.configuration
        if not self.is_candidates:
            o_columns.nueva("DEPTH", "^", 40, align_center=True)
        o_columns.nueva("BESTMOVE", rotulo, 80, align_center=True, edicion=delegado)
        o_columns.nueva("EVALUATION", _("Evaluation"), 85, align_center=True)
        o_columns.nueva("MAINLINE", _("Main line"), 400, edicion=delegado_pgn)
        self.grid = Grid.Grid(
            self,
            o_columns,
            dic_video=self.dic_video,
            complete_row_select=True,
            heigh_row=configuration.x_pgn_rowheight,
        )
        f = Controles.FontType(puntos=configuration.x_pgn_fontpoints)
        self.grid.set_font(f)

        self.lbDepth = Controles.LB(self)

        li_acciones = [
            (_("Quit"), Iconos.Kibitzer_Close(), self.finalize),
            (_("Continue"), Iconos.Kibitzer_Play(), self.play),
            (_("Pause"), Iconos.Kibitzer_Pause(), self.pause),
            (_("Original position"), Iconos.HomeBlack(), self.home),
            (_("Takeback"), Iconos.Kibitzer_Back(), self.takeback),
            (
                _("The line selected is saved to the clipboard"),
                Iconos.Kibitzer_Clipboard(),
                self.portapapeles_jug_selected,
            ),
            (_("Analyze color"), Iconos.Kibitzer_Side(), self.color),
            (_("Show/hide board"), Iconos.Kibitzer_Board(), self.config_board),
            (_("Manual position"), Iconos.Kibitzer_Voyager(), self.set_position),
            (
                f"{_('Enable')}: {_('window on top')}",
                Iconos.Pin(),
                self.window_top,
            ),
            (
                f"{_('Disable')}: {_('window on top')}",
                Iconos.Unpin(),
                self.window_bottom,
            ),
            (_("Options"), Iconos.Kibitzer_Options(), self.change_options),
        ]
        if cpu.tipo == Kibitzers.KIB_THREATS:
            del li_acciones[4]
        self.tb = Controles.TBrutina(self, li_acciones, with_text=False, icon_size=24)
        for rut in (self.play, self.home):
            self.tb.set_action_visible(rut, False)

        ly1 = Colocacion.H().control(self.tb).relleno().control(self.lbDepth).margen(0)
        ly2 = Colocacion.H().control(self.board).control(self.grid).margen(0)
        layout = Colocacion.V().otro(ly1).espacio(-10).otro(ly2).margen(3)
        self.setLayout(layout)

        self.siPlay = True
        self.is_white = True
        self.is_black = True

        if not self.show_board:
            self.board.hide()
        self.restore_video(self.dic_video)
        self.set_flags()

        self.launch_engine()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check_input)
        self.timer.start(200)

        self.need_refresh_data = False  # Se mira cada 200ms en check_input también, para que no se acumule
        # la recepción de señales en profundidades bajas.
        self.stopped = False
        self._game_version = 0

    def change_options(self):
        self.pause()
        w = WindowKibitzers.WKibitzerLive(self, self.cpu.configuration, self.cpu.num_kibitzer)
        if w.exec():
            self.kibitzer = self.cpu.reset_kibitzer()
            self.engine_run.close()
            self.launch_engine()
            self.cpu.reprocesa()
        self.play()
        self.grid.refresh()

    def stop(self):
        self.engine_run.stop()

    def grid_num_datos(self, _grid):
        return len(self.li_moves)

    def grid_dato(self, _grid, row, obj_column):
        rm = self.li_moves[row]
        key = obj_column.key
        if key == "EVALUATION":
            return rm.abbrev_text_base()

        elif key == "BESTMOVE":
            p = Game.Game(first_position=self.game.last_position)
            p.read_pv(rm.movimiento())
            if len(p) > 0:
                move: Move.Move = p.li_moves[0]
                resp = move.pgn_figurines() if self.with_figurines else move.pgn_translated()
                if self.with_figurines:
                    is_white = self.game.last_position.is_white
                    return resp, is_white, None, None, None, None, False, True
                else:
                    return resp
            else:
                return None

        elif key == "DEPTH":
            return "%d" % rm.depth

        else:
            if rm.pv:
                p = Game.Game(first_position=self.game.last_position)
                p.read_pv(rm.pv)
                if p.li_moves:
                    move0: Move.Move = p.li_moves[0]
                    p.first_position = move0.position
                    p.li_moves = p.li_moves[1:]
                    txt = p.pgn_base_raw() if self.with_figurines else p.pgn_translated()
                    return txt.lstrip("0123456789. ") if ".." in txt else txt
        return None

    def grid_doble_click(self, _grid, row, _obj_column):
        if 0 <= row < len(self.li_moves):
            rm = self.li_moves[row]
            self.game.read_pv(rm.movimiento())
            self.reset()

    def is_move_done(self, row):
        if self.is_candidates and self.kibitzer.pointofview == KIB_BEFORE_MOVE and self.cpu.last_move:
            rm = self.li_moves[row]
            movimiento = self.cpu.last_move.movimiento()
            if rm.movimiento() == movimiento:
                return True
        return False

    def grid_color_fondo(self, _grid, row, _obj_column):
        if self.is_move_done(row):
            return self.color_done
        return None

    def grid_bold(self, _grid, row, _obj_column):
        return self.is_move_done(row)

    def check_input(self):
        self.cpu.check_input()
        if self.need_refresh_data:
            self.refresh_data()

    def changed_depth_from_engine(self):
        if not self.engine_run:
            return
        if self.valid_to_play() and not self.stopped:
            self.need_refresh_data = True

    def bestmove_from_engine(self, _bestmove):
        if not self.engine_run:
            return
        if self.valid_to_play() and not self.stopped:
            self.need_refresh_data = True

    def refresh_data(self):
        self.need_refresh_data = False
        if self.stopped:
            return
        mrm = self.engine_run.mrm
        rm = mrm.rm_best()
        if rm is None:
            return
        if self.is_candidates:
            self.li_moves = mrm.li_rm
            if self.kibitzer.pointofview == KIB_BEFORE_MOVE and self.cpu.last_move:
                movimiento = self.cpu.last_move.movimiento()
                for pos, rm1 in enumerate(mrm.li_rm):
                    if rm1.movimiento() == movimiento:
                        rm = rm1
                        rm.is_done = True
                        break

            self.lbDepth.set_text("%s: %d" % (_("Depth"), rm.depth))
        else:
            self.li_moves.insert(0, rm.copia())
            if len(self.li_moves) > 256:
                self.li_moves = self.li_moves[:128]

        game = Game.Game(first_position=self.game.last_position)
        game.read_pv(rm.pv)
        if len(game):
            self.board.remove_arrows()
            tipo = "mt"
            opacity = 100
            salto = (80 - 15) * 2 // (self.nArrows - 1) if self.nArrows > 1 else 1
            cambio = max(30, salto)

            for njg in range(min(len(game), self.nArrows)):
                tipo = "ms" if tipo == "mt" else "mt"
                move = game.move(njg)
                self.board.show_arrow_mov(move.from_sq, move.to_sq, tipo, opacity=opacity / 100)
                if njg % 2 == 1:
                    opacity -= cambio
                    cambio = salto

        self.grid.refresh()

        QTUtils.refresh_gui()

    def launch_engine(self):
        if self.is_candidates:
            num_multipv = self.kibitzer.current_multipv()
            if num_multipv <= 1:
                num_multipv = min(self.kibitzer.maxMultiPV, 10)
        else:
            num_multipv = 1

        exe = self.kibitzer.path_exe
        if not Util.exist_file(exe):
            QTMessages.message_error(self, f"{_('Engine not found')}:\n  {exe}")
            sys.exit()

        self.run_engine_params = EngineRun.RunEngineParams()
        self.run_engine_params.multipv = num_multipv
        self.run_engine_params.fixed_ms = int(self.kibitzer.max_time * 1000)
        self.run_engine_params.fixed_depth = self.kibitzer.max_depth
        if self.kibitzer.max_depth == 0 and self.kibitzer.max_time == 0:
            self.run_engine_params.infinite = True
        # fixed_nodes: int = 0

        run_param = EngineRun.StartEngineParams()
        run_param.name = self.kibitzer.name
        run_param.path_exe = exe
        run_param.li_options_uci = self.kibitzer.liUCI
        run_param.args = self.kibitzer.args
        run_param.num_multipv = num_multipv
        run_param.emulate_movetime = True

        self.engine_run = EngineRun.EngineRun(run_param)
        self.engine_run.bestmove_found.connect(self.bestmove_from_engine)
        self.engine_run.depth_changed.connect(self.changed_depth_from_engine)

    def valid_to_play(self):
        if self.game is None:
            return False
        siw = self.game.last_position.is_white
        if not self.siPlay or (siw and not self.is_white) or (not siw and not self.is_black):
            return False
        return True

    def finalizar(self):
        self.save_video()
        if self.engine_run:
            self.engine_run.close()
            self.engine_run = None
            self.siPlay = False

    def portapapeles_jug_selected(self):
        if self.li_moves:
            n = self.grid.recno()
            if n < 0 or n >= len(self.li_moves):
                n = 0
            rm = self.li_moves[n]
            fen = self.game.last_position.fen()
            p = Game.Game(fen=fen)
            p.read_pv(rm.pv)
            jg0 = p.move(0)
            jg0.set_comment(f"{rm.abbrev_text_pdt()} {self.kibitzer.name}")
            pgn = p.pgn_base_raw()
            resp = f'[FEN "{fen}"]\n\n{pgn}'
            QTUtils.set_clipboard(resp)
            QTMessages.temporary_message(self, _("The line selected is saved to the clipboard"), 0.7)

    def orden_game(self, game: Game.Game):
        if game is None:
            return
        posicion = game.last_position

        is_white = posicion.is_white

        self.board.set_position(posicion)
        self.board.activate_side(is_white)

        self.game = game
        self.li_moves = []
        self.need_refresh_data = False
        self.stopped = True

        if self.valid_to_play():
            self._game_version += 1
            current_version = self._game_version
            self.engine_run.set_game_position(game, None, False)
            if current_version == self._game_version:
                self.engine_run.play(self.run_engine_params)
                self.stopped = False
        self.grid.refresh()

        self.test_tb_home()

    def pegar(self):
        tp, data = QTUtils.get_clipboard()
        if tp:
            position = Position.Position()
            if tp == "t":
                try:
                    position.read_fen(str(data))
                except:
                    return
            elif tp == "h":
                try:
                    position.read_fen(QTUtils.get_txt_clipboard())
                except:
                    return
            else:
                return
            game = Game.Game(first_position=position)
            self.orden_game(game)

            self.test_tb_home()
