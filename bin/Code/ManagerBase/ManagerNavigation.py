from Code.Base import Move
from Code.Base.Constantes import (
    GO_BACK,
    GO_BACK2,
    GO_END,
    GO_FORWARD,
    GO_FORWARD2,
    GO_START,
)


class ManagerNavigation:
    def __init__(self, manager):
        self.manager = manager
        self.main_window = manager.main_window
        self.game = manager.game

    def mueve_number(self, tipo):
        game = self.manager.game
        row, column = self.main_window.pgn_pos_actual()

        col = 0

        starts_with_black = game.starts_with_black
        lj = len(game)
        if starts_with_black:
            lj += 1
        ult_fila = (lj - 1) // 2

        if tipo == GO_BACK:
            row -= 1
            if row < 0:
                self.goto_firstposition()
                return
            col = 1
        elif tipo == GO_BACK2:
            if row == 0:
                return
            row -= 1
        elif tipo == GO_FORWARD:
            if (row == 0 and col == 0) and game.starts_with_black:
                move: Move.Move = self.manager.game.move(0)
                self.manager.set_position(move.position)
                self.main_window.base.pgn.goto(0, 2)
                self.manager.board.put_arrow_sc(move.from_sq, move.to_sq)
                self.manager.refresh_pgn()
                self.manager.put_view()
                return
            col = 1
        elif tipo == GO_FORWARD2:
            row += 1
        elif tipo == GO_START:
            self.goto_firstposition()
            return
        elif tipo == GO_END:
            row = ult_fila

        if row > ult_fila:
            return

        move: Move.Move = self.manager.game.move(row * 2 + col)
        self.manager.set_position(move.position_before)
        self.main_window.base.pgn.goto(row, col)
        self.manager.refresh_pgn()  # No se puede usar pgn_refresh, ya que se usa con gobottom en otros lados
        self.manager.put_view()
        if row > 0 or col > 0:
            move: Move.Move = self.manager.game.move(row * 2 + col - 1)
            self.manager.board.put_arrow_sc(move.from_sq, move.to_sq)
            self.main_window.place_on_pgn_table(row, col)
            self.pgn_move(row, move.is_white())

    def move_according_key(self, tipo):
        game = self.manager.game
        if not len(game):
            return None
        row, column = self.main_window.pgn_pos_actual()

        starts_with_black = game.starts_with_black

        key = column.key
        if key == "NUMBER":
            return self.mueve_number(tipo)
        else:
            is_white = key != "BLACK"

        lj = len(game)
        if starts_with_black:
            lj += 1
        ult_fila = (lj - 1) / 2
        si_ult_blancas = lj % 2 == 1

        if tipo == GO_BACK:
            if is_white:
                row -= 1
            is_white = not is_white
            pos = row * 2
            if not is_white:
                pos += 1
            if row < 0 or (row == 0 and pos == 0 and starts_with_black):
                self.goto_firstposition()
                return None
        elif tipo == GO_BACK2:
            row -= 1
        elif tipo == GO_FORWARD:
            if not is_white:
                row += 1
            is_white = not is_white
        elif tipo == GO_FORWARD2:
            row += 1
        elif tipo == GO_START:
            self.goto_firstposition()
            return None
        elif tipo == GO_END:
            row = ult_fila
            is_white = not game.last_position.is_white

        if row == ult_fila:
            if si_ult_blancas and not is_white:
                return None

        if row < 0 or row > ult_fila:
            self.manager.refresh()
            return None
        if row == 0 and is_white and starts_with_black:
            is_white = False

        self.main_window.place_on_pgn_table(row, is_white)
        self.pgn_move(row, is_white)

        return None

    def goto_firstposition(self):
        self.manager.set_position(self.manager.game.first_position)
        self.main_window.base.pgn.goto(0, 0)
        self.manager.refresh_pgn()  # No se puede usar pgn_refresh, ya que se usa con gobottom en otros lados
        self.manager.put_view()
        self.manager.board.set_last_position(self.manager.game.first_position)

    def pgn_move(self, row, is_white):
        self.manager.pgn.goto_row_iswhite(row, is_white)
        self.manager.put_view()

    def goto_pgn_base(self, row, column):
        if column == "NUMBER":
            if row <= 0:
                if self.manager.pgn.variations_mode:
                    self.manager.set_position(self.manager.game.first_position, "-1")
                    self.main_window.base.pgn.goto(0, 0)
                    self.manager.refresh_pgn()  # No se puede usar pgn_refresh,
                    self.manager.put_view()
                else:
                    self.goto_firstposition()
                return
            else:
                row -= 1
                is_white = False
        else:
            is_white = column == "WHITE"
        self.manager.pgn.goto_row_iswhite(row, is_white)
        self.manager.put_view()

    def goto_end(self):
        if len(self.manager.game):
            self.move_according_key(GO_END)
        else:
            self.manager.set_position(self.manager.game.first_position)
            self.manager.refresh_pgn()  # No se puede usar pgn_refresh,
        self.manager.put_view()

    def goto_current(self):
        num_moves, nj, row, is_white = self.current_move()
        self.pgn_move(row, is_white)

    def current_move(self):
        game = self.manager.game
        row, column = self.main_window.pgn_pos_actual()
        is_white = column.key != "BLACK"
        starts_with_black = game.starts_with_black

        num_moves = len(game)
        if num_moves == 0:
            return 0, -1, -1, game.first_position.is_white
        nj = row * 2
        if not is_white:
            nj += 1
        if starts_with_black:
            nj -= 1
        return num_moves, nj, row, is_white

    def current_move_number(self):
        game = self.manager.game
        row, column = self.main_window.pgn_pos_actual()
        if column.key == "WHITE":
            is_white = True
        elif column.key == "BLACK":
            is_white = False
        else:
            if row > 0:
                is_white = False
                row -= 1
            else:
                is_white = True
        # is_white = column.key != "BLACK"
        starts_with_black = game.starts_with_black

        num_moves = len(game)
        if num_moves == 0:
            return 0, -1, -1, game.first_position.is_white
        nj = row * 2
        if not is_white:
            nj += 1
        if starts_with_black:
            nj -= 1
        return num_moves, nj, row, is_white

    def in_end_of_line(self):
        num_moves, nj, row, is_white = self.current_move()
        return nj == num_moves - 1

    def get_movement(self, row, key):
        is_white = key != "BLACK"

        pos = row * 2
        if not is_white:
            pos += 1
        if self.manager.game.starts_with_black:
            pos -= 1
        tam_lj = len(self.manager.game)
        if tam_lj == 0:
            return None
        si_ultimo = (pos + 1) >= tam_lj

        move = self.manager.game.move(pos)
        return move, is_white, si_ultimo, tam_lj, pos
