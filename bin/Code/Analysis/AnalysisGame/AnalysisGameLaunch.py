from typing import Optional

from Code import Util
from Code.Analysis import WindowAnalysisParam
from Code.Analysis.AnalysisGame import AnalysisGame
from Code.Databases import WDB_Utils
from Code.Engines import EngineResponse


def analysis_game(manager):
    game = manager.game
    main_window = manager.main_window

    analysis_params = WindowAnalysisParam.analysis_parameters(main_window, True)

    if analysis_params is None:
        return

    li_moves = []
    lni = Util.ListaNumerosImpresion(analysis_params.num_moves)
    num_move = int(game.primeraJugada())
    is_white = not game.starts_with_black
    for nRaw in range(game.num_moves()):
        must_save = lni.if_in_list(num_move)
        if must_save:
            if is_white:
                if not analysis_params.white:
                    must_save = False
            elif not analysis_params.black:
                must_save = False
        if must_save:
            li_moves.append(nRaw)
        is_white = not is_white
        if is_white:
            num_move += 1

    num_moves = len(li_moves)
    if len(analysis_params.num_moves) > 0 and num_moves == 0:
        return

    mens = _("Analyzing the move....")

    manager_main_window_base = manager.main_window.base
    manager_main_window_base.show_message(mens, True, tit_cancel=_("Stop thinking"))
    manager_main_window_base.tb.setDisabled(True)

    def dispatch_bp(
        position: Optional[tuple] = None, rm: Optional[EngineResponse.EngineResponse] = None, ms: Optional[int] = None
    ):
        if position is not None:
            pos, ntotal, njg = position
            message = f'{_("Analyzing the move....")}: {pos + 1}/{ntotal}'
            run_analysis_game.dispatch_bp_message = message
            message = f'{run_analysis_game.dispatch_bp_message}<br><small>{_("Depth")}: 0  {_("Time")}: 0"'
            manager_main_window_base.change_message(message)
            move = game.move(njg)
            manager.set_position(move.position)

            if game.starts_with_black:
                njg += 1
            manager.main_window.pgnColocate(njg / 2, (njg + 1) % 2)
            manager.board.put_arrow_sc(move.from_sq, move.to_sq)
            manager.put_view()

        if rm is not None:
            if ms is None:
                ms = rm.time
            message = f'{run_analysis_game.dispatch_bp_message}<br><small>{_("Depth")}: {rm.depth} {_("Time")}: {ms / 1000:.01f}"'
            manager_main_window_base.change_message(message)

        return not manager_main_window_base.is_canceled()

    run_analysis_game = AnalysisGame.AnalysisGame(analysis_params, False, dispatch_bp, li_moves)

    run_analysis_game.run_analisis(game, manager_main_window_base)

    manager_main_window_base.tb.setDisabled(False)
    manager_main_window_base.hide_message()

    not_canceled = not manager_main_window_base.is_canceled()
    # run_analysis_game.(not_canceled)

    if not_canceled:
        li_creados = []
        li_no_creados = []

        if analysis_params.tacticblunders:
            if run_analysis_game.siTacticBlunders:
                li_creados.append(analysis_params.tacticblunders)
            else:
                li_no_creados.append(analysis_params.tacticblunders)

        for x in (
            analysis_params.pgnblunders,
            analysis_params.fnsbrilliancies,
            analysis_params.pgnbrilliancies,
        ):
            if x:
                if Util.exist_file(x):
                    li_creados.append(x)
                else:
                    li_no_creados.append(x)

        if analysis_params.bmtblunders:
            if run_analysis_game.si_bmt_blunders:
                li_creados.append(analysis_params.bmtblunders)
            else:
                li_no_creados.append(analysis_params.bmtblunders)
        if analysis_params.bmtbrilliancies:
            if run_analysis_game.si_bmt_brilliancies:
                li_creados.append(analysis_params.bmtbrilliancies)
            else:
                li_no_creados.append(analysis_params.bmtbrilliancies)

        if li_creados or li_no_creados:
            WDB_Utils.message_creating_trainings(main_window, li_creados, li_no_creados)

    manager.goto_end()

    if not_canceled:
        if analysis_params.show_graphs:
            manager.show_analysis()
