from Code.Base.Constantes import (
    BLINDFOLD_ALL,
    BLINDFOLD_BLACK,
    BLINDFOLD_CONFIG,
    BLINDFOLD_WHITE,
)
from Code.QT import Piezas


class BoardBlindfold:
    def __init__(self, board):
        self._board = board
        self._blind_sides = None

    def blind_sides(self):
        return self._blind_sides

    def show_pieces(self, is_white, is_black):
        if is_white and is_black:
            self._blind_sides = None
        elif is_white:
            self._blind_sides = BLINDFOLD_BLACK
        elif is_black:
            self._blind_sides = BLINDFOLD_WHITE
        else:
            self._blind_sides = BLINDFOLD_ALL
        self.blindfold_reset()

    def blindfold_change(self):
        self._blind_sides = None if self._blind_sides else BLINDFOLD_CONFIG
        self.blindfold_reset()

    def blindfold_reset(self):
        board = self._board
        ap, apc = board.pieces_are_active, board.side_pieces_active
        is_arrow = board.arrow_sc is not None

        is_white_bottom = board.is_white_bottom

        atajos_raton = board.atajos_raton

        board.draw_window()
        if not is_white_bottom:
            board.try_to_rotate_the_board(None)

        if ap:
            board.activate_side(apc)
            board.set_side_indicator(apc)

        if is_arrow:
            board.reset_arrow_sc()

        board.atajos_raton = atajos_raton
        board.init_kb_buffer()

    def blindfold_remove(self):
        if self._blind_sides:
            self._blind_sides = None
            self.blindfold_reset()

    def blindfold_config(self):
        board = self._board
        nom_pieces_ori = board.config_board.nomPiezas()
        w = Piezas.WBlindfold(board, nom_pieces_ori)
        if w.exec():
            self._blind_sides = BLINDFOLD_CONFIG
            self.blindfold_reset()
