import time

from Code.Adjudicator import Adjudicator
from Code.Base import Move, Game
from Code.Base.Constantes import (
    GT_AGAINST_PGN,
    ST_ENDGAME,
    ST_PLAYING,
    TB_CANCEL,
    TB_CLOSE,
    TB_CONFIG,
    TB_UTILITIES,
    TB_RESIGN,
    TB_ADJUDICATOR_STOP,
    TB_ADJUDICATOR,
    TB_TAKEBACK,
)
from Code.Expeditions import Everest
from Code.ManagerBase import Manager
from Code.QT import Iconos
from Code.QT import QTMessages
from Code.ZQT import WindowJuicio


class ManagerEverest(Manager.Manager):
    expedition: Everest.Expedition
    dic_analysis: dict
    comment: str | None
    is_human_side_white: bool
    game_obj: Game.Game
    analysis: tuple | None
    numJugadasObj: int
    pos_move_obj: int
    adjudicator: Adjudicator.Adjudicator
    initial_time: float
    puntos: int
    vtime: float
    name_obj: str
    show_all: bool

    def start(self, recno):

        self.expedition = Everest.Expedition(self.configuration, recno)
        self.expedition.run()

        self.dic_analysis = {}

        self.game_type = GT_AGAINST_PGN

        self.is_competitive = True
        self.resultado = None
        self.human_is_playing = False
        self.analysis = None
        self.comment = None
        self.is_analyzing = False
        self.is_human_side_white = self.expedition.is_white
        self.is_engine_side_white = not self.expedition.is_white
        self.game_obj = self.expedition.game
        self.game.set_tags(self.game_obj.li_tags)
        self.numJugadasObj = self.game_obj.num_moves()
        self.pos_move_obj = 0
        self.name_obj = self.expedition.name

        self.adjudicator = Adjudicator.Adjudicator(self, self.main_window, self.name_obj, self.player_has_moved)

        self.puntos = 0
        self.vtime = 0.0

        self.pon_toolbar()

        self.main_window.active_game(True, False)
        self.remove_hints(True, True)

        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.put_pieces_bottom(self.is_human_side_white)
        self.show_side_indicator(True)
        self.set_label1(self.expedition.label())
        self.set_label2("")

        self.pgn_refresh(True)
        self.show_info_extra()
        self.check_boards_setposition()

        self.state = ST_PLAYING
        self.play_next_move()

    def configurar_local(self):
        li_extra_options = [
            (
                "adjudicator_options",
                f"{_('Adjudicator')} - {_('Options')}",
                Iconos.Engines(),
            ),
        ]

        if resp := Manager.Manager.configurar(self, li_extra_options):
            if resp == "adjudicator_options":
                self.adjudicator.change_adjudicator_options()

    def thinking(self, ok):
        super().thinking(ok)
        self.pon_toolbar(stop_analysis=ok)

    def pon_toolbar(self, stop_analysis=False):
        li_tool = [TB_RESIGN, TB_CONFIG, TB_UTILITIES, TB_ADJUDICATOR]
        if stop_analysis:
            li_tool.append(TB_ADJUDICATOR_STOP)
        self.set_toolbar(li_tool)
        if stop_analysis:
            for tool in li_tool[:-1]:
                self.main_window.enable_option_toolbar(tool, False)

    def set_score(self):
        self.set_label2("%s : <b>%d</b>" % (_("Score"), self.puntos))

    def run_action(self, key):
        if key == TB_CANCEL:
            self.resign()

        elif key == TB_RESIGN:
            self.resign()

        elif key == TB_CONFIG:
            self.configurar()

        elif key == TB_TAKEBACK:
            return  # disable

        elif key == TB_UTILITIES:
            self.menu_utilities_elo()

        elif key == TB_ADJUDICATOR:
            self.adjudicator.change_adjudicator_options()

        elif key == TB_ADJUDICATOR_STOP:
            self.adjudicator.analyze_end()

        elif key == TB_CLOSE:
            self.finalize()

        elif key in self.procesador.li_opciones_inicio:
            self.procesador.run_action(key)

        else:
            self.routine_default(key)

    def final_x(self):
        return self.resign()

    def resign(self):
        if self.pos_move_obj > 1 and self.state == ST_PLAYING:
            self.restart(False)
        self.finalize()
        return False

    def finalize(self):
        self.procesador.start()
        self.procesador.showEverest(self.expedition.recno)

    def reiniciar(self):
        self.main_window.active_information_pgn(False)
        self.game.set_position()
        self.pos_move_obj = 0
        self.puntos = 0
        self.set_score()
        self.vtime = 0.0
        self.state = ST_PLAYING
        self.board.set_position(self.game.first_position)
        self.pgn_refresh(True)
        self.check_boards_setposition()

        self.set_label1(self.expedition.label())
        self.set_score()
        self.play_next_move()

    def restart(self, lost_points):
        change_game, is_last, is_last_last = self.expedition.add_try(False, self.vtime, self.puntos)
        self.vtime = 0.0
        licoment = []
        if lost_points:
            licoment.append(_("You have exceeded the limit of lost centipawns."))

        if change_game:
            licoment.append(_("You have exceeded the limit of tries, you will fall back to the previous."))
        elif lost_points:
            licoment.append(_("You must repeat the game"))
        if licoment:
            comment = "\n".join(licoment)
            QTMessages.message_information(self.main_window, comment)
        return change_game

    def play_next_move(self):
        if self.state == ST_ENDGAME:
            return

        if self.puntos < -self.expedition.tolerance:
            self.restart(True)
            self.state = ST_ENDGAME
            self.set_toolbar((TB_CLOSE, TB_CONFIG, TB_UTILITIES))
            return

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.put_view()
        is_white = self.game.last_position.is_white

        num_moves = len(self.game)
        if num_moves >= self.numJugadasObj:
            self.put_result()
            return

        is_rival = is_white == self.is_engine_side_white
        self.set_side_indicator(is_white)

        if is_rival:
            self.add_move(False)
            self.play_next_move()

        else:
            self.human_is_playing = True
            self.activate_side(is_white)
            self.initial_time = time.time()
            self.adjudicator.analyze_begin(self.game)

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
                self.name_obj,
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
            f"{self.name_obj}: {obj_move.pgn_translated()} {comentario_obj}\n"
            f"{self.configuration.x_player}: {user_move.pgn_translated()} {comentario_usu}\n"
            f"{comentario_puntos}"
        )

        self.add_move(True, comment, analysis, same_move=same_move)
        self.play_next_move()
        return True

    def add_move(self, is_player_move, comment=None, analysis=None, same_move=False):
        move = self.game_obj.move(self.pos_move_obj)
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

        change_game, is_last, is_last_last = self.expedition.add_try(True, self.vtime, self.puntos)

        if is_last:
            mensaje = _("Congratulations, goal achieved")
            if is_last_last:
                mensaje += f"\n\n{_('You have climbed Everest!')}"
        else:
            mensaje = _("Congratulations you have passed this game.")
        self.mensaje(mensaje)

        self.finalize()
