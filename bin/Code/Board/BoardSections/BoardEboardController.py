import time

from PySide6 import QtCore
from PySide6.QtCore import Qt

import Code
from Code.Base import Position
from Code.Base.Constantes import BLACK, WHITE
from Code.QT import QTUtils


class BoardEboardController:
    def __init__(self, board):
        self._board = board

    def try_eboard_takeback(self, side):
        board = self._board
        if not board.allow_eboard:
            return 1
        if Code.eboard.fen_eboard == board.last_position.fen():
            return 0
        if board.allow_takeback():

            against_engine = board.main_window.manager.xrival is not None
            if against_engine and hasattr(board.main_window.manager, "play_against_engine"):
                against_engine = board.main_window.manager.play_against_engine

            if against_engine:
                allow_human_takeback = Code.eboard.allowHumanTB and board.last_position.is_white == side
            else:
                allow_human_takeback = True

            if allow_human_takeback:
                Code.eboard.allowHumanTB = False
                if board.main_window.manager.in_end_of_line():
                    board.exec_kb_buffer(Qt.Key.Key_Backspace, 0)
                else:
                    board.main_window.key_pressed("T", QtCore.Qt.Key.Key_Left)
                return 1

            Code.eboard.allowHumanTB = True
        return 0

    def dispatch_eboard(self, quien, a1h8):
        board = self._board
        if board.mensajero and board.pieces_are_active and board.allow_eboard:

            if quien == "whiteMove":
                Code.eboard.allowHumanTB = False
                if not board.side_pieces_active:
                    return 0
            elif quien == "blackMove":
                Code.eboard.allowHumanTB = False
                if board.side_pieces_active:
                    return 0
            elif quien == "scan":
                QTUtils.set_clipboard(a1h8)
                return 1

            elif quien == "whiteTakeBack":
                return board.try_eboard_takeback(WHITE)

            elif quien == "blackTakeBack":
                return board.try_eboard_takeback(BLACK)

            elif quien == "stableBoard":
                return 1

            elif quien in ("stopSetupWTM", "stopSetupBTM"):
                if hasattr(board.main_window, "manager") and hasattr(board.main_window.manager, "setup_board_live"):
                    side = "w" if "W" in quien else "b"
                    fen = f"{a1h8} {side} KQkq - 0 1"
                    position = Position.Position()
                    position.read_fen(fen)
                    position.legal()
                    board.main_window.manager.setup_board_live(side == "w", position)
                return 1

            else:
                return 1

            return 1 if board.mensajero(a1h8[:2], a1h8[2:4], a1h8[4:]) else 0
        return 1

    def disable_eboard_here(self):
        board = self._board
        board.allow_eboard = False

    def enable_eboard_here(self):
        board = self._board
        board.allow_eboard = True
        if Code.eboard and Code.eboard.driver:
            Code.eboard.set_position(board.last_position)

    def eboard_arrow(self, a1, h8, prom):
        board = self._board
        if Code.eboard and Code.eboard.driver and board.allow_eboard:
            position = board.last_position.copia()
            position.play(a1, h8, prom)
            Code.eboard.set_position(position)
            time.sleep(2.0)
            Code.eboard.set_position(board.last_position)
