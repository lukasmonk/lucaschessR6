from PySide6 import QtGui

import Code


class Icons:
    NORMAL = 0
    SEPIA = 1
    DARK = 2
    dic_files = {NORMAL: "Iconos", SEPIA: "Iconos_sepia", DARK: "Iconos_dark"}
    bin_icons = None
    dic_icons = None
    mode = NORMAL

    def __init__(self):
        self.cache = {}

    def reset(self, mode):
        if mode != self.mode or self.bin_icons is None:
            self.mode = mode
            self.bin_icons = self.read_bin()
            self.dic_icons = self.read_dic()
            self.cache.clear()

    def combobox(self):
        return [
            (_("By default"), self.NORMAL),
            (_("Sepia"), self.SEPIA),
            (_("Dark"), self.DARK),
        ]

    def read_bin(self):
        file = f"{self.dic_files[self.mode]}.bin"
        with open(Code.path_resource("IntFiles", file), "rb") as f:
            return f.read()

    def read_dic(self):
        file = f"{self.dic_files[self.mode]}.dic"
        with open(Code.path_resource("IntFiles", file), "rt") as f:
            d = {}
            for linea in f:
                key, rg = linea.split("=")
                xfrom, xto = rg.strip().split(",")
                d[key] = (int(xfrom), int(xto))
            return d

    def icon(self, name):
        return self.get(name)

    def pixmap(self, name):
        return self.get(f"pm{name}")

    def get(self, name_icon):
        resp = self.cache.get(name_icon)
        if resp is not None:
            return resp
        is_pixmap = name_icon[0] == "p"
        name = name_icon[2:] if is_pixmap else name_icon
        xfrom, xto = self.dic_icons[name]
        pm = QtGui.QPixmap()
        pm.loadFromData(self.bin_icons[xfrom:xto])
        resp = pm if is_pixmap else QtGui.QIcon(pm)
        self.cache[name_icon] = resp
        return resp


icons = Icons()
iget = icons.get
