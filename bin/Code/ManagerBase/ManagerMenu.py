class ManagerMenu:
    def __init__(self, manager):
        self.manager = manager
        self.configuration = manager.configuration
        self.procesador = manager.procesador
        self.main_window = manager.main_window

    @property
    def game(self):
        return self.manager.game

    @property
    def board(self):
        return self.manager.board

    @staticmethod
    def add_extra_options(menu, li_extra_options):
        # Mas Opciones
        if not li_extra_options:
            return
        menu.separador()
        submenu = menu
        for data in li_extra_options:
            if len(data) == 3:
                key, label, icono = data
                shortcut = ""
            elif len(data) == 4:
                key, label, icono, shortcut = data
            else:
                key, label, icono, shortcut = None, None, None, None

            if label is None:
                if icono is None:
                    submenu.separador()
                else:
                    submenu = menu
            elif key is None:
                submenu = menu.submenu(label, icono)

            else:
                submenu.opcion(key, label, icono, shortcut=shortcut)
        menu.separador()
