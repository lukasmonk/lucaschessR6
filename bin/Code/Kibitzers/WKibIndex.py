import FasterCode
from PySide6 import QtCore, QtGui, QtWidgets

import Code
from Code.Analysis import AnalysisIndexes
from Code.Base import Game
from Code.Board import Board
from Code.Engines import EngineRun
from Code.QT import Colocacion, Columnas, Controles, Grid, Iconos, Piezas, QTDialogs, QTUtils, ScreenUtils
from Code.Voyager import Voyager


class WKibIndex(QtWidgets.QDialog):
    run_engine_params: EngineRun.RunEngineParams
    engine_run = EngineRun.EngineRun
    game: Game.Game

    def __init__(self, cpu):
        QtWidgets.QDialog.__init__(self)

        self.cpu = cpu
        self.kibitzer = cpu.kibitzer

        dic_video = self.cpu.dic_video
        if not dic_video:
            dic_video = {}

        self.siTop = dic_video.get("SITOP", True)
        self.show_board = dic_video.get("SHOW_BOARD", True)
        self.history = []

        self.fen = ""
        self.liData = []

        self.setWindowTitle(cpu.titulo)
        self.setWindowIcon(Iconos.Engine())

        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowMinimizeButtonHint
        )

        self.setBackgroundRole(QtGui.QPalette.ColorRole.Light)

        Code.all_pieces = Piezas.AllPieces()
        config_board = cpu.configuration.config_board(f"kib{cpu.kibitzer.huella}", 24)
        self.board = Board.Board(self, config_board)
        self.board.draw_window()
        self.board.set_dispatcher(self.mensajero)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("titulo", "", 120, align_right=True)
        o_columns.nueva("valor", "", 100, align_center=True)
        o_columns.nueva("info", "", 110)
        self.grid = Grid.Grid(
            self,
            o_columns,
            dic_video=dic_video,
            complete_row_select=True,
            header_visible=True,
            header_heigh=4,
        )
        f = Controles.FontType(puntos=self.cpu.configuration.x_pgn_fontpoints)
        self.grid.set_font(f)

        li_acciones = (
            (_("Continue"), Iconos.Kibitzer_Play(), self.play),
            (_("Pause"), Iconos.Kibitzer_Pause(), self.pause),
            (_("Takeback"), Iconos.Kibitzer_Back(), self.takeback),
            (_("Analyze color"), Iconos.Kibitzer_Side(), self.color),
            (_("Show/hide board"), Iconos.Kibitzer_Board(), self.config_board),
            (_("Manual position"), Iconos.Voyager(), self.set_position),
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
        )
        self.tb = Controles.TBrutina(self, li_acciones, with_text=False, icon_size=24)
        self.tb.set_action_visible(self.play, False)

        ly1 = Colocacion.H().control(self.tb).relleno()
        ly2 = Colocacion.V().otro(ly1).control(self.grid)

        layout = Colocacion.H().control(self.board).otro(ly2)
        self.setLayout(layout)

        self.siPlay = True
        self.is_white = True
        self.is_black = True

        if not self.show_board:
            self.board.hide()
        self.restore_video(dic_video)
        self.set_flags()

        self.launch_engine()
        self.need_refresh_data = False

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check_input)
        self.timer.start(200)

    def refresh_data(self):
        self.need_refresh_data = False
        mrm = self.engine_run.mrm
        if mrm.li_rm:

            cp = self.game.last_position

            self.liData = []

            def tr(xtp, xmas=""):
                porc = max(min(xtp[1], 100), 0)

                self.liData.append((xtp[0], f"{porc:.01f}%", f"{xmas}{xtp[2]}"))

            tp = AnalysisIndexes.tp_gamestage(cp, mrm)
            self.liData.append((tp[0], "%d" % tp[1], tp[2]))

            pts = mrm.li_rm[0].centipawns_abs()
            mas = ""
            if pts:
                w, b = _("White"), _("Black")
                si_w = cp.is_white
                if pts > 0:
                    mas = w if si_w else b
                elif pts < 0:
                    mas = b if si_w else w
                mas += "-"
            tr(AnalysisIndexes.tp_winprobability(cp, mrm), mas)
            tr(AnalysisIndexes.tp_complexity(cp, mrm))
            tr(AnalysisIndexes.tp_efficientmobility(cp, mrm))

            tr(AnalysisIndexes.tp_narrowness(cp, mrm))
            tr(AnalysisIndexes.tp_piecesactivity(cp, mrm))
            tr(AnalysisIndexes.tp_exchangetendency(cp, mrm))

            tp = AnalysisIndexes.tp_positionalpressure(cp, mrm)
            self.liData.append((tp[0], f"{int(tp[1])}", ""))

            tr(AnalysisIndexes.tp_materialasymmetry(cp, mrm))

            self.grid.refresh()
            self.grid.resizeRowsToContents()

        QTUtils.refresh_gui()

    def check_input(self):
        if not self.engine_run:
            return
        self.cpu.check_input()
        if self.need_refresh_data:
            self.refresh_data()

    def set_flags(self):
        flags = self.windowFlags()
        if self.siTop:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~QtCore.Qt.WindowType.WindowStaysOnTopHint
        flags |= QtCore.Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)
        self.tb.set_action_visible(self.window_top, not self.siTop)
        self.tb.set_action_visible(self.window_bottom, self.siTop)
        self.show()

    def window_top(self):
        self.siTop = True
        self.set_flags()

    def window_bottom(self):
        self.siTop = False
        self.set_flags()

    def finalize(self):
        self.finalizar()
        self.accept()

    def pause(self):
        self.siPlay = False
        self.tb.set_pos_visible(0, True)
        self.tb.set_pos_visible(1, False)
        self.stop()

    def play(self):
        self.siPlay = True
        self.tb.set_pos_visible(0, False)
        self.tb.set_pos_visible(1, True)
        self.reset()

    def stop(self):
        self.siPlay = False
        self.engine_run.stop()

    def grid_num_datos(self, _grid):
        return len(self.liData)

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        titulo, valor, info = self.liData[row]
        if key == "titulo":
            return titulo

        elif key == "valor":
            return valor

        elif key == "info":
            return info

        return None

    @staticmethod
    def grid_bold(_grid, _row, obj_column):
        return obj_column.key in ("Titulo",)

    def changed_depth_from_engine(self):
        if not self.engine_run:
            return
        if self.siPlay:
            self.need_refresh_data = True

    def bestmove_from_engine(self, _bestmove):
        if not self.engine_run:
            return
        if self.siPlay:
            self.need_refresh_data = True

    def launch_engine(self):
        self.run_engine_params = EngineRun.RunEngineParams()
        self.run_engine_params.multipv = self.kibitzer.multiPV
        self.run_engine_params.fixed_ms = int(self.kibitzer.max_time * 1000)
        self.run_engine_params.fixed_depth = self.kibitzer.max_depth
        if self.kibitzer.max_depth == 0 and self.kibitzer.max_time == 0:
            self.run_engine_params.infinite = True
        # fixed_nodes: int = 0

        run_param = EngineRun.StartEngineParams()
        run_param.name = self.kibitzer.name
        run_param.path_exe = self.kibitzer.path_exe
        run_param.li_options_uci = self.kibitzer.liUCI
        run_param.args = self.kibitzer.args
        run_param.num_multipv = 1
        run_param.emulate_movetime = True

        self.engine_run = EngineRun.EngineRun(run_param)
        self.engine_run.bestmove_found.connect(self.bestmove_from_engine)
        self.engine_run.depth_changed.connect(self.changed_depth_from_engine)

    def closeEvent(self, event):
        self.finalizar()

    def whether_to_analyse(self):
        if not self.siPlay:
            return False
        siw = self.game.last_position.is_white
        return (siw and self.is_white) or (not siw and self.is_black)

    def color(self):
        menu = QTDialogs.LCMenu(self)

        def ico(ok):
            return Iconos.Aceptar() if ok else Iconos.PuntoAmarillo()

        menu.opcion("blancas", _("White"), ico(self.is_white and not self.is_black))
        menu.opcion("negras", _("Black"), ico(not self.is_white and self.is_black))
        menu.opcion(
            "blancasnegras",
            f"{_('White')} + {_('Black')}",
            ico(self.is_white and self.is_black),
        )
        resp = menu.lanza()
        if resp:
            self.is_black = True
            self.is_white = True
            if resp == "blancas":
                self.is_black = False
            elif resp == "negras":
                self.is_white = False
            self.reset()

    def finalizar(self):
        self.siPlay = False
        self.save_video()
        if self.engine_run:
            self.engine_run.close()
            self.engine_run = None

    def save_video(self):
        dic = {}

        pos = self.pos()
        dic["_POSICION_"] = "%d,%d" % (pos.x(), pos.y())

        tam = self.size()
        dic["_SIZE_"] = "%d,%d" % (tam.width(), tam.height())

        dic["SHOW_BOARD"] = self.show_board

        dic["SITOP"] = self.siTop

        self.grid.save_video(dic)

        self.cpu.save_video(dic)

    def restore_video(self, dic_video):
        if dic_video:
            w_e, h_e = ScreenUtils.desktop_size()
            x, y = dic_video["_POSICION_"].split(",")
            x = int(x)
            y = int(y)
            if not (0 <= x <= (w_e - 50)):
                x = 0
            if not (0 <= y <= (h_e - 50)):
                y = 0
            self.move(x, y)
            if "_SIZE_" not in dic_video:
                w, h = self.width(), self.height()
                for k in dic_video:
                    if k.startswith("_TAMA"):
                        w, h = dic_video[k].split(",")
            else:
                w, h = dic_video["_SIZE_"].split(",")
            w = int(w)
            h = int(h)
            if w > w_e:
                w = w_e
            elif w < 20:
                w = 20
            if h > h_e:
                h = h_e
            elif h < 20:
                h = 20
            self.resize(w, h)

    def orden_game(self, game):
        self.game = game
        self.siPlay = False
        if game is None:
            return
        position = game.last_position
        self.is_white = position.is_white
        self.board.set_position(position)
        self.board.activate_side(self.is_white)

        if position.is_white:
            if not self.is_white:
                self.liData = []
                self.grid.refresh()
                return
        else:
            if not self.is_black:
                self.liData = []
                self.grid.refresh()
                return

        self.siPlay = True

        self.engine_run.set_game_position(game, None, False)
        self.engine_run.play(self.run_engine_params)

    def orden_game_original(self, game):
        self.orden_game(game)

    def config_board(self):
        self.show_board = not self.show_board
        self.board.setVisible(self.show_board)
        self.save_video()

    def takeback(self):
        nmoves = len(self.game)
        if nmoves:
            self.game.shrink(nmoves - 2)
            self.orden_game(self.game)

    def mensajero(self, from_sq, to_sq, promocion=""):
        FasterCode.set_fen(self.game.last_position.fen())
        if FasterCode.make_move(from_sq + to_sq + promocion):
            self.game.read_pv(from_sq + to_sq + promocion)
            self.reset()

    def set_position(self):
        position, is_white_bottom = Voyager.voyager_position(self, self.game.last_position)
        if position is not None:
            game = Game.Game(first_position=position)
            self.orden_game(game)

    def reset(self):
        self.orden_game(self.game)
