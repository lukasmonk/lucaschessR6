import copy

from PySide6 import QtCore, QtWidgets

import Code
from Code.Z import Util
from Code.Board import Board, BoardTypes
from Code.Director import TabVisual
from Code.QT import Colocacion, Columnas, Controles, FormLayout, Grid, Iconos, LCDialog, QTDialogs, QTMessages, QTUtils


class WTVMarco(QtWidgets.QDialog):
    def __init__(self, owner, reg_marco):

        QtWidgets.QDialog.__init__(self, owner)

        self.setWindowTitle(_("Box"))
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
        )

        if not reg_marco:
            reg_marco = TabVisual.PMarco()

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
        li_gen.append((config, reg_marco.name))

        # ( "tipo", "n", Qt.PenStyle.SolidLine ), #1=SolidLine, 2=DashLine, 3=DotLine, 4=DashDotLine, 5=DashDotDotLine
        config = FormLayout.Combobox(_("Line Type"), QTMessages.lines_type())
        li_gen.append((config, reg_marco.tipo))

        # ( "color", "n", 0 ),
        config = FormLayout.Colorbox(_("Color"), 80, 20)
        li_gen.append((config, reg_marco.color))

        # ( "colorinterior", "n", -1 ),
        config = FormLayout.Colorbox(_("Internal color"), 80, 20, is_checked=True)
        li_gen.append((config, reg_marco.colorinterior))

        # ( "opacity", "n", 1.0 ),
        config = FormLayout.Dial(_("Degree of transparency"), 0, 99)
        li_gen.append((config, 100 - int(reg_marco.opacity * 100)))

        # ( "grosor", "n", 1 ), # ancho del trazo
        config = FormLayout.Spinbox(_("Thickness"), 1, 20, 50)
        li_gen.append((config, reg_marco.grosor))

        # ( "redEsquina", "n", 0 ),
        config = FormLayout.Spinbox(_("Rounded corners"), 0, 100, 50)
        li_gen.append((config, reg_marco.redEsquina))

        # orden
        config = FormLayout.Combobox(_("Order concerning other items"), QTMessages.list_zvalues())
        li_gen.append((config, reg_marco.physical_pos.orden))

        self.form = FormLayout.FormWidget(li_gen, dispatch=self.cambios)

        # Layout
        layout = Colocacion.H().control(self.form).relleno().control(self.board)
        layout1 = Colocacion.V().control(tb).otro(layout)
        self.setLayout(layout1)

        # Ejemplos
        li_movs = ["b4c4", "e2e2", "e4g7"]
        self.liEjemplos = []
        for a1h8 in li_movs:
            reg_marco.a1h8 = a1h8
            reg_marco.siMovible = True
            box = self.board.create_marco(reg_marco)
            self.liEjemplos.append(box)

    def cambios(self):
        if hasattr(self, "form"):
            li = self.form.get()
            for n, box in enumerate(self.liEjemplos):
                reg_marco = box.block_data
                reg_marco.name = li[0]
                reg_marco.tipo = li[1]
                reg_marco.color = li[2]
                reg_marco.colorinterior = li[3]
                # reg_marco.colorinterior2 = li[]
                reg_marco.opacity = (100.0 - float(li[4])) / 100.0
                reg_marco.grosor = li[5]
                reg_marco.redEsquina = li[6]
                reg_marco.physical_pos.orden = li[7]
                box.setOpacity(reg_marco.opacity)
                box.setZValue(reg_marco.physical_pos.orden)
                box.update()
            self.board.escena.update()
            QTUtils.refresh_gui()

    def grabar(self):
        reg_marco = self.liEjemplos[0].block_data
        name = reg_marco.name.strip()
        if name == "":
            QTMessages.message_error(self, _("Name missing"))
            return

        self.reg_marco = reg_marco
        pm = self.liEjemplos[0].pixmap()
        bf = QtCore.QBuffer()
        pm.save(bf, "PNG")
        self.reg_marco.png = bytes(bf.data().data())

        self.accept()


class WTVMarcos(LCDialog.LCDialog):
    def __init__(self, owner, list_boxes, db_marcos):

        titulo = _("Boxes")
        icono = Iconos.Marcos()
        extparam = "marcos"
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, extparam)

        self.owner = owner

        flb = Controles.FontType(puntos=8)

        self.liPMarcos = list_boxes
        self.configuration = Code.configuration

        self.db_marcos = db_marcos

        self.liPMarcos = owner.list_boxes()

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
        reg_marco = BoardTypes.Marco()
        for a1h8 in li_movs:
            reg_marco.a1h8 = a1h8
            reg_marco.siMovible = True
            box = self.board.create_marco(reg_marco)
            self.liEjemplos.append(box)

        self.grid.gotop()
        self.grid.setFocus()

    def closeEvent(self, event):
        self.save_video()

    def finalize(self):
        self.save_video()
        self.close()

    def grid_num_datos(self, _grid):
        return len(self.liPMarcos)

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        if key == "NUMBER":
            return str(row + 1)
        elif key == "NOMBRE":
            return self.liPMarcos[row].name
        return None

    def grid_doble_click(self, _grid, _row, _obj_column):
        self.modificar()

    def grid_cambiado_registro(self, _grid, row, _obj_column):
        if row >= 0:
            reg_marco = self.liPMarcos[row]
            for ejemplo in self.liEjemplos:
                a1h8 = ejemplo.block_data.a1h8
                bd = copy.deepcopy(reg_marco)
                bd.a1h8 = a1h8
                bd.width_square = self.board.width_square
                ejemplo.block_data = bd
                ejemplo.reset()
            self.board.escena.update()

    def mas(self):
        w = WTVMarco(self, None)
        if w.exec():
            reg_marco = w.reg_marco
            reg_marco.id = Util.huella()
            reg_marco.ordenVista = (self.liPMarcos[-1].ordenVista + 1) if self.liPMarcos else 1
            self.db_marcos[reg_marco.id] = reg_marco.save_dic()
            self.liPMarcos.append(reg_marco)
            self.grid.refresh()
            self.grid.gobottom()
            self.grid.setFocus()

    def borrar(self):
        row = self.grid.recno()
        if row >= 0:
            if QTMessages.pregunta(self, _X(_("Delete box %1?"), self.liPMarcos[row].name)):
                reg_marco = self.liPMarcos[row]
                str_id = reg_marco.id
                del self.db_marcos[str_id]
                del self.liPMarcos[row]
                self.grid.refresh()
                self.grid.setFocus()

    def modificar(self):
        row = self.grid.recno()
        if row >= 0:
            w = WTVMarco(self, self.liPMarcos[row])
            if w.exec():
                reg_marco = w.reg_marco
                str_id = reg_marco.id
                self.liPMarcos[row] = reg_marco
                self.db_marcos[str_id] = reg_marco.save_dic()
                self.grid.refresh()
                self.grid.setFocus()
                self.grid_cambiado_registro(self.grid, row, None)

    def copiar(self):
        row = self.grid.recno()
        if row >= 0:
            reg_marco = copy.deepcopy(self.liPMarcos[row])

            def exist_name(xname):
                for rf in self.liPMarcos:
                    if rf.name == xname:
                        return True
                return False

            n = 1
            name = "%s-%d" % (reg_marco.name, n)
            while exist_name(name):
                n += 1
                name = "%s-%d" % (reg_marco.name, n)
            reg_marco.name = name
            reg_marco.id = Util.huella()
            reg_marco.ordenVista = self.liPMarcos[-1].ordenVista + 1
            self.db_marcos[reg_marco.id] = reg_marco
            self.liPMarcos.append(reg_marco)
            self.grid.refresh()
            self.grid.setFocus()

    def interchange(self, fila1, fila2):
        reg_marco1, reg_marco2 = self.liPMarcos[fila1], self.liPMarcos[fila2]
        reg_marco1.ordenVista, reg_marco2.ordenVista = (
            reg_marco2.ordenVista,
            reg_marco1.ordenVista,
        )
        self.db_marcos[reg_marco1.id] = reg_marco1.save_dic()
        self.db_marcos[reg_marco2.id] = reg_marco2.save_dic()
        self.liPMarcos[fila1], self.liPMarcos[fila2] = (
            self.liPMarcos[fila2],
            self.liPMarcos[fila1],
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
        if 0 <= row < (len(self.liPMarcos) - 1):
            self.interchange(row, row + 1)
