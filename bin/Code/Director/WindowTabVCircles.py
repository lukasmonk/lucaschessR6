import copy

from PySide6 import QtCore, QtWidgets

import Code
from Code.Z import Util
from Code.Board import Board, BoardTypes
from Code.Director import TabVisual
from Code.QT import Colocacion, Columnas, Controles, FormLayout, Grid, Iconos, LCDialog, QTDialogs, QTMessages, QTUtils


class WTVCircle(QtWidgets.QDialog):
    def __init__(self, owner, reg_circle):

        QtWidgets.QDialog.__init__(self, owner)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.setWindowTitle(_("Circle"))
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
        )

        if not reg_circle:
            reg_circle = TabVisual.PCircle()
        self.reg_circle = reg_circle

        tb = QTDialogs.LCTB(self)
        tb.new(_("Save"), Iconos.Aceptar(), self.grabar),
        tb.new(_("Cancel"), Iconos.Cancelar(), self.reject)

        # Board
        config_board = owner.board.config_board.copia(owner.board.config_board.id())
        config_board.width_piece(36)
        self.board = Board.Board(self, config_board, with_director=False)
        self.board.draw_window()
        self.board.copia_posicion_de(owner.board)

        # Datos generales
        li_gen = []

        # name del box que se usara en los menus del tutorial
        config = FormLayout.Editbox(_("Name"), ancho=120)
        li_gen.append((config, reg_circle.name))

        # ( "tipo", "n", Qt.PenStyle.SolidLine ), #1=SolidLine, 2=DashLine, 3=DotLine, 4=DashDotLine, 5=DashDotDotLine
        config = FormLayout.Combobox(_("Line Type"), QTMessages.lines_type())
        li_gen.append((config, reg_circle.tipo))

        # ( "color", "n", 0 ),
        config = FormLayout.Colorbox(_("Color"), 80, 20)
        li_gen.append((config, reg_circle.color))

        # ( "colorinterior", "n", -1 ),
        config = FormLayout.Colorbox(_("Internal color"), 80, 20, is_checked=True)
        li_gen.append((config, reg_circle.colorinterior))

        # ( "opacity", "n", 1.0 ),
        config = FormLayout.Dial(_("Degree of transparency"), 0, 99)
        li_gen.append((config, 100 - int(reg_circle.opacity * 100)))

        # ( "grosor", "n", 1 ), # ancho del trazo
        config = FormLayout.Spinbox(_("Thickness"), 1, 20, 50)
        li_gen.append((config, reg_circle.grosor))

        # orden
        config = FormLayout.Combobox(_("Order concerning other items"), QTMessages.list_zvalues())
        li_gen.append((config, reg_circle.physical_pos.orden))

        self.form = FormLayout.FormWidget(li_gen, dispatch=self.cambios)

        # Layout
        layout = Colocacion.H().control(self.form).relleno().control(self.board)
        layout1 = Colocacion.V().control(tb).otro(layout)
        self.setLayout(layout1)

        # Ejemplos
        li_movs = ["b4c4", "e2e2", "e4g7"]
        self.liEjemplos = []
        for a1h8 in li_movs:
            reg_circle.a1h8 = a1h8
            reg_circle.siMovible = True
            box = self.board.create_circle(reg_circle)
            self.liEjemplos.append(box)

    def cambios(self):
        if hasattr(self, "form"):
            li = self.form.get()
            for n, box in enumerate(self.liEjemplos):
                reg_circle = box.block_data
                reg_circle.name = li[0]
                reg_circle.tipo = li[1]
                reg_circle.color = li[2]
                reg_circle.colorinterior = li[3]
                reg_circle.opacity = (100.0 - float(li[4])) / 100.0
                reg_circle.grosor = li[5]
                reg_circle.physical_pos.orden = li[6]
                box.setOpacity(reg_circle.opacity)
                box.setZValue(reg_circle.physical_pos.orden)
                box.update()
            self.board.escena.update()
            QTUtils.refresh_gui()

    def grabar(self):
        reg_circle = self.liEjemplos[0].block_data
        name = reg_circle.name.strip()
        if name == "":
            QTMessages.message_error(self, _("Name missing"))
            return

        self.reg_circle = reg_circle
        pm = self.liEjemplos[0].pixmap()
        bf = QtCore.QBuffer()
        pm.save(bf, "PNG")
        self.reg_circle.png = bytes(bf.data().data())

        self.accept()


class WTVCircles(LCDialog.LCDialog):
    def __init__(self, owner, list_circles, db_circles):

        titulo = _("Circles")
        icono = Iconos.Circle()
        extparam = "circles"
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, extparam)

        self.owner = owner

        flb = Controles.FontType(puntos=8)

        self.lip_circles = list_circles
        self.configuration = Code.configuration

        self.db_circles = db_circles

        # Lista
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NUMBER", _("N."), 60, align_center=True)
        o_columns.nueva("NOMBRE", _("Name"), 256)

        self.grid = Grid.Grid(self, o_columns, xid="M", complete_row_select=True)

        tb = QTDialogs.LCTB(self)
        tb.new(_("Close"), Iconos.MainMenu(), self.finalize)
        tb.new(_("New"), Iconos.Nuevo(), self.mas)
        tb.new(_("Remove"), Iconos.Borrar(), self.borrar)
        tb.new(_("Modify"), Iconos.Modificar(), self.modificar)
        tb.new(_("Copy"), Iconos.Copiar(), self.copiar)
        tb.new(_("Up"), Iconos.Arriba(), self.arriba)
        tb.new(_("Down"), Iconos.Abajo(), self.abajo)
        tb.setFont(flb)

        ly = Colocacion.V().control(tb).control(self.grid)

        # Board
        config_board = Code.configuration.config_board("EDIT_GRAPHICS", 48)
        self.board = Board.Board(self, config_board, with_director=False)
        self.board.draw_window()
        self.board.copia_posicion_de(owner.board)

        # Layout
        layout = Colocacion.H().otro(ly).control(self.board)
        self.setLayout(layout)

        self.register_grid(self.grid)
        self.restore_video()

        # Ejemplos
        li_movs = ["b4c4", "e2e2", "e4g7"]
        self.liEjemplos = []
        reg_circle = BoardTypes.Circle()
        for a1h8 in li_movs:
            reg_circle.a1h8 = a1h8
            reg_circle.siMovible = True
            circle = self.board.create_circle(reg_circle)
            self.liEjemplos.append(circle)

        self.grid.gotop()
        self.grid.setFocus()

    def closeEvent(self, event):
        self.save_video()

    def finalize(self):
        self.save_video()
        self.close()

    def grid_num_datos(self, _grid):
        return len(self.lip_circles)

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        if key == "NUMBER":
            return str(row + 1)
        elif key == "NOMBRE":
            return self.lip_circles[row].name
        return None

    def grid_doble_click(self, _grid, _row, _obj_column):
        self.modificar()

    def grid_cambiado_registro(self, _grid, row, _obj_column):
        if row >= 0:
            reg_circle = self.lip_circles[row]
            for ejemplo in self.liEjemplos:
                a1h8 = ejemplo.block_data.a1h8
                bd = copy.deepcopy(reg_circle)
                bd.a1h8 = a1h8
                bd.width_square = self.board.width_square
                ejemplo.block_data = bd
                ejemplo.reset()
            self.board.escena.update()

    def mas(self):
        w = WTVCircle(self, None)
        if w.exec():
            reg_circle = w.reg_circle
            reg_circle.id = Util.huella()
            reg_circle.ordenVista = (self.lip_circles[-1].ordenVista + 1) if self.lip_circles else 1
            self.db_circles[reg_circle.id] = reg_circle.save_dic()
            self.lip_circles.append(reg_circle)
            self.grid.refresh()
            self.grid.gobottom()
            self.grid.setFocus()

    def borrar(self):
        row = self.grid.recno()
        if row >= 0:
            if QTMessages.pregunta(self, _X(_("Delete circle %1?"), self.lip_circles[row].name)):
                reg_circle = self.lip_circles[row]
                str_id = reg_circle.id
                del self.db_circles[str_id]
                del self.lip_circles[row]
                self.grid.refresh()
                self.grid.setFocus()

    def modificar(self):
        row = self.grid.recno()
        if row >= 0:
            w = WTVCircle(self, self.lip_circles[row])
            if w.exec():
                reg_circle = w.reg_circle
                str_id = reg_circle.id
                self.lip_circles[row] = reg_circle
                self.db_circles[str_id] = reg_circle.save_dic()
                self.grid.refresh()
                self.grid.setFocus()
                self.grid_cambiado_registro(self.grid, row, None)

    def copiar(self):
        row = self.grid.recno()
        if row >= 0:
            reg_circle = copy.deepcopy(self.lip_circles[row])

            def exist_name(xname):
                for rf in self.lip_circles:
                    if rf.name == xname:
                        return True
                return False

            n = 1
            name = "%s-%d" % (reg_circle.name, n)
            while exist_name(name):
                n += 1
                name = "%s-%d" % (reg_circle.name, n)
            reg_circle.name = name
            reg_circle.id = Util.huella()
            reg_circle.ordenVista = self.lip_circles[-1].ordenVista + 1
            self.db_circles[reg_circle.id] = reg_circle.save_dic()
            self.lip_circles.append(reg_circle)
            self.grid.refresh()
            self.grid.setFocus()

    def interchange(self, fila1, fila2):
        reg_circle1, reg_circle2 = self.lip_circles[fila1], self.lip_circles[fila2]
        reg_circle1.ordenVista, reg_circle2.ordenVista = (
            reg_circle2.ordenVista,
            reg_circle1.ordenVista,
        )
        self.db_circles[reg_circle1.id] = reg_circle1.save_dic()
        self.db_circles[reg_circle2.id] = reg_circle2.save_dic()
        self.lip_circles[fila1], self.lip_circles[fila2] = (
            self.lip_circles[fila2],
            self.lip_circles[fila1],
        )
        self.grid.goto(fila2, 0)
        self.grid.refresh()
        self.grid.setFocus()

    def arriba(self):
        row = self.grid.recno()
        if row > 0:
            self.interchange(row, row - 1)

    def abajo(self):
        row = self.grid.recno()
        if 0 <= row < (len(self.lip_circles) - 1):
            self.interchange(row, row + 1)
