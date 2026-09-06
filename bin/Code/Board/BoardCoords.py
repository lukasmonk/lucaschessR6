"""Centralized coordinate conversion service for the chess board.

Provides conversions between:
  - Algebraic notation (a1-h8)
  - Row/col indices (1-8)
  - Pixel coordinates

All methods are pure functions that depend only on the board geometry
parameters passed at construction time.
"""


class BoardCoords:
    def __init__(self, width_square, tam_frontera, margin_center, margin_pieces, is_white_bottom):
        self.width_square = width_square
        self.tam_frontera = tam_frontera
        self.margin_center = margin_center
        self.margin_pieces = margin_pieces
        self.is_white_bottom = is_white_bottom

    def _origin_offset(self):
        return self.margin_center + self.tam_frontera / 2 + self.margin_pieces

    def row_to_y(self, row):
        factor = (8 - row) if self.is_white_bottom else (row - 1)
        return factor * self.width_square + self._origin_offset()

    def col_to_x(self, column):
        factor = (column - 1) if self.is_white_bottom else (8 - column)
        return factor * self.width_square + self._origin_offset()

    def y_to_row(self, y):
        pos = y - self._origin_offset()
        pos //= self.width_square
        return int(8 - pos) if self.is_white_bottom else int(pos + 1)

    def x_to_col(self, x):
        pos = x - self._origin_offset()
        pos //= self.width_square
        return int(pos + 1) if self.is_white_bottom else int(8 - pos)

    def algebraic_to_pixel(self, sq):
        col = ord(sq[0]) - 96
        row = int(sq[1])
        return self.col_to_x(col), self.row_to_y(row)

    def pixel_to_algebraic(self, x, y):
        minimo = self.margin_center
        maximo = self.margin_center + self.width_square * 8
        if not (minimo < x < maximo and minimo < y < maximo):
            return None
        col = 1 + int(float(x - self.margin_center) / self.width_square)
        row = 1 + int(float(y - self.margin_center) / self.width_square)
        if self.is_white_bottom:
            row = 9 - row
        else:
            col = 9 - col
        if 1 <= row <= 8 and 1 <= col <= 8:
            return chr(96 + col) + str(row)
        return None

    def rowcol_to_pixel(self, row, col):
        return self.col_to_x(col), self.row_to_y(row)

    def pixel_to_rowcol(self, x, y):
        minimo = self.margin_center
        maximo = self.margin_center + self.width_square * 8
        if not (minimo < x < maximo and minimo < y < maximo):
            return None, None
        col = 1 + int(float(x - self.margin_center) / self.width_square)
        row = 1 + int(float(y - self.margin_center) / self.width_square)
        if self.is_white_bottom:
            row = 9 - row
        else:
            col = 9 - col
        if 1 <= row <= 8 and 1 <= col <= 8:
            return row, col
        return None, None

    def a1h8_to_rowcols(self, a1h8):
        if len(a1h8) < 4:
            return 0, 0, 0, 0
        df = int(a1h8[1])
        dc = ord(a1h8[0]) - 96
        hf = int(a1h8[3])
        hc = ord(a1h8[2]) - 96
        if self.is_white_bottom:
            df = 9 - df
            hf = 9 - hf
        else:
            dc = 9 - dc
            hc = 9 - hc
        return df, dc, hf, hc

    def rowcols_to_a1h8(self, df, dc, hf, hc):
        if self.is_white_bottom:
            df = 9 - df
            hf = 9 - hf
        else:
            dc = 9 - dc
            hc = 9 - hc
        return chr(dc + 96) + str(df) + chr(hc + 96) + str(hf)

    @staticmethod
    def num2alg(row, column):
        return chr(96 + column) + str(row)

    def alg2num(self, a1):
        return self.algebraic_to_pixel(a1)
