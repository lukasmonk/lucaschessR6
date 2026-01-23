import copy
import os

from PySide6 import QtCore, QtWidgets

import Code
from Code.Z import Util
from Code.Board import Board
from Code.Director import TabVisual
from Code.QT import (
    Colocacion,
    Columnas,
    Controles,
    FormLayout,
    Grid,
    Iconos,
    LCDialog,
    QTDialogs,
    QTMessages,
    QTUtils,
    SelectFiles,
)


class WTVMarker(QtWidgets.QDialog):
    def __init__(self, owner, reg_marker, xml=None, name=None):

        QtWidgets.QDialog.__init__(self, owner)

        self.setWindowTitle(_("Marker"))
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
        )

        self.configuration = Code.configuration

        if reg_marker is None:
            reg_marker = TabVisual.PMarker()
            reg_marker.xml = xml
            if name:
                reg_marker.name = name

        li_acciones = [
            (_("Save"), Iconos.Aceptar(), self.grabar),
            None,
            (_("Cancel"), Iconos.Cancelar(), self.reject),
            None,
        ]
        tb = QTDialogs.LCTB(self, li_acciones)

        # Board
        config_board = owner.board.config_board
        self.board = Board.Board(self, config_board, with_director=False)
        self.board.draw_window()
        self.board.copia_posicion_de(owner.board)

        # Datos generales
        li_gen = []

        # name del svg que se usara en los menus del tutorial
        config = FormLayout.Editbox(_("Name"), ancho=120)
        li_gen.append((config, reg_marker.name))

        # ( "opacity", "n", 1.0 ),
        config = FormLayout.Dial(_("Degree of transparency"), 0, 99)
        li_gen.append((config, 100 - int(reg_marker.opacity * 100)))

        # ( "psize", "n", 100 ),
        config = FormLayout.Spinbox(f"{_('Size')} %", 1, 1600, 50)
        li_gen.append((config, reg_marker.psize))

        # ( "poscelda", "n", 1 ),
        li = (
            (f"{_('Top')}-{_('Left')}", 0),
            (f"{_('Top')}-{_('Right')}", 1),
            (f"{_('Bottom')}-{_('Left')}", 2),
            (f"{_('Bottom')}-{_('Right')}", 3),
        )
        config = FormLayout.Combobox(_("Position in the square"), li)
        li_gen.append((config, reg_marker.poscelda))

        # orden
        config = FormLayout.Combobox(_("Order concerning other items"), QTMessages.list_zvalues())
        li_gen.append((config, reg_marker.physical_pos.orden))

        self.form = FormLayout.FormWidget(li_gen, dispatch=self.cambios)

        # Layout
        layout = Colocacion.H().control(self.form).relleno().control(self.board)
        layout1 = Colocacion.V().control(tb).otro(layout)
        self.setLayout(layout1)

        # Ejemplos
        li_movs = ["b4c4", "e2e2", "e4g7"]
        self.liEjemplos = []
        for a1h8 in li_movs:
            reg_marker.a1h8 = a1h8
            reg_marker.siMovible = True
            marker = self.board.create_marker(reg_marker, is_editing=True)
            self.liEjemplos.append(marker)

    def cambios(self):
        if hasattr(self, "form"):
            li = self.form.get()
            for n, marker in enumerate(self.liEjemplos):
                reg_marker = marker.block_data
                reg_marker.name = li[0]
                reg_marker.opacity = (100.0 - float(li[1])) / 100.0
                reg_marker.psize = li[2]
                reg_marker.poscelda = li[3]
                reg_marker.physical_pos.orden = li[4]
                marker.setOpacity(reg_marker.opacity)
                marker.setZValue(reg_marker.physical_pos.orden)
                marker.update()
            self.board.escena.update()
            QTUtils.refresh_gui()

    def grabar(self):
        reg_marker = self.liEjemplos[0].block_data
        name = reg_marker.name.strip()
        if name == "":
            QTMessages.message_error(self, _("Name missing"))
            return

        pm = self.liEjemplos[0].get_pixmap()
        bf = QtCore.QBuffer()
        pm.save(bf, "PNG")
        reg_marker.png = bytes(bf.data().data())

        self.regMarker = reg_marker
        self.accept()


class WTVMarkers(LCDialog.LCDialog):
    def __init__(self, owner, list_markers, db_markers):

        titulo = _("Markers")
        icono = Iconos.Markers()
        extparam = "markers"
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, extparam)

        self.owner = owner

        flb = Controles.FontType(puntos=8)

        self.configuration = Code.configuration
        self.liPMarkers = list_markers
        self.db_markers = db_markers

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
        config_board = self.configuration.config_board("EDIT_GRAPHICS", 48)
        self.board = Board.Board(self, config_board, with_director=False)
        self.board.draw_window()
        self.board.copia_posicion_de(owner.board)

        # Layout
        layout = Colocacion.H().otro(ly).control(self.board)
        self.setLayout(layout)

        self.grid.gotop()
        self.grid.setFocus()

    def closeEvent(self, event):
        self.save_video()

    def finalize(self):
        self.save_video()
        self.close()

    def grid_num_datos(self, _grid):
        return len(self.liPMarkers)

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        if key == "NUMBER":
            return str(row + 1)
        elif key == "NOMBRE":
            return self.liPMarkers[row].name
        return None

    def grid_doble_click(self, _grid, _row, _obj_column):
        self.modificar()

    def grid_cambiado_registro(self, _grid, row, _obj_column):
        if row >= 0:
            reg_marker = self.liPMarkers[row]
            self.board.remove_movables()
            # Ejemplos
            li_movs = ["g4h3", "e2e4", "d6f4"]
            for a1h8 in li_movs:
                reg_marker.a1h8 = a1h8
                reg_marker.siMovible = True
                self.board.create_marker(reg_marker, is_editing=True)
            self.board.escena.update()

    def mas(self):

        menu = QTDialogs.LCMenu(self)

        def seek_folder(submenu, xfolder):
            for entry in os.scandir(xfolder):
                if entry.is_dir():
                    smenu = submenu.submenu(entry.name, Iconos.Carpeta())
                    seek_folder(smenu, entry.path)
            for entry in os.scandir(xfolder):
                if entry.is_file() and entry.name.lower().endswith(".svg"):
                    ico = QTDialogs.fsvg2ico(entry.path, 32)
                    if ico:
                        submenu.opcion(entry.path, entry.name[:-4], ico)

        seek_folder(menu, Code.path_resource("Imgs"))

        menu.separador()

        menu.opcion("@", _X(_("To seek %1 file"), "Marker"), Iconos.Fichero())

        resp = menu.lanza()

        if resp is None:
            return

        if resp == "@":
            key = "MARKERS"
            dic = Code.configuration.read_variables(key)
            folder = dic.get("PATH_SEEK", Code.configuration.paths.folder_userdata())
            file = SelectFiles.leeFichero(self, folder, "svg", titulo=_("Image"))
            if not file:
                return
            dic["PATH_SEEK"] = os.path.dirname(file)
            Code.configuration.write_variables(key, dic)
        else:
            file = resp
        with open(file, "rt", encoding="utf-8", errors="ignore") as f:
            contenido = f.read()
        name = os.path.basename(file)[:-4]
        w = WTVMarker(self, None, xml=contenido, name=name)
        if w.exec():
            reg_marker = w.regMarker
            reg_marker.id = Util.huella()
            reg_marker.ordenVista = (self.liPMarkers[-1].ordenVista + 1) if self.liPMarkers else 1
            self.db_markers[reg_marker.id] = reg_marker.save_dic()
            self.liPMarkers.append(reg_marker)
            self.grid.refresh()
            self.grid.gobottom()
            self.grid.setFocus()

    def borrar(self):
        row = self.grid.recno()
        if row >= 0:
            if QTMessages.pregunta(self, _X(_("Delete %1?"), self.liPMarkers[row].name)):
                reg_marker = self.liPMarkers[row]
                str_id = reg_marker.id
                del self.liPMarkers[row]
                del self.db_markers[str_id]
                self.grid.refresh()
                self.grid.setFocus()

    def modificar(self):
        row = self.grid.recno()
        if row >= 0:
            w = WTVMarker(self, self.liPMarkers[row])
            if w.exec():
                reg_marker = w.regMarker
                str_id = reg_marker.id
                self.liPMarkers[row] = reg_marker
                self.db_markers[str_id] = reg_marker.save_dic()
                self.grid.refresh()
                self.grid.setFocus()
                self.grid_cambiado_registro(self.grid, row, None)

    def copiar(self):
        row = self.grid.recno()
        if row >= 0:
            reg_marker = copy.deepcopy(self.liPMarkers[row])
            n = 1

            def exist_name(xname):
                for rf in self.liPMarkers:
                    if rf.name == xname:
                        return True
                return False

            name = "%s-%d" % (reg_marker.name, n)
            while exist_name(name):
                n += 1
                name = "%s-%d" % (reg_marker.name, n)
            reg_marker.name = name
            reg_marker.id = Util.huella()
            reg_marker.ordenVista = self.liPMarkers[-1].ordenVista + 1
            self.db_markers[reg_marker.id] = reg_marker
            self.liPMarkers.append(reg_marker)
            self.grid.refresh()
            self.grid.setFocus()

    def interchange(self, fila1, fila2):
        reg_marker1, reg_marker2 = self.liPMarkers[fila1], self.liPMarkers[fila2]
        reg_marker1.ordenVista, reg_marker2.ordenVista = (
            reg_marker2.ordenVista,
            reg_marker1.ordenVista,
        )
        self.db_markers[reg_marker1.id] = reg_marker1.save_dic()
        self.db_markers[reg_marker2.id] = reg_marker2.save_dic()
        self.liPMarkers[fila1], self.liPMarkers[fila2] = (
            self.liPMarkers[fila2],
            self.liPMarkers[fila1],
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
        if 0 <= row < (len(self.liPMarkers) - 1):
            self.interchange(row, row + 1)
