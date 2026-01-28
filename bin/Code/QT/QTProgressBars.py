import time

from PySide6 import QtCore, QtWidgets

from Code.QT import Colocacion, Controles, QTUtils, ScreenUtils, QTMessages


class TwoProgressBars(QtWidgets.QDialog):
    def __init__(self, owner, titulo, formato1="%v/%m", formato2="%v/%m", with_pause=False):
        super().__init__(owner)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.owner = owner
        self.with_pause = with_pause

        self._paused = False
        self._canceled = False
        self._closed = False

        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
        )
        self.setWindowTitle(titulo)

        self.bp1 = QtWidgets.QProgressBar()
        self.bp1.setFormat(formato1)
        self.gb1 = Controles.GB(self, "", Colocacion.H().control(self.bp1))

        self.bp2 = QtWidgets.QProgressBar()
        self.bp2.setFormat(formato2)
        self.gb2 = Controles.GB(self, "", Colocacion.H().control(self.bp2))

        ly_bt = Colocacion.H().relleno()

        if with_pause:
            self.bt_pause = Controles.PB(self, _("Pause"), self.toggle_pause, plano=False)
            ly_bt.control(self.bt_pause).espacio(10)

        bt_cancel = Controles.PB(self, _("Cancel"), self.cancelar, plano=False)
        ly_bt.control(bt_cancel)

        self.setLayout(Colocacion.V().control(self.gb1).control(self.gb2).otro(ly_bt))

    # ---------- Eventos ----------

    def closeEvent(self, event):
        self._canceled = True
        self._closed = True
        event.accept()

    # ---------- Control ----------

    def mostrar(self):
        self.show()
        ScreenUtils.center_on_widget(self)
        return self

    def cancelar(self):
        self._canceled = True
        self._paused = False
        self.close()

    def cerrar(self):
        if not self._closed:
            self._closed = True
            self.close()

    # ---------- Pausa ----------

    def toggle_pause(self):
        self._paused = not self._paused
        texto = _("Continue") if self._paused else _("Pause")
        self.bt_pause.set_text(texto)

    def is_paused(self):
        return self._paused and not self._canceled

    # ---------- API pública ----------

    def put_label(self, cual, texto):
        (self.gb1 if cual == 1 else self.gb2).set_text(texto)

    def set_total(self, cual, maximo):
        (self.bp1 if cual == 1 else self.bp2).setRange(0, maximo)

    def pon(self, cual, valor):
        (self.bp1 if cual == 1 else self.bp2).setValue(valor)

    def is_canceled(self):
        return self._canceled

    def check_paused(self):
        while self._paused and not self._canceled:
            QTUtils.refresh_gui()
            time.sleep(0.05)  # 50ms es suficiente y más eficiente que 10ms


class ProgressBarWithTime(QtWidgets.QDialog):
    def __init__(self, owner, titulo, formato1="%v/%m", show_time=False):
        QtWidgets.QDialog.__init__(self, owner)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.owner = owner
        self.show_time = show_time
        self.total = 0

        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
        )
        self.setWindowTitle(titulo)

        # gb1 + progress
        self.progressbar = QtWidgets.QProgressBar()
        self.progressbar.setFormat(formato1)
        ly = Colocacion.V().control(self.progressbar)
        if show_time:
            self.li_times = []
            self.lb_time = Controles.LB(self)
            self.time_inicial = None
            self.valor_previo = 0
            ly.control(self.lb_time)
        self.gb1 = Controles.GB(self, "", ly)

        # cancelar
        bt = Controles.PB(self, _("Cancel"), self.cancelar, plano=False)
        ly_bt = Colocacion.H().relleno().control(bt)

        layout = Colocacion.V().control(self.gb1).otro(ly_bt)

        self.setMinimumWidth(480)

        self.setLayout(layout)
        self._is_canceled = False
        self._is_closed = False

    def closeEvent(self, event):
        self._is_canceled = True
        self.cerrar()

    def mostrar(self):
        self.show()
        ScreenUtils.center_on_widget(self)
        return self

    def show_top_right(self):
        self.move(self.owner.x() + self.owner.width() - self.width(), self.owner.y())
        self.show()
        return self

    def cerrar(self):
        if not self._is_closed:
            self.hide()
            self.reject()
            QTUtils.refresh_gui()
            self._is_closed = True

    def cancelar(self):
        self._is_canceled = True
        self.cerrar()

    def put_label(self, texto):
        self.gb1.set_text(texto)

    def set_total(self, maximo):
        self.total = maximo
        self.progressbar.setRange(0, maximo)
        if self.show_time:
            self.li_times = []
            self.time_inicial = time.time()
            self.valor_previo = 0

    def pon(self, valor):
        self.progressbar.setValue(valor)
        QTUtils.refresh_gui()
        if self.show_time:
            salto = valor - self.valor_previo
            if salto == 0:
                return
            time_actual = time.time()
            tm = (time_actual - self.time_inicial) / salto
            self.valor_previo = valor
            self.time_inicial = time_actual
            self.li_times.append(tm)
            tm = sum(self.li_times) / len(self.li_times)
            previsto = int(tm * (self.total - valor))
            xmessage = QTMessages.time_message(previsto)

            lb_pt = _("Pending time")
            self.lb_time.set_text(f"{lb_pt}: {xmessage}")

    def is_canceled(self):
        QTUtils.refresh_gui()
        return self._is_canceled

    def __enter__(self):
        self.mostrar()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cerrar()


class ProgressBarSimple(QtWidgets.QProgressDialog):
    # ~ bp = QTMessages.ProgressBarSimple( self, "me", 5 ).mostrar()
    # ~ n = 0
    # ~ for n in range(5):
    # ~ prlk( n )
    # ~ bp.pon( n )
    # ~ time.sleep(1)
    # ~ if bp.is_canceled():
    # ~ break
    # ~ bp.cerrar()

    def __init__(self, owner, titulo, mensaje, total, width=None):
        QtWidgets.QProgressDialog.__init__(self, mensaje, _("Cancel"), 0, total, owner)
        self.total = total
        self.actual = 0
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setWindowTitle(titulo)
        self.owner = owner
        self.setAutoClose(False)
        self.setAutoReset(False)
        if width:
            self.setFixedWidth(width)

    def mostrar(self):
        if self.owner:
            self.move(
                self.owner.x() + (self.owner.width() - self.width()) / 2,
                self.owner.y() + (self.owner.height() - self.height()) / 2,
            )
        self.show()
        return self

    def show_top_right(self):
        if self.owner:
            self.move(self.owner.x() + self.owner.width() - self.width(), self.owner.y())
        self.show()
        return self

    def cerrar(self):
        self.setValue(self.total)
        self.close()

    def mensaje(self, mens):
        self.setLabelText(mens)

    def is_canceled(self):
        QTUtils.refresh_gui()
        return self.wasCanceled()

    def set_total(self, total):
        self.setMaximum(total)
        self.pon(0)

    def pon(self, valor):
        self.setValue(valor)
        self.actual = valor

    def inc(self):
        self.pon(self.actual + 1)
