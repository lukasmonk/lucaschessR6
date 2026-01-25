from PySide6 import QtCore, QtGui, QtWidgets

import Code
from Code.QT import QTUtils
from Code.Z import Util

dAlineacion = {
    "i": QtCore.Qt.AlignmentFlag.AlignLeft,
    "d": QtCore.Qt.AlignmentFlag.AlignRight,
    "c": QtCore.Qt.AlignmentFlag.AlignCenter,
}


def qt_alignment(c_alin):
    """
    Convierte alineacion en letras (i-c-d) en constantes qt
    """
    return dAlineacion.get(c_alin, QtCore.Qt.AlignmentFlag.AlignLeft)


def qt_color(n_color):
    """
    Genera un color a partir de un dato numerico
    """
    return QtGui.QColor(n_color)


def qt_color_rgb(r, g, b):
    """
    Genera un color a partir del rgb
    """
    return QtGui.QColor(r, g, b)


def qt_brush(n_color):
    """
    Genera un brush a partir de un dato numerico
    """
    return QtGui.QBrush(qt_color(n_color))


def get_screen(widget: QtWidgets.QWidget) -> QtGui.QScreen:
    """Return the screen where widget is located, with safe fallbacks."""
    try:
        screen = widget.screen()
    except AttributeError:
        global_point = widget.mapToGlobal(QtCore.QPoint(2, 2))
        screen = QtGui.QGuiApplication.screenAt(global_point)

    return screen or primary_screen()


def get_screen_geometry(widget: QtWidgets.QWidget) -> QtCore.QRect:
    """Return geometry (QRect) of the screen where widget is located."""
    return get_screen(widget).geometry()


def center_on_desktop(window: QtWidgets.QWidget) -> None:
    """Center window on the desktop (monitor where it lives)."""
    screen_rect = get_screen_geometry(window)
    win_rect = window.geometry()

    x = screen_rect.x() + (screen_rect.width() - win_rect.width()) // 2
    y = screen_rect.y() + (screen_rect.height() - win_rect.height()) // 2

    window.move(x, y)


def center_on_widget(window: QtWidgets.QWidget) -> None:
    """Center window on its parent widget."""
    parent = window.parent()
    if not parent:
        center_on_desktop(window)
        return

    parent_rect = parent.geometry()
    win_rect = window.geometry()

    x = (parent_rect.width() - win_rect.width()) // 2
    y = (parent_rect.height() - win_rect.height()) // 2

    global_pos = parent.mapToGlobal(QtCore.QPoint(x, y))
    window.move(global_pos)


def dic_monitores() -> dict[int, QtCore.QRect]:
    """Return dict {index: geometry} of all monitors."""
    return {i: screen.geometry() for i, screen in enumerate(QtGui.QGuiApplication.screens())}


class EscondeWindow:
    """Context manager to temporarily hide window off-screen or minimized."""

    def __init__(self, window: QtWidgets.QWidget):
        self.window = window
        self.is_maximized = window.isMaximized()
        self.was_minimized = False

    def __enter__(self):
        if Util.is_windows():
            self.normal_geometry = self.window.normalGeometry()
            self.pos = self.window.pos()
            self.size = self.window.size()

            monitors = dic_monitores()
            width_total = sum(rect.width() for rect in monitors.values())

            self.window.setGeometry(
                width_total + self.window.width() + 10,
                0,
                self.size.width(),
                self.size.height(),
            )
        else:
            self.was_minimized = True
            self.window.showMinimized()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if Util.is_windows():
            if hasattr(self, "normal_geometry") and self.normal_geometry.isValid():
                self.window.setGeometry(self.normal_geometry)
            else:
                self.window.resize(self.size)
                self.window.move(self.pos)

            QtCore.QTimer.singleShot(50, self.finalize_restore)
        else:
            self.finalize_restore()

    def finalize_restore(self):
        if self.is_maximized:
            self.window.showMaximized()
        elif self.was_minimized:
            self.window.showNormal()

        QTUtils.refresh_gui()


def primary_screen() -> QtGui.QScreen:
    """Return the primary screen, creating a QApplication if needed."""
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication([])

    return app.primaryScreen()


def desktop_size() -> tuple[int, int]:
    """Return available desktop size."""
    if Code.main_window:
        screen = get_screen(Code.main_window)
    else:
        screen = primary_screen()

    geometry = screen.availableGeometry()
    return geometry.width(), geometry.height()


def desktop_width() -> int:
    return desktop_size()[0]


def desktop_height() -> int:
    return desktop_size()[1]


def set_clipboard(dato, tipo="t"):
    cb = QtWidgets.QApplication.clipboard()
    if tipo == "t":
        cb.setText(dato)
    elif tipo == "i":
        cb.setImage(dato)
    elif tipo == "p":
        cb.setPixmap(dato)


class MaintainGeometry:
    def __init__(self, window):
        self.window = window
        self.geometry = window.geometry()

    def __enter__(self):
        return self

    def __exit__(self, ex_type, value, traceback):
        self.window.setGeometry(self.geometry)


# def shrink(widget: QtWidgets.QWidget):
#     pos = widget.pos()
#     r = widget.geometry()
#     r.setWidth(0)
#     r.setHeight(0)
#     widget.setGeometry(r)
#     widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
#     widget.adjustSize()
#     if widget.layout():
#         widget.layout().activate()
#     widget.move(pos)


def shrink(widget: QtWidgets.QWidget):
    if widget.layout():
        widget.layout().invalidate()
    widget.adjustSize()
    widget.resize(widget.minimumSizeHint())


class EstadoWindow:
    def __init__(self, x):
        self.noEstado = x == QtCore.Qt.WindowState.WindowNoState
        self.minimizado = x == QtCore.Qt.WindowState.WindowMinimized
        self.maximizado = x == QtCore.Qt.WindowState.WindowMaximized
        self.fullscreen = x == QtCore.Qt.WindowState.WindowFullScreen
        self.active = x == QtCore.Qt.WindowState.WindowActive


def get_width_text(widget, text):
    metrics = QtGui.QFontMetrics(widget.font())
    return metrics.horizontalAdvance(text)


def get_height_text(widget, text):
    metrics = QtGui.QFontMetrics(widget.font())
    return metrics.boundingRect(text).height()
