from PySide6 import QtCore

from Code.Endings import LibChess
from Code.Kibitzers import WKibCommon
from Code.QT import Colocacion, Columnas, Controles, Delegados, Grid, Iconos


class WGaviota(WKibCommon.WKibCommon):
    def __init__(self, cpu):
        WKibCommon.WKibCommon.__init__(self, cpu, Iconos.Finales())

        self.t4 = LibChess.T4(cpu.configuration)

        o_columns = Columnas.ListaColumnas()
        delegado = Delegados.EtiquetaPOS(True, with_lines=False) if self.with_figurines else None
        o_columns.nueva("MOVE", _("Move"), 80, align_center=True, edicion=delegado)
        o_columns.nueva("DTM", "DTM", 60, align_center=True)
        self.grid = Grid.Grid(
            self,
            o_columns,
            dic_video=self.dic_video,
            complete_row_select=True,
            heigh_row=self.cpu.configuration.x_pgn_rowheight,
        )
        f = Controles.FontType(puntos=self.cpu.configuration.x_pgn_fontpoints)
        self.grid.set_font(f)

        li_acciones = (
            (_("Quit"), Iconos.Kibitzer_Close(), self.finalize),
            (_("Continue"), Iconos.Kibitzer_Play(), self.play),
            (_("Pause"), Iconos.Kibitzer_Pause(), self.pause),
            (_("Original position"), Iconos.HomeBlack(), self.home),
            (_("Takeback"), Iconos.Kibitzer_Back(), self.takeback),
            (_("Manual position"), Iconos.Kibitzer_Voyager(), self.set_position),
            (_("Show/hide board"), Iconos.Kibitzer_Board(), self.config_board),
            (
                f"{_('Enable')}: {_('window on top')}",
                Iconos.Pin(),
                self.window_top,
            ),
            (
                f"{_('Disable')}: {_('window on top')}",
                Iconos.Unpin(),
                self.window_bottom,
            ),
        )
        self.tb = Controles.TBrutina(self, li_acciones, with_text=False, icon_size=24)
        self.tb.set_action_visible(self.play, False)

        ly_h = Colocacion.H().control(self.board).control(self.grid)
        layout = Colocacion.V().control(self.tb).espacio(-8).otro(ly_h).margen(3)
        self.setLayout(layout)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.cpu.check_input)
        self.timer.start(500)

        if not self.show_board:
            self.board.hide()
        self.restore_video(self.dic_video)
        self.set_flags()

    def grid_doble_click(self, _grid, row, _obj_column):
        if 0 <= row < len(self.li_moves):
            if 0 <= row < len(self.li_moves):
                san, xdtm, orden, from_sq, to_sq, promotion = self.li_moves[row]
                mov = from_sq + to_sq + promotion
                self.game.read_pv(mov)
                self.reset()

    def grid_cambiado_registro(self, _grid, row, _obj_column):
        self.place_arrow(row)

    def place_arrow(self, row):
        if -1 < row < len(self.li_moves):
            san, xdtm, orden, from_sq, to_sq, promotion = self.li_moves[row]
            self.board.put_arrow_sc(from_sq, to_sq)

    def stop(self):
        self.siPlay = False

    def grid_num_datos(self, _grid):
        return len(self.li_moves)

    def grid_dato(self, _grid, row, obj_column):
        san, xdtm, orden, from_sq, to_sq, promotion = self.li_moves[row]

        key = obj_column.key
        if key == "MOVE":
            if self.with_figurines:
                is_white = self.game.last_position.is_white
                return san, is_white, None, None, None, None, False, True
            else:
                return san
        elif key == "DTM":
            return xdtm
        return None

    def whether_to_analyse(self) -> bool:
        is_white_to_move = self.game.last_position.is_white

        if not self.siPlay:
            return False

        if is_white_to_move and not self.is_white:
            return False

        if not is_white_to_move and not self.is_black:
            return False

        return True

    def finalizar(self):
        self.t4.close()
        self.save_video()

    def orden_game(self, game):
        self.game = game

        if self.siPlay:
            position = game.last_position
            self.is_white = position.is_white
            self.board.set_position(position)
            self.board.activate_side(self.is_white)
            self.li_moves = self.t4.list_fen(position.fen())
            self.grid.gotop()
            self.grid.refresh()
            self.place_arrow(0)

        self.test_tb_home()
