import webbrowser

import Code
from Code import Update
from Code.About import About
from Code.Menus import BaseMenu
from Code.QT import Iconos


class InformationMenu(BaseMenu.RootMenu):
    name = "Information"

    def add_options(self):
        self.new("docs", _("Documents"), Iconos.Ayuda())
        self.new("web", _("Homepage"), Iconos.Web())
        self.new("blog", "Fresh news", Iconos.Blog())
        self.new("mail", f"{_('Contact')} (lukasmonk@gmail.com)", Iconos.Mail())
        if Code.configuration.is_main:
            self.new("actualiza", _("Check for updates"), Iconos.Update())
            # submenu = menu.submenu(_("Updates"), Iconos.Update())
            # submenu.opcion("actualiza", _("Check for updates"), Iconos.Actualiza())
            # submenu.separador()
            # submenu.opcion("actualiza_manual", _("Manual update"), Iconos.Zip())

        self.new("acercade", _("About"), Iconos.Aplicacion64())

    def run_select(self, resp):

        if resp == "acercade":
            self.acercade()
        elif resp == "docs":
            webbrowser.open(f"{Code.web}/docs")
        elif resp == "blog":
            webbrowser.open(Code.blog)
        elif resp.startswith("http"):
            webbrowser.open(resp)
        elif resp == "web":
            webbrowser.open(f"{Code.web}/index?lang={Code.configuration.translator()}")
        elif resp == "mail":
            webbrowser.open("mailto:lukasmonk@gmail.com")

        elif resp == "actualiza":
            self.actualiza()

        elif resp == "actualiza_manual":
            self.actualiza_manual()

    @staticmethod
    def acercade():
        w = About.WAbout()
        w.exec()

    def actualiza(self):
        if Update.update(self.wparent):
            self.reiniciar()

    def actualiza_manual(self):
        if Update.update_manual(self.wparent):
            self.reiniciar()
