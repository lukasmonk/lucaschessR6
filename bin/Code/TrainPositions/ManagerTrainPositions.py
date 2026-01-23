import os
from typing import Optional

from PySide6.QtCore import Qt

from Code.Z import FNSLine, Util
from Code.Base import Game, Move
from Code.Base.Constantes import (
    GT_POSITIONS,
    INFINITE,
    ON_TOOLBAR,
    ST_ENDGAME,
    ST_PLAYING,
    TB_ADVICE,
    TB_CHANGE,
    TB_CLOSE,
    TB_COMMENTS,
    TB_CONFIG,
    TB_CONTINUE,
    TB_NEXT,
    TB_PGN_LABELS,
    TB_PREVIOUS,
    TB_REINIT,
    TB_TAKEBACK,
    TB_UTILITIES,
)
from Code.CompetitionWithTutor import WCompetitionWithTutor
from Code.Engines import EngineResponse
from Code.MainWindow import WindowSolve
from Code.ManagerBase import Manager
from Code.QT import Iconos, QTMessages, QTUtils
from Code.SQL import UtilSQL
from Code.Translations import TrListas
from Code.Tutor import Tutor


class ManagerTrainPositions(Manager.Manager):
    """Manager for training positions mode."""

    line_fns: FNSLine.FNSLine
    pos_obj: int
    game_obj: Optional[Game.Game]
    pos_training: int
    num_trainings: int
    title_training: str
    li_trainings: list[tuple[str, int]]
    is_automatic_jump: bool
    remove_solutions: bool
    advanced: bool
    entreno: str
    li_histo: list[int]
    pos_training_origin: int
    is_human_side_white: bool
    is_engine_side_white: bool
    reiniciando: bool
    is_rival_thinking: bool
    current_helps: int
    li_options_toolbar: list = []
    show_comments: bool
    mrm_tutor: Optional[EngineResponse.MultiEngineResponse] = None
    is_tutor_enabled: bool = False
    is_tutor_analysing: bool = False
    player_has_moved_a1h8: Optional[Move.Move] = None
    wsolve: WindowSolve.WSolve

    def set_training(self, entreno: str) -> None:
        """Set the current training file path."""
        self.entreno = entreno

    def save_pos(self, pos_training: int) -> None:
        """Save the last position reached in the training to the database."""
        with UtilSQL.DictSQL(self.configuration.paths.file_trainings()) as db:
            data = db[self.entreno]
            if data is None:
                data = {}
            data["POSULTIMO"] = pos_training
            db[self.entreno] = data

    def start(
        self,
        pos_training: int,
        num_trainings: int,
        title_training: str,
        li_trainings: list[tuple[str, int]],
        is_tutor_enabled: bool,
        is_automatic_jump: bool,
        remove_solutions: bool,
        show_comments: bool,
        advanced: bool,
    ) -> None:
        """Start the training session.

        Args:
            pos_training: Current position number.
            num_trainings: Total number of positions.
            title_training: Title of the training.
            li_trainings: List of training positions.
            is_tutor_enabled: Whether tutor is enabled.
            is_automatic_jump: Whether to auto-jump to next position.
            remove_solutions: Whether to remove solutions.
            show_comments: Whether to show comments.
            advanced: Whether advanced mode is active.
        """

        self.game_type = GT_POSITIONS
        if self.board.blindfold_something():
            self.board.blindfold_change()

        self.main_window.active_game(True, False)
        self.main_window.remove_hints(False, False)
        self.show_info_extra()
        self.set_dispatcher(self.player_has_moved_dispatcher)
        QTUtils.refresh_gui()

        self.the_next(
            pos_training,
            num_trainings,
            title_training,
            li_trainings,
            is_tutor_enabled,
            is_automatic_jump,
            remove_solutions,
            show_comments,
            advanced,
        )

    def the_next(
        self,
        pos_training: int,
        num_trainings: int,
        title_training: str,
        li_trainings: list[tuple[str, int]],
        is_tutor_enabled: Optional[bool],
        is_automatic_jump: bool,
        remove_solutions: bool,
        show_comments: bool,
        advanced: bool,
    ) -> None:
        """Load and prepare the next position in the training sequence.

        Args:
            pos_training: Position number to load.
            num_trainings: Total number of positions.
            title_training: Title of the training.
            li_trainings: List of training positions.
            is_tutor_enabled: Whether tutor is enabled (or None to use default).
            is_automatic_jump: Whether to auto-jump to next position.
            remove_solutions: Whether to remove solutions.
            show_comments: Whether to show comments.
            advanced: Whether advanced mode is active.
        """
        if hasattr(self, "reiniciando"):
            if self.reiniciando:
                return
        self.reiniciando = True

        if is_tutor_enabled is None:
            is_tutor_enabled = self.configuration.x_default_tutor_active

        self.pos_training = pos_training
        self.save_pos(pos_training)
        self.num_trainings = num_trainings
        self.title_training = title_training
        self.li_trainings = li_trainings
        self.is_automatic_jump = is_automatic_jump
        self.remove_solutions = remove_solutions
        self.advanced = advanced
        self.show_comments = show_comments

        self.li_histo = [self.pos_training]

        self.hints = INFINITE
        self.set_hints(self.hints)

        linea, self.pos_training_origin = self.li_trainings[self.pos_training - 1]
        self.line_fns = FNSLine.FNSLine(linea)
        if self.remove_solutions:
            self.line_fns.game_obj = None

        self.game_obj = self.line_fns.game_obj
        self.pos_obj = 0

        self.is_rival_thinking = False

        cp = self.line_fns.position

        is_white = cp.is_white

        if self.line_fns.with_game_original():
            self.game = self.line_fns.game_original
        else:
            self.game.set_position(cp)
            if self.game_obj:
                self.game.set_first_comment(self.game_obj.first_comment, True)
        self.game.pending_opening = False

        self.human_is_playing = False
        self.state = ST_PLAYING

        self.is_human_side_white = is_white
        self.is_engine_side_white = not is_white

        self.rm_rival = None

        self.is_tutor_enabled = is_tutor_enabled
        self.main_window.set_activate_tutor(self.is_tutor_enabled)

        self.ayudas_iniciales = 0

        self.set_toolbar_comments()

        self.set_position(self.game.last_position)
        self.show_side_indicator(True)
        self.put_pieces_bottom(is_white)
        titulo = f"<b>{TrListas.dic_training().get(self.title_training, self.title_training)}</b>"
        if self.line_fns.label:
            titulo += f"<br>{self.line_fns.label}"
        self.set_label1(titulo)
        if pos_training != self.pos_training_origin:
            self.set_label2(f"{_('Original position')}: {self.pos_training_origin}\n {pos_training} / {num_trainings}")
        else:
            self.set_label2(f"{pos_training} / {num_trainings}")
        self.pgn_refresh(True)

        if self.manager_rival is None:
            engine = self.configuration.engines.search(self.configuration.x_tutor_clave)
            self.manager_rival = self.procesador.create_manager_engine(
                engine,
                self.configuration.x_tutor_mstime,
                self.configuration.x_tutor_depth,
                0,
            )
        player = self.configuration.nom_player()
        other = self.manager_rival.engine.name
        w, b = (player, other) if self.is_human_side_white else (other, player)
        self.game.set_tag("White", w)
        self.game.set_tag("Black", b)

        self.is_analyzed_by_tutor = False
        self.continueTt = not self.configuration.x_engine_notbackground

        self.check_boards_setposition()

        if self.line_fns.with_game_original():
            self.repeat_last_movement()

        self.reiniciando = False
        self.is_rival_thinking = False
        self.is_analyzing = False
        self.current_helps = 0
        self.update_help()

        self.show_button_tutor(not self.is_playing_gameobj())

        if self.is_playing_gameobj() and self.advanced:
            self.board.show_coordinates(False)
            self.put_view()
            self.wsolve = self.main_window.base.wsolve
            self.wsolve.set_game(self.game_obj, self.advanced_return)

        else:
            self.play_next_move()

    def set_toolbar_comments(self, with_help: bool = True, with_continue: bool = False) -> None:
        li_options = [
            TB_CLOSE,
        ]
        if with_help and self.state == ST_PLAYING:
            li_options.append(TB_ADVICE)
        li_options.extend([TB_CHANGE, TB_REINIT])
        if not self.advanced:
            li_options.append(TB_TAKEBACK)
        li_options.append(TB_PGN_LABELS)
        li_options.extend((TB_CONFIG, TB_UTILITIES))
        if with_continue:
            li_options.append(TB_CONTINUE)
        if self.game_obj and self.game_obj.has_comments():
            self.main_window.base.set_title_toolbar(TB_COMMENTS, _("Disable") if self.show_comments else _("Enable"))
            li_options.append(TB_COMMENTS)
        if self.num_trainings > 1:
            li_options.extend((TB_PREVIOUS, TB_NEXT))

        if li_options != self.li_options_toolbar:
            self.li_options_toolbar = li_options
            self.set_toolbar(li_options)

    def advanced_return(self, solved: bool) -> None:
        self.wsolve.hide()
        self.board.show_coordinates(True)
        if solved:
            for move in self.game_obj.li_moves:
                self.game.add_move(move)
            self.goto_end()
            self.linea_terminada_opciones()

        else:
            self.advanced = False
            self.play_next_move()

    def run_action(self, key: str) -> None:
        if key == TB_CLOSE:
            self.end_game()

        elif key == TB_TAKEBACK:
            self.takeback()

        elif key == TB_REINIT:
            self.reiniciar()

        elif key == TB_CONFIG:
            if self.advanced:
                txt = _("Disable")
                ico = Iconos.Remove1()
            else:
                txt = _("Enable")
                ico = Iconos.Add()

            li_extra_options = [("lmo_advanced", f"{txt}: {_('Advanced mode')}", ico)]
            resp = self.configurar(with_sounds=True, li_extra_options=li_extra_options)
            if resp == "lmo_advanced":
                self.advanced = not self.advanced
                self.reiniciar()

        elif key == TB_CHANGE:
            self.ent_otro()

        elif key == TB_UTILITIES:
            if "/Tactics/" in self.entreno:
                li_extra_options = []
            else:
                li_extra_options = [
                    ("tactics", _("Create tactics training"), Iconos.Tacticas()),
                    (None, None, None),
                ]

            resp = self.utilities(li_extra_options)
            if resp == "tactics":
                self.create_tactics()

        elif key == TB_PGN_LABELS:
            self.pgn_informacion_menu()

        elif key in (TB_NEXT, TB_PREVIOUS):
            self.ent_siguiente(key)

        elif key == TB_CONTINUE:
            self.sigue()

        elif key == TB_ADVICE:
            self.help()

        elif key == TB_COMMENTS:
            self.change_comments()

        elif key in self.procesador.li_opciones_inicio:
            self.procesador.run_action(key)

        else:
            self.routine_default(key)

    def change_comments(self) -> None:
        self.show_comments = not self.show_comments
        self.main_window.base.set_title_toolbar(TB_COMMENTS, _("Disable") if self.show_comments else _("Enable"))

    def help(self) -> None:
        if self.advanced:
            self.wsolve.help()
        elif self.is_playing_gameobj() or self.is_tutor_enabled or self.is_active_analysys_bar():
            if self.is_playing_gameobj():
                move_obj: Move.Move = self.game_obj.move(self.pos_obj)
                from_sq = move_obj.from_sq
                to_sq = move_obj.to_sq
                promotion = move_obj.promotion
            elif self.is_tutor_enabled:
                mrm: EngineResponse.MultiEngineResponse
                if self.is_analyzed_by_tutor:
                    mrm = self.mrm_tutor
                else:
                    mrm = self.manager_tutor.ac_estado()

                if mrm and mrm.li_rm:
                    mrm.ordena()
                    rm: EngineResponse.EngineResponse = mrm.li_rm[0]
                    from_sq = rm.from_sq
                    to_sq = rm.to_sq
                    promotion = rm.promotion
                else:
                    return
            else:
                rm = self.bestmove_from_analysis_bar()
                if not rm:
                    return
                from_sq = rm.from_sq
                to_sq = rm.to_sq
                promotion = rm.promotion

            self.current_helps += 1
            if self.current_helps == 1:
                self.board.mark_position(from_sq)
            else:
                self.board.show_arrows_temp(([from_sq, to_sq, True],))
                if promotion and promotion.upper() != "Q":
                    dic = TrListas.dic_nom_pieces()
                    QTMessages.temporary_message(self.main_window, dic[promotion.upper()], 2.0)

    def reiniciar(self) -> None:
        if self.is_rival_thinking:
            self.manager_rival.stop()
        if self.is_analyzing:
            self.manager_tutor.stop()
        self.main_window.active_information_pgn(False)
        self.the_next(
            self.pos_training,
            self.num_trainings,
            self.title_training,
            self.li_trainings,
            self.is_tutor_enabled,
            self.is_automatic_jump,
            self.remove_solutions,
            self.show_comments,
            self.advanced,
        )

    def show_comment_move(self, pos: int) -> None:
        if not self.show_comments:
            return
        if not self.game_obj:
            return

        if pos < 0:
            comment = self.game_obj.first_comment
        else:
            comment = self.game_obj.move(pos).comment
        comment = comment.strip()
        if not comment:
            return
        if pos >= 0:
            move = self.game_obj.move(pos)
            text_move = f"{pos // 2 + 1}."
            if not move.is_white():
                text_move += ".."
            text_move += move.pgn_translated()
            if self.game_obj.first_position.is_white:
                delayed = pos % 2 == 1
            else:
                delayed = pos % 2 == 0
        else:
            text_move = _("Information")
            delayed = False

        QTMessages.message_menu(self.main_window.base.pgn, text_move, comment, delayed, zzpos=False)

    def ent_siguiente(self, tipo: str) -> None:
        if not self.advanced:
            if not (self.human_is_playing or self.state == ST_ENDGAME):
                return
        pos = self.pos_training + (+1 if tipo == TB_NEXT else -1)
        if pos > self.num_trainings:
            pos = 1
        elif pos == 0:
            pos = self.num_trainings
        self.the_next(
            pos,
            self.num_trainings,
            self.title_training,
            self.li_trainings,
            self.is_tutor_enabled,
            self.is_automatic_jump,
            self.remove_solutions,
            self.show_comments,
            self.advanced,
        )

    def control_teclado(self, nkey: int) -> None:
        if nkey in (Qt.Key.Key_Plus, Qt.Key.Key_PageDown):
            self.ent_siguiente(TB_NEXT)
        elif nkey in (Qt.Key.Key_Minus, Qt.Key.Key_PageUp):
            self.ent_siguiente(TB_PREVIOUS)

    @staticmethod
    def list_help_keyboard(add_key) -> None:
        add_key(f"-/{_('Page Up')}", _("Previous"))
        add_key(f"+/{_('Page Down')}", _("Next"))

    def end_game(self) -> None:
        self.state = ST_ENDGAME
        self.board.show_coordinates(True)
        self.procesador.start()

    def rival_dispatch(self, rm: EngineResponse.EngineResponse) -> bool:
        return self.state == ST_PLAYING

    def final_x0(self) -> bool:
        self.end_game()
        return False

    def takeback(self) -> None:
        if self.is_rival_thinking:
            return
        if len(self.game) and self.in_end_of_line():
            self.analyze_terminate()
            self.rm_rival = None
            self.game.remove_last_move(self.is_human_side_white)
            self.goto_end()
            self.is_analyzed_by_tutor = False
            self.state = ST_PLAYING
            self.refresh()
            self.play_next_move()

    def play_next_move(self) -> None:
        """Determines the next action in the game: engine's move, user's turn, or game end."""
        if self.state == ST_ENDGAME:
            if self.game_obj and self.is_automatic_jump:
                self.ent_siguiente(TB_NEXT)
            return

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.current_helps = 0
        self.put_view()

        is_white = self.game.last_position.is_white

        if self.game.is_finished():
            self.pon_resultado()
            return

        self.set_side_indicator(is_white)
        self.refresh()

        is_rival_move = is_white == self.is_engine_side_white

        self.show_comment_move(len(self.game) - 1)
        if is_rival_move:
            self.pon_help(False)
            self.play_rival()

        else:
            self.update_help()
            self.play_human(is_white)

    def play_human(self, is_white: bool) -> None:
        """Prepare for the human player's turn.

        Args:
            is_white: True if it's white's turn.
        """
        if self.game_obj and self.pos_obj == len(self.game_obj):
            self.linea_terminada_opciones()
            return

        self.human_is_playing = True
        self.activate_side(is_white)
        self.analyze_begin()

    def analyze_begin(self):
        self.mrm_tutor = None
        self.is_analyzed_by_tutor = False
        self.is_tutor_analysing = False
        if not self.is_tutor_enabled:
            return
        if self.is_playing_gameobj():
            return

        if not self.is_finished():
            self.is_tutor_analysing = True
            self.manager_tutor.analyze_tutor(self.game, self.analyze_bestmove_found, self.analyze_changedepth)

    def analyze_bestmove_found(self, bestmove):
        if self.is_tutor_analysing:
            self.mrm_tutor = self.manager_tutor.get_current_mrm()
            self.is_tutor_analysing = False
            self.main_window.pensando_tutor(False)
            if self.player_has_moved_a1h8:
                move = self.player_has_moved_a1h8
                self.player_has_moved_a1h8 = None
                self.player_has_moved(move, False)

    def analyze_changedepth(self, mrm: EngineResponse.MultiEngineResponse):
        if self.is_tutor_analysing:
            self.mrm_tutor = mrm

    def analyze_end(self):
        if self.is_tutor_analysing:
            self.manager_tutor.stop()

    def analyze_terminate(self):
        self.player_has_moved_a1h8 = None
        if self.is_tutor_analysing:
            self.is_tutor_analysing = False
            self.manager_tutor.stop()

    def player_has_moved_dispatcher(self, from_sq: str, to_sq: str, promotion: str = ""):
        """Viene desde el board via MainWindow, es previo, ya que si está pendiente el análisis, sólo se indica que ha
        elegido una jugada"""
        move = self.check_human_move(from_sq, to_sq, promotion)
        if not move:
            return False

        a1h8 = move.movimiento()
        ok = False
        is_playing_gameobj = self.is_playing_gameobj()
        if is_playing_gameobj:
            move_obj = self.game_obj.move(self.pos_obj)
            is_main, is_var = move_obj.check_a1h8(a1h8)
            if is_main:
                ok = True
                self.pos_obj += 1
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
            if not ok:
                self.beep_error()
                self.continue_human()
                return False

        if self.is_tutor_analysing:
            self.main_window.pensando_tutor(True)

            self.player_has_moved_a1h8 = move
            if not self.manager_tutor.is_run_fixed():
                self.analyze_end()
            return None

        return self.player_has_moved(move, is_playing_gameobj)

    def player_has_moved(self, move: Move.Move, is_playing_gameobj: bool) -> bool:

        if not is_playing_gameobj and self.is_tutor_enabled:
            from_sq = move.from_sq
            to_sq = move.to_sq
            a1h8 = move.movimiento()
            self.analyze_end()  # tiene que acabar siempre
            if self.mrm_tutor.better_move_than(a1h8):
                if not move.is_mate:
                    self.beep_error()
                    rm_user, n = self.mrm_tutor.search_rm(a1h8)
                    if not rm_user:
                        self.main_window.pensando_tutor(True)
                        self.is_tutor_analysing = True
                        self.is_analyzing = True
                        self.mrm_tutor = self.manager_tutor.analyze_tutor_move(self.game, a1h8)
                        self.state = ST_PLAYING
                        self.main_window.pensando_tutor(False)
                        rm_user, n = self.mrm_tutor.search_rm(a1h8)
                    move.analysis = self.mrm_tutor, n

                    tutor = Tutor.Tutor(self, move, from_sq, to_sq)

                    if tutor.elegir(True):
                        self.set_piece_again(from_sq)
                        from_sq = tutor.from_sq
                        to_sq = tutor.to_sq
                        promotion = tutor.promotion
                        si_bien, mens, move_tutor = Move.get_game_move(
                            self.game,
                            self.game.last_position,
                            from_sq,
                            to_sq,
                            promotion,
                        )
                        if si_bien:
                            move = move_tutor

                    del tutor
        self.mrm_tutor = None

        self.move_the_pieces(move.list_piece_moves)
        self.add_move(move, True)

        if self.game_obj and self.pos_obj >= len(self.game_obj):
            self.linea_terminada_opciones()

        self.play_next_move()
        return True

    def play_rival(self) -> None:
        """Execute the engine's move logic."""
        self.human_is_playing = False
        self.is_rival_thinking = True
        self.disable_all()

        is_obj = self.is_playing_gameobj()
        if is_obj:
            if self.game_obj and self.pos_obj == len(self.game_obj):
                self.is_rival_thinking = False
                self.linea_terminada_opciones()
                return
            move = self.game_obj.move(self.pos_obj)
            self.pos_obj += 1
            from_sq, to_sq, promotion = move.from_sq, move.to_sq, move.promotion

        else:
            self.thinking(True)
            self.rm_rival = self.manager_rival.play_game(self.game)
            self.thinking(False)
            if self.rm_rival is None or self.state == ST_ENDGAME:
                return
            from_sq, to_sq, promotion = (
                self.rm_rival.from_sq,
                self.rm_rival.to_sq,
                self.rm_rival.promotion,
            )

        self.is_rival_thinking = False
        ok, mens, move = Move.get_game_move(self.game, self.game.last_position, from_sq, to_sq, promotion)
        self.is_analyzed_by_tutor = False

        self.move_the_pieces(move.list_piece_moves, True)
        self.add_move(move, False)

        if is_obj and len(self.game_obj) == self.pos_obj:
            self.linea_terminada_opciones()

        self.play_next_move()

    def sigue(self) -> None:
        self.state = ST_PLAYING
        self.set_toolbar_comments(with_continue=False)
        self.game_obj = None
        self.show_button_tutor(True)
        self.play_next_move()
        self.update_help()

    def linea_terminada_opciones(self) -> bool:
        self.show_comment_move(len(self.game) - 1)
        self.pon_help(False)
        self.state = ST_ENDGAME
        if self.is_automatic_jump:
            self.ent_siguiente(TB_NEXT)
            return False
        else:
            QTMessages.temporary_message(self.main_window, _("Line completed"), 0.9, fixed_size=None)
            if not self.is_finished():
                self.set_toolbar_comments(with_continue=True)
            if not self.line_fns.with_game_original():
                li_tags = self.game.li_tags
                self.game = self.game_obj.copia()
                self.game.li_tags = li_tags
            self.goto_end()
            return False

    def pon_help(self, show: bool) -> None:
        if show:
            if TB_ADVICE not in self.li_options_toolbar:
                self.set_toolbar_comments(with_help=True)
        else:
            if TB_ADVICE in self.li_options_toolbar:
                self.set_toolbar_comments(with_help=False)

    def is_playing_gameobj(self) -> bool:
        if self.game_obj:
            move = self.game_obj.move(self.pos_obj)
            return move.position_before == self.game.last_position
        return False

    def add_move(self, move: Move.Move, is_our_move: bool) -> None:
        if self.is_playing_gameobj():
            move_obj = self.game_obj.move(self.pos_obj)
            move = move_obj.clone(self.game)
        self.game.add_move(move)

        self.check_boards_setposition()

        self.put_arrow_sc(move.from_sq, move.to_sq)
        self.beep_extended(is_our_move)

        self.pgn_refresh(self.game.last_position.is_white)
        self.refresh()

        if self.game.is_finished():
            self.pon_help(False)

    def pon_resultado(self) -> None:
        mensaje, beep, player_win = self.game.label_result_player(self.is_human_side_white)

        QTUtils.refresh_gui()
        QTMessages.message(self.main_window, mensaje)

        self.state = ST_ENDGAME
        self.disable_all()
        self.human_is_playing = False
        self.disable_all()
        self.refresh()

    def ent_otro(self) -> None:
        pos = WCompetitionWithTutor.edit_training_position(
            self.main_window,
            self.title_training,
            self.num_trainings,
            pos=self.pos_training,
        )
        if pos is not None:
            self.pos_training = pos
            self.reiniciar()

    def create_tactics(self) -> None:
        """Create a tactics training from the current training file."""
        name_tactic = os.path.basename(self.entreno)[:-4]

        nom_dir = Util.opj(self.configuration.paths.folder_tactics(), name_tactic)
        if os.path.isdir(nom_dir):
            nom = f"{nom_dir}-%d"
            n = 1
            while os.path.isdir(nom % n):
                n += 1
            nom_dir = nom % n
        nom_ini = Util.opj(nom_dir, "Config.ini")
        nom_tactic = "TACTIC1"
        Util.create_folder(nom_dir)
        nom_fns = Util.opj(nom_dir, "Puzzles.fns")

        # Se leen todos los fens
        with open(self.entreno, "rt", errors="ignore") as f:
            li_base = [linea.strip() for linea in f if linea.strip()]

        # Se crea el file con los puzzles
        nregs = len(li_base)
        tmp_bp = QTMessages.ProgressBarSimple(self.main_window, name_tactic, _("Working..."), nregs)
        tmp_bp.mostrar()
        with open(nom_fns, "wt", encoding="utf-8", errors="ignore") as q:
            for n in range(nregs):

                if tmp_bp.is_canceled():
                    break

                tmp_bp.pon(n + 1)

                linea = li_base[n]
                li = linea.split("|")
                fen = li[0]
                if len(li) < 3 or not li[2]:
                    # tutor a trabajar
                    mrm = self.manager_rival.analiza(fen)
                    if not mrm.li_rm:
                        continue
                    rm = mrm.li_rm[0]
                    p = Game.Game(fen=fen)
                    p.read_pv(rm.pv)
                    pts = rm.centipawns_abs()
                    move = p.move(0)
                    for pos, rm1 in enumerate(mrm.li_rm):
                        if pos:
                            if rm1.centipawns_abs() == pts:
                                p1 = Game.Game(fen=fen)
                                p1.read_pv(rm1.pv)
                                move.add_variation(p1)
                            else:
                                break

                    num_moves = p.pgn_base_raw()
                    txt = f"{fen}||{num_moves}\n"
                else:
                    txt = linea

                q.write(f"{txt}\n")

        tmp_bp.cerrar()

        # Se crea el file de control
        dic_ini = {}
        dic_ini[nom_tactic] = d = {}
        d["MENU"] = name_tactic
        d["FILESW"] = f"{os.path.basename(nom_fns)}:100"

        nom_dir = Util.relative_path(os.path.realpath(nom_dir))

        Util.dic2ini(nom_ini, dic_ini)

        name = os.path.basename(nom_dir)

        QTMessages.message(
            self.main_window,
            _("Tactic training %s created.") % nom_dir,
            explanation=_X(
                _("You can access this training from menu Train - Learn tactics by repetition - %1"),
                name,
            ),
        )

    def set_activate_tutor(self, enable: bool) -> None:
        self.main_window.set_activate_tutor(enable)
        self.is_tutor_enabled = enable
        self.update_help()

    def update_help(self) -> None:
        if self.is_finished():
            with_help = False
        elif self.is_playing_gameobj():
            with_help = True
        elif self.is_tutor_enabled:
            with_help = True
        elif self.is_active_analysys_bar():
            with_help = True
        else:
            with_help = False
        self.pon_help(with_help)
