from typing import Any

from Code.Base import Move, Position
from Code.Base.Constantes import (
    GT_WORLD_MAPS,
    ST_ENDGAME,
    ST_PLAYING,
    TB_CLOSE,
    TB_CONFIG,
    TB_REINIT,
    TB_UTILITIES,
)
from Code.ManagerBase import Manager
from Code.QT import QTUtils


class ManagerMateMap(Manager.Manager):
    workmap: Any
    player_win: bool
    is_rival_thinking: bool
    is_human_side_white: bool
    reiniciando: bool
    is_human_thinking: bool
    error: str

    def start(self, workmap):
        self.workmap = workmap

        self.hints = 0

        self.player_win = False

        initial_fen = workmap.fen_aim()

        self.is_rival_thinking = False

        etiqueta = ""
        if "|" in initial_fen:
            li = initial_fen.split("|")

            initial_fen = li[0]
            if initial_fen.endswith(" 0"):
                initial_fen = f"{initial_fen[:-1]}1"

            nli = len(li)
            if nli >= 2:
                etiqueta = li[1]

        cp = Position.Position()
        cp.read_fen(initial_fen)

        self.fen = initial_fen

        is_white = cp.is_white

        self.game.set_position(cp)

        self.game.pending_opening = False

        self.game_type = GT_WORLD_MAPS

        self.human_is_playing = False
        self.state = ST_PLAYING

        self.is_human_side_white = is_white
        self.is_engine_side_white = not is_white

        self.rm_rival = None

        self.is_tutor_enabled = False
        self.main_window.set_activate_tutor(False)

        self.ayudas_iniciales = 0

        li_options = [TB_CLOSE, TB_REINIT, TB_CONFIG, TB_UTILITIES]
        self.set_toolbar(li_options)

        self.main_window.active_game(True, False)
        self.main_window.remove_hints(True, True)
        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.show_side_indicator(True)
        self.put_pieces_bottom(is_white)
        self.set_label1(etiqueta)
        self.set_label2(workmap.name_aim())
        self.pgn_refresh(True)
        QTUtils.refresh_gui()

        if self.manager_rival is None:
            self.manager_rival = self.procesador.create_manager_engine(
                self.configuration.engines.engine_tutor(),
                self.configuration.x_tutor_mstime,
                None,
            )

        self.is_analyzed_by_tutor = False

        self.check_boards_setposition()

        self.reiniciando = False
        self.is_rival_thinking = False

        self.show_info_extra()

        self.play_next_move()

    def run_action(self, key):
        if key == TB_CLOSE:
            self.end_game()
            self.procesador.trainingMap(self.workmap.mapa)

        elif key == TB_REINIT:
            self.reiniciar()

        elif key == TB_CONFIG:
            self.configurar(with_sounds=True)

        elif key == TB_UTILITIES:
            self.utilities()

        else:
            self.routine_default(key)

    def reiniciar(self):
        if self.is_rival_thinking:
            return
        self.main_window.active_information_pgn(False)
        self.start(self.workmap)

    def end_game(self):
        self.procesador.start()

    def final_x(self):
        self.end_game()
        return False

    def play_next_move(self):
        if self.state == ST_ENDGAME:
            return
        self.is_human_thinking = False

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.put_view()

        is_white = self.game.last_position.is_white

        if self.game.is_finished():
            self.show_result()
            return

        self.set_side_indicator(is_white)
        self.refresh()

        si_rival = is_white == self.is_engine_side_white
        if si_rival:
            self.piensa_rival()

        else:
            self.human_is_playing = True
            self.activate_side(is_white)

    def piensa_rival(self):
        self.is_rival_thinking = True
        self.thinking(True)
        self.disable_all()

        self.rm_rival = self.manager_rival.play_game(self.game)

        self.thinking(False)
        from_sq, to_sq, promotion = (
            self.rm_rival.from_sq,
            self.rm_rival.to_sq,
            self.rm_rival.promotion,
        )

        if self.rival_has_moved(from_sq, to_sq, promotion):
            self.is_rival_thinking = False
            self.play_next_move()
        else:
            self.is_rival_thinking = False

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        move = self.check_human_move(from_sq, to_sq, promotion)
        if not move:
            return False

        self.move_the_pieces(move.list_piece_moves)
        self.add_move(move, True)
        self.error = ""
        self.play_next_move()
        return True

    def add_move(self, move, is_player_move):
        self.game.add_move(move)
        self.check_boards_setposition()

        self.put_arrow_sc(move.from_sq, move.to_sq)
        self.beep_extended(is_player_move)

        self.pgn_refresh(self.game.last_position.is_white)
        self.refresh()

    def rival_has_moved(self, from_sq, to_sq, promotion):
        ok, mens, move = Move.get_game_move(self.game, self.game.last_position, from_sq, to_sq, promotion)
        if ok:
            self.add_move(move, False)
            self.move_the_pieces(move.list_piece_moves, True)

            self.error = ""

            return True
        else:
            self.error = mens
            return False

    def show_result(self):
        self.disable_all()
        self.human_is_playing = False
        self.state = ST_ENDGAME

        mensaje, beep_result, player_win = self.game.label_result_player(self.is_human_side_white)

        self.player_win = player_win

        self.beep_result(beep_result)
        mensaje = _("Game ended")
        if player_win:
            mensaje = _("Congratulations you have won %s.") % self.workmap.name_aim()
            is_finished = self.workmap.win_aim(self.main_window, self.game.pv())
            if not is_finished:  # si ha terminado ya ha puesto el mensaje
                self.message_on_pgn(mensaje)
        else:
            self.message_on_pgn(mensaje)

        self.disable_all()
        self.refresh()

    def analize_position(self, row, key):
        if self.player_win:
            super().analize_position(row, key)
