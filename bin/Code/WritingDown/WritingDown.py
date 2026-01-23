import Code
from Code.Base import Game
from Code.QT import Colocacion, Columnas, Grid, Iconos, LCDialog, QTDialogs, QTMessages
from Code.SQL import UtilSQL


class WritingDown(LCDialog.LCDialog):
    def __init__(self, procesador):
        self.procesador = procesador
        self.configuration = Code.configuration
        self.db = UtilSQL.DictSQL(self.configuration.paths.file_writing_down())
        self.lista = self.db.keys(True, True)
        self.resultado = None

        LCDialog.LCDialog.__init__(
            self,
            self.procesador.main_window,
            _("Writing down moves of a game"),
            Iconos.Write(),
            "annotateagame",
        )

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("DATE", _("Date"), 110)
        o_columns.nueva("COLOR", _("Color"), 80, align_center=True)
        o_columns.nueva("GAME", _("Game"), 280)
        o_columns.nueva("MOVES", _("Moves"), 80, align_center=True)
        o_columns.nueva("TIME", _("Average time"), 80, align_center=True)
        o_columns.nueva("ERRORS", _("Errors"), 80, align_center=True)
        o_columns.nueva("HINTS", _("Hints"), 80, align_center=True)
        o_columns.nueva("SUCCESS", _("Success"), 90, align_center=True)
        self.glista = Grid.Grid(self, o_columns, complete_row_select=True, select_multiple=True)

        tb = QTDialogs.LCTB(self)
        tb.new(_("Close"), Iconos.MainMenu(), self.finalize)
        tb.new(_("New"), Iconos.Nuevo(), self.new)
        tb.new(_("Repeat"), Iconos.Copiar(), self.repetir)
        tb.new(_("Remove"), Iconos.Borrar(), self.borrar)

        ly = Colocacion.V().control(tb).control(self.glista).margen(4)

        self.setLayout(ly)

        self.register_grid(self.glista)
        self.restore_video(default_width=self.glista.width_columns_displayables() + 20)
        self.glista.gotop()

    def grid_doble_click(self, grid, row, obj_column):
        self.repetir()

    def repetir(self):
        recno = self.glista.recno()
        if recno >= 0:
            registro = self.db[self.lista[recno]]
            self.haz(registro["PC"])

    def new(self):
        self.haz(None)

    def haz(self, game_saved):
        if game_saved:
            game = Game.Game()
            game.restore(game_saved)
        else:
            game = None
        if_white_below = QTDialogs.white_or_black(self, False)
        if if_white_below is None:
            return
        self.resultado = game, if_white_below
        self.save_video()
        self.db.close()
        self.accept()

    def borrar(self):
        li = self.glista.list_selected_recnos()
        if len(li) > 0:
            mens = _("Do you want to delete all selected records?")
            if QTMessages.pregunta(self, mens):
                for row in li:
                    del self.db[self.lista[row]]
                recno = self.glista.recno()
                self.glista.refresh()
                self.lista = self.db.keys(True, True)
                if recno >= len(self.lista):
                    self.glista.gobottom()

    def grid_num_datos(self, grid):
        return len(self.lista)

    def game(self, reg) -> Game.Game:
        if isinstance(reg["PC"], Game.Game):
            game = reg["PC"]
        else:
            game = Game.Game()
            game.restore(reg["PC"])
        return game

    def grid_dato(self, grid, row, obj_column):
        col = obj_column.key
        reg = self.db[self.lista[row]]
        if not reg:
            return ""
        if col == "DATE":
            return self.lista[row]
        elif col == "GAME":
            return self.game(reg).titulo("DATE", "EVENT", "WHITE", "BLACK", "RESULT")
        elif col == "MOVES":
            total = reg.get("TOTAL_MOVES", len(self.game(reg)))
            moves = reg["MOVES"]
            if total == moves:
                return str(total)
            else:
                return "%d/%d" % (moves, total)
        elif col == "TIME":
            return f"{reg['TIME']:0.2f}\""
        elif col == "HINTS":
            return str(reg["HINTS"])
        elif col == "ERRORS":
            return str(reg["ERRORS"])
        elif col == "SUCCESS":
            err = int(reg["ERRORS"]) if reg["ERRORS"] else 0
            hin = int(reg["HINTS"]) if reg["HINTS"] else 0
            nmv = int(reg["MOVES"]) if reg["MOVES"] else None
            return f"{100.0 - (err + hin) * 100 / nmv:0.02f}%" if nmv else ""
        elif col == "COLOR":
            return _("White") if reg["COLOR"] else _("Black")

    def closeEvent(self, event):  # Cierre con X
        self.db.close()
        self.save_video()

    def finalize(self):
        self.db.close()
        self.save_video()
        self.reject()
