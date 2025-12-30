from typing import Any, Dict


import Code
from Code.Base.Constantes import (
    ST_PLAYING,
)
from Code.Openings import Opening
from Code.QT import QTDialogs


from Code.Base.Constantes import (
    GT_AGAINST_CHILD_ENGINE,
)
from Code.PlayAgainstEngine import ManagerPlayAgainstEngine


class ManagerPerson(ManagerPlayAgainstEngine.ManagerPlayAgainstEngine):
    imagen: Any
    def _init_vars(self, dic_var: Dict[str, Any]):
        self.reinicio = dic_var

        self.game_type = GT_AGAINST_CHILD_ENGINE
        self.human_is_playing = False
        self.rival_is_thinking = False
        self.state = ST_PLAYING

        self.cache = dic_var.get("cache", {})

        self.summary = {}
        self.with_summary = False

        is_white = dic_var["ISWHITE"]
        self.is_human_side_white = is_white
        self.is_engine_side_white = not is_white

        self.play_while_win = False

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
            self.secs_extra = 0
            zeitnot = 0

            self.disable_user_time = False

            self.tc_player.config_clock(self.max_seconds, self.seconds_per_move, zeitnot, self.secs_extra)
            self.tc_rival.config_clock(self.max_seconds, self.seconds_per_move, zeitnot, 0)

    def _init_hints(self, dic_var: Dict[str, Any]):
        self.hints = 0
        self.with_takeback = False
        self.is_tutor_enabled = False

        self.tutor_con_flechas = False
        self.tutor_book = None
        self.is_analyzed_by_tutor = False

    def _init_opening(self, dic_var: Dict[str, Any]):
        self.opening_mandatory = None
        self.opening_line = None
        self.book_rival_active = False
        self.book_player_active = False
        self.aperturaStd = Opening.OpeningPol(1)

    def _init_game(self, dic_var: Dict[str, Any]):
        self.game.set_tag("Event", _("Opponents for young players"))

        self.player_name = self.configuration.nom_player()
        self.rival_name = self.manager_rival.engine.name

        w, b = self.player_name, self.rival_name
        if not self.is_human_side_white:
            w, b = b, w
        self.game.set_tag("White", w)
        self.game.set_tag("Black", b)

        self.fen = None

        self.game.add_tag_timestart()

        time_control = f"{int(self.max_seconds)}"
        if self.seconds_per_move:
            time_control += f"+{self.seconds_per_move}"
        self.game.set_tag("TimeControl", time_control)

    def _init_rival(self, dic_var: Dict[str, Any]):
        engine = self.configuration.engines.search("irina", None)
        self.manager_rival = self.procesador.create_manager_engine(engine, 0, 2, 0 )
        self.imagen = None
        for name, trans, ico, elo in QTDialogs.list_irina():
            if name == dic_var["RIVAL"]:
                self.manager_rival.engine.name = trans
                self.imagen = ico.pixmap(ico.availableSizes()[0])
                break
        self.manager_rival.set_option("Personality", dic_var["RIVAL"])
        if not dic_var["FASTMOVES"]:
            self.manager_rival.set_option("Max Time", "5")
            self.manager_rival.set_option("Min Time", "1")
            self.humanize = 1
        else:
            self.humanize = 0

        self.lirm_engine = []
        self.next_test_resign = 0
        self.resign_limit = -99999  # never

    def base_inicio(self, dic_var):
        self.reinicio = dic_var
        self._init_vars(dic_var)
        self._init_time(dic_var)
        self._init_rival(dic_var)
        self._init_opening(dic_var)
        self._init_hints(dic_var)
        self._init_game(dic_var)
        self._init_show(dic_var)

    def show_basic_label(self):
        if self.imagen:
            self.main_window.base.lbRotulo1.put_image(self.imagen)
            self.main_window.base.lbRotulo1.show()

