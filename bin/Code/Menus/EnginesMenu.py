import Code
from Code.Engines import WConfEngines, WExternalEngines
from Code.Leagues import WLeagues
from Code.Menus import BaseMenu
from Code.QT import Iconos
from Code.STS import WindowSTS
from Code.Swiss import WSwisses
from Code.Tournaments import WTournaments


class EnginesMenu(BaseMenu.RootMenu):
    name = "Engines"

    def add_options(self):
        self.new("external_engines", _("External engines"), Iconos.Engine())
        self.new("configuration", _("Configuration"), Iconos.ConfEngines())

        # Logs of engines
        is_engines_log_active = Code.list_engine_managers.is_logs_active()
        label = _("Save engines log")
        if is_engines_log_active:
            icono = Iconos.LogActive()
            label += " ...%s" % _("Working...")
            key = "log_close"
        else:
            icono = Iconos.LogInactive()
            key = "log_open"
        self.new(key, label, icono)

        self.new("kibitzers", _("Kibitzers"), Iconos.Kibitzer())
        self.new("sts", _("STS: Strategic Test Suite"), Iconos.STS())

        submenu_competitions = self.new_submenu(_("Competitions"), Iconos.Engine2())
        submenu_competitions.new("tournaments", _("Tournaments between engines"), Iconos.Torneos())
        submenu_competitions.new("leagues", _("Chess leagues"), Iconos.League())
        submenu_competitions.new("swiss", _("Swiss Tournaments"), Iconos.Swiss())

    def run_select(self, resp):

        if resp == "configuration":
            w = WConfEngines.WConfEngines(self.wparent)
            w.exec()
            self.procesador.change_manager_analyzer()
            self.procesador.change_manager_tutor()

        elif resp == "external_engines":
            w = WExternalEngines.WExternalEngines(self.wparent)
            w.exec()

        elif resp == "log_open":
            Code.list_engine_managers.active_logs(True)

        elif resp == "log_close":
            Code.list_engine_managers.active_logs(False)

        elif resp == "kibitzers":
            self.procesador.kibitzers_manager.edit()

        elif resp == "sts":
            WindowSTS.sts(self.procesador, self.wparent)

        elif resp == "tournaments":
            WTournaments.tournaments(self.wparent)

        elif resp == "leagues":
            WLeagues.leagues(self.wparent)

        elif resp == "swiss":
            WSwisses.swisses(self.wparent)
