from PySide6 import QtWidgets

import Code
from Code.QT import Colocacion, Controles, FormLayout, Iconos, LCDialog, QTDialogs


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

        self.form = self.setup_form()

        # Layout
        layout = Colocacion.V().control(tb).control(self.form).margen(5)
        self.setLayout(layout)

        self.restore_video(default_width=460, default_height=500)

    def setup_form(self):
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

    def aceptar(self):
        # General tab data
        li_gen = self.form.get()
        self.dvar["SECONDS"] = li_gen[0]
        self.dvar["START"] = li_gen[1]
        self.dvar["PGN"] = li_gen[2]
        self.dvar["BEEP"] = li_gen[3]
        self.dvar["CUSTOM_SOUNDS"] = li_gen[4]
        self.dvar["SECONDS_BEFORE"] = li_gen[5]
        if self.with_previous_next:
            self.dvar["REPLAY_CONTINUOUS"] = li_gen[6]

        # Save configuration
        Code.configuration.write_variables("PARAMPELICULA", self.dvar)

        super().accept()
