from typing import Optional

from Code.Leitner import Leitner, WEditLeitner, WShowLeitner
from Code.QT import Colocacion, Columnas, Controles, Grid, Iconos, LCDialog, QTMessages
from Code.Z import Util


class WLeitner(LCDialog.LCDialog):
    result_recno: Optional[int]

    def __init__(self, main_window):
        title = _("Tactics with the Leitner method")
        icon = Iconos.Leitner()

        LCDialog.LCDialog.__init__(self, main_window, title, icon, "LeitnerTactics4")

        self.db = Leitner.LeitnerDB()

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("REFERENCE", _("Reference"), 240)
        o_columns.nueva("START", _("Start date"), 120, align_center=True)
        o_columns.nueva("END", _("End date"), 120, align_center=True)
        o_columns.nueva("PUZZLES", _("Num. puzzles"), 100, align_center=True)
        o_columns.nueva("SUCCESS", _("Success"), 100, align_center=True)
        o_columns.nueva("ERRORS", _("Errors"), 100, align_center=True)

        self.grid = Grid.Grid(self, o_columns, complete_row_select=True, select_multiple=True)
        self.grid.setMinimumWidth(self.grid.width_columns_displayables() + 20)

        # Toolbar
        self.tb = Controles.TBrutina(self)
        self.set_toolbar()

        # Colocamos
        ly_tb = Colocacion.H().control(self.tb).margen(0)
        ly = Colocacion.V().otro(ly_tb).control(self.grid).margen(3)

        self.setLayout(ly)

        self.register_grid(self.grid)
        self.restore_video()

        self.grid.gotop()

    def grid_num_datos(self, _grid):
        return len(self.db)

    def grid_doble_click(self, _grid, row, _obj_column):
        if row >= 0:
            self.run_selected()

    def grid_dato(self, _grid, row, obj_column):
        col = obj_column.key
        leitner = self.db.get_leitner(row)
        if leitner is None:
            return ""

        if col == "REFERENCE":
            return leitner.reference

        if col == "START":
            return Util.local_date_time(leitner.init_date) if leitner.init_date else "..."

        if col == "END":
            return Util.local_date_time(leitner.end_date) if leitner.end_date else "..."

        if col == "PUZZLES":
            return str(len(leitner.dic_regs))

        if col == "ERRORS":
            return str(sum(reg.wrong for reg in leitner.dic_regs.values()))

        if col == "SUCCESS":
            return str(sum(reg.right for reg in leitner.dic_regs.values()))

        return ""

    def finalize(self):
        self.save_video()
        self.reject()

    def create_training(self):
        leitner = Leitner.Leitner()
        w = WEditLeitner.WEditLeitner(self, leitner)
        if not w.exec():
            return
        self.db.add_leitner(w.leitner_work)
        self.grid.gotop()
        self.grid.refresh()

    def borrar(self):
        li = self.grid.list_selected_recnos()
        if len(li) > 0:
            if QTMessages.pregunta(self, _("Do you want to delete all selected records?")):
                for pos in sorted(li, reverse=True):
                    self.db.rem_leitner(pos)
        self.grid.gotop()
        self.grid.refresh()

        self.set_toolbar()

    def set_toolbar(self):
        self.tb.clear()
        self.tb.new(_("Close"), Iconos.MainMenu(), self.finalize)
        self.tb.new(_("New"), Iconos.Nuevo(), self.create_training)
        if self.grid.reccount():
            self.tb.new(_("Copy"), Iconos.Copiar(), self.copy)
            self.tb.new(_("Remove"), Iconos.Borrar(), self.borrar)

    def copy(self):
        row = self.grid.recno()
        if row < 0:
            return
        leitner = self.db.get_leitner(row)
        leitner_new = leitner.clone()
        leitner_new.zap()
        self.db.append(leitner_new)
        self.grid.refresh()

    def finalizar(self, accept: bool):
        self.db.close()
        self.save_video()
        if accept:
            self.result_recno = self.grid.recno()
            self.accept()
        else:
            self.result_recno = None
            self.reject()

    def run_selected(self):
        row = self.grid.recno()
        if row < 0:
            return
        leitner = self.db.get_leitner(row)
        if leitner.check_session():
            self.db.set_leitner(row, leitner)
        w = WShowLeitner.WShowLeitner(self, leitner)
        if w.exec():
            self.finalizar(True)

    def closeEvent(self, arg__1, /):
        self.finalizar(False)




