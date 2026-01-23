from typing import Optional, Dict, Any

from PySide6 import QtCore, QtGui, QtWidgets

import Code
from Code.QT import ScreenUtils


class LCDialog(QtWidgets.QDialog):
    def __init__(self, main_window, titulo, icono, extparam):
        super().__init__(main_window)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.key_video = extparam
        self.liGrids = []
        self.liSplitters = []

        self.setWindowTitle(titulo)
        self.setWindowIcon(icono)
        self.setWindowFlags(
            QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowMinimizeButtonHint
            | QtCore.Qt.WindowType.WindowMaximizeButtonHint
            | QtCore.Qt.WindowType.WindowCloseButtonHint
        )

        shortcut_alt_o = QtGui.QShortcut(QtGui.QKeySequence("Alt+O"), self)
        shortcut_alt_o.activated.connect(self.pressed_shortcut_alt_o)

    def pressed_shortcut_alt_o(self) -> None:
        self.move(QtCore.QPoint(0, 0))

    def register_grid(self, grid: Any) -> None:
        """Register a grid to save its state."""
        if grid:
            self.liGrids.append(grid)

    def register_splitter(self, splitter: QtWidgets.QSplitter, name: str) -> None:
        """Register a splitter to save its state."""
        if splitter and name:
            self.liSplitters.append((splitter, name))

    def save_video(self, dic_extended: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        dic = dic_extended if dic_extended is not None else {}

        pos = self.pos()
        dic["_POSICION_"] = f"{pos.x()},{pos.y()}"

        tam = self.size()
        dic["_SIZE_"] = f"{tam.width()},{tam.height()}"

        for grid in self.liGrids:
            grid.save_video(dic)

        for sp, name in self.liSplitters:
            dic[f"SP_{name}"] = sp.sizes()

        Code.configuration.save_video(self.key_video, dic)
        return dic

    def restore_dicvideo(self) -> Optional[Dict[str, Any]]:
        return Code.configuration.restore_video(self.key_video)

    def restore_video(
        self,
        with_tam: bool = True,
        with_width: bool = True,
        default_width: Optional[int] = None,
        default_height: Optional[int] = None,
        default_dic: Optional[Dict[str, Any]] = None,
        shrink: bool = False,
    ) -> bool:
        dic = self.restore_dicvideo()
        if not dic:
            dic = default_dic

        screen_geometry = ScreenUtils.get_screen_geometry(self)
        width_desktop = screen_geometry.width()
        height_desktop = screen_geometry.height()

        if dic:
            if with_tam:
                w, h = self.width(), self.height()
                if "_SIZE_" in dic:
                    try:
                        w, h = map(int, dic["_SIZE_"].split(","))
                    except (ValueError, TypeError, AttributeError):
                        pass
                else:
                    # Legacy support for _TAMA
                    w, h = self.width(), self.height()
                    for k, v in dic.items():
                        if k.startswith("_TAMA"):
                            try:
                                parts = v.split(",")
                                if len(parts) == 2:
                                    w, h = int(parts[0]), int(parts[1])
                                break
                            except (ValueError, TypeError, IndexError):
                                pass

                # Boundary checks
                w = max(20, min(w, width_desktop))
                h = max(20, min(h, height_desktop - 40))

                if with_width:
                    self.resize(w, h)
                else:
                    self.resize(self.width(), h)

            for grid in self.liGrids:
                grid.restore_video(dic)
                if hasattr(grid, "reread_columns"):
                    grid.reread_columns()

            for sp, name in self.liSplitters:
                k = f"SP_{name}"
                li_sp = dic.get(k)
                if li_sp and isinstance(li_sp, list) and len(li_sp) == 2 and isinstance(li_sp[0], int):
                    try:
                        sp.setSizes(li_sp)
                    except (TypeError, ValueError):
                        pass

            if shrink:
                ScreenUtils.shrink(self)

            if "_POSICION_" in dic:
                try:
                    x, y = map(int, dic["_POSICION_"].split(","))

                    # Multi-monitor clamping
                    monitors = ScreenUtils.dic_monitores()
                    width_all = sum(m.width() for m in monitors.values())
                    height_all = max((m.y() + m.height()) for m in monitors.values()) if monitors else height_desktop

                    # Horizontal check
                    if x > width_all - 50:
                        x = (width_desktop - self.width()) // 2
                    elif x < -self.width() + 50:
                        x = 0

                    # Vertical check
                    if y > height_all - 50:
                        y = 10
                    elif y < -10:
                        y = 0

                    self.move(x, y)
                except (ValueError, TypeError, AttributeError):
                    pass
            return True

        else:
            # Fallback if no config found
            if default_width is not None or default_height is not None:
                w = default_width if default_width is not None else self.width()
                h = default_height if default_height is not None else self.height()

                w = min(w, width_desktop)
                h = min(h, height_desktop - 40)

                self.resize(w, h)

        return False

    def accept(self) -> None:
        self.save_video()
        super().accept()

    def reject(self) -> None:
        self.save_video()
        super().reject()
