from dataclasses import dataclass
from typing import List, Optional, Union

from PySide6.QtGui import QIcon

import Code
from Code.Base.Constantes import ExitProgram
from Code.QT import Controles, QTDialogs
from Code.QT import QTUtils


@dataclass(frozen=True)
class Option:
    key: str
    label: str
    icon: QIcon
    sep: bool
    enabled: bool

    def add_to_menu(self, menu_parent):
        if self.sep:
            menu_parent.separador()
        if self.label.startswith("KP"):
            texto = self.label
            talpha = Controles.FontType("Chess Merida", Code.configuration.x_menu_points + 4)
            k2 = texto.index("K", 2)
            texto = texto[:k2] + texto[k2:].lower()
            menu_parent.opcion(
                self.key,
                texto,
                self.icon,
                is_disabled=not self.enabled,
                font_type=talpha,
            )
        else:
            menu_parent.opcion(self.key, self.label, self.icon, is_disabled=not self.enabled)


class RootMenuBase:
    def __init__(self):
        self.li_options: List[Union[Option, SubMenu]] = []

    def new(self, key: str, label: str, icon: QIcon, sep=True, enabled=True) -> Option:
        option = Option(key, label, icon, sep, enabled)
        self.li_options.append(option)
        return option

    def new_submenu(self, label: str, icon: QIcon, sep=True, enabled=True):
        submenu = SubMenu(label, icon, sep=sep, enabled=enabled)
        self.li_options.append(submenu)
        return submenu


class SubMenu(RootMenuBase):
    def __init__(self, label: str, icon: QIcon, sep=True, enabled=True):
        super().__init__()
        self.label = label
        self.icon = icon
        self.sep = sep
        self.enabled = enabled

    def add_to_menu(self, menu_parent):
        if self.sep:
            menu_parent.separador()
        submenu = menu_parent.submenu(self.label, self.icon, is_disabled=not self.enabled)
        for option in self.li_options:
            option.add_to_menu(submenu)


class RootMenu(RootMenuBase):
    name: str

    def __init__(self, procesador):
        super().__init__()
        self.procesador = procesador
        self.wparent = procesador.main_window
        self.pending_update = True

    def add_options(self):
        pass

    def check_pending(self):
        if self.pending_update:
            self.li_options = []
            self.add_options()
            self.pending_update = False

    def launch(self):
        self.check_pending()
        menu = QTDialogs.LCMenu(self.wparent)
        for option in self.li_options:
            option.add_to_menu(menu)
        return menu.lanza()

    def must_be_updated(self):
        self.pending_update = True

    def list_possible_shortcuts(self):
        self.check_pending()
        list_pshortcuts = []

        def add_to_list(opt: Option):
            if isinstance(opt, SubMenu):
                for other_opt in opt.li_options:
                    add_to_list(other_opt)
            else:
                list_pshortcuts.append(opt)

        for option in self.li_options:
            add_to_list(option)

        return list_pshortcuts

    def locate_key(self, key: str) -> Optional[Option]:
        self.check_pending()
        locate_option: Optional[Option] = None

        def locate_in(opt: Option):
            nonlocal locate_option
            if isinstance(opt, SubMenu):
                for other_opt in opt.li_options:
                    locate_in(other_opt)
            else:
                if opt.key == key:
                    locate_option = opt

        for option in self.li_options:
            if locate_option is None:
                locate_in(option)
            else:
                return locate_option

        return locate_option

    def run(self):
        resp = self.launch()
        if resp is None:
            return
        self.run_select(resp)

    def run_exec(self, resp):
        self.check_pending()
        self.run_select(resp)

    def run_select(self, resp):
        pass

    def reiniciar(self):
        self.wparent.final_processes()
        self.wparent.accept()
        QTUtils.exit_application(ExitProgram.REINIT)
