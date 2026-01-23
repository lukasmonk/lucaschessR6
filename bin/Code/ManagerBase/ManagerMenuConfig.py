import Code
from Code.Base.Constantes import (
    GT_AGAINST_ENGINE,
)
from Code.Engines import WConfEngines, WExternalEngines
from Code.ManagerBase import ManagerMenu
from Code.QT import FormLayout, Iconos, QTDialogs


class ManagerMenuConfig(ManagerMenu.ManagerMenu):

    def launch(self, li_extra_options=None, with_sounds=False, with_blinfold=True):
        menu = QTDialogs.LCMenu(self.main_window)

        menu_vista = menu.submenu(_("Show/hide"), Iconos.Vista())
        self.manager.add_menu_vista(menu_vista)
        menu.separador()

        if with_blinfold:
            menu_cg = menu.submenu(_("Blindfold chess"), Iconos.Ojo())

            if self.manager.board.blindfold_something():
                ico = Iconos.Naranja()
                tit = _("Disable")
            else:
                ico = Iconos.Verde()
                tit = _("Enable")
            menu_cg.opcion("cg_change", tit, ico, shortcut="Alt+Y")
            menu_cg.separador()
            menu_cg.opcion("cg_conf", _("Configuration"), Iconos.Opciones(), shortcut="CTRL+Y")
            menu_cg.separador()
            menu_cg.opcion(
                "cg_pgn",
                f"{_('PGN')}: {_('Hide') if self.manager.pgn.must_show else _('Show')}",
                Iconos.PGN(),
            )

        # Sonidos
        if with_sounds:
            menu.separador()
            menu.opcion("sonido", _("Sounds"), Iconos.S_Play())

        menu.separador()
        menu.opcion("external_engines", _("External engines"), Iconos.Engine())

        menu.separador()
        menu.opcion("engines", _("Engines configuration"), Iconos.ConfEngines())

        # On top
        menu.separador()
        label = _("Disable") if self.main_window.onTop else _("Enable")
        menu.opcion(
            "ontop",
            f"{label}: {_('window on top')}",
            Iconos.Unpin() if self.main_window.onTop else Iconos.Pin(),
        )

        # Right mouse
        menu.separador()
        label = _("Disable") if self.configuration.x_direct_graphics else _("Enable")
        menu.opcion(
            "mouseGraphics",
            f"{label}: {_('Live graphics with the right mouse button')}",
            Iconos.RightMouse(),
        )

        # Logs of engines
        menu.separador()
        is_engines_log_active = Code.list_engine_managers.is_logs_active()
        label = _("Save engines log")
        if is_engines_log_active:
            icono = Iconos.LogActive()
            label += f" ...{_('Working...')}"
            key = "log_close"
        else:
            icono = Iconos.LogInactive()
            key = "log_open"
        menu.opcion(key, label, icono)
        menu.separador()

        # auto_rotate
        if self.manager.auto_rotate is not None:
            menu.separador()
            prefix = _("Disable") if self.manager.auto_rotate else _("Enable")
            menu.opcion(
                "auto_rotate",
                f"{prefix}: {_('Auto-rotate board')}",
                Iconos.JS_Rotacion(),
            )

        # Mas Opciones
        self.add_extra_options(menu, li_extra_options)

        resp = menu.lanza()
        if resp:

            if li_extra_options:
                for data in li_extra_options:
                    key = data[0]
                    if resp == key:
                        return resp

            if resp == "log_open":
                Code.list_engine_managers.active_logs(True)

            elif resp == "log_close":
                Code.list_engine_managers.active_logs(False)

            elif resp.startswith("vista_"):
                self.manager.exec_menu_vista(resp)

            elif resp == "sonido":
                self.config_sonido()

            elif resp == "engines":
                self.conf_engines()

            elif resp == "external_engines":
                self.external_engines()

            elif resp == "ontop":
                self.main_window.on_top_window()

            elif resp == "mouseGraphics":
                self.configuration.x_direct_graphics = not self.configuration.x_direct_graphics
                self.configuration.graba()

            elif resp.startswith("cg_"):
                orden = resp[3:]
                if orden == "pgn":
                    self.manager.pgn.must_show = not self.manager.pgn.must_show
                    self.manager.refresh_pgn()
                elif orden == "change":
                    self.board.blindfold_change()

                elif orden == "conf":
                    self.board.blindfold_config()

            elif resp == "auto_rotate":
                self.manager.change_auto_rotate()

        return None

    def config_sonido(self):
        form = FormLayout.FormLayout(self.main_window, _("Configuration"), Iconos.S_Play(), minimum_width=440)
        form.separador()
        form.apart(_("After each opponent move"))
        form.checkbox(_("Sound a beep"), self.configuration.x_sound_beep)
        form.checkbox(_("Play customised sounds"), self.configuration.x_sound_move)
        form.separador()
        form.checkbox(_("The same for player moves"), self.configuration.x_sound_our)
        form.separador()
        form.separador()
        form.apart(_("When finishing the game"))
        form.checkbox(
            _("Play customised sounds for the result"),
            self.configuration.x_sound_results,
        )
        form.separador()
        form.separador()
        form.apart(_("Others"))
        form.checkbox(
            _("Play a beep when there is an error in tactic trainings"),
            self.configuration.x_sound_error,
        )
        form.separador()
        form.add_tab(_("Sounds"))
        resultado = form.run()
        if resultado:
            (
                self.configuration.x_sound_beep,
                self.configuration.x_sound_move,
                self.configuration.x_sound_our,
                self.configuration.x_sound_results,
                self.configuration.x_sound_error,
            ) = resultado[1][0]
            self.configuration.graba()

    def reset_engines(self):
        self.manager.manager_analyzer = self.procesador.change_manager_analyzer()

        self.manager.manager_tutor = self.procesador.change_manager_tutor()
        self.manager.set_label2(f"{_('Tutor')}: <b>{self.manager.manager_tutor.engine.name}")
        self.manager.is_analyzed_by_tutor = False

        if self.manager.game_type == GT_AGAINST_ENGINE:
            getattr(self.manager, "analyze_begin")()

    def conf_engines(self):
        w = WConfEngines.WConfEngines(self.main_window)
        w.exec()

        self.reset_engines()

    def external_engines(self):
        w = WExternalEngines.WExternalEngines(self.main_window)
        w.exec()

        self.reset_engines()
