from typing import Optional
from Code.Engines import EngineManager, EngineRun
from Code.Base import Game


class EngineManagerRefresh(EngineManager.EngineManager):
    def __init__(self, engine, run_engine_params: EngineRun.RunEngineParams):
        super().__init__(engine, run_engine_params, False)
        self.pending_game: Optional[Game.Game] = None
        self.pending_fen: Optional[str] = None

    def refresh(self, game: Game.Game):
        if self.check_engine():
            try:
                st = self.engine_run.state
                if st in (EngineRun.EngineState.THINKING, EngineRun.EngineState.READING_EVAL_STOCKFISH):
                    self.pending_game = game
                    self.pending_fen = None
                    self.engine_run.stop()
                else:
                    self.pending_game = None
                    self.pending_fen = None
                    self.engine_run.set_game_position(game, None, False)
                    self.engine_run.play(self.run_engine_params)
            except AttributeError:
                pass

    def refresh_eval(self, fen: str):
        if self.check_engine():
            st = self.engine_run.state
            if st in (EngineRun.EngineState.THINKING, EngineRun.EngineState.READING_EVAL_STOCKFISH):
                self.pending_fen = fen
                self.pending_game = None
                self.engine_run.stop()
            else:
                self.pending_fen = None
                self.pending_game = None
                self.engine_run.run_eval_stockfish(fen)

    def bestmove_found(self, bestmove):
        super().bestmove_found(bestmove)
        self._check_pending()

    def eval_stockfish_found(self, txt):
        self._check_pending()

    def _check_pending(self):
        if self.pending_game:
            game = self.pending_game
            self.pending_game = None
            self.refresh(game)
        elif self.pending_fen:
            fen = self.pending_fen
            self.pending_fen = None
            self.refresh_eval(fen)

    def connect_eval_stockfish(self, rutina):
        if self.check_engine():
            self.engine_run.eval_stockfish_found.connect(rutina)
            self.engine_run.eval_stockfish_found.connect(self.eval_stockfish_found)
