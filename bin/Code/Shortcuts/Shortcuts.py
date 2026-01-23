from typing import Optional

import Code
from Code.Z import Util
from Code.Menus import (
    BaseMenu,
    CompeteMenu,
    EnginesMenu,
    InformationMenu,
    OptionsMenu,
    PlayMenu,
    ToolsMenu,
    TrainMenu,
)
from Code.QT import Iconos, QTDialogs
from Code.Shortcuts import WShortcuts


class Shortcut:
    key_menu: str
    key: str
    label: str

    def set_label(self, label):
        self.label = label

    def save(self):
        return {
            "key_menu": self.key_menu,
            "key": self.key,
            "label": self.label,
        }

    def read(self, dic):
        self.key_menu = dic["key_menu"]
        self.key = dic["key"]
        self.label = dic["label"]


class Shortcuts:
    def __init__(self, procesador):
        self.procesador = procesador
        self.wparent = procesador.main_window
        self._play_menu = None
        self._train_menu = None
        self._compete_menu = None
        self._tools_menu = None
        self._engines_menu = None
        self._options_menu = None
        self._information_menu = None
        self.li_shortcuts = []
        self.read()

    def play_menu(self):
        if self._play_menu is None:
            self._play_menu = PlayMenu.PlayMenu(self.procesador)
        return self._play_menu

    def train_menu(self):
        if self._train_menu is None:
            self._train_menu = TrainMenu.TrainMenu(self.procesador)
        return self._train_menu

    def compete_menu(self):
        if self._compete_menu is None:
            self._compete_menu = CompeteMenu.CompeteMenu(self.procesador)
        return self._compete_menu

    def tools_menu(self):
        if self._tools_menu is None:
            self._tools_menu = ToolsMenu.ToolsMenu(self.procesador)
        return self._tools_menu

    def engines_menu(self):
        if self._engines_menu is None:
            self._engines_menu = EnginesMenu.EnginesMenu(self.procesador)
        return self._engines_menu

    def options_menu(self):
        if self._options_menu is None:
            self._options_menu = OptionsMenu.OptionsMenu(self.procesador)
        return self._options_menu

    def information_menu(self):
        if self._information_menu is None:
            self._information_menu = InformationMenu.InformationMenu(self.procesador)
        return self._information_menu

    def get_txtmenu(self, txt_menu):
        return getattr(self, f"{txt_menu}_menu")()

    def read(self):
        lista = Util.restore_pickle(Code.configuration.paths.file_shortcuts())
        if lista is None:
            lista = []
        self.li_shortcuts = []
        for dic in lista:
            s = Shortcut()
            s.read(dic)
            self.li_shortcuts.append(s)

    def save(self):
        lista = []
        for shortcut in self.li_shortcuts:
            lista.append(shortcut.save())
        Util.save_pickle(Code.configuration.paths.file_shortcuts(), lista)

    def get_grid_column(self, nshortcut, column):
        shortcut: Shortcut = self.li_shortcuts[nshortcut]
        if column == "OPTION":
            tb_menu = self.get_txtmenu(shortcut.key_menu)
            option = tb_menu.locate_key(shortcut.key)
            return option.label
        elif column == "MENU":
            tb_menu = self.get_txtmenu(shortcut.key_menu)
            return _F(tb_menu.name)
        elif column == "LABEL":
            return shortcut.label
        return None

    def remove(self, nshortcut):
        del self.li_shortcuts[nshortcut]

    def go_up(self, nshortcut):
        self.li_shortcuts[nshortcut], self.li_shortcuts[nshortcut - 1] = (
            self.li_shortcuts[nshortcut - 1],
            self.li_shortcuts[nshortcut],
        )

    def go_down(self, nshortcut):
        self.li_shortcuts[nshortcut], self.li_shortcuts[nshortcut + 1] = (
            self.li_shortcuts[nshortcut + 1],
            self.li_shortcuts[nshortcut],
        )

    def menu(self):
        menu = QTDialogs.LCMenu(self.wparent)
        alt = 1
        option: Optional[BaseMenu.Option]
        for shortcut in self.li_shortcuts:
            key = shortcut.key
            key_menu = shortcut.key_menu
            tb_menu = self.get_txtmenu(key_menu)
            option = tb_menu.locate_key(key)
            if option is not None:
                if alt <= 9:
                    sh = f"ALT+{alt}"
                    alt += 1
                else:
                    sh = None
                menu.opcion(
                    shortcut,
                    shortcut.label,
                    option.icon,
                    not option.enabled,
                    shortcut=sh,
                )
                menu.separador()
        menu.separador()
        menu.opcion("shortcuts", _("Add new shortcuts"), Iconos.Mas())
        resp = menu.lanza()
        if resp == "shortcuts":
            w = WShortcuts.WShortcuts(self)
            w.exec()
        elif resp is not None:
            shortcut: Shortcut = resp
            self.lauch_shortcut(shortcut)

    def launch_alt(self, number):
        if 0 < number <= len(self.li_shortcuts):
            shortcut: Shortcut = self.li_shortcuts[number - 1]
            self.lauch_shortcut(shortcut)

    def lauch_shortcut(self, shortcut):
        menu_gen = self.get_txtmenu(shortcut.key_menu)
        menu_gen.run_exec(shortcut.key)

    def add_shortcut(self, menu, copt, label):
        shortcut = Shortcut()
        shortcut.key_menu = menu
        shortcut.key = copt
        shortcut.label = label
        self.li_shortcuts.append(shortcut)
