import time

import FasterCode

from Code.Z import Util
from Code.Base import Game, Move
from Code.Base.Constantes import (
    GT_LEARN_PLAY,
    RS_WIN_OPPONENT,
    RS_WIN_PLAYER,
    ST_ENDGAME,
    ST_PLAYING,
    TB_CANCEL,
    TB_CLOSE,
    TB_CONFIG,
    TB_QUIT,
    TB_REINIT,
    TB_UTILITIES,
    TB_ADJUDICATOR
)
from Code.LearnGame import WindowPlayGame
from Code.ManagerBase import Manager
from Code.Openings import Opening, OpeningsStd
from Code.QT import QTMessages
from Code.ZQT import WindowJuicio
from Code.Adjudicator import Adjudicator


class ManagerPlayGame(Manager.Manager):
    is_human_side_white: bool
    is_human_side_black: bool
    game_obj: Game.Game
    close_on_exit = False
    name_obj_white: str
    name_obj_black: str
    is_analyzing: bool
    recno: int
    analysis: object
    comment = None
    numJugadasObj: int
    pos_move_obj: int
    is_save: bool
    puntosMax: int
    min_mstime: int
    puntos: int
    vtime: float
    book = None
    mrm = None
    mrm_tutor = None
    initial_time = None
    adjudicator: Adjudicator.Adjudicator

    def start(self, recno, is_white, is_black, close_on_exit=False):
        self.game_type = GT_LEARN_PLAY

        self.close_on_exit = close_on_exit

        db = WindowPlayGame.DBPlayGame(self.configuration.paths.file_play_game())
        reg = db.read_record(recno)
        db.close()

        game_obj = Game.Game()
        game_obj.restore(reg["GAME"])
        self.game.set_position(game_obj.first_position)
        self.name_obj_white = game_obj.get_tag("WHITE")
        self.name_obj_black = game_obj.get_tag("BLACK")
        label = db.label(recno)

        self.recno = recno
        self.resultado = None
        self.human_is_playing = False
        self.analysis = None
        self.comment = None
        self.is_analyzing = False
        self.is_human_side_white = is_white
        self.is_human_side_black = is_black
        self.numJugadasObj = game_obj.num_moves()
        self.game_obj = game_obj
        self.pos_move_obj = 0

        if is_white and is_black:
            self.auto_rotate = self.get_auto_rotate()

        self.is_save = False
        self.min_mstime = 5000

        self.adjudicator = Adjudicator.Adjudicator(self, self.main_window, self.name_obj_common(), self.player_has_moved)

        self.puntosMax = 0
        self.puntos = 0
        self.vtime = 0.0

        self.book = Opening.OpeningPol(999)

        self.set_toolbar((TB_CANCEL, TB_REINIT, TB_CONFIG, TB_UTILITIES, TB_ADJUDICATOR))

        self.main_window.active_game(True, False)
        self.remove_hints(True, True)

        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.put_pieces_bottom(self.is_human_side_white)
        self.show_side_indicator(True)
        self.set_label1(label)
        self.set_label2("")

        self.pgn_refresh(True)
        self.show_info_extra()
        self.check_boards_setposition()

        self.state = ST_PLAYING

        self.play_next_move()

    def name_obj(self):
        return self.name_obj_white if self.game.last_position.is_white else self.name_obj_black

    def name_obj_common(self):
        if self.is_human_side_black and self.is_human_side_white:
            return f"{self.name_obj_white}/{self.name_obj_black}"
        elif self.is_human_side_white:
            return self.name_obj_white
        else:
            return self.name_obj_black

    def set_score(self):
        lb_score = _("Score in relation to")
        self.set_label2(
            f'{lb_score}:<table border="1" cellpadding="5" cellspacing="0" style="margin-left:60px">'
            f'<tr><td align="right">{self.name_obj_common()}</td><td align="right"><b>{self.puntos:+d}'
            f'</b></td></tr>'
            f'<tr><td align="right">{self.manager_analyzer.name}</td>'
            f'<td align="right"><b>{-self.puntosMax:+d}</b></td>'
            '</tr></table>'
        )

    def run_action(self, key):
        if key == TB_CLOSE:
            if self.close_on_exit:
                self.procesador.run_action(TB_QUIT)
            else:
                self.procesador.start()
                self.procesador.play_game_show(self.recno)

        elif key == TB_CANCEL:
            if self.close_on_exit:
                self.run_action(TB_QUIT)
            else:
                self.cancelar()

        elif key == TB_REINIT:
            self.reiniciar(True)

        elif key == TB_CONFIG:
            self.configurar(with_sounds=True)

        elif key == TB_UTILITIES:
            self.menu_utilities_elo()

        elif key == TB_ADJUDICATOR:
            self.adjudicator.change_adjudicator_options()

        elif key in self.procesador.li_opciones_inicio:
            self.procesador.run_action(key)

        else:
            self.routine_default(key)

    def final_x(self):
        return self.cancelar()

    def cancelar(self):
        self.puntos = -999
        self.adjudicator.close()
        self.procesador.start()
        return False

    def reiniciar(self, with_question):
        if with_question:
            if not QTMessages.pregunta(self.main_window, _("Restart the game?")):
                return
        self.main_window.active_information_pgn(False)
        self.game.set_position(self.game_obj.first_position)
        self.pos_move_obj = 0
        self.puntos = 0
        self.puntosMax = 0
        self.set_score()
        self.vtime = 0.0
        self.book = Opening.OpeningPol(999)
        self.state = ST_PLAYING
        self.board.set_position(self.game.first_position)
        self.pgn_refresh(True)
        self.check_boards_setposition()
        self.adjudicator.analyze_end()
        self.show_info_extra()

        self.play_next_move()

    def valid_mrm(self, pv_usu, pv_obj, mrm_actual):
        move = self.game_obj.move(self.pos_move_obj)
        if move.analysis:
            mrm, pos = move.analysis
            ms_analisis = mrm.get_time()
            if ms_analisis > self.min_mstime:
                if mrm_actual.get_time() > ms_analisis and mrm_actual.contain(pv_usu) and mrm_actual.contain(pv_obj):
                    return None
                if mrm.contain(pv_obj) and mrm.contain(pv_usu):
                    return mrm
        return None

    def play_next_move(self):
        if self.state == ST_ENDGAME:
            return

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.put_view()
        is_white = self.game.last_position.is_white

        num_moves = len(self.game)
        if num_moves >= self.numJugadasObj:
            self.put_result()
            return

        if is_white:
            is_turn_human = self.is_human_side_white
        else:
            is_turn_human = self.is_human_side_black

        self.set_side_indicator(is_white)

        self.refresh()

        if is_turn_human:
            self.human_is_playing = True
            if self.auto_rotate:
                if is_white != self.board.is_white_bottom:
                    self.board.rotate_board()

            self.human_is_playing = True
            self.activate_side(is_white)
            self.initial_time = time.time()
            self.adjudicator.analyze_begin(self.game)
        else:
            self.add_move(False)
            self.play_next_move()

    def check_book(self, fen, from_sq, to_sq):
        if self.book.check_human(fen, from_sq, to_sq):
            return True
        FasterCode.set_fen(fen)
        FasterCode.make_move(from_sq + to_sq)
        fen1 = FasterCode.get_fen()
        fenm2 = FasterCode.fen_fenm2(fen1)
        return OpeningsStd.ap.is_book_fenm2(fenm2)

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        user_move = self.check_human_move(from_sq, to_sq, promotion)
        if not user_move:
            return False

        self.vtime += time.time() - self.initial_time

        self.board.set_position(user_move.position)
        self.put_arrow_sc(user_move.from_sq, user_move.to_sq)
        self.board.disable_all()

        obj_move = self.game_obj.move(self.pos_move_obj)

        self.thinking(True)

        self.adjudicator.check_moves(obj_move, user_move)

        return True

    def player_has_moved(self, user_move: Move.Move, book_moves=False):
        self.thinking(False)
        obj_move = self.game_obj.move(self.pos_move_obj)

        if book_moves:
            comentario_obj = comentario_usu = _("book move")
            analysis = None
            comentario_puntos = ""
        else:
            comentario_usu = ""
            comentario_obj = ""

            mrm = self.adjudicator.get_mrm()
            rm_obj, pos_obj = mrm.search_rm(obj_move.movimiento())
            rm_usu, pos_usu = mrm.search_rm(user_move.movimiento())

            analysis = mrm, pos_obj

            w = WindowJuicio.WJuicio(
                self,
                self.adjudicator,
                self.name_obj_common(),
                self.game.last_position,
                mrm,
                rm_obj,
                rm_usu,
                analysis,
                is_competitive=not self.adjudicator.show_all,
                continue_tt=self.adjudicator.is_analysing(),
            )
            w.exec()
            analysis = w.analysis
            dpts = w.difPuntos()
            self.puntos += dpts
            self.puntosMax += w.difPuntosMax()
            self.set_score()
            comentario_usu += f" {w.rm_usu.abbrev_text()}"
            comentario_obj += f" {w.rm_obj.abbrev_text()}"

            comentario_puntos = (
                f"{_('Score')} = {self.puntos - dpts} {w.rm_usu.centipawns_abs():+d} "
                f"{-w.rm_obj.centipawns_abs():+d} = {self.puntos}"
            )

        self.adjudicator.analyze_end()  # Por si acaso no lo está ya.

        same_move = user_move.movimiento() == obj_move.movimiento()
        if not same_move:
            self.board.remove_arrows()
            self.board.set_position(user_move.position_before)

        comment = (
            f"{self.name_obj()}: {obj_move.pgn_translated()} {comentario_obj}\n"
            f"{self.configuration.x_player}: {user_move.pgn_translated()} {comentario_usu}\n"
            f"{comentario_puntos}"
        )

        self.add_move(True, comment, analysis, same_move=same_move)
        self.play_next_move()
        return True

    def add_move(self, is_player_move, comment=None, analysis=None, same_move=False):
        move = self.game_obj.move(self.pos_move_obj).clone(self.game)
        self.pos_move_obj += 1
        if analysis is not None:
            move.analysis = analysis
        if comment:
            move.set_comment(comment)

        if comment:
            self.comment = f"{comment.replace('\n', '<br><br>')}<br>"

        if not is_player_move:
            if self.pos_move_obj:
                self.comment = None

        self.game.add_move(move)
        self.check_boards_setposition()
        if not same_move:
            self.move_the_pieces(move.list_piece_moves, True)
            self.board.set_position(move.position)
            self.board.remove_arrows()
            self.put_arrow_sc(move.from_sq, move.to_sq)
        self.beep_extended(is_player_move)

        self.pgn_refresh(self.game.last_position.is_white)
        self.refresh()

    def put_result(self):
        self.disable_all()
        self.human_is_playing = False

        self.state = ST_ENDGAME

        if self.puntos < 0:
            mensaje = _("Unfortunately you have lost.")
            quien = RS_WIN_OPPONENT
        else:
            mensaje = _("Congratulations you have won.")
            quien = RS_WIN_PLAYER

        self.beep_result_change(quien)

        self.message_on_pgn(mensaje)
        self.set_end_game()
        self.guardar()

    def guardar(self):
        db = WindowPlayGame.DBPlayGame(self.configuration.paths.file_play_game())
        reg = db.read_record(self.recno)

        dic_intento = {
            "DATE": Util.today(),
            "COLOR": ("w" if self.is_human_side_white else "") + ("b" if self.is_human_side_black else ""),
            "POINTS": self.puntos,
            "POINTSMAX": self.puntosMax,
            "TIME": self.vtime,
        }

        if "LIINTENTOS" not in reg:
            reg["LIINTENTOS"] = []
        reg["LIINTENTOS"].insert(0, dic_intento)

        if self.is_save:
            reg["GAME"] = self.game_obj.save()
            self.is_save = False

        db.change_record(self.recno, reg)

        db.close()
