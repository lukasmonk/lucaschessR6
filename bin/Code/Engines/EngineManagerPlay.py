import os
import random
import time
from types import SimpleNamespace
from typing import Callable, Optional

from PySide6 import QtCore

from Code.Base import Game
from Code.Books import Books
from Code.Engines import EngineManager, EngineResponse, EngineRun, Engines, EnginesWicker


class PlayBook:
    book: Optional[Books.Book] = None
    num_tries: int = 0
    active: bool = False
    name: str

    def __init__(self, path, resp_type, max_tries, max_depth):
        self.name = str(os.path.basename(path)[:-4])
        self.path = path
        self.num_tries_max = max_tries
        self.select_type = resp_type
        self.max_depth = max_depth
        self.reset()

    def reset(self):
        self.book = Books.Book("P", self.name, self.path, True)
        self.book.polyglot()
        self.num_tries = 0
        self.active = True

    def check_move(
        self, game: Optional[Game.Game] = None, fen: Optional[str] = None
    ) -> Optional[EngineResponse.EngineResponse]:
        if not self.active:
            return None

        if game is not None:
            if self.max_depth:
                if len(game) > self.max_depth:
                    self.active = False
                    return None

            position = game.last_position
            fen = position.fen()

        pv = self.book.select_move_type(fen, self.select_type)
        if pv is None:
            self.num_tries += 1
            if self.num_tries > self.num_tries_max:
                self.active = False
            return None
        rm = EngineResponse.EngineResponse(self.name, " w " in fen)
        rm.from_sq = pv[:2]
        rm.to_sq = pv[2:4]
        rm.promotion = pv[4:6]
        rm.pv = pv
        return rm


class EngineManagerPlay(EngineManager.EngineManager):
    def __init__(self, engine: Engines.Engine, run_engine_params: EngineRun.RunEngineParams):
        super().__init__(engine, run_engine_params, False)

        self.playbook: Optional[PlayBook] = None
        self.playbook_active: bool = False
        self.seconds_humanize: float = 0

        # Ctrl engines Wicker is a change in engine options at the end of the game to engines of type Wicker.
        # Once this is done, it switches to None.
        self.wicker_ctrl: EnginesWicker.WickerCtrl | None = EnginesWicker.check_is_wicker(engine, self.engine_run)

    def check_previous(
        self, game: Optional[Game.Game] = None, fen: Optional[str] = None, dispacher: Optional[Callable] = None
    ):
        if not self.check_engine():
            return None
        resp = None

        if self.wicker_ctrl is not None:
            if fen is None:
                position = game.last_position
                fen = position.fen()
            if self.wicker_ctrl.check(fen=fen):
                self.wicker_ctrl = None

        if self.playbook_active:
            if fen is None:
                position = game.last_position
                fen = position.fen()
            rm = self.playbook.check_move(fen=fen)
            if rm:
                if dispacher:
                    dispacher(rm=rm)
                resp = rm
            else:
                self.playbook_active = self.playbook.active
        return resp

    def play_game(self, game, dispacher: Optional[Callable] = None) -> Optional[EngineResponse.EngineResponse]:
        return self.play(game=game, dispacher=dispacher)

    def play_fen(self, fen: str, dispacher: Optional[Callable] = None) -> Optional[EngineResponse.EngineResponse]:
        return self.play(fen=fen, dispacher=dispacher)

    def play(self, game: Optional[Game.Game] = None, fen: Optional[str] = None, dispacher: Optional[Callable] = None):
        rm = self.check_previous(game, fen, dispacher)
        if rm:
            return rm

        if self.engine_run is None:
            return None

        with_timer = (
            self.run_engine_params.fixed_nodes > 10000
            or self.run_engine_params.fixed_ms > 1000
            or self.run_engine_params.fixed_depth > 5
            or (
                self.run_engine_params.fixed_nodes
                + self.run_engine_params.fixed_ms
                + self.run_engine_params.fixed_depth
            )
            == 0
            or self.seconds_humanize > 0
        )
        state = SimpleNamespace(
            ini_time=time.time(), secs_humanize=self.seconds_humanize, with_timer=with_timer, found_bestmove=False
        )

        self.seconds_humanize = 0  # must be restarted each time
        self.is_canceled = False

        def check_state(bestmove):
            def close():
                if self.engine_run is not None:
                    try:
                        self.engine_run.bestmove_found.disconnect(check_state)
                    except (RuntimeError, TypeError):
                        pass
                if state.with_timer and timer is not None:
                    timer.stop()
                loop.quit()

            if self.engine_run is None:
                self.is_canceled = True
                close()
                return

            if dispacher and self.engine_run.mrm:
                if not dispacher(rm=self.engine_run.mrm.best_rm_ordered()):
                    self.is_canceled = True
                    close()

            if bestmove is not None:
                state.found_bestmove = True

            if state.found_bestmove:
                if state.secs_humanize > 0:
                    used_time = time.time() - state.ini_time
                    if used_time < state.secs_humanize:
                        return
                close()

        loop = QtCore.QEventLoop()
        timer = None
        try:
            self.engine_run.bestmove_found.connect(check_state)
            if game is not None:
                self.engine_run.set_game_position(game, None, False)
            else:
                self.engine_run.set_fen_position(fen)
            self.engine_run.play(self.run_engine_params)

            if state.with_timer:
                timer = QtCore.QTimer(loop)
                timer.setInterval(self.ms_refresh)
                timer.timeout.connect(lambda: check_state(None))
                timer.start()

            self.active_loop = loop
            loop.exec()
        except AttributeError:
            pass
        finally:
            self.active_loop = None
            try:
                if self.engine_run is not None:
                    self.engine_run.bestmove_found.disconnect(check_state)
            except (RuntimeError, TypeError):
                pass
            if timer is not None:
                timer.stop()

        if self.engine_run is None:
            return None

        if self.is_canceled:
            return None

        if self.engine_run.mrm is None:
            return None

        self.mrm = self.engine_run.mrm.clone()
        self.mrm.ordena()
        return self.mrm.best_rm_ordered()

    def humanize(
        self, factor_humanize: float, game: Game.Game, seconds_white: float, seconds_black: float, seconds_move: int
    ):
        # Hay que tener en cuenta
        # Si estamos en la apertura -> mas rápido
        # Si hay muchas opciones -> mas lento
        # Si hay pocas pieces
        # Si son las primeras 20 jugadas, el procentaje aumenta de 1 a 100
        # para el resto
        movestogo = 40
        last_position = game.last_position

        # Seconds per move, considering that each player has {movestogo} moves left
        if last_position.is_white:
            movetime_seconds = seconds_white + movestogo * seconds_move
        else:
            movetime_seconds = seconds_black + movestogo * seconds_move
        movetime_seconds = 0.9 * movetime_seconds / movestogo

        # If these are the first plays, the percentage is less than 100.
        porc = 100.0
        num_moves_played = last_position.num_moves
        if num_moves_played <= 20:
            porc = 10.0 + (last_position.num_moves - 1) * 4.5

        # If there are few movements to choose from, faster
        nmoves = len(last_position.get_exmoves())
        if nmoves < 6:
            if nmoves == 1:
                return
            x = 50.0 + nmoves * 10.0
            porc *= x / 100.0

        # First calc
        movetime_seconds *= porc / 100.0

        # We take into account the time it takes the player of last 5 moves
        if num_moves_played > 5:
            average_previous_user = game.average_mstime_user(5)
            if average_previous_user:
                # Up to 80% of the time taken by the player, with a maximum of 150% of the calculated time
                movetime_seconds = min(
                    max(0.8 * average_previous_user / 1000, movetime_seconds), movetime_seconds * 1.5
                )

        # max 45 seconds, and minimum between 1 and 3 seconds by the porc
        self.seconds_humanize = max(
            min(movetime_seconds * factor_humanize, 45), porc * random.randint(1000, 3000) / 100000
        )

    def play_nomodal(self, game: Optional[Game.Game]) -> bool:
        if not self.check_engine():
            return False
        self.engine_run.set_game_position(game, None, False)
        self.engine_run.play(self.run_engine_params)
        return True

    def set_book(self, path: str, resp_type, max_tries: int, max_depth):
        self.playbook = PlayBook(path, resp_type, max_tries, max_depth)
        self.playbook_active = True

    def reset_book(self):
        # en previsión de anulación de movimientos
        if self.playbook:
            self.playbook.reset()
            self.playbook_active = True
