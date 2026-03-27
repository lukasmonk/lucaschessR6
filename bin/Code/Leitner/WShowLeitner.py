from PySide6 import QtCore, QtWidgets

from Code.Leitner import WShowBoxesLeitner
from Code.QT import LCDialog, Iconos, Controles, Colocacion


class WShowLeitner(LCDialog.LCDialog):
    def __init__(self, owner, leitner):
        self.leitner = leitner
        self.box_contents = leitner.box_contents()

        titulo = f'{_("Leitner Training")} - {self.leitner.reference}'
        icon = Iconos.Leitner()
        LCDialog.LCDialog.__init__(self, owner, titulo, icon, "WShowLeitner")

        # Crear componentes
        wheader = self.create_header()
        wboxes = self.create_boxes()
        winfo = self.create_info()

        # Layout principal
        layout = Colocacion.V()
        # layout.setContentsMargins(10, 10, 10, 10)
        # layout.setSpacing(10)
        layout.control(wheader)
        layout.control(wboxes)
        layout.control(winfo)
        self.setLayout(layout)

        self.restore_video()

    def create_header(self):
        wheader = QtWidgets.QWidget()

        ly = Colocacion.V(wheader)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #5D6D7E; max-height: 1px;")
        ly.espacio(-5)
        ly.control(line)

        font = Controles.FontTypeNew(point_size_delta=4, extra_bold=True)
        tb = Controles.TBrutina(self, style=QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon, icon_size=32)
        if self.leitner.is_the_end():
            tb.new(_("Close"), Iconos.Close(), self.cancel)
        else:
            tb.new(_("Train"), Iconos.Entrenar(), self.train)
            tb.new(_("Cancel"), Iconos.Cancelar(), self.cancel)
        tb.setFont(font)
        lytb = Colocacion.H().relleno().control(tb).relleno()
        ly.otro(lytb)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #5D6D7E; max-height: 1px;")
        ly.espacio(-5)
        ly.control(line)

        return wheader

    def create_boxes(self):
        """Crea el widget de cajas usando WShowBoxesLeitner"""
        # Preparar datos: box_content[0] es puzzles sin entrenar, 1-5 son las cajas del Leitner
        wboxes = WShowBoxesLeitner.WShowBoxesLeitner(self, self.box_contents, self.leitner.box_session())
        return wboxes

    def train(self):
        self.save_video()
        self.accept()

    def cancel(self):
        self.save_video()
        self.reject()

    def create_info(self):
        """Crea el panel de información inferior con estadísticas visuales"""
        panel = QtWidgets.QFrame()
        panel.setObjectName("infoPanel")

        panel.setStyleSheet(
            """
            QFrame#infoPanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #54697E, stop:1 #4C5E70);
                border-radius: 1px;
                padding: 0px;
                border: 1px solid #5D6D7E;
            }
            QLabel {
                color: #ECF0F1;
                background: transparent;
            }
        """
        )

        font = Controles.FontTypeNew(point_size_delta=2)

        # Fechas
        ly_date = Colocacion.H().margen(0)
        lb_init_date = Controles.LB(self, f'📅 {_("Start date")}: {self.leitner.init_date.strftime('%Y/%m/%d')} ')
        lb_init_date.set_font(font)
        if self.leitner.end_date:
            lb_end_date = Controles.LB(self, f'{_("End date")}: {self.leitner.end_date.strftime('%Y/%m/%d')} ')
            lb_end_date.set_font(font)
            ly_date.control(lb_init_date).control(lb_end_date)
        else:
            ly_date.control(lb_init_date)

        # Session
        pending = len(self.leitner.current_ids_session)
        lb_session = Controles.LB(self, f'🎲 {_("Current session")}: {self.leitner.current_num_session} - '
                                        f'{_("Pending positions")}: {pending}')
        lb_session.set_font(font)

        # Success/errors
        right, wrong = self.leitner.right_wrong()
        total = right + wrong
        porc = right*100/total if total else 0.0
        symbol = '📈' if porc >= 50 else '📉'
        lb_result = Controles.LB(self, f'{_("Success")}: {right} - {_("Errors")}: {wrong}  ({symbol} {porc:0.02f}%)')

        ly_info = Colocacion.H().control(lb_session).relleno()
        ly_info.control(lb_result).relleno().otro(ly_date).margen(0)

        panel.setLayout(ly_info)

        return panel
