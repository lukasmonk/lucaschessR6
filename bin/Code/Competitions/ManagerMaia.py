import os


import Code
from Code.Base import Move
from Code.Base.Constantes import (
    WHITE,
    BLACK,
    GT_MAIA,
    RS_WIN_OPPONENT,
    RS_WIN_PLAYER,
    RS_DRAW,
    ST_ENDGAME,
    ST_PLAYING,
    TB_CANCEL,
    TB_CONFIG,
    TB_DRAW,
    TB_RESIGN,
    TB_UTILITIES,
)
from Code.Engines import EngineResponse, Engines
from Code.ManagerBase import Manager
from Code.Openings import Opening
from Code.QT import QTMessages


class MaiaState:
    current: int
    white: int
    black: int
    last: bool
    key: str = "MAIALADDER"
    engine: Engines.Engine
    book_path: str
    MOVE_FORWARD = 1
    MOVE_BACKWARD = 2
    NOMOVE = 3
    WINNER = 4

    def __init__(self):
        self.read()

    def read(self):
        dic = Code.configuration.read_variables(self.key)
        self.current = dic.get("current", 1100)
        self.white = dic.get("white", 0)
        self.black = dic.get("black", 0)
        self.last = dic.get("last", BLACK)
        self.engine = Code.configuration.engines.search(f"maia-{self.current}")

        base = os.path.dirname(self.engine.path_exe)
        if self.current < 1500:
            book = "1100-1500"
        elif self.current < 2000:
            book = "1600-1900"
        else:
            book = "2200"
        self.book_path = os.path.join(base, f"{book}.bin")

    def write(self):
        dic = {
            "current": self.current,
            "white": self.white,
            "black": self.black,
            "last": self.last
        }
        Code.configuration.write_variables(self.key, dic)

    def get_side(self):
        return WHITE if self.last == BLACK else BLACK

    def get_engine(self):
        return self.engine

    def get_book_path(self):
        return self.book_path

    def new_result(self, is_white, result):
        if result == RS_WIN_PLAYER:
            if is_white:
                self.white = 1
            else:
                self.black = 1
        elif result == RS_WIN_OPPONENT:
            if is_white:
                self.white = -1
            else:
                self.black = -1
        else:  # Draw
            pass

        self.last = is_white

        resp = self.NOMOVE

        if self.white == 1 and self.black == 1:
            resp = self.forward()
            self.white = 0
            self.black = 0
        elif self.white == -1 and self.black == -1:
            resp = self.backward()
            self.white = 0
            self.black = 0

        self.write()
        return resp

    def forward(self):
        if self.current == 2200:
            self.current = 2300
            return self.WINNER
        if self.current < 1900:
            self.current += 100
        else:
            self.current = 2200
        return self.MOVE_FORWARD

    def backward(self):
        if self.current == 1100:
            return self.NOMOVE
        if self.current == 2200:
            self.current = 1900
        elif self.current > 1100:
            self.current -= 100
        return self.MOVE_BACKWARD

    def label(self):
        return f"Maia-{self.current}"

    def stats(self):
        st = {1: "🟢", -1: "🔴", 0: "⚪"}
        sp = "&nbsp;"
        return f'{st.get(self.white, "⚪")} {_("White")} {sp * 5} {st.get(self.black, "⚪")} {_("Black")}'

    def current_elo(self):
        if self.current <= 1900:
            return self.current - 100
        elif self.current == 2200:
            return 1900
        else:
            return 2200

    def set_current_elo(self, new_current_elo):
        if new_current_elo < 1900:
            nc = new_current_elo + 100
        elif new_current_elo >= 2200:
            nc = 2300
        else:
            nc = 1900
        self.current = nc
        self.white = self.black = 0
        self.write()

    def is_finished(self):
        return self.current > 2200


class ManagerMaia(Manager.Manager):
    error: str
    is_human_side_white: bool
    in_the_opening: bool
    white_elo: int
    black_elo: int
    opening: Opening.OpeningPol
    pte_tool_resigndraw: bool
    ladder_state: MaiaState
    maia_engine: Engines.Engine

    def start(self):
        self.base_inicio()
        self.play_next_move()

    def base_inicio(self):
        self.game_type = GT_MAIA

        self.ladder_state = MaiaState()

        self.is_competitive = True

        self.resultado = None
        self.human_is_playing = False
        self.state = ST_PLAYING

        is_white = self.ladder_state.get_side()

        self.is_human_side_white = is_white
        self.is_engine_side_white = not is_white

        self.lirm_engine = []
        self.next_test_resign = 5
        self.resign_limit = -1000

        self.is_tutor_enabled = False
        self.main_window.set_activate_tutor(False)

        self.hints = 0
        self.ayudas_iniciales = self.hints

        self.in_the_opening = True

        self.opening = Opening.OpeningPol(999, file=self.ladder_state.get_book_path())

        self.maia_engine = self.ladder_state.get_engine()
        rival = self.configuration.engines.search(self.maia_engine.key)
        self.manager_rival = self.procesador.create_manager_engine(rival, 0, 0, 1)

        self.pte_tool_resigndraw = True

        self.pon_toolbar()

        self.main_window.active_game(True, False)
        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.put_pieces_bottom(is_white)
        self.remove_hints(True, remove_back=True)
        self.show_side_indicator(True)
        label = f"{_('Opponent')}: <b>{self.ladder_state.label()}</b>"
        self.set_label1(label)

        txt = self.ladder_state.stats()

        self.set_label2(f"<center>{txt}</center>")
        self.pgn_refresh(True)
        self.show_info_extra()

        self.check_boards_setposition()

        self.game.set_tag("Event", _("Maia Ladder"))

        player = self.configuration.nom_player()
        other = self.maia_engine.name
        w, b = (player, other) if self.is_human_side_white else (other, player)
        self.game.set_tag("White", w)
        self.game.set_tag("Black", b)

        self.game.add_tag_timestart()

    def pon_toolbar(self):
        li_tool = (TB_CANCEL, TB_CONFIG, TB_UTILITIES)
        if self.pte_tool_resigndraw and len(self.game) > 1:
            li_tool = (TB_RESIGN, TB_DRAW, TB_CONFIG, TB_UTILITIES)
            self.pte_tool_resigndraw = False

        self.set_toolbar(li_tool)

    def run_action(self, key):
        if key in (TB_RESIGN, TB_CANCEL):
            self.rendirse()

        elif key == TB_DRAW:
            self.check_draw_player()

        elif key == TB_CONFIG:
            self.configurar(with_sounds=True)

        elif key == TB_UTILITIES:
            self.menu_utilities_elo()

        elif key in self.procesador.li_opciones_inicio:
            self.procesador.run_action(key)

        else:
            self.routine_default(key)

    def final_x(self):
        return self.rendirse()

    def rendirse(self):
        if self.state == ST_ENDGAME:
            return True
        if not self.pte_tool_resigndraw:
            if not QTMessages.pregunta(self.main_window, _("Do you want to resign?")):
                return False  # no abandona
            self.game.resign(self.is_human_side_white)
            self.show_result()
        else:
            self.procesador.start()

        return False

    def play_next_move(self):

        if self.state == ST_ENDGAME:
            return

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.put_view()
        is_white = self.game.last_position.is_white

        if self.game.is_finished():
            self.show_result()
            return

        is_rival = is_white == self.is_engine_side_white
        self.set_side_indicator(is_white)

        self.refresh()

        if is_rival:
            self.thinking(True)
            self.disable_all()

            rm_rival = None

            if self.in_the_opening:
                ok, from_sq, to_sq, promotion = self.opening.run_engine(self.last_fen())

                if ok:
                    rm_rival = EngineResponse.EngineResponse("Opening", self.is_engine_side_white)
                    rm_rival.from_sq = from_sq
                    rm_rival.to_sq = to_sq
                    rm_rival.promotion = promotion

            if rm_rival is None:
                factor_humanize = 0.8
                self.manager_rival.humanize(factor_humanize, self.game, 600, 600, 0)
                rm_rival = self.manager_rival.play_game(self.game)

            self.thinking(False)
            if self.rival_has_moved(rm_rival):
                self.lirm_engine.append(rm_rival)
                if self.evaluate_rival_rm():
                    self.play_next_move()
                else:
                    self.show_result()
                    return
        else:
            self.human_is_playing = True
            self.activate_side(is_white)

    def show_result(self):
        self.state = ST_ENDGAME
        self.disable_all()
        self.human_is_playing = False

        mensaje, beep, player_win = self.game.label_result_player(self.is_human_side_white)

        self.beep_result(beep)

        if player_win:
            result = RS_WIN_PLAYER
        elif self.game.is_draw():
            result = RS_DRAW
        else:
            result = RS_WIN_OPPONENT

        ladder_resp = self.ladder_state.new_result(self.is_human_side_white, result)

        if ladder_resp == MaiaState.MOVE_FORWARD:
            mensaje += "\n\n" + _("Congratulations! You move up to the next level.")
        elif ladder_resp == MaiaState.MOVE_BACKWARD:
            mensaje += "\n\n" + _("You move down to the previous level.")
        elif ladder_resp == MaiaState.WINNER:
            mensaje += "\n\n" + _("AMAZING! You have completed the Maia Ladder!")

        self.set_label2("")

        self.mensaje(mensaje)
        self.set_end_game()
        self.autosave()

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        move = self.check_human_move(from_sq, to_sq, promotion)
        if not move:
            return False

        if self.in_the_opening:
            self.in_the_opening = self.opening.check_human(self.last_fen(), from_sq, to_sq)

        self.move_the_pieces(move.list_piece_moves)

        self.add_move(move, True)
        self.error = ""
        self.play_next_move()
        return True

    def add_move(self, move, is_player_move):
        self.game.add_move(move)

        self.put_arrow_sc(move.from_sq, move.to_sq)
        self.beep_extended(is_player_move)

        # self.set_hints( self.hints )

        self.pgn_refresh(self.game.last_position.is_white)
        self.refresh()

        self.check_boards_setposition()

        if self.pte_tool_resigndraw:
            self.pon_toolbar()

    def rival_has_moved(self, engine_response):
        from_sq = engine_response.from_sq
        to_sq = engine_response.to_sq

        promotion = engine_response.promotion

        ok, mens, move = Move.get_game_move(self.game, self.game.last_position, from_sq, to_sq, promotion)
        if ok:
            self.add_move(move, False)
            self.move_the_pieces(move.list_piece_moves, True)

            self.error = ""

            return True
        else:
            self.error = mens
            return False
