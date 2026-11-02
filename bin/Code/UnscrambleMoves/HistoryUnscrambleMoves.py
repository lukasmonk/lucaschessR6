import Code
from Code.QT import Colocacion, Columnas, Grid, Iconos, LCDialog, QTDialogs, QTMessages
from Code.SQL import Base

TABLE = "Results"
FIELDS = "DATE_TIME,LEVEL_REACHED,ERRORS"
KEY_VIDEO = "unscramblemoveshistory"


class UnscrambleMovesHistorial:
    """Results of the "Unscramble the moves" training.

    LEVEL_REACHED is the level that was being played and ERRORS how many times the sequence was
    distributed wrongly along the run.
    """

    def __init__(self):
        self.db = Base.DBBase(Code.configuration.paths.file_unscramble_moves())
        if not self.db.existeTabla(TABLE):
            self.create_table()
        self.dbf = self.db.dbf(TABLE, FIELDS, orden="ID DESC")
        self.dbf.leer()

    def create_table(self):
        table = Base.TablaBase(TABLE)
        table.nuevoCampo("ID", "INTEGER", primaryKey=True, autoInc=True)
        table.nuevoCampo("DATE_TIME", "TEXT", notNull=True)
        table.nuevoCampo("LEVEL_REACHED", "INTEGER", notNull=True)
        table.nuevoCampo("ERRORS", "INTEGER", notNull=True)
        self.db.generarTabla(table)

    def close(self):
        if self.dbf is not None:
            self.dbf.cerrar()
            self.dbf = None
        self.db.cerrar()

    def __len__(self):
        return self.dbf.reccount()

    def __getitem__(self, position):
        """(date and time, level reached, errors) of a record, the most recent one first."""
        if not 0 <= position < len(self):
            raise IndexError(position)
        self.dbf.goto(position)
        record = self.dbf.registroActual()
        return record.DATE_TIME, record.LEVEL_REACHED, record.ERRORS

    def append(self, date_time, level_reached, errors):
        record = self.dbf.baseRegistro()
        record.DATE_TIME = date_time
        record.LEVEL_REACHED = level_reached
        record.ERRORS = errors
        self.dbf.insertar(record)

    def remove_list_recnos(self, li_recnos):
        self.dbf.remove_list_recnos(li_recnos)
        self.dbf.pack()
        self.dbf.leer()


def save_result(date_time: str, level_reached: int, errors: int) -> None:
    historial = UnscrambleMovesHistorial()
    try:
        historial.append(date_time, level_reached, errors)
    finally:
        historial.close()


class WUnscrambleMovesHistory(LCDialog.LCDialog):
    DATE_TIME = 0
    LEVEL_REACHED = 1
    ERRORS = 2
    RECNO = 3

    def __init__(self, parent):
        LCDialog.LCDialog.__init__(
            self,
            parent,
            _("History"),
            Iconos.UnscrambleMoves(),
            KEY_VIDEO,
        )
        self.li_regs = self.read_records()
        self.li_orders = [False, True, False]

        columns = Columnas.ListaColumnas()
        columns.nueva("POS", _("N."), 30, align_center=True)
        columns.nueva("DATE_TIME", _("Date"), 170, align_center=True)
        columns.nueva("LEVEL_REACHED", _("Level"), 120, align_center=True)
        columns.nueva("ERRORS", _("Errors"), 100, align_center=True)
        self.grid = Grid.Grid(self, columns, complete_row_select=True, select_multiple=True)
        self.grid.fix_min_width()

        li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.finalize),
            None,
            (_("Remove"), Iconos.Borrar(), self.remove_selected),
            None,
        )
        self.tb = QTDialogs.LCTB(self, li_acciones)

        layout = Colocacion.V().control(self.tb).control(self.grid).margen(3)
        self.setLayout(layout)
        self.register_grid(self.grid)
        self.restore_video(default_width=500, default_height=360)
        self.grid.gotop()

    def read_records(self):
        historial = UnscrambleMovesHistorial()
        try:
            data = [historial[position] for position in range(len(historial))]
            if len(data) == 0:
                return data

            # 1. Añadir la posición original (índice) a cada elemento: (*item, posicion_original)
            data_con_posicion = [(*item, i) for i, item in enumerate(data)]

            # 2. Ordenar de mejor a peor resultado:
            # - Segundo número (índice 1) de mayor a menor.
            # - Tercer número (índice 2) de menor a mayor (por eso usamos -x[2]).
            # Usamos `reverse=True` para que el mayor valor de la clave vaya primero.
            resultado = sorted(data_con_posicion, key=lambda x: (x[self.LEVEL_REACHED], -x[self.ERRORS]), reverse=True)
            return resultado
        finally:
            historial.close()

    def grid_num_datos(self, _grid):
        return len(self.li_regs)

    def get_index(self, str_key):
        return {"DATE_TIME": self.DATE_TIME, "LEVEL_REACHED": self.LEVEL_REACHED, "ERRORS": self.ERRORS}[str_key]

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        if key == "POS":
            return str(row + 1)
        index = self.get_index(key)
        return self.li_regs[row][index]

    def grid_doubleclick_header(self, _grid, obj_column):
        key = obj_column.key
        if key == "POS":
            return
        index = self.get_index(key)

        reverse = not self.li_orders[index]
        self.li_orders[index] = reverse

        self.li_regs = sorted(self.li_regs, key=lambda x: (x[index], x[self.LEVEL_REACHED], -x[self.ERRORS]),
                           reverse=reverse)
        self.grid.refresh()
        self.grid.gotop()

    def remove_selected(self):
        li_recnos = self.grid.list_selected_recnos()
        if not li_recnos:
            return
        if not QTMessages.pregunta(self, _("Do you want to delete all selected records?")):
            return
        li_recnos = [self.li_regs[r][self.RECNO] for r in li_recnos]
        historial = UnscrambleMovesHistorial()
        try:
            historial.remove_list_recnos(li_recnos)
        finally:
            historial.close()

        self.li_regs = self.read_records()
        self.grid.refresh()
        self.grid.gotop()

    def finalize(self):
        self.accept()

    def closeEvent(self, event):
        self.save_video()
        event.accept()


def show_history(parent):
    WUnscrambleMovesHistory(parent).exec()
