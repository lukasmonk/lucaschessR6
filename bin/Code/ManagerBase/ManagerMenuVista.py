from Code.ManagerBase import ManagerMenu


class ManagerMenuVista(ManagerMenu.ManagerMenu):
    def add(self, menu_vista):
        menu_vista.opcion(
            "vista_pgn_information",
            _("PGN information"),
            is_checked=self.main_window.is_active_information_pgn(),
        )
        menu_vista.separador()
        menu_vista.opcion(
            "vista_captured_material",
            _("Captured material"),
            is_checked=self.main_window.is_active_captures(),
        )
        menu_vista.separador()
        menu_vista.opcion(
            "vista_analysis_bar",
            _("Analysis Bar"),
            is_checked=self.main_window.is_active_analysisbar(),
        )
        menu_vista.separador()
        menu_vista.opcion(
            "vista_bestmove",
            _("Arrow with the best move when there is an analysis"),
            is_checked=self.configuration.x_show_bestmove,
        )
        menu_vista.separador()
        menu_vista.opcion(
            "vista_rating",
            _("Ratings") + " (NAGs)",
            is_checked=self.configuration.x_show_rating,
        )

    def exec(self, resp):
        resp = resp[6:]
        if resp == "bestmove":
            self.configuration.x_show_bestmove = not self.configuration.x_show_bestmove
            self.configuration.graba()
            self.manager.put_view()
        elif resp == "rating":
            self.configuration.x_show_rating = not self.configuration.x_show_rating
            self.configuration.graba()
            self.manager.put_view()
        else:
            self.manager.change_info_extra(resp)
