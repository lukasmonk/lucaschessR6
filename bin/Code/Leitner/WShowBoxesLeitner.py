from PySide6 import QtCore, QtWidgets, QtSvgWidgets

from Code.QT import Controles, Colocacion

SVG_TEMPLATE_BOX = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="120" height="110" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- Gradiente sutil para el cuerpo (luz desde arriba-izquierda) -->
    <linearGradient id="cuerpoGrad{nivel}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%"   style="stop-color:{color_claro};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{color_oscuro};stop-opacity:1" />
    </linearGradient>
    <!-- Gradiente para la tapa (ligeramente más claro) -->
    <linearGradient id="tapaGrad{nivel}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%"   style="stop-color:{color_tapa_claro};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{color_tapa};stop-opacity:1" />
    </linearGradient>
    <!-- Sombra para la caja completa -->
    <filter id="sombra{nivel}" x="-15%" y="-15%" width="140%" height="140%">
      <feDropShadow dx="4" dy="4" stdDeviation="3" flood-color="#555555" flood-opacity="0.30"/>
    </filter>
  </defs>

  <!-- Grupo con sombra -->
  <g filter="url(#sombra{nivel})">
    <!-- Cuerpo principal de la caja -->
    <rect x="12" y="38" width="88" height="62" rx="3" ry="3"
          fill="url(#cuerpoGrad{nivel})"/>

    <!-- Tapa -->
    <rect x="8" y="20" width="96" height="22" rx="3" ry="3"
          fill="url(#tapaGrad{nivel})"/>
  </g>

  <!-- Línea separadora tapa/cuerpo -->
  <line x1="12" y1="40" x2="100" y2="40"
        stroke="{color_borde}" stroke-width="1" opacity="0.25"/>

  <!-- Asa: fondo oscuro (agujero) -->
  <rect x="38" y="27" width="36" height="10" rx="5" ry="5"
        fill="{color_borde}" opacity="0.55"/>

  <!-- Asa: borde interior claro (efecto profundidad) -->
  <rect x="39" y="28" width="34" height="8" rx="4" ry="4"
        fill="none"
        stroke="{color_tapa_claro}" stroke-width="1.2" opacity="0.5"/>

  <!-- Número centrado en el cuerpo -->
  <!-- Sombra del número -->
  <text x="57" y="78"
        font-family="'Arial Black', 'Impact', sans-serif"
        font-size="26" fill="{color_borde}"
        text-anchor="middle" font-weight="900"
        opacity="0.25" dx="1" dy="1">{numero}</text>
  <!-- Número principal -->
  <text x="56" y="77"
        font-family="'Arial Black', 'Impact', sans-serif"
        font-size="26" fill="white"
        text-anchor="middle" font-weight="900"
        opacity="0.85">{numero}</text>
</svg>"""


class WShowBoxesLeitner(QtWidgets.QWidget):
    cajas_widget: list

    def __init__(self, owner, box_contents: list, box_session: list):
        super().__init__(owner)

        self.box_session_win = box_session[-1]
        self.box_session_not_trained = box_session[0]

        # Iconos para cada nivel
        self.iconos = {0: "⛽", 1: "🚧", 2: "🔥", 3: "✨", 4: "💫", 5: "🌟"}

        # Paleta de colores
        self.colors = {
            0: {
                "principal": "#5D6D7E",
                "secundario": "#85929E",
                "claro": "#AEB6BF",
                "oscuro": "#34495E",
                "fondo": "#EBF5FB",
                "texto": "#2C3E50",
                "borde": "#5D6D7E",
                "tapa_claro": "#AEB6BF",
                "tapa": "#85929E",
            },
            1: {
                "principal": "#C0392B",
                "secundario": "#E74C3C",
                "claro": "#F1948A",
                "oscuro": "#922B21",
                "fondo": "#FDEDEC",
                "texto": "#641E16",
                "borde": "#C0392B",
                "tapa_claro": "#F1948A",
                "tapa": "#E74C3C",
            },
            2: {
                "principal": "#27AE60",
                "secundario": "#58D68D",
                "claro": "#82E0AA",
                "oscuro": "#1E8449",
                "fondo": "#EAFAF1",
                "texto": "#145A32",
                "borde": "#27AE60",
                "tapa_claro": "#82E0AA",
                "tapa": "#58D68D",
            },
            3: {
                "principal": "#3498DB",
                "secundario": "#5DADE2",
                "claro": "#85C1E9",
                "oscuro": "#2874A6",
                "fondo": "#EBF5FB",
                "texto": "#1B4F72",
                "borde": "#3498DB",
                "tapa_claro": "#85C1E9",
                "tapa": "#5DADE2",
            },
            4: {
                "principal": "#F39C12",
                "secundario": "#F8C471",
                "claro": "#FAD7A0",
                "oscuro": "#D68910",
                "fondo": "#FEF5E7",
                "texto": "#7E5109",
                "borde": "#F39C12",
                "tapa_claro": "#FAD7A0",
                "tapa": "#F8C471",
            },
            5: {
                "principal": "#7D3C98",
                "secundario": "#A569BD",
                "claro": "#C39BD3",
                "oscuro": "#5B2C6F",
                "fondo": "#F5EEF8",
                "texto": "#4A235A",
                "borde": "#7D3C98",
                "tapa_claro": "#C39BD3",
                "tapa": "#A569BD",
            },
        }

        layout = Colocacion.H()
        for num_box in range(0, 6):
            wbox = self.create_box(num_box, box_contents[num_box], box_session[num_box])
            layout.control(wbox)
            if num_box != 5:
                if num_box in (0, 4):
                    conector = "⇒"
                else:
                    conector = "→"
                lb_conector = Controles.LB(self, conector)
                lb_conector.setStyleSheet(
                    f"font-size: 24px; color: {self.colors[num_box]['principal']}; font-weight: bold;"
                )
                layout.control(lb_conector)
        layout.relleno()

        self.setLayout(layout)

    def create_box(self, num_box, num_elements, num_elements_session):
        """Crea un contenedor de caja completo con tarjeta, progreso y efectos"""
        card = QtWidgets.QFrame()
        card.setObjectName(f"cajaCard{num_box}")

        card.setStyleSheet(
            f"""
            QFrame#cajaCard{num_box} {{
                background-color: {self.colors[num_box]["fondo"]};
                border-radius: 16px;
                border: 3px solid {self.colors[num_box]["borde"]};
                padding: 8px;
            }}
        """
        )
        card.setFixedSize(150, 200)

        layout = Colocacion.V(card)

        # Header con icono y nombre
        header = Colocacion.H()

        if 0 < num_box < 5:
            icono = Controles.LB(self, self.iconos[num_box] + f" {num_box}")
            icono.setStyleSheet("font-size: 24px; background: transparent;")
            header.control(icono)
            header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        else:
            text = _("Never trained") if num_box == 0 else _("Completed")
            lb_name = Controles.LB(self, text)
            lb_name.setStyleSheet(
                f"""
                color: {self.colors[num_box]["texto"]}; 
                font-weight: bold; 
                background: transparent;
            """
            )
            lb_name.setWordWrap(True)
            lb_name.align_center()
            header.controlc(lb_name)
        layout.otro(header)

        if num_box == 0:
            symbol = "💼"
        elif num_box == 5:
            symbol = "👑"
        else:
            symbol = "💼"

        svg_box = self.create_svg(num_box, num_elements)
        layout.relleno()
        layout.controlc(svg_box)

        txt = ""
        if num_elements_session > 0:
            txt = f"{symbol} {num_elements_session}"
        lb_train = Controles.LB(self, txt)
        lb_train.set_font(Controles.FontTypeNew(point_size_delta=-1))
        lb_train.setStyleSheet("background: transparent;")
        layout.controld(lb_train)
        layout.relleno()

        return card

    def create_svg(self, num_box, num_elements):
        """Genera el widget SVG para una caja específica"""
        colores = self.colors[num_box]

        size = (120, 100)
        template = SVG_TEMPLATE_BOX

        svg_content = template.format(
            nivel=num_box,
            color_caja=colores["secundario"],
            color_claro=colores["claro"],
            color_oscuro=colores["oscuro"],
            color_tapa=colores["tapa"],
            color_tapa_claro=colores["tapa_claro"],
            color_borde=colores["borde"],
            numero=str(num_elements),
        )

        svg_widget = QtSvgWidgets.QSvgWidget()
        svg_widget.load(QtCore.QByteArray(svg_content.encode()))
        svg_widget.setFixedSize(*size)

        svg_widget.setStyleSheet("background-color: transparent;")

        return svg_widget
