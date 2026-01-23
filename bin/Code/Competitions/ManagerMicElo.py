import datetime
import random
from typing import List, Optional, Tuple

import Code
from Code.Z import Adjournments, TimeControl, Util
from Code.Base import Move
from Code.Base.Constantes import (
    BOOK_RANDOM_PROPORTIONAL,
    BOOK_RANDOM_UNIFORM,
    GT_MICELO,
    RS_DRAW,
    RS_WIN_OPPONENT,
    RS_WIN_PLAYER,
    ST_ENDGAME,
    ST_PLAYING,
    TB_ADJOURN,
    TB_CANCEL,
    TB_CONFIG,
    TB_DRAW,
    TB_RESIGN,
    TB_TAKEBACK,
    TB_UTILITIES,
    TERMINATION_RESIGN,
)
from Code.Books import Books
from Code.Engines import EngineManagerPlay, EngineResponse, Engines, EnginesMicElo
from Code.ManagerBase import Manager
from Code.QT import QTMessages, QTUtils
from Code.SQL import UtilSQL


class DicMicElos:
    def __init__(self):
        self.variable = "DicMicElos"
        self.configuration = Code.configuration
        self._dic = self.configuration.read_variables(self.variable)

    def dic(self):
        return self._dic

    def cambia_elo(self, clave_motor, nuevo_elo):
        self._dic = self.configuration.read_variables(self.variable)
        self._dic[clave_motor] = nuevo_elo
        self.configuration.write_variables(self.variable, self._dic)


def lista():
    li = EnginesMicElo.all_engines()
    dic_elos = DicMicElos().dic()
    for mt in li:
        k = mt.key
        if k in dic_elos:
            mt.elo = dic_elos[k]

    li.sort(key=lambda x: x.elo)
    return li


class ManagerMicElo(Manager.Manager):
    li_t: Optional[Tuple[Tuple[int, int, int], ...]] = None
    with_time: bool = True
    list_engines: List[EnginesMicElo.EngineTourneys]
    engine_rival: EnginesMicElo.EngineTourneys
    minutos: int
    seconds: int
    is_competitive: bool
    resultado: Optional[int]
    human_is_playing: bool
    state: int
    showed_result: bool
    is_human_side_white: bool
    is_engine_side_white: bool
    lirm_engine: List[EngineResponse.EngineResponse]
    next_test_resign: int
    resign_limit: int
    is_tutor_enabled: bool
    ayudas_iniciales: int
    hints: int
    max_seconds: int
    seconds_per_move: int
    tc_player: TimeControl.TimeControl
    tc_rival: TimeControl.TimeControl
    book: Optional[Books.Book]
    maxMoveBook: int
    white_elo: int
    black_elo: int
    manager_rival: EngineManagerPlay.EngineManagerPlay
    pte_tool_resigndraw: bool
    maxPlyRendirse: int
    rival: str
    error: str

    @staticmethod
    def calc_dif_elo(elo_jugador, elo_rival, resultado):
        if resultado == RS_WIN_PLAYER:
            result = 1
        elif resultado == RS_DRAW:
            result = 0
        else:
            result = -1
        return Util.fide_elo(elo_jugador, elo_rival, result)

    def list_engines(self, elo):
        self.li_t = (
            (0, 50, 3),
            (20, 53, 5),
            (40, 58, 4),
            (60, 62, 4),
            (80, 66, 5),
            (100, 69, 4),
            (120, 73, 3),
            (140, 76, 3),
            (160, 79, 3),
            (180, 82, 2),
            (200, 84, 9),
            (300, 93, 4),
            (400, 97, 3),
        )
        # self.liK = ((0, 60), (800, 50), (1200, 40), (1600, 30), (2000, 30), (2400, 10))

        li = []
        self.list_engines = lista()
        num_x = len(self.list_engines)
        for num, mt in enumerate(self.list_engines):
            mt_elo = mt.elo
            mt.siJugable = abs(mt_elo - elo) < 400
            mt.siOut = not mt.siJugable
            mt.baseElo = elo  # servira para rehacer la lista y elegir en aplazamiento
            if mt.siJugable or (mt_elo > elo):

                def rot(res):
                    return self.calc_dif_elo(elo, mt_elo, res)

                def rrot(res):
                    return self.calc_dif_elo(mt_elo, elo, res)

                mt.points_win = rot(RS_WIN_PLAYER)
                mt.points_draw = rot(RS_DRAW)
                mt.points_lose = rot(RS_WIN_OPPONENT)

                mt.rgana = rrot(RS_WIN_PLAYER)
                mt.rtablas = rrot(RS_DRAW)
                mt.rpierde = rrot(RS_WIN_OPPONENT)

                mt.number = num_x - num

                li.append(mt)

        return li

    def start(self, engine_rival, minutos, seconds):
        self.base_inicio(engine_rival, minutos, seconds)
        self.start_message()
        self.play_next_move()

    def base_inicio(self, engine_rival, minutos, seconds, human_side=None):
        self.game_type = GT_MICELO

        self.engine_rival = engine_rival
        self.minutos = minutos
        self.seconds = seconds

        self.is_competitive = True

        self.resultado = None
        self.human_is_playing = False
        self.state = ST_PLAYING
        self.showed_result = False  # Problema doble asignacion de ptos Thomas

        if human_side is None:
            is_white = self.get_the_side(engine_rival)
        else:
            is_white = human_side

        self.is_human_side_white = is_white
        self.is_engine_side_white = not is_white

        self.lirm_engine = []
        self.next_test_resign = 0
        self.resign_limit = -1000

        self.is_tutor_enabled = False
        self.main_window.set_activate_tutor(False)
        self.ayudas_iniciales = self.hints = 0

        self.max_seconds = minutos * 60
        self.with_time = self.max_seconds > 0
        self.seconds_per_move = seconds if self.with_time else 0

        self.tc_player = self.tc_white if self.is_human_side_white else self.tc_black
        self.tc_rival = self.tc_white if self.is_engine_side_white else self.tc_black

        if self.engine_rival.book:
            cbook = self.engine_rival.book
        else:
            path_rodent = Code.configuration.path_book("rodent.bin")
            cbook = random.choice([Code.tbook, path_rodent])

        self.book = Books.Book("P", cbook, cbook, True)
        self.book.polyglot()

        elo = self.engine_rival.elo
        self.maxMoveBook = (elo // 100) if 0 <= elo <= 1700 else 9999

        eloengine = self.engine_rival.elo
        eloplayer = self.configuration.micelo_current()
        self.white_elo = eloplayer if is_white else eloengine
        self.black_elo = eloplayer if not is_white else eloengine

        self.manager_rival = self.procesador.create_manager_engine(
            self.engine_rival, 0, 0, 0, has_multipv=self.engine_rival.multiPV > 0
        )
        self.manager_rival.check_engine()

        self.pte_tool_resigndraw = False
        if self.is_human_side_white:
            self.pte_tool_resigndraw = True
            self.maxPlyRendirse = 1
        else:
            self.maxPlyRendirse = 0

        self.pon_toolbar()

        self.main_window.active_game(True, self.with_time)
        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.put_pieces_bottom(is_white)
        self.remove_hints(True, remove_back=True)
        self.show_side_indicator(True)

        nbsp = "&nbsp;" * 3

        txt = "%s:%+d%s%s:%+d%s%s:%+d" % (
            _("Win"),
            self.engine_rival.points_win,
            nbsp,
            _("Draw"),
            self.engine_rival.points_draw,
            nbsp,
            _("Loss"),
            self.engine_rival.points_lose,
        )
        self.set_label1(f"<center>{txt}</center>")
        self.set_label2("")
        self.pgn_refresh(True)
        self.show_info_extra()

        rival_name = Util.primera_mayuscula(self.engine_rival.key)
        self.rival = "%s (%d)" % (rival_name, self.engine_rival.elo)
        white_name, black_name = self.configuration.nom_player(), rival_name
        white_elo, black_elo = self.configuration.micelo_current(), self.engine_rival.elo
        if self.is_engine_side_white:
            white_name, black_name = black_name, white_name
            white_elo, black_elo = black_elo, white_elo

        self.game.set_tag("Event", _("Tourney-Elo"))

        self.game.set_tag("White", white_name)
        self.game.set_tag("Black", black_name)
        self.game.set_tag("WhiteElo", str(white_elo))
        self.game.set_tag("BlackElo", str(black_elo))

        white_player = white_name + " (%d)" % white_elo
        black_player = black_name + " (%d)" % black_elo

        if self.with_time:
            time_control = f"{int(self.max_seconds)}"
            if self.seconds_per_move:
                time_control += "+%d" % self.seconds_per_move
            self.game.set_tag("TimeControl", time_control)
            self.tc_player.config_clock(self.max_seconds, self.seconds_per_move, 0, 0)
            self.tc_rival.config_clock(self.max_seconds, self.seconds_per_move, 0, 0)

            tp_bl, tp_ng = self.tc_white.label(), self.tc_black.label()
            self.main_window.set_data_clock(white_player, tp_bl, black_player, tp_ng)
            self.main_window.start_clock(self.set_clock, 1000)

        else:
            self.set_label1(f"{_('White')}: <b>{white_player}</b><br>{_('Black')}: <b>{black_player}</b>")

        self.refresh()

        self.check_boards_setposition()

        self.game.add_tag_timestart()

    def pon_toolbar(self):
        if self.pte_tool_resigndraw:
            li_tool = (TB_CANCEL, TB_ADJOURN, TB_TAKEBACK, TB_CONFIG, TB_UTILITIES)
        else:
            li_tool = (TB_RESIGN, TB_DRAW, TB_ADJOURN, TB_CONFIG, TB_UTILITIES)

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

        elif key == TB_ADJOURN:
            self.adjourn()

        elif key in self.procesador.li_opciones_inicio:
            self.procesador.run_action(key)

        else:
            self.routine_default(key)

    def save_state(self):
        self.main_window.stop_clock()
        self.tc_white.stop()
        self.tc_black.stop()

        dic = {
            "engine_rival": self.engine_rival.save(),
            "minutos": self.minutos,
            "seconds": self.seconds,
            "game_save": self.game.save(),
            "time_white": self.tc_white.save(),
            "time_black": self.tc_black.save(),
            "points_win": self.engine_rival.points_win,
            "points_draw": self.engine_rival.points_draw,
            "points_lose": self.engine_rival.points_lose,
            "alias": self.engine_rival.key,
            "human_side": self.is_human_side_white,
        }

        return dic

    def restore_state(self, dic):
        engine_rival = Engines.Engine()
        engine_rival.restore(dic["engine_rival"])
        engine_rival.points_win = dic["points_win"]
        engine_rival.points_draw = dic["points_draw"]
        engine_rival.points_lose = dic["points_lose"]
        engine_rival.key = dic["alias"]

        minutos = dic["minutos"]
        seconds = dic["seconds"]

        self.base_inicio(engine_rival, minutos, seconds, human_side=dic.get("human_side"))

        self.game.restore(dic["game_save"])

        self.tc_white.restore(dic["time_white"])
        self.tc_black.restore(dic["time_black"])

        self.goto_end()

    def adjourn(self):
        if QTMessages.pregunta(self.main_window, _("Do you want to adjourn the game?")):
            dic = self.save_state()

            # se guarda en una bd Adjournments dic key = fecha y hora y tipo
            label_menu = f"{_('Tourney-Elo')}. {self.engine_rival.name}"

            self.state = ST_ENDGAME

            with Adjournments.Adjournments() as adj:
                adj.add(self.game_type, dic, label_menu)
                adj.si_seguimos(self)

    def run_adjourn(self, dic):
        self.restore_state(dic)
        self.check_boards_setposition()
        self.start_message()
        self.show_clocks()
        self.play_next_move()

    def final_x(self):
        return self.rendirse()

    def rendirse(self):
        if self.state == ST_ENDGAME:
            return True
        if (len(self.game) > 0) and not self.pte_tool_resigndraw:
            if not QTMessages.pregunta(
                self.main_window,
                _("Do you want to resign?") + " (%d)" % self.engine_rival.points_lose,
            ):
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

        is_rival_play = is_white == self.is_engine_side_white
        self.set_side_indicator(is_white)

        self.refresh()

        if is_rival_play:
            self.play_rival()
        else:
            self.tc_player.start()

            self.human_is_playing = True
            self.activate_side(is_white)

    def play_rival(self):
        self.tc_rival.start()
        self.thinking(True)
        self.disable_all()

        si_encontrada = False
        rm_rival = None

        if self.book:
            if self.game.last_position.num_moves >= self.maxMoveBook:
                self.book = None
            else:
                fen = self.last_fen()
                pv = self.book.select_move_type(
                    fen,
                    (BOOK_RANDOM_UNIFORM if len(self.game) > 2 else BOOK_RANDOM_PROPORTIONAL),
                )
                if pv:
                    rm_rival = EngineResponse.EngineResponse("Opening", self.is_engine_side_white)
                    rm_rival.from_sq = pv[:2]
                    rm_rival.to_sq = pv[2:4]
                    rm_rival.promotion = pv[4:]
                    si_encontrada = True
                else:
                    self.book = None

        if not si_encontrada:
            if self.with_time:
                time_white = self.tc_white.pending_time
                time_black = self.tc_black.pending_time
            else:
                time_white = int(5 * 60 * self.white_elo / 1500)
                time_black = int(5 * 60 * self.black_elo / 1500)
            self.manager_rival.update_time_run(time_white, time_black, self.seconds_per_move)
            rm_rival = self.manager_rival.play_game(self.game)
            if rm_rival is None:
                self.thinking(False)
                return

        self.thinking(False)
        if self.rival_has_moved(rm_rival):
            self.lirm_engine.append(rm_rival)
            if self.evaluate_rival_rm():
                self.play_next_move()
            else:
                if self.game.is_finished():
                    self.show_result()
                    return
        else:
            self.game.set_termination(TERMINATION_RESIGN, RS_WIN_PLAYER)
            self.show_result()

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        move = self.check_human_move(from_sq, to_sq, promotion)
        if not move:
            return False

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

            self.error = ""

            return True
        else:
            self.error = mens
            return False

    def add_move(self, move, is_player_move):
        self.game.add_move(move)
        self.check_boards_setposition()

        self.put_arrow_sc(move.from_sq, move.to_sq)
        self.beep_extended(is_player_move)

        self.pgn_refresh(self.game.last_position.is_white)
        self.refresh()

        if self.pte_tool_resigndraw:
            if len(self.game) > self.maxPlyRendirse:
                self.pte_tool_resigndraw = False
                self.pon_toolbar()

    def show_result(self):
        if self.showed_result:  # Problema doble asignacion de ptos Thomas
            return
        self.state = ST_ENDGAME
        self.disable_all()
        self.human_is_playing = False
        self.main_window.stop_clock()

        mensaje, beep, player_win = self.game.label_result_player(self.is_human_side_white)

        self.beep_result(beep)
        self.autosave()
        QTUtils.refresh_gui()

        elo = self.configuration.micelo_current()
        relo = self.engine_rival.elo
        if player_win:
            difelo = self.engine_rival.points_win

        elif self.game.is_draw():
            difelo = self.engine_rival.points_draw

        else:
            difelo = self.engine_rival.points_lose

        nelo = elo + difelo
        if nelo < 0:
            nelo = 0
        self.configuration.set_current_micelo(nelo)

        rnelo = max(relo - difelo, 100)
        dme = DicMicElos()
        dme.cambia_elo(self.engine_rival.key, rnelo)
        self.historial(elo, nelo)
        self.configuration.graba()

        mensaje += "\n\n%s : %d\n" % (_("New Tourney-Elo"), nelo)

        self.showed_result = True
        self.message_on_pgn(mensaje)
        self.set_end_game()

    def historial(self, elo, nelo):
        dic = {
            "FECHA": datetime.datetime.now(),
            "RIVAL": self.engine_rival.name,
            "RESULTADO": self.resultado,
            "AELO": elo,
            "NELO": nelo,
        }

        lik = UtilSQL.ListSQL(self.configuration.paths.file_estad_mic_elo())
        lik.append(dic)
        lik.close()

        dd = UtilSQL.DictSQL(self.configuration.paths.file_estad_mic_elo(), tabla="color")
        key = self.engine_rival.name
        dd[key] = self.is_human_side_white
        dd.close()

    def get_the_side(self, engine_rival):
        key = engine_rival.name

        dd = UtilSQL.DictSQL(self.configuration.paths.file_estad_mic_elo(), tabla="color")
        previo = dd.get(key, random.randint(0, 1) == 0)
        dd.close()
        return not previo

    def set_clock(self):
        if self.state != ST_PLAYING:
            return False

        def mira(xis_white):
            tc = self.tc_white if xis_white else self.tc_black
            tc.set_labels()

            if tc.time_is_consumed():
                self.game.set_termination_time(xis_white)
                self.show_result()
                return False

            return True

        if Code.eboard:
            Code.eboard.writeClocks(self.tc_white.label_dgt(), self.tc_black.label_dgt())

        if self.human_is_playing:
            is_white = self.is_human_side_white
        else:
            is_white = not self.is_human_side_white
        return mira(is_white)

    def stop_clock(self, is_player):
        tc = self.tc_player if is_player else self.tc_rival
        secs = tc.stop()
        self.show_clocks()
        return secs

    def show_clocks(self):
        if Code.eboard:
            Code.eboard.writeClocks(self.tc_white.label_dgt(), self.tc_black.label_dgt())

        self.tc_white.set_labels()
        self.tc_black.set_labels()
