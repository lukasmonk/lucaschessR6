import datetime

from PySide6 import QtCore, QtGui, QtWidgets


def calc_fixed_width(fixed_width: int) -> int:
    metricas = QtGui.QFontMetrics(QtWidgets.QApplication.font())
    ancho_caracter = metricas.horizontalAdvance('M')
    return max(int(fixed_width * ancho_caracter / 12), fixed_width)


# def calc_fixed_chars(widget, num_caracteres) -> int:
#     font = widget.font()
#     font_metrics = QtGui.QFontMetrics(font)
#
#     ancho_promedio = font_metrics.averageCharWidth()
#     margen = font_metrics.maxWidth() * 0.2
#
#     return int(num_caracteres * ancho_promedio + margen)
#
#
# def calc_fixed_numbers(widget, num_numbers) -> int:
#     font_metrics = QtGui.QFontMetrics(widget.font())
#     ancho_promedio = font_metrics.horizontalAdvance("8")
#     return int(num_numbers * ancho_promedio * 1.2)


class ED(QtWidgets.QLineEdit):
    """
    Control de entrada de texto en una linea.
    """

    def __init__(self, parent, texto=None):
        """
        @param parent: ventana propietaria.
        @param texto: texto inicial.
        """
        if texto:
            QtWidgets.QLineEdit.__init__(self, texto, parent)
        else:
            QtWidgets.QLineEdit.__init__(self, parent)
        self.parent = parent

        self.decimales = 1

        self.menu = None

    def read_only(self, sino):
        self.setReadOnly(sino)
        return self

    def password(self):
        self.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        return self

    def set_disabled(self, sino):
        self.setDisabled(sino)
        return self

    def capture_enter(self, rutina):
        self.returnPressed.connect(rutina)
        return self

    def capture_changes(self, rutina):
        self.textEdited.connect(rutina)
        return self

    def set_text(self, texto):
        self.setText(texto)

    def texto(self):
        txt = self.text()
        return txt

    def align_center(self):
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        return self

    def align_right(self):
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        return self

    def minimum_width(self, px):
        self.setMinimumWidth(calc_fixed_width(px))
        return self

    def ancho_maximo(self, px):
        self.setMaximumWidth(calc_fixed_width(px))
        return self

    def caracteres(self, num):
        self.setMaxLength(num)
        # self.numCaracteres = num
        return self

    def relative_width(self, px):
        self.setFixedWidth(calc_fixed_width(px))
        return self

    def controlrx(self, regexpr):
        rx = QtCore.QRegularExpression(regexpr)
        validator = QtGui.QRegularExpressionValidator(rx, self)
        self.setValidator(validator)
        return self

    def set_font(self, f):
        self.setFont(f)
        return self

    def set_font_type(
            self,
            name="",
            puntos=8,
            peso=50,
            is_italic=False,
            is_underlined=False,
            is_striked=False,
            txt=None,
    ):
        f = FontType(name, puntos, peso, is_italic, is_underlined, is_striked, txt)
        self.setFont(f)
        return self

    def type_float(
            self,
            valor: float = 0.0,
            from_sq: float = -36000.0,
            to_sq: float = 36000.0,
            decimales: int = None,
    ):
        """
        Valida los caracteres suponiendo que es un tipo decimal con unas condiciones
        @param valor: valor inicial
        @param from_sq: valor minimo
        @param to_sq: valor maximo
        @param decimales: num. decimales
        """
        if from_sq is None:
            validator = QtGui.QDoubleValidator(self)
            validator.setNotation(QtGui.QDoubleValidator.Notation.StandardNotation)
            validator.setLocale(QtCore.QLocale.c())
            self.setValidator(validator)
        else:
            if decimales is None:
                decimales = self.decimales
            else:
                self.decimales = decimales
            validator = QtGui.QDoubleValidator(from_sq, to_sq, decimales, self)
            validator.setNotation(QtGui.QDoubleValidator.Notation.StandardNotation)
            validator.setLocale(QtCore.QLocale.c())
            self.setValidator(validator)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.set_float(valor)
        return self

    # def type_float_positive(self, valor: float = 0.00, decimals: int = 2):
    #     self.controlrx(rf"^\d+(\.\d{{1,{decimals}}})?$")
    #     self.set_float(valor)

    def set_float(self, valor):
        fm = f"%0.{self.decimales}f"

        self.set_text(fm % valor)
        return self

    def text_to_float(self):
        txt = self.text()
        if "," in txt:
            txt = txt.replace(",", ".")
        while txt.count(".") > 1:
            x = txt.index(".")
            txt = txt[:x] + txt[x + 1:]
            self.set_text(txt)
        return round(float(txt), self.decimales) if txt else 0.0

    def type_integer(self, valor=0):
        """
        Valida los caracteres suponiendo que es un tipo entero con unas condiciones
        @param valor: valor inicial
        """
        self.setValidator(QtGui.QIntValidator(self))
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.set_integer(valor)
        return self

    def type_integer_positive(self, valor):
        self.controlrx("^[0-9]+$")
        self.set_integer(valor)
        self.align_right()
        return self

    def set_integer(self, valor):
        self.set_text(str(valor))
        return self

    def text_to_integer(self):
        txt = self.text()
        try:
            int_num = int(float(txt))
        except ValueError:
            int_num = 0
        return int_num


class SB(QtWidgets.QSpinBox):
    """
    SpinBox: Entrada de numeros enteros, con control de incremento o reduccion
    """

    def __init__(self, parent, valor, from_sq, to_sq):
        """
        @param valor: valor inicial
        @param from_sq: limite inferior
        @param to_sq: limite superior
        """
        QtWidgets.QSpinBox.__init__(self, parent)
        self.setRange(from_sq, to_sq)
        self.setSingleStep(1)
        self.setValue(int(valor))

    def relative_width(self, px):
        self.setFixedWidth(calc_fixed_width(px))
        return self

    def valor(self):
        return self.value()

    def set_value(self, valor):
        self.setValue(int(valor) if valor else 0)

    def capture_changes(self, rutina):
        self.valueChanged.connect(rutina)
        return self

    def set_font(self, font):
        self.setFont(font)
        return self


class CB(QtWidgets.QComboBox):
    """
    ComboBox : entrada de una lista de options = etiqueta,key[,icono]
    """
    li_options: list

    def __init__(self, parent, li_options, init_value, extend_seek=False):
        """
        @param li_options: lista de (etiqueta,key)
        @param init_value: valor inicial
        """
        QtWidgets.QComboBox.__init__(self, parent)
        self.rehacer(li_options, init_value)
        if extend_seek:
            self.setEditable(True)
            self.setInsertPolicy(self.InsertPolicy.NoInsert)

    def valor(self):
        return self.itemData(self.currentIndex())

    def label(self):
        return self.itemText(self.currentIndex())

    def set_font(self, f):
        self.setFont(f)
        return self

    def rehacer(self, li_options, init_value):
        self.li_options = li_options
        self.clear()
        nindex = 0
        for n, opcion in enumerate(li_options):
            if len(opcion) == 2:
                etiqueta, key = opcion
                self.addItem(etiqueta, key)
            else:
                etiqueta, key, icono = opcion
                self.addItem(icono, etiqueta, key)
            if key == init_value:
                nindex = n
        self.setCurrentIndex(nindex)

    def set_value(self, valor):
        for n, opcion in enumerate(self.li_options):
            key = opcion[1]
            if key == valor:
                self.setCurrentIndex(n)
                break

    def set_width(self, px):
        r = self.geometry()
        r.setWidth(px)
        self.setGeometry(r)
        return self

    def set_width_minimo(self):
        self.setSizeAdjustPolicy(self.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        return self

    def capture_changes(self, rutina):
        self.currentIndexChanged.connect(rutina)
        return self

    def set_multiline(self, max_px):
        self.setFixedWidth(calc_fixed_width(max_px))
        list_view = QtWidgets.QListView()
        # Turn On the word wrap
        list_view.setWordWrap(True)
        # set popup view widget into the combo box
        self.setView(list_view)
        return self


class CHB(QtWidgets.QCheckBox):
    """
    CheckBox : entrada de una campo seleccionable
    """

    def __init__(self, parent, etiqueta, init_value):
        """
        @param etiqueta: label mostrado
        @param init_value: valor inicial : True/False
        """
        QtWidgets.QCheckBox.__init__(self, etiqueta, parent)
        self.setChecked(init_value)

    def set_value(self, si):
        self.setChecked(si)
        return self

    def valor(self):
        return self.isChecked()

    def set_font(self, f):
        self.setFont(f)
        return self

    def capture_changes(self, rutina):
        self.clicked.connect(rutina)
        return self

    def relative_width(self, px):
        self.setFixedWidth(calc_fixed_width(px))
        return self


class LB(QtWidgets.QLabel):
    """
    Etiquetas de texto.
    """

    def __init__(self, parent, texto=None):
        """
        @param texto: texto inicial.
        """
        if texto:
            QtWidgets.QLabel.__init__(self, texto, parent)
        else:
            QtWidgets.QLabel.__init__(self, parent)

        self.setOpenExternalLinks(True)
        self.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction | QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )

    def set_text(self, texto):
        self.setText(texto)

    def texto(self):
        return self.text()

    def set_font(self, f):
        self.setFont(f)
        return self

    def set_font_type(
            self,
            name="",
            puntos=None,
            peso=50,
            is_italic=False,
            is_underlined=False,
            is_striked=False,
            txt=None,
    ):
        f = FontType(name, puntos, peso, is_italic, is_underlined, is_striked, txt)
        self.setFont(f)
        return self

    def align_center(self):
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        return self

    def align_right(self):
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        return self

    def align(self, center=False, right=False, top=True):
        if right:
            alignment = QtCore.Qt.AlignmentFlag.AlignRight
        elif center:
            alignment = QtCore.Qt.AlignmentFlag.AlignCenter
        else:
            alignment = QtCore.Qt.AlignmentFlag.AlignLeft
        if top:
            alignment |= QtCore.Qt.AlignmentFlag.AlignTop
        self.setAlignment(alignment)
        return self

    def ancho_maximo(self, px):
        self.setMaximumWidth(calc_fixed_width(px))
        return self

    def relative_width(self, px):
        self.setFixedWidth(calc_fixed_width(px))
        return self

    def minimum_width(self, px):
        self.setMinimumWidth(calc_fixed_width(px))
        return self

    def minimum_height(self, px):
        self.setMinimumHeight(px)
        return self

    def fixed_height(self, px):
        self.setFixedHeight(px)
        return self

    def set_height(self, px):
        rec = self.geometry()
        rec.setHeight(px)
        self.setGeometry(rec)
        return self

    def alinea_y(self, otro_lb):
        rec = self.geometry()
        rec.setY(otro_lb.geometry().y())
        self.setGeometry(rec)
        return self

    def put_image(self, pm):
        self.setPixmap(pm)
        return self

    def set_color_background(self, color):
        return self.set_background(color.name())

    def set_background(self, txt_color: str):
        self.setStyleSheet(f"QWidget {{ background-color: {txt_color} }}")
        return self

    def set_color_foreground(self, color):
        return self.set_foreground(color.name())

    def set_foreground(self, txt_color: str):
        self.setStyleSheet(f"QWidget {{ color: {txt_color} }}")
        return self

    def set_foreground_background(self, color, fondo):
        self.setStyleSheet(f"QWidget {{ color: {color}; background-color: {fondo}}}")
        return self

    def set_wrap(self):
        self.setWordWrap(True)
        return self

    def set_width(self, px):
        r = self.geometry()
        r.setWidth(px)
        self.setGeometry(r)
        return self

    # def set_fixed_width(self, px):
    #     self.setFixedWidth(px)
    #     return self

    def set_fixed_lines(self, num_lines):
        font_metrics = QtGui.QFontMetrics(self.font())
        line_height = font_metrics.height()
        required_height = line_height * num_lines
        self.setFixedHeight(required_height)
        return self


def LB2P(parent, texto):
    return LB(parent, f"{texto}: ")


class PB(QtWidgets.QPushButton):
    """
    Boton.
    """

    def __init__(self, parent, texto, rutina=None, plano=True):
        """
        @param parent: ventana propietaria, necesario para to_connect una rutina.
        @param texto: etiqueta inicial.
        @param rutina: rutina a la que se conecta el boton.
        """
        QtWidgets.QPushButton.__init__(self, texto, parent)
        self.w_parent = parent
        self.setFlat(plano)
        if rutina:
            self.to_connect(rutina)

    def set_icono(self, icono, icon_size=16):
        self.setIcon(icono)
        self.setIconSize(QtCore.QSize(icon_size, icon_size))
        return self

    def set_font(self, f):
        self.setFont(f)
        return self

    def set_font_type(
            self,
            name="",
            puntos=8,
            peso=50,
            is_italic=False,
            is_underlined=False,
            is_striked=False,
            txt=None,
    ):
        f = FontType(name, puntos, peso, is_italic, is_underlined, is_striked, txt)
        self.setFont(f)
        return self

    def relative_width(self, px):
        self.setFixedWidth(calc_fixed_width(px))
        return self

    def fixed_height(self, px):
        self.setFixedHeight(px)
        return self

    def cuadrado(self, px):
        px = calc_fixed_width(px)
        self.setFixedSize(px, px)
        return self

    def minimum_width(self, px):
        self.setMinimumWidth(calc_fixed_width(px))
        return self

    def to_connect(self, rutina):
        self.clicked.connect(rutina)
        return self

    def set_background(self, txt_fondo):
        self.setStyleSheet(f"QWidget {{ background: {txt_fondo} }}")
        return self

    def set_flat(self, si_plano):
        self.setFlat(si_plano)
        return self

    def set_tooltip(self, txt):
        self.setToolTip(txt)
        return self

    def set_text(self, txt):
        self.setText(txt)

    def set_pordefecto(self, ok):
        self.setDefault(ok)
        self.setAutoDefault(ok)


class RB(QtWidgets.QRadioButton):
    """
    RadioButton: lista de alternativas
    """

    def __init__(self, w_parent, texto, rutina=None):
        QtWidgets.QRadioButton.__init__(self, texto, w_parent)
        if rutina:
            self.clicked.connect(rutina)

    def activate(self, activate=True):
        self.setChecked(activate)
        return self


class GB(QtWidgets.QGroupBox):
    """
    GroupBox: Recuadro para agrupamiento de controles
    """

    def __init__(self, w_parent, texto, layout):
        QtWidgets.QGroupBox.__init__(self, texto, w_parent)
        self.setLayout(layout)
        self.w_parent = w_parent

    def set_font(self, f):
        self.setFont(f)
        return self

    def set_font_type(
            self,
            name="",
            puntos=8,
            peso=50,
            is_italic=False,
            is_underlined=False,
            is_striked=False,
            txt=None,
    ):
        f = FontType(name, puntos, peso, is_italic, is_underlined, is_striked, txt)
        self.setFont(f)
        return self

    def align_center(self):
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        return self

    def to_connect(self, rutina):
        self.setCheckable(True)
        self.setChecked(False)
        self.clicked.connect(rutina)
        return self

    def set_text(self, text):
        self.setTitle(text)
        return self


class EM(QtWidgets.QTextEdit):
    """
    Control de entrada de texto en varias lineas.
    """

    def __init__(self, parent, texto=None, is_html=True):
        """
        @param texto: texto inicial.
        """
        QtWidgets.QTextEdit.__init__(self, parent)
        self.parent = parent

        self.menu = None  # menu de contexto
        self.rutinaDobleClick = None

        self.setAcceptRichText(is_html)

        if texto:
            if is_html:
                self.setText(texto)
            else:
                self.insertPlainText(texto)

    def set_html(self, texto):
        self.setHtml(texto)
        return self

    def insert_html(self, texto):
        self.insertHtml(texto)
        return self

    def insert_text(self, texto):
        self.insertPlainText(texto)
        return self

    def read_only(self):
        self.setReadOnly(True)
        return self

    def texto(self):
        return self.toPlainText()

    def set_text(self, txt):
        self.setText("")
        self.insert_text(txt)

    def html(self):
        return self.toHtml()

    def set_width(self, px):
        r = self.geometry()
        r.setWidth(px)
        self.setGeometry(r)
        return self

    def minimum_width(self, px):
        self.setMinimumWidth(px)
        return self

    def minimum_height(self, px):
        self.setMinimumHeight(px)
        return self

    def fixed_height(self, px):
        self.setFixedHeight(px)
        return self

    def relative_width(self, px):
        self.setFixedWidth(calc_fixed_width(px))
        return self

    def set_font(self, f):
        self.setFont(f)
        return self

    def set_font_type(
            self,
            name="",
            puntos=8,
            peso=50,
            is_italic=False,
            is_underlined=False,
            is_striked=False,
            txt=None,
    ):
        f = FontType(name, puntos, peso, is_italic, is_underlined, is_striked, txt)
        self.setFont(f)
        return self

    def set_wrap(self, activate):
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.WordWrap if activate else QtGui.QTextOption.WrapMode.NoWrap)
        return self

    def capture_changes(self, rutina):
        self.textChanged.connect(rutina)
        return self

    def captura_doble_click(self, rutina):
        self.rutinaDobleClick = rutina
        return self

    def mouseDoubleClickEvent(self, event):
        if self.rutinaDobleClick:
            self.rutinaDobleClick(event)
        else:
            super().mouseDoubleClickEvent(event)

    def position(self):
        return self.textCursor().position()


class Menu(QtWidgets.QMenu):
    """
    Menu popup.

    Ejemplo::

        menu = Controles.Menu(window)

        menu.opcion( "op1", "Primera opcion", icono )
        menu.separador()
        menu.opcion( "op2", "Segunda opcion", icono1 )
        menu.separador()

        menu1 = menu.submenu( "Submenu", icono2 )
        menu1.opcion( "op3_1", "opcion 1", icono3 )
        menu1.separador()
        menu1.opcion( "op3_2", "opcion 2", icono3 )
        menu1.separador()

        resp = menu.lanza()

        if resp:
            if resp == "op1":
                ..........

            elif resp == "op2":
                ................
    """
    is_left: bool
    is_right: bool

    def __init__(self, parent, titulo=None, icono=None, is_disabled=False, puntos=None, bold=True):

        self.parent = parent
        QtWidgets.QMenu.__init__(self, parent)

        if titulo:
            self.setTitle(titulo)
        if icono:
            self.setIcon(icono)

        if is_disabled:
            self.setDisabled(True)

        if puntos:
            tl = FontType(puntos=puntos, peso=75) if bold else FontType(puntos=puntos)
            self.setFont(tl)

        # app = QtWidgets.QApplication.instance()
        # style = app.style().metaObject().className()
        self.si_separadores = True  # style != "QFusionStyle"

    def set_font(self, f):
        self.setFont(f)
        return self

    def set_font_type(
            self,
            name="",
            puntos=8,
            peso=50,
            is_italic=False,
            is_underlined=False,
            is_striked=False,
            txt=None,
    ):
        f = FontType(name, puntos, peso, is_italic, is_underlined, is_striked, txt)
        self.setFont(f)
        return self

    def opcion(
            self,
            key,
            label,
            icono=None,
            is_disabled=False,
            font_type=None,
            is_checked=None,
            tooltip: str = "",
            shortcut: str = "",
    ):
        if icono:
            accion = QtGui.QAction(icono, label, self)
        else:
            accion = QtGui.QAction(label, self)
        accion.key = key
        if is_disabled:
            accion.setDisabled(True)
        if font_type:
            accion.setFont(font_type)
        if is_checked is not None:
            accion.setCheckable(True)
            accion.setChecked(is_checked)
        if tooltip != "":
            accion.setToolTip(tooltip)
        if shortcut:
            accion.setShortcut(QtGui.QKeySequence(shortcut))
        self.addAction(accion)
        return accion

    def submenu(self, label, icono=None, is_disabled=False):
        menu = Menu(self, label, icono, is_disabled)
        menu.setFont(self.font())
        self.addMenu(menu)
        return menu

    def mousePressEvent(self, event):
        self.is_left = event.button() == QtCore.Qt.MouseButton.LeftButton
        self.is_right = event.button() == QtCore.Qt.MouseButton.RightButton
        return QtWidgets.QMenu.mousePressEvent(self, event)

    def separador(self):
        if self.si_separadores:
            self.addSeparator()

    def lanza(self):
        QtCore.QCoreApplication.processEvents()
        QtWidgets.QApplication.processEvents()
        resp = self.exec(QtGui.QCursor.pos())
        if resp:
            return resp.key
        else:
            return None


def equalize_toolbar_buttons(toolbar: QtWidgets.QToolBar) -> int:
    buttons = [toolbar.widgetForAction(a) for a in toolbar.actions() if toolbar.widgetForAction(a)]
    if not buttons:
        return 0

    max_w = max(btn.sizeHint().width() for btn in buttons)

    for btn in buttons:
        btn.setFixedWidth(max_w)

    return max_w


class TB(QtWidgets.QToolBar):
    """
    Crea una barra de tareas simple.

    @param li_acciones: lista de acciones, en forma de tupla = titulo, icono, key
    @param with_text: si muestra texto
    @param icon_size: tama_o del icono
    @param rutina: rutina que se llama al pulsar una opcion. Por defecto sera parent.process_toolbar().
        Y la key enviada se obtiene de self.sender().key
    """

    li_acciones: list
    dic_toolbar: dict

    def __init__(
            self,
            parent,
            li_acciones,
            with_text=True,
            icon_size=32,
            rutina=None,
            puntos=None,
            background=None,
    ):

        QtWidgets.QToolBar.__init__(self, "BASIC", parent)

        self.setIconSize(QtCore.QSize(icon_size, icon_size))

        self.parent = parent

        self.rutina = parent.process_toolbar if rutina is None else rutina

        self.with_text = with_text

        if with_text:
            self.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        self.f = FontType(puntos=puntos) if puntos else None

        if background:
            self.setStyleSheet(f"QWidget {{ background: {background} }}")

        self.set_actions(li_acciones)

    def set_actions(self, li_acciones):
        self.dic_toolbar = {}
        lista = []
        tooltips_bydefault = not self.with_text

        for datos in li_acciones:
            if datos:
                if isinstance(datos, int):
                    self.addWidget(LB("").relative_width(datos))
                else:
                    titulo, icono, key = datos
                    accion = QtGui.QAction(titulo, self.parent)
                    accion.setIcon(icono)
                    accion.setIconText(titulo)
                    accion.triggered.connect(self.rutina)
                    accion.key = key
                    if self.f:
                        accion.setFont(self.f)
                    lista.append(accion)
                    self.addAction(accion)
                    self.dic_toolbar[key] = accion
                    if not tooltips_bydefault:
                        widget = self.widgetForAction(accion)
                        widget.setToolTip("")
            else:
                self.addSeparator()
        self.li_acciones = lista

    def reset(self, li_acciones):
        self.clear()
        self.set_actions(li_acciones)
        self.update()

    def vertical(self):
        self.setOrientation(QtCore.Qt.Orientation.Vertical)
        return self

    def set_action_visible(self, key, value):
        for accion in self.li_acciones:
            if accion.key == key:
                accion.setVisible(value)

    def set_same_width(self) -> int:
        return equalize_toolbar_buttons(self)

    # def mousePressEvent(self, event: QtGui.QMouseEvent):
    #     if event.button() == QtCore.Qt.MouseButton.RightButton:
    #         if hasattr(self.parent, "toolbar_rightmouse"):
    #             self.parent.toolbar_rightmouse()
    #             return
    #     QtWidgets.QToolBar.mousePressEvent(self, event)


class TBrutina(QtWidgets.QToolBar):
    """
    Crea una barra de tareas simple.

    @param li_acciones: lista de acciones, en forma de tupla = titulo, icono, key
    @param with_text: si muestra texto
    @param icon_size: tama_o del icono
        Y la key enviada se obtiene de self.sender().key
    """

    li_acciones: list
    dic_toolbar: dict

    def __init__(
            self,
            parent,
            li_acciones=None,
            with_text=True,
            icon_size=None,
            puntos=None,
            background=None,
            style=None,
    ):

        QtWidgets.QToolBar.__init__(self, "BASIC", parent)
        self.tooltip_default = False
        if style:
            self.setToolButtonStyle(style)
            if style != QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon and icon_size is None:
                icon_size = 16
        elif with_text:
            self.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        else:
            self.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)

        self.with_text = with_text

        tam = 32 if icon_size is None else icon_size
        self.setIconSize(QtCore.QSize(tam, tam))

        self.parent = parent

        self.f = FontType(puntos=puntos) if puntos else None

        if background:
            self.setStyleSheet(f"QWidget {{ background: {background} }}")

        if li_acciones:
            self.set_actions(li_acciones)

        else:
            self.dic_toolbar = {}
            self.li_acciones = []

    def new(self, titulo, icono, key, sep=True, tool_tip=None):
        accion = QtGui.QAction(titulo, self.parent)
        accion.setIcon(icono)
        accion.setIconText(titulo)
        if tool_tip:
            accion.setToolTip(tool_tip)

        accion.triggered.connect(key)
        if self.f:
            accion.setFont(self.f)
        self.li_acciones.append(accion)
        self.addAction(accion)
        self.dic_toolbar[key] = accion
        if sep:
            self.addSeparator()

        if tool_tip is None and self.with_text:
            widget = self.widgetForAction(accion)
            widget.setToolTip("")

    def set_actions(self, li_acc):
        self.dic_toolbar = {}
        self.li_acciones = []
        for datos in li_acc:
            if datos:
                if isinstance(datos, int):
                    self.addWidget(LB("").relative_width(datos))
                elif len(datos) == 3:
                    titulo, icono, key = datos
                    self.new(titulo, icono, key, False)
                else:
                    titulo, icono, key, tool_tip = datos
                    self.new(titulo, icono, key, False, tool_tip=tool_tip)
            else:
                self.addSeparator()

    def reset(self, li_acciones):
        self.clear()
        self.set_actions(li_acciones)
        self.update()

    def remove_tooltips(self):
        if self.with_text:
            for action in self.dic_toolbar.values():
                widget = self.widgetForAction(action)
                if widget:
                    widget.setToolTip("")

    def vertical(self):
        self.setOrientation(QtCore.Qt.Orientation.Vertical)
        return self

    def set_pos_visible(self, pos, value):
        self.li_acciones[pos].setVisible(value)

    def set_action_visible(self, key, value):
        accion = self.dic_toolbar.get(key, None)
        if accion:
            accion.setVisible(value)

    def set_action_enabled(self, key, value):
        accion = self.dic_toolbar.get(key, None)
        if accion:
            accion.setEnabled(value)

    def set_action_title(self, key, title):
        accion: QtGui.QAction
        accion = self.dic_toolbar.get(key, None)
        if accion:
            accion.setIconText(title)
            accion.setToolTip(title)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        QtWidgets.QToolBar.mousePressEvent(self, event)

    def set_same_width(self) -> int:
        return equalize_toolbar_buttons(self)


class FontType(QtGui.QFont):
    def __init__(
            self,
            name="",
            puntos=0,
            peso=50,
            is_italic=False,
            is_underlined=False,
            is_striked=False,
            txt=None,
            more_puntos=0,
    ):
        QtGui.QFont.__init__(self)
        if txt is None:
            if puntos == 0 or more_puntos > 0:
                font = QtWidgets.QApplication.font()
                puntos = font.pointSize() + more_puntos
            cursiva = 1 if is_italic else 0
            subrayado = 1 if is_underlined else 0
            tachado = 1 if is_striked else 0
            if not name:
                font = QtWidgets.QApplication.font()
                name = font.family()
            txt = f"{name},{puntos},-1,5,{peso},{cursiva},{subrayado},{tachado},0,0"
        self.fromString(txt)


class Tab(QtWidgets.QTabWidget):
    def new_tab(self, widget, texto, pos=None):
        if pos is None:
            self.addTab(widget, texto)
            pos = self.currentIndex()
        else:
            self.insertTab(pos, widget, texto)
        self.set_tooltip_x(pos, "")

    def set_tooltip_x(self, pos, txt):
        p = self.tabBar().tabButton(pos, QtWidgets.QTabBar.ButtonPosition.RightSide)
        if p:
            p.setToolTip(txt)

    def current_position(self):
        return self.currentIndex()

    def set_value(self, cual, valor):
        self.setTabText(cual, valor)

    def activate(self, cual):
        self.setCurrentIndex(cual)

    def set_position(self, pos):
        rpos = self.TabPosition.North
        if pos == "S":
            rpos = self.TabPosition.South
        elif pos == "E":
            rpos = self.TabPosition.East
        elif pos == "W":
            rpos = self.TabPosition.West
        self.setTabPosition(rpos)
        return self

    def set_position_south(self):
        self.setTabPosition(self.TabPosition.South)
        return self

    def set_position_east(self):
        self.setTabPosition(self.TabPosition.East)
        return self

    def set_position_west(self):
        self.setTabPosition(self.TabPosition.West)
        return self

    def set_icono(self, pos, icono):
        if icono is None:
            icono = QtGui.QIcon()
        self.setTabIcon(pos, icono)

    def set_font(self, f):
        self.setFont(f)
        return self

    def set_font_type(
            self,
            name="",
            puntos=8,
            peso=50,
            is_italic=False,
            is_underlined=False,
            is_striked=False,
            txt=None,
    ):
        f = FontType(name, puntos, peso, is_italic, is_underlined, is_striked, txt)
        self.setFont(f)
        return self

    def dispatch_change(self, dispatch):
        self.currentChanged.connect(dispatch)

    def quita_x(self, pos):
        self.tabBar().tabButton(pos, QtWidgets.QTabBar.ButtonPosition.RightSide).hide()

        # def formaTriangular( self ):
        # self.setTabShape(self.Triangular)


class SL(QtWidgets.QSlider):
    def __init__(self, parent, minimo, maximo, nvalor, dispatch, tick=10, step=1):
        QtWidgets.QSlider.__init__(self, QtCore.Qt.Orientation.Horizontal, parent)

        self.setMinimum(minimo)
        self.setMaximum(maximo)

        self.dispatch = dispatch
        if tick:
            self.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
            self.setTickInterval(tick)
        self.setSingleStep(step)

        self.setValue(nvalor)

        self.valueChanged.connect(self.movido)

    def set_value(self, nvalor):
        self.setValue(nvalor)
        return self

    def movido(self, valor):
        if self.dispatch:
            self.dispatch()

    def valor(self):
        return self.value()

    def set_width(self, px):
        self.setFixedWidth(calc_fixed_width(px))
        return self


class GetDate(QtWidgets.QDateTimeEdit):
    def __init__(self, owner, date: datetime.date):
        QtWidgets.QDateTimeEdit.__init__(self, owner)

        self.setDisplayFormat("yyyy-MM-dd")

        self.setCalendarPopup(True)
        calendar = QtWidgets.QCalendarWidget()
        calendar.setFirstDayOfWeek(QtCore.Qt.DayOfWeek.Monday)
        calendar.setGridVisible(True)
        self.setCalendarWidget(calendar)

        self.setDate(self.date2qdate(date))

    @staticmethod
    def date2qdate(date: datetime.date):
        qdate = QtCore.QDate()
        qdate.setDate(date.year, date.month, date.day)
        return qdate

    def set_date(self, date: datetime.date):
        self.setDate(self.date2qdate(date))

    def pydate(self):
        return self.date().toPython()
