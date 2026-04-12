import Code
from PySide6 import QtWidgets

from Code.QT import Colocacion, Controles, Iconos, LCDialog, QTDialogs, ScreenUtils


class WExportPGN(LCDialog.LCDialog):
    def __init__(self, w_parent, db_games, li_sel):
        LCDialog.LCDialog.__init__(self, w_parent, _("Export"), Iconos.Databases(), "export_pgn")

        self.db_games = db_games
        self.w_parent = w_parent
        self.li_sel = li_sel
        self.total = db_games.reccount()
        self.n_selected = len(li_sel)

        self._create_ui()

    def _create_ui(self):
        ly = Colocacion.V()

        # Toolbar
        tb = QTDialogs.LCTB(self)
        tb.new(_("Export"), Iconos.Aceptar(), self.exportar)
        tb.new(_("Cancel"), Iconos.Cancelar(), self.reject)
        ly.control(tb)
        ly.espacio(15)

        # ==== SECCIÓN 1: FORMATO ====
        gb_format = self._create_format_section()
        ly.control(gb_format)
        ly.espacio(15)

        # ==== SECCIÓN 2: SELECCIÓN ====
        gb_selection = self._create_selection_section()
        ly.control(gb_selection)

        ly.espacio(10)
        ly.relleno()

        self.setLayout(ly)
        self.setMinimumWidth(400)
        ScreenUtils.shrink(self)

    def _create_format_section(self):
        """Crea la sección de formato de exportación."""
        gb = QtWidgets.QGroupBox("1. " + _("Format"))
        Code.configuration.set_property(gb, "title")

        ly = Colocacion.V().margen(10)

        self.rb_pgn = Controles.RB(self, _("To a PGN file"), init_value=True)
        self.rb_pgn.setIcon(Iconos.PGN())

        self.rb_csv = Controles.RB(self, _("To a CSV file"), init_value=False)
        self.rb_csv.setIcon(Iconos.CSV())

        self.rb_db = Controles.RB(self, _("To another database"), init_value=False)
        self.rb_db.setIcon(Iconos.Datos())
        
        ly.control(self.rb_pgn)
        ly.control(self.rb_csv)
        ly.control(self.rb_db)

        if self.db_games.has_positions():
            self.rb_odt = Controles.RB(self, _("To a position sheet in ODF format"), init_value=False)
            self.rb_odt.setIcon(Iconos.ODT())
            ly.control(self.rb_odt)
        else:
            self.rb_odt = None

        gb.setLayout(ly)
        return gb

    def _create_selection_section(self):
        """Crea la sección de selección de registros."""
        gb = QtWidgets.QGroupBox("2. " + _("Selection"))
        Code.configuration.set_property(gb, "title")

        ly = Colocacion.V().margen(10)

        self.rb_all = Controles.RB(
            self, f"{_('All games')} ({self.total})", init_value=(self.n_selected == 0 or self.n_selected > 1)
        )
        self.rb_all.setIcon(Iconos.Datos())

        self.rb_selected = Controles.RB(
            self, f"{_('Only selected games')} ({self.n_selected})", init_value=(self.n_selected == 1)
        )

        ly.control(self.rb_all)
        ly.control(self.rb_selected)

        # Solo mostrar opción de seleccionados si hay selección activa
        if self.n_selected == 0:
            self.rb_selected.setVisible(False)
            self.rb_all.setChecked(True)
        elif self.n_selected > 1:
            self.rb_selected.setChecked(True)
        else:
            self.rb_all.setChecked(True)

        gb.setLayout(ly)
        return gb

    def exportar(self):
        only_selected = self.rb_selected.isChecked() and self.rb_selected.isVisible()

        if self.rb_pgn.isChecked():
            mode = "pgn"
        elif self.rb_csv.isChecked():
            mode = "csv"
        elif self.rb_db.isChecked():
            mode = "db"
        else:
            mode = "odt"

        if only_selected and self.li_sel:
            lista = self.li_sel
        else:
            lista = list(range(self.total))

        self.save_video()
        self.accept()

        if mode == "pgn":
            self.w_parent.tw_export_pgn_list(lista)
        elif mode == "csv":
            self.w_parent.tw_export_csv_list(lista)
        elif mode == "db":
            self.w_parent.tw_export_db_list(lista)
        elif mode == "odt":
            self.w_parent.tw_export_odt_list(lista)
