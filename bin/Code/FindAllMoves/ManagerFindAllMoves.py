import ast
import os
import random
import time
from typing import Any, List, Optional, Tuple

import FasterCode
from PySide6.QtCore import Qt

import Code
from Code import Util
from Code.Base import Position
from Code.Base.Constantes import (
    ST_ENDGAME,
    ST_PLAYING,
    TB_CLOSE,
    TB_CONFIG,
    TB_NEXT,
    TB_PLAY,
    TB_RESIGN,
)
from Code.CompetitionWithTutor import WCompetitionWithTutor
from Code.ManagerBase import Manager
from Code.QT import Iconos, QTDialogs, QTMessages, QTUtils
from Code.Translations import TrListas


class ControlFindAllMoves:
    def __init__(self, manager: "ManagerFindAllMoves", is_the_player: bool):
        with open(Code.path_resource("IntFiles", "findallmoves.dkv"), "r", encoding="utf-8") as f:
            self.db: List[List[str]] = ast.literal_eval(f.read())

        mas = "P" if is_the_player else "R"
        self.fichPuntos = f"{manager.configuration.paths.folder_results}/score60{mas}.dkv"

        if os.path.isfile(self.fichPuntos):
            self.liPuntos: List[List[Any]] = Util.restore_pickle(self.fichPuntos)
        else:
            self.liPuntos = [[0, 0] for _ in range(len(self.db))]

    def guardar(self) -> None:
        Util.save_pickle(self.fichPuntos, self.liPuntos)

    def num_rows(self) -> int:
        return len(self.db)

    def first_no_solved(self) -> int:
        nd = self.num_rows()
        for i in range(nd):
            if self.liPuntos[i][0] == 0:
                return i
        return nd - 1

    def pos_with_error(self) -> int:
        nd = self.num_rows()
        for i in range(nd):
            if self.liPuntos[i][1] > 0:
                return i
        return 999

    @staticmethod
    def analysis(_row: int, _key: str) -> str:  # compatibilidad
        return ""

    @staticmethod
    def only_move(_row: int, _key: str) -> None:  # compatibilidad
        return None

    @staticmethod
    def goto_row_iswhite(_row: int, _is_white: bool) -> bool:  # compatibilidad
        return False

    def dato(self, row: int, key: str) -> str:
        if key == "LEVEL":
            return str(row + 1)
        vtime, errors = self.liPuntos[row]
        if key == "TIME":
            if vtime == 0:
                return "-"
            tiempo = vtime / 100.0
            tm = tiempo / (row + 1)
            return f'{tiempo:0.02f}" / {tm:0.02f}"'
        else:
            return "-" if vtime == 0 else str(errors)

    def dame(self, number: int) -> str:
        li = self.db[number]
        pos = random.randint(0, len(li) - 1)
        return f"{li[pos]} 0 1"

    def message_result(self, number: int, vtime: int, errors: int) -> Tuple[str, bool]:
        tm = vtime / (number + 1)

        if self.liPuntos[number][0] > 0:
            t0, e0 = self.liPuntos[number]
            si_record = False
            if e0 > errors:
                si_record = True
            elif e0 == errors:
                si_record = vtime < t0
        else:
            si_record = True

        mensaje = (
            f"<b>{_('Level')}</b> : {number + 1}<br>"
            f"<b>{_('Errors')}</b> : {errors}<br>"
            f"<b>{_('Time')}:</b> {vtime / 100.0:.02f}<br>"
            f"<b>{_('Average')}: </b>{tm / 100.0:.02f}<br>"
        )
        if si_record:
            mensaje += f"<br><br><b>{_('New record!')}</b><br>"
            self.liPuntos[number] = [vtime, errors]
            self.guardar()

        return mensaje, si_record

    def remove_all(self) -> None:
        Util.remove_file(self.fichPuntos)
        self.liPuntos = [[0, 0]] * len(self.db)

    def average_time(self) -> float:
        num = 0
        tm = 0.0
        for row in range(self.num_rows()):
            vtime, errors = self.liPuntos[row]
            if vtime > 0:
                num += row + 1
                tm += vtime
        return tm / (num * 100) if num > 0 else 0.0


class ManagerFindAllMoves(Manager.Manager):
    is_the_player: bool
    last_a1h8: Optional[str] = None
    pgn: ControlFindAllMoves
    number: Optional[int]
    is_human_side_white: bool
    is_white: bool
    li_movs: list
    order_pz: str
    errors: int
    ini_time: float
    level: int

    def start(self, is_the_player: bool) -> None:

        self.is_the_player = is_the_player

        self.pgn = ControlFindAllMoves(self, is_the_player)

        self.main_window.columnas60(True, cBlack=f"{_('Time')} / {_('Avg || Abrev. of Average')}")

        self.end_game()

        self.main_window.active_game(True, False)
        self.remove_hints(True, False)
        self.main_window.set_label1(None)
        self.main_window.set_label2(None)
        self.show_side_indicator(False)
        self.put_pieces_bottom(True)
        self.set_dispatcher(self.player_has_moved)
        self.pgn_refresh(True)
        self.main_window.base.pgn.gotop()
        self.main_window.board.can_be_rotated_the_board = False

        self.board.do_pressed_number = None
        self.remove_info()
        self.pon_rotulotm()
        self.refresh()

    def num_rows(self) -> int:
        return self.pgn.num_rows()

    def run_action(self, key: str) -> None:

        if key == TB_CLOSE:
            self.fin60()

        elif key == TB_PLAY:
            self.play()

        elif key == TB_RESIGN:
            self.end_game()

        elif key == TB_CONFIG:
            self.config()

        elif key == TB_NEXT:
            self.next()

        else:
            self.routine_default(key)

    def config(self) -> None:
        menu = QTDialogs.LCMenu(self.main_window)
        menu.opcion("remove", _("Remove all results of all levels"), Iconos.Cancelar())

        resp = menu.lanza()
        if resp:
            if resp == "remove":
                if QTMessages.pregunta(
                        self.main_window,
                        _("Are you sure you want to delete all results of all levels and start again from scratch?"),
                ):
                    self.pgn.remove_all()
                    self.pgn_refresh(True)
                    self.main_window.base.pgn.gotop()
                    self.pon_rotulotm()

    def fin60(self) -> None:
        self.main_window.board.can_be_rotated_the_board = True
        self.board.remove_arrows()
        self.main_window.columnas60(False)
        self.procesador.start()

    def end_game(self) -> None:
        self.main_window.pon_toolbar((TB_CLOSE, TB_PLAY, TB_CONFIG, TB_NEXT))
        self.disable_all()
        self.state = ST_ENDGAME
        self.pon_rotulotm()

    def next(self) -> None:
        if self.state == ST_PLAYING:
            return
        pos = self.pgn.first_no_solved()
        pos_with_error = self.pgn.pos_with_error()
        if pos_with_error <= pos:
            pos = pos_with_error
        self.play(pos)

    def control_teclado(self, nkey) -> None:
        if nkey in (Qt.Key.Key_Plus, Qt.Key.Key_PageDown):
            self.next()

    def play(self, number: Optional[int] = None) -> None:
        if self.state == ST_PLAYING:
            self.state = ST_ENDGAME
            self.disable_all()

        if number is None:

            pos = self.pgn.first_no_solved() + 1
            pos_with_error = self.pgn.pos_with_error() + 1
            if pos_with_error <= pos:
                pos = pos_with_error

            mens = _('Movements must be indicated in the following order: King, Queen, Rook, Bishop, Knight and Pawn.')
            number = WCompetitionWithTutor.edit_training_position(
                self.main_window,
                _("Find all moves"),
                pos,
                etiqueta=_("Level"),
                pos=pos,
                mensAdicional=f"<b><red>{mens}</red></b>",
            )
            if number is None:
                return
            number -= 1

        fen = self.pgn.dame(number)
        self.number = number
        cp = Position.Position()
        cp.read_fen(fen)
        self.is_human_side_white = self.is_white = cp.is_white
        if self.is_white:
            si_p = self.is_the_player
        else:
            si_p = not self.is_the_player
        self.put_pieces_bottom(si_p)
        self.set_position(cp)
        self.refresh()

        FasterCode.set_fen(fen)
        self.li_movs = FasterCode.get_exmoves()
        self.last_a1h8 = None

        # Creamos una variable para controlar que se mueven en orden
        d = {}
        fchs = "KQRBNP"
        if not cp.is_white:
            fchs = fchs.lower()
        for k in fchs:
            d[k] = ""
        for mov in self.li_movs:
            mov.is_selected = False
            pz = mov.piece()
            d[pz] += pz
        self.order_pz = ""
        for k in fchs:
            self.order_pz += d[k]

        self.errors = 0
        self.ini_time = time.time()
        self.state = ST_PLAYING

        self.board.remove_arrows()

        mens = ""
        if cp.castles:
            if ("K" if cp.is_white else "k") in cp.castles:
                mens = "O-O"
            if ("Q" if cp.is_white else "q") in cp.castles:
                if mens:
                    mens += " + "
                mens += "O-O-O"
            if mens:
                mens = f"{_('Castling moves possible')}: {mens}"
        if cp.en_passant != "-":
            mens += f" {_('En passant')}: {cp.en_passant}"

        self.main_window.set_label1(mens)

        self.level = number
        self.is_white = cp.is_white
        self.pon_rotulo2n()

        self.main_window.pon_toolbar((TB_RESIGN,))
        self.main_window.base.pgn.goto(number, 0)
        self.activate_side(self.is_white)

    def pon_rotulo2n(self) -> None:
        self.main_window.set_label2(
            f"<h3>{_('White') if self.is_white else _('Black')}"
            f" - {TrListas.level(self.level + 1)}"
            f" - {_('Errors')} : {self.errors}</h3>"
        )

    def pon_rotulotm(self) -> None:
        self.main_window.set_label1("")
        tm = self.pgn.average_time()
        if tm == 0.0:
            txt = ""
        else:
            txt = f"<h3>{_('Time')}/{_('Move')}: {tm:0.02f}</h3>"
        self.main_window.set_label2(txt)
        self.refresh()

    def final_x(self) -> bool:
        self.procesador.start()
        return False

    def player_has_moved(self, from_sq: str, to_sq: str, _promotion: str = "") -> bool:
        a1h8 = from_sq + to_sq
        if self.last_a1h8 == a1h8:
            return False
        self.last_a1h8 = a1h8
        if from_sq == to_sq:
            return False
        QTUtils.refresh_gui()
        for mov in self.li_movs:
            if (mov.xfrom() + mov.xto()) == a1h8:
                if not mov.is_selected:
                    if mov.piece() == self.order_pz[0]:
                        # self.board.creaFlechaMulti(a1h8, False, opacity=0.4)
                        mov.is_selected = True
                        self.order_pz = self.order_pz[1:]
                        if len(self.order_pz) == 0:
                            self.put_result()
                    else:
                        break
                self.board.put_arrow_scvar([(mov.xfrom(), mov.xto()) for mov in self.li_movs if mov.is_selected])
                self.reset_shortcuts_mouse()
                return False
        self.errors += 1
        self.pon_rotulo2n()
        self.reset_shortcuts_mouse()

        return False

    def put_result(self) -> None:
        vtime = int((time.time() - self.ini_time) * 100.0)
        self.end_game()

        mensaje, si_record = self.pgn.message_result(self.number, vtime, self.errors)
        self.pon_rotulotm()

        if self.number == 59 and si_record and self.errors == 0:
            mens = f'<b><span style="color:green">{_("Congratulations, goal achieved")}</span></b>'
            QTMessages.message(self.main_window, mens)
        else:
            QTMessages.temporary_message(
                self.main_window,
                mensaje,
                10,
                background="#ffa13b" if si_record else None,
                with_image=False
            )

    def analize_position(self, row: int, key: str) -> None:
        if self.state == ST_PLAYING:
            self.end_game()
            return
        if row <= self.pgn.first_no_solved():
            pos_with_error = self.pgn.pos_with_error()
            if pos_with_error < row:
                QTMessages.message(
                    self.main_window,
                    _("To be able to play at this level, the previous levels must be solved without errors."),
                )
                return
            self.play(row)

    def move_according_key(self, tipo: str) -> None:
        row, col = self.main_window.pgnPosActual()
        if tipo == "+":
            if row > 0:
                row -= 1
        elif tipo == "-":
            if row < (self.pgn.num_rows() - 1):
                row += 1
        elif tipo == "p":
            row = 0
        elif tipo == "f":
            row = self.pgn.num_rows() - 1

        self.main_window.base.pgn.goto(row, 0)

    def information_pgn(self) -> None:
        pass  # Para anular el efecto del boton derecho
