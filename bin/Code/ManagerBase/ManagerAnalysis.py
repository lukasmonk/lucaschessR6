from types import SimpleNamespace

import Code
from Code.Analysis import Analysis, AnalysisIndexes, Histogram, WindowAnalysisConfig, WindowAnalysisGraph
from Code.Analysis.AnalysisGame import AnalysisGameLaunch
from Code.Base.Constantes import (
    GT_AGAINST_ENGINE,
    GT_AGAINST_GM,
    GT_AGAINST_PGN,
    GT_ALONE,
    GT_BOOK,
    GT_ELO,
    GT_GAME,
    GT_MICELO,
    GT_OPENINGS,
    GT_POSITIONS,
    GT_TACTICS,
    GT_VARIATIONS,
    GT_WICKER,
    ST_ENDGAME,
    TB_EBOARD,
)
from Code.QT import QTMessages


class ManagerAnalysis:
    def __init__(self, manager):
        self.manager = manager
        self.main_window = manager.main_window
        self.configuration = manager.configuration
        self.game = manager.game
        self.procesador = manager.procesador
        self.manager_tutor = self.procesador.get_manager_tutor()
        self.manager_analyzer = self.procesador.get_manager_analyzer()

    def analyze_with_tutor(self, with_cursor=False):
        if with_cursor:
            self.main_window.pensando_tutor(True)
        self.manager.thinking(True)
        fen = self.game.last_position.fen()
        if not self.manager.is_finished():
            self.manager.mrm_tutor = self.manager_tutor.analiza(fen)
        else:
            self.manager.mrm_tutor = None
        self.manager.thinking(False)
        if with_cursor:
            self.main_window.pensando_tutor(False)
        return self.manager.mrm_tutor

    def analize_after_last_move(self):
        mens = _("Analyzing the move....")
        self.main_window.base.show_message(mens, True, tit_cancel=_("Stop thinking"))
        self.main_window.base.tb.setDisabled(True)

        state = SimpleNamespace(canceled=False, ms=0, depth=0)

        def test_me(rm=None, ms=None):
            if ms:
                state.ms = ms
            if rm and rm.depth:
                state.depth = rm.depth
            if self.main_window.base.is_canceled():
                if not state.canceled:
                    self.manager_analyzer.stop()
                state.canceled = True
            else:
                self.main_window.base.change_message(
                    '%s<br><small>%s: %d %s: %.01f"'
                    % (mens, _("Depth"), rm.depth, _("Time"), (ms if ms else rm.time) / 1000)
                )
            return True

        self.manager_analyzer.analyze_last_position(self.manager.game, test_me)
        self.main_window.base.tb.setDisabled(False)
        self.main_window.base.hide_message()
        mrm = self.manager_analyzer.mrm
        if state.canceled:
            if state.ms:
                mrm.max_time = state.ms
            if state.depth:
                mrm.max_depth = state.depth
        return mrm

    def analize_position(self, row, key):
        if row < 0:
            return

        move, is_white, si_ultimo, tam_lj, pos_jg = self.manager.get_movement(row, key)
        if not move:
            return
        if self.manager.state != ST_ENDGAME:
            if not (
                self.manager.game_type
                in [
                    GT_POSITIONS,
                    GT_AGAINST_PGN,
                    GT_AGAINST_ENGINE,
                    GT_AGAINST_GM,
                    GT_ALONE,
                    GT_GAME,
                    GT_VARIATIONS,
                    GT_BOOK,
                    GT_OPENINGS,
                    GT_TACTICS,
                ]
                or (self.manager.game_type in [GT_ELO, GT_MICELO, GT_WICKER] and not self.manager.is_competitive)
            ):
                if si_ultimo or self.manager.hints == 0:
                    return
        if move.analysis is None:
            si_cancelar = not self.manager_analyzer.is_run_fast()
            mens = _("Analyzing the move....")
            self.main_window.base.show_message(mens, si_cancelar, tit_cancel=_("Stop thinking"))
            self.main_window.base.tb.setDisabled(True)
            if si_cancelar:

                def test_me(rm, ms):
                    if self.main_window.base.is_canceled():
                        return False
                    else:
                        self.main_window.base.change_message(
                            f'{mens}<br><small>{_("Depth")}: {rm.depth} {_("Time")}: {ms / 1000:.01f}'
                        )
                    return True

                dispacher = test_me
            else:
                dispacher = None
            mrm, pos = self.manager_analyzer.analyze_move(self.manager.game, pos_jg, dispacher=dispacher)
            ok = pos >= 0
            if ok:
                move.analysis = mrm, pos
                move.refresh_nags()
            self.main_window.base.tb.setDisabled(False)
            self.main_window.base.hide_message()
            if not ok:
                return

        Analysis.show_analysis(self.manager_analyzer, move, self.manager.board.is_white_bottom, pos_jg)
        self.manager.put_view()
        self.manager.check_changed()

    def analizar(self):
        if Code.eboard and Code.eboard.driver:
            self.manager.routine_default(TB_EBOARD)
        self.main_window.base.tb.setDisabled(True)
        self.manager.is_analyzing = True
        activate_analisisbar = False
        if self.main_window.with_analysis_bar:
            activate_analisisbar = True
            self.main_window.activate_analysis_bar(False)
        AnalysisGameLaunch.analysis_game(self.manager)
        if activate_analisisbar:
            self.main_window.activate_analysis_bar(True)
            self.manager.put_view()
        self.manager.is_analyzing = False
        self.main_window.base.tb.setDisabled(False)
        self.manager.refresh()
        self.manager.check_changed()

    def show_analysis(self):
        with QTMessages.one_moment_please(self.main_window):
            self.manager.game.assign_isbook_phases()
            elos = self.manager.game.calc_elos()
            alm = Histogram.gen_histograms(self.manager.game)
            (
                alm.indexesHTML,
                alm.indexesHTMLelo,
                alm.indexesHTMLmoves,
                alm.indexesHTMLold,
                alm.indexesRAW,
                alm.eloW,
                alm.eloB,
                alm.eloT,
            ) = AnalysisIndexes.gen_indexes(self.manager.game, elos, alm)
            alm.is_white_bottom = self.manager.board.is_white_bottom

        if len(alm.lijg) == 0:
            QTMessages.message(self.main_window, _("There are no analyzed moves."))
        else:
            WindowAnalysisGraph.show_graph(self.main_window, self.manager, alm, Analysis.show_analysis)

    def refresh_analysis(self):
        if not self.manager.game:
            return

        for move in self.manager.game.li_moves:
            move.refresh_nags()

        self.main_window.base.pgn.refresh()
        self.manager.refresh()

    def config_analysis_parameters(self):
        w = WindowAnalysisConfig.WConfAnalysis(self.main_window, self.manager)
        w.show()
