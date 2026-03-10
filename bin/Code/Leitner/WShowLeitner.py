from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QFrame,
    QWidget,
    QSizePolicy
)

from Code.Leitner import WShowBoxesLeitner
from Code.QT import LCDialog, Iconos, Controles, Colocacion


class WShowLeitner(LCDialog.LCDialog):
    def __init__(self, owner, leitner):
        self.leitner = leitner
        self.box_contents = leitner.box_contents()

        titulo = f'{_("Leitner Training")}: {self.leitner.reference}'
        icon = Iconos.Leitner()
        LCDialog.LCDialog.__init__(self, owner, titulo, icon, "WShowLeitner")

        # Crear componentes
        wheader = self.create_header()
        wboxes = self.create_boxes()
        winfo = self.create_info()

        # Layout principal
        layout = Colocacion.V()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.control(wheader)
        layout.control(wboxes)
        layout.control(winfo)
        self.setLayout(layout)

        self.restore_video()

    def create_header(self):
        """Crea el toolbar con botones Entrenar y Cancelar usando TBrutina"""
        pb_train = Controles.PB(self, _("Train"), rutina=self.train).set_icono(Iconos.Entrenar(), 32)
        pb_train.setStyleSheet("""
    QPushButton {
        /* Fondo gris medio con un degradado sutil para dar volumen */
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #757b85, stop:1 #5d636b);
        
        /* Texto en blanco suave (off-white) para que no canse */
        color: #f1f1f1;
        
        /* Bordes definidos pero suaves */
        border: 1px solid #4a4f57;
        border-radius: 12px;
        padding: 12px;
    }

    QPushButton:hover {
        /* Aclaramos el tono un poco al pasar el ratón */
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #868c96, stop:1 #6b727c);
        border: 1px solid #9aa0a9;
    }

    QPushButton:pressed {
        /* Efecto de hundimiento con sombra interior simulada */
        background-color: #4a4f57;
        padding-left: 14px;
        padding-top: 14px;
        border: 2px solid #3a3f46;
    }

    QPushButton:disabled {
        background-color: #a0a0a0;
        color: #d1d1d1;
        border: 1px solid #8e8e8e;
    }
""")
        font = Controles.FontTypeNew(family="Segoe UI", bold=True, point_size_delta=14)
        pb_train.setFont(font)
        pb_train.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        tb = Controles.TBrutina(self)

        if self.leitner.is_the_end():
            tb.new(_("Close"), Iconos.Close(), self.cancel)
        else:
            # tb.new(_("Train"), Iconos.Entrenar(), self.train)
            tb.new(_("Cancel"), Iconos.Cancelar(), self.cancel)
        w = QWidget(self)
        ly = Colocacion.H().control(pb_train).control(tb)
        w.setLayout(ly)
        return w

    def create_boxes(self):
        """Crea el widget de cajas usando WShowBoxesLeitner"""
        # Preparar datos: box_content[0] es puzzles sin entrenar, 1-5 son las cajas del Leitner
        wboxes = WShowBoxesLeitner.WShowBoxesLeitner(self, self.box_contents, self.leitner.box_session())
        return wboxes

    def create_info(self):
        """Crea el panel de información inferior con estadísticas visuales"""
        panel = QFrame()
        panel.setObjectName("infoPanel")
        panel.setStyleSheet(
            """
            QFrame#infoPanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #34495E, stop:1 #2C3E50);
                border-radius: 20px;
                padding: 15px;
                border: 2px solid #5D6D7E;
            }
            QLabel {
                color: #ECF0F1;
                background: transparent;
            }
        """
        )

        layout = Colocacion.H()
        layout.setSpacing(25)

        # Círculo de progreso
        terminadas = self.box_contents[6]
        total = sum(self.box_contents)
        ratio = (terminadas / total * 100) if total > 0 else 0

        # Contenedor del círculo
        circle_container = QFrame()
        circle_container.setFixedSize(140, 140)
        circle_container.setStyleSheet("background: transparent; border: none;")

        # Widget de progreso circular
        progress_widget = QFrame(circle_container)
        progress_widget.setGeometry(10, 10, 120, 120)
        progress_widget.setStyleSheet(
            f"""
            QFrame {{
                background: qconicalgradient(cx:0.5, cy:0.5, angle:90, 
                    stop:0 #F1C40F, stop:{ratio / 100} #F1C40F, 
                    stop:{ratio / 100} #7F8C8D, stop:1 #7F8C8D);
                border-radius: 60px;
                border: 4px solid #2C3E50;
            }}
        """
        )

        # Centro del círculo
        center = QFrame(progress_widget)
        center.setGeometry(20, 20, 80, 80)
        center.setStyleSheet(
            """
            QFrame {
                background-color: #34495E;
                border-radius: 40px;
                border: 2px solid #F1C40F;
            }
        """
        )

        # Texto del porcentaje
        porc_text = QLabel(f"{ratio:.0f}%", center)
        porc_text.setGeometry(0, 0, 80, 80)
        porc_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        porc_text.setStyleSheet(
            """
            color: #F1C40F; 
            font-weight: bold; 
            font-size: 20px;
            background: transparent;
        """
        )

        layout.addWidget(circle_container)

        # Información estadística
        ly_stats = Colocacion.V()
        ly_stats.setSpacing(8)

        mastered = Controles.LB(self, f'{_("Completed positions")}: ')
        mastered.setStyleSheet(
            """
            font-size: 24px; 
            font-weight: bold; 
            color: #F1C40F;
            background: transparent;
        """
        )
        mastered_num = Controles.LB(self, f"{terminadas} / {total}")
        mastered_num.setStyleSheet(
            """
            font-size: 32px; 
            font-weight: bold; 
            color: #F1C40F;
            background: transparent;
        """
        )
        ly = Colocacion.H().control(mastered).control(mastered_num).relleno()
        font = Controles.FontTypeNew(point_size_delta=2)
        if self.box_contents[0] > 0 or self.leitner.end_date is None:
            lb_pending = Controles.LB(self, f'⛽ {_("Puzzles never trained")}: {self.box_contents[0]}')
            lb_pending.set_font(font)
            ly.relleno().control(lb_pending)
        else:
            ly.relleno()

        ly_stats.otro(ly)

        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #5D6D7E; max-height: 2px;")
        ly_stats.control(line)

        # Info adicional
        ly_info = Colocacion.H()

        lb_init_date = Controles.LB(self, f'📅 {_("Start date")}: {self.leitner.init_date.strftime('%Y/%m/%d')} ')
        lb_init_date.set_font(font)
        if self.leitner.end_date:
            lb_end_date = Controles.LB(self, f'{_("End date")}: {self.leitner.end_date.strftime('%Y/%m/%d')} ')
            lb_end_date.set_font(font)
            ly_date = Colocacion.V().control(lb_init_date).control(lb_end_date)
            ly_info.otro(ly_date)
        else:
            ly_info.control(lb_init_date)

        pending = len(self.leitner.current_ids_session)
        lb_sessions = Controles.LB(self, f'🎲 {_("Current session")}: {self.leitner.current_num_session} '
                                         f'({pending} {_("Positions")})')
        lb_sessions.set_font(font)
        ly_info.relleno().control(lb_sessions)

        ly_stats.otro(ly_info)

        layout.otro(ly_stats)
        panel.setLayout(layout)

        return panel

    def train(self):
        self.save_video()
        self.accept()

    def cancel(self):
        self.save_video()
        self.reject()
