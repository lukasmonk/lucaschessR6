import datetime
import random

import OSEngines

import Code
from Code.Z import Adjournments, Util
from Code.Base import Move
from Code.Base.Constantes import (
    GT_ELO,
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
    TB_UTILITIES,
)
from Code.Engines import EngineResponse
from Code.ManagerBase import Manager
from Code.Openings import Opening
from Code.QT import QTDialogs, QTMessages
from Code.SQL import UtilSQL


def list_engines_play_elo():
    x = """amyan|1|1112|5461
amyan|2|1360|6597
amyan|3|1615|7010
amyan|4|1914|7347
alaric|1|1151|5442
alaric|2|1398|6552
alaric|3|1781|7145
alaric|4|2008|7864
bikjump|1|1123|4477
bikjump|2|1204|5352
bikjump|3|1405|5953
bikjump|4|1710|6341
cheng|1|1153|5728
cheng|2|1402|6634
cheng|3|1744|7170
cheng|4|1936|7773
chispa|1|1109|5158
chispa|2|1321|6193
chispa|3|1402|6433
chispa|4|1782|7450
clarabit|1|1134|5210
clarabit|2|1166|6014
clarabit|3|1345|6407
clarabit|4|1501|6863
critter|1|1203|6822
critter|2|1618|7519
critter|3|1938|8196
critter|4|2037|8557
cyrano|1|1184|5587
cyrano|2|1392|6688
cyrano|3|1929|7420
cyrano|4|2033|7945
daydreamer|2|1358|6362
daydreamer|3|1381|6984
daydreamer|4|1629|7462
discocheck|1|1131|6351
discocheck|2|1380|6591
discocheck|3|1613|7064
discocheck|4|1817|7223
fruit|1|1407|6758
fruit|2|1501|6986
fruit|3|1783|7446
fruit|4|1937|8046
gaia|2|1080|5734
gaia|3|1346|6582
gaia|4|1766|7039
garbochess|1|1149|5640
garbochess|2|1387|6501
garbochess|3|1737|7231
garbochess|4|2010|7933
gaviota|1|1166|6503
gaviota|2|1407|7127
gaviota|3|1625|7437
gaviota|4|2026|7957
glaurung|2|1403|6994
glaurung|3|1743|7578
glaurung|4|2033|7945
greko|1|1151|5552
greko|2|1227|6282
greko|3|1673|6861
greko|4|1931|7518
hamsters|1|1142|5779
hamsters|2|1386|6365
hamsters|3|1649|7011
hamsters|4|1938|7457
komodo|1|1187|6636
komodo|2|1514|7336
komodo|3|1633|7902
komodo|4|2036|8226
lime|1|1146|5251
lime|2|1209|6154
lime|3|1500|6907
lime|4|1783|7499
pawny|2|1086|6474
pawny|3|1346|6879
pawny|4|1503|7217
rhetoric|1|1147|5719
rhetoric|2|1371|6866
rhetoric|3|1514|7049
rhetoric|4|1937|7585
rybka|1|1877|8203
rybka|2|2083|8675
rybka|3|2237|9063
rybka|4|2290|9490
simplex|1|1126|4908
simplex|2|1203|5868
simplex|3|1403|6525
simplex|4|1757|7265
stockfish|1|1200|6419
stockfish|2|1285|6252
stockfish|3|1382|6516
stockfish|4|1561|6796
texel|1|1165|6036
texel|2|1401|7026
texel|3|1506|7255
texel|4|1929|7813
toga|1|1202|6066
toga|2|1497|6984
toga|3|2031|7639
toga|4|2038|8254
ufim|1|1214|6161
ufim|2|1415|7260
ufim|3|2014|8032
ufim|4|2104|8363
umko|1|1151|6004
umko|2|1385|6869
umko|3|1883|7462
umko|4|2081|7887"""
    li = []
    dic_engines = OSEngines.read_engines(Code.folder_engines)

    for linea in x.split("\n"):
        key, depth, fide, sts = linea.split("|")
        if key in dic_engines:
            depth = int(depth)
            sts = int(sts)
            fide = int(fide)
            elo = int((fide + 0.2065 * sts + 154.51) / 2)
            li.append((elo, key, depth))
    return li


# li = list_engines_play_elo()
# li.sort(key=lambda x: x[0])
# for x, y, z in li:
#     pr int(x, y)
# p rint(len(li))


class MotorElo:
    def __init__(self, elo, name, alias, depth):
        self.elo = elo
        self.name = name
        self.depth = depth
        self.max_depth = depth
        self.siInterno = depth == 0
        self.depthOpen = (elo / 100 - 8) if elo < 2100 else 100
        self.depthOpen = max(self.depthOpen, 2)
        self.key = alias
        if self.depth:
            self.key += " %d" % self.depth
        self.points_win = self.points_lose = self.points_draw = 0

    def label(self):
        resp = self.name
        if self.depth:
            resp += " %d" % self.depth
        resp += " (%d)" % self.elo
        return resp


class ManagerElo(Manager.Manager):
    list_engines: list[MotorElo]
    error: str
    is_human_side_white: bool
    in_the_opening: bool
    white_elo: int
    black_elo: int
    is_child_engine: bool
    datos_motor: MotorElo
    opening: Opening.OpeningPol
    pte_tool_resigndraw: bool

    def valores(self):
        li = QTDialogs.list_irina()

        self.list_engines = []
        for alias, name, icono, elo in li:
            self.list_engines.append(MotorElo(elo, name, alias, 0))

        def m(xelo, xkey, xdepth):
            self.list_engines.append(MotorElo(xelo, Util.primera_mayuscula(xkey), xkey, xdepth))

        for elo, key, depth in list_engines_play_elo():
            m(elo, key, depth)

        for k, v in self.configuration.engines.dic_engines().items():
            if v.elo > 2000:
                m(v.elo, v.key, None)  # ponemos depth a None, para diferenciar del 0 de los motores internos

        self.list_engines.sort(key=lambda x: x.elo)

    @staticmethod
    def calc_dif_elo(elo_player, elo_rival, result):
        if result == RS_WIN_PLAYER:
            result = 1
        elif result == RS_DRAW:
            result = 0
        else:
            result = -1
        return Util.fide_elo(elo_player, elo_rival, result)

    def list_engines(self, elo):
        self.valores()
        li = []
        total_emgines = len(self.list_engines)
        for num, mt in enumerate(self.list_engines):
            mt_elo = mt.elo
            mt.siOut = False
            if mt_elo > elo + 400:
                mt.siOut = True
                mt_elo = elo + 400
            mt.siJugable = abs(mt_elo - elo) <= 400
            if mt.siJugable:

                def rot(res):
                    return self.calc_dif_elo(elo, mt_elo, res)

                mt.points_win = rot(RS_WIN_PLAYER)
                mt.points_draw = rot(RS_DRAW)
                mt.points_lose = rot(RS_WIN_OPPONENT)

                mt.number = total_emgines - num

                li.append(mt)

        return li

    def get_motor(self, alias, depth):
        self.valores()
        return next(
            (mt for mt in self.list_engines if mt.key == alias and mt.depth == depth),
            None,
        )

    def start(self, datos_motor):
        self.base_inicio(datos_motor)
        self.play_next_move()

    def base_inicio(self, datos_motor):
        self.game_type = GT_ELO

        self.is_competitive = True

        self.resultado = None
        self.human_is_playing = False
        self.state = ST_PLAYING

        is_white = self.determina_side(datos_motor)

        self.is_human_side_white = is_white
        self.is_engine_side_white = not is_white

        self.lirm_engine = []
        self.next_test_resign = 5
        self.resign_limit = -1000

        self.is_tutor_enabled = False
        self.main_window.set_activate_tutor(self.is_tutor_enabled)

        self.hints = 0
        self.ayudas_iniciales = self.hints

        self.in_the_opening = True

        self.datos_motor = datos_motor
        self.opening = Opening.OpeningPol(100, elo=self.datos_motor.elo)

        eloengine = self.datos_motor.elo
        eloplayer = self.configuration.elo_current()
        self.white_elo = eloplayer if is_white else eloengine
        self.black_elo = eloengine if is_white else eloplayer

        self.is_child_engine = self.datos_motor.siInterno
        if self.is_child_engine:
            rival = self.configuration.engines.search("irina")
            depth = 2 if self.datos_motor.key in ("Rat", "Snake") else 1
            self.manager_rival = self.procesador.create_manager_engine(rival, 0, depth, 0)
            self.manager_rival.set_option("Personality", self.datos_motor.key)

        else:
            rival = self.configuration.engines.search(self.datos_motor.key)
            self.manager_rival = self.procesador.create_manager_engine(rival, 0, self.datos_motor.depth, 0)

        self.pte_tool_resigndraw = True

        self.pon_toolbar()

        self.main_window.active_game(True, False)
        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.put_pieces_bottom(is_white)
        self.remove_hints(True, remove_back=True)
        self.show_side_indicator(True)
        label = f'{_("Opponent")}: <b>{self.datos_motor.label()}</b>'
        self.set_label1(label)

        nbsp = "&nbsp;" * 3

        txt = "%s:%+d%s%s:%+d%s%s:%+d" % (
            _("Win"),
            self.datos_motor.points_win,
            nbsp,
            _("Draw"),
            self.datos_motor.points_draw,
            nbsp,
            _("Loss"),
            self.datos_motor.points_lose,
        )

        self.set_label2(f"<center>{txt}</center>")
        self.pgn_refresh(True)
        self.show_info_extra()

        self.check_boards_setposition()

        self.game.set_tag("Event", _("Lucas-Elo"))

        player = self.configuration.nom_player()
        other = self.datos_motor.name
        w, b = (player, other) if self.is_human_side_white else (other, player)
        self.game.set_tag("White", w)
        self.game.set_tag("Black", b)
        self.game.set_tag("WhiteElo", str(self.white_elo))
        self.game.set_tag("BlackElo", str(self.black_elo))

        self.game.add_tag_timestart()

    def adjourn(self):
        if len(self.game) > 0 and QTMessages.pregunta(self.main_window, _("Do you want to adjourn the game?")):
            self.state = ST_ENDGAME
            dic = {
                "ISWHITE": self.is_human_side_white,
                "GAME_SAVE": self.game.save(),
                "CLAVE": self.datos_motor.key,
                "DEPTH": self.datos_motor.depth,
                "PGANA": self.datos_motor.points_win,
                "PPIERDE": self.datos_motor.points_lose,
                "PTABLAS": self.datos_motor.points_draw,
            }

            label_menu = f'{_("Lucas-Elo")}. {self.datos_motor.name}'
            if self.datos_motor.depth:
                label_menu += " - %d" % self.datos_motor.depth
            with Adjournments.Adjournments() as adj:
                adj.add(self.game_type, dic, label_menu)
                adj.si_seguimos(self)

    def run_adjourn(self, dic):
        engine = self.get_motor(dic["CLAVE"], dic["DEPTH"])
        if engine is None:
            return
        engine.points_win = dic["PGANA"]
        engine.points_lose = dic["PPIERDE"]
        engine.points_draw = dic["PTABLAS"]
        self.base_inicio(engine)
        self.is_human_side_white = dic["ISWHITE"]
        self.is_engine_side_white = not self.is_human_side_white
        self.put_pieces_bottom(self.is_human_side_white)

        self.game.restore(dic["GAME_SAVE"])
        self.goto_end()

        self.pon_toolbar()

        self.play_next_move()

    def pon_toolbar(self):
        li_tool = (TB_CANCEL, TB_CONFIG, TB_UTILITIES)
        if self.pte_tool_resigndraw and len(self.game) > 1:
            if self.is_child_engine:
                li_tool = (TB_RESIGN, TB_ADJOURN, TB_CONFIG, TB_UTILITIES)
            else:
                li_tool = (TB_RESIGN, TB_DRAW, TB_ADJOURN, TB_CONFIG, TB_UTILITIES)
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

        elif key == TB_ADJOURN:
            self.adjourn()

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
            if not QTMessages.pregunta(
                self.main_window,
                _("Do you want to resign?") + " (%d)" % self.datos_motor.points_lose,
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
                factor_humanize = 0.5 if self.is_child_engine else 0.8
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

        elo = self.configuration.elo_current()
        if player_win:
            difelo = self.datos_motor.points_win

        elif self.game.is_draw():
            difelo = self.datos_motor.points_draw

        else:
            difelo = self.datos_motor.points_lose

        nelo = elo + difelo
        nelo = max(nelo, 0)
        self.configuration.set_current_elo(nelo)

        self.historial(elo, nelo)
        self.configuration.graba()

        mensaje += "\n\n%s : %d\n" % (
            _("New Lucas-Elo"),
            self.configuration.elo_current(),
        )

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

    def historial(self, elo, nelo):
        dic = {
            "FECHA": datetime.datetime.now(),
            "RIVAL": self.datos_motor.label(),
            "RESULTADO": self.resultado,
            "AELO": elo,
            "NELO": nelo,
        }

        lik = UtilSQL.ListSQL(self.configuration.paths.file_estad_elo())
        lik.append(dic)
        lik.close()

        dd = UtilSQL.DictSQL(self.configuration.paths.file_estad_elo(), tabla="color")
        key = "%s-%d" % (
            self.datos_motor.name,
            self.datos_motor.depth or 0,
        )
        dd[key] = self.is_human_side_white
        dd.close()

    def determina_side(self, engine_elo: MotorElo):
        key = "%s-%d" % (engine_elo.key, engine_elo.depth or 0)

        with UtilSQL.DictSQL(self.configuration.paths.file_estad_elo(), tabla="color") as dd:
            return not dd.get(key, random.choice((True, False)))
