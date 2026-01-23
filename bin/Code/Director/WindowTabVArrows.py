import copy

from PySide6 import QtCore, QtWidgets

import Code
from Code.Z import Util
from Code.Board import Board, BoardArrows, BoardTypes
from Code.Director import TabVisual
from Code.QT import Colocacion, Columnas, Controles, FormLayout, Grid, Iconos, LCDialog, QTDialogs, QTMessages, QTUtils


def types_destination():
    li = ((_("To center"), "c"), (_("To closest point"), "m"))
    return li


class WTVArrow(QtWidgets.QDialog):
    def __init__(self, owner, reg_flecha, if_name):

        QtWidgets.QDialog.__init__(self, owner)

        self.setWindowTitle(_("Arrow"))
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
        )

        self.siNombre = if_name

        if reg_flecha is None:
            reg_flecha = TabVisual.PFlecha()

        tb = QTDialogs.LCTB(self)
        tb.new(_("Save"), Iconos.Aceptar(), self.grabar),
        tb.new(_("Cancel"), Iconos.Cancelar(), self.reject)

        # Board
        config_board = owner.board.config_board.copia(owner.board.config_board.id())
        config_board.width_piece(36)
        self.board = Board.Board(self, config_board, with_director=False)
        self.board.draw_window()
        self.board.copia_posicion_de(owner.board)
        self.board.allowed_extern_resize(False)
        self.board.activa_menu_visual(False)

        # Datos generales
        li_gen = []

        if if_name:
            # name de la arrow que se usara en los menus del tutorial
            config = FormLayout.Editbox(_("Name"), ancho=120)
            li_gen.append((config, reg_flecha.name))

        # ( "forma", "t", "a" ), # a = abierta -> , c = cerrada la cabeza, p = poligono cuadrado,
        li_forms = (
            (_("Opened"), "a"),
            (_("Head closed"), "c"),
            (_("Polygon  1"), "1"),
            (_("Polygon  2"), "2"),
            (_("Polygon  3"), "3"),
        )
        config = FormLayout.Combobox(_("Form"), li_forms)
        li_gen.append((config, reg_flecha.forma))

        # ( "tipo", "n", Qt.PenStyle.SolidLine ), #1=SolidLine, 2=DashLine, 3=DotLine, 4=DashDotLine, 5=DashDotDotLine
        config = FormLayout.Combobox(_("Line Type"), QTMessages.lines_type())
        li_gen.append((config, reg_flecha.tipo))

        # li_gen.append( (None,None) )

        # ( "color", "n", 0 ),
        config = FormLayout.Colorbox(_("Color"), 80, 20)
        li_gen.append((config, reg_flecha.color))

        # ( "colorinterior", "n", -1 ), # si es cerrada
        config = FormLayout.Colorbox(_("Internal color"), 80, 20, is_checked=True)
        li_gen.append((config, reg_flecha.colorinterior))

        # ( "opacity", "n", 1.0 ),
        config = FormLayout.Dial(_("Degree of transparency"), 0, 99)
        li_gen.append((config, 100 - int(reg_flecha.opacity * 100)))

        # li_gen.append( (None,None) )

        # ( "redondeos", "l", False ),
        li_gen.append((_("Rounded edges"), reg_flecha.redondeos))

        # ( "grosor", "n", 1 ), # ancho del trazo
        config = FormLayout.Spinbox(_("Thickness"), 1, 20, 50)
        li_gen.append((config, reg_flecha.grosor))

        # li_gen.append( (None,None) )

        # ( "altocabeza", "n", 1 ), # altura de la cabeza
        config = FormLayout.Spinbox(_("Head height"), 0, 100, 50)
        li_gen.append((config, reg_flecha.altocabeza))

        # ( "ancho", "n", 10 ), # ancho de la base de la arrow si es un poligono
        config = FormLayout.Spinbox(_("Base width"), 1, 100, 50)
        li_gen.append((config, reg_flecha.ancho))

        # ( "vuelo", "n", 5 ), # vuelo de la arrow respecto al ancho de la base
        config = FormLayout.Spinbox(_("Additional width of the base of the head"), 1, 100, 50)
        li_gen.append((config, reg_flecha.vuelo))

        # ( "descuelgue", "n", 2 ), # vuelo hacia arriba
        config = FormLayout.Spinbox(_("Height of the base angle of the head"), -100, 100, 50)
        li_gen.append((config, reg_flecha.descuelgue))

        # li_gen.append( (None,None) )

        # ( "destino", "t", "c" ), # c = centro, m = minimo
        config = FormLayout.Combobox(_("Target position"), types_destination())
        li_gen.append((config, reg_flecha.destino))

        # li_gen.append( (None,None) )

        # orden
        config = FormLayout.Combobox(_("Order concerning other items"), QTMessages.list_zvalues())
        li_gen.append((config, reg_flecha.physical_pos.orden))

        self.form = FormLayout.FormWidget(li_gen, dispatch=self.cambios)

        # Layout
        layout = Colocacion.H().control(self.form).relleno().control(self.board)
        layout1 = Colocacion.V().control(tb).otro(layout)
        self.setLayout(layout1)

        # Ejemplos
        self.board.remove_movables()
        li_movs = ["d2d6", "a8h8", "h5b7"]
        self.liEjemplos = []
        for a1h8 in li_movs:
            reg_flecha.a1h8 = a1h8
            reg_flecha.siMovible = True
            arrow = self.board.create_arrow(reg_flecha)
            self.liEjemplos.append(arrow)

    def cambios(self):
        if hasattr(self, "form"):
            li = self.form.get()
            n = 1 if self.siNombre else 0
            for arrow in self.liEjemplos:
                reg_arrow = arrow.block_data
                if self.siNombre:
                    reg_arrow.name = li[0]
                reg_arrow.forma = li[n]
                reg_arrow.tipo = li[n + 1]
                reg_arrow.color = li[n + 2]
                reg_arrow.colorinterior = li[n + 3]
                # reg_arrow.colorinterior2 = li[4]
                reg_arrow.opacity = (100.0 - float(li[n + 4])) / 100.0
                reg_arrow.redondeos = li[n + 5]
                reg_arrow.grosor = li[n + 6]
                reg_arrow.altocabeza = li[n + 7]
                reg_arrow.ancho = li[n + 8]
                reg_arrow.vuelo = li[n + 9]
                reg_arrow.descuelgue = li[n + 10]
                reg_arrow.destino = li[n + 11]
                reg_arrow.physical_pos.orden = li[n + 12]
                arrow.physical_pos2xy()  # posible cambio en destino
                arrow.setOpacity(reg_arrow.opacity)
                arrow.setZValue(reg_arrow.physical_pos.orden)
            self.board.escena.update()
            QTUtils.refresh_gui()

    def grabar(self):
        reg_arrow = self.liEjemplos[0].block_data
        if self.siNombre:
            name = reg_arrow.name.strip()
            if name == "":
                QTMessages.message_error(self, _("Name missing"))
                return

        bf = reg_arrow
        p = bf.physical_pos
        p.x = 0
        p.y = 16
        p.ancho = 32
        p.alto = 16

        pm = BoardArrows.pixmap_arrow(bf, 32, 32)
        buf = QtCore.QBuffer()
        pm.save(buf, "PNG")
        reg_arrow.png = bytes(buf.data().data())
        self.reg_arrow = reg_arrow
        self.accept()


class WTVArrows(LCDialog.LCDialog):
    def __init__(self, owner, db_arrows):

        titulo = _("Arrows")
        icono = Iconos.Flechas()
        extparam = "flechas"
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, extparam)

        self.owner = owner

        flb = Controles.FontType(puntos=8)

        self.configuration = Code.configuration

        self.db_arrows = db_arrows

        self.liPFlechas = owner.list_arrows()

        # Lista
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NUMBER", _("N."), 60, align_center=True)
        o_columns.nueva("NOMBRE", _("Name"), 256)

        self.grid = Grid.Grid(self, o_columns, xid="F", complete_row_select=True)

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
        li_movs = ["d2d6", "a8h8", "h5b7"]
        self.liEjemplos = []
        reg_flecha = BoardTypes.Flecha()
        for a1h8 in li_movs:
            reg_flecha.a1h8 = a1h8
            reg_flecha.siMovible = True
            arrow = self.board.create_arrow(reg_flecha)
            self.liEjemplos.append(arrow)

        self.grid.gotop()
        self.grid.setFocus()

    def closeEvent(self, event):
        self.save_video()

    def finalize(self):
        self.save_video()
        self.close()

    def grid_num_datos(self, _grid):
        return len(self.liPFlechas)

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        if key == "NUMBER":
            return str(row + 1)
        elif key == "NOMBRE":
            return self.liPFlechas[row].name

        return len(self.liPFlechas)

    def grid_doble_click(self, _grid, _row, _obj_column):
        self.modificar()

    def grid_cambiado_registro(self, _grid, row, _obj_column):
        if row >= 0:
            reg_arrow = self.liPFlechas[row]
            for ejemplo in self.liEjemplos:
                a1h8 = ejemplo.block_data.a1h8
                bd = copy.deepcopy(reg_arrow)
                bd.a1h8 = a1h8
                bd.width_square = self.board.width_square
                ejemplo.block_data = bd
                ejemplo.reset()
            self.board.escena.update()

    def mas(self):
        w = WTVArrow(self, None, True)
        if w.exec():
            reg_arrow = w.reg_arrow
            reg_arrow.id = Util.huella()
            reg_arrow.ordenVista = (self.liPFlechas[-1].ordenVista + 1) if self.liPFlechas else 1
            self.db_arrows[reg_arrow.id] = reg_arrow.save_dic()
            self.liPFlechas.append(reg_arrow)
            self.grid.refresh()
            self.grid.gobottom()
            self.grid.setFocus()

    def borrar(self):
        row = self.grid.recno()
        if row >= 0:
            if QTMessages.pregunta(self, _X(_("Delete the arrow %1?"), self.liPFlechas[row].name)):
                reg_arrow = self.liPFlechas[row]
                str_id = reg_arrow.id
                del self.db_arrows[str_id]
                del self.liPFlechas[row]
                self.grid.refresh()
                self.grid.setFocus()

    def modificar(self):
        row = self.grid.recno()
        if row >= 0:
            w = WTVArrow(self, self.liPFlechas[row], True)
            if w.exec():
                reg_arrow = w.reg_arrow
                str_id = reg_arrow.id
                self.liPFlechas[row] = reg_arrow
                self.db_arrows[str_id] = reg_arrow.save_dic()
                self.grid.refresh()
                self.grid.setFocus()
                self.grid_cambiado_registro(self.grid, row, None)

    def copiar(self):
        row = self.grid.recno()
        if row >= 0:
            reg_arrow = copy.deepcopy(self.liPFlechas[row])

            def exist_name(xname):
                for rf in self.liPFlechas:
                    if rf.name == xname:
                        return True
                return False

            n = 1
            name = "%s-%d" % (reg_arrow.name, n)
            while exist_name(name):
                n += 1
                name = "%s-%d" % (reg_arrow.name, n)
            reg_arrow.name = name
            reg_arrow.id = Util.huella()
            reg_arrow.ordenVista = self.liPFlechas[-1].ordenVista + 1
            self.db_arrows[reg_arrow.id] = reg_arrow.save_dic()
            self.liPFlechas.append(reg_arrow)
            self.grid.refresh()
            self.grid.setFocus()

    def interchange(self, fila1, fila2):
        reg_flecha1, reg_flecha2 = self.liPFlechas[fila1], self.liPFlechas[fila2]
        reg_flecha1.ordenVista, reg_flecha2.ordenVista = (
            reg_flecha2.ordenVista,
            reg_flecha1.ordenVista,
        )
        self.db_arrows[reg_flecha1.id] = reg_flecha1.save_dic()
        self.db_arrows[reg_flecha2.id] = reg_flecha2.save_dic()
        self.liPFlechas[fila1], self.liPFlechas[fila2] = (
            self.liPFlechas[fila2],
            self.liPFlechas[fila1],
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
        if 0 <= row < (len(self.liPFlechas) - 1):
            self.interchange(row, row + 1)
