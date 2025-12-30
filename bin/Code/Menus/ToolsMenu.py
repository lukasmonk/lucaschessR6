import Code
from Code.Menus import BaseMenu, ToolsMenuRun
from Code.QT import Iconos, QTDialogs


class ToolsMenu(BaseMenu.RootMenu):
    name = "Tools"

    def add_options(self):
        self.new("create_own_game", _("Create your own game"), Iconos.JuegaSolo())
        self.add_databases()
        self.add_pgn()
        self.add_openings()

    def add_databases(self):
        submenu_databases = self.new_submenu(_("Databases"), Iconos.Database())

        nico = QTDialogs.rondo_puntos()

        def haz_elem(submenu, elem: QTDialogs.ElemDB):
            if elem.is_folder:
                submenu_new = submenu.new_submenu(elem.name, Iconos.Carpeta(), sep=False)
                for xelem in elem.li_elems:
                    if xelem.is_folder:
                        haz_elem(submenu_new, xelem)
                for xelem in elem.li_elems:
                    if not xelem.is_folder:
                        haz_elem(submenu_new, xelem)
            else:
                submenu.new(f"dbase_R{elem.path}", elem.name, nico.otro(), sep=False)

        dbli = QTDialogs.lista_db(Code.configuration, True)
        for relem in dbli.li_elems:
            if relem.is_folder:
                haz_elem(submenu_databases, relem)
        for relem in dbli.li_elems:
            if not relem.is_folder:
                haz_elem(submenu_databases, relem)

        submenu_maintenance = submenu_databases.new_submenu(_("Maintenance"), Iconos.DatabaseMaintenance())
        submenu_maintenance.new("dbase_N", _("Create new database"), Iconos.DatabaseMas())
        submenu_maintenance.new("dbase_D", _("Delete a database"), Iconos.DatabaseDelete())
        submenu_maintenance.new("dbase_M", _("Direct maintenance"), Iconos.Configurar())

    def add_pgn(self):
        submenu_pgn = self.new_submenu(_("PGN"), Iconos.PGN())

        submenu_pgn.new("pgn_visor", _("Read PGN file"), Iconos.Fichero())
        submenu_pgn.new("pgn_paste", _("Paste PGN"), Iconos.Pegar())
        submenu_pgn.new(
            "pgn_manual_save",
            _("Edit and save positions to PGN or FNS"),
            Iconos.ManualSave(),
        )
        submenu_pgn.new("pgn_miniatura", _("Miniature of the day"), Iconos.Miniatura())

    def add_openings(self):
        submenu_pgn = self.new_submenu(_("Openings"), Iconos.Openings())

        submenu_pgn.new("openings_lines", _("Opening lines"), Iconos.OpeningLines())
        submenu_pgn.new("openings_custom", _("Custom openings"), Iconos.Opening())
        submenu_pgn.new("openings_polyglot", _("Polyglot book factory"), Iconos.FactoryPolyglot())
        submenu_pgn.new("openings_books", _("Registered books"), Iconos.Libros())

    def run_select(self, resp):
        tmr = ToolsMenuRun.ToolsMenuRun(self)
        tmr.run(resp)
