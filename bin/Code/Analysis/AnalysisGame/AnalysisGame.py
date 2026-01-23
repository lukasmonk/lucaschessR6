from dataclasses import dataclass
from typing import Callable, Optional

from PySide6 import QtCore

import Code
from Code.Z import Util
from Code.Analysis import AnalysisIndexes
from Code.Analysis.AnalysisGame import AnalysisGameSaveTrainings
from Code.Base import Game
from Code.Base.Constantes import (
    BLUNDER,
    INACCURACY,
    INACCURACY_MISTAKE,
    INACCURACY_MISTAKE_BLUNDER,
    MISTAKE,
    MISTAKE_BLUNDER,
)
from Code.BestMoveTraining import BMT
from Code.Engines import EngineManagerAnalysis, EngineRun, Engines
from Code.Nags.Nags import NAG_3
from Code.Themes import AssignThemes


@dataclass
class MoveAnalysisData:
    must_be_analyzed: bool
    is_main: bool
    game: Game.Game
    pos_in_game: int
    pos_in_table: int  # En las variantes es diferente que pos_in_game

    def ensure_analysis(self, engine_manager, dispatcher):
        if not self.must_be_analyzed:
            return self.game.move(self.pos_in_game).analysis
        resp = engine_manager.analyze_move(self.game, self.pos_in_game, dispatcher)
        if resp is None:
            return None
        self.game.move(self.pos_in_game).analysis = resp
        return resp


@dataclass
class AnalysisState:
    si_blunders: bool
    si_brilliancies: bool
    si_bp2: bool
    total_moves: int
    pgn_original_blunders: bool = False
    pgn_original_brilliancies: bool = False
    cl_game: Optional[str] = None


class AnalysisGame(QtCore.QObject):
    def __init__(self, analysis_params, is_massiv, dispatcher: Callable, li_selected: list):
        super().__init__()

        self.analysis_params = analysis_params
        self.si_bmt_blunders = False
        self.si_bmt_brilliancies = False

        self.li_selected = li_selected
        self.dispatcher = dispatcher

        # Asignacion de variables para blunders:
        dic = {
            INACCURACY: {
                INACCURACY,
            },
            MISTAKE: {
                MISTAKE,
            },
            BLUNDER: {
                BLUNDER,
            },
            INACCURACY_MISTAKE_BLUNDER: {INACCURACY, BLUNDER, MISTAKE},
            INACCURACY_MISTAKE: {INACCURACY, MISTAKE},
            MISTAKE_BLUNDER: {BLUNDER, MISTAKE},
        }
        self.kblunders_condition_list = dic.get(analysis_params.kblunders_condition, {BLUNDER, MISTAKE})

        self.tacticblunders = (
            Util.opj(
                Code.configuration.paths.folder_personal_trainings(),
                "../Tactics",
                analysis_params.tacticblunders,
            )
            if analysis_params.tacticblunders
            else None
        )
        self.bmt_listaBlunders = None

        self.si_tactic_blunders = False

        self.bmt_listaBrilliancies = None

        self.white = analysis_params.white
        self.black = analysis_params.black
        if is_massiv:
            self.li_players = (
                [player.upper() for player in analysis_params.li_players] if analysis_params.li_players else []
            )
        else:
            self.li_players = None

        self.themes_assign = AssignThemes.AssignThemes() if analysis_params.themes_assign else None
        self.with_themes_tags = analysis_params.themes_tags
        self.themes_reset = analysis_params.themes_reset

    def get_engine_manager(self):
        ap = self.analysis_params
        if ap.engine == "default":
            engine: Engines.Engine = Code.configuration.engines.engine_analyzer()
        else:
            engine: Engines.Engine = Code.configuration.engines.search(ap.engine, "stockfish")

        run_engine_params = EngineRun.RunEngineParams()
        run_engine_params.update(engine, ap.vtime, ap.depth, ap.nodes, ap.multiPV)

        engine_manager = EngineManagerAnalysis.EngineManagerAnalysis(engine, run_engine_params)
        engine_manager.set_priority(ap.priority)
        return engine_manager

    def get_moves(self, game):
        ap = self.analysis_params

        is_white, is_black = self._resolve_sides(game, ap)
        if not (is_white or is_black):
            return None

        li_pos_moves = self.li_selected[:] if self.li_selected else list(range(len(game)))
        st_moves_to_skip = self._skip_opening_moves(game, ap, li_pos_moves)

        if ap.from_last_move:
            li_pos_moves.reverse()

        li_moves_to_analyze = []

        for pos_move in li_pos_moves:
            if pos_move in st_moves_to_skip:
                continue

            move = game.move(pos_move)
            must_analyze = True if ap.delete_previous else move.analysis is None

            li_moves_to_analyze.append(MoveAnalysisData(must_analyze, True, game, pos_move, pos_move))

            if ap.analyze_variations:
                li_moves_to_analyze.extend(self._variation_moves(move, ap, is_white, is_black, pos_move))

        return li_moves_to_analyze

    def _resolve_sides(self, game, analysis_params):
        is_white = analysis_params.white
        is_black = analysis_params.black

        if not self.li_players:
            return is_white, is_black

        for color in ("BLACK", "WHITE"):
            player = game.get_tag(color)
            if not player:
                continue

            if self._player_matches(player.upper()):
                continue

            if color == "BLACK":
                is_black = False
            else:
                is_white = False

        return is_white, is_black

    def _player_matches(self, player):
        for raw_pattern in self.li_players:
            pattern = raw_pattern.strip().upper()
            starts_wild = pattern.startswith("*")
            ends_wild = pattern.endswith("*")
            core = pattern.replace("*", "").strip()

            if starts_wild:
                if player.endswith(core):
                    return True
                if ends_wild and core in player:
                    return True
            elif ends_wild:
                if player.startswith(core):
                    return True
            elif player == core:
                return True

        return False

    @staticmethod
    def _skip_opening_moves(game, analysis_params, li_pos_moves) -> set:
        st_to_skip = set()
        book = analysis_params.book
        if book is not None:
            for mov in li_pos_moves:
                move = game.move(mov)
                if book.get_list_moves(move.position.fen()):
                    move.is_book = True
                    st_to_skip.add(mov)
                    continue
                break

        if analysis_params.standard_openings:
            for mov in li_pos_moves:
                if mov in st_to_skip:
                    continue
                move = game.move(mov)
                if move.in_the_opening:
                    move.is_book = True
                    st_to_skip.add(mov)
                    continue
                break
        return st_to_skip

    @staticmethod
    def _variation_moves(move, analysis_params, is_white_allowed, is_black_allowed, pos_move):
        li_moves_games = move.list_all_moves()
        white_move = move.position_before.is_white
        if white_move and not is_white_allowed:
            return []
        if not white_move and not is_black_allowed:
            return []

        li_moves_to_analyze = []
        for move_var, game_var, pos_in_var in li_moves_games:
            must_analyze = True if analysis_params.delete_previous else move_var.analysis is None
            if must_analyze:
                li_moves_to_analyze.append(MoveAnalysisData(must_analyze, False, game_var, pos_in_var, pos_move))
        return li_moves_to_analyze

    def run_analisis(self, game, wprogressbar):
        with self.get_engine_manager() as engine_manager:
            self.run_one_analysis(game, wprogressbar, engine_manager, False)

    def run_one_analysis(self, game, wprogressbar, engine_manager, must_check_paused):
        self._reset_training_flags()

        ap = self.analysis_params
        si_bp2 = hasattr(wprogressbar, "bp2")

        self._prepare_bmt_lists(ap)

        li_moves_to_analyze = self.get_moves(game)

        if si_bp2:
            wprogressbar.set_total(2, len(li_moves_to_analyze))

        training_state = AnalysisState(
            si_blunders=ap.pgnblunders or ap.oriblunders or ap.bmtblunders or self.tacticblunders,
            si_brilliancies=ap.fnsbrilliancies or ap.pgnbrilliancies or ap.bmtbrilliancies,
            si_bp2=si_bp2,
            total_moves=len(li_moves_to_analyze),
            cl_game=Util.huella(),
        )

        for pos, mad in enumerate(li_moves_to_analyze):
            move = mad.game.move(mad.pos_in_game)
            if must_check_paused:
                wprogressbar.check_paused()

            self._update_progress(wprogressbar, training_state, mad, pos)

            if mad.is_main:
                position = pos, training_state.total_moves, mad.pos_in_table
                if not self.dispatcher(position=position):
                    break

            analysis_result = mad.ensure_analysis(engine_manager, self.dispatcher)
            if analysis_result is None:
                break

            mrm, pos_act = analysis_result
            if pos_act == -1:
                break

            allow_add_variations = self._allow_add_variations(move, ap)
            rm, nag = self._update_move_indexes(move, mrm, pos_act)

            if mad.is_main and (training_state.si_blunders or training_state.si_brilliancies or ap.include_variations):
                self._process_main_move(
                    game,
                    move,
                    mrm,
                    pos_act,
                    mad,
                    ap,
                    training_state,
                    allow_add_variations,
                    rm,
                    nag,
                )

        self._finalize_outputs(ap, game, training_state)

        if self.analysis_params.accuracy_tags:
            game.add_accuracy_tags()

        if self.themes_assign:
            self.themes_assign.assign_game(game, self.with_themes_tags, self.themes_reset)

    def _reset_training_flags(self):
        self.si_bmt_blunders = False
        self.si_bmt_brilliancies = False
        self.si_tactic_blunders = False

    def _prepare_bmt_lists(self, analysis_params):
        if analysis_params.bmtblunders and self.bmt_listaBlunders is None:
            self.bmt_listaBlunders = BMT.BMTLista()

        if analysis_params.bmtbrilliancies and self.bmt_listaBrilliancies is None:
            self.bmt_listaBrilliancies = BMT.BMTLista()

    @staticmethod
    def _update_progress(wprogressbar, training_state, move_data, position):
        if training_state.si_bp2 and move_data.is_main:
            wprogressbar.pon(2, position + 1)

    @staticmethod
    def _allow_add_variations(move, analysis_params):
        if analysis_params.delete_previous:
            return True
        if not move.analysis:
            return True
        if analysis_params.include_variations and move.variations:
            return False
        return True

    @staticmethod
    def _update_move_indexes(move, mrm, pos_act):
        xcp = move.position_before
        move.complexity = AnalysisIndexes.calc_complexity(xcp, mrm)
        move.winprobability = AnalysisIndexes.calc_winprobability(xcp, mrm)
        move.narrowness = AnalysisIndexes.calc_narrowness(xcp, mrm)
        move.efficientmobility = AnalysisIndexes.calc_efficientmobility(xcp, mrm)
        move.piecesactivity = AnalysisIndexes.calc_piecesactivity(xcp, mrm)
        move.exchangetendency = AnalysisIndexes.calc_exchangetendency(xcp, mrm)

        rm = mrm.li_rm[pos_act]
        nag, _ = mrm.set_nag_color(rm)
        move.add_nag(nag)
        return rm, nag

    def _process_main_move(
        self,
        game,
        move,
        mrm,
        pos_act,
        move_data,
        analysis_params,
        training_state,
        allow_add_variations,
        rm,
        nag,
    ):
        fen = move.position_before.fen()

        if analysis_params.include_variations and allow_add_variations:
            if not move.analysis_to_variations(self.analysis_params, analysis_params.delete_previous):
                move.remove_all_variations()

        if training_state.si_blunders and nag in self.kblunders_condition_list:
            mj = mrm.li_rm[0]
            self.si_tactic_blunders = AnalysisGameSaveTrainings.graba_tactic(
                self.tacticblunders,
                game,
                move_data.pos_in_game,
                mrm,
                pos_act,
            )

            if AnalysisGameSaveTrainings.save_pgn(
                analysis_params.pgnblunders,
                mrm.name,
                game.dic_tags(),
                fen,
                move,
                rm,
                mj,
            ):
                training_state.pgn_original_blunders = True

            if analysis_params.bmtblunders:
                txt_game = Game.game_without_variations(game).save()
                AnalysisGameSaveTrainings.save_bmt(
                    True,
                    fen,
                    mrm,
                    pos_act,
                    training_state.cl_game,
                    txt_game,
                    self.bmt_listaBlunders,
                    self.bmt_listaBrilliancies,
                )
                self.si_bmt_blunders = True

        if training_state.si_brilliancies and move.is_brilliant():
            move.add_nag(NAG_3)
            AnalysisGameSaveTrainings.save_brilliancies_fns(
                analysis_params.fnsbrilliancies,
                fen,
                mrm,
                game,
                move_data.pos_in_game,
            )

            if AnalysisGameSaveTrainings.save_pgn(
                analysis_params.pgnbrilliancies,
                mrm.name,
                game.dic_tags(),
                fen,
                move,
                rm,
                None,
            ):
                training_state.pgn_original_brilliancies = True

            if analysis_params.bmtbrilliancies:
                txt_game = Game.game_without_variations(game).save()
                AnalysisGameSaveTrainings.save_bmt(
                    False,
                    fen,
                    mrm,
                    pos_act,
                    training_state.cl_game,
                    txt_game,
                    self.bmt_listaBlunders,
                    self.bmt_listaBrilliancies,
                )
                self.si_bmt_brilliancies = True

    @staticmethod
    def _finalize_outputs(analysis_params, game, training_state):
        if training_state.pgn_original_blunders and analysis_params.oriblunders:
            with open(analysis_params.pgnblunders, "at", encoding="utf-8", errors="ignore") as q:
                q.write(f"\n{game.pgn()}\n\n")

        if training_state.pgn_original_brilliancies and analysis_params.oribrilliancies:
            with open(analysis_params.pgnbrilliancies, "at", encoding="utf-8", errors="ignore") as q:
                q.write(f"\n{game.pgn()}\n\n")
