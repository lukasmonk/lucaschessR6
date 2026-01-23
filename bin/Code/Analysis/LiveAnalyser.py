from typing import Optional

import Code
from Code.Base import Move, Game
from Code.Engines import EngineManagerAnalysis, EngineResponse


class LiveAnalyser:

    def __init__(self, multipv: str | int):

        self.manager_analysis: EngineManagerAnalysis.EngineManagerAnalysis = self.create_manager(multipv, True)

        self._analysing: bool = False
        self._mrm: Optional[EngineResponse.MultiEngineResponse] = None

        self._move_played: Optional[Move.Move] = None

    def close(self):
        self.manager_analysis.close()

    def create_manager(self, multipv: str | int, create: bool) -> EngineManagerAnalysis.EngineManagerAnalysis:
        if not create:
            self.manager_analysis.close()
        return Code.procesador.analyzer_clone(0, 0, 0, multipv)

    def set_move_played(self, move: Move.Move):
        self._move_played = move

    def begin_analysis(self, game: Game.Game):
        self._move_played = None
        self._mrm = None
        self._analysing = True
        self.manager_analysis.analyze_tutor(
            game, dispacher_bestmove=self.bestmove_found, dispacher_changedepth=self.changed_depth
        )

    def end_now_analysis(self):
        if self._analysing:
            self.manager_analysis.stop()
            self._analysing = False

    def bestmove_found(self, _rm):
        self._analysing = False
        self._mrm = self.manager_analysis.get_current_mrm()

    def changed_depth(self, mrm: EngineResponse.MultiEngineResponse):
        self._mrm = mrm
        return True

    def get_mrm(self):
        return self._mrm

    def analysing(self):
        return self._analysing

    def change_multipv(self, multipv):
        self.manager_analysis.change_multipv(multipv)
