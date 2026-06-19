import os
import sys
from PySide6 import QtCore, QtGui, QtWidgets
from shiboken6 import isValid


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


# def close_app():
#     app: QtWidgets.QApplication = QtWidgets.QApplication.instance()
#     if app is not None:
#         app.closeAllWindows()
#         app.quit()
#         try:
#             os._exit(0)
#         except Exception:
#             pass

def close_app():
    app = QtWidgets.QApplication.instance()
    if app is not None:
        # 1. Detener todos los QTimers
        for timer in app.findChildren(QtCore.QTimer):
            timer.stop()

        # 2. Detener TODOS los QThreads
        for thread in app.findChildren(QtCore.QThread):
            if thread.isRunning():
                thread.quit()
                thread.wait(1000)
                if thread.isRunning():
                    thread.terminate()
                    thread.wait()

        # 3. Cerrar ventanas (aquí se disparan los closeEvent que
        #    guardan configuración, posición, etc.)
        app.closeAllWindows()

        # 4. Procesar eventos pendientes
        app.processEvents()

        # 5. Salir del bucle de eventos
        app.quit()

    # Asegurar que todo lo escrito (logs, configuración) queda en disco
    # antes de saltarnos la finalización normal del proceso.
    sys.stdout.flush()
    sys.stderr.flush()

    # Salida inmediata a nivel de SO: evita que se ejecuten los
    # destructores de librerías nativas cargadas dinámicamente
    # (p.ej. los drivers .so de los eboards, que en Linux nunca se
    # descargan con dlclose), cuya finalización choca con la
    # limpieza de Qt/PySide6 y provoca el segfault al cerrar.
    os._exit(0)


def delay(ms: int):
    loop = QtCore.QEventLoop()
    timer = QtCore.QTimer(loop)
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(ms)
    loop.exec()


def scene_remove_item_safe(scene, item):
    if item is None or not isValid(item) or scene != item.scene():
        return
    try:
        scene.removeItem(item)
    except RuntimeError as e:
        if __debug__:
            from Code.Z import Debug
            Debug.prln(f"[warn] scene_remove_item_safe: {e}", color="red")
