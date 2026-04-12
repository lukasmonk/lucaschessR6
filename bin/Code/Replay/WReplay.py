import collections
import time

import FasterCode
from PySide6 import QtCore, QtGui

import Code
from Code.Base import Position
from Code.Base.Constantes import (
    TB_CONTINUE_REPLAY,
    TB_END_REPLAY,
    TB_FAST_REPLAY,
    TB_PAUSE_REPLAY,
    TB_PGN_REPLAY,
    TB_REPEAT_REPLAY,
    TB_SETTINGS,
    TB_SLOW_REPLAY,
    TB_SPACE,
)
from Code.Board import BoardTypes
from Code.QT import QTDialogs, Iconos
from Code.QT import QTUtils, ScreenUtils


class SpaceControlLayer:
    """Crea 64 MarcoSC persistentes para visualizar el espacio controlado.
    Solo actualiza colores en cada posición (sin crear/destruir items Qt)
    para evitar el temblor que produce recrearlos en cada movimiento."""

    def __init__(self, board):
        self.board = board
        self.marcos = {}  # sq -> MarcoSC
        self._dic_colors = {}
        for side in "WB":
            self._dic_colors[side == "W"] = {
                pos: ScreenUtils.qt_int(Code.dic_colors[f"SQUARED_CONTROLLED_{side}_{pos}"]) for pos in range(6)
            }
        self._create_marcos()

    def _create_marcos(self):
        reg_marco = BoardTypes.Marco()
        reg_marco.siMovible = False
        color0 = self._dic_colors[0]
        for c in "abcdefgh":
            for r in "12345678":
                sq = f"{c}{r}"
                reg_marco.a1h8 = sq + sq
                reg_marco.color = color0
                reg_marco.grosor = 1
                reg_marco.redEsquina = 0
                reg_marco.colorinterior = color0
                box = self.board.create_marco(reg_marco)
                box.setZValue(5)
                box.setVisible(True)
                self.marcos[sq] = box

    def mezclar_con_pesos(self, peso1, peso2):
        # Convertimos las entradas a objetos QColor de PySide6
        color1_val = self._dic_colors[True][min(peso1, 5)]
        color2_val = self._dic_colors[False][min(peso2, 5)]
        c1 = QtGui.QColor(color1_val)
        c2 = QtGui.QColor(color2_val)

        # Calculamos el peso total
        # if peso1 > peso2:
        #     peso1 *= 1.5
        # else:
        #     peso2 *= 1.5
        peso_total = peso1 + peso2

        # Calculamos los nuevos canales ponderados
        # Usamos division entera // para obtener valores validos de 0-255
        r = (c1.red() * peso1 + c2.red() * peso2) // peso_total
        g = (c1.green() * peso1 + c2.green() * peso2) // peso_total
        b = (c1.blue() * peso1 + c2.blue() * peso2) // peso_total
        a = (c1.alpha() * peso1 + c2.alpha() * peso2) // peso_total

        return QtGui.QColor(r, g, b, a).rgba()

    def update(self, fen, number):
        """Recalcula frecuencias y actualiza colores (sin crear/destruir items).
        number=2,3 -> casillas controladas por blancas, 7,6 -> por negras."""
        cp = Position.Position()
        cp.read_fen(fen)
        is_white = " w " in fen
        dic_movs_side = {is_white: cp.aura()}

        fen2 = FasterCode.fen_other(fen)
        cp.read_fen(fen2)
        dic_movs_side[not is_white] = cp.aura()

        if number in (2, 7):
            li_movs = dic_movs_side[number == 2]
            dic_frec = collections.Counter(li_movs)

            for sq, box in self.marcos.items():
                frec = min(dic_frec.get(sq, 0), 5)
                color = self._dic_colors[number == 2][frec]
                box.block_data.color = color
                box.block_data.colorinterior = color

                box.setVisible(True)
                box.update()

        elif number in (3, 6):
            dic_frec_w = collections.Counter(dic_movs_side[True])
            dic_frec_b = collections.Counter(dic_movs_side[False])

            for sq, box in self.marcos.items():
                fw = dic_frec_w.get(sq, 0)
                fb = dic_frec_b.get(sq, 0)
                fw = min(fw, 5)
                fb = min(fb, 5)
                if fw and fb:
                    color = self.mezclar_con_pesos(fw, fb)
                else:
                    if fw:
                        color = self._dic_colors[True][fw]
                    elif fb:
                        color = self._dic_colors[False][fb]
                    else:
                        color = self._dic_colors[False][0]

                box.block_data.color = color
                box.block_data.colorinterior = color
                box.setVisible(True)
                box.update()

        self.board.escena.update()

    def hide(self):
        for box in self.marcos.values():
            box.setVisible(False)
        self.board.escena.update()

    def remove(self):
        for box in self.marcos.values():
            self.board.xremove_item(box)
        self.marcos = {}
        self.board.escena.update()


class ParamsReplay:
    def __init__(self):
        self.key = "PARAMPELICULA"
        self.dic_data = self.read()

    def read(self):
        dic = {
            "SECONDS": 2.0,
            "START": True,
            "PGN": True,
            "BEEP": False,
            "CUSTOM_SOUNDS": False,
            "SECONDS_BEFORE": 0.0,
            "REPLAY_CONTINUOUS": False,
            "TRANSPARENCY": 0,
            "P_WHITE": False,
            "P_BLACK": False,
            "N_WHITE": False,
            "N_BLACK": False,
            "B_WHITE": False,
            "B_BLACK": False,
            "R_WHITE": False,
            "R_BLACK": False,
            "Q_WHITE": False,
            "Q_BLACK": False,
            "K_WHITE": False,
            "K_BLACK": False,
        }
        dic.update(Code.configuration.read_variables(self.key))
        return dic

    def edit(self, parent, with_previous_next):
        from Code.Replay import WReplayParams

        w = WReplayParams.WReplayParams(parent, self.dic_data, with_previous_next)
        if w.exec():
            self.dic_data = w.dvar
            return True
        return False


class Replay:
    seconds: float
    seconds_before: float
    if_beep: bool
    if_custom_sounds: bool
    with_pgn: bool
    ghost_level: float
    dic_ghost_pieces: dict
    board_create_piece: object

    def __init__(self, manager, next_game=None):
        self.params = ParamsReplay()
        dic_var = self.params.dic_data
        self.manager = manager
        self.procesador = manager.procesador
        self.main_window = manager.main_window
        self.starts_with_black = manager.game.starts_with_black
        self.board = manager.board
        self.space_layer = None
        self.relee_params(dic_var)
        self.rapidez = 1.0
        self.next_game = next_game
        self.if_start = True

        self.previous_visible_capturas = self.main_window.siCapturas
        self.previous_visible_information = self.main_window.siInformacionPGN

        self.li_acciones = (
            TB_END_REPLAY,
            TB_SLOW_REPLAY,
            TB_PAUSE_REPLAY,
            TB_CONTINUE_REPLAY,
            TB_FAST_REPLAY,
            TB_REPEAT_REPLAY,
            TB_PGN_REPLAY,
            TB_SETTINGS,
            TB_SPACE
        )

        self.antAcciones = self.main_window.get_toolbar()
        self.main_window.pon_toolbar(self.li_acciones, separator=True)

        self.manager.set_routine_default(self.process_toolbar)

        self.show_pause(True, False)

        self.num_moves, self.jugInicial, self.filaInicial, self.is_white = self.manager.current_move()

        self.li_moves = self.manager.game.li_moves
        self.current_position = 0 if self.if_start else self.jugInicial
        self.initial_position = self.current_position

        self.stopped = False

        # Space control overlay (teclas 2/7): creado una sola vez, colores actualizados
        self._prev_do_pressed_number = self.board.do_pressed_number
        self.board.do_pressed_number = self._do_pressed_number

        self.show_information()

        if self.seconds_before > 0.0:
            if self.li_moves:
                move = self.li_moves[self.current_position]
                self.board.set_position(move.position_before)
                if not self.sleep_refresh(self.seconds_before):
                    return

        self.show_current()

    def relee_params(self, dic_var):
        self.seconds = dic_var["SECONDS"]
        self.seconds_before = dic_var["SECONDS_BEFORE"]
        self.if_start = dic_var["START"]
        self.if_beep = dic_var["BEEP"]
        self.if_custom_sounds = dic_var["CUSTOM_SOUNDS"]
        self.with_pgn = dic_var["PGN"]

        self.space_number = None

        self.ghost_level = dic_var.get("TRANSPARENCY", 0) / 100.0
        self.dic_ghost_pieces = {
            "P": dic_var.get("P_WHITE", False),
            "p": dic_var.get("P_BLACK", False),
            "N": dic_var.get("N_WHITE", False),
            "n": dic_var.get("N_BLACK", False),
            "B": dic_var.get("B_WHITE", False),
            "b": dic_var.get("B_BLACK", False),
            "R": dic_var.get("R_WHITE", False),
            "r": dic_var.get("R_BLACK", False),
            "Q": dic_var.get("Q_WHITE", False),
            "q": dic_var.get("Q_BLACK", False),
            "K": dic_var.get("K_WHITE", False),
            "k": dic_var.get("K_BLACK", False),
        }
        self.update_ghost()
        if self.space_number:
            self._update_space_control()

    def update_ghost(self):
        if self.ghost_level > 0.0:
            if self.board.create_piece != self.create_piece:
                self.board_create_piece = self.board.create_piece
                self.board.create_piece = self.create_piece
        else:
            if hasattr(self, "board_create_piece"):
                self.board.create_piece = self.board_create_piece

        for pz, pz_sc, x in self.board.li_pieces:
            if self.ghost_level > 0.0 and self.dic_ghost_pieces.get(pz, False):
                pz_sc.setOpacity(1.0 - self.ghost_level)
            else:
                pz_sc.setOpacity(1.0)

    def create_piece(self, cpieza, pos_a1_h8):
        pz_sc = self.board_create_piece(cpieza, pos_a1_h8)
        if self.ghost_level > 0.0:
            if self.dic_ghost_pieces.get(cpieza, False):
                pz_sc.setOpacity(1.0 - self.ghost_level)
        return pz_sc

    def sleep_refresh(self, seconds):
        ini_time = time.time()
        while (time.time() - ini_time) < seconds:
            QTUtils.refresh_gui()
            if self.stopped:
                return False
            time.sleep(0.01)
        return True

    def show_information(self):
        if self.with_pgn:
            if self.previous_visible_information:
                self.main_window.active_information_pgn(True)
            if self.previous_visible_capturas:
                self.main_window.siCapturas = True
            self.main_window.base.show_replay()
        else:
            if self.previous_visible_information:
                self.main_window.active_information_pgn(False)
            if self.previous_visible_capturas:
                self.main_window.siCapturas = False
            self.main_window.base.hide_replay()
        QTUtils.refresh_gui()

    def show_current(self):
        if self.stopped or self.current_position >= len(self.li_moves):
            return

        move = self.li_moves[self.current_position]
        # self.board.set_position(move.position_before)
        if self.current_position > self.initial_position:
            if not self.sleep_refresh(self.seconds / self.rapidez):
                return
        li_movs = [("b", move.to_sq), ("m", move.from_sq, move.to_sq)]
        if move.position.li_extras:
            li_movs.extend(move.position.li_extras)
        self.move_the_pieces(li_movs)

        QtCore.QTimer.singleShot(10, self.skip)

    def move_the_pieces(self, li_movs):
        if self.stopped:
            return
        cpu = self.procesador.cpu
        cpu.reset()
        secs = None

        move = self.li_moves[self.current_position]
        num = self.current_position
        if self.starts_with_black:
            num += 1
        row = int(num / 2)
        self.main_window.end_think_analysis_bar()
        self.main_window.place_on_pgn_table(row, move.position_before.is_white)
        self.main_window.base.pgn_refresh()

        # primero los movimientos
        for movim in li_movs:
            if movim[0] == "m":
                from_sq, to_sq = movim[1], movim[2]
                if secs is None:
                    dc = ord(from_sq[0]) - ord(to_sq[0])
                    df = int(from_sq[1]) - int(to_sq[1])
                    # Maxima distancia = 9.9 ( 9,89... sqrt(7**2+7**2)) = 4 seconds
                    dist = (dc ** 2 + df ** 2) ** 0.5
                    rp = self.rapidez if self.rapidez > 1.0 else 1.0
                    secs = 4.0 * dist / (9.9 * rp)
                cpu.move_piece(from_sq, to_sq, secs)
        # return
        if secs is None:
            secs = 1.0

        # segundo los borrados
        for movim in li_movs:
            if movim[0] == "b":
                cpu.remove_piece_in_seconds(movim[1], secs)

        # tercero los cambios
        for movim in li_movs:
            if movim[0] == "c":
                cpu.change_piece(movim[1], movim[2], is_exclusive=True)

        cpu.run_linear()
        if self.stopped:
            return

        wait_seconds = 0.0
        if self.if_custom_sounds:
            wait_seconds = Code.runSound.play_list_seconds(move.sounds_list())
        if wait_seconds == 0.0 and self.if_beep:
            Code.runSound.play_beep()

        self.manager.put_arrow_sc(move.from_sq, move.to_sq)

        self.board.set_position(move.position)

        # Actualiza overlay de espacio controlado si está activo (sin temblor)
        if self.space_number is not None:
            self._update_space_control()

        self.manager.put_view()
        if wait_seconds:
            self.sleep_refresh(wait_seconds / 1000 + 0.2)

    def show_pause(self, si_pausa, si_continue):
        self.main_window.show_option_toolbar(TB_PAUSE_REPLAY, si_pausa)
        self.main_window.show_option_toolbar(TB_CONTINUE_REPLAY, si_continue)

    def process_toolbar(self, key):
        if key == TB_END_REPLAY:
            self.finalize()
        elif key == TB_SLOW_REPLAY:
            self.lento()
        elif key == TB_PAUSE_REPLAY:
            self.pausa()
        elif key == TB_CONTINUE_REPLAY:
            self.seguir()
        elif key == TB_FAST_REPLAY:
            self.rapido()
        elif key == TB_REPEAT_REPLAY:
            self.repetir()
        elif key == TB_PGN_REPLAY:
            self.with_pgn = not self.with_pgn
            self.show_information()

        elif key == TB_SETTINGS:
            self.pausa()
            if self.params.edit(self.main_window, False):
                self.relee_params(self.params.dic_data)
                self.show_information()
        elif key == TB_SPACE:
            self.space()

    def space(self):
        menu = QTDialogs.LCMenu(self.main_window)
        menu.opcion("both", _("Both"), Iconos.SpaceBoth())
        menu.opcion("white", _("White"), Iconos.SpaceWhite())
        menu.opcion("black", _("Black"), Iconos.SpaceBlack())
        resp = menu.lanza()
        if resp == "both":
            self._do_pressed_number(True, 3)
        elif resp == "white":
            self._do_pressed_number(True, 2)
        elif resp == "black":
            self._do_pressed_number(True, 7)

    def _do_pressed_number(self, si_activar, number):
        """Handler para teclas 2/7 en modo replay: toggle del overlay de espacio controlado."""
        if number not in (2, 7, 3, 6):
            return
        if not si_activar:
            return  # Solo reaccionar al press (no al release)
        if self.space_number == number:
            # Mismo número: apagar
            self.space_number = None
            if self.space_layer:
                self.space_layer.hide()
        else:
            # Nuevo número: encender/cambiar
            self.space_number = number
            self._update_space_control()

    def _update_space_control(self):
        """Crea el overlay si no existe y actualiza los colores con la posición actual."""
        if self.space_number is None:
            return
        fen = self.board.fen_active()
        if self.space_layer is None:
            self.space_layer = SpaceControlLayer(self.board)
        self.space_layer.update(fen, self.space_number)

    def finalize(self):
        # Limpiar overlay de espacio controlado
        if self.space_layer is not None:
            self.space_layer.remove()
            self.space_layer = None
        self.space_number = None
        self.board.do_pressed_number = self._prev_do_pressed_number

        if self.ghost_level > 0.0:
            for pz, pz_sc, x in self.board.li_pieces:
                pz_sc.setOpacity(1.0)
            self.board.create_piece = self.board_create_piece
        self.stopped = True
        self.main_window.pon_toolbar(self.antAcciones)
        self.manager.set_routine_default(None)
        self.manager.xpelicula = None
        if self.previous_visible_capturas:
            self.main_window.siCapturas = True
        if not self.with_pgn:
            self.with_pgn = True
            self.show_information()

    def lento(self):
        self.rapidez /= 1.2

    def rapido(self):
        self.rapidez *= 1.2

    def pausa(self):
        self.stopped = True
        self.show_pause(False, True)

    def seguir(self):
        num_moves, self.current_position, filaInicial, is_white = self.manager.current_move()
        self.current_position += 1
        self.stopped = False
        self.show_pause(True, False)
        self.show_current()

    def repetir(self):
        self.current_position = 0 if self.if_start else self.jugInicial
        self.show_pause(True, False)
        if self.stopped:
            self.stopped = False
            self.show_current()

    def skip(self):
        if self.stopped:
            return
        self.current_position += 1
        if self.current_position >= self.num_moves:
            if self.next_game:
                if self.next_game():
                    self.jugInicial = 0
                    self.current_position = 0
                    self.initial_position = 0
                    self.if_start = True
                    self.antAcciones = self.main_window.get_toolbar()
                    self.main_window.pon_toolbar(self.li_acciones, separator=False)
                    self.li_moves = self.manager.game.li_moves
                    self.num_moves = len(self.li_moves)
                    if self.seconds_before > 0.0:
                        move = self.li_moves[self.current_position]
                        self.board.set_position(move.position_before)
                        if not self.sleep_refresh(self.seconds_before):
                            return
                    self.show_current()
                    return
            self.finalize()
        else:
            self.show_current()
