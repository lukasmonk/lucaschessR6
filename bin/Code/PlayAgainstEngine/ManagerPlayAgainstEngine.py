import os
import time
from enum import Enum, auto
from functools import partial
from typing import Any, Dict, List, Optional, Tuple

import FasterCode
from PySide6 import QtCore

import Code
from Code.Analysis import Analysis
from Code.Base import Game, Move, Position
from Code.Base.Constantes import (
    ADJUST_BETTER,
    ADJUST_SELECTED_BY_PLAYER,
    BLACK,
    BOOK_BEST_MOVE,
    ENG_ELO,
    GT_AGAINST_ENGINE,
    MISTAKE,
    RESULT_WIN_BLACK,
    RESULT_WIN_WHITE,
    SELECTED_BY_PLAYER,
    ST_ENDGAME,
    ST_PAUSE,
    ST_PLAYING,
    ST_TUTOR_THINKING,
    TB_ADJOURN,
    TB_ADVICE,
    TB_CANCEL,
    TB_CLOSE,
    TB_CONFIG,
    TB_CONTINUE,
    TB_DRAW,
    TB_PAUSE,
    TB_QUIT,
    TB_REINIT,
    TB_RESIGN,
    TB_STOP,
    TB_TAKEBACK,
    TB_TUTOR_STOP,
    TB_UTILITIES,
    TERMINATION_RESIGN,
    TERMINATION_WIN_ON_TIME,
    WHITE,
    MULTIPV_MAXIMIZE
)
from Code.Books import Books, WBooks
from Code.Engines import EngineManagerPlay, EngineResponse, Engines, SelectEngines
from Code.ManagerBase import Manager
from Code.Openings import Opening, OpeningLines
from Code.PlayAgainstEngine import Personalities, WPlayAgainstEngine
from Code.QT import Iconos, QTDialogs, QTMessages, QTUtils
from Code.Translations import TrListas
from Code.Tutor import Tutor
from Code.Voyager import Voyager
from Code.Z import Adjournments, Util


class ToolbarState(Enum):
    HUMAN_PLAYING = auto()
    ENGINE_PLAYING = auto()
    TUTOR_THINKING = auto()
    GAME_PAUSED = auto()
    # GAME_FINISHED = auto()


class ManagerPlayAgainstEngine(Manager.Manager):
    """
    Manager for playing games against a chess engine.
    Handles game state, time control, engine interaction, and UI updates.
    """

    reinicio: Optional[Dict[str, Any]] = None
    cache: Optional[Dict[str, Any]] = None
    is_analyzing: bool = False

    tc_player: Any = None
    tc_rival: Any = None

    player_name: str
    rival_name: str

    summary: Optional[Dict[int, Dict[str, Any]]] = None
    with_summary: bool = False

    is_engine_side_white: bool = False
    engine_rival: Optional[Engines.Engine] = None
    manager_rival: Optional[EngineManagerPlay.EngineManagerPlay] = None
    lirm_engine: List[EngineResponse.EngineResponse] = []

    next_test_resign: int = 0
    opening_mandatory: Optional[Opening.JuegaOpening] = None
    primeroBook: bool = False
    book_player: Optional[Books.Book] = None
    book_player_active: bool = False
    book_player_depth: int = 0
    book_rival: Optional[Books.Book] = None
    book_rival_active: bool = False
    book_rival_select: Optional[str] = None
    book_rival_depth: int = 0
    current_helps: int = 0
    nArrows: int = 0
    thoughtOp: int = -1
    thoughtTt: int = -1
    chance: bool = True
    nAjustarFuerza: int = 0
    resign_limit: int = -99999
    siBookAjustarFuerza: bool = True
    timed: bool = False
    max_seconds: float = 0.0
    seconds_move: int = 0
    disable_user_time: bool = False
    nodes: int = 0
    zeitnot: int = 0
    premove: Optional[Tuple[str, str]] = None
    last_time_show_arrows: Optional[float] = None
    rival_is_thinking: bool = False
    humanize: int = 0
    unlimited_minutes: int = 6
    is_human_side_white: bool
    opening_line: Optional[Dict[str, Any]] = None
    play_while_win: Optional[bool] = None
    limit_pww: int = 90
    dic_reject: Dict[str, int]
    cache_analysis: Dict[str, Any] = {}
    with_takeback: bool = True
    seconds_per_move: int = 0
    secs_extra: float = 0.0

    mrm_tutor: Optional[EngineResponse.MultiEngineResponse] = None

    is_tutor_enabled: bool = False
    is_tutor_analysing: bool = False
    nArrowsTt: int = 0
    tutor_con_flechas: bool = False
    tutor_book: Optional[Books.BookGame] = None

    player_has_moved_a1h8: Optional[Move.Move] = None
    game_over_message_pww: Optional[str] = None

    key_crash: Optional[str] = None
    start_pending_continue: bool = False

    tb_huella: str

    dic_times_prev_move: dict

    def start(self, dic_var: Dict[str, Any]):
        self.base_inicio(dic_var)
        if self.timed:
            if self.hints:
                self.manager_tutor.check_engine()
            self.manager_rival.check_engine()
            self.start_pending_continue = True
            self.start_message(nomodal=Code.eboard and Util.is_linux())  # nomodal: problema con eboard
            self.start_pending_continue = False

        self.play_next_move()

    def base_inicio(self, dic_var: Dict[str, Any]):
        self._init_vars(dic_var)
        self._init_time(dic_var)
        self._init_rival(dic_var)
        self._init_opening(dic_var)
        self._init_hints(dic_var)
        self._init_game(dic_var)
        self._init_show(dic_var)

    def _init_vars(self, dic_var: Dict[str, Any]):
        self.reinicio = dic_var

        self.game_type = GT_AGAINST_ENGINE
        self.human_is_playing = False
        self.rival_is_thinking = False
        self.state = ST_PLAYING
        self.is_tutor_analysing = False

        self.cache = dic_var.get("cache", {})
        self.cache_analysis = dic_var.get("cache_analysis", {})

        self.summary = {}  # movenum : "a"ccepted, "s"ame, "r"ejected, dif points, time used
        self.with_summary = dic_var.get("SUMMARY", False)

        is_white = dic_var["ISWHITE"]
        self.is_human_side_white = is_white
        self.is_engine_side_white = not is_white

        self.play_while_win = dic_var.get("WITH_LIMIT_PWW", False)
        self.limit_pww = dic_var.get("LIMIT_PWW", 90)

        self.dic_times_prev_move = {}

    def _init_show(self, dic_var: Dict[str, Any]):
        n_box_height = dic_var.get("BOXHEIGHT", 24)
        mx = max(self.thoughtOp, self.thoughtTt)
        if mx > -1:
            self.set_hight_label3(n_box_height)

        self.main_window.set_activate_tutor(self.is_tutor_enabled)
        self.main_window.active_game(True, self.timed)
        if self.disable_user_time:
            if self.is_human_side_white:
                self.main_window.hide_clock_white()
            else:
                self.main_window.hide_clock_black()

        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.show_side_indicator(True)
        if self.ayudas_iniciales:
            self.show_hints()
        else:
            self.remove_hints(remove_back=False)
        if self.play_while_win:
            self.is_tutor_enabled = True
        self.put_pieces_bottom(self.is_human_side_white)

        self.show_basic_label()
        self.set_label2("")

        self.show_info_extra()

        self.pgn_refresh(True)

        bl, ng = self.player_name, self.rival_name
        if self.is_engine_side_white:
            bl, ng = ng, bl

        if self.timed:
            tp_bl, tp_ng = self.tc_white.label(), self.tc_black.label()

            self.main_window.set_data_clock(bl, tp_bl, ng, tp_ng)
            self.refresh()
        else:
            self.main_window.base.change_player_labels(bl, ng)

        self.main_window.start_clock(self.set_clock, 1000)

        self.main_window.set_notify(self.mueve_rival_base)
        if dic_var.get("ACTIVATE_EBOARD"):
            Code.eboard.activate(self.board.dispatch_eboard)
        self.check_boards_setposition()

    def _init_time(self, dic_var: Dict[str, Any]):
        self.tc_player = self.tc_white if self.is_human_side_white else self.tc_black
        self.tc_rival = self.tc_white if self.is_engine_side_white else self.tc_black

        self.timed = dic_var["WITHTIME"]
        self.tc_white.set_displayed(self.timed)
        self.tc_black.set_displayed(self.timed)
        if self.timed:
            self.max_seconds = dic_var["MINUTES"] * 60.0
            self.seconds_per_move = dic_var["SECONDS"]
            self.secs_extra = dic_var.get("MINEXTRA", 0) * 60.0
            zeitnot = dic_var.get("ZEITNOT", 0)

            self.disable_user_time = dic_var.get("DISABLEUSERTIME", False)
            if self.disable_user_time:
                self.secs_extra = 3 * 60 * 60  # 3 horas
                self.tc_player.set_displayed(False)

            self.tc_player.config_clock(self.max_seconds, self.seconds_per_move, zeitnot, self.secs_extra)
            self.tc_rival.config_clock(self.max_seconds, self.seconds_per_move, zeitnot, 0)

    def _init_hints(self, dic_var: Dict[str, Any]):
        self.hints = dic_var["HINTS"]
        self.ayudas_iniciales = self.hints  # Se guarda para guardar el PGN
        self.nArrows = dic_var.get("ARROWS", 0)
        self.thoughtOp = dic_var.get("THOUGHTOP", -1)
        self.thoughtTt = dic_var.get("THOUGHTTT", -1)
        self.nArrowsTt = dic_var.get("ARROWSTT", 0)
        self.chance = dic_var.get("2CHANCE", True)
        self.is_tutor_enabled = self.configuration.x_default_tutor_active
        if self.nArrowsTt != 0 and self.hints == 0:
            self.nArrowsTt = 0
        if self.nAjustarFuerza != ADJUST_BETTER:
            pers = Personalities.Personalities(None, self.configuration)
            label = pers.label(self.nAjustarFuerza)
            if label:
                self.game.set_tag("Strength", label)
        self.with_takeback = dic_var.get("TAKEBACK", True)
        self.last_time_show_arrows = time.time() - 2.0

        self.tutor_con_flechas = self.nArrowsTt > 0 and self.hints > 0
        self.tutor_book = Books.BookGame(Code.tbook)
        self.is_analyzed_by_tutor = False

    def _init_opening(self, dic_var: Dict[str, Any]):
        self.dic_reject = {"opening_line": 0, "book_rival": 0, "book_player": 0}

        self.opening_mandatory = None

        if dic_var["OPENING"]:
            self.opening_mandatory = Opening.JuegaOpening(dic_var["OPENING"].a1h8)
            self.primeroBook = False  # la opening es obligatoria

        self.opening_line = None
        if dic_var["OPENING_LINE"]:
            dic_op = dic_var["OPENING_LINE"]
            path = self.configuration.paths.folder_base_openings()
            if "folder" in dic_op:
                path = Util.opj(path, dic_op["folder"])
            path = Util.opj(path, dic_op["file"])
            if os.path.isfile(path):
                self.opening_line = OpeningLines.Opening(path).dic_fenm2_moves()

        self.book_rival_active = False
        self.book_rival = dic_var.get("BOOKR", None)
        if self.book_rival:
            self.book_rival_active = True
            self.book_rival_depth = dic_var.get("BOOKRDEPTH", 0)
            self.book_rival.polyglot()
            self.book_rival_select = dic_var.get("BOOKRR", BOOK_BEST_MOVE)
        elif self.engine_rival.book and Util.exist_file(self.engine_rival.book):
            self.book_rival_active = True
            self.book_rival = Books.Book("P", self.engine_rival.book, self.engine_rival.book, True)
            self.book_rival.polyglot()
            self.book_rival_select = BOOK_BEST_MOVE
            self.book_rival_depth = getattr(self.engine_rival, "book_max_plies", 0)

        self.book_player_active = False
        self.book_player = dic_var.get("BOOKP", None)
        if self.book_player:
            self.book_player_active = True
            self.book_player_depth = dic_var.get("BOOKPDEPTH", 0)
            self.book_player.polyglot()
        self.siBookAjustarFuerza = self.nAjustarFuerza != ADJUST_BETTER

    def _init_game(self, dic_var: Dict[str, Any]):
        self.game.set_tag("Event", _("Play against an engine"))

        self.player_name = self.configuration.nom_player()
        self.rival_name = self.engine_rival.name

        w, b = self.player_name, self.rival_name
        if not self.is_human_side_white:
            w, b = b, w
        self.game.set_tag("White", w)
        self.game.set_tag("Black", b)

        self.fen = dic_var["FEN"]
        if self.fen:
            cp = Position.Position()
            cp.read_fen(self.fen)
            self.game.set_position(cp)
            self.game.pending_opening = False

        self.game.add_tag_timestart()

        time_control = f"{int(self.max_seconds)}"
        if self.seconds_per_move:
            time_control += f"+{self.seconds_per_move}"
        self.game.set_tag("TimeControl", time_control)
        if self.secs_extra:
            if self.disable_user_time:
                self.game.set_tag(f"TimeExtra{'White' if self.is_human_side_white else 'Black'}", _("No limit"))
            else:
                self.game.set_tag(f"TimeExtra{'White' if self.is_human_side_white else 'Black'}", f"{self.secs_extra}")

    def _init_rival(self, dic_var: Dict[str, Any]):
        dr = dic_var["RIVAL"]
        if "CM" not in dr:
            dr["CM"] = SelectEngines.busca_engine_default(dr["TYPE"], dr["ENGINE"], dr.get("ALIAS"))
        self.engine_rival = dr["CM"]
        self.unlimited_minutes = dr.get("ENGINE_UNLIMITED", 3)

        if dr["TYPE"] == ENG_ELO:
            rival_time_ms = 0
            rival_depth = self.engine_rival.max_depth
            self.nAjustarFuerza = ADJUST_BETTER

        else:
            rival_time_ms = dr["ENGINE_TIME"] * 100  # Se guarda en decimas -> milesimas
            rival_depth = dr["ENGINE_DEPTH"]
            self.nAjustarFuerza = dic_var.get("ADJUST", ADJUST_BETTER)

        self.nodes = dr.get("ENGINE_NODES", 0)

        if not self.manager_rival:  # reiniciando is not None
            if rival_time_ms <= 0:
                rival_time_ms = 0
            if rival_depth <= 0:
                rival_depth = 0
            self.engine_rival.liUCI = dr["LIUCI"]

            self.limit_time_seconds = None
            if rival_depth > 0 or self.nodes > 0:
                self.limit_time_seconds = rival_time_ms / 1000 if rival_time_ms else None
                rival_time_ms = 0
            elif self.engine_rival.emulate_movetime and rival_time_ms:
                self.limit_time_seconds = rival_time_ms / 1000

            if self.nAjustarFuerza != ADJUST_BETTER:
                self.engine_rival.set_multipv_var(MULTIPV_MAXIMIZE)
            self.manager_rival = self.procesador.create_manager_engine(
                self.engine_rival, rival_time_ms, rival_depth, self.nodes, self.nAjustarFuerza != ADJUST_BETTER
            )

            self.manager_rival.check_engine()  # para que el tiempo de carga del ejecutable no compute

        # self.manager_rival.is_white = self.is_engine_side_white
        self.lirm_engine = []
        self.next_test_resign = 0
        self.resign_limit = -99999  # never
        self.resign_limit = dic_var["RESIGN"]
        self.humanize = dic_var.get("LEVEL_HUMANIZE", 0)

    def pon_toolbar(self, tb_state: ToolbarState):
        self.tb_huella = Util.huella()

        def list_base():
            li = [TB_CANCEL, TB_RESIGN, TB_DRAW, TB_REINIT, TB_PAUSE, TB_ADJOURN, TB_CONFIG, TB_UTILITIES]
            if self.with_takeback:
                li.insert(3, TB_TAKEBACK)
            if self.hints > 0 and self.is_tutor_enabled:
                li.insert(3, TB_ADVICE)
            return li

        if tb_state == ToolbarState.HUMAN_PLAYING:
            self.set_toolbar(list_base())
            return

        if tb_state == ToolbarState.TUTOR_THINKING:

            def haz_tutor(with_all):
                li = list_base()
                if with_all:
                    li.append(TB_TUTOR_STOP)
                self.set_toolbar(li)
                for key in li:
                    self.main_window.enable_option_toolbar(key, key == TB_TUTOR_STOP)

            haz_tutor(False)

            def deferred(huella):
                if huella == self.tb_huella:
                    haz_tutor(True)

            QtCore.QTimer.singleShot(800, partial(deferred, self.tb_huella))
            return

        if tb_state == ToolbarState.ENGINE_PLAYING:

            def haz_engine(with_all):
                li = list_base()
                if with_all:
                    li.append(TB_STOP)
                self.set_toolbar(li)
                for key in li:
                    self.main_window.enable_option_toolbar(key, key == TB_STOP)

            haz_engine(False)

            def deferred(huella):
                if huella == self.tb_huella:
                    haz_engine(True)

            QtCore.QTimer.singleShot(800, partial(deferred, self.tb_huella))
            return

        if tb_state == ToolbarState.GAME_PAUSED:
            self.set_toolbar([TB_CONTINUE])
            return

    def show_basic_label(self):
        rotulo1 = ""
        if self.book_rival_active:
            rotulo1 += f"<br>{_('Book')}-{_('Opponent')}: <b>{os.path.basename(self.book_rival.name)}</b>"
        if self.book_player_active:
            rotulo1 += f"<br>{_('Book')}-{_('Player')}: <b>{os.path.basename(self.book_player.name)}</b>"
        self.set_label1(rotulo1)

    def show_time(self, is_player: bool):
        tc = self.tc_player if is_player else self.tc_rival
        tc.set_labels()

    def set_clock(self):
        if self.state == ST_ENDGAME:
            self.main_window.stop_clock()
            return
        if self.state != ST_PLAYING:
            return

        if self.start_pending_continue:
            return

        if self.timed:
            if Code.eboard:
                Code.eboard.writeClocks(self.tc_white.label_dgt(), self.tc_black.label_dgt())

            is_white = self.game.last_position.is_white
            is_player = self.is_human_side_white == is_white

            tc = self.tc_player if is_player else self.tc_rival
            tc.set_labels()

            if tc.time_is_consumed():
                t = time.time()
                if is_player and QTMessages.pregunta(
                        self.main_window,
                        f"{_X(_('%1 has won on time.'), self.rival_name)}\n\n{_('Add time and keep playing?')}",
                ):
                    min_x = WPlayAgainstEngine.get_extra_minutes(self.main_window)
                    if min_x:
                        more = time.time() - t
                        tc.add_extra_seconds(min_x * 60 + more)
                        tc.set_labels()
                        return
                self.game.set_termination(TERMINATION_WIN_ON_TIME, RESULT_WIN_BLACK if is_white else RESULT_WIN_WHITE)
                self.state = ST_ENDGAME  # necesario que esté antes de stop_clock para no entrar en bucle
                self.stop_clock(is_player)
                self.show_result()
                return

            elif is_player and tc.is_zeitnot():
                self.beep_zeitnot()

    def stop_clock(self, is_player: bool) -> float:
        tc = self.tc_player if is_player else self.tc_rival
        time_s = tc.stop()
        self.show_time(is_player)
        return time_s

    def run_action(self, key: int):
        if key == TB_CANCEL:
            self.finalizar()

        elif key == TB_RESIGN:
            self.rendirse()

        elif key == TB_DRAW:
            if self.check_draw_player():
                self.show_result()

        elif key == TB_TAKEBACK:
            self.takeback()

        elif key == TB_TUTOR_STOP:
            self.analyze_end()
            self.pon_toolbar(ToolbarState.HUMAN_PLAYING)

        elif key == TB_ADVICE:
            self.help_current()

        elif key == TB_PAUSE:
            self.xpause()

        elif key == TB_CONTINUE:
            self.xcontinue()

        elif key == TB_REINIT:
            self.reiniciar(True)

        elif key == TB_CONFIG:
            li_mas_opciones = []
            if self.state == ST_PLAYING and self.game_type == GT_AGAINST_ENGINE:
                li_mas_opciones.append((None, None, None))
                li_mas_opciones.append(("rival", _("Change opponent"), Iconos.Engine()))
                if len(self.game) > 0:
                    li_mas_opciones.append((None, None, None))
                    li_mas_opciones.append(("moverival", _("Change opponent move"), Iconos.TOLchange()))
            resp = self.configurar(li_mas_opciones, with_sounds=True)
            if resp == "rival":
                self.change_rival()
            elif resp == "moverival":
                self.change_last_move_engine()

        elif key == TB_UTILITIES:
            li_mas_opciones = []
            if self.human_is_playing or self.is_finished():
                li_mas_opciones.append(("books", _("Consult a book"), Iconos.Libros()))
            # li_mas_opciones.append((None, None, None))
            # li_mas_opciones.append(("start_position", _("Change the starting position"), Iconos.PGN()))

            resp = self.utilities(li_mas_opciones)
            if resp == "books":
                si_en_vivo = self.human_is_playing and not self.is_finished()
                li_movs = self.consult_books(si_en_vivo)
                if li_movs and si_en_vivo:
                    from_sq, to_sq, promotion = li_movs[-1]
                    self.player_has_moved_dispatcher(from_sq, to_sq, promotion)

        elif key == TB_ADJOURN:
            self.adjourn()

        elif key == TB_STOP:
            self.stop_engine()

        else:
            self.routine_default(key)

    def save_state(self, temporary: bool = False) -> Dict[str, Any]:
        self.analyze_terminate()
        dic = self.reinicio

        # cache
        dic["cache"] = self.cache
        dic["cache_analysis"] = self.cache_analysis

        # game
        dic["game_save"] = self.game.save()

        # tiempos
        if self.timed:
            self.main_window.stop_clock()
            dic["time_white"] = self.tc_white.save()
            dic["time_black"] = self.tc_black.save()
            if temporary:
                self.main_window.start_clock(self.set_clock, 1000)

        dic["is_tutor_enabled"] = self.is_tutor_enabled

        dic["hints"] = self.hints
        dic["summary"] = self.summary

        return dic

    def restore_state(self, dic: Dict[str, Any]):
        self.base_inicio(dic)
        self.game.restore(dic["game_save"])

        if self.timed:
            self.tc_white.restore(dic["time_white"])
            self.tc_black.restore(dic["time_black"])

        self.is_tutor_enabled = dic["is_tutor_enabled"]
        self.hints = dic["hints"]
        self.summary = dic["summary"]
        self.goto_end()

    def close_position(self, key: int):
        self.main_window.deactivate_eboard(100)
        if key == TB_CLOSE:
            self.autosave_now()
            self.procesador.run_action(TB_QUIT)
        else:
            self.run_action(key)

    def play_position(self, dic: Dict[str, Any], restore_game: str):
        self.set_routine_default(self.close_position)
        game = Game.Game()
        game.restore(restore_game)
        self.base_inicio(dic)
        self.reinicio["play_position"] = dic, restore_game
        w, b = self.player_name, self.rival_name
        if self.is_human_side_white:
            w, b = b, w
        for tag, value in self.game.li_tags:
            if not game.get_tag(tag):
                game.set_tag(tag, value)
        game.add_tag_date()
        game.set_tag("White", w)
        game.set_tag("Black", b)
        game.add_tag_timestart()
        game.set_unknown()
        game.order_tags()
        self.game = game
        self.goto_end()
        self.play_next_move()

    def reiniciar(self, si_pregunta: bool):
        if self.state == ST_ENDGAME and self.play_while_win:
            si_pregunta = False
        if si_pregunta:
            if not QTMessages.pregunta(self.main_window, _("Restart the game?")):
                return
        self.crash_adjourn_end()
        if self.timed:
            self.main_window.stop_clock()
        self.analyze_terminate()
        if self.book_rival_select == SELECTED_BY_PLAYER or self.nAjustarFuerza == ADJUST_SELECTED_BY_PLAYER:
            self.cache = {}
        self.reinicio["cache"] = self.cache
        self.reinicio["cache_analysis"] = self.cache_analysis
        if not self.play_while_win:
            self.autosave_now()

        if "play_position" in self.reinicio:
            self.procesador.close_engines()
            dic, restore_game = self.reinicio["play_position"]
            self.play_position(dic, restore_game)
            return

        self.game.reset()
        self.main_window.active_information_pgn(False)

        reinicio = self.reinicio.get("REINIT", 0) + 1
        self.game.set_tag("Reinit", str(reinicio))
        self.reinicio["REINIT"] = reinicio

        self.start(self.reinicio)

    def adjourn(self):
        if QTMessages.pregunta(self.main_window, _("Do you want to adjourn the game?")):
            self.crash_adjourn_end()
            dic = self.save_state()

            # se guarda en una bd Adjournments dic key = fecha y hora y tipo
            label_menu = f"{_('Play against an engine')}. {self.rival_name}"

            self.state = ST_ENDGAME

            self.finalizar()
            if self.is_tutor_analysing:
                self.analyze_end()

            bp = dic.get("BOOKP")
            if bp:
                bp.book = None
            br = dic.get("BOOKR")
            if br:
                br.book = None

            with Adjournments.Adjournments() as adj:
                if self.game_type == GT_AGAINST_ENGINE:
                    engine = dic["RIVAL"]["CM"]
                    if hasattr(engine, "ICON"):
                        delattr(engine, "ICON")
                adj.add(self.game_type, dic, label_menu)
                adj.si_seguimos(self)

    def crash_adjourn_init(self):
        if self.configuration.x_prevention_crashes:
            label_menu = f"{_('Play against an engine')}. {self.rival_name}"
            with Adjournments.Adjournments() as adj:
                self.key_crash = adj.key_crash(self.game_type, label_menu)
        else:
            self.key_crash = None

    def crash_adjourn(self):
        if self.key_crash is None:
            return
        with Adjournments.Adjournments() as adj:
            dic = self.save_state(temporary=True)
            dic1 = {}
            for k, v in dic.items():
                if k not in ("BOOKR", "BOOKP", "play_position"):
                    dic1[k] = v

            if self.game_type == GT_AGAINST_ENGINE:
                engine = dic1["RIVAL"]["CM"]
                if hasattr(engine, "ICON"):
                    delattr(engine, "ICON")
            adj.add_crash(self.key_crash, dic1)

    def run_adjourn(self, dic: Dict[str, Any]):
        self.restore_state(dic)
        self.check_boards_setposition()
        if self.timed:
            self.show_clocks()
        if self.timed:
            if self.hints:
                self.manager_tutor.check_engine()
            self.manager_rival.check_engine()
            self.start_message()

        self.pgn_refresh(not self.is_engine_side_white)
        self.play_next_move()

    def xpause(self):
        is_white = self.game.last_position.is_white
        tc = self.tc_white if is_white else self.tc_black
        if is_white == self.is_human_side_white:
            tc.pause()
        else:
            tc.reset()
            self.stop_engine()
        tc.set_labels()
        self.state = ST_PAUSE
        self.thinking(False)
        if self.is_tutor_analysing:
            self.analyze_end()
        self.board.set_position(self.game.first_position)
        self.board.disable_all()
        self.main_window.hide_pgn()
        self.pon_toolbar(ToolbarState.GAME_PAUSED)

    def xcontinue(self):
        self.state = ST_PLAYING
        self.board.set_position(self.game.last_position)
        self.pon_toolbar(ToolbarState.HUMAN_PLAYING)
        self.main_window.show_pgn()
        self.play_next_move()

    def final_x(self):
        return self.finalizar()

    def stop_engine(self):
        if not self.human_is_playing:
            if self.manager_rival is not None:
                self.manager_rival.stop()

    def finalizar(self):
        if self.state == ST_ENDGAME:
            return True

        def close_comun():
            if self.timed:
                self.main_window.stop_clock()
                self.show_clocks()

            self.crash_adjourn_end()
            self.analyze_terminate()
            self.state = ST_ENDGAME
            self.manager_tutor.close()

        if len(self.game) > 0:

            if not QTMessages.pregunta(self.main_window, _("End game?")):
                return False  # no abandona

            close_comun()
            self.game.set_unknown()
            self.set_end_game(self.with_takeback)
            self.autosave()
        else:
            close_comun()
            self.main_window.active_game(False, False)
            self.remove_captures()
            if self.xRutinaAccionDef:
                self.xRutinaAccionDef(TB_CLOSE)
            else:
                self.procesador.start()

        return True

    def rendirse(self, with_question: bool = True):
        if self.state == ST_ENDGAME:
            return True
        if len(self.game) > 0 or self.play_while_win:
            if with_question:
                if not QTMessages.pregunta(self.main_window, _("Do you want to resign?")):
                    return False  # no abandona
            if self.timed:
                self.main_window.stop_clock()
                self.show_clocks()
            self.analyze_terminate()
            self.game.set_termination(
                TERMINATION_RESIGN, RESULT_WIN_WHITE if self.is_engine_side_white else RESULT_WIN_BLACK
            )
            self.save_summary()
            self.crash_adjourn_end()
            self.set_end_game(self.with_takeback)
            if len(self.game) > 0:
                self.autosave()
        else:
            if self.timed:
                self.main_window.stop_clock()
                self.show_clocks()
            self.analyze_terminate()
            self.main_window.active_game(False, False)
            self.remove_captures()
            self.procesador.start()

        return False

    def takeback(self):
        if len(self.game) and self.in_end_of_line():
            if self.is_tutor_analysing:
                self.is_tutor_analysing = False
                self.manager_tutor.stop()
            if self.hints:
                self.hints -= 1
                self.tutor_con_flechas = self.nArrowsTt > 0 and self.hints > 0
            self.show_hints()
            self.game.remove_last_move(self.is_human_side_white)
            if not self.fen:
                self.game.assign_opening()
            self.goto_end()
            self.reopen_book()
            self.refresh()
            if self.state == ST_ENDGAME:
                self.state = ST_PLAYING
                self.pon_toolbar(ToolbarState.HUMAN_PLAYING)

            if self.timed:
                w_save, b_save = self.dic_times_prev_move[len(self.game)]
                self.tc_white.restore(w_save)
                self.tc_black.restore(b_save)
                self.tc_white.set_labels()
                self.tc_black.set_labels()

            self.play_next_move()

    def reopen_book(self):
        if self.book_rival:
            self.book_rival_active = True
            self.show_basic_label()
        if self.book_player:
            self.book_player_active = True
        self.siBookAjustarFuerza = self.nAjustarFuerza != ADJUST_BETTER

    def play_next_move(self):
        if self.state == ST_ENDGAME:
            self.crash_adjourn_end()
            return

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.rival_is_thinking = False
        self.put_view()

        is_white = self.game.is_white()

        if self.game.is_finished():
            self.crash_adjourn_end()
            self.show_result()
            return

        self.set_side_indicator(is_white)
        self.refresh()

        si_rival = is_white == self.is_engine_side_white

        if len(self.game) > 1:
            self.crash_adjourn()

        if self.timed:
            self.dic_times_prev_move[len(self.game)] = (self.tc_white.save(), self.tc_black.save())

        if si_rival:
            self.play_rival()

        else:
            self.current_helps = 0

            self.play_human()

    def set_summary(self, key: str, value: Any):
        njug = len(self.game)
        if njug not in self.summary:
            self.summary[njug] = {}
        self.summary[njug][key] = value

    def is_mandatory_move(self):
        if self.opening_mandatory:
            if len(self.opening_mandatory.dicFEN) <= len(self.game):
                self.opening_mandatory = None
            else:
                return True

        # OPENING LINE--------------------------------------------------------------------------------------------------
        if self.opening_line:
            fen_basem2 = self.game.last_position.fenm2()
            if fen_basem2 in self.opening_line:
                return True

        # BOOK----------------------------------------------------------------------------------------------------------
        if self.book_player_active:
            fen_base = self.game.last_position.fen()
            lista_jugadas = self.book_player.get_list_moves(fen_base)
            if lista_jugadas:
                return True

        return False

    def analyze_begin(self):
        self.mrm_tutor = None
        self.is_analyzed_by_tutor = False
        self.is_tutor_analysing = False
        if not self.is_tutor_enabled:
            return

        if self.is_mandatory_move():
            return

        if self.game.last_position.fenm2() in self.cache_analysis:
            self.mrm_tutor = self.cache_analysis[self.game.last_position.fenm2()]
            self.is_analyzed_by_tutor = True
            return

        if not self.play_while_win and not self.tutor_con_flechas:
            if self.opening_mandatory or self.ayudas_iniciales <= 0:
                return

        if not self.is_finished():
            self.is_tutor_analysing = True
            self.manager_tutor.analyze_tutor(self.game, self.analyze_bestmove_found, self.analyze_changedepth)

    def analyze_bestmove_found(self, _bestmove):
        if self.is_tutor_analysing:
            self.mrm_tutor = self.manager_tutor.get_current_mrm()
            self.is_tutor_analysing = False
            self.manager_tutor.add_cache_position(self.game.last_position, self.mrm_tutor)
            self.main_window.pensando_tutor(False)
            if self.player_has_moved_a1h8:
                move = self.player_has_moved_a1h8
                self.player_has_moved_a1h8 = None
                self.player_has_moved(move)

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

    def current_bestmove(self) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        if not self.is_in_last_move():
            return None, None, None
        if self.state != ST_PLAYING or self.is_finished() or self.game_type != GT_AGAINST_ENGINE:
            return None, None, None

        fen_base = self.last_fen()

        if self.opening_mandatory:
            apdesde, aphasta, promotion = self.opening_mandatory.from_to_active(fen_base)
            if apdesde:
                return apdesde, aphasta, promotion

        if self.opening_line:
            fenm2 = FasterCode.fen_fenm2(fen_base)
            if fenm2 in self.opening_line:
                st = self.opening_line[fenm2]
                sel = list(st)[0]
                return sel[:2], sel[2:4], sel[4:]

        if self.book_player_active:
            if self.book_player_depth == 0 or self.book_player_depth >= len(self.game):
                pv = self.book_player.select_move_type(fen_base, BOOK_BEST_MOVE)
                if pv:
                    return pv[:2], pv[2:4], pv[4:]

        if self.is_active_analysys_bar():
            rm = self.bestmove_from_analysis_bar()
            if rm:
                return rm.from_sq, rm.to_sq, rm.promotion

        if self.is_tutor_analysing:
            if self.mrm_tutor:
                rm = self.mrm_tutor.best_rm_ordered()
                if rm:
                    return rm.from_sq, rm.to_sq, rm.promotion

        mrm: EngineResponse.MultiEngineResponse
        mrm = self.analize_after_last_move()
        rm = mrm.best_rm_ordered()
        if rm:
            return rm.from_sq, rm.to_sq, rm.promotion

        return None, None, None

    def help_to_move(self):
        if self.is_in_last_move():
            mrm: EngineResponse.MultiEngineResponse
            mrm = self.analize_after_last_move()
            if not mrm or len(mrm.li_rm) == 0:
                return
            move = Move.Move(self.game, position_before=self.game.last_position.copia())
            move.analysis = mrm, 0
            Analysis.show_analysis(
                self.manager_analyzer,
                move,
                self.board.is_white_bottom,
                0,
                must_save=False,
            )
            if self.hints:
                self.hints -= 1
                self.show_hints()

    def help_current(self):
        xfrom, xto, xpromotion = self.current_bestmove()
        if xfrom is None:
            return

        if self.hints:
            self.hints -= 1
            if self.hints:
                self.set_hints(self.hints)
            else:
                self.remove_hints()
        self.pon_toolbar(ToolbarState.HUMAN_PLAYING)
        self.current_helps += 1
        if self.current_helps == 1:
            self.board.mark_position(xfrom, ms=2000)
        else:
            if self.current_helps > 2:
                self.board.remove_arrows()
            self.board.show_arrows(([xfrom, xto, True],))
            self.board.show_arrow_sc()
            if xpromotion and xpromotion != "Q":
                dic = TrListas.dic_nom_pieces()
                QTMessages.temporary_message(self.main_window, dic[xpromotion.upper()], 2.0)

        self.show_hints()

    def play_instead_of_me(self):
        xfrom, xto, xpromotion = self.current_bestmove()
        if xfrom is None:
            return

        if self.hints:
            self.hints -= 1
            if self.hints:
                self.set_hints(self.hints)
            else:
                self.remove_hints()

        self.player_has_moved_base(xfrom, xto, xpromotion)

    def adjust_player(self, mrm_rival: EngineResponse.MultiEngineResponse) -> Optional[EngineResponse.EngineResponse]:
        position = self.game.last_position

        FasterCode.set_fen(position.fen())
        li = FasterCode.get_exmoves()

        li_options = []
        for rm in mrm_rival.li_rm:
            li_options.append(
                (rm, f"{position.pgn_translated(rm.from_sq, rm.to_sq, rm.promotion)} ({rm.abbrev_text()})")
            )
            mv = rm.movimiento()
            for x in range(len(li)):
                if li[x].move() == mv:
                    del li[x]
                    break

        for mj in li:
            rm = EngineResponse.EngineResponse("", position.is_white)
            rm.from_sq = mj.xfrom()
            rm.to_sq = mj.xto()
            rm.promotion = mj.promotion()
            rm.puntos = 0
            li_options.append((rm, position.pgn_translated(rm.from_sq, rm.to_sq, rm.promotion)))

        if len(li_options) == 1:
            return li_options[0][0]

        menu = QTDialogs.LCMenu(self.main_window)
        titulo = _("White") if position.is_white else _("Black")
        icono = Iconos.Carpeta()

        self.main_window.cursor_out_board()
        menu.opcion(None, titulo, icono)
        menu.separador()
        icono = Iconos.PuntoNaranja() if position.is_white else Iconos.PuntoNegro()
        for rm, txt in li_options:
            menu.opcion(rm, txt, icono)
        while True:
            resp = menu.lanza()
            if resp:
                return resp

    def select_book_move_base(
            self, book: Books.Book, book_select: int
    ) -> Tuple[bool, Optional[int], Optional[int], Optional[str]]:
        fen = self.last_fen()

        if book_select == SELECTED_BY_PLAYER:
            lista_jugadas = book.get_list_moves(fen)
            if lista_jugadas:
                resp = WBooks.select_move_books(self.main_window, lista_jugadas, self.game.last_position.is_white)
                return True, resp[0], resp[1], resp[2]
        else:
            pv = book.select_move_type(fen, book_select)
            if pv:
                return True, pv[:2], pv[2:4], pv[4:]

        return False, None, None, None

    def select_book_move(self):
        return self.select_book_move_base(self.book_rival, self.book_rival_select)

    def select_book_move_adjusted(self):
        if self.nAjustarFuerza < 1000:
            return False, None, None, None
        dic_personalidad = self.configuration.li_personalities[self.nAjustarFuerza - 1000]
        nombook = dic_personalidad.get("BOOK", None)
        if (nombook is None) or (not Util.exist_file(nombook)):
            return False, None, None, None

        book = Books.Book("P", nombook, nombook, True)
        book.polyglot()
        mode = dic_personalidad.get("BOOKRR", BOOK_BEST_MOVE)
        return self.select_book_move_base(book, mode)

    def play_human(self):
        self.tc_player.start()
        self.human_is_playing = True
        last_position = self.game.last_position
        si_changed, from_sq, to_sq = self.board.piece_out_position(last_position)
        if si_changed:
            self.board.set_position(last_position)
            if from_sq:
                self.premove = from_sq, to_sq
        if self.premove:
            from_sq, to_sq = self.premove
            promotion = "q" if self.game.last_position.pawn_can_promote(from_sq, to_sq) else None
            ok, error, move = Move.get_game_move(
                self.game, self.game.last_position, self.premove[0], self.premove[1], promotion
            )
            if ok:
                self.player_has_moved_dispatcher(from_sq, to_sq, promotion)
                return
            self.premove = None

        self.player_has_moved_a1h8 = None

        self.game_over_message_pww = None

        self.activate_side(self.is_human_side_white)

        self.pon_toolbar(ToolbarState.HUMAN_PLAYING)

        self.analyze_begin()

    def player_has_moved_dispatcher(self, from_sq: str, to_sq: str, promotion: str = ""):
        """Viene desde el board via MainWindow, es previo, ya que si está pendiente el análisis, sólo se indica que ha
        elegido una jugada"""
        if self.rival_is_thinking:
            return self.check_premove(from_sq, to_sq)

        move = self.check_human_move(from_sq, to_sq, promotion, not self.is_tutor_enabled)
        if not move:
            return False

        if not self.player_has_moved_mandatory(move):
            return False

        self.tc_player.pause()
        self.tc_player.set_labels()

        if self.is_tutor_analysing:
            self.pon_toolbar(ToolbarState.TUTOR_THINKING)
            if self.game_over_message_pww:
                self.analyze_end()
            else:
                self.main_window.pensando_tutor(True)

                self.player_has_moved_a1h8 = move
                if not self.manager_tutor.is_run_fixed():
                    self.analyze_end()
            return None

        return self.player_has_moved(move)

    def player_has_moved_mandatory(self, move: Move.Move) -> bool:
        a1h8 = move.movimiento()
        is_choosed = False
        fen_base = self.last_fen()
        fen_basem2 = FasterCode.fen_fenm2(fen_base)

        # OPENING MANDATORY---------------------------------------------------------------------------------------------
        if self.opening_mandatory:
            if self.opening_mandatory.check_human(fen_base, move.from_sq, move.to_sq):
                is_choosed = True
            else:
                apdesde, aphasta, promotion = self.opening_mandatory.from_to_active(fen_base)
                if apdesde is None:
                    self.opening_mandatory = None
                else:
                    if self.play_while_win:
                        self.board.show_arrows(((apdesde, aphasta, False),))
                        is_choosed = True  # para que continue sin buscar
                        self.game_over_message_pww = _("This movement is not in the mandatory opening")
                    else:
                        self.board.show_arrows_temp(((apdesde, aphasta, False),))
                        self.beep_error()
                        self.tc_player.restart()
                        self.enable_toolbar()
                        self.continue_human()
                        self.analyze_begin()
                        return False

        # OPENING LINE--------------------------------------------------------------------------------------------------
        if self.opening_line:
            if fen_basem2 in self.opening_line:
                st_validos: set = self.opening_line[fen_basem2]
                if a1h8 in st_validos:
                    is_choosed = True
                else:
                    li_flechas = [(a1h8[:2], a1h8[2:4], False) for a1h8 in st_validos]
                    if self.play_while_win:
                        self.board.show_arrows(li_flechas)
                        is_choosed = True  # para que continue sin buscar
                        self.game_over_message_pww = _("This movement is not in the opening line selected")
                    else:
                        self.board.show_arrows_temp(li_flechas)
                        self.beep_error()
                        self.tc_player.restart()
                        self.enable_toolbar()
                        self.continue_human()
                        return False
            else:
                self.dic_reject["opening_line"] += 1
                if self.dic_reject["opening_line"] > 5:
                    self.opening_line = None

        # BOOK----------------------------------------------------------------------------------------------------------
        if not is_choosed and self.book_player_active:
            test_book = False
            if self.book_player_depth == 0 or self.book_player_depth > len(self.game):
                lista_jugadas = self.book_player.get_list_moves(fen_base)
                if lista_jugadas:
                    li = []
                    for apdesde, aphasta, appromotion, nada, nada1 in lista_jugadas:
                        mx = apdesde + aphasta + appromotion
                        if mx.strip().lower() == a1h8:
                            is_choosed = True
                            break
                        li.append((apdesde, aphasta, False))
                    if not is_choosed:
                        if self.play_while_win:
                            self.board.show_arrows(li)
                            self.game_over_message_pww = _("This movement is not in the mandatory book")
                        else:
                            self.board.show_arrows_temp(li)
                            self.tc_player.restart()
                            self.enable_toolbar()
                            self.continue_human()
                            return False
                else:
                    test_book = True
            else:
                test_book = True
            if test_book:
                self.dic_reject["book_player"] += 1
                self.book_player_active = self.dic_reject["book_player"] > 5
            self.show_basic_label()
        return True

    def player_has_moved(self, move: Move.Move) -> bool:
        a1h8 = move.movimiento()
        si_analisis = False
        fen_base = self.last_fen()
        fen_basem2 = FasterCode.fen_fenm2(fen_base)
        self.pon_toolbar(ToolbarState.HUMAN_PLAYING)

        # TUTOR---------------------------------------------------------------------------------------------------------
        is_mate = move.is_mate
        self.analyze_end()  # tiene que acabar siempre
        if not is_mate and self.is_tutor_enabled and not self.game_over_message_pww:
            if not self.tutor_book.si_esta(fen_base, a1h8):
                rm_user, n = self.mrm_tutor.search_rm(a1h8)
                if not rm_user:
                    self.main_window.pensando_tutor(True)
                    self.state = ST_TUTOR_THINKING
                    self.is_tutor_analysing = True
                    self.is_analyzing = True
                    self.pon_toolbar(ToolbarState.TUTOR_THINKING)
                    self.mrm_tutor = self.manager_tutor.analyze_tutor_move(self.game, a1h8)
                    self.state = ST_PLAYING
                    self.pon_toolbar(ToolbarState.HUMAN_PLAYING)
                    self.main_window.pensando_tutor(False)
                    if self.mrm_tutor is None:
                        self.tc_player.restart()
                        self.enable_toolbar()
                        return False
                    rm_user, n = self.mrm_tutor.search_rm(a1h8)
                self.cache_analysis[fen_basem2] = self.mrm_tutor

                si_analisis = True
                points_best, points_user = self.mrm_tutor.dif_points_best(a1h8)
                self.set_summary("POINTSBEST", points_best)
                self.set_summary("POINTSUSER", points_user)

                if self.play_while_win:
                    if Tutor.launch_tutor(self.mrm_tutor, rm_user, tp=MISTAKE):
                        self.game_over_message_pww = _("You have made a bad move.")
                    else:
                        cpws_lost = self.pww_centipawns_lost(self.mrm_tutor, rm_user)
                        if cpws_lost > self.limit_pww:
                            self.game_over_message_pww = "%s<br>%s" % (
                                _("You have exceeded the limit of lost centipawns."),
                                _("Lost centipawns %d") % cpws_lost,
                            )
                    if self.game_over_message_pww:
                        rm0 = self.mrm_tutor.best_rm_ordered()
                        self.board.put_arrow_scvar([(rm0.from_sq, rm0.to_sq)])

                elif Tutor.launch_tutor(self.mrm_tutor, rm_user):
                    if not move.is_mate:
                        si_tutor = True
                        self.beep_error()
                        if self.chance:
                            num = self.mrm_tutor.num_better_move_than(a1h8)
                            if num:
                                while True:
                                    rm_tutor = self.mrm_tutor.rm_best()
                                    menu = QTDialogs.LCMenu(self.main_window)
                                    menu.opcion("None", _("There are %d best movements") % num, Iconos.Engine())
                                    menu.separador()
                                    resp = rm_tutor.abbrev_text_base()
                                    if not resp:
                                        resp = _("Mate")
                                    menu.opcion("tutor", f"&1. {_('Show tutor')} ({resp})", Iconos.Tutor())
                                    menu.separador()
                                    menu.opcion("try", f"&2. {_('Try again')}", Iconos.Atras())
                                    menu.separador()
                                    menu.opcion(
                                        "user",
                                        f"&3. {_('Select my move')} ({rm_user.abbrev_text_base()})",
                                        Iconos.Player(),
                                    )
                                    self.main_window.cursor_out_board()
                                    resp = menu.lanza()
                                    if resp == "user":
                                        si_tutor = False
                                        break
                                    elif resp == "tutor":
                                        break
                                    else:
                                        self.tc_player.restart()
                                        self.continue_human()
                                        self.play_human()
                                        return False
                        if si_tutor:
                            tutor = Tutor.Tutor(self, move, move.from_sq, move.to_sq)

                            li_ap_posibles = self.listaOpeningsStd.list_possible_openings(self.game)

                            if tutor.elegir(self.hints > 0, li_ap_posibles=li_ap_posibles):
                                if self.hints > 0:  # doble entrada a tutor.
                                    self.set_piece_again(move.from_sq)
                                    self.hints -= 1
                                    self.tutor_con_flechas = self.nArrowsTt > 0 and self.hints > 0
                                    from_sq = tutor.from_sq
                                    to_sq = tutor.to_sq
                                    promotion = tutor.promotion
                                    ok, mens, jg_tutor = Move.get_game_move(
                                        self.game, self.game.last_position, from_sq, to_sq, promotion
                                    )
                                    if ok:
                                        move = jg_tutor
                                        self.set_summary("SELECTTUTOR", True)
                            if self.configuration.x_save_tutor_variations:
                                tutor.add_variations_to_move(move, 1 + len(self.game) / 2)

                            del tutor

        # --------------------------------------------------------------------------------------------------------------
        time_s = self.tc_player.stop()
        if self.timed:
            self.show_clocks()

        move.set_time_ms(time_s * 1000)
        if not self.disable_user_time:
            move.set_clock_ms(self.tc_player.pending_time * 1000)
        self.set_summary("TIMEUSER", time_s)

        if si_analisis:
            rm, n_pos = self.mrm_tutor.search_rm(move.movimiento())
            if rm:
                move.analysis = self.mrm_tutor, n_pos
                nag, color = self.mrm_tutor.set_nag_color(rm)
                move.add_nag(nag)

        self.add_move(move)
        self.move_the_pieces(move.list_piece_moves, False)
        self.beep_extended(True)

        if self.game_over_message_pww:
            self.game_over_message_pww = '<span style="font-size:14pts">%s<br>%s<br><br><b>%s</b>' % (
                _("GAME OVER"),
                self.game_over_message_pww,
                _("You can try again, by pressing Reinit, the engine will repeat the moves."),
            )
            self.message_on_pgn(self.game_over_message_pww)
            self.rendirse(with_question=False)
            return True

        self.enable_toolbar()
        self.play_next_move()
        return True

    def play_rival(self):
        self.board.remove_arrows()
        self.tc_rival.start()
        self.human_is_playing = False
        self.rival_is_thinking = True
        self.rm_rival = None
        if not self.is_tutor_enabled:
            self.activate_side(self.is_human_side_white)

        from_sq = to_sq = promotion = ""
        is_choosed = False

        # CACHE---------------------------------------------------------------------------------------------------------
        fen_ultimo = self.last_fen()
        if fen_ultimo in self.cache:
            move = self.cache[fen_ultimo]
            self.move_the_pieces(move.list_piece_moves, True)
            self.add_move(move)
            if self.timed:
                self.tc_rival.restore(move.cacheTime)
                self.show_clocks()
            self.play_next_move()
            return

        # OPENING MANDATORY---------------------------------------------------------------------------------------------
        if self.opening_mandatory:
            is_choosed, from_sq, to_sq, promotion = self.opening_mandatory.run_engine(fen_ultimo)
            if not is_choosed:
                self.opening_mandatory = None

        # BOOK----------------------------------------------------------------------------------------------------------
        if not is_choosed and self.book_rival_active:
            if self.book_rival_depth == 0 or self.book_rival_depth > len(self.game):
                is_choosed, from_sq, to_sq, promotion = self.select_book_move()

                if not is_choosed:
                    self.dic_reject["book_rival"] += 1
            else:
                self.dic_reject["book_rival"] += 1
            self.book_rival_active = self.dic_reject["book_rival"] <= 5
            self.show_basic_label()

        if not is_choosed and self.siBookAjustarFuerza:
            is_choosed, from_sq, to_sq, promotion = self.select_book_move_adjusted()  # book de la personalidad
            if not is_choosed:
                self.siBookAjustarFuerza = False

        # --------------------------------------------------------------------------------------------------------------
        if is_choosed:
            rm_rival = EngineResponse.EngineResponse("Opening", self.is_engine_side_white)
            rm_rival.from_sq = from_sq
            rm_rival.to_sq = to_sq
            rm_rival.promotion = promotion
            self.rival_has_moved(rm_rival)
        else:
            self.play_engine_rival()

    def play_engine_rival(self):
        self.thinking(True)
        self.pon_toolbar(ToolbarState.ENGINE_PLAYING)

        if self.timed:
            seconds_white = self.tc_white.pending_time
            seconds_black = self.tc_black.pending_time
            seconds_move = self.tc_white.seconds_per_move
        else:
            seconds_white = seconds_black = self.unlimited_minutes * 60
            seconds_move = 0

        self.manager_rival.run_engine_params.update_var_time(seconds_white, seconds_black, seconds_move)

        if self.humanize:
            if not self.timed:
                seconds_white = seconds_black = 600

            self.manager_rival.humanize(self.humanize, self.game, seconds_white, seconds_black, seconds_move)

        rm_rival: EngineResponse.EngineResponse = self.manager_rival.play(game=self.game, dispacher=self.dispatch_rival)
        if rm_rival is not None:
            self.rival_has_moved(rm_rival)

    def dispatch_rival(self, rm: EngineResponse.EngineResponse):
        if self.thoughtOp > -1 or self.nArrows > 0:
            if rm:
                if self.nArrows:
                    self.last_time_show_arrows = time.time()
                    self.show_pv(rm.pv, self.nArrows)
                if self.thoughtOp > -1:
                    self.show_dispatch(self.thoughtOp, rm)
        return True

    def mueve_rival_base(self):
        self.rival_has_moved(self.main_window.dato_notify)

    def rival_has_moved(self, rm_rival: EngineResponse.EngineResponse) -> bool:
        if self.state == ST_PAUSE:
            return True
        self.rival_is_thinking = False
        time_s = self.stop_clock(False)
        self.thinking(False)
        self.set_summary("TIMERIVAL", time_s)

        if self.state in (ST_ENDGAME, ST_PAUSE):
            return self.state == ST_ENDGAME
        with_cache = True
        if self.nAjustarFuerza == ADJUST_SELECTED_BY_PLAYER:
            rm_rival = self.adjust_player(self.manager_rival.get_current_mrm())
            with_cache = False

        self.lirm_engine.append(rm_rival)
        if not self.evaluate_rival_rm():
            self.show_result()
            return True

        ok, error, move = Move.get_game_move(
            self.game,
            self.game.last_position,
            rm_rival.from_sq,
            rm_rival.to_sq,
            rm_rival.promotion,
        )
        self.rm_rival = rm_rival
        if ok:
            fen_ultimo = self.last_fen()
            move.set_time_ms(int(time_s * 1000))
            move.set_clock_ms(int(self.tc_rival.pending_time * 1000))
            self.add_move(move)
            self.move_the_pieces(move.list_piece_moves, True)
            self.beep_extended(False)
            if with_cache:
                if self.timed:
                    move.cacheTime = self.tc_rival.save()
                self.cache[fen_ultimo] = move
            self.play_next_move()
            return True

        else:
            return False

    def check_premove(self, from_sq: str, to_sq: str) -> bool:
        self.board.remove_arrows()
        if self.premove:
            if from_sq == self.premove[0] and to_sq == self.premove[1]:
                self.premove = None
                return False
        self.board.show_arrow_premove(from_sq, to_sq)
        self.premove = from_sq, to_sq

        return True

    def remove_premove(self):
        if self.premove:
            self.board.remove_arrows()
            self.premove = None

    def pww_centipawns_lost(
            self, mrm: EngineResponse.MultiEngineResponse, rm_user: EngineResponse.EngineResponse
    ) -> int:
        if len(self.game.li_moves) == 0:
            best = mrm.best_rm_ordered()
            return best.score_abs5() - rm_user.score_abs5()
        for move in self.game.li_moves:
            if move.is_white() == self.is_human_side_white:
                if move.analysis:
                    mrm: EngineResponse.MultiEngineResponse
                    mrm, pos = move.analysis
                    rm_best1: EngineResponse.EngineResponse = mrm.rm_best()
                    return rm_best1.score_abs5() - rm_user.score_abs5()

        return 0

    def enable_toolbar(self):
        self.main_window.toolbar_enable(True)

    def disable_toolbar(self):
        self.main_window.toolbar_enable(False)

    def add_move(self, move: Move.Move):
        self.game.add_move(move)
        self.show_clocks()
        self.board.remove_movables()
        self.check_boards_setposition()

        self.put_arrow_sc(move.from_sq, move.to_sq)

        self.show_hints()

        self.pgn_refresh(self.game.last_position.is_white)

        self.refresh()

    def save_summary(self):
        if not self.with_summary or not self.summary:
            return

        j_num = 0
        j_same = 0
        st_accept = 0
        st_reject = 0
        nt_accept = 0
        nt_reject = 0
        j_sum = 0

        time_user = 0.0
        ntime_user = 0
        time_rival = 0.0
        ntime_rival = 0

        for njg, d in self.summary.items():
            if "POINTSBEST" in d:
                j_num += 1
                p = d["POINTSBEST"] - d["POINTSUSER"]
                if p:
                    if d.get("SELECTTUTOR", False):
                        st_accept += p
                        nt_accept += 1
                    else:
                        st_reject += p
                        nt_reject += 1
                    j_sum += p
                else:
                    j_same += 1
            if "TIMERIVAL" in d:
                ntime_rival += 1
                time_rival += d["TIMERIVAL"]
            if "TIMEUSER" in d:
                ntime_user += 1
                time_user += d["TIMEUSER"]

        comment = self.game.first_comment
        if comment:
            comment += "\n"

        if j_num:
            comment += f"{_('Tutor')}: {self.manager_tutor.name}\n"
            comment += f"{_('Number of moves')}:{j_num}\n"
            comment += f"{_('Same move')}:{j_same} ({j_same * 1.0 / j_num:0.2f}%)\n"
            comment += (
                f"{_('Accepted')}:{nt_accept} ({nt_accept * 100.0 / j_num:0.2f}%)\n -> "
                f"{_('Average centipawns lost')}: {st_accept * 1.0 / nt_accept if nt_accept else 0.0:0.2f}\n"
            )
            comment += (
                f"{_('Rejected')}:{nt_reject} ({nt_reject * 100.0 / j_num:0.2f}%)\n -> "
                f"{_('Average centipawns lost')}: {st_reject * 1.0 / nt_reject if nt_reject else 0.0:0.2f}\n"
            )
            comment += f"{_('Total')}:{j_num} (100%)\n -> {_('Average centipawns lost')}: {j_sum * 1.0 / j_num:0.2f}\n"

        if ntime_user or ntime_rival:
            comment += f"{_('Average time (seconds)')}:\n"
            if ntime_user:
                comment += f"{self.configuration.x_player}: {time_user / ntime_user:0.2f}\n"
            if ntime_rival:
                comment += f"{self.engine_rival.name}: {time_rival / ntime_rival:0.2f}\n"
            comment += f"\n{_('Total time')}:\n"
            if ntime_user:
                comment += f"{self.configuration.x_player}: {Util.secs2str(time_user)}\n"
            if ntime_rival:
                comment += f"{self.engine_rival.name}: {Util.secs2str(time_rival)}\n"

        self.game.first_comment = comment

    def show_result(self):
        self.state = ST_ENDGAME
        self.disable_all()
        self.human_is_playing = False
        if self.timed:
            self.main_window.stop_clock()

        if Code.eboard and Code.eboard.driver:
            self.main_window.delay_routine(
                300, self.muestra_resultado_delayed
            )  # Para que eboard siga su proceso y no se pare por la pregunta
        else:
            self.muestra_resultado_delayed()

    def muestra_resultado_delayed(self):
        mensaje, beep, player_win = self.game.label_result_player(self.is_human_side_white)

        self.beep_result(beep)
        self.save_summary()
        self.autosave()
        QTUtils.refresh_gui()
        p0 = self.main_window.base.pgn.pos()
        p = self.main_window.mapToGlobal(p0)
        if not (self.play_while_win and self.game.termination == TERMINATION_RESIGN):
            QTMessages.message(self.main_window, mensaje, px=p.x(), py=p.y(), si_bold=True)
        self.set_end_game(self.with_takeback)

    def show_hints(self):
        self.set_hints(self.hints, remove_back=False)

    def change_rival(self):
        dic = WPlayAgainstEngine.change_rival(self.main_window, self.configuration, self.reinicio)

        if dic:
            dr = dic["RIVAL"]
            rival = dr["CM"]
            if hasattr(rival, "icono"):
                delattr(rival, "icono")
            for k, v in dic.items():
                self.reinicio[k] = v

            is_white = dic["ISWHITE"]

            self.pon_toolbar(ToolbarState.HUMAN_PLAYING)

            self.nAjustarFuerza = dic["ADJUST"]

            r_t = dr["ENGINE_TIME"] * 100  # Se guarda en decimas y se pasa a milesimas
            r_p = dr["ENGINE_DEPTH"]
            r_n = dr["ENGINE_NODES"]
            if r_t <= 0:
                r_t = None
            if r_p <= 0:
                r_p = None

            dr["RESIGN"] = self.resign_limit
            self.manager_rival.close()
            self.manager_rival = self.procesador.create_manager_engine(
                rival, r_t, r_p, r_n, self.nAjustarFuerza != ADJUST_BETTER
            )

            self.manager_rival.is_white = not is_white

            rival = self.manager_rival.engine.name
            player = self.configuration.x_player
            bl, ng = player, rival
            if not is_white:
                bl, ng = ng, bl
            self.main_window.change_player_labels(bl, ng)

            self.show_basic_label()

            self.put_pieces_bottom(is_white)
            if is_white != self.is_human_side_white:
                self.is_human_side_white = is_white
                self.is_engine_side_white = not is_white

                self.play_next_move()

    def show_dispatch(self, tp: int, rm: EngineResponse.EngineResponse):
        if rm.time or rm.depth:
            # color_engine = "DarkBlue" if self.human_is_playing else "brown"
            if rm.nodes:
                nps = f"/{rm.nps}" if rm.nps else ""
                nodes = f" | {rm.nodes}{nps}"
            else:
                nodes = ""
            seldepth = f"/{rm.seldepth}" if rm.seldepth else ""
            li = [
                f'{rm.name}',
                f'<b>{rm.abbrev_text_base()}</b> | <b>{rm.depth}</b>{seldepth} | <b>{rm.time // 1000}"</b>{nodes}',
            ]
            pv = rm.pv
            if tp < 999:
                li1 = pv.split(" ")
                if len(li1) > tp:
                    pv = " ".join(li1[:tp])
            p = Game.Game(self.game.last_position)
            p.read_pv(pv)
            li.append(p.pgn_base_raw())
            self.set_label3("<br>".join(li))
            QTUtils.refresh_gui()

    def show_clocks(self):
        if not self.timed:
            return

        if Code.eboard:
            Code.eboard.writeClocks(self.tc_white.label_dgt(), self.tc_black.label_dgt())

        for is_white in (WHITE, BLACK):
            tc = self.tc_white if is_white else self.tc_black
            tc.set_labels()

    def change_tutor_active(self):
        previous = self.is_tutor_enabled
        self.is_tutor_enabled = not previous
        self.set_activate_tutor(self.is_tutor_enabled)
        if previous:
            self.analyze_end()
        elif self.human_is_playing:
            self.analyze_begin()
        self.pon_toolbar(ToolbarState.HUMAN_PLAYING)

    def change_last_move_engine(self):
        if self.state != ST_PLAYING or not self.human_is_playing or len(self.game) == 0:
            return
        self.main_window.cursor_out_board()
        menu = QTDialogs.LCMenu(self.main_window)
        last_move = self.game.move(-1)
        position = last_move.position_before
        li_exmoves = position.get_exmoves()
        icono = Iconos.PuntoNaranja() if position.is_white else Iconos.PuntoNegro()

        for mj in li_exmoves:
            rm = EngineResponse.EngineResponse("", position.is_white)
            rm.from_sq = mj.xfrom()
            rm.to_sq = mj.xto()
            rm.promotion = mj.promotion()
            rm.puntos = 0
            txt = position.pgn_translated(rm.from_sq, rm.to_sq, rm.promotion)
            menu.opcion(rm, txt, icono)
        rm = menu.lanza()
        if rm is None:
            return

        self.analyze_terminate()

        self.board.disable_eboard_here()

        last_move = self.game.move(-1)
        self.game.remove_only_last_movement()

        self.set_position(position)
        ok, error, move = Move.get_game_move(self.game, self.game.last_position, rm.from_sq, rm.to_sq, rm.promotion)
        self.rm_rival = rm
        move.set_time_ms(last_move.time_ms)
        move.set_clock_ms(last_move.clock_ms)
        fen_ultimo = self.last_fen()
        self.add_move(move)
        self.move_the_pieces(move.list_piece_moves, True)
        if hasattr(last_move, "cacheTime"):
            move.cacheTime = last_move.cacheTime
        self.cache[fen_ultimo] = move

        self.check_boards_setposition()

        self.board.enable_eboard_here()

        self.play_next_move()

    def show_pv(self, pv: str, n_arrows: int) -> bool:
        if not pv:
            return True
        self.board.remove_arrows()
        pv = pv.strip()
        while "  " in pv:
            pv = pv.replace("  ", " ")
        lipv = pv.split(" ")
        npv = len(lipv)
        nbloques = min(npv, n_arrows)

        for side in range(2):
            base = "p" if side == 0 else "r"
            alt = f"{base}t"
            opacity = 1.00

            previo = None
            for n in range(side, nbloques, 2):
                pv = lipv[n]
                if previo:
                    self.board.show_arrow_mov(previo[2:4], pv[:2], "tr", opacity=max(opacity / 2, 0.3))

                self.board.show_arrow_mov(pv[:2], pv[2:4], base if n == side else alt, opacity=opacity)
                previo = pv
                opacity = max(opacity - 0.20, 0.40)
        return True

    def setup_board_live(self, is_white: bool, position: Position.Position):
        previo = self.current_position().fen()
        previo = " ".join(previo.split(" ")[:2])
        new = position.fen()
        new = " ".join(new.split(" ")[:2])
        if previo != new:
            self.board.set_side_bottom(is_white)
            self.reinicio["FEN"] = position.fen()
            self.reiniciar(False)

    def start_position(self):
        if Code.eboard and Code.eboard.deactivate():
            self.main_window.set_title_toolbar_eboard()

        position, is_white_bottom = Voyager.voyager_position(self.main_window, self.game.last_position)
        if position is not None:
            self.setup_board_live(is_white_bottom, position)

    def control_teclado(self, nkey: int):
        if QTUtils.is_control_pressed():
            if nkey == QtCore.Qt.Key.Key_S:
                self.start_position()

    def list_help_keyboard(self, add_key: Any):
        if self.active_play_instead_of_me():
            add_key("1", _("Play instead of me"), is_ctrl=True)
        if self.active_help_to_move():
            add_key("2", _("Help to move"), is_ctrl=True)

    def active_play_instead_of_me(self):
        if self.state != ST_PLAYING:
            return False
        if self.ayudas_iniciales == 0:
            return True
        return self.hints > 0

    def active_help_to_move(self):
        if self.state != ST_PLAYING:
            return True
        if self.ayudas_iniciales == 0:
            return True
        return self.hints > 0
