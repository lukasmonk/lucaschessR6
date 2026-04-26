import random
import time

from PySide6 import QtCore, QtGui, QtWidgets

import Code
from Code.Base import Position
from Code.Base.Constantes import BLACK, WHITE
from Code.Board import Board2
from Code.QT import Colocacion, Columnas, Controles, Delegados, Grid, Iconos, LCDialog, QTDialogs, QTMessages, \
    ScreenUtils
from Code.Memory import Memory


class WMemoryWork(LCDialog.LCDialog):
    fen_user: str
    fen_aim: str
    vtime: float
    initial_time: float
    squares: dict
    num_level: int

    def __init__(self, wowner, memory: Memory.Memory, li_fens, num_cat, num_level):

        titulo = _("Check your memory on a chessboard")
        icono = Iconos.Memoria()
        extparam = "memoriaA"
        LCDialog.LCDialog.__init__(self, wowner, titulo, icono, extparam)

        f = Controles.FontTypeNew(bold=True)

        self.memory: Memory.Memory = memory

        self.configuration = Code.configuration
        self.num_level = num_level
        self.num_category = num_cat
        self.categoria = self.memory.name_categoria(num_cat)
        self.num_pieces = num_level + 3
        self.seconds = (6 - num_cat) * self.num_pieces
        self.record = self.memory.dic_data[num_cat][num_level]
        self.repetitions = 0
        self.pending_time = 0
        self.cumulative_time = 0

        # Board
        config_board = self.configuration.config_board("MEMORIA", 48)

        self.listaFen = li_fens

        self.position = Position.Position()

        self.board = Board2.PosBoard(self, config_board)
        self.board.draw_window()
        self.board.set_dispatch_drop(self.dispatch_drop)
        self.board.baseCasillasSC.setAcceptDrops(True)
        self.ultimaPieza = "P"
        self.pieces = self.board.pieces
        self.ini_time_target = None

        width_pieces = max(16, int(32 * self.board.config_board.width_piece() / 48))
        self.listaPiezasW = QTDialogs.ListaPiezas(self, WHITE, self.board, width_pieces, margen=0)
        self.listaPiezasB = QTDialogs.ListaPiezas(self, BLACK, self.board, width_pieces, margen=0)

        # Ayuda
        lb_ayuda = Controles.LB(
            self,
            _(
                "<ul><li><b>Add piece</b> : Right mouse button on empty square</li><li><b>Copy piece</b> : Left mouse button on empty square</li><li><b>Move piece</b> : Drag and drop piece with left mouse button</li><li><b>Delete piece</b> : Right mouse button on occupied square</li></ul>"
            ),
        )
        lb_ayuda.set_wrap()
        ly = Colocacion.H().control(lb_ayuda)
        self.gbAyuda = Controles.GB(self, _("Help"), ly)

        # Rotulos informacion
        lb_categoria = Controles.LB(self, self.categoria)
        lb_categoria.setStyleSheet("border:1px solid lightgray;")
        lb_nivel = Controles.LB(self, _X(_("Level %1/%2"), str(self.num_level + 1), "25"))

        lb_record = Controles.LB(self, _X(_("Record %1 seconds"), f"{self.record:0.02f}") if self.record else "")
        lb_record.setVisible(bool(self.record))

        f_rot16 = Controles.FontTypeNew(point_size_delta=+7, bold=True)
        f_rot14 = Controles.FontType(point_size_delta=+5)
        for lb in (lb_nivel, lb_categoria, lb_record):
            lb.set_font(f_rot16 if lb == lb_categoria else f_rot14)
            lb.align_center()
            lb.set_wrap()
            # lb.relative_width(460)

        ly_rot_basicos = Colocacion.V().control(lb_categoria).control(lb_nivel).control(lb_record).margen(0)

        # Rotulo de vtime
        self.rotuloDispone = (
            Controles.LB(
                self,
                _X(
                    _("You have %1 seconds to remember the position of %2 pieces"),
                    str(self.seconds),
                    str(self.num_level + 3),
                ),
            )
            .set_wrap()
            .set_font(f)
            .align_center()
        )
        self.rotuloDispone1 = (
            Controles.LB(self, _("when you know you can press the Continue button"))
            .set_wrap()
            .set_font(f)
            .align_center()
        )
        ly = Colocacion.V().control(self.rotuloDispone).control(self.rotuloDispone1)
        self.gbTiempo = Controles.GB(self, "", ly)

        self.rotuloDispone1.hide()

        tbmenu = Controles.TBrutina(self)
        tbmenu.new(_("Close"), Iconos.MainMenu(), self.finalize)

        # Toolbar
        li_acciones = (
            (_("Start"), Iconos.Empezar(), self.start),
            (_("Continue"), Iconos.Pelicula_Seguir(), self.seguir),
            (_("Verify"), Iconos.Check(), self.comprobar),
            (_("Target"), Iconos.Verde32(), self.target),
            (_("Wrong"), Iconos.Rojo32(), self.wrong),
            (_("Repeat"), Iconos.Pelicula_Repetir(), self.repetir),
            (_("Resign"), Iconos.Abandonar(), self.abandonar),
            (_("New"), Iconos.New1(), self.new_try),
        )
        self.tb = tb = Controles.TBrutina(self)
        tb.set_actions(li_acciones)
        self.pon_toolbar(
            [
                self.start,
            ]
        )

        ly_tb = Colocacion.H().control(tbmenu).relleno().control(self.tb).margen(0)

        # Colocamos
        ly_up = Colocacion.H().relleno().control(self.listaPiezasB).relleno().margen(0)
        ly_down = Colocacion.H().relleno().control(self.listaPiezasW).relleno().margen(0)
        ly_t = Colocacion.V().otro(ly_up).control(self.board).otro(ly_down).margen(0)

        ly_i = Colocacion.V()
        ly_i.otro(ly_tb)
        ly_i.espacio(10)
        ly_i.otro(ly_rot_basicos)
        ly_i.relleno()
        ly_i.controlc(self.gbTiempo)
        ly_i.relleno(2)
        ly_i.control(self.gbAyuda)
        ly_i.margen(3)

        ly = Colocacion.H().otro(ly_i).otro(ly_t).relleno()
        ly.margen(3)

        self.setLayout(ly)

        self.timer = None

        for lb in (lb_ayuda, self.rotuloDispone1, self.rotuloDispone):
            lb.minimum_width(300)

        self.activate_extras(False)

        self.restore_video()

    def finalize(self):
        self.save_video()
        self.reject()

    def closeEvent(self, event):
        self.save_video()

    def mueve(self, from_sq, to_sq):
        if from_sq == to_sq:
            return
        if self.squares.get(to_sq):
            self.board.remove_piece(to_sq)
        self.squares[to_sq] = self.squares.get(from_sq)
        self.squares[from_sq] = None
        self.board.move_piece(from_sq, to_sq)

    def clean_square(self, from_sq):
        self.squares[from_sq] = None
        self.board.remove_piece(from_sq)

    def rightmouse_square(self, from_sq):
        menu = QtWidgets.QMenu(self)

        si_kw = False
        si_kb = False
        for p in self.squares.values():
            if p == "K":
                si_kw = True
            elif p == "k":
                si_kb = True

        li_options = []
        if not si_kw:
            li_options.append((_("King"), "K"))
        li_options.extend(
            [
                (_("Queen"), "Q"),
                (_("Rook"), "R"),
                (_("Bishop"), "B"),
                (_("Knight"), "N"),
                (_("Pawn"), "P"),
            ]
        )
        if not si_kb:
            li_options.append((_("King"), "k"))
        li_options.extend(
            [
                (_("Queen"), "q"),
                (_("Rook"), "r"),
                (_("Bishop"), "b"),
                (_("Knight"), "n"),
                (_("Pawn"), "p"),
            ]
        )

        for txt, pieza in li_options:
            icono = self.board.pieces.icono(pieza)

            accion = QtGui.QAction(icono, txt, menu)
            accion.key = pieza
            menu.addAction(accion)

        resp = menu.exec(QtGui.QCursor.pos())
        if resp:
            pieza = resp.key
            self.ensure_piece_at(from_sq, pieza)

    def repeat_piece(self, from_sq):
        self.squares[from_sq] = self.ultimaPieza
        pieza = self.board.create_piece(self.ultimaPieza, from_sq)
        pieza.activate(True)

    def ensure_piece_at(self, from_sq, pieza):
        antultimo = self.ultimaPieza
        self.ultimaPieza = pieza
        self.repeat_piece(from_sq)
        if pieza == "K":
            self.ultimaPieza = antultimo
        if pieza == "k":
            self.ultimaPieza = antultimo

    def dispatch_drop(self, from_sq, pieza):
        if self.squares.get(from_sq):
            self.clean_square(from_sq)
        self.ensure_piece_at(from_sq, pieza)

    def new_try(self):
        self.empezar(True)

    def start(self):
        self.empezar(True)

    def abandonar(self):
        self.reject()

    def pon_toolbar(self, li_acciones):
        self.tb.clear()
        for k in li_acciones:
            self.tb.dic_toolbar[k].setVisible(True)
            self.tb.dic_toolbar[k].setEnabled(True)
            self.tb.addAction(self.tb.dic_toolbar[k])

        self.tb.li_acciones = li_acciones
        self.tb.update()
        self.tb.remove_tooltips()

    def empezar(self, new=True):

        # Elegimos el fen de la lista
        if new:
            n_pos = random.randint(0, len(self.listaFen) - 1)
            self.fen_aim = self.listaFen[n_pos]
            del self.listaFen[n_pos]
            self.repetitions = 0
            self.cumulative_time = 0
        else:
            self.repetitions += 1
            if self.ini_time_target:
                self.cumulative_time += time.time() - self.ini_time_target

        self.ini_time_target = None
        self.position.read_fen(self.fen_aim)
        self.board.set_position(self.position)
        self.board.disable_all()
        self.squares = self.position.squares
        self.board.squares = self.squares

        # Quitamos empezar y ponemos seguir
        self.pon_toolbar(
            [
                self.seguir,
            ]
        )

        if new:
            self.pending_time = self.seconds
        else:
            self.pending_time = max(int(self.seconds // (self.repetitions + 1)), self.num_level + 3)

        self.rotuloDispone.set_text(
            _X(
                _("You have %1 seconds to remember the position of %2 pieces"),
                str(self.pending_time),
                str(self.num_level + 3),
            )
        )
        self.rotuloDispone1.set_text(_("when you know you can press the Continue button"))

        self.rotuloDispone.show()
        self.rotuloDispone1.show()
        self.gbTiempo.show()

        self.start_clock()

    def seguir(self):
        self.stop_clock()

        self.board.set_dispatcher(self.mueve)
        self.board.message_to_delete = self.clean_square
        self.board.create_message = self.rightmouse_square
        self.board.repeat_message = self.repeat_piece

        # Quitamos seguir y ponemos comprobar
        self.pon_toolbar(
            [
                self.comprobar,
            ]
        )

        self.rotuloDispone1.set_text(
            _X(
                _("When you've loaded the %1 pieces you can click the Check button"),
                str(self.num_level + 3),
            )
        )
        self.rotuloDispone.setVisible(False)

        self.initial_time = time.time()

        for k in self.squares:
            self.squares[k] = None
        self.board.set_position(self.position)

        self.activate_extras(True)

        self.rotuloDispone1.show()

    def activate_extras(self, si):
        self.gbAyuda.setVisible(si)
        self.listaPiezasW.setEnabled(si)
        self.listaPiezasB.setEnabled(si)

    def show_cursor(self):
        cursor = self.pieces.cursor(self.ultimaPieza)
        for item in self.board.escena.items():
            item.setCursor(cursor)
        self.board.setCursor(cursor)

    def comprobar(self):
        self.vtime = time.time() - self.initial_time
        self.cumulative_time += self.vtime

        fen_nuevo = self.position.fen()
        fen_nuevo = fen_nuevo[: fen_nuevo.index(" ")]
        fen_comprobar = self.fen_aim
        fen_comprobar = fen_comprobar[: fen_comprobar.index(" ")]

        if fen_comprobar == fen_nuevo:
            mens = _X(_("Right, it took %1 seconds."), f"{self.cumulative_time: 0.02f}")
            if self.cumulative_time < self.record or self.record == 0:
                mens += f"<br>{_('New record!')}"
            QTMessages.message_bold(self, mens)
            self.memory.save_category(self.num_category, self.num_level, self.cumulative_time)
            self.accept()
            return

        QTMessages.message_bold(self, _("The position is incorrect."))

        self.fen_user = self.position.fen()

        self.board.set_dispatcher(None)
        self.board.message_to_delete = None
        self.board.create_message = None
        self.board.repeat_message = None
        self.board.disable_all()

        self.gbTiempo.hide()

        self.activate_extras(False)

        # Quitamos comprobar y ponemos el resto
        li = [self.repetir, self.target, self.wrong]
        if len(self.listaFen):
            li.append(self.new_try)

        self.pon_toolbar(li)

    def target(self):
        self.ini_time_target = time.time()
        self.position.read_fen(self.fen_aim)
        self.board.set_position(self.position)
        self.board.disable_all()
        # self.quita_repetir()

    def wrong(self):
        if self.ini_time_target:
            self.cumulative_time += time.time() - self.ini_time_target
            self.ini_time_target = None
        self.position.read_fen(self.fen_user)
        self.board.set_position(self.position)
        self.board.disable_all()
        # self.quita_repetir()

    def repetir(self):
        self.rotuloDispone.set_text(
            _X(
                _("You have %1 seconds to remember the position of %2 pieces"),
                str(self.seconds),
                str(self.num_level + 3),
            )
        )
        self.rotuloDispone.show()
        self.rotuloDispone1.hide()
        self.gbTiempo.show()

        self.empezar(False)

    def reloj(self):
        self.pending_time -= 1

        self.rotuloDispone.set_text(
            _X(
                _("You have %1 seconds to remember the position of %2 pieces"),
                str(self.pending_time),
                str(self.num_level + 3),
            )
        )
        if self.pending_time == 0:
            self.seguir()

    def start_clock(self):
        if self.timer is not None:
            self.timer.stop()
            del self.timer

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.reloj)
        self.timer.start(1000)

    def stop_clock(self):
        if self.timer is not None:
            self.timer.stop()
            del self.timer
            self.timer = None


class WMemoryMain(LCDialog.LCDialog):
    def __init__(self, w_parent):
        title = f'{_("Check your memory on a chessboard")}'
        super(WMemoryMain, self).__init__(w_parent, title, Iconos.Memoria(), "memory_resultsF")

        self.memory = Memory.Memory()

        delegate_cell = Delegados.MemoryResultCell()

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("cat", _("Category"), 190, align_center=True)

        for num_lv in range(25):
            o_columns.nueva(
                f"lv_{num_lv}", str(num_lv + 1), 72, align_center=True, edicion=delegate_cell, is_editable=False
            )
        self.grid = Grid.Grid(self, o_columns, heigh_row=40, is_column_header_movable=False)
        self.grid.alternate_colors()
        self.register_grid(self.grid)

        tb = Controles.TBrutina(self)
        tb.new(_("Close"), Iconos.MainMenu(), self.finalize)

        lb_help = Controles.LB(self, _("Double-click + to train or numbers to upgrade").replace("+", "➕")).align_center()

        layout = Colocacion.V().control(tb).control(self.grid).control(lb_help).margen(3)

        self.setLayout(layout)

        self.restore_video(default_width=840, default_height=390)
        self.grid.gotop()
        self.grid.setFocus()

    def closeEvent(self, event):
        self.save_video()

    def finalize(self):
        self.save_video()
        self.accept()

    @staticmethod
    def grid_num_datos(_grid):
        return 6  # una fila por categoría

    def is_selectable(self, ncat, nlevel):
        # si tiene informacion
        dic_data = self.memory.dic_data
        if dic_data[ncat][nlevel] != 0:
            return True
        # si el anterior tiene datos
        if nlevel == 0 or dic_data[ncat][nlevel - 1] != 0:
            if ncat == 0 or dic_data[ncat - 1][nlevel] != 0:
                return True
        return False

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        xcat = row  # fila = índice de categoría
        if key == "cat":
            cat = self.memory.categorias.number(xcat)
            return cat.name()
        # columnas lv_N: devuelven tupla (valor_total, delta_por_pieza)
        xlv = int(key[3:])  # índice de nivel 0-24
        li_data = self.memory.dic_data[xcat]
        record = li_data[xlv]
        if record == 0:
            if self.is_selectable(xcat, xlv):
                return "➕", ""
            else:
                return "", ""
        main_value = f"{record:0.02f}\""
        delta = f"{record / (xlv + 3):0.02f}"
        return main_value, delta

    @staticmethod
    def grid_bold(_grid, row, obj_column):
        return obj_column.key == "cat"

    @staticmethod
    def grid_color_fondo(_grid, row, _obj_column):
        if _obj_column.key == "cat":
            dic_colors = Code.dic_colors
            return ScreenUtils.qt_color(dic_colors[f"SQUARED_CONTROLLED_B_{row}"])
        return None

    def grid_doble_click(self, _grid, row, obj_column):
        key = obj_column.key
        if key != "cat":
            xcat = row  # fila = índice de categoría
            xlv = int(key[3:])  # índice de nivel 0-24
            if self.is_selectable(xcat, xlv):
                self.launch(xcat, xlv)

    def launch(self, num_cat, num_level):
        with QTMessages.working(self):
            li_fens = self.memory.get_list_fens(num_level + 3)
        w = WMemoryWork(self, self.memory, li_fens, num_cat, num_level)
        if w.exec():
            self.grid.refresh()
