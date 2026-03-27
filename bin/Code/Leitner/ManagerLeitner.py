import time

from Code.Base import Game
from Code.Base.Constantes import GT_TACTICS, ST_ENDGAME, ST_PLAYING, TB_ADVICE, TB_CLOSE, ON_TOOLBAR
from Code.Leitner import Leitner
from Code.ManagerBase import Manager
from Code.QT import QTMessages
from Code.Z import FNSLine


class ManagerLeitner(Manager.Manager):
    leitner: Leitner.Leitner
    leitner_db: Leitner.LeitnerDB
    line_fns: FNSLine.FNSLine
    pos_obj: int
    game_obj: Game.Game
    pos_db: int
    reg: Leitner.LeitnerReg
    label_puzzle: str
    requested_help: bool
    with_error: bool
    ini_clock: float

    def start(self, leitner_db, pos_db):
        self.leitner = leitner_db.get_leitner(pos_db)
        self.leitner_db = leitner_db
        self.pos_db = pos_db
        self.with_error = False

        self.is_tutor_enabled = False
        self.is_competitive = False

        self.reiniciar_puzzle()

    def reiniciar_puzzle(self):
        if len(self.leitner.current_ids_session) == 0:
            self.leitner.check_session()

            if self.leitner.is_the_end():
                message = _("Congratulations, goal achieved")
            else:
                message = _("Session finished")
            QTMessages.message(self.main_window, message)

            self.leitner_db.set_leitner(self.pos_db, self.leitner)
            self.finalizar()
            return

        reg_id = self.leitner.current_ids_session[0]
        self.reg = self.leitner.dic_regs[reg_id]

        # Parse FEN|Label|Solution|<game original>
        self.line_fns = FNSLine.FNSLine(self.reg.line)
        self.game_obj = self.line_fns.game_obj
        self.pos_obj = 0
        self.label_puzzle = self.line_fns.label

        self.requested_help = False
        self.with_error = False

        cp = self.game_obj.first_position
        if self.line_fns.with_game_original():
            self.game = self.line_fns.game_original
        else:
            self.game.set_position(cp)
            if self.game_obj:
                self.game.set_first_comment(self.game_obj.first_comment, True)
        self.game.pending_opening = False

        self.is_human_side_white = cp.is_white
        self.is_engine_side_white = not cp.is_white

        self.game.set_first_comment(self.game_obj.first_comment, True)
        self.game_type = GT_TACTICS

        self.main_window.active_information_pgn(True)
        self.main_window.set_activate_tutor(False)
        self.main_window.active_game(True, False)
        self.main_window.remove_hints(True, True)

        self.set_dispatcher(self.has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.show_side_indicator(True)
        self.put_pieces_bottom(self.is_human_side_white)

        self.set_label1(f"{self.leitner.reference} - {self.label_puzzle}")
        self.show_info_extra()
        self.set_toolbar([TB_CLOSE, TB_ADVICE])

        self.show_label_positions()
        self.state = ST_PLAYING

        self.pgn_refresh(self.is_human_side_white)
        if self.line_fns.with_game_original():
            self.repeat_last_movement()

        self.play_next_move()

    def show_label_positions(self):
        txt = f'{_("Puzzles pending in this session")}: {len(self.leitner.current_ids_session)}'
        html = f'<table border="1" align="center" cellpadding="5"><tr><td><h4>{txt}</h4></td></tr></table>'
        self.set_label2(html)

    def has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        move = self.check_human_move(from_sq, to_sq, promotion)
        if not move:
            return False

        move_obj = self.game_obj.move(self.pos_obj)
        is_main, is_var = move_obj.check_a1h8(move.movimiento())
        if is_main:
            self.add_move(True)
            self.play_next_move()
            return True
        elif is_var:
            mens = _("You have selected a correct move, but this line uses another one.")
            QTMessages.temporary_message(
                self.main_window,
                mens,
                2,
                physical_pos=ON_TOOLBAR,
                background="#C3D6E8",
            )
            li_movs = [
                (move.from_sq, move.to_sq, False),
                (move_obj.from_sq, move_obj.to_sq, True),
            ]
            self.board.show_arrows_temp(li_movs)
        else:
            self.with_error = True
            self.beep_error()
        self.continue_human()
        return False

    def puzzle_finished(self):
        success = not self.with_error
        self.state = ST_ENDGAME
        reg_id = self.leitner.current_ids_session[0]
        new_box = self.leitner.assign_result(reg_id, success)
        self.leitner.current_ids_session.remove(reg_id)
        self.leitner_db.set_leitner(self.pos_db, self.leitner)

        if new_box == self.leitner.win_box:
            txt = _("Position won!")
        else:
            txt = f'{_("Position sent to box")}: {new_box}'

        if success:
            txt = f'{_("Correct!")}<br>{txt}'
        else:
            txt = f'{_("There have been errors")}<br>{txt}'
        QTMessages.message(self.main_window, txt)
        self.with_error = False

        self.reiniciar_puzzle()

    def finalizar(self):
        if self.with_error:
            self.puzzle_finished()
        self.leitner_db.close()
        self.procesador.start()
        self.procesador.show_leitner(self.pos_db)

    def final_x(self):
        return self.finalizar()

    def run_action(self, key):
        if key == TB_CLOSE:
            self.finalizar()

        elif key == TB_ADVICE:
            move_obj = self.game_obj.move(self.pos_obj)
            self.board.mark_position(move_obj.from_sq)
            if self.with_error:
                self.board.show_one_arrow_temp(move_obj.from_sq, move_obj.to_sq, True)
            self.with_error = True

        else:
            self.routine_default(key)

    def play_next_move(self):
        if self.state == ST_ENDGAME:
            return

        self.human_is_playing = False
        is_white = self.game.last_position.is_white
        self.set_side_indicator(is_white)

        if self.pos_obj == len(self.game_obj) or self.game.is_mate():
            self.puzzle_finished()
            return

        is_white = self.game.last_position.is_white

        self.set_side_indicator(is_white)
        self.refresh()
        self.put_view()

        is_rival_move = is_white == self.is_engine_side_white

        if is_rival_move:
            self.play_rival()

        else:
            self.play_human()

    def play_rival(self):
        self.add_move(False)
        self.play_next_move()

    def play_human(self):
        self.human_is_playing = True
        self.activate_side(self.is_human_side_white)
        self.ini_clock = time.time()

    def add_move(self, is_our_move: bool) -> None:
        move_obj = self.game_obj.move(self.pos_obj)
        self.pos_obj += 1
        move = move_obj.clone(self.game)
        self.game.add_move(move)

        self.beep_extended(is_our_move)
        if not is_our_move:
            self.move_the_pieces(move.list_piece_moves, True)
        self.board.set_position(move.position)
        self.main_window.base.pgn.refresh()
        self.main_window.base.pgn.gobottom(1 if move.is_white() else 2)
        self.board.put_arrow_sc(move.from_sq, move.to_sq)
