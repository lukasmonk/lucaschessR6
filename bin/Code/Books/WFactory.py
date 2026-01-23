import datetime
import os
import os.path
import shutil

import Code
from Code.Z import Util
from Code.Books import DBPolyglot, WPolyglot
from Code.QT import Colocacion, Columnas, Grid, Iconos, LCDialog, QTDialogs, QTMessages


class WFactoryPolyglots(LCDialog.LCDialog):
    def __init__(self, procesador):
        self.procesador = procesador
        self.configuration = Code.configuration
        self.resultado = None

        self.index_polyglots = DBPolyglot.IndexPolyglot()

        self.list_db = self.index_polyglots.list()

        LCDialog.LCDialog.__init__(
            self,
            procesador.main_window,
            _("Polyglot book factory"),
            Iconos.FactoryPolyglot(),
            "factorypolyglots",
        )

        o_columnas = Columnas.ListaColumnas()
        o_columnas.nueva("NAME", _("Name"), 200)
        o_columnas.nueva("MTIME", _("Last modification"), 160, align_center=True)
        o_columnas.nueva("SIZE", _("Moves"), 100, align_right=True)
        self.glista = Grid.Grid(self, o_columnas, complete_row_select=True, select_multiple=True)

        li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.finalize),
            None,
            (_("Edit"), Iconos.Modificar(), self.edit),
            None,
            (_("New"), Iconos.Nuevo(), self.new),
            None,
            (_("Copy"), Iconos.Copiar(), self.copy),
            None,
            (_("Rename"), Iconos.Modificar(), self.renombrar),
            None,
            (_("Remove"), Iconos.Borrar(), self.borrar),
            None,
            (_("Update"), Iconos.Reiniciar(), self.update),
            None,
        )
        tb = QTDialogs.LCTB(self, li_acciones)

        ly = Colocacion.V().control(tb).control(self.glista).margen(4)
        self.setLayout(ly)

        self.register_grid(self.glista)
        self.restore_video(default_width=self.glista.width_columns_displayables() + 20, default_height=324)

        self.glista.gotop()

    def edit(self):
        recno = self.glista.recno()
        if recno >= 0:
            self.run_edit(self.list_db[recno]["FILENAME"])

    def grid_doble_click(self, _grid, _row, _o_columna):
        self.edit()

    def run_edit(self, filename):
        self.resultado = Util.opj(Code.configuration.paths.folder_polyglots_factory(), filename)
        self.save_video()
        self.accept()

    def get_new_path(self, name):
        while True:
            name = QTMessages.read_simple(self, _("New polyglot book"), _("Name"), name)
            if name:
                path = Util.opj(self.configuration.paths.folder_polyglots_factory(), f"{name}.lcbin")
                if os.path.isfile(path):
                    QTMessages.message_error(self, f"{_('This file already exists')}\n{path}")
                else:
                    return os.path.realpath(path)
            else:
                return None

    def new(self):
        if path := self.get_new_path(""):
            with DBPolyglot.DBPolyglot(path):  # To create the file
                pass
            self.update(soft=True)
            self.run_edit(path)

    @staticmethod
    def path_db(filename):
        return Util.opj(Code.configuration.paths.folder_polyglots_factory(), filename)

    def copy(self):
        recno = self.glista.recno()
        if recno >= 0:
            if path := self.get_new_path(self.list_db[recno]["FILENAME"][:-6]):
                folder = Code.configuration.paths.folder_polyglots_factory()
                shutil.copy(
                    self.path_db(self.list_db[recno]["FILENAME"]),
                    Util.opj(folder, path),
                )
                self.update()
                self.glista.refresh()

    def renombrar(self):
        recno = self.glista.recno()
        if recno >= 0:
            reg = self.list_db[recno]
            if path := self.get_new_path(reg["FILENAME"][:-6]):
                os.rename(self.path_db(reg["FILENAME"]), path)
                self.update()
                self.glista.refresh()

    def borrar(self):
        li = self.glista.list_selected_recnos()
        if len(li) > 0:
            mens = _("Do you want to delete all selected records?")
            mens += "\n"
            for num, row in enumerate(li, 1):
                mens += "\n%d. %s" % (num, self.list_db[row]["FILENAME"][:-6])
            if QTMessages.pregunta(self, mens):
                li.sort(reverse=True)
                for row in li:
                    Util.remove_file(self.path_db(self.list_db[row]["FILENAME"]))
                self.update(soft=True)
                self.glista.refresh()

    def grid_num_datos(self, _grid):
        return len(self.list_db)

    def grid_dato(self, _grid, row, o_columna):
        col = o_columna.key

        reg = self.list_db[row]
        if col == "MTIME":
            return Util.local_date_time(datetime.datetime.fromtimestamp(reg["MTIME"]))
        elif col == "NAME":
            return reg["FILENAME"][:-6]
        elif col == "SIZE":
            return f"{reg['SIZE']:,}".replace(",", ".")
        return None

    def update(self, soft=False):
        if soft:
            self.list_db = self.index_polyglots.update_soft()
        else:
            self.list_db = self.index_polyglots.update_hard(self)
        self.glista.refresh()
        self.glista.gotop()

    def closeEvent(self, event):  # Cierre con X
        self.save_video()

    def finalize(self):
        self.save_video()
        self.accept()


def polyglots_factory(procesador):
    w = WFactoryPolyglots(procesador)
    return w.resultado if w.exec() else None


def edit_polyglot(procesador, path_dbbin):
    w = WPolyglot.WPolyglot(procesador.main_window, Code.configuration, path_dbbin)
    w.exec()
