import os

import Code
from Code.Z import RemoveResults, Util
from Code.Board import WBoardColors
from Code.Config import WindowConfig
from Code.MainWindow import LucasChessGui
from Code.Menus import BaseMenu
from Code.QT import Iconos, SelectFiles, WColors
from Code.Shortcuts import Shortcuts, WShortcuts
from Code.Sound import WindowSonido


class OptionsMenu(BaseMenu.RootMenu):
    name = "Options"

    def add_options(self):
        self.new("cambiaconfiguration", _("General configuration"), Iconos.Opciones())

        txt = _("Language")
        if txt != "Language":
            txt += " (Language)"
        self.new("select_language", txt, Iconos.Language())

        submenu_colors = self.new_submenu(_("Colors"), Iconos.Colores())
        submenu_colors.new("edit_board_colors", _("Main board"), Iconos.EditarColores())
        submenu_colors.new("change_colors", _("General"), Iconos.Vista())

        self.new("sonidos", _("Custom sounds"), Iconos.SoundTool())
        self.new("atajos_edit", _("Shortcuts"), Iconos.Atajos())
        self.new("remove_results", _("Remove results"), Iconos.Delete())
        self.new("set_password", _("Set password"), Iconos.Password())

        if Code.configuration.is_main:
            self.new("usuarios", _("Users"), Iconos.Usuarios())

            submenu_user_folder = self.new_submenu(_("User data folder"), Iconos.Carpeta())
            submenu_user_folder.new(
                "open_explorer", f"{_('Current')}: {Code.configuration.paths.folder_userdata()}", None
            )
            submenu_user_folder.new("folder_change", _("Change the folder"), Iconos.FolderChange())
            if not Code.configuration.paths.is_default_folder():
                submenu_user_folder.new("folder_default", _("Reset to default"), Iconos.Defecto())

    @staticmethod
    def open_explorer():
        Util.startfile(Code.configuration.paths.folder_userdata())

    def remove_results(self):
        rem = RemoveResults.RemoveResults(self.wparent)
        rem.menu()

    def select_language(self):
        if LucasChessGui.select_language(self.wparent, False):
            self.reiniciar()

    def cambiaconfiguration(self):
        if WindowConfig.options(self.wparent, Code.configuration):
            Code.configuration.graba()
            self.reiniciar()

    def edit_board_colors(self):
        w = WBoardColors.WBoardColors(self.procesador.board)
        w.exec()

    def change_colors(self):
        w = WColors.WColors(self.procesador)
        if w.exec():
            self.reiniciar()

    def sonidos(self):
        w = WindowSonido.WSonidos(self.procesador)
        w.exec()

    def folder_change(self):
        carpeta = SelectFiles.get_existing_directory(
            self.wparent,
            Code.configuration.paths.folder_userdata(),
            f"{_('Change the folder where all data is saved')}. {_('Be careful please')}",
        )
        if carpeta and os.path.isdir(carpeta):
            Code.configuration.paths.change_active_folder(carpeta)
            self.reiniciar()

    def folder_default(self):
        Code.configuration.paths.change_active_folder(None)
        self.reiniciar()

    def atajos_edit(self):
        shortcuts = Shortcuts.Shortcuts(self.procesador)
        w = WShortcuts.WShortcuts(shortcuts)
        w.exec()

    def run_select(self, resp):
        getattr(self, resp)()
