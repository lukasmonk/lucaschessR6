import datetime
import random

import FasterCode

import Code
from Code.Z import Adjournments, Util
from Code.Arbiter import Arbiter
from Code.Base import Game, Move
from Code.Base.Constantes import (
    GO_END,
    GT_FICS,
    GT_FIDE,
    GT_LICHESS,
    RS_DRAW,
    RS_WIN_OPPONENT,
    RS_WIN_PLAYER,
    ST_ENDGAME,
    ST_PLAYING,
    TB_ADJOURN,
    TB_CANCEL,
    TB_CONFIG,
    TB_RESIGN,
    TB_TAKEBACK,
    TB_UTILITIES,
    TB_ARBITER_STOP,
    TB_ARBITER,
)
from Code.ManagerBase import Manager
from Code.QT import QTMessages, QTUtils
from Code.ZQT import WindowJuicio
from Code.SQL import Base, UtilSQL


class ManagerFideFicsLichess(Manager.Manager):
    _db: str
    _activo = None
    _ponActivo = None
    name_obj: str
    _fichEstad: str
    _titulo: str
    _newTitulo: str
    _TIPO: str
    _key_configuration: str
    analysis = None
    comment = None
    eloObj = 0
    eloUsu = 0
    pwin = 0
    pdraw = 0
    plost = 0
    puntos = 0
    nivel = 0
    is_human_side_white = True
    game_obj = None
    pos_move_obj = 0
    numJugadasObj = 0
    tag_result = None
    id_game = 0
    arbiter: Arbiter.Arbiter

    def selecciona(self, type_play):
        self.game_type = type_play
        if type_play == GT_FICS:
            self._db = Code.path_resource("IntFiles", "FicsElo.db")
            self._activo = self.configuration.fics_current
            self._ponActivo = self.configuration.set_current_fics
            self.name_obj = _("Fics-player")
            self._fichEstad = self.configuration.paths.file_estad_fics_elo()
            self._titulo = _("Fics-Elo")
            self._newTitulo = _("New Fics-Elo")
            self._TIPO = "FICS"

        elif type_play == GT_FIDE:
            self._db = Code.path_resource("IntFiles", "FideElo.db")
            self._activo = self.configuration.fide_current
            self._ponActivo = self.configuration.set_current_fide
            self.name_obj = _("Fide-player")
            self._fichEstad = self.configuration.paths.file_estad_fide_elo()
            self._titulo = _("Fide-Elo")
            self._newTitulo = _("New Fide-Elo")
            self._TIPO = "FIDE"

        elif type_play == GT_LICHESS:
            self._db = Code.path_resource("IntFiles", "LichessElo.db")
            self._activo = self.configuration.lichess_current
            self._ponActivo = self.configuration.set_current_lichess
            self.name_obj = _("Lichess-player")
            self._fichEstad = self.configuration.paths.file_estad_lichess_elo()
            self._titulo = _("Lichess-Elo")
            self._newTitulo = _("New Lichess-Elo")
            self._TIPO = "LICHESS"

        self._key_configuration = f"manager{self._TIPO}"

    def elige_juego(self, nivel):
        color = self.get_the_side(nivel)

        db = Base.DBBase(self._db)
        dbf = db.dbfT(
            "data",
            "ROWID",
            condicion=f"LEVEL={nivel} AND WHITE={1 if color else 0}",
        )
        dbf.leer()
        reccount = dbf.reccount()
        recno = random.randint(1, reccount)
        dbf.goto(recno)
        xid = dbf.ROWID
        dbf.cerrar()
        db.cerrar()

        return xid

    def read_id(self, xid):
        db = Base.DBBase(self._db)
        dbf = db.dbfT("data", "LEVEL,WHITE,CABS,MOVS", condicion=f"ROWID={xid}")
        dbf.leer()
        dbf.gotop()

        self.nivel = dbf.LEVEL

        is_white = dbf.WHITE
        self.is_human_side_white = is_white
        self.is_engine_side_white = not is_white

        pv = FasterCode.xpv_pv(dbf.MOVS)
        self.game_obj = Game.Game()
        self.game_obj.read_pv(pv)
        self.pos_move_obj = 0
        self.numJugadasObj = self.game_obj.num_moves()

        li = dbf.CABS.split("\n")
        for x in li:
            if x:
                key, valor = x.split("=")
                self.game.set_tag(key, valor)

        self.tag_result = self.game.get_tag("RESULT")

        self.game.set_unknown()
        dbf.cerrar()
        db.cerrar()

    def start(self, id_game):
        self.base_inicio(id_game)
        self.play_next_move()

    def base_inicio(self, id_game):
        self.resultado = None
        self.human_is_playing = False
        self.state = ST_PLAYING
        self.analysis = None
        self.comment = None
        self.is_analyzing = False

        self.is_competitive = True

        self.read_id(id_game)
        self.id_game = id_game

        self.eloObj = int(self.game.get_tag("WhiteElo" if self.is_human_side_white else "BlackElo"))
        self.eloUsu = self._activo()

        self.pwin = Util.fide_elo(self.eloUsu, self.eloObj, +1)
        self.pdraw = Util.fide_elo(self.eloUsu, self.eloObj, 0)
        self.plost = Util.fide_elo(self.eloUsu, self.eloObj, -1)

        self.puntos = 0

        self.is_tutor_enabled = False
        self.main_window.set_activate_tutor(self.is_tutor_enabled)

        self.hints = 0
        self.ayudas_iniciales = 0

        self.arbiter = Arbiter.Arbiter(self, self.main_window, self.name_obj, self.player_has_moved)

        self.pon_toolbar()

        self.main_window.active_game(True, False)
        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.put_pieces_bottom(self.is_human_side_white)
        self.remove_hints(True, remove_back=True)
        self.show_side_indicator(True)
        label = f"{self._titulo}: <b>{self.eloUsu}</b> | {_('Elo rival')}: <b>{self.eloObj}</b>"
        label += f" | {self.pwin:+d} {self.pdraw:+d} {self.plost:+d}"
        self.set_label1(label)

        self.set_label2("")
        self.pgn_refresh(True)
        self.show_info_extra()

        self.check_boards_setposition()

    def set_score(self):
        self.set_label2(f"{_("Score")}: <b>{self.puntos:+d}</b>")

    def pon_toolbar(self, stop_analysis=False):
        li_tool = [TB_RESIGN, TB_ADJOURN, TB_CONFIG, TB_UTILITIES, TB_ARBITER]
        if stop_analysis:
            li_tool.append(TB_ARBITER_STOP)
        self.set_toolbar(li_tool)
        if stop_analysis:
            for tool in li_tool[:-1]:
                self.main_window.enable_option_toolbar(tool, False)

    def run_action(self, key):
        if key in (TB_RESIGN, TB_CANCEL):
            self.rendirse()

        elif key == TB_CONFIG:
            self.configurar()

        elif key == TB_TAKEBACK:
            return  # disable

        elif key == TB_UTILITIES:
            self.menu_utilities_elo()

        elif key == TB_ADJOURN:
            self.adjourn()

        elif key == TB_ARBITER:
            self.arbiter.change_arbiter_options()

        elif key == TB_ARBITER_STOP:
            self.arbiter.analyze_end()

        elif key in self.procesador.li_opciones_inicio:
            self.procesador.run_action(key)

        else:
            self.routine_default(key)

    def adjourn(self):
        if len(self.game) > 0 and QTMessages.pregunta(self.main_window, _("Do you want to adjourn the game?")):
            dic = {
                "IDGAME": self.id_game,
                "POSJUGADAOBJ": self.pos_move_obj,
                "GAME_SAVE": self.game.save(),
                "PUNTOS": self.puntos,
            }

            with Adjournments.Adjournments() as adj:
                adj.add(self.game_type, dic, self._titulo)
                self.arbiter.close()
                adj.si_seguimos(self)

    def run_adjourn(self, dic):
        id_game = dic["IDGAME"]
        self.base_inicio(id_game)
        self.pos_move_obj = dic["POSJUGADAOBJ"]
        self.game.restore(dic["GAME_SAVE"])
        self.puntos = dic["PUNTOS"]
        self.move_according_key(GO_END)
        self.set_score()

        self.play_next_move()

    def final_x(self):
        return self.rendirse()

    def rendirse(self):
        if self.state == ST_ENDGAME:
            self.arbiter.close()
            return True
        if len(self.game) > 0:
            if not QTMessages.pregunta(self.main_window, f"{_('Do you want to resign?')} ({self.plost})"):
                return False  # no abandona
            self.puntos = -999
            self.arbiter.close()
            self.show_result()
        else:
            self.arbiter.close()
            self.procesador.start()
        return False

    def play_next_move(self):
        if self.state == ST_ENDGAME:
            return

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.put_view()
        is_white = self.game.last_position.is_white

        num_moves = len(self.game)
        if num_moves >= self.numJugadasObj:
            self.show_result()
            return

        si_rival = is_white == self.is_engine_side_white
        self.set_side_indicator(is_white)

        self.refresh()

        if si_rival:
            self.add_move(False)
            QTUtils.deferred_call(3, self.play_next_move)
        else:
            self.human_is_playing = True
            self.activate_side(is_white)
            self.arbiter.analyze_begin(self.game)

    def thinking(self, ok):
        super().thinking(ok)
        self.pon_toolbar(stop_analysis=ok)

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        user_move = self.check_human_move(from_sq, to_sq, promotion)
        if not user_move:
            return False

        self.board.set_position(user_move.position)
        self.put_arrow_sc(user_move.from_sq, user_move.to_sq)
        self.board.disable_all()

        obj_move = self.game_obj.move(self.pos_move_obj)

        self.thinking(True)

        # QTUtils.deferred_call(1, lambda: self.arbiter.check_moves(obj_move, user_move))
        self.arbiter.check_moves(obj_move, user_move)

        return True

    def player_has_moved(self, user_move: Move.Move, book_moves=False):
        self.thinking(False)

        obj_move = self.game_obj.move(self.pos_move_obj)

        if book_moves:
            comentario_obj = comentario_usu = _("book move")
            analysis = ""
            comentario_puntos = ""
        else:
            comentario_usu = ""
            comentario_obj = ""

            mrm = self.arbiter.get_mrm()
            rm_obj, pos_obj = mrm.search_rm(obj_move.movimiento())
            rm_usu, pos_usu = mrm.search_rm(user_move.movimiento())

            analysis = mrm, pos_obj

            w = WindowJuicio.WJuicio(
                self,
                self.arbiter,
                self.name_obj,
                self.game.last_position,
                mrm,
                rm_obj,
                rm_usu,
                analysis,
                is_competitive=not self.arbiter.show_all,
                continue_tt=self.arbiter.is_analysing(),
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

        self.arbiter.analyze_end()  # Por si acaso no lo está ya.

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

    def add_move(self, si_nuestra, comment=None, analysis=None, same_move=False):
        move = self.game_obj.move(self.pos_move_obj)
        self.pos_move_obj += 1
        if analysis:
            move.analysis = analysis
        if comment:
            move.set_comment(comment)

        if comment:
            self.comment = f"{comment.replace('\n', '<br><br>')}<br>"

        if not si_nuestra:
            if self.pos_move_obj:
                self.comment = None

        self.game.add_move(move)
        self.check_boards_setposition()
        if not same_move:
            self.move_the_pieces(move.list_piece_moves, True)
            self.board.set_position(move.position)
            self.board.remove_arrows()
            self.put_arrow_sc(move.from_sq, move.to_sq)
        self.beep_extended(si_nuestra)

        self.pgn_refresh(self.game.last_position.is_white)
        self.refresh()

    def show_result(self):
        self.arbiter.analyze_end()
        self.disable_all()
        self.human_is_playing = False

        self.state = ST_ENDGAME

        if self.puntos < -50:
            mensaje = _X(_("Unfortunately you have lost against %1."), self.name_obj)
            quien = RS_WIN_OPPONENT
            difelo = self.plost
        elif self.puntos > 50:
            mensaje = _X(_("Congratulations you have won against %1."), self.name_obj)
            quien = RS_WIN_PLAYER
            difelo = self.pwin
        else:
            mensaje = _X(_("Draw against %1."), self.name_obj)
            quien = RS_DRAW
            difelo = self.pdraw

        self.beep_result_change(quien)

        nelo = self.eloUsu + difelo
        if nelo < 0:
            nelo = 0
        self._ponActivo(nelo)

        self.historial(self.eloUsu, nelo)
        self.configuration.graba()

        mensaje += f"<br><br>{self._newTitulo} : {self._activo()}<br>"

        self.mensaje(mensaje)

        if self.tag_result:
            self.game.set_tag("Result", self.tag_result)

        self.set_end_game()

    def historial(self, elo, nelo):
        dic = {
            "FECHA": datetime.datetime.now(),
            "LEVEL": self.nivel,
            "RESULTADO": self.resultado,
            "AELO": elo,
            "NELO": nelo,
        }

        lik = UtilSQL.ListSQL(self._fichEstad)
        lik.append(dic)
        lik.close()

        dd = UtilSQL.DictSQL(self._fichEstad, tabla="color")
        key = f"{self._TIPO}-{self.nivel}"
        dd[key] = self.is_human_side_white
        dd.close()

    def get_the_side(self, nivel):
        key = f"{self._TIPO}-{nivel}"

        dd = UtilSQL.DictSQL(self._fichEstad, tabla="color")
        previo = dd.get(key, random.randint(0, 1) == 0)
        dd.close()
        return not previo
