import contextlib
import time
from typing import Callable, Optional, List

from PySide6 import QtCore

from Code.Base import Game, Position
from Code.Engines import EngineManager, EngineResponse, EngineRun, Engines


class EngineManagerAnalysis(EngineManager.EngineManager):
    def __init__(self, engine: Engines.Engine, run_engine_params: EngineRun.RunEngineParams):
        super().__init__(engine, run_engine_params, True)

    def _run_analysis_loop(
        self, dispacher: Optional[Callable], run_engine_params: Optional[EngineRun.RunEngineParams] = None
    ):
        """Ejecuta el loop de análisis con manejo de señales."""
        loop = QtCore.QEventLoop()
        timer = QtCore.QTimer(loop)
        timer.setInterval(self.ms_refresh)
        self._is_canceled = False

        def check_state(bestmove):
            def close():
                with contextlib.suppress(RuntimeError, TypeError):
                    if self.engine_run is not None:
                        self.engine_run.bestmove_found.disconnect(check_state)
                timer.stop()
                loop.quit()

            if self.is_disabled:
                self.stop()
                close()
                return

            if dispacher and self.engine_run and self.engine_run.mrm:
                if not dispacher(rm=self.engine_run.mrm.best_rm_ordered(), ms=self.elapsed_time.elapsed()):
                    self._is_canceled = True
                    self.engine_run.stop()
                    close()
                    return

            if bestmove is not None:
                close()

        if self.engine_run is None:
            return

        try:
            self.engine_run.bestmove_found.connect(check_state)
            self.engine_run.play(self.run_engine_params if run_engine_params is None else run_engine_params)
            timer.timeout.connect(lambda: check_state(None))
            timer.start()
            self.active_loop = loop
            loop.exec()
        except:
            pass
        finally:
            self.active_loop = None
            if self.engine_run is not None:
                try:
                    self.engine_run.bestmove_found.disconnect(check_state)
                except:
                    pass
            timer.stop()

    def get_cache(self, fenm2):
        if fenm2 in self.cache_analysis:
            mrm = self.cache_analysis[fenm2]
            self.engine_run.set_mrm_cached(mrm)
            return mrm
        return None

    def set_cache(self, fenm2, mrm):
        self.cache_analysis[fenm2] = mrm

    def analyze_move(self, game, movement: int, dispacher: Optional[Callable]) -> tuple:

        if not self.check_engine():
            return None, -1

        move = game.move(movement)

        # Cache""
        fenm2 = ""
        if self.cache_analysis is not None:
            position = move.position_before if movement >= 0 else game.first_position
            fenm2 = position.fenm2()
            if fenm2 in self.cache_analysis:
                mrm: EngineResponse.MultiEngineResponse = self.cache_analysis[fenm2]
                rm, pos = mrm.search_rm(move.movimiento())
                if pos >= 0:
                    self.engine_run.set_mrm_cached(mrm)
                    return mrm, pos

        self.engine_run.set_game_position(game, movement if len(game) > 0 else None, True)
        self.engine_run.play(self.run_engine_params)

        self.elapsed_time.start()

        self._run_analysis_loop(dispacher)

        if self.engine_run is None or self.engine_run.mrm is None:
            return None, -1

        self.mrm = self.engine_run.mrm
        if self._is_canceled:
            return self.mrm, -1

        movimiento = move.movimiento()
        rm, pos = self.mrm.search_rm(movimiento)
        if rm is None:
            mrm = self.mrm.clone()

            if mrm.depth > 1 and self.run_engine_params.fixed_nodes == 0 and self.run_engine_params.fixed_depth == 0:
                tmp_play_params = self.run_engine_params.clone()
                tmp_play_params.fixed_depth = mrm.depth - 1
            else:
                tmp_play_params = self.run_engine_params
            rm = self.analyze_post_move(game, movement, tmp_play_params, dispacher)
            if self._is_canceled or rm is None:
                return mrm, -1
            rm.change_side(mv_insert=movimiento)
            mrm.add_rm(rm)
            self.engine_run.set_mrm_cached(mrm)
            self.mrm = mrm

        self.mrm.ordena()
        rm, pos = self.mrm.search_rm(movimiento)
        if self.cache_analysis is not None:
            self.cache_analysis[fenm2] = self.mrm
        return self.mrm, pos

    def analyze_post_move(self, game, movement: int, tmp_play_params: EngineRun.RunEngineParams, dispacher: Callable):
        try:
            self.engine_run.set_multipv(1)
            self.engine_run.set_game_position(game, movement, False)
            self.engine_run.play(tmp_play_params)

            self._run_analysis_loop(dispacher)

            mrm = self.engine_run.mrm

        finally:
            if self.engine_run is not None:
                self.engine_run.set_multipv(self.multipv)

        return mrm.best_rm_ordered() if mrm is not None else None

    def analyze_nomodal(self, game: Game.Game) -> bool:
        if not self.check_engine():
            return False
        self.engine_run.set_game_position(game, None, False)
        self.engine_run.play(self.run_engine_params)
        return True

    def analyze_tutor(
        self, game, dispacher_bestmove: Optional[Callable], dispacher_changedepth: Optional[Callable]
    ) -> bool:
        if not self.check_engine():
            return False
        try:
            if dispacher_bestmove is not None:
                self.connect_bestmove(dispacher_bestmove)

            if dispacher_changedepth is not None:
                self.connect_depthchanged(dispacher_changedepth)

            if self.cache_analysis is not None:
                fenm2 = game.last_position.fenm2()
                if fenm2 in self.cache_analysis:
                    mrm: EngineResponse.MultiEngineResponse = self.cache_analysis[fenm2]
                    self.engine_run.set_mrm_cached(mrm)
                    if dispacher_bestmove is not None:
                        if mrm.li_rm:
                            dispacher_bestmove(mrm.best_rm_ordered().movimiento())
                            return True

            self.engine_run.set_game_position(game, None, False)
            self.engine_run.play(self.run_engine_params)

        except AttributeError:
            return False

        return True

    def add_cache_position(self, position: Position.Position, mrm: EngineResponse.MultiEngineResponse):
        if self.cache_analysis is not None:
            self.cache_analysis[position.fenm2()] = mrm

    def analyze_tutor_move(self, game: Game.Game, a1h8: str):
        mrm = self.engine_run.mrm
        tmp_play_params = self.run_engine_params.clone()
        tmp_play_params.fixed_depth = mrm.depth - 1 if mrm.depth > 1 else 1

        emit_bestmove_found = self.enabled_emit_bestmove_found
        emit_depth_changed = self.enabled_emit_depth_changed
        self.enabled_emit_bestmove_found = False
        self.enabled_emit_depth_changed = False

        try:
            self.engine_run.set_multipv(1)

            game_tmp = game.copia()
            game_tmp.add_a1h8(a1h8)
            self.engine_run.set_game_position(game_tmp, None, False)

            self._run_analysis_loop(None, run_engine_params=tmp_play_params)

            mrm_new = self.engine_run.mrm

        finally:
            if self.engine_run:
                self.engine_run.set_multipv(self.multipv)
            else:
                return None

        self.enabled_emit_bestmove_found = emit_bestmove_found
        self.enabled_emit_depth_changed = emit_depth_changed
        if self.is_disabled or self._is_canceled or mrm_new is None:
            return None

        rm = mrm_new.best_rm_ordered()
        rm.change_side(mv_insert=a1h8)

        mrm.add_rm(rm)
        self.engine_run.set_mrm_cached(mrm)
        return mrm

    def stop_deferred(self, max_mstime):
        """Lanza un stop() después de un tiempo máximo sin bloquear el hilo principal."""
        if self.engine_run is None:
            return

        if self.engine_run.state != EngineRun.EngineState.THINKING:
            self.stop()
            return

        while (
            self.engine_run.state != EngineRun.EngineState.THINKING
            and self.engine_run.time_played() * 1000 < max_mstime
        ):
            time.sleep(0.1)
        self.stop()

    def analyze_last_position(self, game, dispacher: Optional[Callable]) -> EngineResponse.MultiEngineResponse | None:

        if not self.check_engine():
            return None

        self.engine_run.set_game_position(game, None, False)
        self.engine_run.play(self.run_engine_params)

        self.elapsed_time.start()

        self._run_analysis_loop(dispacher)

        if self.engine_run is None or self.engine_run.mrm is None:
            return None

        self.mrm = self.get_current_mrm()
        if self.mrm:
            self.mrm.ordena()
        return self.mrm

    def analyze_fen(self, fen, dispacher: Optional[Callable]) -> EngineResponse.MultiEngineResponse | None:

        if not self.check_engine():
            return None

        self.engine_run.set_fen_position(fen)
        self.engine_run.play(self.run_engine_params)

        self.elapsed_time.start()

        self._run_analysis_loop(dispacher)

        if self.engine_run is None or self.engine_run.mrm is None:
            return None

        self.mrm = self.get_current_mrm()
        if self.mrm:
            self.mrm.ordena()
        return self.mrm

    def seek_mate(self, game: Game.Game, mate: int) -> List[EngineResponse.EngineResponse] | None:

        def check_mate(rm: EngineResponse.EngineResponse, ms: float):
            if 0 < rm.mate <= mate:
                return False
            return True

        mrm: EngineResponse.MultiEngineResponse = self.analyze_last_position(game, check_mate)
        mate = mrm.best_rm_ordered().mate

        return [rm for rm in mrm.li_rm if rm.mate == mate]



