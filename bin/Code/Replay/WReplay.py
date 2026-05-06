import time
from typing import Callable, Optional

from PySide6 import QtCore

import Code
from Code.Base.Constantes import (
    TB_CONTINUE_REPLAY,
    TB_END_REPLAY,
    TB_FAST_REPLAY,
    TB_PAUSE_REPLAY,
    TB_PGN_REPLAY,
    TB_REPEAT_REPLAY,
    TB_SETTINGS,
    TB_SLOW_REPLAY,
)
from Code.QT import QTUtils


class ParamsReplay:
    def __init__(self):
        self.key = "PARAMPELICULA"
        self.dic_data = self.read()

    def read(self):
        dic = {
            "SECONDS": 2.0,
            "START": True,
            "PGN": True,
            "BEEP": False,
            "CUSTOM_SOUNDS": False,
            "SECONDS_BEFORE": 0.0,
            "REPLAY_CONTINUOUS": False,
            "TRANSPARENCY": 0,
            "P_WHITE": False,
            "P_BLACK": False,
            "N_WHITE": False,
            "N_BLACK": False,
            "B_WHITE": False,
            "B_BLACK": False,
            "R_WHITE": False,
            "R_BLACK": False,
            "Q_WHITE": False,
            "Q_BLACK": False,
            "K_WHITE": False,
            "K_BLACK": False,
        }
        dic.update(Code.configuration.read_variables(self.key))
        return dic

    def edit(self, parent, with_previous_next):
        from Code.Replay import WReplayParams

        w = WReplayParams.WReplayParams(parent, self.dic_data, with_previous_next)
        if w.exec():
            self.dic_data = w.dvar
            return True
        return False


class Replay:
    def __init__(self, manager, next_game=None, rapidez=None):
        self.seconds: float = 0
        self.seconds_before: float = 0.01
        self.if_beep: bool = False
        self.if_custom_sounds: bool = False
        self.with_pgn: bool = False
        self.ghost_level: float = 0  # （0-1）
        self.dic_ghost_pieces: dict = {}
        self.board_create_piece: Optional[Callable] = None

        self.params = ParamsReplay()
        dic_var = self.params.dic_data
        self.manager = manager
        self.procesador = manager.procesador
        self.main_window = manager.main_window
        self.starts_with_black = manager.game.starts_with_black
        self.board = manager.board
        self.relee_params(dic_var)
        self.rapidez = 1.0 if rapidez is None else rapidez
        self.next_game = next_game
        self.if_start = True

        self.previous_visible_capturas = self.main_window.siCapturas
        self.previous_visible_information = self.main_window.siInformacionPGN

        self.li_acciones = (
            TB_END_REPLAY,
            TB_SLOW_REPLAY,
            TB_PAUSE_REPLAY,
            TB_CONTINUE_REPLAY,
            TB_FAST_REPLAY,
            TB_REPEAT_REPLAY,
            TB_PGN_REPLAY,
            TB_SETTINGS,
        )

        self.antAcciones = self.main_window.get_toolbar()
        self.main_window.pon_toolbar(self.li_acciones, separator=True)

        self.manager.set_routine_default(self.process_toolbar)

        self.show_pause(True, False)

        self.num_moves, self.jugInicial, self.filaInicial, self.is_white = self.manager.current_move()

        self.li_moves = self.manager.game.li_moves
        self.current_position = 0 if self.if_start else self.jugInicial
        self.initial_position = self.current_position
        self._initial_waited = self.seconds_before <= 0.0
        self._skip_id = 0
        self._active_animations = []

        self.stopped = False

        self.board.hide_selection()

        self.show_information()
        move = self.li_moves[self.current_position]
        self.board.set_position(move.position_before)

        if self.seconds_before > 0.0:
            if self.li_moves:
                move = self.li_moves[self.current_position]
                self.board.set_position(move.position_before)
                if not self.sleep_refresh(self.seconds_before):
                    return
                self._initial_waited = True

        self.show_current()

    def relee_params(self, dic_var):
        self.seconds = dic_var["SECONDS"]
        self.seconds_before = dic_var["SECONDS_BEFORE"]
        self.if_start = dic_var["START"]
        self.if_beep = dic_var["BEEP"]
        self.if_custom_sounds = dic_var["CUSTOM_SOUNDS"]
        self.with_pgn = dic_var["PGN"]

        self.ghost_level = dic_var.get("TRANSPARENCY", 0) / 100.0
        self.dic_ghost_pieces = {
            "P": dic_var.get("P_WHITE", False),
            "p": dic_var.get("P_BLACK", False),
            "N": dic_var.get("N_WHITE", False),
            "n": dic_var.get("N_BLACK", False),
            "B": dic_var.get("B_WHITE", False),
            "b": dic_var.get("B_BLACK", False),
            "R": dic_var.get("R_WHITE", False),
            "r": dic_var.get("R_BLACK", False),
            "Q": dic_var.get("Q_WHITE", False),
            "q": dic_var.get("Q_BLACK", False),
            "K": dic_var.get("K_WHITE", False),
            "k": dic_var.get("K_BLACK", False),
        }
        self.update_ghost()

    def update_ghost(self):
        if self.ghost_level > 0.0:
            if self.board.create_piece != self.create_piece:
                self.board_create_piece = self.board.create_piece
                self.board.create_piece = self.create_piece
        else:
            if self.board_create_piece is not None:
                self.board.create_piece = self.board_create_piece

        for pz, pz_sc, x in self.board.li_pieces:
            if self.ghost_level > 0.0 and self.dic_ghost_pieces.get(pz, False):
                pz_sc.setOpacity(1.0 - self.ghost_level)
            else:
                pz_sc.setOpacity(1.0)

    def create_piece(self, cpieza, pos_a1_h8):
        pz_sc = self.board_create_piece(cpieza, pos_a1_h8)
        if self.ghost_level > 0.0:
            if self.dic_ghost_pieces.get(cpieza, False):
                pz_sc.setOpacity(1.0 - self.ghost_level)
        return pz_sc

    def sleep_refresh(self, seconds):
        ini_time = time.time()
        while (time.time() - ini_time) < seconds:
            QTUtils.refresh_gui()
            if self.stopped:
                return False
            QTUtils.delay(10)
        return True

    def show_information(self):
        if self.with_pgn:
            if self.previous_visible_information:
                self.main_window.active_information_pgn(True)
            if self.previous_visible_capturas:
                self.main_window.siCapturas = True
            self.main_window.base.show_replay()
        else:
            if self.previous_visible_information:
                self.main_window.active_information_pgn(False)
            if self.previous_visible_capturas:
                self.main_window.siCapturas = False
            self.main_window.base.hide_replay()
        QTUtils.refresh_gui()

    def show_current(self):
        if self.stopped or self.current_position >= len(self.li_moves):
            return

        move = self.li_moves[self.current_position]
        if self.current_position > self.initial_position:
            if not self.sleep_refresh(self.seconds / self.rapidez):
                return
        elif not self._initial_waited:
            if not self.sleep_refresh(self.seconds_before):
                return
            self._initial_waited = True
        li_movs = [("b", move.to_sq), ("m", move.from_sq, move.to_sq)]
        if move.position.li_extras:
            li_movs.extend(move.position.li_extras)
        self.move_the_pieces(li_movs)

        self._skip_id += 1
        skip_id = self._skip_id
        QtCore.QTimer.singleShot(0, lambda xskip_id=skip_id: self.skip(xskip_id))

    def move_the_pieces(self, li_movs):
        if self.stopped:
            return
        self.procesador.cpu.stop()

        move = self.li_moves[self.current_position]
        num = self.current_position
        if self.starts_with_black:
            num += 1
        row = int(num / 2)
        self.main_window.end_think_analysis_bar()
        self.main_window.place_on_pgn_table(row, move.position_before.is_white)
        self.main_window.base.pgn_refresh()

        self.board.animate_move(li_movs, rapidez=self.rapidez, active_animations_out=self._active_animations)

        if self.stopped:
            return

        for movim in li_movs:
            if movim[0] == "b":
                self.board.remove_piece(movim[1])

        if self.stopped:
            return

        for movim in li_movs:
            if movim[0] == "c":
                self.board.change_piece(movim[1], movim[2])

        if self.stopped:
            return

        wait_seconds = 0.0
        if self.if_custom_sounds:
            wait_seconds = Code.runSound.play_list_seconds(move.sounds_list())
        if wait_seconds == 0.0 and self.if_beep:
            Code.runSound.play_beep()

        if self.stopped:
            return
        self.manager.put_arrow_sc(move.from_sq, move.to_sq)

        self.board.set_position(move.position)

        if self.stopped:
            return

        self.manager.put_view()
        if self.stopped:
            return
        if wait_seconds:
            self.sleep_refresh(wait_seconds / 1000 + 0.2)

    def show_pause(self, si_pausa, si_continue):
        self.main_window.show_option_toolbar(TB_PAUSE_REPLAY, si_pausa)
        self.main_window.show_option_toolbar(TB_CONTINUE_REPLAY, si_continue)

    def process_toolbar(self, key):
        if key == TB_END_REPLAY:
            self.finalize()
        elif key == TB_SLOW_REPLAY:
            self.lento()
        elif key == TB_PAUSE_REPLAY:
            self.pausa()
        elif key == TB_CONTINUE_REPLAY:
            self.seguir()
        elif key == TB_FAST_REPLAY:
            self.rapido()
        elif key == TB_REPEAT_REPLAY:
            self.repetir()
        elif key == TB_PGN_REPLAY:
            self.with_pgn = not self.with_pgn
            self.show_information()

        elif key == TB_SETTINGS:
            self.pausa()
            if self.params.edit(self.main_window, False):
                self.relee_params(self.params.dic_data)
                self.show_information()

    def finalize(self):
        if self.ghost_level > 0.0:
            for pz, pz_sc, x in self.board.li_pieces:
                pz_sc.setOpacity(1.0)
            self.board.create_piece = self.board_create_piece
        self.stopped = True
        self.main_window.pon_toolbar(self.antAcciones)
        self.manager.set_routine_default(None)
        self.manager.xpelicula = None
        for animation in self._active_animations:
            try:
                animation.stop()
            except Exception:
                pass
        self._active_animations = []
        if self.previous_visible_capturas:
            self.main_window.siCapturas = True
        if not self.with_pgn:
            self.with_pgn = True
            self.show_information()

    def lento(self):
        self.rapidez /= 1.2

    def rapido(self):
        self.rapidez *= 1.2

    def pausa(self):
        self.stopped = True
        self.show_pause(False, True)

    def seguir(self):
        if self.current_position >= self.num_moves:
            self.repetir()
            return
        num_moves, self.current_position, filaInicial, is_white = self.manager.current_move()
        self.current_position += 1
        self.stopped = False
        self.show_pause(True, False)
        self.show_current()

    def repetir(self):
        if not self.li_moves:
            return
        self._skip_id += 1
        self.finalize()
        QtCore.QTimer.singleShot(
            0,
            lambda: setattr(
                self.manager,
                "xpelicula",
                Replay(
                    self.manager,
                    next_game=self.next_game,
                    rapidez=self.rapidez,
                ),
            ),
        )

    def skip(self, skip_id=None):
        if skip_id is not None and skip_id != self._skip_id:
            return
        if self.stopped:
            return
        self.current_position += 1
        if self.current_position >= self.num_moves:
            if self.next_game:
                if self.next_game():
                    self.jugInicial = 0
                    self.current_position = 0
                    self.initial_position = 0
                    self.if_start = True
                    self.antAcciones = self.main_window.get_toolbar()
                    self.main_window.pon_toolbar(self.li_acciones, separator=False)
                    self.li_moves = self.manager.game.li_moves
                    self.num_moves = len(self.li_moves)
                    if self.seconds_before > 0.0:
                        move = self.li_moves[self.current_position]
                        self.board.set_position(move.position_before)
                        if not self.sleep_refresh(self.seconds_before):
                            return
                    self.show_current()
                    return
            self.pausa()
        else:
            self.show_current()
