from Code.Base import Move
from Code.Base.Constantes import (
    GT_RESISTANCE,
    ST_ENDGAME,
    ST_PLAYING,
    TB_CLOSE,
    TB_CONFIG,
    TB_REINIT,
    TB_RESIGN,
    TB_UTILITIES,
)
from Code.ManagerBase import Manager
from Code.Menus import TrainMenu
from Code.QT import QTMessages
from Code.Z import Util
from Code.Resistance import Resistance
from Code.Engines import EngineManagerPlay


class ManagerResistance(Manager.Manager):
    resistance: Resistance.Resistance
    num_engine: int
    str_side: str
    seconds: int
    puntos: int
    maxerror: int
    movimientos: int
    rival_points: int
    lostmovepoints: int
    is_battle: bool
    movements_rival: int
    manager_arbiter: EngineManagerPlay.EngineManagerPlay
    
    def start(self, resistance, num_engine, str_side):

        self.game_type = GT_RESISTANCE

        self.resistance = resistance
        self.num_engine = num_engine
        self.str_side = str_side
        is_white = "WHITE" in str_side
        self.seconds, self.puntos, self.maxerror = resistance.actual()
        self.movimientos = 0
        self.rival_points = 0
        self.lostmovepoints = 0

        self.human_is_playing = False
        self.state = ST_PLAYING

        self.is_human_side_white = is_white
        self.is_engine_side_white = not is_white

        self.is_battle = True

        self.rm_rival = None
        self.movements_rival = 0

        # debe hacerse antes que rival
        self.procesador.close_engines()
        engine_arbiter = self.configuration.engines.engine_analyzer()
        self.manager_arbiter = self.procesador.create_manager_engine(engine_arbiter, self.seconds * 1000, 0, 0)

        engine = resistance.dameClaveEngine(num_engine)
        rival = self.configuration.engines.search(engine)
        self.manager_rival = self.procesador.create_manager_engine(rival, self.seconds * 1000, 0, 0)

        self.game.set_tag("Event", _("Resistance Test"))

        player = self.configuration.nom_player()
        other = self.manager_rival.engine.name
        w, b = (player, other) if self.is_human_side_white else (other, player)
        self.game.set_tag("White", w)
        self.game.set_tag("Black", b)

        self.set_toolbar((TB_RESIGN, TB_REINIT, TB_CONFIG, TB_UTILITIES))
        self.main_window.active_game(True, False)
        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.put_pieces_bottom(is_white)
        self.remove_hints()
        self.set_activate_tutor(False)
        self.show_side_indicator(True)
        self.put_target_label()
        self.put_current_label()
        self.pgn_refresh(True)
        self.show_info_extra()
        self.check_boards_setposition()

        tp = self.resistance.tipo
        # mode = _("Normal")
        if tp:
            mode = _("Blindfold chess")
            if tp == "p1":
                mode += f"-{_('Hide only our pieces')}"
            elif tp == "p2":
                mode += f"-{_('Hide only opponent pieces')}"
            self.game.set_tag("Mode", mode)
            b = n = False
            if tp == "p2":
                if is_white:
                    b = True
                else:
                    n = True
            elif tp == "p1":
                if is_white:
                    n = True
                else:
                    b = True
            self.board.show_pieces(b, n)

        self.play_next_move()

    def put_target_label(self):
        label = self.resistance.rotuloActual(False)
        label += f"<br><br><b>{_('Opponent')}</b>: {self.manager_rival.engine.name}"
        label += f"<br><b>{_('Record')}</b>: {self.resistance.dameEtiRecord(self.str_side, self.num_engine)}"

        self.set_label1(label)

    def put_current_label(self):
        label = f"<b>{_('Moves')}</b>: {self.movimientos}"

        color = "black"
        if self.rival_points != 0:
            color = "red" if self.rival_points > 0 else "green"

        label += f'<br><b>{_("Score")}</b>: <font color="{color}"><b>{-self.rival_points}</b></font>'

        self.set_label2(label)

    def run_action(self, str_side):
        if str_side == TB_RESIGN:
            self.end_resistance(False)

        elif str_side == TB_CLOSE:
            self.procesador.close_engines()
            self.procesador.start()
            tm = TrainMenu.TrainMenu(self)
            tm.run_exec(f"resistance{self.resistance.tipo}")

        elif str_side == TB_REINIT:
            self.reiniciar()

        elif str_side == TB_CONFIG:
            self.configurar(with_sounds=True, with_blinfold=False)

        elif str_side == TB_UTILITIES:
            self.utilities(with_tree=self.state == ST_ENDGAME)

        elif str_side in self.procesador.li_opciones_inicio:
            self.procesador.run_action(str_side)

        else:
            self.routine_default(str_side)

    def reiniciar(self):
        if len(self.game) and QTMessages.pregunta(self.main_window, _("Restart the game?")):
            self.game.set_position()
            self.main_window.active_information_pgn(False)
            self.start(self.resistance, self.num_engine, self.str_side)

    def final_x(self):
        return self.end_resistance(False)

    def play_next_move(self):
        if self.state == ST_ENDGAME:
            return

        self.put_current_label()

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.put_view()
        is_white = self.game.last_position.is_white

        if self.game.is_finished():
            self.autosave()
            if self.game.is_mate():
                si_ganado = self.is_human_side_white != is_white
                if si_ganado:
                    self.movimientos += 2000
                self.end_resistance(True)
                return
            if self.game.is_draw():
                self.movimientos += 1000
                self.end_resistance(True)
                return

        si_rival = is_white == self.is_engine_side_white
        self.set_side_indicator(is_white)

        self.refresh()
        self.disable_all()

        if si_rival:
            self.thinking(True)

            puntos_rival_previo = self.rival_points

            self.rm_rival = self.manager_rival.play(self.game)
            self.rival_points = self.rm_rival.centipawns_abs()
            self.put_current_label()
            self.thinking(False)

            if self.rival_has_moved(self.rm_rival):
                self.movements_rival += 1
                lostmovepoints = self.rival_points - puntos_rival_previo
                if self.is_battle and self.movements_rival > 1:
                    if (self.rival_points > self.puntos) or (self.maxerror and lostmovepoints > self.maxerror):
                        if self.verify():
                            return
                self.play_next_move()

        else:

            self.human_is_playing = True
            self.activate_side(is_white)

    def verify(self):
        if len(self.game) < (3 if self.is_engine_side_white else 4):
            return False
        if self.manager_rival.engine.key != self.manager_arbiter.engine.key:

            with QTMessages.WaitingMessage(self.main_window, _("Checking...")):
                rm1 = self.manager_arbiter.play(self.game)
                self.rival_points = -rm1.centipawns_abs()   # el movimiento del rival está ya en game
                self.put_current_label()
                if self.maxerror:
                    game1 = self.game.copia()
                    game1.remove_only_last_movement()
                    game1.remove_only_last_movement()
                    rm0 = self.manager_arbiter.play(game1)
                    previo_rival = -rm0.centipawns_abs()
                    self.lostmovepoints = self.rival_points - previo_rival
                    if self.lostmovepoints > self.maxerror:
                        self.movimientos -= 1
                        return self.end_resistance(False)

        if self.rival_points > self.puntos:
            self.movimientos -= 1
            return self.end_resistance(False)

        return False

    def end_resistance(self, is_ended_game):
        if self.is_battle:
            if self.movimientos:
                is_record = self.resistance.put_result(self.num_engine, self.str_side, self.movimientos)
            else:
                is_record = False

            if is_ended_game:
                txt = f"<h2>{_('Game ended')}<h2>"
                txt += f"<h3>{self.resistance.dameEti(Util.today(), self.movimientos)}<h3>"
            else:
                if self.rival_points > self.puntos:
                    txt = f"<h3>{_X(_('You have lost %1 centipawns.'), str(self.rival_points))}</h3>"
                else:
                    txt = ""
                if self.lostmovepoints > 0:
                    msg = _("You have lost in the last move %d centipawns")
                    try:
                        msg = msg % self.lostmovepoints
                    except:
                        msg = f"{msg} {self.lostmovepoints}"
                    txt += f"<h3>{msg}</h3>"

            if is_record:
                txt += f"<h2>{_('New record!')}<h2>"
                txt += f"<h3>{self.resistance.dameEtiRecord(self.str_side, self.num_engine)}<h3>"
                self.put_target_label()

            if is_ended_game:
                self.message_on_pgn(txt)
            else:
                br = "<br>" if txt else ""
                resp = QTMessages.pregunta(
                    self.main_window,
                    f"{txt}{br}{_('Do you want to resign or continue playing?')}",
                    label_yes=_("Resign"),
                    label_no=_("Continue"),
                )
                if not resp:
                    self.is_battle = False
                    return False

        self.disable_all()
        self.state = ST_ENDGAME
        self.procesador.close_engines()
        self.main_window.adjust_size()
        self.main_window.resize(0, 0)
        if self.movimientos >= 1:
            li_options = [TB_CLOSE, TB_CONFIG, TB_UTILITIES]
            self.set_toolbar(li_options)
        else:
            self.run_action(TB_CLOSE)

        return True

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        move = self.check_human_move(from_sq, to_sq, promotion)
        if not move:
            return False

        self.move_the_pieces(move.list_piece_moves)

        self.add_move(move, True)
        self.movimientos += 1
        self.play_next_move()
        return True

    def add_move(self, move, is_player_move):
        self.game.add_move(move)
        self.check_boards_setposition()

        self.put_arrow_sc(move.from_sq, move.to_sq)
        self.beep_extended(is_player_move)

        self.pgn_refresh(self.game.last_position.is_white)
        self.refresh()

    def rival_has_moved(self, engine_response):
        from_sq = engine_response.from_sq
        to_sq = engine_response.to_sq

        promotion = engine_response.promotion

        ok, mens, move = Move.get_game_move(self.game, self.game.last_position, from_sq, to_sq, promotion)
        if ok:
            self.add_move(move, False)
            self.move_the_pieces(move.list_piece_moves, True)

            return True
        else:
            return False
