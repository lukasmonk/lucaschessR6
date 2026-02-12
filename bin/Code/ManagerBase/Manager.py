import random
import time

import FasterCode

import Code
from Code.Z import Adjournments, ControlPGN, TimeControl, Util, XRun
from Code.Base import Game, Move, Position
from Code.Base.Constantes import (
    BLACK,
    COL_BLACK,
    COL_NUMBER,
    DICT_GAME_TYPES,
    GO_BACK,
    GO_BACK2,
    GO_FORWARD,
    GO_FORWARD2,
    GOOD_MOVE,
    GT_ELO,
    GT_MICELO,
    GT_WICKER,
    NO_RATING,
    RESULT_DRAW,
    RS_DRAW,
    RS_DRAW_50,
    RS_DRAW_MATERIAL,
    RS_DRAW_REPETITION,
    RS_UNKNOWN,
    RS_WIN_OPPONENT,
    RS_WIN_OPPONENT_TIME,
    RS_WIN_PLAYER,
    RS_WIN_PLAYER_TIME,
    ST_ENDGAME,
    ST_PLAYING,
    TB_CLOSE,
    TB_CONFIG,
    TB_EBOARD,
    TB_REINIT,
    TB_REPLAY,
    TB_TAKEBACK,
    TB_UTILITIES,
    TERMINATION_DRAW_AGREEMENT,
    WHITE,
)
from Code.Board import BoardTypes
from Code.Databases import DBgames
from Code.Engines import EngineResponse, EngineManagerAnalysis
from Code.ManagerBase import (
    ManagerAnalysis,
    ManagerMenuConfig,
    ManagerMenuUtilities,
    ManagerMenuVista,
    ManagerNavigation,
)
from Code.Openings import Opening, OpeningsStd
from Code.QT import (
    Iconos,
    QTDialogs,
    QTMessages,
    QTUtils,
)
from Code.ZQT import WReplay, WindowArbolBook, WindowArbol


class Manager:
    def __init__(self, procesador):

        self.fen = None

        self.procesador = procesador
        self.procesador.manager = self
        self.main_window = procesador.main_window
        self.board = procesador.board
        self.board.set_accept_drop_pgns(None)
        self.configuration = Code.configuration
        self.runSound = Code.runSound

        self.state = ST_ENDGAME  # Para que siempre este definido

        self.game_type = None
        self.hints = 99999999
        self.ayudas_iniciales = 0
        self.must_be_autosaved = False

        self.is_competitive = False

        self.resultado = RS_UNKNOWN

        self.categoria = None

        self.main_window.set_manager_active(self)

        self.game: Game.Game = Game.Game()
        self.new_game()

        self.listaOpeningsStd = OpeningsStd.ap

        self.human_is_playing = False
        self.is_engine_side_white = False
        self.is_human_side_white = False

        self.pgn = ControlPGN.ControlPGN(self)

        self.manager_tutor: EngineManagerAnalysis.EngineManagerAnalysis = procesador.get_manager_tutor()
        self.manager_analyzer: EngineManagerAnalysis.EngineManagerAnalysis = procesador.get_manager_analyzer()
        self.manager_rival = None
        self.is_tutor_enabled = False

        self.is_analyzing = False
        self.is_analyzed_by_tutor = False

        self.resign_limit = -99999
        self.lirm_engine = []

        self.rm_rival = None  # Usado por el tutor para mostrar las intenciones del rival

        self.um = None

        self.xRutinaAccionDef = None

        self.xpelicula = None

        self.main_window.adjust_size()

        self.board.do_pressed_number = self.do_pressed_number
        self.board.do_pressed_letter = self.do_pressed_letter

        self.capturasActivable = False
        self.activatable_info = False

        self.auto_rotate = None

        self.nonDistract = None

        # x Control del tutor
        #  asi sabemos si ha habido intento de analysis previo (por ejemplo el usuario
        #  mientras piensa decide activar el tutor)
        self.siIniAnalizaTutor = False

        self.continueTt = not self.configuration.x_engine_notbackground

        # Atajos raton:
        self.atajosRatonDestino = None
        self.atajosRatonOrigen = None

        self.messenger = None

        self.closed = False

        self.kibitzers_manager = self.procesador.kibitzers_manager

        self.with_eboard = len(self.configuration.x_digital_board) > 0

        self.with_previous_next = False

        self.tc_white = TimeControl.TimeControl(self.main_window, self.game, WHITE)
        self.tc_black = TimeControl.TimeControl(self.main_window, self.game, BLACK)

        self.ap_ratings = None

        self.key_crash = None

        self.li_marcos_tmp = []
        self.next_test_resign = 999

        self.manager_menu_config = ManagerMenuConfig.ManagerMenuConfig(self)
        self.manager_menu_utilities = ManagerMenuUtilities.ManagerMenuUtilities(self)
        self.manager_menu_vista = ManagerMenuVista.ManagerMenuVista(self)
        self.manager_navigation = ManagerNavigation.ManagerNavigation(self)
        self.manager_analysis = ManagerAnalysis.ManagerAnalysis(self)

    def close(self):
        if not self.closed:
            self.procesador.reset()
            if self.must_be_autosaved:
                self.autosave_now()
                self.must_be_autosaved = False
            self.closed = True

    def disable_use_eboard(self):
        if self.configuration.x_digital_board:
            self.with_eboard = False

    def refresh_pgn(self):
        self.main_window.base.pgn_refresh()

    def new_game(self):
        self.game = Game.Game()
        self.game.set_tag("Site", Code.lucas_chess)
        hoy = Util.today()
        self.game.set_tag("Date", "%d.%02d.%02d" % (hoy.year, hoy.month, hoy.day))

    def set_end_game(self, with_takeback=False):
        self.main_window.thinking(False)
        self.runSound.close()
        self.state = ST_ENDGAME
        self.disable_all()
        li_options = [TB_CLOSE]
        if hasattr(self, "reiniciar"):
            li_options.append(TB_REINIT)
        if len(self.game):
            li_options.append(TB_REPLAY)
            if with_takeback:
                li_options.append(TB_TAKEBACK)
        li_options.append(TB_CONFIG)
        li_options.append(TB_UTILITIES)

        self.set_toolbar(li_options)
        self.main_window.toolbar_enable(True)
        self.remove_hints(remove_back=not with_takeback)

    def set_toolbar(self, li_options):
        self.main_window.pon_toolbar(li_options, with_eboard=self.with_eboard)

    def end_manager(self):
        # se llama from_sq procesador.start, antes de borrar el manager
        self.board.atajos_raton = None
        if self.nonDistract:
            self.main_window.base.tb.setVisible(True)
        if self.must_be_autosaved:
            self.autosave_now()
        self.crash_adjourn_end()

    def crash_adjourn_end(self):
        if self.key_crash:
            with Adjournments.Adjournments() as adj:
                adj.rem_crash(self.key_crash)
                self.key_crash = None

    def reset_shortcuts_mouse(self):
        self.atajosRatonDestino = None
        self.atajosRatonOrigen = None

    @staticmethod
    def other_candidates(li_moves, position, li_c):
        li_player = []
        for mov in li_moves:
            if mov.mate():
                li_player.append((mov.xto(), "P#"))
            elif mov.check():
                li_player.append((mov.xto(), "P+"))
            elif mov.capture():
                li_player.append((mov.xto(), "Px"))
        oposic = position.copia()
        oposic.is_white = not position.is_white
        oposic.en_passant = ""
        si_jaque = FasterCode.ischeck()
        FasterCode.set_fen(oposic.fen())
        li_o = FasterCode.get_exmoves()
        li_rival = []
        for n, mov in enumerate(li_o):
            if not si_jaque:
                if mov.mate():
                    li_rival.append((mov.xto(), "R#"))
                elif mov.check():
                    li_rival.append((mov.xto(), "R+"))
                elif mov.capture():
                    li_player.append((mov.xto(), "Rx"))
            elif mov.capture():
                li_player.append((mov.xto(), "Rx"))

        li_c.extend(li_rival)
        li_c.extend(li_player)

    def colect_candidates(self, a1h8):
        if not hasattr(self.pgn, "get_pos_move"):  # manager60 por ejemplo
            return None
        row, column = self.main_window.pgn_pos_actual()
        pos_move, move = self.pgn.get_pos_move(row, column.key)
        if move:
            position = move.position
        else:
            position = self.game.first_position

        FasterCode.set_fen(position.fen())
        li = FasterCode.get_exmoves()
        if not li:
            return None

        # Se verifica si algun movimiento puede empezar o finalize ahi
        si_origen = si_destino = False
        for mov in li:
            from_sq = mov.xfrom()
            to_sq = mov.xto()
            if a1h8 == from_sq:
                si_origen = True
                break
            if a1h8 == to_sq:
                si_destino = True
                break
        origen = destino = None
        if si_origen or si_destino:
            pieza = position.squares.get(a1h8, None)
            if pieza is None:
                destino = a1h8
            elif position.is_white:
                if pieza.isupper():
                    origen = a1h8
                else:
                    destino = a1h8
            else:
                if pieza.isupper():
                    destino = a1h8
                else:
                    origen = a1h8

        li_c = []
        for mov in li:
            a1 = mov.xfrom()
            h8 = mov.xto()
            si_o = (origen == a1) if origen else None
            si_d = (destino == h8) if destino else None

            if (si_o and si_d) or ((si_o is None) and si_d) or ((si_d is None) and si_o):
                t = (a1, h8)
                if t not in li_c:
                    li_c.append(t)

        if origen:
            li_c = [(dh[1], "C") for dh in li_c]
        else:
            li_c = [(dh[0], "C") for dh in li_c]
        self.other_candidates(li, position, li_c)
        return li_c

    def atajos_raton(self, position, a1h8):
        if a1h8 is None or not self.board.pieces_are_active:
            self.reset_shortcuts_mouse()
            return

        FasterCode.set_fen(position.fen())
        li_moves = FasterCode.get_exmoves()
        if not li_moves:
            return

        # Se verifica si algun movimiento puede empezar o finalize ahi
        li_destinos = []
        li_origenes = []
        for mov in li_moves:
            from_sq = mov.xfrom()
            to_sq = mov.xto()
            if a1h8 == from_sq:
                li_destinos.append(to_sq)
            if a1h8 == to_sq:
                li_origenes.append(from_sq)
        if not (li_destinos or li_origenes):
            self.reset_shortcuts_mouse()
            return

        def mueve():
            self.board.move_piece_temp(self.atajosRatonOrigen, self.atajosRatonDestino)
            if (not self.board.mensajero(self.atajosRatonOrigen, self.atajosRatonDestino)) and self.atajosRatonOrigen:
                self.board.set_piece_again(self.atajosRatonOrigen)
            self.reset_shortcuts_mouse()

        def show_candidates():
            if self.configuration.x_show_candidates:
                li_c = []
                for xmov in li_moves:
                    a1 = xmov.xfrom()
                    h8 = xmov.xto()
                    if a1 == self.atajosRatonOrigen:
                        li_c.append((h8, "C"))
                if self.state != ST_PLAYING:
                    self.other_candidates(li_moves, position, li_c)
                self.board.show_candidates(li_c)

        if self.configuration.x_mouse_shortcuts is None:
            return

        if not self.configuration.x_mouse_shortcuts:
            if li_destinos:
                self.atajosRatonOrigen = a1h8
                self.atajosRatonDestino = None
                show_candidates()
                return
            elif li_origenes:
                self.atajosRatonDestino = a1h8
                if self.atajosRatonOrigen and self.atajosRatonOrigen in li_origenes:
                    mueve()
                else:
                    self.atajosRatonOrigen = None
                    self.atajosRatonDestino = None
                    show_candidates()
            return

        if li_origenes:
            self.atajosRatonDestino = a1h8
            if self.atajosRatonOrigen and self.atajosRatonOrigen in li_origenes:
                mueve()
            elif len(li_origenes) == 1:
                self.atajosRatonOrigen = li_origenes[0]
                mueve()
            else:
                show_candidates()
            return

        if li_destinos:
            self.atajosRatonOrigen = a1h8
            if self.atajosRatonDestino and self.atajosRatonDestino in li_destinos:
                mueve()
            elif len(li_destinos) == 1:
                self.atajosRatonDestino = li_destinos[0]
                mueve()
            else:
                show_candidates()
            return

    def repeat_last_movement(self):
        # Manager ent tac + ent pos si hay game
        if len(self.game):
            move = self.game.last_jg()
            self.board.set_position(move.position_before)
            self.board.put_arrow_sc(move.from_sq, move.to_sq)
            QTUtils.refresh_gui()
            time.sleep(0.6)

            ant_show = self.configuration.x_show_effects
            ant_speed = self.configuration.x_pieces_speed
            self.configuration.x_show_effects = True
            self.configuration.x_pieces_speed = 200
            self.move_the_pieces(move.list_piece_moves, True)
            self.configuration.x_show_effects = ant_show
            self.configuration.x_pieces_speed = ant_speed

            self.board.set_position(move.position)
            self.main_window.base.pgn.refresh()
            self.main_window.base.pgn.gobottom(1 if move.is_white() else 2)
            self.board.put_arrow_sc(move.from_sq, move.to_sq)
            # self.goto_end()

    def move_the_pieces(self, li_moves, is_rival=False):
        self.main_window.end_think_analysis_bar()
        if is_rival and self.configuration.x_show_effects:
            if self.procesador.manager is None:
                return

            rapidez = self.configuration.pieces_speed_porc()
            cpu = self.procesador.cpu
            cpu.reset()
            seconds = None

            # primero los movimientos
            for movim in li_moves:
                if movim[0] == "m":
                    if seconds is None:
                        from_sq, to_sq = movim[1], movim[2]
                        dc = ord(from_sq[0]) - ord(to_sq[0])
                        df = int(from_sq[1]) - int(to_sq[1])
                        # Maxima distancia = 9.9 ( 9,89... sqrt(7**2+7**2)) = 4 seconds
                        dist = (dc**2 + df**2) ** 0.5
                        seconds = 4.0 * dist / (9.9 * rapidez)
                    cpu.move_piece(movim[1], movim[2], seconds)

            if seconds is None:
                seconds = 1.0

            # segundo los borrados
            for movim in li_moves:
                if movim[0] == "b":
                    cpu.remove_piece_in_seconds(movim[1], seconds)

            # tercero los cambios
            for movim in li_moves:
                if movim[0] == "c":
                    cpu.change_piece(movim[1], movim[2], is_exclusive=True)

            cpu.run_linear()

        else:
            for movim in li_moves:
                if movim[0] == "b":
                    self.board.remove_piece(movim[1])
                elif movim[0] == "m":
                    self.board.move_piece(movim[1], movim[2])
                elif movim[0] == "c":
                    self.board.change_piece(movim[1], movim[2])
        # Aprovechamos que esta operacion se hace en cada move
        self.reset_shortcuts_mouse()

    def num_rows(self):
        return self.pgn.num_rows()

    def put_view(self):
        if not hasattr(self.pgn, "get_pos_move"):  # manager60 por ejemplo
            return
        row, column = self.main_window.pgn_pos_actual()
        pos_move, move = self.pgn.get_pos_move(row, column.key)
        inicio = False
        if column.key == COL_NUMBER:
            if row > 0:
                pos_move, move = self.pgn.get_pos_move(row - 1, COL_BLACK)
            else:
                inicio = True

        if self.is_active_analysys_bar():
            self.main_window.run_analysis_bar(self.current_game())

        if move and self.configuration.x_director_icon is False and not inicio:
            if "%csl" in move.comment or "%cal" in move.comment:
                self.board.show_lichess_graphics(move.comment)

        if (
            self.main_window.siCapturas
            or self.main_window.siInformacionPGN
            or self.kibitzers_manager.some_working()
            or self.configuration.x_show_bestmove
            or self.configuration.x_show_rating
        ):
            if move and (self.configuration.x_show_bestmove or self.configuration.x_show_rating):
                move_check = move
                if column.key == COL_NUMBER:
                    if row == 0:
                        move_check = None
                if move_check:
                    if move_check.analysis and self.configuration.x_show_bestmove:
                        self.show_bestmove(move_check)

                    if self.configuration.x_show_rating:
                        self.show_nags(move_check)

            nom_opening = ""
            opening = self.game.opening
            if opening:
                nom_opening = opening.tr_name
                if opening.eco:
                    nom_opening += f" ({opening.eco})"

            self.check_captures()

            if self.main_window.siInformacionPGN:
                if (row == 0 and column.key == COL_NUMBER) or row < 0:
                    self.main_window.put_information_pgn(self.game, None, nom_opening)
                elif move:
                    move_check = move
                    move_check.pos_in_game = pos_move
                    self.main_window.put_information_pgn(None, move_check, nom_opening)

            if self.kibitzers_manager.some_working():
                if self.si_check_kibitzers():
                    self.check_kibitzers(True)
                else:
                    self.kibitzers_manager.stop()
        self.check_changed()

    def check_captures(self):
        if self.main_window.siCapturas and self.board.last_position is not None:
            if Code.configuration.x_captures_mode_diferences:
                dic = self.board.last_position.capturas_diferencia()
            else:
                dic = self.board.last_position.capturas()
            self.main_window.put_captures(dic)

    def show_nags(self, move_check):
        nag = move_check.get_nag()
        color = NO_RATING
        if not nag:
            if move_check.analysis:
                mrm, pos = move_check.analysis
                rm = mrm.li_rm[pos]
                nag, color = mrm.set_nag_color(rm)
        if nag == NO_RATING:
            if move_check.in_the_opening:
                nag = 1000
            elif color == GOOD_MOVE:
                nag = 999
            else:
                if move_check.is_book:
                    nag = 1001
                elif move_check.is_book is None:
                    if self.ap_ratings is None:
                        self.ap_ratings = Opening.OpeningGM()
                    move_check.is_book = self.ap_ratings.check_human(
                        move_check.position_before.fen(),
                        move_check.from_sq,
                        move_check.to_sq,
                    )
                    if move_check.is_book:
                        nag = 1001
        poscelda = (
            0 if (move_check.to_sq[0] < move_check.from_sq[0]) and (move_check.to_sq[1] < move_check.from_sq[1]) else 1
        )
        if nag != NO_RATING or (nag == NO_RATING and move_check.analysis):
            self.board.put_rating(move_check.from_sq, move_check.to_sq, nag, poscelda)
        if nag != 1000 and move_check.in_the_opening:
            poscelda = 1 if poscelda == 0 else 0
            self.board.put_rating(move_check.from_sq, move_check.to_sq, 1000, poscelda)

    def show_bestmove(self, move_check):
        mrm, pos = move_check.analysis
        if pos:  # no se muestra el mejor move si es la realizada
            rm0 = mrm.best_rm_ordered()
            self.board.put_arrow_scvar([(rm0.from_sq, rm0.to_sq)])

    def si_check_kibitzers(self):
        return (self.state == ST_ENDGAME) or (not self.is_competitive)

    def show_bar_kibitzers_variation(self, game_run):
        if self.kibitzers_manager.some_working():
            if self.si_check_kibitzers():
                self.kibitzers_manager.put_game(game_run, self.board.is_white_bottom, False)
        if self.is_active_analysys_bar():
            self.main_window.run_analysis_bar(game_run)

    def current_game(self):
        row, column = self.main_window.pgn_pos_actual()
        pos_move, move = self.pgn.get_pos_move(row, column.key)
        if pos_move is not None:
            if column.key == COL_NUMBER and pos_move != -1:
                pos_move -= 1
        if pos_move is None or pos_move + 1 == len(self.game):
            return self.game
        game_run = self.game.copy_raw(pos_move)
        if move is None or move.position != self.board.last_position:
            game_run = Game.Game(self.board.last_position)
        return game_run

    def check_kibitzers(self, all_kibitzers):
        game_run = self.current_game()
        self.kibitzers_manager.put_game(game_run, self.board.is_white_bottom, not all_kibitzers)

    def put_pieces_bottom(self, is_white):
        self.board.set_side_bottom(is_white)

    def remove_hints(self, also_tutor_back=True, remove_back=True):
        self.main_window.remove_hints(also_tutor_back, remove_back)
        self.set_activate_tutor(False)

    def set_hints(self, hints, remove_back=True):
        self.main_window.set_hints(hints, remove_back)

    def show_button_tutor(self, ok):
        self.main_window.show_button_tutor(ok)

    def thinking(self, si_pensando):
        if self.configuration.x_cursor_thinking:
            self.main_window.thinking(si_pensando)

    def set_activate_tutor(self, si_activar):
        self.main_window.set_activate_tutor(si_activar)
        self.is_tutor_enabled = si_activar

    def change_tutor_active(self):
        self.is_tutor_enabled = not self.is_tutor_enabled
        self.set_activate_tutor(self.is_tutor_enabled)

    def disable_all(self):
        self.board.disable_all()

    def activate_side(self, is_white):
        self.board.activate_side(is_white)

    def show_side_indicator(self, yes_no):
        self.board.side_indicator_sc.setVisible(yes_no)

    def set_side_indicator(self, is_white):
        self.board.set_side_indicator(is_white)

    def set_dispatcher(self, messenger):
        self.messenger = messenger
        self.board.set_dispatcher(self.player_has_moved_base, self.atajos_raton)

    def put_arrow_sc(self, from_sq, to_sq, lipvvar=None):
        self.board.remove_arrows()
        self.board.put_arrow_sc(from_sq, to_sq)
        if lipvvar:
            self.board.put_arrow_scvar(lipvvar)

    def set_piece_again(self, posic):
        self.board.set_piece_again(posic)

    def set_label1(self, mensaje):
        return self.main_window.set_label1(mensaje)

    def set_label2(self, mensaje):
        return self.main_window.set_label2(mensaje)

    def set_label3(self, mensaje):
        return self.main_window.set_label3(mensaje)

    def remove_label3(self):
        return self.main_window.set_label3(None)

    def set_hight_label3(self, px):
        return self.main_window.set_hight_label3(px)

    def get_labels(self):
        return self.main_window.get_labels()

    def restore_labels(self, li_labels):
        lb1, lb2, lb3 = li_labels

        def pon(lb, rut):
            if lb:
                rut(lb)

        pon(lb1, self.set_label1)
        pon(lb2, self.set_label2)
        pon(lb3, self.set_label3)

    def beep_extended(self, is_player_move):
        self.main_window.end_think_analysis_bar()
        if is_player_move:
            if not self.configuration.x_sound_our:
                return
        played = False
        if self.configuration.x_sound_move:
            if len(self.game):
                move = self.game.move(-1)
                played = self.runSound.play_list(move.sounds_list())
        if not played and self.configuration.x_sound_beep:
            self.runSound.play_beep()

    def beep_zeitnot(self):
        self.runSound.play_zeinot()

    def beep_error(self):
        if self.configuration.x_sound_error:
            self.runSound.play_error()

    def beep_result_change(self, resfinal):  # TOO Cambiar por beepresultado1
        if not self.configuration.x_sound_results:
            return
        dic = {
            RS_WIN_PLAYER: "GANAMOS",
            RS_WIN_OPPONENT: "GANARIVAL",
            RS_DRAW: "TABLAS",
            RS_DRAW_REPETITION: "TABLASREPETICION",
            RS_DRAW_50: "TABLAS50",
            RS_DRAW_MATERIAL: "TABLASFALTAMATERIAL",
            RS_WIN_PLAYER_TIME: "GANAMOSTIEMPO",
            RS_WIN_OPPONENT_TIME: "GANARIVALTIEMPO",
        }
        if resfinal in dic:
            self.runSound.play_key(dic[resfinal])

    def beep_result(self, xbeep_result):
        if xbeep_result:
            if not self.configuration.x_sound_results:
                return
            self.runSound.play_key(xbeep_result)

    def pgn_refresh(self, is_white):
        self.main_window.pgn_refresh(is_white)

    def refresh(self):
        self.board.escena.update()
        self.main_window.update()
        QTUtils.refresh_gui()

    def mueve_number(self, tipo):
        self.manager_navigation.mueve_number(tipo)

    def move_according_key(self, tipo):
        self.manager_navigation.move_according_key(tipo)

    def goto_firstposition(self):
        self.manager_navigation.goto_firstposition()

    def goto_pgn_base(self, row, column):
        self.manager_navigation.goto_pgn_base(row, column)

    def goto_end(self):
        self.manager_navigation.goto_end()

    def goto_current(self):
        self.manager_navigation.goto_current()

    def current_move(self):
        return self.manager_navigation.current_move()

    def current_move_number(self):
        return self.manager_navigation.current_move_number()

    def in_end_of_line(self):
        return self.manager_navigation.in_end_of_line()

    def information_pgn(self):
        if self.activatable_info:
            self.main_window.active_information_pgn()
            self.put_view()
            self.refresh()

    def remove_info(self, is_activatable=False):
        self.main_window.active_information_pgn(False)
        self.activatable_info = is_activatable

    def autosave(self):
        self.must_be_autosaved = True
        if len(self.game) > 1:
            self.game.tag_timeend()
            self.game.set_extend_tags()
            if self.ayudas_iniciales > 0:
                if self.hints is not None:
                    usado = self.ayudas_iniciales - self.hints
                    if usado:
                        self.game.set_tag("HintsUsed", str(usado))

    def autosave_now(self):
        if len(self.game) > 1:
            if self.game.has_analisis():
                self.game.add_accuracy_tags()
            DBgames.autosave(self.game)
            self.must_be_autosaved = False

    def show_info_extra(self):
        key = f"SHOW_INFO_EXTRA_{DICT_GAME_TYPES[self.game_type]}"
        dic = self.configuration.read_variables(key)

        captured_material = dic.get("CAPTURED_MATERIAL")
        if captured_material is None:  # importante preguntarlo aquí, no vale pillarlo en el get
            captured_material = self.configuration.x_captures_activate
        self.main_window.activate_captures(captured_material)

        pgn_information = dic.get("PGN_INFORMATION")
        if pgn_information is None:
            pgn_information = self.configuration.x_info_activate
        self.main_window.active_information_pgn(pgn_information)

        analysis_bar = dic.get("ANALYSIS_BAR")
        if analysis_bar is None:
            analysis_bar = self.configuration.x_analyzer_activate_ab
        self.main_window.activate_analysis_bar(analysis_bar)

        self.put_view()

    def change_info_extra(self, who):
        key = f"SHOW_INFO_EXTRA_{DICT_GAME_TYPES[self.game_type]}"
        dic = self.configuration.read_variables(key)

        if who == "pgn_information":
            pgn_information = not self.main_window.is_active_information_pgn()
            if pgn_information == self.configuration.x_info_activate:  # cuando es igual que el por defecto general,
                # se aplicará el general, por lo que si se cambia el general se cambiarán los que tengan None
                pgn_information = None
            dic["PGN_INFORMATION"] = pgn_information

        elif who == "captured_material":
            captured_material = not self.main_window.is_active_captures()
            if captured_material == self.configuration.x_captures_activate:
                captured_material = None
            dic["CAPTURED_MATERIAL"] = captured_material

        elif who == "analysis_bar":
            analysis_bar = not self.main_window.is_active_analysisbar()
            if analysis_bar == self.configuration.x_analyzer_activate_ab:
                analysis_bar = None
            dic["ANALYSIS_BAR"] = analysis_bar

        self.configuration.write_variables(key, dic)

        self.show_info_extra()
        self.put_view()

    def capturas(self):
        if self.capturasActivable:
            self.main_window.activate_captures()
            self.put_view()

    def remove_captures(self):
        self.main_window.activate_captures(False)
        self.put_view()

    def non_distract_mode(self):
        self.nonDistract = self.main_window.base.non_distract_mode(self.nonDistract)
        self.main_window.adjust_size()

    def board_right_mouse(self, _is_control, _is_alt):
        self.board.launch_director()

    def grid_right_mouse(self, _is_shift, _is_control, is_alt):
        if is_alt:
            self.arbol()
        else:
            menu = QTDialogs.LCMenu(self.main_window)
            self.manager_menu_vista.add(menu)
            resp = menu.lanza()
            if resp:
                self.manager_menu_vista.exec(resp)

    def listado(self, tipo):
        if tipo == "pgn":
            return self.pgn.actual()
        elif tipo == "fen":
            return self.fen_active()
        return None

    def active_movement(self):
        row, column = self.main_window.pgn_pos_actual()
        is_white = column.key != COL_BLACK
        pos = row * 2
        if not is_white:
            pos += 1
        if self.game.starts_with_black:
            pos -= 1
        tam_lj = len(self.game)
        si_ultimo = (pos + 1) >= tam_lj
        if si_ultimo:
            pos = tam_lj - 1
        return pos, self.game.move(pos) if tam_lj else None

    def fen_active(self):
        pos, move = self.active_movement()
        if pos == 0:
            row, column = self.main_window.pgn_pos_actual()
            if column.key == COL_NUMBER:
                return self.game.first_position.fen()
        return move.position.fen() if move else self.last_fen()

    def last_fen(self):
        return self.game.last_fen()

    def analyze_with_tutor(self, with_cursor=False):
        return self.manager_analysis.analyze_with_tutor(with_cursor)

    def is_finished(self):
        return self.game.is_finished()

    def get_movement(self, row, key):
        return self.manager_navigation.get_movement(row, key)

    def analize_after_last_move(self):
        return self.manager_analysis.analize_after_last_move()

    def analize_position(self, row, key):
        self.manager_analysis.analize_position(row, key)

    def analizar(self):
        self.manager_analysis.analizar()

    def check_changed(self):
        pass

    def replay(self):
        if not WReplay.param_replay(self.configuration, self.main_window, self.with_previous_next):
            return

        if self.with_previous_next:
            dic_var = WReplay.read_params()
            if dic_var["REPLAY_CONTINUOUS"]:
                getattr(self, "replay_continuous")()
                return

        self.xpelicula = WReplay.Replay(self)

    def replay_direct(self):
        if self.game:
            self.xpelicula = WReplay.Replay(self)

    def set_routine_default(self, rutina):
        self.xRutinaAccionDef = rutina

    def routine_default(self, key):
        if key == TB_EBOARD:
            if Code.eboard and self.with_eboard:
                if Code.eboard.is_working():
                    return
                Code.eboard.set_working()
                if Code.eboard.driver:
                    self.main_window.deactivate_eboard(50)

                else:
                    if Code.eboard.activate(self.board.dispatch_eboard):
                        Code.eboard.set_position(self.board.last_position)

                self.main_window.set_title_toolbar_eboard()
                QTUtils.refresh_gui()

        elif self.xRutinaAccionDef:
            self.xRutinaAccionDef(key)

        elif key == TB_CLOSE:
            self.close()

        elif key == TB_REPLAY:
            self.replay_direct()

        else:
            self.procesador.run_action(key)

    def final_x0(self):
        # Se llama from_sq la main_window al pulsar X
        # Se verifica si estamos en la replay
        if self.xpelicula:
            self.xpelicula.finalize()
            return False
        if self.is_analyzing:
            self.main_window.base.check_is_hide()
        return getattr(self, "final_x")()

    def do_pressed_number(self, si_activar, number):
        if number in [1, 8]:
            if si_activar:
                # Que move esta en el board
                fen = self.board.fen_active()  # fen_active()
                is_white = " w " in fen
                if number == 1:
                    si_mb = is_white
                else:
                    si_mb = not is_white
                self.board.remove_arrows()
                if self.board.arrow_sc:
                    self.board.arrow_sc.hide()
                li = FasterCode.get_captures(fen, si_mb)
                for m in li:
                    d = m.xfrom()
                    h = m.xto()
                    self.board.show_arrow_mov(d, h, "c")
            else:
                num_moves, nj, row, is_white = self.current_move_number()
                if nj < 0:
                    return
                move = self.game.move(nj)
                self.board.set_position(move.position)
                self.board.remove_arrows()
                self.board.put_arrow_sc(move.from_sq, move.to_sq)
                if Code.configuration.x_show_bestmove:
                    move = self.game.move(nj)
                    mrm: EngineResponse.MultiEngineResponse
                    mrm, pos = move.analysis
                    if not move.analysis:
                        return
                    rm0 = mrm.best_rm_ordered()
                    self.board.put_arrow_scvar([(rm0.from_sq, rm0.to_sq)])

        elif number in [2, 7]:
            if si_activar:
                # Que move esta en el board
                fen = self.board.fen_active()  # fen_active()
                is_white = " w " in fen
                if number == 2:
                    si_mb = is_white
                else:
                    si_mb = not is_white
                if si_mb != is_white:
                    fen = FasterCode.fen_other(fen)
                cp = Position.Position()
                cp.read_fen(fen)
                li_movs = cp.aura()

                self.li_marcos_tmp = []
                reg_marco = BoardTypes.Marco()
                color = self.board.config_board.flechaActivoDefecto().colorinterior
                if color == -1:
                    color = self.board.config_board.flechaActivoDefecto().color

                st = set()
                for h8 in li_movs:
                    if h8 not in st:
                        reg_marco.a1h8 = h8 + h8
                        reg_marco.siMovible = True
                        reg_marco.color = color
                        reg_marco.colorinterior = color
                        reg_marco.opacity = 0.5
                        box = self.board.create_marco(reg_marco)
                        self.li_marcos_tmp.append(box)
                        st.add(h8)

            else:
                for box in self.li_marcos_tmp:
                    self.board.xremove_item(box)
                self.li_marcos_tmp = []

    def do_pressed_letter(self, si_activar, letra):
        num_moves, nj, row, is_white = self.current_move_number()
        if not (num_moves and num_moves > nj):
            return
        move = self.game.move(nj)
        if not move.analysis:
            return
        mrm: EngineResponse.MultiEngineResponse
        mrm, pos = move.analysis

        if si_activar:
            self.board.remove_arrows()
            if self.board.arrow_sc:
                self.board.arrow_sc.hide()
            self.board.set_position(move.position_before)

            def show(xpos):
                if xpos >= len(mrm.li_rm):
                    return
                rm: EngineResponse.EngineResponse = mrm.li_rm[xpos]
                li_pv = rm.pv.split(" ")
                for side in range(2):
                    base = "s" if side == 0 else "t"
                    alt = f"m{base}"
                    opacity = 0.8
                    li = [li_pv[x] for x in range(len(li_pv)) if x % 2 == side]
                    for pv in li:
                        self.board.show_arrow_mov(pv[:2], pv[2:4], alt, opacity=opacity)
                        opacity = max(opacity / 1.4, 0.3)

            if letra == "a":
                show(pos)
            else:
                show(ord(letra) - ord("b"))

        else:
            self.board.set_position(move.position)
            self.board.remove_arrows()
            self.board.put_arrow_sc(move.from_sq, move.to_sq)
            if Code.configuration.x_show_bestmove:
                rm0 = mrm.best_rm_ordered()
                self.board.put_arrow_scvar([(rm0.from_sq, rm0.to_sq)])

    def kibitzers(self, orden):
        if orden == "edit":
            self.kibitzers_manager.edit()
        else:
            huella = orden
            self.kibitzers_manager.run_new(huella)
            self.check_kibitzers(False)

    def stop_human(self):
        self.human_is_playing = False
        self.disable_all()

    def continue_human(self):
        self.human_is_playing = True
        self.board.set_base_position(self.game.last_position)
        self.activate_side(self.game.last_position.is_white)
        QTUtils.refresh_gui()

    def check_human_move(self, from_sq, to_sq, promotion, with_premove=False):
        if self.human_is_playing:
            if not with_premove:
                self.stop_human()
        else:
            self.continue_human()
            return None

        movimiento = from_sq + to_sq

        # Peon coronando
        if not promotion and self.game.last_position.pawn_can_promote(from_sq, to_sq):
            promotion = self.board.pawn_promoting(self.game.last_position.is_white)
            if promotion is None:
                self.continue_human()
                return None
        if promotion:
            movimiento += promotion

        ok, error, move = Move.get_game_move(self.game, self.game.last_position, from_sq, to_sq, promotion)
        if ok:
            return move
        else:
            self.continue_human()
            return None

    def consult_books(self, on_live):
        w = WindowArbolBook.WindowArbolBook(self, on_live)
        if w.exec():
            return w.resultado
        else:
            return None

    def set_position(self, position, variation_history=None):
        self.board.set_position(position, variation_history=variation_history)

    def check_boards_setposition(self):
        self.board.set_raw_last_position(self.game.last_position)

    def control1(self):
        if self.active_play_instead_of_me():
            self.play_instead_of_me()

    def control2(self):
        self.check_help_to_move()

    def can_be_analysed(self):
        return len(self.game) > 0 and not (
            self.game_type in (GT_ELO, GT_MICELO, GT_WICKER) and self.is_competitive and self.state == ST_PLAYING
        )

    def check_help_to_move(self):
        if self.active_help_to_move():
            if hasattr(self, "help_to_move"):
                getattr(self, "help_to_move")()

    def play_instead_of_me(self):
        if self.is_in_last_move():
            rm = self.bestmove_from_analysis_bar()
            if rm is None:
                self.main_window.pensando_tutor(True)
                self.thinking(True)
                cp = self.current_position()
                mrm_tutor = self.manager_tutor.analiza(cp.fen())
                self.thinking(False)
                self.main_window.pensando_tutor(False)
                rm = mrm_tutor.best_rm_ordered()
            if rm.from_sq:
                self.player_has_moved_base(rm.from_sq, rm.to_sq, rm.promotion)

    def alt_a(self):
        if self.can_be_analysed():
            self.analizar()

    def active_play_instead_of_me(self):
        if self.is_competitive and not self.game.is_finished():
            return False
        return True

    @staticmethod
    def active_help_to_move():
        return True

    def add_menu_vista(self, menu_vista):
        self.manager_menu_vista.add(menu_vista)

    def exec_menu_vista(self, resp):
        self.manager_menu_vista.exec(resp)

    def configurar(self, li_extra_options=None, with_sounds=False, with_blinfold=True):
        return self.manager_menu_config.launch(li_extra_options, with_sounds, with_blinfold)

    def change_auto_rotate(self):
        self.auto_rotate = not self.auto_rotate
        self.configuration.set_auto_rotate(self.game_type, self.auto_rotate)
        is_white = self.game.last_position.is_white
        if self.auto_rotate:
            if is_white != self.board.is_white_bottom:
                self.board.rotate_board()

    def get_auto_rotate(self):
        return Code.configuration.get_auto_rotate(self.game_type)

    def config_analysis_parameters(self):
        self.manager_analysis.config_analysis_parameters()

    def refresh_analysis(self):
        self.manager_analysis.refresh_analysis()

    def utilities(self, li_extra_options=None, with_tree=True):
        return self.manager_menu_utilities.launch(li_extra_options, with_tree)

    def message_on_pgn(self, mens, titulo=None, delayed=False):
        p0 = self.main_window.base.pgn.pos()
        p = self.main_window.mapToGlobal(p0)
        QTMessages.message(self.main_window, mens, titulo=titulo, px=p.x(), py=p.y(), delayed=delayed)

    def mensaje(self, mens, titulo=None, delayed=False):
        QTMessages.message_bold(self.main_window, mens, titulo, delayed=delayed)

    def show_analysis(self):
        self.manager_analysis.show_analysis()

    def save_pgn_clipboard(self):
        # Llamado desde board
        self.manager_menu_utilities.save_pgn_clipboard()

    def arbol(self):
        row, column = self.main_window.pgn_pos_actual()
        num_moves, nj, row, is_white = self.current_move()
        if column.key == COL_NUMBER:
            nj -= 1
        w = WindowArbol.WindowArbol(self.main_window, self.game, nj, self.procesador)
        w.exec()

    def control0(self):
        row, column = self.main_window.pgn_pos_actual()
        num_moves, nj, row, is_white = self.current_move()
        if num_moves:
            self.game.is_finished()
            if row == 0 and column.key == COL_NUMBER:
                fen = self.game.first_position.fen()
                nj = -1
            else:
                move = self.game.move(nj)
                fen = move.position.fen()

            pgn_active = self.pgn.actual()
            pgn = ""
            for linea in pgn_active.split("\n"):
                if linea.startswith("["):
                    pgn += linea.strip()
                else:
                    break

            p = self.game.copia(nj)
            pgn += p.pgn_base_raw()
            pgn = pgn.replace("|", "-")

            siguientes = ""
            if nj < len(self.game) - 1:
                p = self.game.copy_from_move(nj + 1)
                siguientes = p.pgn_base_raw(p.first_position.num_moves).replace("|", "-")

            txt = f"{fen}||{siguientes}|{pgn}\n"
            QTUtils.set_clipboard(txt)
            QTMessages.temporary_message(
                self.main_window,
                _("It is saved in the clipboard to paste it wherever you want."),
                2,
            )

    def check_draw_player(self):
        # Para elo games + entmaq
        si_acepta = False
        nplies = len(self.game)
        if len(self.lirm_engine) >= 4 and nplies > 40:
            if nplies > 100:
                limite = -50
            elif nplies > 60:
                limite = -100
            else:
                limite = -150
            si_acepta = True
            for rm in self.lirm_engine[-3:]:
                if rm.centipawns_abs() > limite:
                    si_acepta = False
            if not si_acepta:
                si_ceros = True
                for rm in self.lirm_engine[-3:]:
                    if abs(rm.centipawns_abs()) > 15:
                        si_ceros = False
                        break
                if si_ceros:
                    mrm = self.manager_tutor.analiza(self.game.last_position.fen(), None, 7)
                    rm = mrm.best_rm_ordered()
                    if abs(rm.centipawns_abs()) < 15:
                        si_acepta = True
        if si_acepta:
            self.game.last_jg().is_draw_agreement = True
            self.game.set_termination(TERMINATION_DRAW_AGREEMENT, RESULT_DRAW)
        else:
            QTMessages.message_bold(
                self.main_window,
                _("Sorry, but the engine doesn't accept a draw right now."),
            )
        self.next_test_resign = 999
        return si_acepta

    def evaluate_rival_rm(self):
        if len(self.game) < 50 or len(self.lirm_engine) <= 5:
            return True
        if self.next_test_resign:
            self.next_test_resign -= 1
            return True
        b = random.random() ** 0.33

        # Resign
        is_resign = True
        for n, rm in enumerate(self.lirm_engine[-5:]):
            if int(rm.centipawns_abs() * b) > self.resign_limit:
                is_resign = False
                break
        if is_resign:
            if self.runSound and self.configuration.x_sound_results:
                self.runSound.play_key("OFRECERESIGNAR")
            resp = QTMessages.pregunta(
                self.main_window,
                _X(_("%1 wants to resign, do you accept it?"), self.manager_rival.engine.name),
            )
            if resp:
                self.game.resign(self.is_engine_side_white)
                return False
            else:
                self.next_test_resign = 999
                return True

        # # Draw
        is_draw = True
        for rm in self.lirm_engine[-5:]:
            pts = rm.centipawns_abs()
            if (not (-250 < int(pts * b) < -100)) or pts < -250:
                is_draw = False
                break
        if is_draw:
            if self.runSound and self.configuration.x_sound_results:
                self.runSound.play_key("OFRECETABLAS")
            resp = QTMessages.pregunta(
                self.main_window,
                _X(_("%1 proposes draw, do you accept it?"), self.manager_rival.engine.name),
            )
            if resp:
                self.game.last_jg().is_draw_agreement = True
                self.game.set_termination(TERMINATION_DRAW_AGREEMENT, RESULT_DRAW)
                return False
            else:
                self.next_test_resign = 999
                return True

        return True

    def menu_utilities_elo(self):
        if self.is_competitive:
            self.utilities(with_tree=False)
        else:
            li_extra_options = (("books", _("Consult a book"), Iconos.Libros()),)

            resp = self.utilities(li_extra_options, with_tree=True)
            if resp == "books":
                li_movs = self.consult_books(True)
                if li_movs:
                    for x in range(len(li_movs) - 1, -1, -1):
                        from_sq, to_sq, promotion = li_movs[x]
                        self.player_has_moved_dispatcher(from_sq, to_sq, promotion)

    def pgn_informacion_menu(self):
        menu = QTDialogs.LCMenu(self.main_window)

        for key, valor in self.game.dic_tags().items():
            si_fecha = key.upper().endswith("DATE")
            if key.upper() == "FEN":
                continue
            if si_fecha:
                valor = valor.replace(".??", "").replace(".?", "")
            valor = valor.strip("?")
            if valor:
                menu.opcion(key, f"{key} : {valor}", Iconos.PuntoAzul())

        menu.lanza()

    def current_position(self):
        num_moves, nj, row, is_white = self.current_move()
        if nj == -1:
            return self.game.first_position
        else:
            move: Move.Move = self.game.move(nj)
            return move.position

    def play_current_position(self):
        row, column = self.main_window.pgn_pos_actual()
        num_moves, nj, row, is_white = self.current_move()
        self.game.is_finished()
        if row == 0 and column.key == COL_NUMBER or nj == -1:
            gm = self.game.copia(0)
            gm.li_moves = []
        else:
            gm = self.game.copia(nj)
        gm.set_unknown()
        gm.is_finished()
        gm.li_tags = []
        gm.set_tag("Site", Code.lucas_chess)
        gm.set_tag("Event", _("Play current position"))
        for previous in (
            "Event",
            "Site",
            "Date",
            "Round",
            "White",
            "Black",
            "Result",
            "WhiteElo",
            "BlackElo",
        ):
            ori = self.game.get_tag(previous)
            if ori:
                gm.set_tag(f"Original{previous}", ori)
        dic = {"GAME": gm.save(), "ISWHITE": gm.last_position.is_white}
        fich = Util.relative_path(self.configuration.temporary_file("pkd"))
        Util.save_pickle(fich, dic)

        XRun.run_lucas("-play", fich)

    def start_message(self, nomodal=False):
        mensaje = _("Press the continue button to start.")
        self.mensaje(mensaje, delayed=nomodal)

    def player_has_moved_base(self, from_sq, to_sq, promotion=""):
        if self.board.variation_history is not None:
            if not (self.in_end_of_line() and self.board.variation_history.count("|") == 0):
                return self.mueve_variation(from_sq, to_sq, promotion="")
        return self.messenger(from_sq, to_sq, promotion)

    def mueve_variation(self, from_sq, to_sq, promotion=""):
        link_variation_pressed = self.main_window.pgn_information.variantes.link_variation_pressed
        li_variation_move = [int(cnum) for cnum in self.board.variation_history.split("|")]
        num_var_move = li_variation_move[0]

        is_in_main_move = len(li_variation_move) == 1
        variation = None

        if is_in_main_move:
            num_var_move += 1
            var_move = self.game.move(num_var_move)
            # pgn debe ir al siguiente movimiento
        else:
            is_num_variation = True
            var_move = self.game.move(num_var_move)
            variation = None
            for num in li_variation_move[1:]:
                if is_num_variation:
                    variation = var_move.variations.get(num)
                else:
                    var_move = variation.move(num)
                    num_var_move = num
                is_num_variation = not is_num_variation

        if not promotion and var_move.position_before.pawn_can_promote(from_sq, to_sq):
            promotion = self.board.pawn_promoting(var_move.position_before.is_white)
            if promotion is None:
                return
        else:
            promotion = ""

        movimiento = from_sq + to_sq + promotion

        if is_in_main_move:
            if var_move.movimiento() == movimiento:
                self.move_according_key(GO_FORWARD)
                return
            else:
                position_before = var_move.position_before.copia()
                game_var = Game.Game(first_position=position_before)
                ok, mens, new_move = Move.get_game_move(game_var, position_before, from_sq, to_sq, promotion)
                if not ok:
                    return

                game_var.add_move(new_move)
                num_var = var_move.add_variation(game_var)

                self.main_window.active_information_pgn(True)
                row, column = self.main_window.pgn_pos_actual()
                is_white = var_move.position_before.is_white
                # if is_white and column.key == COL_WHITE:
                if is_white and column.key == COL_BLACK:
                    row += 1
                self.main_window.place_on_pgn_table(row, is_white)
                self.put_view()
                link_variation_pressed(f"{num_var_move}|{num_var}|0")
                self.kibitzers_manager.put_game(game_var, self.board.is_white_bottom)
        else:
            # si tiene mas movimientos se verifica si coincide con el siguiente
            if len(variation) > num_var_move + 1:
                cvariation_move = "|".join([cnum for cnum in self.board.variation_history.split("|")][:-1])
                var_move = variation.move(num_var_move + 1)
                if var_move.movimiento() == movimiento:
                    link = "%s|%d" % (cvariation_move, (num_var_move + 1))
                    self.main_window.pgn_information.variantes.link_variation_pressed(link)
                    return

                position_before = var_move.position_before.copia()
                game_var = Game.Game(first_position=position_before)
                ok, mens, new_move = Move.get_game_move(game_var, position_before, from_sq, to_sq, promotion)
                if not ok:
                    return

                game_var.add_move(new_move)
                var_move.add_variation(game_var)
                link_variation_pressed(
                    "%s|%d|%d|%d"
                    % (
                        cvariation_move,
                        (num_var_move + 1),
                        len(var_move.variations) - 1,
                        0,
                    )
                )
                self.kibitzers_manager.put_game(game_var, self.board.is_white_bottom)

            # si no tiene mas movimientos se añade al final
            else:
                position_before = var_move.position.copia()
                ok, mens, new_move = Move.get_game_move(variation, position_before, from_sq, to_sq, promotion)
                if not ok:
                    return

                variation.add_move(new_move)
                cvariation_move = "|".join([cnum for cnum in self.board.variation_history.split("|")][:-1])
                link_variation_pressed("%s|%d" % (cvariation_move, (num_var_move + 1)))
                self.kibitzers_manager.put_game(variation, self.board.is_white_bottom)

    def keypressed_when_variations(self, nkey):
        if len(self.game) == 0:
            return None

        # Si no tiene variantes -> move_according_key
        num_moves, nj, row, is_white = self.current_move()
        main_move: Move.Move = self.game.move(nj)
        if len(main_move.variations) == 0:
            return self.move_according_key(nkey)

        is_shift, is_control, is_alt = QTUtils.keyboard_modifiers()

        variation_history = self.board.variation_history
        navigating_variations = variation_history.count("|") >= 2
        if is_shift or is_control or is_alt:
            if not navigating_variations:
                variation_history = f'{variation_history.split("|")[0]}|0|0'
                self.main_window.pgn_information.variantes.link_variation_pressed(variation_history)
                return None

        if not navigating_variations:
            return self.move_according_key(nkey)

        if variation_history.count("|") == 2:
            num_move, num_variation, num_variation_move = [int(cnum) for cnum in variation_history.split("|")]
            main_move: Move.Move = self.game.move(num_move)
            num_variations = len(main_move.variations)
            num_moves_current_variation = len(main_move.variations.li_variations[num_variation])

            if nkey == GO_BACK:
                if num_variation_move > 0:
                    num_variation_move -= 1
                else:
                    self.move_according_key(nkey)
                    return None
            elif nkey == GO_FORWARD:
                if num_variation_move < num_moves_current_variation - 1:
                    num_variation_move += 1
                else:
                    return None
            elif nkey == GO_BACK2:
                if num_variation > 0 and is_shift:
                    num_variation -= 1
                    num_variation_move = 0
                else:
                    if is_shift:
                        self.main_window.pgn_information.variantes.link_variation_pressed(str(num_move))
                    return None
            elif nkey == GO_FORWARD2:
                if num_variation < num_variations - 1:
                    num_variation += 1
                    num_variation_move = 0
                else:
                    return None
            else:
                return None

            link = f"{num_move}|{num_variation}|{num_variation_move}"
            self.main_window.pgn_information.variantes.link_variation_pressed(link)

        else:

            li_var = variation_history.split("|")
            last = int(li_var[-1])

            if nkey == GO_BACK:
                if last > 0:
                    li_var[-1] = str(last - 1)
                else:
                    li_var = li_var[:-2]

            elif nkey == GO_FORWARD:
                li_var[-1] = str(last + 1)

            elif nkey == GO_BACK2:
                li_var = li_var[:-2]

            elif nkey == GO_FORWARD2:
                li_var = li_var[:-2]

            else:
                return None

            link = "|".join(li_var)
            self.main_window.pgn_information.variantes.link_variation_pressed(link)
        return None

    def bestmove_from_analysis_bar(self):
        return self.main_window.bestmove_from_analysis_bar()

    def is_active_analysys_bar(self):
        return self.main_window.with_analysis_bar

    def is_in_last_move(self) -> bool:
        if self.board.last_position == self.game.last_position and not self.is_finished():
            return True
        else:
            QTMessages.message(
                self.main_window,
                _("This utility only works in the last position of the game and if it is not finished."),
            )
            return False
