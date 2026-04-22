from typing import Optional, Literal

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
    __slots__ = ("key_menu", "key", "label")

    key_menu: str
    key: str
    label: str

    def __init__(self, key_menu: str = "", key: str = "", label: str = "") -> None:
        self.key_menu = key_menu
        self.key = key
        self.label = label

    def set_label(self, label: str) -> None:
        self.label = label

    def get_label(self) -> str:
        return self.label

    def save(self) -> dict[str, str]:
        return {
            "key_menu": self.key_menu,
            "key": self.key,
            "label": self.label,
        }

    def to_dict(self) -> dict[str, str]:
        return self.save()

    def read(self, dic: dict) -> None:
        self.key_menu = dic.get("key_menu", "")
        self.key = dic.get("key", "")
        self.label = dic.get("label", "")

    def from_dict(self, dic: dict) -> None:
        self.read(dic)


class Shortcuts:
    def __init__(self, procesador) -> None:
        self.procesador = procesador
        self.wparent = procesador.main_window
        self._play_menu: Optional[PlayMenu.PlayMenu] = None
        self._train_menu: Optional[TrainMenu.TrainMenu] = None
        self._compete_menu: Optional[CompeteMenu.CompeteMenu] = None
        self._tools_menu: Optional[ToolsMenu.ToolsMenu] = None
        self._engines_menu: Optional[EnginesMenu.EnginesMenu] = None
        self._options_menu: Optional[OptionsMenu.OptionsMenu] = None
        self._information_menu: Optional[InformationMenu.InformationMenu] = None
        self.li_shortcuts: list[Shortcut] = []
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

    def get_txtmenu(self, txt_menu: str):
        return getattr(self, f"{txt_menu}_menu")()

    def read(self) -> None:
        lista = Util.restore_pickle(Code.configuration.paths.file_shortcuts())
        if not lista:
            self.li_shortcuts = []
            return
        shortcuts: list[Shortcut] = []
        for dic in lista:
            if not isinstance(dic, dict):
                continue
            s = Shortcut()
            try:
                s.read(dic)
            except Exception:
                continue
            shortcuts.append(s)
        self.li_shortcuts = shortcuts

    def save(self) -> None:
        lista: list[dict[str, str]] = [shortcut.save() for shortcut in self.li_shortcuts]
        Util.save_pickle(Code.configuration.paths.file_shortcuts(), lista)

    def get_grid_column(self, nshortcut: int, column: Literal["OPTION", "MENU", "LABEL"]):
        shortcut: Shortcut = self.li_shortcuts[nshortcut]
        if column == "LABEL":
            return shortcut.label
        tb_menu = self.get_txtmenu(shortcut.key_menu)
        if column == "OPTION":
            option = tb_menu.locate_key(shortcut.key)
            return option.label if option else ""
        if column == "MENU":
            return _F(tb_menu.name)
        return None

    def remove(self, nshortcut: int) -> None:
        del self.li_shortcuts[nshortcut]

    @staticmethod
    def _format_label_and_shortcut(label: str, alt: int, with_add: bool) -> tuple[str, Optional[str], int]:
        shortcut_text: Optional[str]
        if alt <= 9 and with_add:
            shortcut_text = f"ALT+{alt}"
            alt += 1
        else:
            if alt <= 9 and Util.is_windows():
                label = f"&{alt}. {label}"
                alt += 1
            shortcut_text = None
        return label, shortcut_text, alt

    def menu_base(self, with_add: bool):
        if not with_add and not self.li_shortcuts:
            return None
        menu = QTDialogs.LCMenu(self.wparent)
        alt = 1
        option: Optional[BaseMenu.Option]
        for shortcut in self.li_shortcuts:
            key = shortcut.key
            key_menu = shortcut.key_menu
            tb_menu = self.get_txtmenu(key_menu)
            option = tb_menu.locate_key(key)
            if option is not None:
                label, sh, alt = self._format_label_and_shortcut(option.label, alt, with_add)
                menu.opcion(
                    shortcut,
                    label,
                    option.icon,
                    not option.enabled,
                    shortcut=sh,
                )
                menu.separador()
        if with_add:
            menu.separador()
            menu.opcion("shortcuts", _("Add new shortcuts"), Iconos.Mas())
        return menu.lanza()

    def menu(self) -> None:
        resp = self.menu_base(True)
        if resp == "shortcuts":
            w = WShortcuts.WShortcuts(self)
            w.exec()
        elif resp is not None:
            shortcut: Shortcut = resp
            self.launch_shortcut(shortcut)

    def launch_alt(self, number: int) -> bool:
        if 0 < number <= len(self.li_shortcuts):
            shortcut: Shortcut = self.li_shortcuts[number - 1]
            self.launch_shortcut(shortcut)
            return True
        return False

    def launch_key(self, key: str) -> bool:
        for shortcut in self.li_shortcuts:
            if shortcut.key == key:
                self.launch_shortcut(shortcut)
                return True
        return False

    def launch_shortcut(self, shortcut: Shortcut) -> None:
        menu_gen = self.get_txtmenu(shortcut.key_menu)
        menu_gen.run_exec(shortcut.key)

    def add_shortcut(self, menu: str, copt: str, label: str) -> None:
        shortcut = Shortcut(menu, copt, label)
        self.li_shortcuts.append(shortcut)
