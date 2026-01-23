import random

import Code
from Code.Menus import BaseMenu
from Code.PlayAgainstEngine import (
    Albums,
    ManagerAlbum,
    ManagerPerson,
    ManagerPlayAgainstEngine,
    WindowAlbumes,
    WPlayAgainstEngine,
    ConfigurationsPAE,
)
from Code.PlayHuman import ManagerPlayHuman, WPlayHuman
from Code.QT import Iconos, QTDialogs


class PlayMenu(BaseMenu.RootMenu):
    name = "Play"

    def add_options(self):
        if Code.configuration.x_menu_play_config:
            pae = ConfigurationsPAE.ConfigurationsPAE()
            li_conf = pae.list_visible()
            if li_conf:
                for conf, order, dic in li_conf:
                    self.new(f"free_{conf}", conf, Iconos.Engine2())

        self.new("free", _("Play against an engine"), Iconos.Libre())

        submenu = self.new_submenu(_("Opponents for young players"), Iconos.RivalesMP())

        self.menu_youngs(submenu)

        self.new("human", _("Play human vs human"), Iconos.HumanHuman())

    @staticmethod
    def menu_youngs(submenu: BaseMenu.SubMenu) -> None:
        for name, trans, ico, elo in QTDialogs.list_irina():
            submenu.new(f"person_{name}", trans, ico, sep=False)

        submenu_animals = submenu.new_submenu(_("Album of animals"), Iconos.Penguin())
        albumes = Albums.AlbumAnimales()
        dic = albumes.list_menu()
        anterior = None
        for animal in dic:
            enabled = True
            if anterior and not dic[anterior]:
                enabled = False
            submenu_animals.new(f"animals_{animal}", _F(animal), Iconos.icono(animal), enabled=enabled)
            anterior = animal

        submenu_vehicles = submenu.new_submenu(_("Album of vehicles"), Iconos.Wheel())
        albumes = Albums.AlbumVehicles()
        dic = albumes.list_menu()
        anterior = None
        for character in dic:
            enabled = True
            if anterior and not dic[anterior]:
                enabled = False
            trans = ""
            for c in character:
                if c.isupper():
                    if trans:
                        trans += " "
                trans += c
            trans = _F(trans)
            submenu_vehicles.new(f"vehicles_{character}", trans, Iconos.icono(character), enabled=enabled)
            anterior = character

    def run_select(self, resp):
        if "_" in resp:
            key, opcion = resp.split("_")
            getattr(self, key)(opcion)
        else:
            getattr(self, resp)()

    def free(self, opcion=None):
        assistant = self.procesador
        if opcion is None:
            dic = WPlayAgainstEngine.play_against_engine(assistant, _("Play against an engine"))
        else:
            pae = ConfigurationsPAE.ConfigurationsPAE()
            dic = pae[opcion]
        if dic is None:
            return
        manager = ManagerPlayAgainstEngine.ManagerPlayAgainstEngine(assistant)
        side = dic["SIDE"]
        if side == "R":
            side = "B" if random.randint(1, 2) == 1 else "N"
        dic["ISWHITE"] = side == "B"
        manager.start(dic)

    def human(self):
        assistant = self.procesador
        w = WPlayHuman.WPlayHuman()
        if not w.exec():
            return

        manager = ManagerPlayHuman.ManagerPlayHuman(assistant)
        manager.start(w.dic)

    def person(self, opcion):
        assistant = self.procesador
        uno = QTDialogs.blancasNegrasTiempo(self.wparent)
        if not uno:
            return
        is_white, si_tiempo, minutos, seconds, fastmoves = uno
        if is_white is None:
            return

        dic = {
            "ISWHITE": is_white,
            "RIVAL": opcion,
            "WITHTIME": si_tiempo and minutos > 0,
            "MINUTES": minutos,
            "SECONDS": seconds,
            "FASTMOVES": fastmoves,
        }

        manager = ManagerPerson.ManagerPerson(assistant)
        manager.start(dic)

    def animals(self, animal):
        assistant = self.procesador
        albumes = Albums.AlbumAnimales()
        album = albumes.get_album(animal)
        album.event = _("Album of animals")
        album.test_finished()
        cromo, must_reset = WindowAlbumes.elige_cromo(self.wparent, album)
        if cromo is None:
            if must_reset:
                albumes.reset(animal)
                self.animals(animal)
            return

        manager = ManagerAlbum.ManagerAlbum(assistant)
        manager.start(album, cromo)

    def vehicles(self, vehicle):
        assistant = self.procesador
        albumes = Albums.AlbumVehicles()
        album = albumes.get_album(vehicle)
        album.event = _("Album of vehicles")
        album.test_finished()
        cromo, must_reset = WindowAlbumes.elige_cromo(self.wparent, album)
        if cromo is None:
            if must_reset:
                albumes.reset(vehicle)
                self.vehicles(vehicle)
            return

        manager = ManagerAlbum.ManagerAlbum(assistant)
        manager.start(album, cromo)
