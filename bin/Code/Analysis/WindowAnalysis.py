import contextlib

from PySide6 import QtCore, QtWidgets

import Code
from Code.Analysis import Analysis, WindowAnalysisParam
from Code.Base import Game, Move
from Code.Board import Board
from Code.Engines import EngineManagerAnalysis
from Code.QT import (
    Colocacion,
    Columnas,
    Controles,
    Delegados,
    Grid,
    Iconos,
    LCDialog,
    QTDialogs,
    QTMessages,
    QTUtils,
    ScreenUtils,
)
from Code.Z import Util, XRun


class OneAnalysis(QtWidgets.QWidget):
    """Widget for a single analysis panel (one engine / one line).

    Multiple instances can appear side-by-side inside WAnalisis.
    Each panel shows:
      - the engine name and time control
      - a grid of candidate moves (best lines)
      - navigation controls via keyboard / toolbar actions
    """

    def __init__(self, owner, tab_analysis):
        super().__init__(owner)

        self.tab_analysis = tab_analysis
        self.owner = owner
        self.board = owner.board

        # Labels shared with the parent window
        self.lbPuntuacion = owner.lbPuntuacion
        self.lb_engine = owner.lb_engine
        self.lb_time = owner.lb_time
        self.lbPGN = owner.lbPGN

        # Candidate moves: list of (rm, display_name, centipawns)
        self.list_rm_name = tab_analysis.list_rm_name

        self.is_timed_active = False
        self._color_active = {True: "blue", False: "grey"}
        self.color_negative = ScreenUtils.qt_color_rgb(255, 0, 0)
        self.color_odd_row = ScreenUtils.qt_color_rgb(231, 244, 254)

        self._build_header_labels(tab_analysis)
        self._build_candidate_grid(tab_analysis)
        self._build_layout()

        self.wrm.setFocus()

    def _build_header_labels(self, tab_analysis):
        self.time_engine = tab_analysis.time_engine()
        self.time_label = tab_analysis.time_label()

        self.lb_engine_m = (
            Controles.LB(self, self.time_engine).align_center().set_font_type(peso=75).set_wrap()
        )
        self.lb_tiempo_m = Controles.LB(self, self.time_label).align_center().set_font_type(puntos=9, peso=75)
        self.bt_remove = Controles.PB(self, "", self.remove).set_icono(Iconos.X())

    def _build_candidate_grid(self, tab_analysis):
        configuration = Code.configuration
        self.with_figurines = configuration.x_pgn_withfigurines
        col_width = (configuration.x_pgn_width - 52 - 12) // 2

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva(
            "JUGADAS",
            f"{len(self.list_rm_name)} {_('Movements')}",
            col_width,
            align_center=True,
            edicion=Delegados.EtiquetaPGN(
                tab_analysis.move.is_white() if self.with_figurines else None,
                si_indicador_inicial=False,
            ),
        )
        self.wrm = Grid.Grid(self, o_columns, with_lines=False)
        self.wrm.fix_min_width()
        self.wrm.goto(self.tab_analysis.pos_selected, 0)

    def _build_layout(self):
        row_time = Colocacion.H().relleno().control(self.lb_tiempo_m).relleno().control(self.bt_remove)
        layout = Colocacion.V().control(self.lb_engine_m).otro(row_time).control(self.wrm).margen(3)
        self.setLayout(layout)

    # -- Activation / deactivation ---------------------------------------------

    def activate(self, is_active: bool):
        """Highlight this panel (blue) when active, dim it (grey) when inactive."""
        color = self._color_active[is_active]
        self.lb_engine_m.set_foreground(color)
        self.lb_tiempo_m.set_foreground(color)
        self.bt_remove.setVisible(not is_active)
        self.is_timed_active = False

        if is_active:
            self.lb_engine.set_text(self.time_engine)
            self.lb_time.set_text(self.time_label)

    def remove(self):
        """Remove this analysis panel from the parent window."""
        self.owner.remove_analysis(self.tab_analysis)

    # -- Move selection and board refresh --------------------------------------

    def select_candidate(self, row):
        """Select a candidate move by grid row and update the board."""
        self.tab_analysis.set_pos_rm_active(row)
        self.lbPuntuacion.set_text(self.tab_analysis.score_active_depth())
        self._refresh_board()

    def change_pos_active(self, pos):
        """Navigate to a specific position within the active variation."""
        self.tab_analysis.set_pos_mov_active(pos)
        self._refresh_board()

    def _refresh_board(self):
        """Sync the board, arrow, and PGN label with the current active position."""
        position, from_sq, to_sq = self.tab_analysis.activate_position()
        self.board.set_position(position)
        self.board.activate_side(position.is_white)
        if from_sq:
            self.board.put_arrow_sc(from_sq, to_sq)
        self.lbPGN.set_text(self.tab_analysis.pgn_active())
        QTUtils.refresh_gui()

    # -- Grid callbacks (called by the Grid widget) ----------------------------

    def grid_num_datos(self, _grid):
        return len(self.list_rm_name)

    def grid_left_button(self, _grid, row, _column):
        self.select_candidate(row)
        self.owner.activate_analysis(self.tab_analysis)

    def grid_right_button(self, _grid, row, _column, _modificadores):
        self.select_candidate(row)

    def grid_bold(self, _grid, row, _column):
        return self.tab_analysis.is_selected(row)

    def grid_dato(self, _grid, row, _obj_column):
        # Cell format: "Nf3 (0.35/12)" → split into move text and analysis score
        text = self.list_rm_name[row][1]
        if "(" in text:
            pgn, rest = text.split("(")
            analysis = rest[:-1]  # strip closing ')'
        else:
            pgn, analysis = text, ""
        # Returns (pgn, color, analysis_text, indicator, nags) for the cell renderer
        return pgn, None, analysis, None, None

    def grid_color_texto(self, _grid, row, _obj_column):
        rm = self.list_rm_name[row][0]
        return None if rm.centipawns_abs() >= 0 else self.color_negative

    def grid_color_fondo(self, _grid, row, _obj_column):
        return self.color_odd_row if row % 2 == 1 else None

    # -- Navigation within the candidate list ----------------------------------

    def grid_wheel_event(self, ogrid, forward):
        self._go_to(ogrid.recno() + (-1 if forward else +1))

    def _go_to(self, row):
        if 0 <= row < len(self.list_rm_name):
            self.wrm.goto(row, 0)
            self.select_candidate(row)
            self.owner.activate_analysis(self.tab_analysis)

    def go_up(self):
        self._go_to(self.wrm.recno() - 1)

    def go_down(self):
        self._go_to(self.wrm.recno() + 1)

    def go_first(self):
        self._go_to(0)

    def go_last(self):
        self._go_to(len(self.list_rm_name) - 1)

    # -- Toolbar / keyboard actions --------------------------------------------

    def process_toolbar(self, action):
        """Handle an action dispatched by the parent WAnalisis.

        ``action`` has the form ``"move_<verb>"``; the "move_" prefix is
        stripped before routing so the verbs match what tab_analysis expects.
        """
        verb = action[5:]  # strip "move_" prefix
        if verb in ("forward", "back", "to_beginning", "to_end"):
            self.tab_analysis.change_mov_active(verb)
            self._refresh_board()
        elif verb == "timed":
            self._toggle_timed_playback()
        elif verb == "save":
            self._save_dialog()
        elif verb == "save_all":
            self._save_all_dialog()
        elif verb == "play":
            self._play_position()
        elif verb == "FEN":
            QTUtils.set_clipboard(self.tab_analysis.fen_active())
            QTDialogs.fen_is_in_clipboard(self)

    # -- Timed playback --------------------------------------------------------

    def _toggle_timed_playback(self):
        self.is_timed_active = not self.is_timed_active
        if self.is_timed_active:
            self.tab_analysis.change_mov_active("to_beginning")
            self._refresh_board()
            QtCore.QTimer.singleShot(Code.configuration.x_interval_replay, self._timed_next)

    def _timed_next(self):
        if not self.is_timed_active:
            return
        self.tab_analysis.change_mov_active("forward")
        self._refresh_board()
        if self.tab_analysis.is_final_position():
            self.is_timed_active = False
        else:
            if Code.configuration.x_beep_replay:
                Code.runSound.play_beep()
            QtCore.QTimer.singleShot(Code.configuration.x_interval_replay, self._timed_next)

    # -- Play / save helpers ---------------------------------------------------

    def _play_position(self):
        position, _, __ = self.tab_analysis.activate_position()
        game = Game.Game(first_position=position)
        tmp_file = Code.configuration.temporary_file("pk")
        Util.save_pickle(tmp_file, {"ISWHITE": position.is_white, "GAME": game.save()})
        XRun.run_lucas("-play", tmp_file)

    def _save_dialog(self):
        menu = QTDialogs.LCMenu(self)
        menu.opcion(True, _("All moves"), Iconos.PuntoVerde())
        menu.separador()
        menu.opcion(False, _("Only the first move"), Iconos.PuntoRojo())
        is_complete = menu.lanza()
        if is_complete is None:
            return
        self.tab_analysis.save_base(self.tab_analysis.game, self.tab_analysis.rm, is_complete)
        self.tab_analysis.put_view_manager()

    def _save_all_dialog(self):
        menu = QTDialogs.LCMenu(self)
        menu.opcion(True, _("All moves in each variation"), Iconos.PuntoVerde())
        menu.separador()
        menu.opcion(False, _("Only the first move of each variation"), Iconos.PuntoRojo())
        is_complete = menu.lanza()
        if is_complete is None:
            return
        for rm, _name, _cp in self.tab_analysis.list_rm_name:
            game = Game.Game(self.tab_analysis.move.position_before)
            game.read_pv(rm.pv)
            self.tab_analysis.save_base(game, rm, is_complete)
        self.tab_analysis.put_view_manager()


class WAnalisis(LCDialog.LCDialog):
    """Main analysis window.

    Hosts one or more OneAnalysis panels side-by-side (one per engine /
    sub-analysis). The active panel is highlighted; the others are dimmed.
    """

    def __init__(self, tb_analysis, ventana, is_white, must_save, tab_analysis_init, subanalysis=False):
        titulo = _("Subanalysis") if subanalysis else _("Analysis")
        extparam = self._unique_window_key(subanalysis)
        LCDialog.LCDialog.__init__(self, ventana, titulo, Iconos.Analizar(), extparam)

        self.tb_analysis = tb_analysis
        self.active_tab = None   # the currently focused TabAnalysis
        self.timer = None
        self.subanalysis = subanalysis

        configuration = Code.configuration
        config_board = configuration.config_board(
            "SUBANALYSIS" if subanalysis else "ANALISIS",
            32 if subanalysis else 48,
        )
        self.must_save = must_save
        self.is_white = is_white

        self._setup_board(config_board, is_white)
        self._setup_shared_labels(configuration)
        ly_left, lytb = self._build_left_column(must_save)

        # First analysis panel (appears to the right of the board column)
        first_panel = OneAnalysis(self, tab_analysis_init)
        tab_analysis_init.wmu = first_panel

        self.ly = Colocacion.H().margen(10).otro(ly_left).control(first_panel)
        layout = Colocacion.V().otro(Colocacion.H().margen(0).otro(self.ly).relleno()).margen(3)
        layout.setSpacing(1)
        self.setLayout(layout)

        self.restore_video(with_width=False)
        first_panel.select_candidate(tab_analysis_init.pos_selected)
        self.activate_analysis(tab_analysis_init)

    @staticmethod
    def _unique_window_key(subanalysis):
        """Return a unique geometry key for video saving.

        Sub-analysis windows are numbered (subanalysis1, subanalysis2, …)
        so multiple instances each remember their own size/position.
        """
        if not subanalysis:
            return "analysis"
        existing = {
            int(w.key_video[11:])
            for w in QtWidgets.QApplication.topLevelWidgets()
            if hasattr(w, "key_video") and w.key_video.startswith("subanalysis")
        }
        num = next((x for x in range(1, 100) if x not in existing), 1)
        return f"subanalysis{num}"

    def _setup_board(self, config_board, is_white):
        self.board = Board.Board(self, config_board)
        self.board.draw_window()
        self.board.set_side_bottom(is_white)
        self.board.set_dispatcher(self.player_has_moved_dispatcher)

    def _setup_shared_labels(self, configuration):
        """Create the labels shared by all OneAnalysis panels."""
        self.lb_engine = Controles.LB(self).align_center()
        self.lb_time = Controles.LB(self).align_center()
        self.lbPuntuacion = Controles.LB(self).align_center()

        self.lbPGN = Controles.LB(self)
        configuration.set_property(self.lbPGN, "pgn")
        self.lbPGN.set_wrap().set_font_type(puntos=configuration.x_pgn_fontpoints)
        self.lbPGN.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.lbPGN.setOpenExternalLinks(False)
        self.lbPGN.linkActivated.connect(self.change_pos_active)

    def _build_left_column(self, must_save):
        """Build the left column: top toolbar, board, mini toolbar, engine info, PGN scroll."""
        tb_work = QTDialogs.LCTB(self, icon_size=24)
        tb_work.new(_("Close"), Iconos.MainMenu(), self.finalize)
        tb_work.new(_("New"), Iconos.NuevoMas(), self.new_analysis)

        self.setStyleSheet("QStatusBar::item { border-style: outset; border: 1px solid LightSlateGray ;}")
        list_more_actions = ((f"FEN:{_('Copy to clipboard')}", "MoverFEN", Iconos.Clipboard()),)
        lytb, self.tb = QTDialogs.ly_mini_buttons(
            self, "", must_save=must_save, if_save_all=must_save,
            if_play=True, list_more_actions=list_more_actions, icon_size=24,
        )

        pgn_scroll = self._build_pgn_scroll()

        ly_board = Colocacion.H().relleno().control(self.board).relleno()
        ly_engine_row = (Colocacion.H().control(self.lbPuntuacion).relleno().control(self.lb_engine)
                         .control(self.lb_time))
        ly_left = (
            Colocacion.V()
            .control(tb_work)
            .otro(ly_board)
            .otro(lytb).espacio(20)
            .otro(ly_engine_row)
            .control(pgn_scroll)
        )
        return ly_left, lytb

    def _build_pgn_scroll(self):
        scroll = QtWidgets.QScrollArea()
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        container = QtWidgets.QWidget()
        container.setLayout(Colocacion.V().control(self.lbPGN).margen(3))
        scroll.setWidget(container)
        return scroll

    # -- PGN link callback -----------------------------------------------------

    def change_pos_active(self, pos):
        """Called when the user clicks a move link in the PGN text label."""
        self.active_tab.wmu.change_pos_active(int(pos))

    # -- Keyboard and wheel ----------------------------------------------------

    def keyPressEvent(self, event):
        self._handle_key(event.key())

    def _handle_key(self, k):
        wmu = self.active_tab.wmu
        key = QtCore.Qt.Key
        if k == key.Key_Down:
            wmu.go_down()
        elif k == key.Key_Up:
            wmu.go_up()
        elif k == key.Key_Left:
            wmu.process_toolbar("move_back")
        elif k == key.Key_Right:
            wmu.process_toolbar("move_forward")
        elif k == key.Key_Home:
            wmu.process_toolbar("move_to_beginning")
        elif k == key.Key_End:
            wmu.process_toolbar("move_to_end")
        elif k == key.Key_PageUp:
            wmu.go_first()
        elif k == key.Key_PageDown:
            wmu.go_last()
        elif k == key.Key_Escape:
            self.finalize()

    def board_wheel_event(self, _board, forward):
        forward = Code.configuration.wheel_board(forward)
        self._handle_key(QtCore.Qt.Key.Key_Left if forward else QtCore.Qt.Key.Key_Right)

    # -- Window lifecycle ------------------------------------------------------

    def closeEvent(self, event):
        self.finalize(False)

    def finalize(self, accepted=True):
        # Save geometry of any open sub-analysis windows
        for window in QtWidgets.QApplication.topLevelWidgets():
            if hasattr(window, "key_video") and window.key_video.startswith("subanalysis"):
                with contextlib.suppress(AttributeError):
                    getattr(window, "save_video")()
        # Stop timed playback in all panels
        for tab in self.tb_analysis.li_tabs_analysis:
            tab.wmu.is_timed_active = False
        self.save_video()
        if accepted:
            self.accept()
        else:
            self.reject()

    # -- Analysis panel management ---------------------------------------------

    def activate_analysis(self, tab_analysis):
        """Make ``tab_analysis`` the active panel; dim all others."""
        self.active_tab = tab_analysis
        for tab in self.tb_analysis.li_tabs_analysis:
            if hasattr(tab, "wmu"):
                tab.wmu.activate(tab is tab_analysis)

    def create_analysis(self, tab_analysis):
        """Add a new OneAnalysis panel to the window and make it active."""
        panel = OneAnalysis(self, tab_analysis)
        self.ly.control(panel)
        panel.show()
        tab_analysis.set_wmu(panel)
        self.activate_analysis(tab_analysis)
        panel.grid_left_button(panel.wrm, tab_analysis.pos_rm_active, 0)
        return panel

    def remove_analysis(self, tab_analysis):
        tab_analysis.desactiva()
        self.adjustSize()
        QTUtils.refresh_gui()

    def process_toolbar(self):
        key = getattr(self.sender(), "key")
        if key == "finalize":
            self.finalize()
            self.accept()
        elif key == "crear":
            self.new_analysis()
        else:
            self.active_tab.wmu.process_toolbar(key)

    # -- Clock (used by external callers) -------------------------------------

    def start_clock(self, funcion):
        if self.timer is None:
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(funcion)
        self.timer.start(1000)

    def stop_clock(self):
        if self.timer:
            self.timer.stop()
            self.timer = None

    # -- New analysis / play from board ----------------------------------------

    def new_analysis(self):
        if alm := WindowAnalysisParam.analysis_parameters(self, False, True, False, False):
            tab_analysis = self.tb_analysis.create_show(self, alm)
            self.create_analysis(tab_analysis)

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        game = self.active_tab.wmu.tab_analysis.get_game()
        if not promotion and game.last_position.pawn_can_promote(from_sq, to_sq):
            promotion = self.board.pawn_promoting(game.last_position.is_white)
            if promotion is None:
                return False
        ok, _error, move = Move.get_game_move(game, game.last_position, from_sq, to_sq, promotion)
        if ok:
            self._analyze_player_move(game, move)
        return False

    def _analyze_player_move(self, game, move):
        """Analyze a move played on the board and open a sub-analysis window."""
        game.add_move(move)
        xanalyzer: EngineManagerAnalysis.EngineManagerAnalysis = Code.procesador.get_manager_analyzer()
        can_cancel = not xanalyzer.is_run_fast()

        with QTMessages.WaitingMessage(
            self,
            _("Analyzing the move...."),
            with_cancel=can_cancel,
            tit_cancel=_("Stop thinking"),
            opacity=1.0,
        ) as wm:
            dispatcher = wm.dispatcher_analysis if can_cancel else None
            mrm, pos = xanalyzer.analyze_move(game, len(game) - 1, dispatcher)
            if pos >= 0:
                move.analysis = mrm, pos

        if pos >= 0:
            Analysis.show_analysis(
                xanalyzer,
                move,
                self.board.is_white_bottom,
                len(game) - 1,
                main_window=self,
                must_save=False,
                subanalysis=True,
            )
