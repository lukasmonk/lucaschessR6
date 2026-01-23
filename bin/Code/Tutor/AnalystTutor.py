from enum import Enum, auto
from typing import Optional, Callable

import Code
from Code.Base import Game, Move
from Code.Engines import EngineManagerAnalysis, EngineResponse


class AnalystTutorState(Enum):
    analysing = auto()  # Análizando
    active = auto()  # No hace nada el motor, a la espera de ordenes
    closing = auto()  # Cerrando, si está analizando se lanza un stop y bestmove se encarga de cerrar


class AnalystTutor:
    manager_tutor: Optional[EngineManagerAnalysis.EngineManagerAnalysis]
    mrm: Optional[EngineResponse.MultiEngineResponse]
    move_played: Optional[Move.Move]
    _rut_player_move: Optional[Callable]
    user_move: Optional[Move.Move]
    state: AnalystTutorState

    def __init__(self, rut_player_move: Callable):
        self._rut_player_move: Callable = rut_player_move

        self.manager_tutor = self.open_manager_tutor()

        self.mrm = None
        self.game = None
        self.state: AnalystTutorState = AnalystTutorState.active

    @staticmethod
    def open_manager_tutor():
        return Code.procesador.create_manager_tutor()

    def maximize_multipv(self):
        self.manager_tutor.maximize_multipv()

    def analyze_begin(self, game: Game.Game):
        self.game = game
        self.state = AnalystTutorState.analysing
        self.mrm = None
        self.user_move = None
        dispatcher_bestmove = self.bestmove_found
        self.manager_tutor.analyze_tutor(
            game, dispacher_bestmove=dispatcher_bestmove, dispacher_changedepth=self.changed_depth
        )

    def analyze_end(self):
        if self.is_analysing():
            self.manager_tutor.stop()

    def is_analysing(self):
        return self.state == AnalystTutorState.analysing

    def changed_depth(self, mrm):
        self.mrm = mrm
        return True

    def get_mrm(self):
        return self.mrm

    def is_run_fixed(self):
        return self.manager_tutor.is_run_fixed()

    def set_move_played(self, user_move: Move.Move):
        self.user_move = user_move
        if not self.is_analysing():
            self.ensure_move()
            self._rut_player_move(self.user_move)

    def close(self):
        if self.manager_tutor is not None:
            if self.is_analysing():
                # Está trabajando, esperamos a que se cierre en bestmove, tras parar con stop
                self.manager_tutor.connect_bestmove(self.bestmove_found)  # Aseguramos que exista
                self.state = AnalystTutorState.closing
                self.manager_tutor.stop()

            else:
                # No está trabajando, cerramos directamente
                self.manager_tutor.close()
                self.manager_tutor = None

    def bestmove_found(self, _bestmove):
        # Solo para cuando el tiempo de análisis es un tiempo fijo y para cerrar el motor cuando está trabajando

        if self.state == AnalystTutorState.analysing:
            self.mrm = self.manager_tutor.get_current_mrm()
            self.state = AnalystTutorState.active
            if self.user_move is not None:
                self.ensure_move()
                self._rut_player_move(self.user_move)
            return

        # Si está cerrando, ya podemos cerrar bien
        if self.state == AnalystTutorState.closing:
            self.close()

    def ensure_move(self):
        a1h8 = self.user_move.movimiento()
        rm, pos = self.mrm.search_rm(a1h8)
        if rm is None:
            self.analyze_end()
            self.state = AnalystTutorState.active
            self.mrm = self.manager_tutor.analyze_tutor_move(self.game, self.user_move.movimiento())
