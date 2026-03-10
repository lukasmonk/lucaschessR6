from PySide6 import QtCore, QtGui, QtWidgets, QtSvgWidgets

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
        self.iconos = {1: "🚧", 2: "🔥", 3: "✨", 4: "💫", 5: "🌟"}

        # Paleta de colores
        self.colors = {
            1: {
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
                "principal": "#E67E22",
                "secundario": "#F0B27A",
                "claro": "#F5CBA7",
                "oscuro": "#CA6F1E",
                "fondo": "#FDF2E9",
                "texto": "#784212",
                "borde": "#E67E22",
                "tapa_claro": "#F5CBA7",
                "tapa": "#F0B27A",
            },
        }

        layout = Colocacion.H()
        for i in range(1, 6):
            wbox = self.create_box(i, box_contents[i], box_session[i])
            if i != 1:
                conector = Controles.LB(self, "→")
                conector.setStyleSheet(f"font-size: 24px; color: {self.colors[i]['principal']}; font-weight: bold;")
                layout.control(conector)
            layout.control(wbox)
        layout.relleno()

        self.setLayout(layout)

    def create_box(self, num_box, num_elements, num_elements_session):
        """Crea un contenedor de caja completo con tarjeta, progreso y efectos"""
        card = QtWidgets.QFrame()
        card.setObjectName(f"cajaCard{num_box}")

        card.setStyleSheet(
            f"""
            QFrame#cajaCard{num_box} {{
                background-color: {self.colors[num_box]['fondo']};
                border-radius: 16px;
                border: 3px solid {self.colors[num_box]['borde']};
                padding: 12px;
            }}
            QFrame#cajaCard{num_box}:hover {{
                border: 3px solid {self.colors[num_box]['claro']};
                background-color: white;
            }}
        """
        )
        card.setFixedSize(160, 200)

        # Efecto de sombra si tiene contenido
        if num_elements > 0:
            shadow = QtWidgets.QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QtGui.QColor(self.colors[num_box]['principal']))
            shadow.setOffset(0, 4)
            card.setGraphicsEffect(shadow)

        layout = Colocacion.V(card)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Header con icono y nombre
        header = Colocacion.H()
        header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        icono = Controles.LB(self, self.iconos[num_box])
        icono.setStyleSheet("font-size: 24px; background: transparent;")
        header.control(icono)

        nombre = Controles.LB(self, f'{_("Box")} {num_box}')
        nombre.setStyleSheet(
            f"""
            color: {self.colors[num_box]['texto']}; 
            font-weight: bold; 
            background: transparent;
        """
        )
        header.control(nombre)
        layout.otro(header)

        svg_box = self.create_svg(num_box, num_elements)
        layout.controlc(svg_box)

        txt = ""
        if num_elements_session > 0:
            txt = f"💼 {num_elements_session}"
        if num_box == 5 and self.box_session_win > 0:
            txt += f" + 👑 {self.box_session_win}"
        elif num_box == 1 and self.box_session_not_trained > 0:
            txt = f"⛽{self.box_session_not_trained} {txt}".strip()
        if txt:
            lb_train = Controles.LB(self, txt)
            lb_train.set_font(Controles.FontTypeNew(point_size_delta=-1))
            lb_train.setStyleSheet("background: transparent;")
            layout.controld(lb_train)

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
