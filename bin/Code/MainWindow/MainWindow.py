from PySide6 import QtCore, QtGui, QtWidgets

import Code
from Code.Base.Constantes import TB_CANCEL, TB_CLOSE, TB_QUIT, TB_STOP, TB_TUTOR_STOP
from Code.Board import Eboard
from Code.MainWindow import WBase, WInformation
from Code.QT import Colocacion, Iconos, LCDialog, QTUtils, ScreenUtils
from Code.Translations import WorkTranslate


class MainWindow(LCDialog.LCDialog):
    signal_notify = QtCore.Signal()
    signal_routine_connected = None
    dato_notify = None

    def __init__(self, manager, owner=None, extparam=None):
        self.manager = manager

        titulo = ""
        icono = Iconos.Aplicacion64()
        extparam = extparam if extparam else "maind"
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, extparam)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self.owner = owner
        if owner is None:
            Code.main_window = self

        self.base = WBase.WBase(self, manager)

        self.siCapturas = False
        self.pgn_information = WInformation.Information(self)
        self.siInformacionPGN = False
        self.pgn_information.hide()
        self.register_splitter(self.pgn_information.splitter, "InformacionPGN")
        self.with_analysis_bar = False
        self.base.analysis_bar.hide()

        self.timer = None
        self.siTrabajando = False

        self.cursorthinking = QtGui.QCursor(
            Iconos.pmThinking() if self.manager.configuration.x_cursor_thinking else QtCore.Qt.CursorShape.BlankCursor
        )
        self.cursorthinking_rival = QtGui.QCursor(Iconos.pmConnected())
        self.onTop = False

        self.board = self.base.board
        self.board.set_dispatch_size(self.adjust_size)
        self.board.allowed_extern_resize(True)
        self.anchoAntesMaxim = None
        self.resizing = False

        self.splitter = splitter = QtWidgets.QSplitter(self)
        splitter.addWidget(self.base)
        splitter.addWidget(self.pgn_information)

        ly = Colocacion.H().control(splitter).margen(0)

        self.setLayout(ly)

        ctrl1: QtGui.QShortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+1"), self)
        ctrl1.activated.connect(self.pressed_shortcut_ctrl1)

        ctrl2: QtGui.QShortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+2"), self)
        ctrl2.activated.connect(self.pressed_shortcut_ctrl2)

        alt_a: QtGui.QShortcut = QtGui.QShortcut(QtGui.QKeySequence("Alt+A"), self)
        alt_a.activated.connect(self.pressed_shortcut_alt_a)

        ctrl_0: QtGui.QShortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+0"), self)
        ctrl_0.activated.connect(self.pressed_shortcut_ctrl0)

        alt_m: QtGui.QShortcut = QtGui.QShortcut(QtGui.QKeySequence("Alt+M"), self)
        alt_m.activated.connect(self.pressed_shortcut_alt_m)

        f11: QtGui.QShortcut = QtGui.QShortcut(QtGui.QKeySequence("F11"), self)
        f11.activated.connect(self.pressed_shortcut_f11)
        self.activadoF11 = False
        self.previous_f11_maximized = False

        if QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            f12: QtGui.QShortcut = QtGui.QShortcut(QtGui.QKeySequence("F12"), self)
            f12.activated.connect(self.pressed_shortcut_f12)
            self.trayIcon = None

        self.cursor_pensando = False

        self.work_translate = None

    def set_notify(self, routine):
        if self.signal_routine_connected:
            self.signal_notify.disconnect(self.signal_routine_connected)
        self.signal_notify.connect(routine)
        self.signal_routine_connected = routine

    def notify(self, dato):
        self.dato_notify = dato
        self.signal_notify.emit()

    def closeEvent(self, event):
        li_acciones = self.base.get_toolbar()
        if TB_QUIT in li_acciones:
            Code.procesador.run_action(TB_QUIT)
            return

        event.ignore()
        if self.manager is not None:
            for elem_tb in (TB_CLOSE, TB_CANCEL, TB_STOP, TB_TUTOR_STOP):
                if elem_tb in li_acciones and self.is_enabled_option_toolbar(elem_tb):
                    self.manager.run_action(elem_tb)
                    return
        self.accept()

    def on_top_window(self):
        self.onTop = not self.onTop
        self.muestra()

    def activate_tray_icon(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_tray_icon()

    def restore_tray_icon(self):
        self.showNormal()
        self.trayIcon.hide()

    def quit_tray_icon(self):
        self.trayIcon.hide()
        self.final_processes()
        self.accept()

    def pressed_shortcut_f12(self):
        if not self.trayIcon:
            restore_action: QtGui.QAction = QtGui.QAction(
                Iconos.PGN(), _("Show"), self, triggered=self.restore_tray_icon
            )
            quit_action: QtGui.QAction = QtGui.QAction(
                Iconos.Terminar(), _("Quit"), self, triggered=self.quit_tray_icon
            )
            tray_icon_menu = QtWidgets.QMenu(self)
            tray_icon_menu.addAction(restore_action)
            tray_icon_menu.addSeparator()
            tray_icon_menu.addAction(quit_action)

            self.trayIcon: QtWidgets.QSystemTrayIcon = QtWidgets.QSystemTrayIcon(self)
            self.trayIcon.setContextMenu(tray_icon_menu)
            self.trayIcon.setIcon(Iconos.Aplicacion64())
            self.trayIcon.activated.connect(self.activate_tray_icon)
            self.trayIcon.hide()

        if self.trayIcon:
            self.trayIcon.show()
            self.hide()

    def pressed_shortcut_f11(self):
        self.activadoF11 = not self.activadoF11
        if self.activadoF11:
            if self.siInformacionPGN:
                self.pgn_information.save_width_parent()
            self.showFullScreen()
        else:
            self.showNormal()
            if self.siInformacionPGN:
                self.pgn_information.restore_width()

    def final_processes(self):
        self.stop_clock()
        self.board.close_visual_script()
        self.board.finalize()

        if self.work_translate:
            self.work_translate.close()

        if hasattr(Code, "procesador") and Code.procesador:
            Code.procesador.close_engines()
            if hasattr(Code.procesador, "kibitzers_manager"):
                Code.procesador.kibitzers_manager.close()

        if hasattr(Code, "garbage_collector") and Code.garbage_collector:
            Code.garbage_collector.stop()

    def set_manager_active(self, manager):
        self.manager = manager
        self.base.set_manager_active(manager)

    def muestra(self):
        flags = QtCore.Qt.WindowType.Dialog if self.owner else QtCore.Qt.WindowType.Widget
        flags |= (
            QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowMinimizeButtonHint
            | QtCore.Qt.WindowType.WindowMaximizeButtonHint
        )
        if self.onTop:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        # flags &= ~QtCore.Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowCloseButtonHint | flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_AlwaysShowToolTips, self.onTop)
        if self.board.is_maximized():
            self.showMaximized()
        else:
            self.xrestore_video()
            self.adjust_size()
            self.show()

        self.set_title()

    def save_width_piece(self):
        ct = self.board.config_board
        if ct.width_piece() != 1000:
            dic = Code.configuration.read_variables("WIDTH_PIEZES")
            dic["WIDTH_PIEZE_MAIN"] = ct.width_piece()
            Code.configuration.write_variables("WIDTH_PIEZES", dic)

    @staticmethod
    def restore_width_pieze():
        dic = Code.configuration.read_variables("WIDTH_PIEZES")
        return dic.get("WIDTH_PIEZE_MAIN")

    def changeEvent(self, event):
        QtWidgets.QWidget.changeEvent(self, event)
        if event.type() != QtCore.QEvent.Type.WindowStateChange:
            return

        nue = ScreenUtils.EstadoWindow(self.windowState())
        ant = ScreenUtils.EstadoWindow(event.oldState())

        if getattr(self.manager, "siPresentacion", False):
            self.manager.presentacion(False)

        if nue.fullscreen:
            self.previous_f11_maximized = ant.maximizado
            self.base.tb.hide()
            self.board.siF11 = True
            self.save_width_piece()
            self.board.maximize_size(True)
        else:
            if ant.fullscreen:
                self.base.tb.show()
                self.board.normal_size(self.restore_width_pieze())
                self.adjust_size()
                if self.previous_f11_maximized:
                    self.setWindowState(QtCore.Qt.WindowState.WindowMaximized)
            elif nue.maximizado:
                self.save_width_piece()
                self.board.maximize_size(False)
            elif ant.maximizado:
                self.board.normal_size(self.restore_width_pieze())
                self.adjust_size()

    def show_variations(self, titulo):
        flags = (
            QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowMinimizeButtonHint
            | QtCore.Qt.WindowType.WindowMaximizeButtonHint
        )

        self.setWindowFlags(QtCore.Qt.WindowType.WindowCloseButtonHint | flags)

        self.setWindowTitle(titulo if titulo else "-")

        # self.restore_main_window()
        self.adjust_size()

        resp = self.exec()
        # try:
        #     self.save_video()
        # except RuntimeError:
        #     pass
        return resp

    def adjust_size(self):
        def adjust():
            if self.resizing:
                return
            self.resizing = True
            if self.isMaximized():
                if not self.board.is_maximized():
                    self.board.maximize_size(self.activadoF11)
            else:
                # if not self.activadoF11:
                #     ScreenUtils.shrink(self)
                tb_height = self.base.tb.height() if Code.configuration.x_tb_orientation_horizontal else 0
                n = 0
                while self.height() > self.board.ancho + tb_height + 18:
                    self.adjustSize()
                    self.refresh()
                    n += 1
                    if n > 3:
                        break
            self.refresh()
            self.resizing = False

        QtCore.QTimer.singleShot(15, adjust)

    def _adjust_tamh(self):
        if not (self.isMaximized() or self.board.siF11):
            for n in range(3):
                self.adjustSize()
                self.refresh()
        self.refresh()

    def set_title(self):
        self.setWindowTitle(f"{Code.lucas_chess} {Code.VERSION}")

    def set_label1(self, label):
        return self.base.set_label1(label)

    def set_label2(self, label):
        return self.base.set_label2(label)

    def set_label3(self, label):
        return self.base.set_label3(label)

    def set_hight_label3(self, px):
        return self.base.set_hight_label3(px)

    def get_labels(self):
        return self.base.get_labels()

    def set_white_black(self, white=None, black=None):
        self.base.set_white_black(white, black)

    def set_activate_tutor(self, ok):
        self.base.set_activate_tutor(ok)

    def pon_toolbar(self, li_acciones, separator=True, shortcuts=False, with_eboard=False):
        return self.base.pon_toolbar(li_acciones, separator, shortcuts, with_eboard=with_eboard)

    def get_toolbar(self):
        return self.base.get_toolbar()

    def toolbar_enable(self, ok):
        self.base.tb.setEnabled(ok)

    def set_hints(self, puntos, with_takeback=True):
        self.base.set_hints(puntos, with_takeback)

    def show_button_tutor(self, ok):
        self.base.show_button_tutor(ok)

    def remove_hints(self, also_tutor_back, with_takeback=True):
        self.base.remove_hints(also_tutor_back, with_takeback)

    def enable_option_toolbar(self, opcion, enable):
        self.base.enable_option_toolbar(opcion, enable)

    def show_option_toolbar(self, opcion, must_show):
        self.base.show_option_toolbar(opcion, must_show)

    def is_enabled_option_toolbar(self, opcion):
        return self.base.is_enabled_option_toolbar(opcion)

    def set_title_toolbar_eboard(self):
        self.base.set_title_toolbar_eboard()

    def pgn_refresh(self, is_white):
        self.base.pgn_refresh()
        self.base.pgn.gobottom(2 if is_white else 1)

    def place_on_pgn_table(self, fil, is_white):
        col = 1 if is_white else 2
        self.base.pgn.goto(fil, col)

    def pgn_pos_actual(self):
        return self.base.pgn.current_position()

    def hide_pgn(self):
        self.base.pgn.hide()

    def show_pgn(self):
        self.base.pgn.show()

    def refresh(self):
        self.update()
        QTUtils.refresh_gui()

    def activate_captures(self, activate=None):
        if activate is None:
            self.siCapturas = not self.siCapturas
            Code.configuration.x_captures_activate = self.siCapturas
            Code.configuration.graba()
        else:
            self.siCapturas = activate
        self.base.lb_capt_white.setVisible(self.siCapturas)
        self.base.lb_capt_black.setVisible(self.siCapturas)
        self.base.bt_capt.setVisible(self.siCapturas)

    def active_information_pgn(self, activate=None):
        if activate is None:
            self.siInformacionPGN = not self.siInformacionPGN
            Code.configuration.x_info_activate = self.siInformacionPGN
            Code.configuration.graba()
        else:
            self.siInformacionPGN = activate

        self.pgn_information.activate(self.siInformacionPGN)
        sizes = self.pgn_information.splitter.sizes()
        for n, size in enumerate(sizes):
            if size == 0:
                sizes[n] = 100
                self.pgn_information.splitter.setSizes(sizes)
                break
        if not self.siInformacionPGN:
            self._adjust_tamh()

    def put_captures(self, dic):
        self.base.put_captures(dic)

    def put_information_pgn(self, game, move, opening):
        self.pgn_information.set_move(game, move, opening)

    def active_game(self, si_activar, si_reloj):
        self.base.active_game(si_activar, si_reloj)
        if not self.board.siF11:
            if not self.siInformacionPGN:
                self._adjust_tamh()

    def set_data_clock(self, bl, rb, ng, rn):
        self.base.set_data_clock(bl, rb, ng, rn)

    def set_clock_white(self, tm, tm2):
        self.base.set_clock_white(tm, tm2)

    def set_clock_black(self, tm, tm2):
        self.base.set_clock_black(tm, tm2)

    def hide_clock_white(self):
        self.base.hide_clock_white()

    def hide_clock_black(self):
        self.base.hide_clock_black()

    def change_player_labels(self, bl, ng):
        self.base.change_player_labels(bl, ng)

    def start_clock(self, enlace, transicion=100):
        if self.timer is not None:
            self.timer.stop()
            del self.timer

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(enlace)
        self.timer.start(transicion)

    def stop_clock(self):
        if self.timer is not None:
            self.timer.stop()
            del self.timer
            self.timer = None

    def columnas60(self, activate, label_level=None, label_white=None, label_black=None):
        self.base.columnas60(activate, label_level, label_white, label_black)

    def pressed_shortcut_alt_a(self):
        if self.manager and hasattr(self.manager, "alt_a"):
            self.manager.alt_a()

    def pressed_shortcut_ctrl2(self):
        if self.manager and hasattr(self.manager, "control2"):
            self.manager.control2()

    def pressed_shortcut_ctrl1(self):
        if self.manager and hasattr(self.manager, "control1"):
            self.manager.control1()

    def pressed_shortcut_ctrl0(self):
        if self.manager and hasattr(self.manager, "control0"):
            self.manager.control0()

    def pressed_shortcut_alt_m(self):
        if self.manager and hasattr(self.manager, "arbol"):
            self.manager.arbol()

    def cursor_out_board(self):
        p = self.mapToParent(self.board.pos())
        p.setX(p.x() + self.board.ancho + 4)

        QtGui.QCursor.setPos(p)

    def thinking(self, si_pensando):
        if si_pensando:
            if not self.cursor_pensando:
                QtWidgets.QApplication.setOverrideCursor(self.cursorthinking_rival)
        else:
            if self.cursor_pensando:
                QtWidgets.QApplication.restoreOverrideCursor()
        self.cursor_pensando = si_pensando
        self.refresh()

    def pensando_tutor(self, si_pensando):
        if si_pensando:
            if not self.cursor_pensando:
                QtWidgets.QApplication.setOverrideCursor(self.cursorthinking)
        else:
            if self.cursor_pensando:
                QtWidgets.QApplication.restoreOverrideCursor()
        self.cursor_pensando = si_pensando
        self.refresh()

    def save_video(self, dic_extended=None):
        dic = {} if dic_extended is None else dic_extended

        pos = self.pos()
        dic["_POSICION_"] = "%d,%d" % (pos.x(), pos.y())

        tam = self.size()
        dic["_SIZE_"] = "%d,%d" % (tam.width(), tam.height())

        for grid in self.liGrids:
            grid.save_video(dic)

        for sp, name in self.liSplitters:
            sps = sp.sizes()
            key = f"SP_{name}"
            if name == "InformacionPGN" and sps[1] == 0:
                sps = self.pgn_information.sp_sizes
                if sps is None or sps[1] == 0:
                    dr = self.restore_dicvideo()
                    if dr and key in dr:
                        dic[key] = dr[key]
                        continue
                    sps = [1, 1]
            dic[f"SP_{name}"] = sps

        dic["WINFO_WIDTH"] = self.pgn_information.width_saved
        dic["WINFOPARENT_WIDTH"] = self.pgn_information.parent_width_saved
        Code.configuration.save_video(self.key_video, dic)
        return dic

    def xrestore_video(self):
        if self.restore_video():
            dic = self.restore_dicvideo()
            self.pgn_information.width_saved = dic.get("WINFO_WIDTH")
            if self.pgn_information.width_saved:
                self.pgn_information.resize(self.pgn_information.width_saved, self.pgn_information.height())
            self.pgn_information.parent_width_saved = dic.get("WINFOPARENT_WIDTH")
            self.pgn_information.sp_sizes = dic.get("SP_InformacionPGN")
            if self.pgn_information.sp_sizes:
                try:
                    self.pgn_information.splitter.setSizes(self.pgn_information.sp_sizes)
                except TypeError:
                    pass

    def check_translated_help_mode(self):
        if not Code.configuration.x_translation_mode:
            return

        self.work_translate = WorkTranslate.launch_wtranslation()

        QtCore.QTimer.singleShot(3000, self.check_translated_received)

    def check_translated_received(self):
        salto = 500 if self.work_translate.pending_commit else 1000

        if self.work_translate.check_commits():
            QtCore.QTimer.singleShot(salto, self.check_translated_received)

    def deactivate_eboard(self, ms=500):
        if Code.eboard and Code.eboard.driver:

            def deactive():
                Code.eboard.deactivate()
                self.set_title_toolbar_eboard()
                del Code.eboard
                Code.eboard = Eboard.Eboard()

            if ms > 0:
                QtCore.QTimer.singleShot(ms, deactive)
            else:
                deactive()

    @staticmethod
    def delay_routine(ms, routine):
        QtCore.QTimer.singleShot(ms, routine)

    def activate_analysis_bar(self, ok):
        self.with_analysis_bar = ok
        self.base.analysis_bar.activate(ok)

    def run_analysis_bar(self, game):
        if self.with_analysis_bar:
            self.base.analysis_bar.set_game(game)

    def bestmove_from_analysis_bar(self):
        if self.with_analysis_bar:
            return self.base.analysis_bar.current_bestmove()
        return None

    def end_think_analysis_bar(self):
        if self.with_analysis_bar:
            self.base.analysis_bar.end_think()

    def is_active_information_pgn(self):
        return self.pgn_information.isVisible()

    def is_active_captures(self):
        return self.siCapturas

    def is_active_analysisbar(self):
        return self.with_analysis_bar

    def get_noboard_width(self):
        return self.base.analysis_bar.width() + self.pgn_information.width() + Code.configuration.x_pgn_width
