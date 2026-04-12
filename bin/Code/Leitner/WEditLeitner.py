import os

import Code
from Code.Leitner import Leitner, WMenuFilesLeitner
from Code.QT import Colocacion, Columnas, Controles, Delegados, Grid, Iconos, LCDialog, QTDialogs, QTMessages
from Code.Z import Util


class WEditLeitner(LCDialog.LCDialog):
    def __init__(self, owner, leitner_original: Leitner.Leitner):
        title = _("Tactics with the Leitner method")
        LCDialog.LCDialog.__init__(self, owner, title, Iconos.Leitner(), "editLeitner")

        self.leitner_original = leitner_original
        self.leitner_work = leitner_original.clone()
        self.fns_files = WMenuFilesLeitner.FNSanalyzer()
        self.fns_files.add_folder(Code.folder_resources)
        self.fns_files.add_folder(Code.configuration.paths.folder_userdata())

        tb = QTDialogs.LCTB(self)
        tb.new(_("Accept"), Iconos.Aceptar(), self.aceptar)
        tb.new(_("Cancel"), Iconos.Cancelar(), self.reject)

        lb_reference = Controles.LB(self, f"{_('Reference')}: ")
        self.ed_reference = Controles.ED(self, self.leitner_work.reference)

        lb_elems = Controles.LB(self, f"{_('Elements per session')}: ")
        elems = Util.clamp(self.leitner_work.elems_session, 1, 99)
        self.sb_elems = Controles.SB(self, elems, 1, 99).capture_changes(self.changes)

        lb_min = Controles.LB(self, f"{_('Minimum elements per session')}: ")
        min_val = Util.clamp(self.leitner_work.min_elems_session, 1, elems)
        self.sb_min = Controles.SB(self, min_val, 1, 99).capture_changes(self.changes)

        # Files
        tb_files = QTDialogs.LCTB(self, with_text=False, icon_size=24)
        tb_files.new(_("New"), Iconos.New1(), self.add_file)
        tb_files.new(_("Remove"), Iconos.Borrar(), self.del_file)
        tb_files.new(_("Up"), Iconos.Arriba(), self.up_file)
        tb_files.new(_("Down"), Iconos.Abajo(), self.down_file)

        self.chb_random = Controles.CHB(self, _("Random order"), self.leitner_work.random_order)

        self.lb_total = Controles.LB(self, str(self.leitner_work.num_puzzles()))
        self.lb_total.setStyleSheet("border:1px solid gray;border-radius: 6px;padding:3px;font-weight: bold;")

        o_col = Columnas.ListaColumnas()
        o_col.nueva("FILE", _("File"), 220, align_center=True)
        o_col.nueva("TOTAL", _("Total"), 100, align_center=True)
        o_col.nueva(
            "FROM",
            _("From"),
            100,
            align_center=True,
            edicion=Delegados.LineaTexto(is_integer=True),
        )
        o_col.nueva(
            "TO",
            _("To"),
            100,
            align_center=True,
            edicion=Delegados.LineaTexto(is_integer=True),
        )
        self.grid_files = Grid.Grid(self, o_col, complete_row_select=True, is_editable=True)
        self.grid_files.fix_min_width()
        lyh = Colocacion.H().control(tb_files).relleno().control(self.chb_random).relleno().control(self.lb_total)
        lyh.margen(0)
        ly = Colocacion.V().otro(lyh).control(self.grid_files).margen(0)
        gb_files = Controles.GB(self, "", ly)
        self.grid_files.gotop()

        # Layout
        ly_top = Colocacion.G()
        ly_top.otro(Colocacion.H().control(lb_reference).control(self.ed_reference), 0, 0, 1, 2)
        ly_top.otro(Colocacion.H().control(lb_elems).control(self.sb_elems), 1, 0)
        ly_top.otro(Colocacion.H().control(lb_min).control(self.sb_min), 1, 1)

        layout = Colocacion.V().control(tb).control(gb_files).otro(ly_top).espacio(10)
        self.setLayout(layout)

    def changes(self):
        v = self.sb_elems.valor()
        vmin = self.sb_min.valor()
        if vmin > v:
            self.sb_min.set_value(v)

    def check_errors(self):
        num_puzzles = self.leitner_work.num_puzzles()
        if num_puzzles == 0:
            return _("You must add the files with the puzzles for training")
        if not self.leitner_work.reference:
            return _("You must provide a reference")
        self.leitner_work.elems_session = min(num_puzzles, self.leitner_work.elems_session)
        self.leitner_work.min_elems_session = min(self.leitner_work.elems_session, self.leitner_work.min_elems_session)
        return ""

    def aceptar(self):
        self.leitner_work.reference = self.ed_reference.texto().strip()
        self.leitner_work.random_order = self.chb_random.valor()
        self.leitner_work.elems_session = self.sb_elems.valor()
        self.leitner_work.min_elems_session = self.sb_min.valor()
        self.leitner_work.add_puzzles()
        error = self.check_errors()
        if error:
            QTMessages.message_error(self, error)
            return
        self.accept()

    def add_file(self):
        path_fns = self.fns_files.launch_menu(self)
        if not path_fns:
            return
        # Comprobamos que sean con solución
        num_puzzles = 0
        with Util.OpenCodec(path_fns, "rt") as f:
            for linea in f:
                if linea.count("|") >= 2:
                    num_puzzles += 1
        if num_puzzles == 0:
            QTMessages.message_error(self, _("This file does not contain any solved puzzles"))
            return

        # Importar el fichero FNS dentro del conjunto Leitner y refrescar la tabla
        self.leitner_work.add_file(path_fns, num_puzzles)
        self.grid_files.refresh()
        self.update_total_puzzles()
        ref = self.ed_reference.texto().strip()
        if not ref:
            name = os.path.basename(path_fns)[:-4]
            folder = os.path.dirname(path_fns)
            folder1 = os.path.basename(folder)
            self.ed_reference.set_text(f"{_F(folder1)}: {_F(name)}")

    def grid_num_datos(self, grid):
        return len(self.leitner_work.source_files)

    def grid_dato(self, _grid, row, obj_column):
        col = obj_column.key
        if row >= len(self.leitner_work.source_files):
            return ""
        fns = self.leitner_work.source_files[row]
        if col == "FILE":
            return os.path.basename(getattr(fns, "path", "")) if getattr(fns, "path", "") else ""
        if col == "TOTAL":
            return str(fns.num_fns)
        if col == "FROM":
            return str(fns.from_fns)
        if col == "TO":
            return str(fns.to_fns)
        return ""

    def grid_setvalue(self, grid, row, obj_column, valor):
        if row >= len(self.leitner_work.source_files):
            return
        fns = self.leitner_work.source_files[row]
        try:
            nvalor = int(valor)
        except Exception:
            nvalor = 0
        if obj_column.key == "FROM":
            if nvalor >= fns.num_fns:
                nvalor = 1
            fns.from_fns = max(1, nvalor)
        elif obj_column.key == "TO":
            fns.to_fns = min(max(1, nvalor), fns.num_fns)
        self.update_total_puzzles()

    def del_file(self):
        row = self.grid_files.recno()
        self.leitner_work.source_files.pop(row)
        self.grid_files.refresh()
        self.update_total_puzzles()

    def up_file(self):
        row = self.grid_files.recno()
        if row > 0:
            self.leitner_work.source_files[row], self.leitner_work.source_files[row - 1] = (
                self.leitner_work.source_files[row - 1],
                self.leitner_work.source_files[row],
            )
            self.grid_files.goto(row - 1, 0)
            self.grid_files.refresh()

    def down_file(self):
        row = self.grid_files.recno()
        if 0 <= row < len(self.leitner_work.source_files) - 1:
            self.leitner_work.source_files[row], self.leitner_work.source_files[row + 1] = (
                self.leitner_work.source_files[row + 1],
                self.leitner_work.source_files[row],
            )
            self.grid_files.goto(row + 1, 0)
            self.grid_files.refresh()

    def update_total_puzzles(self):
        self.lb_total.set_text(str(self.leitner_work.num_puzzles()))
