import random
import time
from typing import Callable, Any

import Code
from Code.Z import Adjournments, Util
from Code.Adjudicator import Adjudicator
from Code.Base import Move
from Code.Base.Constantes import (
    GT_AGAINST_GM,
    INFINITE,
    ST_ENDGAME,
    ST_PLAYING,
    TB_ADJOURN,
    TB_CLOSE,
    TB_CONFIG,
    TB_REINIT,
    TB_UTILITIES,
)
from Code.Books import Books
from Code.GM import GM, WindowGM
from Code.ManagerBase import Manager
from Code.QT import QTMessages
from Code.ZQT import WindowJuicio
from Code.SQL import UtilSQL


class AdjudicatorGM(Adjudicator.Adjudicator):
    def __init__(self, owner, gm, rut_player_move: Callable, name_engine: str, ms_time: int, depth: int, multipv: int):
        self.name_engine = name_engine
        self.depth = depth
        self.ms_time = ms_time
        self.multipv = multipv
        super().__init__(owner, owner.main_window, gm, rut_player_move)
        self.disable_message_same_book_moves()

    def open_manager_analyzer(self):
        engine = Code.configuration.engines.search(self.name_engine, defecto="stockfish")
        return Code.procesador.create_manager_analysis(engine, self.ms_time, self.depth, 0, self.multipv)


class ManagerGM(Manager.Manager):
    ini_time_s = 0.0
    puntos: int
    record: Util.Record
    adjudicator: AdjudicatorGM
    name_engine: str
    gm_move: Move.Move
    user_move: Move.Move
    gm: str
    vtime: int
    is_white: bool
    modo: GM.GameMode
    with_adjudicator: bool
    show_evals: bool
    mostrar: bool
    select_rival_move: bool
    jugInicial: int
    gameElegida: str
    bypass_book: Books.Book
    opening: Any
    on_bypass_book: bool | None
    on_opening: bool
    analysis: tuple | None
    is_human_side_white: bool
    engine_gm: GM.GM
    nombreGM: str
    rival_name: str
    textoPuntuacion: str
    time_s_end: float

    def start(self, record):
        self.base_inicio(record)
        self.play_next_move()

    def base_inicio(self, record):
        self.game_type = GT_AGAINST_GM

        self.hints = INFINITE  # Para que analice sin problemas

        self.puntos = 0

        self.record = record

        self.gm = record.gm
        self.is_white = record.is_white
        self.modo = record.modo
        self.with_adjudicator = record.with_adjudicator
        self.show_evals = record.show_evals
        self.mostrar = record.mostrar
        self.select_rival_move = record.select_rival_move
        self.jugInicial = record.jugInicial
        self.gameElegida = record.gameElegida
        self.bypass_book = record.bypass_book
        self.opening = record.opening
        self.on_bypass_book = True if self.bypass_book else False
        if self.on_bypass_book:
            self.bypass_book.polyglot()
        self.on_opening = True if self.opening else False

        self.is_analyzing = False

        if self.with_adjudicator:
            name_engine = record.engine
            ms_time = int(record.vtime * 100)
            depth = record.depth
            multipv = record.multiPV
            self.adjudicator = AdjudicatorGM(self, self.gm, self.player_has_moved, name_engine, ms_time, depth, multipv)
            self.puntos = 0
            self.analysis = None

        self.thinking(True)

        default = GM.get_folder_gm()
        carpeta = default if self.modo == GM.GameMode.STANDARD else self.configuration.paths.folder_personal_trainings()
        self.engine_gm = GM.GM(carpeta, self.gm)
        self.engine_gm.filter_side(self.is_white)
        if self.gameElegida is not None:
            self.engine_gm.set_game_selected(self.gameElegida)

        self.is_human_side_white = self.is_white
        self.is_engine_side_white = not self.is_white
        self.thinking(False)

        self.set_toolbar((TB_CLOSE, TB_REINIT, TB_ADJOURN, TB_CONFIG, TB_UTILITIES))
        self.main_window.active_game(True, False)
        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.show_side_indicator(True)
        self.remove_hints()
        self.put_pieces_bottom(self.is_white)
        dic = GM.dic_gm()
        self.nombreGM = dic[self.gm.lower()] if self.modo == GM.GameMode.STANDARD else self.gm
        rot = _("Grandmaster")
        rotulo1 = f"{rot}: <b>{self.nombreGM}</b>" if self.modo == GM.GameMode.STANDARD else f"<b>{self.nombreGM}</b>"
        self.set_label1(rotulo1)

        self.rival_name = ""
        self.textoPuntuacion = ""
        self.add_secondary_label()
        self.pgn_refresh(True)
        self.show_info_extra()

        self.state = ST_PLAYING

        self.check_boards_setposition()

    def add_secondary_label(self):
        self.set_label2(f"{self.rival_name}<br><br>{self.textoPuntuacion}")

    def run_action(self, key):
        if key == TB_CLOSE:
            self.end_game()

        elif key == TB_REINIT:
            self.reiniciar()

        elif key == TB_ADJOURN:
            self.adjourn()

        elif key == TB_CONFIG:
            self.configurar(with_sounds=True)

        elif key == TB_UTILITIES:
            self.utilities()

        elif key in self.procesador.li_opciones_inicio:
            self.procesador.run_action(key)

        else:
            self.routine_default(key)

    def final_x(self):
        if self.state == ST_ENDGAME:
            return True
        return self.end_game()

    def end_game(self):
        if self.with_adjudicator:
            self.adjudicator.close()
        if len(self.game) > 0 and self.state != ST_ENDGAME:
            self.game.set_unknown()
            self.set_end_game()
        self.procesador.start()

        return False

    def reiniciar(self):
        if QTMessages.pregunta(self.main_window, _("Restart the game?")):
            self.adjudicator.analyze_end()
            self.game.set_position()
            self.main_window.active_information_pgn(False)
            self.start(self.record)

    def automatic_move(self) -> list | None:
        if self.jugInicial > 1:
            si_jug_inicial = len(self.game) < (self.jugInicial - 1) * 2
        else:
            si_jug_inicial = False

        li_alternativas = self.engine_gm.alternativas()
        nli_alternativas = len(li_alternativas)

        # Movimiento automatico
        move = None
        if si_jug_inicial or self.on_opening or self.on_bypass_book:
            si_buscar = True
            if self.on_opening:
                li_pv = self.opening.a1h8.split(" ")
                nj = len(self.game)
                if len(li_pv) > nj:
                    move = li_pv[nj]
                    if move in li_alternativas:
                        si_buscar = False
                    else:
                        self.on_opening = False
                else:
                    self.on_opening = False

            if si_buscar:
                if self.on_bypass_book:
                    li_moves = self.bypass_book.get_list_moves(self.last_fen())
                    li_n = []
                    for from_sq, to_sq, promotion, pgn, peso in li_moves:
                        move = from_sq + to_sq + promotion
                        if move in li_alternativas:
                            li_n.append(move)
                    if li_n:
                        si_buscar = False
                        nli_alternativas = len(li_n)
                        if nli_alternativas > 1:
                            pos = random.randint(0, nli_alternativas - 1)
                            move = li_n[pos]
                        else:
                            move = li_n[0]
                    else:
                        self.on_bypass_book = None

            if si_buscar:
                if si_jug_inicial:
                    si_buscar = False
                    if nli_alternativas > 1:
                        pos = random.randint(0, nli_alternativas - 1)
                        move = li_alternativas[pos]
                    elif nli_alternativas == 1:
                        move = li_alternativas[0]

            if not si_buscar:
                self.rival_has_moved(move)
                self.play_next_move()
                return None

        return li_alternativas

    def play_next_move(self):
        self.disable_all()

        if self.state == ST_ENDGAME:
            return

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.put_view()

        is_white = self.game.last_position.is_white

        if (len(self.game) > 0) and self.engine_gm.is_finished():
            self.put_result()
            return

        self.set_side_indicator(is_white)
        self.refresh()

        li_alternativas = self.automatic_move()
        if li_alternativas is None:
            return

        si_rival = is_white == self.is_engine_side_white

        if si_rival:
            self.play_rival(li_alternativas)

        else:
            self.play_human(is_white)

    def play_rival(self, li_alternativas):
        nli_alternativas = len(li_alternativas)
        if nli_alternativas > 1:
            if self.select_rival_move:
                li_moves = self.engine_gm.get_moves_txt(self.game.last_position, False)
                from_sq, to_sq, promotion = WindowGM.select_move(self, li_moves, False)
                move = from_sq + to_sq + promotion
            else:
                pos = random.randint(0, nli_alternativas - 1)
                move = li_alternativas[pos]
        else:
            move = li_alternativas[0]

        self.rival_has_moved(move)
        self.play_next_move()

    def play_human(self, is_white):
        self.human_is_playing = True
        self.ini_time_s = time.time()
        if self.with_adjudicator:
            self.adjudicator.analyze_begin(self.game)
        self.activate_side(is_white)

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        user_move = self.check_human_move(from_sq, to_sq, promotion)
        if not user_move:
            return False
        self.time_s_end = time.time()

        self.board.set_position(user_move.position)
        self.put_arrow_sc(user_move.from_sq, user_move.to_sq)
        self.board.disable_all()

        if self.with_adjudicator:
            position = self.game.last_position
            li_moves = self.engine_gm.get_moves_txt(position, True)
            if len(li_moves) > 1:
                ok = False
                for mv in li_moves:
                    if mv[0] == from_sq and mv[1] == to_sq and mv[2] == promotion:
                        ok = True
                        from_sq_gm, to_sq_gm, promotion_gm = from_sq, to_sq, promotion
                        break
                if not ok:
                    from_sq_gm, to_sq_gm, promotion_gm = WindowGM.select_move(self, li_moves, True)
            else:
                mv = li_moves[0]
                from_sq_gm, to_sq_gm, promotion_gm = mv[0], mv[1], mv[2]
            self.human_is_playing = True
            self.gm_move = self.check_human_move(from_sq_gm, to_sq_gm, promotion_gm)

            self.thinking(True)
            self.adjudicator.check_moves(self.gm_move, user_move)

        else:
            self.player_has_moved(user_move)

        return True

    def player_has_moved(self, user_move, book_moves=False):
        self.thinking(False)
        gm_move = self.gm_move
        movimiento = user_move.movimiento()
        is_valid = self.engine_gm.is_valid_move(movimiento)
        same_move = user_move == gm_move

        show_adjudicator = self.with_adjudicator and self.modo != GM.ShowOption.NEVER and not book_moves
        if show_adjudicator and self.modo == GM.ShowOption.WHEN_DIFFERENT:
            show_adjudicator = not same_move

        position = self.game.last_position

        if self.with_adjudicator and not book_moves:
            mrm = self.adjudicator.get_mrm()
            rm_gm, pos_gm = mrm.search_rm(gm_move.movimiento())
            rm_user, pos_user = mrm.search_rm(user_move.movimiento())
            analysis = mrm, pos_gm
            dpts = rm_user.centipawns_abs() - rm_gm.centipawns_abs()

            pgn_gm = self.gm_move.pgn_translated()
            pgn_user = user_move.pgn_translated()

            if show_adjudicator:
                w = WindowJuicio.WJuicio(
                    self,
                    self.adjudicator,
                    self.nombreGM,
                    position,
                    mrm,
                    rm_gm,
                    rm_user,
                    analysis,
                    is_competitive=self.show_evals != GM.ShowOption.WHEN_DIFFERENT,
                    continue_tt=self.adjudicator.is_analysing(),
                )
                w.exec()

                rm_gm, pos_gm = mrm.search_rm(gm_move.movimiento())
                analysis = mrm, pos_gm
                rm_user = w.rm_usu
                rm_gm = w.rm_obj
                dpts = w.difPuntos()

            self.puntos += dpts

            comentario0 = f"<b>{self.configuration.x_player}</b> : {pgn_user} = {rm_user.texto()}<br>"
            comentario0 += f"<b>{self.nombreGM}</b> : {pgn_gm} = {rm_gm.texto()}<br>"
            comentario1 = f"<br><b>{_('Difference')}</b> = {dpts:+d}<br>"
            comentario2 = f"<b>{_('Centipawns accumulated')}</b> = {self.puntos:+d}<br>"
            self.textoPuntuacion = comentario2
            self.add_secondary_label()

            if not is_valid:
                gm_move.set_comment(
                    (comentario0 + comentario1 + comentario2)
                    .replace("<b>", "")
                    .replace("</b>", "")
                    .replace("<br>", "\n")
                )
            gm_move.analysis = analysis

        if self.with_adjudicator:
            self.adjudicator.analyze_end()

        # self.move_the_pieces(gm_move.list_piece_moves)

        gm_move.set_time_ms(int((self.time_s_end - self.ini_time_s) * 1000))
        self.add_move(True, gm_move, same_move=same_move)
        self.play_next_move()
        return True

    def rival_has_moved(self, move):
        from_sq = move[:2]
        to_sq = move[2:4]
        promotion = move[4:]

        ok, mens, move = Move.get_game_move(self.game, self.game.last_position, from_sq, to_sq, promotion)
        self.add_move(False, move)

        return True

    def add_move(self, si_nuestra, move, comment=None, analysis=None, same_move=False):
        if analysis:
            move.analysis = analysis
        if comment:
            move.set_comment(comment)

        txt = self.engine_gm.label_game_if_unique(is_gm=self.modo == GM.GameMode.STANDARD)
        if txt:
            self.rival_name = txt
        self.add_secondary_label()

        self.check_boards_setposition()
        if not same_move:
            self.board.set_position(move.position_before)
            self.move_the_pieces(move.list_piece_moves, True)
            self.board.set_position(move.position)
            self.board.remove_arrows()
            self.put_arrow_sc(move.from_sq, move.to_sq)
        self.beep_extended(si_nuestra)

        self.game.add_move(move)
        self.engine_gm.play(move.movimiento())

        self.pgn_refresh(self.game.last_position.is_white)
        self.refresh()

    def put_result(self):
        self.state = ST_ENDGAME
        self.board.disable_all()

        mensaje = _("Game ended")

        txt, porc, txt_resumen = self.engine_gm.resultado(self.game)
        mensaje += f"<br><br>{txt}"
        if self.with_adjudicator:
            mensaje += f"<br><br><b>{_('Centipawns accumulated')}</b> = {self.puntos:+d}<br>"

        self.message_on_pgn(mensaje)

        db_histo = UtilSQL.DictSQL(self.configuration.paths.file_gm_histo())

        gm_k = f"P_{self.gm}" if self.modo == "personal" else self.gm

        dic = {
            "FECHA": Util.today(),
            "PUNTOS": self.puntos,
            "PACIERTOS": porc,
            "JUEZ": self.name_engine,
            "TIEMPO": self.vtime,
            "RESUMEN": txt_resumen,
        }

        li_histo = db_histo[gm_k]
        if li_histo is None:
            li_histo = []
        li_histo.insert(0, dic)
        db_histo[gm_k] = li_histo
        db_histo.pack()
        db_histo.close()

    def save_state(self):
        dic = {}
        li_vars = dir(self)
        ti = type(1)
        tb = type(True)
        ts = type("x")
        for var in li_vars:
            xvar = getattr(self, var)
            if not var.startswith("__"):
                if type(xvar) in (ti, tb, ts):
                    dic[var] = xvar
        dic["record"] = self.record
        dic["game"] = self.game.save()
        dic["labels"] = self.get_labels()
        dic["motorgm"] = self.engine_gm
        return dic

    def run_adjourn(self, dic):
        labels = None, None, None
        motorgm = None
        for k, v in dic.items():
            if k == "record":
                self.base_inicio(v)
            elif k == "game":
                self.game.restore(v)
            elif k == "labels":
                labels = v
            elif k == "motorgm":
                motorgm = v
            else:
                setattr(self, k, v)
        if motorgm:
            self.engine_gm = motorgm
        self.restore_labels(labels)
        self.pgn_refresh(True)
        self.repeat_last_movement()
        self.play_next_move()

    def adjourn(self):
        if QTMessages.pregunta(self.main_window, _("Do you want to adjourn the game?")):
            dic = self.save_state()

            label_menu = f"{_('Play like a Grandmaster')} {self.nombreGM}"
            self.state = ST_ENDGAME

            with Adjournments.Adjournments() as adj:
                adj.add(self.game_type, dic, label_menu)
                adj.si_seguimos(self)

    def current_pgn(self):
        gm = self.gm
        motor_gm = self.engine_gm

        game_gm = motor_gm.get_last_game()

        if game_gm:
            event = game_gm.event
            oponent = game_gm.oponent
            fecha = game_gm.date
            result = game_gm.result
        else:
            event = "?"
            oponent = "?"
            fecha = "????.??.??"
            result = "*"

        if self.is_white:
            blancas = gm
            negras = oponent
        else:
            blancas = oponent
            negras = gm

        resp = f'[Event "{event}"]\n'
        resp += f'[Date "{fecha}"]\n'
        resp += f'[White "{blancas}"]\n'
        resp += f'[Black "{negras}"]\n'
        resp += f'[Result "{result.strip()}"]\n'

        ap = self.game.opening
        if ap:
            resp += f'[ECO "{ap.eco}"]\n'
            resp += f'[Opening "{ap.tr_name}"]\n'

        resp += f"\n{self.game.pgn_base()} {result.strip()}"

        return resp
