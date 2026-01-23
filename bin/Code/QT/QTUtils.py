from PySide6 import QtCore, QtGui, QtWidgets


def refresh_gui():
    """
    Procesa eventos pendientes para que se muestren correctamente las windows
    """
    # QtCore.QCoreApplication.processEvents()
    QtWidgets.QApplication.processEvents()


def send_key_widget(widget, key, ckey):
    event_press = QtGui.QKeyEvent(QtGui.QKeyEvent.Type.KeyPress, key, QtCore.Qt.KeyboardModifier.NoModifier, ckey)
    event_release = QtGui.QKeyEvent(QtGui.QKeyEvent.Type.KeyRelease, key, QtCore.Qt.KeyboardModifier.NoModifier, ckey)
    QtCore.QCoreApplication.postEvent(widget, event_press)
    QtCore.QCoreApplication.postEvent(widget, event_release)
    refresh_gui()


dAlineacion = {
    "i": QtCore.Qt.AlignmentFlag.AlignLeft,
    "d": QtCore.Qt.AlignmentFlag.AlignRight,
    "c": QtCore.Qt.AlignmentFlag.AlignCenter,
}


def exit_application(enum_exit_xid):
    QtWidgets.QApplication.exit(enum_exit_xid.value)


def set_clipboard(dato, tipo="t"):
    cb = QtWidgets.QApplication.clipboard()
    if tipo == "t":
        cb.setText(dato)
    elif tipo == "i":
        cb.setImage(dato)
    elif tipo == "p":
        cb.setPixmap(dato)


def get_txt_clipboard():
    cb = QtWidgets.QApplication.clipboard()
    return cb.text()


def get_clipboard():
    clipboard = QtWidgets.QApplication.clipboard()
    mimedata = clipboard.mimeData()

    if mimedata.hasImage():
        return "p", mimedata.imageData()
    elif mimedata.hasHtml():
        return "h", mimedata.html()
    elif mimedata.hasHtml():
        return "h", mimedata.html()
    elif mimedata.hasText():
        return "t", mimedata.text()
    return None, None


def keyboard_modifiers():
    flags = QtWidgets.QApplication.keyboardModifiers()
    return parse_keyboard_modifiers(flags)


def parse_keyboard_modifiers(flags):
    is_ctrl = bool(flags & QtCore.Qt.KeyboardModifier.ControlModifier)
    is_alt = bool(flags & QtCore.Qt.KeyboardModifier.AltModifier)
    is_shift = bool(flags & QtCore.Qt.KeyboardModifier.ShiftModifier)
    return is_shift, is_ctrl, is_alt


def is_control_pressed() -> bool:
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return (modifiers.value & QtCore.Qt.KeyboardModifier.ControlModifier.value) > 0


def is_shift_pressed() -> bool:
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return (modifiers.value & QtCore.Qt.KeyboardModifier.ShiftModifier.value) > 0


def is_alt_pressed() -> bool:
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return (modifiers.value & QtCore.Qt.KeyboardModifier.AltModifier.value) > 0


def deferred_call(mstime: int, called):
    QtCore.QTimer.singleShot(mstime, called)
