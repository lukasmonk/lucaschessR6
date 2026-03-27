from PySide6 import QtCore, QtWidgets

import Code
from Code.QT import Colocacion, Controles, FormLayout, Iconos, LCDialog, QTDialogs, Piezas


class WReplayParams(LCDialog.LCDialog):
    slider_level: QtWidgets.QSlider
    lb_level: Controles.LB
    dic_checks: dict

    def __init__(self, parent, dvar, with_previous_next):
        titulo = f"{_('Replay game')} - {_('Options')}"
        icono = Iconos.Preferencias()
        extparam = "wreplayparams"
        LCDialog.LCDialog.__init__(self, parent, titulo, icono, extparam)

        self.dvar = dvar
        self.with_previous_next = with_previous_next

        # Toolbar
        tb = QTDialogs.tb_accept_cancel(self)

        # Tabs
        self.tabs = QtWidgets.QTabWidget(self)

        # Tab 1: General
        self.tab_general = self.setup_tab_general()
        self.tabs.addTab(self.tab_general, _("Options"))

        # Tab 2: Transparency
        self.tab_transparency = self.setup_tab_transparency()
        self.tabs.addTab(self.tab_transparency, _("Transparency"))

        # Layout
        layout = Colocacion.V().control(tb).control(self.tabs).margen(5)
        self.setLayout(layout)

        self.restore_video(default_width=460, default_height=500)

    def setup_tab_general(self):
        form = FormLayout.FormLayout(self, "", None)
        form.separador()

        form.seconds(_("Number of seconds between moves"), self.dvar["SECONDS"])
        form.separador()

        form.checkbox(_("Start from first move"), self.dvar["START"])
        form.separador()

        form.checkbox(_("Show PGN"), self.dvar["PGN"])
        form.separador()

        form.checkbox(_("Beep after each move"), self.dvar["BEEP"])
        form.separador()

        form.checkbox(_("Custom sounds"), self.dvar["CUSTOM_SOUNDS"])
        form.separador()

        form.seconds(_("Seconds before first move"), self.dvar["SECONDS_BEFORE"])
        form.separador()

        if self.with_previous_next:
            form.checkbox(_("Replay of the current and following games"), self.dvar["REPLAY_CONTINUOUS"])
            form.separador()

        widget = FormLayout.FormWidget(form.li_gen, parent=self)
        return widget

    def setup_tab_transparency(self):
        widget = QtWidgets.QWidget(self)
        layout = Colocacion.V()

        # Level slider
        ly_level = Colocacion.H().espacio(20)
        ly_level.control(Controles.LB(widget, _("Level") + ":"))
        self.slider_level = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, widget)
        self.slider_level.setMinimum(0)
        self.slider_level.setMaximum(100)
        self.slider_level.setValue(self.dvar["TRANSPARENCY"])

        self.lb_level = Controles.LB(widget, f'{self.slider_level.value()}%').set_width(30).align_center()
        self.slider_level.valueChanged.connect(lambda v: self.lb_level.setText(f'{v}%'))

        ly_level.control(self.slider_level).control(self.lb_level)
        layout.otro(ly_level)

        # Pieces Grid
        grid = Colocacion.G()

        all_pieces = Piezas.AllPieces()

        self.dic_checks = {}
        font = Controles.FontTypeNew(extra_bold=True, point_size_delta=2)

        def add_column(is_white, col):

            label = _("White") if is_white else _("Black")
            pb_title = Controles.PB(widget, f'  {label}').set_font(font)
            pb_title.set_icono(Iconos.Unchecked())
            pb_title.last_click = False
            grid.controlc(pb_title, 0, col, 1, 2)

            pieces_order = "PNBRQK"
            row = 1

            li_checks = []
            for pz_code in pieces_order:
                pz_key = f"{pz_code.upper()}_{'WHITE' if is_white else 'BLACK'}"

                # Piece Icon
                pz_char = pz_code if is_white else pz_code.lower()
                icon = all_pieces.default_icon(pz_char, 32)
                lb_icon = Controles.LB(widget).put_image(icon.pixmap(32, 32))

                cb = Controles.CHB(widget, "", self.dvar[pz_key])
                grid.controld(lb_icon, row, col)
                grid.control(cb, row, col + 1)

                self.dic_checks[pz_key] = cb
                li_checks.append(cb)
                row += 1

            def toggle_all():
                last_click = not pb_title.last_click
                pb_title.last_click = last_click
                pb_title.set_icono(Iconos.Checked() if last_click else Iconos.Unchecked())

                for c in li_checks:
                    c.setChecked(last_click)

            pb_title.to_connect(toggle_all)

        add_column(True, 0)
        add_column(False, 3)

        layout.otro(grid)

        widget.setLayout(layout)
        return widget

    def aceptar(self):
        # General tab data
        li_gen = self.tab_general.get()
        self.dvar["SECONDS"] = li_gen[0]
        self.dvar["START"] = li_gen[1]
        self.dvar["PGN"] = li_gen[2]
        self.dvar["BEEP"] = li_gen[3]
        self.dvar["CUSTOM_SOUNDS"] = li_gen[4]
        self.dvar["SECONDS_BEFORE"] = li_gen[5]
        if self.with_previous_next:
            self.dvar["REPLAY_CONTINUOUS"] = li_gen[6]

        # Transparency tab data
        self.dvar["TRANSPARENCY"] = self.slider_level.value()
        for key, cb in self.dic_checks.items():
            self.dvar[key] = cb.isChecked()

        # Save configuration
        Code.configuration.write_variables("PARAMPELICULA", self.dvar)

        super().accept()
