import sys

from PySide6 import QtCore, QtWidgets

import Code
from Code.Z import Util
from Code.Base import Game, Move
from Code.Engines import EngineRun
from Code.Kibitzers import WindowKibitzers
from Code.QT import Colocacion, Controles, Iconos, QTDialogs, QTMessages, ScreenUtils


class ResizeHandle(QtWidgets.QWidget):
    """Zona visible para redimensionar a lo ancho."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedWidth(5)
        self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)


class DragHandle(QtWidgets.QLabel):
    """Handle visual para arrastrar la ventana."""

    def __init__(self, parent):
        super().__init__("", parent)  # Sin texto
        self.parent_window = parent
        self._drag_pos = None
        self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        self.setStyleSheet("QLabel { background-color: transparent; }")
        self.setToolTip(_("Drag to move window"))

        # Ancho fijo para el área de arrastre
        self.setFixedWidth(8)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


class WrapperWidget(QtWidgets.QWidget):
    def mousePressEvent(self, event):
        event.ignore()


class WKibLine(QtWidgets.QMainWindow):
    siMover: bool
    run_engine_params: EngineRun.RunEngineParams
    engine_run = EngineRun.EngineRun

    def __init__(self, cpu):
        super().__init__()

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)

        wrapper = QtWidgets.QWidget()
        wrapper.setObjectName("wrapper")
        wrapper.setStyleSheet(
            """
            #wrapper {
                background-color: palette(light);
                border-radius: 4px;
                border: 1px solid palette(mid);
            }
        """
        )
        self.setCentralWidget(wrapper)

        self.cpu = cpu
        self.kibitzer = cpu.kibitzer

        self._drag_pos: QtCore.QPoint | None = None
        self._resizing = False

        dic_video = self.cpu.dic_video
        if not dic_video:
            dic_video = {}

        self.siTop = dic_video.get("SITOP", True)

        self.game = None
        self.setWindowIcon(Iconos.Kibitzer())

        f = Controles.FontType(puntos=self.cpu.configuration.x_pgn_fontpoints)
        self.setFont(f)

        def add_bt(tooltip, icon, rutine):
            bt = Controles.PB(self, "", rutine, True).set_icono(icon, 24)
            bt.setToolTip(tooltip)
            bt.setFixedWidth(26)
            return bt

        bt_quit = add_bt(_("Quit"), Iconos.Kibitzer_Close(), self.finalize)
        self.bt_continue = add_bt(_("Continue"), Iconos.Kibitzer_Play(), self.play)
        self.bt_pause = add_bt(_("Pause"), Iconos.Kibitzer_Pause(), self.pause)
        bt_side = add_bt(_("Analyze color"), Iconos.Kibitzer_Side(), self.color)
        self.bt_top = add_bt(f'{_("Enable")}: {_("window on top")}', Iconos.Pin(), self.window_top)
        self.bt_bottom = add_bt(f'{_("Disable")}: {_("window on top")}', Iconos.Unpin(), self.window_bottom)
        bt_options = add_bt(_("Options"), Iconos.Opciones(), self.change_options)

        self.em = Controles.EM(self)
        self.em.setFont(f)
        self.em.setReadOnly(True)
        px = ScreenUtils.get_height_text(self.em, "N")
        self.em.setFixedHeight(px + 6)
        self.setFixedHeight(px + 14)
        self.em.verticalScrollBar().hide()
        self.lb_depth = Controles.LB(self, "")
        self.lb_depth.set_font(f)

        self.handle = ResizeHandle(self)
        self.handle.mousePressEvent = self._handle_press
        self.handle.mouseMoveEvent = self._handle_move
        self.handle.mouseReleaseEvent = self._handle_release

        sp = -6
        self.drag_handle = DragHandle(self)

        layout = (
            Colocacion.H()
            .espacio(3)
            .control(self.lb_depth)
            .control(self.em)
            .control(self.drag_handle)
            .control(self.bt_continue)
            .control(self.bt_pause)
            .espacio(sp)
            .control(bt_side)
            .espacio(sp)
            .control(self.bt_top)
            .control(self.bt_bottom)
            .espacio(sp)
            .control(bt_options)
            .espacio(sp)
            .control(bt_quit)
            .espacio(sp)
            .control(self.handle)
            .margen(2)
        )
        wrapper.setLayout(layout)

        self.bt_continue.hide()

        self.launch_engine()

        self.siPlay = True
        self.is_white = True
        self.is_black = True

        self.restore_video(dic_video)

        self.set_flags()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check_input)
        self.timer.start(200)

        self.need_refresh_data = False  # Se mira cada 200ms en check_input también, para que no se acumule

        self.stopped = False

    def refresh_data(self):
        self.need_refresh_data = False
        if self.valid_to_play():
            pgn = ""
            cdepth = ""
            mrm = self.engine_run.mrm
            rm = mrm.rm_best()
            if rm is None:
                return
            game = Game.Game(first_position=self.game.last_position)
            game.read_pv(rm.pv)
            if len(game):
                move: Move.Move = game.move(0)
                move.add_comment(rm.abbrev_text())
                pgn = game.pgn_base_raw()
                if Code.configuration.x_pgn_withfigurines:
                    d = Move.dicHTMLFigs
                    lc = []
                    is_white = pgn[0].isdigit()
                    for c in pgn:
                        if c == " ":
                            is_white = not is_white
                        else:
                            if c.isupper():
                                c = d.get(c if is_white else c.lower(), c)
                        lc.append(c)
                    pgn = "".join(lc)

                # pgn = f"{rm.depth:02d}: {pgn}"
                cdepth = f"<small>{rm.depth:02d}</small>"

            self.em.set_html(pgn)
            self.lb_depth.set_text(cdepth)

        self.cpu.check_input()

    def change_options(self):
        self.pause()
        w = WindowKibitzers.WKibitzerLive(self, self.cpu.configuration, self.cpu.num_kibitzer)
        if w.exec():
            self.kibitzer = self.cpu.reset_kibitzer()
            self.engine_run.close()
            self.launch_engine()
            self.cpu.reprocesa()
        self.play()

    def set_flags(self):
        flags = QtCore.Qt.WindowType.FramelessWindowHint
        if self.siTop:
            self.bt_top.hide()
            self.bt_bottom.show()
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        else:
            self.bt_top.show()
            self.bt_bottom.hide()

        self.setWindowFlags(flags)
        self.show()

    def window_top(self):
        self.siTop = True
        self.set_flags()

    def window_bottom(self):
        self.siTop = False
        self.set_flags()

    def finalize(self):
        self.finalizar()
        self.close()

    def pause(self):
        self.siPlay = False
        self.bt_pause.hide()
        self.bt_continue.show()
        self.stop()

    def play(self):
        self.siPlay = True
        self.bt_pause.show()
        self.bt_continue.hide()
        self.reset()

    def stop(self):
        self.siPlay = False
        self.engine_run.stop()

    def launch_engine(self):
        exe = self.kibitzer.path_exe
        if not Util.exist_file(exe):
            QTMessages.message_error(self, f"{_('Engine not found')}:\n  {exe}")
            sys.exit()

        self.run_engine_params = EngineRun.RunEngineParams()
        self.run_engine_params.multipv = self.kibitzer.multiPV
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
        run_param.num_multipv = 1
        run_param.emulate_movetime = True

        self.engine_run = EngineRun.EngineRun(run_param)
        self.engine_run.bestmove_found.connect(self.bestmove_from_engine)
        self.engine_run.depth_changed.connect(self.changed_depth_from_engine)

    def closeEvent(self, event):
        self.finalizar()

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

    def whether_to_analyse(self):
        si_w = self.game.last_position.is_white
        if not self.siPlay or (si_w and (not self.is_white)) or (not si_w and not self.is_black):
            return False
        return True

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
            self.orden_game(self.game)

    def finalizar(self):
        self.save_video()
        if self.engine_run:
            self.engine_run.close()
            self.engine_run = None
            self.siPlay = False
            self.stopped = True

    def save_video(self):
        dic = {}

        pos = self.pos()
        dic["_POSICION_"] = "%d,%d" % (pos.x(), pos.y())

        tam = self.size()
        dic["_SIZE_"] = "%d,%d" % (tam.width(), tam.height())

        dic["SITOP"] = self.siTop

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

    def orden_game(self, game: Game.Game):
        if game is None:
            return

        self.game = game
        if self.valid_to_play():
            self.engine_run.set_game_position(game, None, False)
            self.engine_run.play(self.run_engine_params)
            self.stopped = False

    def orden_game_original(self, game: Game.Game):
        self.orden_game(game)

    def valid_to_play(self):
        if self.game is None:
            return False
        siw = self.game.last_position.is_white
        if not self.siPlay or (siw and not self.is_white) or (not siw and not self.is_black):
            return False
        return True

    def reset(self):
        self.orden_game(self.game)

    # ------------------------------------------------------------------
    # Grab-handle: redimensionar con arrastre
    # ------------------------------------------------------------------
    def _handle_press(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._resizing = True
            self._resize_start_x = event.globalPosition().toPoint().x()
            self._initial_width = self.width()

    def _handle_move(self, event):
        if self._resizing:
            delta = event.globalPosition().toPoint().x() - self._resize_start_x
            new_width = max(self.minimumWidth(), self._initial_width + delta)
            self.resize(new_width, self.height())

    def _handle_release(self, _event):
        self._resizing = False

    # ------------------------------------------------------------------
    # Movimiento de la ventana
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
