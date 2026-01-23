from Code.QT import Colocacion, Columnas, Controles, Delegados, Grid, Iconos, LCDialog, QTDialogs


class WShortcuts(LCDialog.LCDialog):
    def __init__(self, shortcuts):

        LCDialog.LCDialog.__init__(self, shortcuts.wparent, _("Shortcuts"), Iconos.Atajos(), "shortcuts2")

        self.shortcuts = shortcuts

        tb = QTDialogs.LCTB(self)
        tb.new(_("Close"), Iconos.MainMenu(), self.finalize)
        tb.new(_("Play"), Iconos.Libre(), self.play_menu, sep=False)
        tb.new(_("Train"), Iconos.Entrenamiento(), self.train_menu, sep=False)
        tb.new(_("Compete"), Iconos.NuevaPartida(), self.compete_menu, sep=False)
        tb.new(_("Tools"), Iconos.Tools(), self.tools_menu, sep=False)
        tb.new(_("Engines"), Iconos.Engines(), self.engines_menu, sep=False)
        tb.new(_("Options"), Iconos.Options(), self.options_menu, sep=False)
        tb.new(_("Information"), Iconos.Informacion(), self.information_menu)
        tb.new(_("Remove"), Iconos.Borrar(), self.remove)
        tb.new(_("Up"), Iconos.Arriba(), self.go_up, sep=False)
        tb.new(_("Down"), Iconos.Abajo(), self.go_down)

        # Lista
        o_columnas = Columnas.ListaColumnas()
        o_columnas.nueva("KEY", _("Key"), 70, align_center=True)
        o_columnas.nueva("MENU", _("Menu"), 90, align_center=True)
        o_columnas.nueva("OPTION", _("Option"), 300)
        o_columnas.nueva(
            "LABEL",
            _("Label"),
            300,
            edicion=Delegados.LineaTextoUTF8(is_password=False),
            is_editable=True,
        )

        self.grid = Grid.Grid(self, o_columnas, complete_row_select=True, is_editable=True)
        self.grid.setMinimumWidth(self.grid.width_columns_displayables() + 20)
        f = Controles.FontType(puntos=10, peso=75)
        self.grid.set_font(f)

        layout = Colocacion.V().control(tb).control(self.grid).margen(3)
        self.setLayout(layout)

        self.restore_video(with_tam=True)

        self.grid.gotop()

    def finalize(self):
        self.save_video()
        self.accept()

    def select_option(self, key_menu):
        menu_gen = self.shortcuts.get_txtmenu(key_menu)
        resp = menu_gen.launch()
        if resp is not None:
            label = menu_gen.locate_key(resp).label
            self.shortcuts.add_shortcut(key_menu, resp, label)
            self.save()
            self.grid.refresh()

    def play_menu(self):
        self.select_option("play")

    def train_menu(self):
        self.select_option("train")

    def compete_menu(self):
        self.select_option("compete")

    def tools_menu(self):
        self.select_option("tools")

    def engines_menu(self):
        self.select_option("engines")

    def options_menu(self):
        self.select_option("options")

    def information_menu(self):
        self.select_option("information")

    def grid_num_datos(self, _grid):
        return len(self.shortcuts.li_shortcuts)

    def grid_dato(self, _grid, row, obj_column):
        column = obj_column.key
        if column == "KEY":
            return "%s %d" % (_("ALT"), row + 1) if row < 9 else ""
        return self.shortcuts.get_grid_column(row, column)

    def grid_setvalue(self, _grid, row, _obj_column, valor):
        valor = valor.strip()
        if valor:
            shortcut = self.shortcuts.li_shortcuts[row]
            shortcut.set_label(valor)
            self.save()

    def grid_doble_click(self, _grid, row, _obj_column):
        if row >= 0:
            shortcut = self.shortcuts.li_shortcuts[row]
            self.finalize()
            self.shortcuts.lauch_shortcut(shortcut)

    def save(self):
        self.shortcuts.save()
        self.grid.refresh()

    def remove(self):
        row = self.grid.recno()
        if row >= 0:
            self.shortcuts.remove(row)
            self.save()

    def go_up(self):
        row = self.grid.recno()
        if row >= 1:
            self.shortcuts.go_up(row)
            self.grid.goto(row - 1, 0)
            self.save()

    def go_down(self):
        row = self.grid.recno()
        if row < len(self.shortcuts.li_shortcuts) - 1:
            self.shortcuts.go_down(row)
            self.grid.goto(row + 1, 0)
            self.save()
