
import Code
from Code.Base import Move
from Code.Base.Constantes import (
    GT_GRID,
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
from Code.Z import TimeControl, Util


class GridDB:
    @staticmethod
    def load_all():
        path = Code.configuration.paths.file_estad_grid_elo()
        return Util.restore_pickle(path, {})

    @staticmethod
    def save_all(data):
        path = Code.configuration.paths.file_estad_grid_elo()
        Util.save_pickle(path, data)


class ManagerGrid(Manager.Manager):
    grid_id: str
    engine_alias: str
    elo_level: int
    min_elo: int
    max_elo: int
    is_white: bool
    minutes: int
    seconds: int

    points_win: int
    points_draw: int
    points_lose: int

    tc_player: TimeControl.TimeControl
    tc_rival: TimeControl.TimeControl
    max_seconds: int
    with_time: bool
    seconds_per_move: int

    in_the_opening: bool
    opening: Opening.OpeningPol

    def start(self, grid_id, engine_alias, elo_level, min_elo, max_elo, is_white, minutes, seconds):
        self.grid_id = grid_id
        self.engine_alias = engine_alias
        self.elo_level = elo_level
        self.min_elo = min_elo
        self.max_elo = max_elo
        self.is_white = is_white
        self.minutes = minutes
        self.seconds = seconds

        self.base_inicio()
        self.play_next_move()

    def base_inicio(self):
        self.game_type = GT_GRID
        self.is_competitive = False

        self.resultado = None
        self.human_is_playing = False
        self.state = ST_PLAYING
        self.showed_result = False

        self.is_human_side_white = self.is_white
        self.is_engine_side_white = not self.is_white

        self.lirm_engine = []
        self.next_test_resign = 5
        self.resign_limit = -1000

        self.is_tutor_enabled = False
        self.main_window.set_activate_tutor(False)

        self.hints = 0
        self.ayudas_iniciales = 0

        self.max_seconds = self.minutes * 60
        self.with_time = self.max_seconds > 0
        self.seconds_per_move = self.seconds if self.with_time else 0

        self.tc_player = self.tc_white if self.is_human_side_white else self.tc_black
        self.tc_rival = self.tc_white if self.is_engine_side_white else self.tc_black

        self.in_the_opening = True
        self.opening = Opening.OpeningPol(100, elo=self.elo_level)

        # Expected score rating changes
        self.points_win = Util.fide_elo(self.elo_level, self.elo_level, 1)
        self.points_draw = Util.fide_elo(self.elo_level, self.elo_level, 0)
        self.points_lose = Util.fide_elo(self.elo_level, self.elo_level, -1)
        self.white_elo = self.elo_level
        self.black_elo = self.elo_level

        # Engine initialization
        rival: Engines.Engine = self.configuration.engines.search(self.engine_alias)

        rival.set_uci_option("UCI_LimitStrength", "true")
        rival.set_uci_option("UCI_Elo", str(self.elo_level))

        rival.elo = self.elo_level
        rival.name = f"{rival.name} ({self.elo_level})"
        rival.key = f"{rival.key} ({self.elo_level})"

        self.manager_rival = self.procesador.create_manager_engine(rival, 0, 0, 0)
        self.manager_rival.check_engine()

        self.pte_tool_resigndraw = False
        self.pon_toolbar()

        self.main_window.active_game(True, self.with_time)
        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.put_pieces_bottom(self.is_human_side_white)
        self.remove_hints(True, remove_back=True)
        self.show_side_indicator(True)

        # Labels
        rival_name = Util.primera_mayuscula(self.engine_alias)
        label_title = f"{_('Opponent')}: <b>{rival_name} ({self.elo_level})</b>"
        self.set_label1(label_title)

        nbsp = "&nbsp;" * 3
        txt = "%s:%+d%s%s:%+d%s%s:%+d" % (
            _("Win"),
            self.points_win,
            nbsp,
            _("Draw"),
            self.points_draw,
            nbsp,
            _("Loss"),
            self.points_lose,
        )
        self.set_label2(f"<center>{txt}</center>")
        self.pgn_refresh(True)
        self.show_info_extra()

        self.game.set_tag("Event", _("The Grid"))
        player = self.configuration.nom_player()
        other = rival.name
        w, b = (player, other) if self.is_human_side_white else (other, player)
        self.game.set_tag("White", w)
        self.game.set_tag("Black", b)
        self.game.set_tag("WhiteElo", str(self.elo_level))
        self.game.set_tag("BlackElo", str(self.elo_level))

        if self.with_time:
            time_control = f"{int(self.max_seconds)}"
            if self.seconds_per_move:
                time_control += "+%d" % self.seconds_per_move
            self.game.set_tag("TimeControl", time_control)
            self.tc_player.config_clock(self.max_seconds, self.seconds_per_move, 0, 0)
            self.tc_rival.config_clock(self.max_seconds, self.seconds_per_move, 0, 0)

            tp_bl, tp_ng = self.tc_white.label(), self.tc_black.label()
            self.main_window.set_data_clock(w, tp_bl, b, tp_ng)
            self.main_window.start_clock(self.set_clock, 1000)

        self.refresh()
        self.check_boards_setposition()
        self.game.add_tag_timestart()

    def pon_toolbar(self):
        li_tool = (TB_RESIGN, TB_DRAW, TB_CONFIG, TB_UTILITIES)
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
        if not QTMessages.pregunta(
                self.main_window,
                _("Do you want to resign?") + " (%d)" % self.points_lose,
        ):
            return False
        self.game.resign(self.is_human_side_white)
        self.show_result()
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
            self.tc_rival.start()
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
                if self.with_time:
                    time_white = self.tc_white.pending_time
                    time_black = self.tc_black.pending_time
                else:
                    time_white = 300
                    time_black = 300
                self.manager_rival.update_time_run(time_white, time_black, self.seconds_per_move)
                rm_rival = self.manager_rival.play_game(self.game)

            self.thinking(False)
            if rm_rival and self.rival_has_moved(rm_rival):
                self.lirm_engine.append(rm_rival)
                if self.evaluate_rival_rm():
                    self.play_next_move()
                else:
                    self.show_result()
            else:
                self.show_result()
        else:
            self.tc_player.start()
            self.human_is_playing = True
            self.activate_side(is_white)

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        move = self.check_human_move(from_sq, to_sq, promotion)
        if not move:
            return False

        if self.in_the_opening:
            self.in_the_opening = self.opening.check_human(self.last_fen(), from_sq, to_sq)

        time_s = self.stop_clock(True)
        move.set_time_ms(time_s * 1000)
        move.set_clock_ms(self.tc_player.pending_time * 1000)

        self.move_the_pieces(move.list_piece_moves)
        self.add_move(move, True)
        self.play_next_move()
        return True

    def rival_has_moved(self, engine_response):
        from_sq = engine_response.from_sq
        to_sq = engine_response.to_sq
        promotion = engine_response.promotion

        ok, mens, move = Move.get_game_move(self.game, self.game.last_position, from_sq, to_sq, promotion)
        if ok:
            time_s = self.stop_clock(False)
            move.set_time_ms(time_s * 1000)
            move.set_clock_ms(self.tc_rival.pending_time * 1000)
            self.add_move(move, False)
            self.move_the_pieces(move.list_piece_moves, True)
            return True
        else:
            return False

    def add_move(self, move, is_player_move):
        self.game.add_move(move)
        self.put_arrow_sc(move.from_sq, move.to_sq)
        self.beep_extended(is_player_move)
        self.pgn_refresh(self.game.last_position.is_white)
        self.refresh()
        self.check_boards_setposition()

    def show_result(self):
        if self.showed_result:
            return
        self.showed_result = True
        self.state = ST_ENDGAME
        self.disable_all()
        self.human_is_playing = False
        self.main_window.stop_clock()

        mensaje, beep, player_win = self.game.label_result_player(self.is_human_side_white)
        self.beep_result(beep)

        if player_win:
            difelo = self.points_win
        elif self.game.is_draw():
            difelo = self.points_draw
        else:
            difelo = self.points_lose

        nelo = self.elo_level + difelo
        nelo = max(self.min_elo, min(nelo, self.max_elo))

        # Save Grid Rating
        grid_data = GridDB.load_all()
        if self.grid_id in grid_data:
            grid_data[self.grid_id]["engines"][self.engine_alias]["current_elo"] = nelo
            grid_data[self.grid_id]["engines"][self.engine_alias]["last_color"] = self.is_human_side_white
            GridDB.save_all(grid_data)

        self.autosave()
        self.configuration.graba()

        mensaje += f"\n\n{_('New Rating')}: {nelo} ({'+' if difelo >= 0 else ''}{difelo})"
        self.mensaje(mensaje)

        self.set_end_game()

        # Reopen WindowGrid to update view
        from Code.Competitions import WindowGrid
        WindowGrid.play_grid(self.procesador, self.grid_id)

    def set_clock(self):
        if self.state != ST_PLAYING:
            return False

        def check_consumed(is_white_clock):
            tc = self.tc_white if is_white_clock else self.tc_black
            tc.set_labels()
            if tc.time_is_consumed():
                self.game.set_termination_time(is_white_clock)
                self.show_result()
                return False
            return True

        if self.human_is_playing:
            return check_consumed(self.is_human_side_white)
        else:
            return check_consumed(self.is_engine_side_white)

    def stop_clock(self, is_player):
        tc = self.tc_player if is_player else self.tc_rival
        secs = tc.stop()
        self.show_clocks()
        return secs

    def show_clocks(self):
        self.tc_white.set_labels()
        self.tc_black.set_labels()
