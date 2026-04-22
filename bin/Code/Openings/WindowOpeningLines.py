import os
import shutil
from typing import Optional, Dict, Any

from PySide6 import QtWidgets, QtCore

import Code
from Code.Base import Game
from Code.Openings import OpeningLines, OpeningsStd, WindowOpenings
from Code.QT import (
    Colocacion,
    Columnas,
    Controles,
    Delegados,
    Grid,
    Iconos,
    LCDialog,
    QTDialogs,
    QTMessages,
)
from Code.Z import Util


class TreeOpeningFolders(QtWidgets.QTreeWidget):
    """QTreeWidget personalizado para aceptar drag & drop de opening lines"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        """Aceptar drag si contiene datos de grid"""
        if event.mimeData().hasFormat("application/x-grid-row"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Mostrar dónde se soltaría"""
        if event.mimeData().hasFormat("application/x-grid-row"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Manejar drop de opening lines"""
        if not event.mimeData().hasFormat("application/x-grid-row"):
            return

        # Obtener el item donde se soltó
        item = self.itemAt(event.pos())
        if not item:
            return

        # Obtener los números de fila arrastrados
        try:
            encoded_data = event.mimeData().data("application/x-grid-row")
            li_rows = [int(x) for x in encoded_data.data().decode().split(",")]
        except (ValueError, AttributeError):
            return

        # Obtener la carpeta destino
        target_rel_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if target_rel_path is None:
            return

        # Llamar a la ventana para manejar el drop
        if hasattr(self.parent_window, "handle_tree_drop"):
            self.parent_window.handle_tree_drop(li_rows, target_rel_path)


class WOpeningLines(LCDialog.LCDialog):
    def __init__(self, procesador):
        self.procesador = procesador
        self.configuration = Code.configuration
        self.resultado: Optional[Dict[str, Any]] = None
        self.listaOpenings = OpeningLines.ListaOpenings(True)
        self.glista: Optional[Grid.Grid] = None
        self.tbtrain: Optional[Controles.TBrutina] = None
        self.wtrain: Optional[QtWidgets.QWidget] = None

        LCDialog.LCDialog.__init__(
            self,
            procesador.main_window,
            _('Opening lines'),
            Iconos.OpeningLines(),
            "openingLines",
        )

        self.tree_folders = TreeOpeningFolders(self)
        self.tree_folders.setHeaderLabel(_("Opening lines"))
        self.populate_tree()
        self.tree_folders.itemClicked.connect(self.on_folder_selected)
        self.tree_folders.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_folders.customContextMenuRequested.connect(self.tree_context_menu)
        self.tree_folders.setToolTip(_("Use the right-click button to open the maintenance options"))
        # Configurar tree para aceptar drops (drag & drop desde grid)
        self.tree_folders.setAcceptDrops(True)
        self.tree_folders.setDropIndicatorShown(True)
        self.tree_folders.setStyleSheet("""/* Contenedor principal: Un gris medio-claro que da sensación de profundidad */
QTreeView {
    background-color: #e2e2e2;
    color: #2c2c2c;
    border: 1px solid #bcbcbc;
    outline: none;
    alternate-background-color: #dadada; /* Para un efecto de cebra muy sutil */
}

/* Estilo de cada item */
QTreeView::item {
    padding: 8px 5px;
    border-bottom: 1px solid #d4d4d4;
}

/* Estado: Mouse encima (Hover) */
QTreeView::item:hover {
    background-color: #d6d6d6;
    color: #000000;
}

/* Estado: Seleccionado (Azul acero profundo o Gris Carbón) */
QTreeView::item:selected {
    background-color: #b0c4de; /* Azul acero claro, muy elegante */
    color: #000000;
    border-left: 4px solid #4682b4; /* Acento en azul más fuerte */
}

/* Estado: Seleccionado pero la ventana no tiene el foco */
QTreeView::item:selected:!active {
    background-color: #cfcfcf;
    color: #444444;
    border-left: 4px solid #999999;
}

/* Cabeceras de columnas: Un tono más fuerte para "enmarcar" */
QHeaderView::section {
    background-color: #cccccc;
    color: #333333;
    padding: 6px;
    border: none;
    border-right: 1px solid #b0b0b0;
    border-bottom: 2px solid #b0b0b0;
    font-weight: bold;
}

/* Scrollbar personalizado para encajar con el tono gris */
QScrollBar:vertical {
    background: #e2e2e2;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #afafaf;
    min-height: 25px;
    border-radius: 6px;
    border: 2px solid #e2e2e2; /* Crea un efecto de margen interno */
}

QScrollBar::handle:vertical:hover {
    background: #909090;
}""")

        sp = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

        tb = QTDialogs.LCTB(self)
        tb.new(_("Close"), Iconos.MainMenu(), self.finalize)
        tb.new(_("Edit"), Iconos.Modificar(), self.modificar)
        tb.new(_("New"), Iconos.Nuevo(), self.new)
        tb.new(_("Copy"), Iconos.Copiar(), self.copy)
        tb.new(_("Change"), Iconos.Preferencias(), self.change)
        tb.new(_("Up"), Iconos.Arriba(), self.arriba, sep=False)
        tb.new(_("Down"), Iconos.Abajo(), self.abajo)
        tb.new(_("Remove"), Iconos.Borrar(), self.grid_remove)
        tb.new(_("Update"), Iconos.Reiniciar(), self.reiniciar)

        tb.setSizePolicy(sp)

        self.tbtrain = tbtrain = Controles.TBrutina(self, with_text=False)
        tbtrain.new(_("Sequential"), Iconos.TrainSequential(), self.tr_sequential)
        tbtrain.new(_("Static"), Iconos.TrainStatic(), self.tr_static)
        tbtrain.new(_("Positions"), Iconos.TrainPositions(), self.tr_positions)
        tbtrain.new(_("With engines"), Iconos.TrainEngines(), self.tr_engines)

        lbtrain = Controles.LB(self, _("Trainings")).align_center()
        lbtrain.setStyleSheet("*{border: 1px solid #bababa;}")
        lytrain = Colocacion.V().control(lbtrain).control(tbtrain).margen(0)
        self.wtrain = QtWidgets.QWidget()
        self.wtrain.setLayout(lytrain)

        lytb = Colocacion.H().control(tb).control(self.wtrain).margen(0)
        wtb = QtWidgets.QWidget()
        wtb.setFixedHeight(66)
        wtb.setLayout(lytb)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("TITLE", _("Name"), 240)
        o_columns.nueva("BASEPV", _("First moves"), 280)
        o_columns.nueva("NUMLINES", _("Lines"), 80, align_center=True)
        o_columns.nueva("FILE", _("File"), 200)
        self.glista = Grid.GridDragDrop(self, o_columns, complete_row_select=True, select_multiple=True)

        ly = Colocacion.V().control(wtb).control(self.glista).margen(0)
        wright = QtWidgets.QWidget()
        wright.setLayout(ly)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self.tree_folders)
        splitter.addWidget(wright)
        splitter.setSizes([200, self.glista.width_and_vbar()])
        self.register_splitter(splitter, "all")

        ly = Colocacion.V().control(splitter)

        self.setLayout(ly)

        self.register_grid(self.glista)
        self.restore_video(default_width=self.glista.width_and_vbar() + 200, default_height=640)

        self.wtrain.setVisible(False)
        self.glista.gotop()
        self.glista.setFocus()

    def populate_tree(self):
        self.tree_folders.clear()
        base = self.configuration.paths.folder_base_openings()
        rondo = QTDialogs.rondo_folders()
        root_item = QtWidgets.QTreeWidgetItem([_("Home")])
        root_item.setIcon(0, Iconos.Home())
        root_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, "")
        self.tree_folders.addTopLevelItem(root_item)
        self.add_folders_recursive(root_item, base, "", rondo)
        self.tree_folders.expandAll()
        current_abs = self.configuration.paths.folder_openings()
        if current_abs.startswith(base):
            current_rel = os.path.relpath(current_abs, base)
        else:
            current_rel = ""
        item = self.find_item(self.tree_folders.invisibleRootItem(), current_rel)
        if item:
            self.tree_folders.setCurrentItem(item)

    def add_folders_recursive(self, parent_item, path, rel_path, rondo):
        try:
            li_folders = os.listdir(path)
            li_folders.sort(key=lambda x: x.lower())
            for item in li_folders:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    rel_item = os.path.join(rel_path, item) if rel_path else item
                    child_item = QtWidgets.QTreeWidgetItem([item])
                    child_item.setIcon(0, rondo.otro())
                    child_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, rel_item)
                    parent_item.addChild(child_item)
                    self.add_folders_recursive(child_item, full_path, rel_item, rondo)
        except:
            pass

    def find_item(self, parent, rel_path):
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.data(0, QtCore.Qt.ItemDataRole.UserRole) == rel_path:
                return child
            found = self.find_item(child, rel_path)
            if found:
                return found
        return None

    def on_folder_selected(self, item):
        rel_path = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if rel_path is not None:
            self.configuration.paths.set_folder_openings(rel_path)
            self.configuration.graba()
            self.listaOpenings = OpeningLines.ListaOpenings(True)
            if len(self.listaOpenings) == 0:
                self.wtrain.setVisible(False)
            self.glista.gotop()
            self.glista.refresh()
            if len(self.listaOpenings) > 0:
                self.grid_cambiado_registro(None, 0, None)

    def tr_(self, tipo):
        recno = self.glista.recno()
        op = self.listaOpenings[recno]
        op["TRAIN"] = tipo
        self.resultado = op
        self.finalize()

    def tr_sequential(self):
        self.tr_("sequential")

    def tr_static(self):
        self.tr_("static")

    def tr_positions(self):
        self.tr_("positions")

    def tr_engines(self):
        self.tr_("engines")

    def reiniciar(self):
        self.listaOpenings.reiniciar()
        self.glista.refresh()
        self.glista.gotop()
        if len(self.listaOpenings) == 0:
            self.wtrain.setVisible(False)

    def _update_move(self, target):
        self.listaOpenings.save()
        self.glista.goto(target, 0)
        self.glista.refresh()

    def arriba(self):
        row = self.glista.recno()
        if row > 0:
            lista = self.listaOpenings.lista
            lista[row], lista[row - 1] = lista[row - 1], lista[row]
            self._update_move(row - 1)

    def abajo(self):
        row = self.glista.recno()
        lista = self.listaOpenings.lista
        if row < (len(lista) - 1):
            lista[row], lista[row + 1] = lista[row + 1], lista[row]
            self._update_move(row + 1)

    def grid_mover_filas(self, _grid, li_rows, target_row):
        lic = self.listaOpenings.lista

        # 1. Obtener los objetos/datos que se van a mover
        items_a_mover = [lic[i] for i in li_rows]

        # 2. Borrar las filas originales (en orden inverso para no alterar los índices)
        for i in sorted(li_rows, reverse=True):
            del lic[i]

        # 3. Ajustar el índice de destino si se han borrado elementos antes de él
        borrados_antes = sum(1 for i in li_rows if i < target_row)
        target_row -= borrados_antes

        # 4. Insertar los elementos en la nueva posición
        for item in reversed(items_a_mover):
            lic.insert(target_row, item)

        self._update_move(target_row)

        return True

    def modificar(self):
        recno = self.glista.recno()
        if recno >= 0:
            self.resultado = self.listaOpenings[recno]
        else:
            self.resultado = None
        self.save_video()
        self.accept()

    def grid_doble_click(self, _grid, _row, _obj_column):
        recno = self.glista.recno()
        if recno >= 0:
            self.modificar()

    def new(self):
        si_expl = len(self.listaOpenings) < 4
        if si_expl:
            QTMessages.message_bold(
                self,
                _("In the next dialog box, play the initial fixed moves for your opening."),
            )
        w = WindowOpenings.WOpenings(self, None)
        if w.exec():
            ap = w.resultado()
            pv = ap.a1h8 if ap else ""
            name = ap.tr_name if ap else ""
        else:
            return

        if si_expl:
            QTMessages.message_bold(self, _("Now choose a name for this opening."))

        name = self.get_nombre(name)
        if name:
            file = self.listaOpenings.select_filename(name)
            self.listaOpenings.new(file, pv, name)
            self.resultado = self.listaOpenings[-1]
            self.save_video()
            self.accept()

    def copy(self):
        recno = self.glista.recno()
        if recno >= 0:
            self.listaOpenings.copy(recno)
            self.glista.refresh()

    def get_nombre(self, name):
        new_name = QTMessages.read_simple(self, _("Opening studio name"), _("Name"), name, width=360)
        if new_name:
            new_name = new_name.strip()
        return new_name

    def change(self):
        row = self.glista.recno()
        if row < 0:
            return
        menu = QTDialogs.LCMenu(self)
        menu.opcion(self.change_name, _("Name"), Iconos.Modificar())
        menu.opcion(self.change_firstmoves, _("First moves"), Iconos.Board())
        menu.opcion(self.change_file, _("File"), Iconos.File())
        resp = menu.lanza()
        if resp:
            resp(row)

    def change_name(self, row):
        op = self.listaOpenings[row]
        name = self.get_nombre(op["title"])
        if name:
            self.listaOpenings.change_title(row, name)
            self.glista.refresh()

    def change_firstmoves(self, row):
        op = self.listaOpenings[row]
        previous_pv = op["pv"]
        op_block = OpeningsStd.Opening("")
        op_block.a1h8 = previous_pv
        w = WindowOpenings.WOpenings(self, op_block)
        if not w.exec():
            return
        ap = w.resultado()
        new_pv = ap.a1h8 if ap else ""

        if new_pv == previous_pv:
            return

        dbop = OpeningLines.Opening(self.listaOpenings.filepath(row))
        if not previous_pv.startswith(new_pv):
            # Comprobamos si hay que borrar lineas
            li_remove = dbop.lines_to_remove(new_pv)
            if len(li_remove) > 0:
                message = f"{len(li_remove)} {_('Lines')}"
                if not QTMessages.pregunta(self, f"{_('Are you sure you want to remove %s?')} {message}"):
                    dbop.close()
                    return
                dbop.remove_list_lines(li_remove, f"{previous_pv} -> {new_pv}")

        self.listaOpenings.change_first_moves(row, new_pv, len(dbop))
        dbop.set_basepv(new_pv)
        dbop.close()
        self.glista.refresh()

    def change_file(self, row, new_name=None):
        dict_op = self.listaOpenings[row]
        current_file = dict_op["file"]
        current_path = Util.opj(self.listaOpenings.folder, current_file)
        if not Util.exist_file(current_path):
            self.listaOpenings.reiniciar()
            self.glista.refresh()
            return None
        name_file = current_file[:-4] if new_name is None else new_name
        new_name = QTMessages.read_simple(self, _("File"), _("Name"), name_file, width=360)
        if not new_name:
            return None
        new_name = new_name.strip()
        if new_name.endswith(".opk"):
            new_name = new_name[:-4]
        if new_name == name_file:
            return None
        new_path = Util.opj(os.path.dirname(current_path), f"{new_name}.opk")
        if os.path.isfile(new_path):
            QTMessages.message_error(self, f"{_('This file already exists')}\n{new_name}.opk")
            return self.change_file(row, new_name)
        try:
            shutil.move(current_path, new_path)
        except:
            QTMessages.message_error(self, _("This is not a valid file name"))
            return self.change_file(row, new_name)
        self.listaOpenings.change_file(row, new_path)
        self.glista.refresh()
        return None

    def grid_remove(self):
        li = self.glista.list_selected_recnos()
        if len(li) > 0:
            mens = _("Do you want to delete all selected records?")
            mens += "\n"
            for num, row in enumerate(li, 1):
                mens += f"\n{num}. {self.listaOpenings[row]['title']}"
            if QTMessages.pregunta(self, mens):
                self.wtrain.setVisible(False)
                li.sort(reverse=True)
                for row in li:
                    del self.listaOpenings[row]
                recno = self.glista.recno()
                self.glista.refresh()
                if recno >= len(self.listaOpenings):
                    self.glista.gobottom()

    def grid_num_datos(self, _grid):
        return len(self.listaOpenings)

    def grid_dato(self, _grid, row, obj_column):
        col = obj_column.key
        op = self.listaOpenings[row]
        if col == "TITLE":
            return op["title"]
        elif col == "FILE":
            return op["file"]
        elif col == "NUMLINES":
            return op["lines"]
        elif col == "BASEPV":
            pv = op["pv"]
            if pv:
                p = Game.Game()
                p.read_pv(pv)
                return p.pgn_base_raw()
        return ""

    def grid_cambiado_registro(self, _grid, row, _obj_column):
        ok_ssp = False
        ok_eng = False
        if row >= 0:
            op = self.listaOpenings[row]
            num = op["lines"]
            num = int(num) if num else 0
            ok_ssp = op.get("withtrainings", False) and num > 0
            ok_eng = op.get("withtrainings_engines", False) and num > 0

        if ok_ssp or ok_eng:
            self.wtrain.setVisible(True)
            self.tbtrain.set_action_visible(self.tr_sequential, ok_ssp)
            self.tbtrain.set_action_visible(self.tr_static, ok_ssp)
            self.tbtrain.set_action_visible(self.tr_positions, ok_ssp)
            self.tbtrain.set_action_visible(self.tr_engines, ok_eng)
        else:
            if self.wtrain:
                self.wtrain.setVisible(False)

    def grid_right_button(self, _grid, row, obj_column, _modif):
        if row < 0:
            return
        col = obj_column.key
        if col == "TITLE":
            self.change_name(row)
        elif col == "FILE":
            self.change_file(row)
        elif col == "BASEPV":
            self.change_firstmoves(row)

    def tree_new(self):
        nof = _("New opening folder")
        base = self.configuration.paths.folder_base_openings()
        name = ""
        error = ""
        while True:
            name = QTMessages.read_simple(self, nof, _("Name"), name, mas_info=error, width=260)
            if not name:
                return
            path = Util.opj(base, name.strip())
            if not Util.create_folder(path):
                error = _("Unable to create the folder")
                continue
            self.configuration.paths.set_folder_openings(name)
            self.populate_tree()
            return

    def tree_edit(self):
        base = self.configuration.paths.folder_base_openings()
        current_abs = self.configuration.paths.folder_openings()
        name = os.path.relpath(current_abs, base)
        error = ""
        while True:
            name = QTMessages.read_simple(self, base, _("Name"), name, mas_info=error, width=260)
            if not name:
                return
            path = Util.opj(base, name.strip())
            if not Util.rename_folder(current_abs, path):
                error = _("Unable to create the folder")
                continue
            self.configuration.paths.set_folder_openings(name)
            self.populate_tree()
            return

    def tree_delete(self):
        base = self.configuration.paths.folder_base_openings()
        current_abs = self.configuration.paths.folder_openings()
        if Util.same_path(base, current_abs):
            return
        if self.grid_num_datos(None) > 0:
            return

        if not Util.remove_folder_if_no_subfolders(current_abs):
            QTMessages.message_error(self, _("Unable to delete the folder"))
            return

        self.configuration.paths.set_folder_openings("")
        self.populate_tree()

    def tree_context_menu(self, pos):
        item = self.tree_folders.itemAt(pos)
        if not item:
            return
        self.on_folder_selected(item)
        data = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        is_folder = bool(data)
        has_childrens = self.grid_num_datos(None) > 0

        menu = QTDialogs.LCMenu(self)

        if is_folder:
            menu.opcion("rename", _("Rename"), Iconos.EditVariation())
            menu.separador()
            if not has_childrens:
                menu.opcion("delete", _("Delete"), Iconos.Borrar())
                menu.separador()
        menu.opcion("update", _("Update"), Iconos.Reiniciar())
        menu.separador()
        menu.opcion("direct", _("Direct maintenance"), Iconos.Configurar())
        menu.separador()
        menu.opcion("new", _("New opening folder"), Iconos.NewBoxRoom())
        resp = menu.lanza()
        if resp is None:
            return
        if resp == "rename":
            self.tree_edit()
        elif resp == "delete":
            self.tree_delete()
        elif resp == "new":
            self.tree_new()
        elif resp == "update":
            self.reiniciar()
        elif resp == "direct":
            current_abs = self.configuration.paths.folder_openings()
            Util.startfile(current_abs)

    def handle_tree_drop(self, li_rows, target_rel_path):
        """Manejar drop de opening lines al tree de carpetas
        
        Args:
            li_rows: Lista de índices de filas seleccionadas en el grid
            target_rel_path: Ruta relativa de la carpeta destino
        """
        if not li_rows or target_rel_path is None:
            return

        # Obtener información de los openings a copiar/mover
        items_to_move = [self.listaOpenings[i] for i in li_rows if i < len(self.listaOpenings)]
        if not items_to_move:
            return

        base_path = self.configuration.paths.folder_base_openings()
        target_abs_path = Util.opj(base_path, target_rel_path) if target_rel_path else base_path
        source_path = self.listaOpenings.folder
        if Util.same_path(target_abs_path, source_path):
            return

        # Mostrar menú para elegir copiar o mover
        menu = QTDialogs.LCMenu(self)
        menu.opcion("copy", _("Copy") + " -> " + target_rel_path, Iconos.Copiar())
        menu.separador()
        menu.opcion("move", _("Move") + " -> " + target_rel_path, Iconos.Mover())
        resp = menu.lanza()

        if not resp:
            return

        # Ejecutar la acción
        if resp == "copy":
            self._copy_to_folder(items_to_move, target_rel_path, li_rows)
        elif resp == "move":
            self._move_to_folder(items_to_move, target_rel_path, li_rows)

    def _copy_to_folder(self, items, target_rel_path, li_rows):
        """Copiar opening lines a otra carpeta"""
        try:
            base_path = self.configuration.paths.folder_base_openings()
            target_abs_path = Util.opj(base_path, target_rel_path) if target_rel_path else base_path
            source_path = self.listaOpenings.folder

            # Copiar cada archivo .opk
            for item in items:
                source_file = Util.opj(source_path, item["file"])
                if os.path.isfile(source_file):
                    # Generar nombre único en destino si es necesario
                    target_file = Util.opj(target_abs_path, item["file"])
                    if os.path.isfile(target_file):
                        # Generar nombre único
                        base_name = item["file"][:-4]  # Sin .opk
                        counter = 1
                        while os.path.isfile(Util.opj(target_abs_path, f"{base_name}-{counter}.opk")):
                            counter += 1
                        target_file = Util.opj(target_abs_path, f"{base_name}-{counter}.opk")

                    shutil.copy2(source_file, target_file)

            # Refrescar listas en origen y destino
            self.listaOpenings.reiniciar()
            self.glista.refresh()
            self.glista.gotop()

            # Refrescar la lista del destino
            self.configuration.paths.set_folder_openings(target_rel_path)
            dest_lista = OpeningLines.ListaOpenings(True)
            dest_lista.reiniciar()

            # Volver a la carpeta original
            self.configuration.paths.set_folder_openings(
                os.path.relpath(self.listaOpenings.folder, base_path) if self.listaOpenings.folder.startswith(
                    base_path) else ""
            )
            self.listaOpenings = OpeningLines.ListaOpenings(True)
            self.glista.refresh()

        except Exception as e:
            QTMessages.message_error(self, f"{_('Error copying opening lines')}\n{str(e)}")

    def _move_to_folder(self, items, target_rel_path, li_rows):
        """Mover opening lines a otra carpeta"""
        try:
            base_path = self.configuration.paths.folder_base_openings()
            target_abs_path = Util.opj(base_path, target_rel_path) if target_rel_path else base_path
            source_path = self.listaOpenings.folder

            # Mover cada archivo .opk
            for item in items:
                source_file = Util.opj(source_path, item["file"])
                if os.path.isfile(source_file):
                    target_file = Util.opj(target_abs_path, item["file"])
                    if os.path.isfile(target_file):
                        # Generar nombre único en destino si es necesario
                        base_name = item["file"][:-4]  # Sin .opk
                        counter = 1
                        while os.path.isfile(Util.opj(target_abs_path, f"{base_name}-{counter}.opk")):
                            counter += 1
                        target_file = Util.opj(target_abs_path, f"{base_name}-{counter}.opk")

                    shutil.move(source_file, target_file)

            # Refrescar listas en origen y destino
            self.listaOpenings.reiniciar()
            self.glista.refresh()
            self.glista.gotop()

            # Refrescar la lista del destino
            self.configuration.paths.set_folder_openings(target_rel_path)
            dest_lista = OpeningLines.ListaOpenings(True)
            dest_lista.reiniciar()

            # Volver a la carpeta original
            self.configuration.paths.set_folder_openings(
                os.path.relpath(self.listaOpenings.folder, base_path) if self.listaOpenings.folder.startswith(
                    base_path) else ""
            )
            self.listaOpenings = OpeningLines.ListaOpenings(True)
            self.glista.refresh()

            QTMessages.message_information(self, _("Opening lines moved successfully"))
        except Exception as e:
            QTMessages.message_error(self, f"{_('Error moving opening lines')}\n{str(e)}")

    def closeEvent(self, event):  # Cierre con X
        self.save_video()

    def finalize(self):
        self.save_video()
        self.accept()


class WStaticTraining(LCDialog.LCDialog):
    def __init__(self, procesador, dbop):
        self.training = dbop.training()
        self.ligames = self.training["LIGAMES_STATIC"]
        self.num_games = len(self.ligames)
        self.elems_fila = 10
        if self.num_games < self.elems_fila:
            self.elems_fila = self.num_games
        self.num_filas = (self.num_games - 1) / self.elems_fila + 1
        self.seleccionado = None

        titulo = f"{_('Opening lines')} - {_('Static training')}"

        extparam = f"openlines_static_{dbop.path_file}"

        LCDialog.LCDialog.__init__(self, procesador.main_window, titulo, Iconos.TrainStatic(), extparam)

        lb = Controles.LB(self, dbop.gettitle())
        lb.set_background("#BDDBE8").align_center().set_font_type(puntos=14)

        # Toolbar
        tb = QTDialogs.LCTB(self)
        tb.new(_("Close"), Iconos.MainMenu(), self.finalize)

        # Lista
        ancho = 42
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("FILA", "", 36, align_center=True)
        for x in range(self.elems_fila):
            o_columns.nueva(
                f"COL{x}",
                f"{x + 1}",
                ancho,
                align_center=True,
                edicion=Delegados.PmIconosWeather(),
            )

        self.grid = Grid.Grid(self, o_columns, heigh_row=ancho, background="white")
        self.grid.setAlternatingRowColors(False)
        self.grid.font_type(puntos=10, peso=500)
        n_ancho_pgn = self.grid.fix_min_width()

        ly = Colocacion.V().control(lb).control(tb).control(self.grid)
        self.setLayout(ly)

        alto = int(self.num_filas * ancho + 146)
        self.restore_video(with_tam=True, default_height=alto, default_width=n_ancho_pgn)

    def finalize(self):

        self.save_video()
        self.reject()

    def grid_num_datos(self, _grid):
        return self.num_filas

    def grid_dato(self, _grid, row, obj_column):
        col = obj_column.key
        if col == "FILA":
            return f"{row}"
        elif col.startswith("COL"):
            num = row * self.elems_fila + int(col[3:])
            if num >= self.num_games:
                return None
            game = self.ligames[num]
            sinerror = game["NOERROR"]
            return str(sinerror) if sinerror < 4 else "4"
        return None

    def grid_doble_click(self, _grid, row, obj_column):
        col = obj_column.key
        if col.startswith("COL"):
            num = row * self.elems_fila + int(col[3:])
            if num >= self.num_games:
                return
            self.seleccionado = num
            self.save_video()
            self.accept()


def select_static_line(procesador, dbop):
    w = WStaticTraining(procesador, dbop)
    w.exec()
    return w.seleccionado


def opening_lines(procesador):
    w = WOpeningLines(procesador)
    return w.resultado if w.exec() else None


def select_line(owner):
    path = Code.configuration.paths.folder_base_openings()
    is_openings = False
    entry: os.DirEntry
    menu = QTDialogs.LCMenuRondo(owner)
    for entry in os.scandir(path):
        if entry.is_dir():
            path_ini = Util.opj(entry.path, "openinglines.pk")
            lista = Util.restore_pickle(path_ini, [])
            if lista:
                is_openings = True
                submenu = menu.submenu(entry.name, Iconos.FolderAnil())
                for dic in lista:
                    dic["folder"] = entry.name
                    submenu.opcion(dic, dic["title"])

    path_ini = Util.opj(path, "openinglines.pk")
    lista = Util.restore_pickle(path_ini, [])
    if lista:
        is_openings = True
        for dic in lista:
            menu.opcion(dic, dic["title"])
    if is_openings:
        return menu.lanza()

    return None
