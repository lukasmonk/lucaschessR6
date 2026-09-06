import Code
from Code.Base import Position
from Code.Board import Board
from Code.QT import Colocacion, Iconos, LCDialog


class WOneMove(LCDialog.LCDialog):
    def __init__(self, wowner, position: Position.Position):
        titulo = _("Change opponent move")
        icono = Iconos.TOLchange()
        extparam = "change_opponent_move"
        LCDialog.LCDialog.__init__(self, wowner, titulo, icono, extparam)

        self.position = position

        self.result = None

        config_board = Code.configuration.config_board("CHANGEMOVE", 48)
        self.board = Board.Board(self, config_board)
        self.board.draw_window()
        self.board.set_side_bottom(not position.is_white)
        self.board.set_position(position)
        self.board.set_dispatcher(self.dispatcher)
        self.board.activate_side(self.position.is_white)

        ly = Colocacion.H().control(self.board).relleno()
        ly.margen(3)

        self.setLayout(ly)

        self.restore_video()

    def finalize(self):
        self.save_video()
        self.accept()

    def closeEvent(self, event):
        self.save_video()

    def dispatcher(self, from_sq: str, to_sq: str):
        promotion = ""
        if self.position.pawn_can_promote(from_sq, to_sq):
            promotion = self.board.pawn_promoting(self.position.is_white)
            if promotion is None:
                return
        self.board.move_piece(from_sq, to_sq)
        move = from_sq + to_sq + promotion
        li_exmoves = self.position.get_exmoves()
        for mj in li_exmoves:
            if mj.move() == move:
                self.result = from_sq, to_sq, promotion
                self.finalize()
                return
        self.board.set_position(self.position)
        self.board.activate_side(self.position.is_white)
