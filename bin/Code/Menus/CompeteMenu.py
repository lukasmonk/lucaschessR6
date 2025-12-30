import Code
from Code.Base.Constantes import GT_FICS, GT_FIDE, GT_LICHESS
from Code.Competitions import ManagerElo, ManagerFideFics, ManagerMicElo, ManagerWicker
from Code.CompetitionWithTutor import ManagerCompeticion, WCompetitionWithTutor
from Code.Engines import WEngines
from Code.MainWindow import Presentacion
from Code.Menus import BaseMenu
from Code.QT import Iconos, QTDialogs
from Code.SingularMoves import ManagerSingularM, WindowSingularM


class CompeteMenu(BaseMenu.RootMenu):
    name = "Compete"

    def add_options(self):

        configuration = Code.configuration
        self.new("competition", _("Competition with tutor"), Iconos.NuevaPartida())

        submenu_elo = self.new_submenu(_("Elo-Rating"), Iconos.Elo())

        submenu_elo.new("lucaselo", f'{_("Lucas-Elo")} ({configuration.x_elo})', Iconos.Elo())
        submenu_elo.new(
            "micelo",
            f'{_("Tourney-Elo")} ({configuration.x_michelo})',
            Iconos.EloTimed(),
        )
        submenu_elo.new(
            "wicker",
            f'{_("The Wicker Park Tourney")} ({configuration.x_wicker})',
            Iconos.Park(),
        )

        rp = QTDialogs.rondo_puntos()

        def haz_submenu_ffl(key, label, icon, current_elo, level_min, level_max):
            if current_elo < level_min * 100:
                min_elo = level_min * 100
                max_elo = max(current_elo + 400, min_elo + 99)
            elif current_elo > level_max * 100:
                max_elo = level_max * 100 + 99
                min_elo = min(current_elo - 400, level_max * 100)
            else:
                min_elo = max(current_elo - 400, level_min * 100)
                max_elo = min(current_elo + 400, level_max * 100)

            if min_elo > max_elo:
                min_elo, max_elo = max_elo, min_elo

            menu_ffl = submenu_elo.new_submenu(f"{label} ({current_elo})", icon)
            for level in range(level_min, level_max + 1):
                elo_level = level * 100
                if min_elo <= elo_level and elo_level + 99 <= max_elo:
                    menu_ffl.new(f"{key}_{level}", f"{elo_level}-{elo_level + 99}", rp.otro())

        fics = configuration.x_fics
        haz_submenu_ffl("fics", _("Fics-Elo"), Iconos.Fics(), fics, 9, 27)

        fide = configuration.x_fide
        haz_submenu_ffl("fide", _("Fide-Elo"), Iconos.Fide(), fide, 10, 28)

        lichess = configuration.x_lichess
        haz_submenu_ffl("lichess", _("Lichess-Elo"), Iconos.Lichess(), lichess, 8, 26)

        submenu_singular_moves = self.new_submenu(_("Singular moves"), Iconos.Singular())
        submenu_singular_moves.new("strenght101", _("Calculate your strength"), Iconos.Strength())
        submenu_singular_moves.new("challenge101", _("Challenge 101"), Iconos.Wheel())

    def run_select(self, resp):
        if "_" in resp:
            key, opcion = resp.split("_")
            getattr(self, key)(opcion)
        else:
            getattr(self, resp)()

    def competition(self):
        options = WCompetitionWithTutor.datos(self.wparent)
        if options:
            categorias, categoria, nivel, is_white, puntos = options

            manager = ManagerCompeticion.ManagerCompeticion(Code.procesador)
            manager.start(categorias, categoria, nivel, is_white, puntos)

    def strenght101(self):
        w = WindowSingularM.WSingularM(self.wparent)
        if w.exec():
            manager = ManagerSingularM.ManagerSingularM(self.procesador)
            manager.start(w.sm)

    def challenge101(self):
        Presentacion.ManagerChallenge101(self.procesador)

    def lucaselo(self):
        manager = ManagerElo.ManagerElo(self.procesador)
        resp = WEngines.select_engine_elo(manager, Code.configuration.elo_current())
        if resp:
            manager.start(resp)

    def micelo(self):
        manager = ManagerMicElo.ManagerMicElo(self.procesador)
        resp = WEngines.select_engine_micelo(manager, Code.configuration.micelo_current())
        if resp:
            key = "MICELO_TIME"
            dic = Code.configuration.read_variables(key)
            default_minutes = dic.get("MINUTES", 10)
            default_seconds = dic.get("SECONDS", 0)
            resp_t = QTDialogs.vtime(
                self.wparent,
                minMinutos=0,
                minSegundos=0,
                maxMinutos=999,
                max_seconds=999,
                default_minutes=default_minutes,
                default_seconds=default_seconds,
            )
            if resp_t:
                minutos, seconds = resp_t
                dic = {"MINUTES": minutos, "SECONDS": seconds}
                Code.configuration.write_variables(key, dic)
                manager.start(resp, minutos, seconds)

    def wicker(self):
        manager = ManagerWicker.ManagerWicker(self.procesador)
        resp = WEngines.select_engine_wicker(manager, Code.configuration.wicker_current())
        if resp:
            key = "WICKER_TIME"
            dic = Code.configuration.read_variables(key)
            default_minutes = dic.get("MINUTES", 10)
            default_seconds = dic.get("SECONDS", 0)
            resp_t = QTDialogs.vtime(
                self.wparent,
                minMinutos=0,
                minSegundos=0,
                maxMinutos=999,
                max_seconds=999,
                default_minutes=default_minutes,
                default_seconds=default_seconds,
            )
            if resp_t:
                minutos, seconds = resp_t
                dic = {"MINUTES": minutos, "SECONDS": seconds}
                Code.configuration.write_variables(key, dic)
                manager.start(resp, minutos, seconds)

    def ficselo(self, nivel):
        manager = ManagerFideFics.ManagerFideFics(self.procesador)
        manager.selecciona(GT_FICS)
        xid = manager.elige_juego(nivel)
        manager.start(xid)

    def fideelo(self, nivel):
        manager = ManagerFideFics.ManagerFideFics(self.procesador)
        manager.selecciona(GT_FIDE)
        xid = manager.elige_juego(nivel)
        manager.start(xid)

    def lichesselo(self, nivel):
        manager = ManagerFideFics.ManagerFideFics(self.procesador)
        manager.selecciona(GT_LICHESS)
        xid = manager.elige_juego(nivel)
        manager.start(xid)
