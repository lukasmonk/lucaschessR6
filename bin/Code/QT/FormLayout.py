"""
formlayout adapted to Lucas Chess
=================================

Original formlayout License Agreement (MIT License)
---------------------------------------------------

Copyright (c) 2009 Pierre Raybaut

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

__license__ = __doc__

import os
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

import Code
from Code.QT import Colocacion, Controles, Iconos, QTDialogs, QTMessages, SelectFiles

separador = (None, None)
(
    SPINBOX,
    COMBOBOX,
    COLORBOX,
    DIAL,
    SLIDER,
    EDITBOX,
    FICHERO,
    CARPETA,
    FONTCOMBOBOX,
    CHSPINBOX,
) = range(10)


class FormLayout:
    def __init__(
            self,
            parent,
            title,
            icon,
            with_default=False,
            minimum_width=None,
            dispatch=None,
            font_txt=None,
    ):
        self.parent = parent
        self.title = title
        self.icon = icon
        self.font_txt = font_txt
        self.with_default = with_default
        self.minimum_width = minimum_width
        self.dispatch = dispatch

        self.li_gen = []
        self.li_tabs = []

    def separador(self):
        self.li_gen.append(separador)

    def base(self, config, valor):
        self.li_gen.append((config, valor))

    def eddefault(self, label: str, init_value):
        self.li_gen.append((f"{label}:", init_value))

    def edit_np(self, label: str, init_value):
        self.li_gen.append((label, init_value))

    def edit(self, label: str, init_value: str):
        self.eddefault(label, init_value)

    def editbox(
            self,
            label,
            ancho=None,
            rx=None,
            tipo=None,
            is_password=False,
            alto=1,
            decimales=1,
            init_value=None,
            negatives=False,
            tooltip=None,
    ):
        self.li_gen.append(
            (
                Editbox(
                    label,
                    ancho,
                    rx,
                    tipo,
                    is_password,
                    alto,
                    decimales,
                    negatives=negatives,
                    tooltip=tooltip,
                ),
                init_value,
            )
        )

    def seconds(self, label: str, init_value: float):
        self.editbox(label, ancho=60, tipo=float, init_value=init_value)

    def minutes(self, label: str, init_value: float):
        self.editbox(label, ancho=60, tipo=float, init_value=init_value, decimales=2)

    def combobox(self, label, lista, init_value, is_editable=False, tooltip=None):
        self.li_gen.append((Combobox(label, lista, is_editable, tooltip), init_value))

    def checkbox(self, label: str, init_value: bool):
        self.eddefault(label, init_value)

    # def float(self, label: str, init_value: float):
    #     self.eddefault(label, float(init_value) if init_value else 0.0)

    def spinbox(self, label, minimo, maximo, ancho, init_value):
        self.li_gen.append((Spinbox(label, minimo, maximo, ancho), init_value))

    def font(self, label, init_value):
        self.li_gen.append((FontCombobox(label), init_value))

    def file(self, label, extension, si_save, init_value, is_relative=True, minimum_width=None, file_default="",
             li_histo=None):
        self.li_gen.append(
            (
                Fichero(
                    label,
                    extension,
                    si_save,
                    is_relative,
                    minimum_width,
                    file_default,
                    li_histo,
                ),
                init_value,
            )
        )

    def filename(self, label: str, init_value: str):
        self.li_gen.append((Editbox(label, rx="[^\\:/|?*^%><()]*"), init_value))

    def folder(self, label, init_value, folder_default):
        self.li_gen.append((Carpeta(label, folder_default), init_value))

    def dial(self, label, minimo, maximo, init_value, siporc=True):
        self.li_gen.append((Dial(label, minimo, maximo, siporc), init_value))

    def slider(self, label, minimo, maximo, init_value, siporc=True):
        sld = XSlider(label, minimo, maximo, siporc)
        self.li_gen.append((sld, init_value))

    def apart(self, title):
        self.li_gen.append((None, f"{title}:"))

    def apart_np(self, title):
        self.li_gen.append((None, title))

    def apart_simple(self, title):
        self.li_gen.append((None, f"${title}:"))

    def apart_simple_np(self, title):
        self.li_gen.append((None, f"${title}"))

    def apart_nothtml_np(self, title):
        self.li_gen.append((None, f"@|{title}"))

    def add_tab(self, title):
        self.li_tabs.append((self.li_gen, title, ""))
        self.li_gen = []

    def run(self):
        li = self.li_tabs if self.li_tabs else self.li_gen

        return fedit(
            li,
            title=self.title,
            parent=self.parent,
            minimum_width=self.minimum_width,
            icon=self.icon,
            if_default=self.with_default,
            dispatch=self.dispatch,
            font=self.font_txt,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class Spinbox:
    def __init__(self, label, minimo, maximo, ancho):
        self.tipo = SPINBOX
        self.label = f"{label}:"
        self.minimo = minimo
        self.maximo = maximo
        self.ancho = ancho


class CHSpinbox:
    def __init__(self, label, minimo, maximo, ancho, chlabel):
        self.tipo = CHSPINBOX
        self.label = f"{label}:"
        self.chlabel = chlabel
        self.minimo = minimo
        self.maximo = maximo
        self.ancho = ancho


class Combobox:
    def __init__(self, label, lista, is_editable=False, tooltip=None, extend_seek=False):
        self.tipo = COMBOBOX
        self.lista = lista  # (key,titulo),....
        self.label = f"{label}:"
        self.is_editable = is_editable
        self.extend_seek = extend_seek
        self.tooltip = tooltip


class FontCombobox:
    def __init__(self, label):
        self.tipo = FONTCOMBOBOX
        self.label = f"{label}:"


class Colorbox:
    def __init__(self, label, ancho, alto, is_checked=False, is_str=False):
        self.tipo = COLORBOX
        self.ancho = ancho
        self.alto = alto
        self.is_checked = is_checked
        self.is_str = is_str
        self.label = f"{label}:"


class Editbox:
    def __init__(
            self,
            label,
            ancho=None,
            rx=None,
            tipo=None,
            is_password=False,
            alto=1,
            decimales=1,
            negatives=False,
            tooltip=None,
    ):
        self.tipo = EDITBOX
        self.label = f"{label}:"
        self.ancho = ancho
        self.rx = rx
        self.tipoCampo = str if tipo is None else tipo
        self.is_password = is_password
        self.alto = alto
        self.decimales = decimales
        self.negatives = negatives
        self.tooltip = tooltip


class Casillabox(Editbox):
    def __init__(self, label):
        Editbox.__init__(self, label, ancho=24, rx="[a-h][1-8]")


class Dial:
    def __init__(self, label, minimo, maximo, siporc=True):
        self.tipo = DIAL
        self.minimo = minimo
        self.maximo = maximo
        self.siporc = siporc
        self.label = f"\n{label}:"


class XSlider:
    def __init__(self, label, minimo, maximo, siporc):
        self.tipo = SLIDER
        self.minimo = minimo
        self.maximo = maximo
        self.siporc = siporc
        self.label = label
        if ":" not in label:
            label += ":"


class Carpeta:
    def __init__(self, label, carpeta_defecto):
        self.tipo = CARPETA
        self.label = f"{label}:"
        self.folder_default = carpeta_defecto


class Fichero:
    def __init__(
            self,
            label,
            extension,
            is_save,
            is_relative=True,
            minimum_width=None,
            file_default="",
            li_histo=None,
    ):
        self.tipo = FICHERO
        self.extension = extension
        self.is_save = is_save
        self.label = f"{label}:"
        self.is_relative = is_relative
        self.minimum_width = minimum_width
        self.file_default = file_default
        self.li_histo = li_histo


class BotonFichero(QtWidgets.QPushButton):
    def __init__(self, file, extension, si_save, si_relativo, minimum_width, fichero_defecto):
        QtWidgets.QPushButton.__init__(self)
        self.clicked.connect(self.change_file)
        self.file = file
        self.extension = extension
        self.is_save = si_save
        self.is_relative = si_relativo
        self.minimum_width = minimum_width
        if minimum_width:
            self.setMinimumWidth(minimum_width)
        self.qm = QtGui.QFontMetrics(self.font())
        self.file = file
        self.file_default = fichero_defecto
        self.is_first_time = True

    def change_file(self):
        titulo = _("File to save") if self.is_save else _("File to read")
        fbusca = self.file if self.file else self.file_default
        if self.is_save:
            resp = SelectFiles.salvaFichero(self, titulo, fbusca, self.extension, True)
        else:
            resp = SelectFiles.leeFichero(self, fbusca, self.extension, titulo=titulo)
        if resp:
            self.set_filepath(resp)

    def set_filepath(self, txt):
        self.file = txt
        if txt:
            txt = os.path.realpath(txt)
            if self.is_relative:
                txt = Code.relative_root(txt)
            tam_txt = self.qm.boundingRect(txt).width()
            tmax = self.width() - 10
            if self.is_first_time:
                self.is_first_time = False
                tmax = self.minimum_width if self.minimum_width else tmax

            while tam_txt > tmax:
                txt = txt[1:]
                tam_txt = self.qm.boundingRect(txt).width()

        self.setText(txt)


class LBotonFichero(QtWidgets.QHBoxLayout):
    def __init__(self, parent, config, file):
        QtWidgets.QHBoxLayout.__init__(self)

        if config.li_histo and not config.file_default:
            config.file_default = os.path.dirname(config.li_histo[0])

        self.boton = BotonFichero(
            file,
            config.extension,
            config.is_save,
            config.is_relative,
            config.minimum_width,
            config.file_default,
        )
        bt_cancelar = Controles.PB(parent, "", self.cancelar)
        bt_cancelar.set_icono(Iconos.Delete()).relative_width(16)
        self.parent = parent

        self.addWidget(self.boton)
        self.addWidget(bt_cancelar)

        if config.li_histo:
            bt_historico = Controles.PB(parent, "", self.historico).set_icono(Iconos.Favoritos())
            self.addWidget(bt_historico)
            self.li_histo = config.li_histo
        self.boton.set_filepath(file)

    def historico(self):
        if self.li_histo:
            menu = Controles.Menu(self.parent, puntos=8)
            menu.setToolTip(_("To choose: <b>left button</b> <br>To erase: <b>right button</b>"))
            for file in self.li_histo:
                menu.opcion(file, file, Iconos.PuntoAzul())

            resp = menu.lanza()
            if resp:
                if menu.is_left:
                    self.boton.set_filepath(resp)
                elif menu.is_right:
                    if QTMessages.pregunta(
                            self.parent,
                            _("Do you want to remove file %s from the list?") % resp,
                    ):
                        del self.li_histo[self.li_histo.index(resp)]

    def cancelar(self):
        self.boton.set_filepath("")


class LBotonCarpeta(QtWidgets.QHBoxLayout):
    def __init__(self, parent, config, carpeta):
        QtWidgets.QHBoxLayout.__init__(self)

        self.config = config
        self.parent = parent

        self.carpeta = carpeta
        self.boton = Controles.PB(parent, self.carpeta, self.change_folder, plano=False)
        bt_cancelar = Controles.PB(parent, "", self.cancelar)
        bt_cancelar.set_icono(Iconos.Delete()).relative_width(16)
        self.parent = parent

        self.addWidget(self.boton)
        self.addWidget(bt_cancelar)

    def change_folder(self):
        carpeta = SelectFiles.get_existing_directory(self.parent, self.carpeta, self.config.label)
        if carpeta:
            self.carpeta = os.path.abspath(carpeta)
            self.boton.set_text(carpeta)

    def cancelar(self):
        self.carpeta = self.config.folder_default
        self.boton.set_text(self.carpeta)


class BotonColor(QtWidgets.QPushButton):
    def __init__(self, parent, ancho, alto, is_str, dispatch):
        QtWidgets.QPushButton.__init__(self, parent)

        self.setFixedSize(Controles.calc_fixed_width(ancho), Controles.calc_fixed_width(alto))

        self.clicked.connect(self.pulsado)

        self.xcolor = "" if is_str else -1

        self.is_str = is_str

        self.dispatch = dispatch

    def set_color_foreground(self, xcolor):

        self.xcolor = xcolor

        if self.is_str:
            color = QtGui.QColor(xcolor)
        else:
            color = QtGui.QColor()
            color.setRgba(xcolor)
        self.setStyleSheet(f"QWidget {{ background-color: {color.name()} }}")

    def pulsado(self):
        if self.is_str:
            color = QtGui.QColor(self.xcolor)
        else:
            color = QtGui.QColor()
            color.setRgba(self.xcolor)
        color = QTDialogs.select_color(color)
        if color:
            if self.is_str:
                self.set_color_foreground(color.name())
            else:
                self.set_color_foreground(color.rgba())
        if self.dispatch:
            self.dispatch()

    def value(self):
        return self.xcolor


class BotonCheckColor(QtWidgets.QHBoxLayout):
    def __init__(self, parent, ancho, alto, dispatch):
        QtWidgets.QHBoxLayout.__init__(self)

        self.boton = BotonColor(parent, ancho, alto, False, dispatch)
        self.checkbox = QtWidgets.QCheckBox(parent)
        x20 = Controles.calc_fixed_width(20)
        self.checkbox.setFixedSize(x20, x20)

        self.checkbox.clicked.connect(self.pulsado)

        self.dispatch = dispatch

        self.addWidget(self.checkbox)
        self.addWidget(self.boton)

    def set_color_foreground(self, ncolor):
        if ncolor == -1:
            self.boton.hide()
            self.checkbox.setChecked(False)
        else:
            self.boton.show()
            self.checkbox.setChecked(True)
            self.boton.set_color_foreground(ncolor)

    def value(self):
        if self.checkbox.isChecked():
            return self.boton.xcolor
        else:
            return -1

    def pulsado(self):
        if self.checkbox.isChecked():
            if self.boton.xcolor == -1:
                self.boton.set_color_foreground(0)
                self.boton.pulsado()
            else:
                self.boton.set_color_foreground(self.boton.xcolor)
            self.boton.show()
        else:
            self.boton.hide()
        if self.dispatch:
            self.dispatch()


class Edit(Controles.ED):
    def __init__(self, parent, config, dispatch):
        Controles.ED.__init__(self, parent)
        if dispatch:
            self.textChanged.connect(dispatch)

        if config.rx:
            self.controlrx(config.rx)
        if config.ancho:
            self.relative_width(config.ancho)
        if config.is_password:
            self.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.tipo = config.tipoCampo
        self.decimales = config.decimales
        if self.tipo is float:
            if config.negatives:
                self.controlrx(rf"^-?\d+(\.\d{{1,{self.decimales}}})?$")
            else:
                self.controlrx(rf"\d+(\.\d{{1,{self.decimales}}})?$")

    def valor(self):
        if self.tipo is int:
            v = self.text_to_integer()
        elif self.tipo is float:
            v = self.text_to_float()
        else:
            v = self.texto()
        return v


class TextEdit(Controles.EM):
    def __init__(self, parent, config, dispatch):
        Controles.EM.__init__(self, parent)
        if dispatch:
            self.textChanged.connect(dispatch)

        self.minimum_height(config.alto)

    def valor(self):
        return self.texto()


class DialNum(Colocacion.H):
    def __init__(self, parent, config, dispatch):
        Colocacion.H.__init__(self)

        self.dial = QtWidgets.QDial(parent)
        self.dial.setMinimum(config.minimo)
        self.dial.setMaximum(config.maximo)
        self.dial.setNotchesVisible(True)
        x40 = Controles.calc_fixed_width(40)
        self.dial.setFixedSize(x40, x40)
        self.lb = QtWidgets.QLabel(parent)

        self.dispatch = dispatch

        self.siporc = config.siporc

        self.dial.valueChanged.connect(self.movido)

        self.addWidget(self.dial)
        self.addWidget(self.lb)

    def set_value(self, nvalor):
        self.dial.setValue(nvalor)
        self.set_txt_label()

    def set_txt_label(self):
        txt = f"{self.dial.value()}"
        if self.siporc:
            txt += "%"
        self.lb.setText(txt)

    def movido(self, _valor):
        self.set_txt_label()
        if self.dispatch:
            self.dispatch()

    def value(self):
        return self.dial.value()


class Slider(Colocacion.H):
    def __init__(self, parent, config, dispatch):
        Colocacion.H.__init__(self)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, parent)
        self.slider.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBothSides)
        self.slider.setTickInterval(1)
        self.slider.setSingleStep(1)
        self.slider.setMinimum(config.minimo)
        self.slider.setMaximum(config.maximo)

        self.slider.valueChanged.connect(self.movido)
        self.lb = QtWidgets.QLabel(parent)

        self.dispatch = dispatch

        self.siporc = config.siporc

        self.control(self.slider)
        self.control(self.lb)

        # self.set_value()

    def set_txt_label(self):
        txt = f"{self.slider.value()}"
        if self.siporc:
            txt += "%"
        self.lb.setText(txt)

    def set_value(self, value):
        self.slider.setValue(value)
        self.set_txt_label()

    def movido(self, _value):
        self.set_txt_label()
        if self.dispatch:
            self.dispatch()

    def value(self):
        return self.slider.value()


class FormWidget(QtWidgets.QWidget):
    def __init__(self, data, comment="", parent=None, dispatch=None):
        super(FormWidget, self).__init__(parent)
        self.data = data
        self.widgets = []
        self.labels = []
        self.formlayout = QtWidgets.QFormLayout(self)
        if comment:
            self.formlayout.addRow(QtWidgets.QLabel(comment, self))
            self.formlayout.addRow(QtWidgets.QLabel(" ", self))

        self.setup(dispatch)

    def setup(self, dispatch):
        for label, value in self.data:

            # Separador
            if label is None and value is None:
                self.formlayout.addRow(QtWidgets.QLabel(" ", self), QtWidgets.QLabel(" ", self))
                self.widgets.append(None)
                self.labels.append(None)

            # Comentario
            elif label is None:
                if value.startswith("$"):
                    lb = Controles.LB(self, value[1:])
                elif value.startswith("@|"):
                    lb = Controles.LB(self, value[2:])
                    lb.setTextFormat(QtCore.Qt.TextFormat.PlainText)
                    lb.setWordWrap(True)
                else:
                    lb = Controles.LB(self, QTMessages.resalta(value, 3))
                self.formlayout.addRow(lb)
                self.widgets.append(None)
                self.labels.append(None)

            else:
                field = None
                # Otros tipos
                if not isinstance(label, (bytes, str)):
                    config = label
                    tipo = config.tipo
                    if tipo == SPINBOX:
                        field = QtWidgets.QSpinBox(self)
                        field.setMinimum(config.minimo)
                        field.setMaximum(config.maximo)
                        field.setValue(value)
                        field.setFixedWidth(Controles.calc_fixed_width(config.ancho))
                        if dispatch:
                            field.valueChanged.connect(dispatch)
                    elif tipo == COMBOBOX:
                        field = Controles.CB(self, config.lista, value, extend_seek=config.extend_seek)
                        if config.is_editable:
                            field.setEditable(True)
                        if config.tooltip:
                            field.setToolTip(config.tooltip)

                        field.lista = config.lista
                        if dispatch:
                            field.currentIndexChanged.connect(dispatch)
                            # field = QtWidgets.QComboBox(self)
                            # for n, tp in enumerate(config.lista):
                            # if len(tp) == 3:
                            # field.addItem( tp[2], tp[0], tp[1] )
                            # else:
                            # field.addItem( tp[0], tp[1] )
                            # if tp[1] == value:
                            # field.setCurrentIndex( n )
                            # if dispatch:
                            # field.currentIndexChanged.connect( dispatch )
                    elif tipo == FONTCOMBOBOX:
                        field = QtWidgets.QFontComboBox(self)
                        if value:
                            font = Controles.FontType(value)
                            field.setCurrentFont(font)
                    elif tipo == COLORBOX:
                        if config.is_checked:
                            field = BotonCheckColor(self, config.ancho, config.alto, dispatch)
                        else:
                            field = BotonColor(self, config.ancho, config.alto, config.is_str, dispatch)
                        field.set_color_foreground(value)

                    elif tipo == DIAL:
                        field = DialNum(self, config, dispatch)
                        field.set_value(value)

                    elif tipo == SLIDER:
                        field = Slider(self, config, dispatch)
                        field.set_value(value)

                    elif tipo == EDITBOX:
                        if config.alto == 1:
                            field = Edit(self, config, dispatch)
                            tp = config.tipoCampo
                            if tp is str:
                                field.set_text(value)
                            elif tp is int:
                                field.type_integer()
                                field.set_integer(value)
                            elif tp is float:
                                field.align_right()
                                # field.type_float(0.0)
                                field.set_float(value)
                        else:
                            field = TextEdit(self, config, dispatch)
                            field.set_text(value)
                        if config.tooltip:
                            field.setToolTip(config.tooltip)

                    elif tipo == FICHERO:
                        field = LBotonFichero(self, config, value)

                    elif tipo == CARPETA:
                        field = LBotonCarpeta(self, config, value)

                    label = config.label

                # Fichero
                elif isinstance(value, dict):
                    file = value["FICHERO"]
                    extension = value.get("EXTENSION", "pgn")
                    si_save = value.get("SISAVE", True)
                    si_relativo = value.get("SIRELATIVO", True)
                    field = BotonFichero(file, extension, si_save, si_relativo, 250, file)
                # Texto
                elif isinstance(value, (bytes, str)):
                    field = QtWidgets.QLineEdit(value, self)

                # Combo
                elif isinstance(value, (list, tuple)):
                    selindex = value.pop(0)
                    field = QtWidgets.QComboBox(self)
                    if isinstance(value[0], (list, tuple)):
                        keys = [key for key, _val in value]
                        value = [val for _key, val in value]
                    else:
                        keys = value
                    field.addItems(value)
                    if selindex in value:
                        selindex = value.index(selindex)
                    elif selindex in keys:
                        selindex = keys.index(selindex)
                    else:
                        selindex = 0
                    field.setCurrentIndex(selindex)

                # Checkbox
                elif isinstance(value, bool):
                    field = QtWidgets.QCheckBox(" ", self)
                    field.setCheckState(QtCore.Qt.CheckState.Checked if value else QtCore.Qt.CheckState.Unchecked)
                    if dispatch:
                        field.stateChanged.connect(dispatch)

                # Float seconds
                elif isinstance(value, float):  # Para los seconds
                    v = f"{value:0.1f}"
                    field = QtWidgets.QLineEdit(v, self)
                    validator = QtGui.QDoubleValidator(0.0, 36000.0, 1, field)
                    validator.setNotation(QtGui.QDoubleValidator.Notation.StandardNotation)
                    validator.setLocale(QtCore.QLocale.c())
                    field.setValidator(validator)  # Para los seconds
                    field.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
                    field.setFixedWidth(Controles.calc_fixed_width(40))

                # Numero
                elif isinstance(value, int):
                    field = QtWidgets.QSpinBox(self)
                    field.setMaximum(9999)
                    field.setValue(value)
                    field.setFixedWidth(Controles.calc_fixed_width(80))

                # Linea
                else:
                    field = QtWidgets.QLineEdit(repr(value), self)

                self.formlayout.addRow(label, field)
                self.formlayout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
                self.widgets.append(field)
                self.labels.append(label)

    def get(self):
        valuelist = []
        for index, (label, value) in enumerate(self.data):
            field = self.widgets[index]
            if label is None:
                # Separator / Comment
                continue
            elif not isinstance(label, (bytes, str)):
                config = label
                tipo = config.tipo
                if tipo == SPINBOX:
                    value = int(field.value())
                elif tipo == COMBOBOX:
                    n = field.currentIndex()
                    value = field.lista[n][1]
                elif tipo == FONTCOMBOBOX:
                    value = field.currentFont().family()
                elif tipo == COLORBOX:
                    value = field.value()
                elif tipo == DIAL:
                    value = field.value()
                elif tipo == SLIDER:
                    value = field.value()
                elif tipo == EDITBOX:
                    value = field.valor()
                elif tipo == FICHERO:
                    value = field.boton.file
                elif tipo == CARPETA:
                    value = field.carpeta

            elif isinstance(value, (bytes, str)):
                value = field.text()
            elif isinstance(value, dict):
                value = field.file
            elif isinstance(value, (list, tuple)):
                index = int(field.currentIndex())
                if isinstance(value[0], (list, tuple)):
                    value = value[index][0]
                else:
                    value = value[index]
            elif isinstance(value, bool):
                value = field.checkState() == QtCore.Qt.CheckState.Checked
            elif isinstance(value, float):
                txt = field.text()
                if "," in txt:
                    txt = txt.replace(",", ".")
                while txt.count(".") > 1:
                    x = txt.index(".")
                    txt = txt[:x] + txt[x + 1:]
                try:
                    value = float(txt)
                except ValueError:
                    value = 0.0
            elif isinstance(value, int):
                value = int(field.value())
            else:
                value = field.text()
            valuelist.append(value)
        return valuelist

    def get_widget(self, number):
        n = -1
        for index in range(len(self.data)):
            field = self.widgets[index]
            if field is not None:
                n += 1
                if n == number:
                    return field
        return None


class FormTabWidget(QtWidgets.QWidget):
    def __init__(self, datalist, comment="", parent=None, dispatch=None):
        super(FormTabWidget, self).__init__(parent)
        layout = Colocacion.V()
        self.tabwidget = QtWidgets.QTabWidget()
        layout.control(self.tabwidget)
        self.setLayout(layout)
        self.widgetlist = []
        for data, title, comment in datalist:
            widget = FormWidget(data, comment=comment, parent=self, dispatch=dispatch)
            index = self.tabwidget.addTab(widget, title)
            self.tabwidget.setTabToolTip(index, comment)
            self.widgetlist.append(widget)

    def get(self):
        return [widget.get() for widget in self.widgetlist]

    def get_widget(self, num_tab, number):
        return self.widgetlist[num_tab].get_widget(number)


class FormDialog(QtWidgets.QDialog):
    data: Any
    accion: str

    def __init__(
            self,
            data,
            title="",
            comment="",
            icon=None,
            parent=None,
            if_default=True,
            dispatch=None,
            li_extra_options=None,
    ):
        super(FormDialog, self).__init__(parent, QtCore.Qt.WindowType.Dialog)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        flags = self.windowFlags()
        flags &= ~QtCore.Qt.WindowType.WindowContextHelpButtonHint
        self.setWindowFlags(flags)

        # Form
        if isinstance(data[0][0], (list, tuple)):
            self.formwidget = FormTabWidget(data, comment=comment, parent=self, dispatch=dispatch)
            if dispatch:
                dispatch(self.formwidget)
        else:
            self.formwidget = FormWidget(data, comment=comment, parent=self, dispatch=dispatch)
            if dispatch:
                dispatch(self.formwidget)  # enviamos el form de donde tomar datos cuando hay cambios

        tb = QTDialogs.tb_accept_cancel(self, if_default, with_cancel=False)

        layout = Colocacion.V()

        lytb = Colocacion.H().control(tb)
        if li_extra_options:
            tb1 = QTDialogs.LCTB(self, li_extra_options)
            lytb.relleno().control(tb1)
        layout.otro(lytb)

        layout.control(self.formwidget)
        layout.margen(3)

        self.setLayout(layout)

        self.setWindowTitle(title)
        if not isinstance(icon, QtGui.QIcon):
            icon = QtWidgets.QWidget().style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxQuestion)
        self.setWindowIcon(icon)

    def aceptar(self):
        self.accion = "aceptar"
        self.data = self.formwidget.get()
        self.accept()

    def defecto(self):
        self.accion = "defecto"
        if not QTMessages.pregunta(self, _("Are you sure you want to set the default configuration?")):
            return
        self.data = self.formwidget.get()
        self.accept()

    def cancelar(self):
        self.data = None
        self.reject()

    def get(self):
        """Return form result"""
        return self.accion, self.data


def fedit(
        data,
        title="",
        comment="",
        icon=None,
        parent=None,
        if_default=False,
        minimum_width=None,
        dispatch=None,
        font=None,
        li_extra_options=None,
):
    """
    Create form dialog and return result
    (if Cancel button is pressed, return None)

    data: datalist, datagroup

    datalist: list/tuple of (field_name, field_value)
    datagroup: list/tuple of (datalist *or* datagroup, title, comment)

    -> one field for each member of a datalist
    -> one tab for each member of a top-level datagroup
    -> one page (of a multipage widget, each page can be selected with a combo
       box) for each member of a datagroup inside a datagroup

    Supported types for field_value:
      - int, float, str, unicode, bool
      - colors: in Qt-compatible text form, i.e. in hex format or name (red,...)
                (automatically detected from a string)
      - list/tuple:
          * the first element will be the selected index (or value)
          * the other elements can be couples (key, value) or only values
    """
    dialog = FormDialog(data, title, comment, icon, parent, if_default, dispatch, li_extra_options)
    if font:
        dialog.setFont(font)
    if minimum_width:
        dialog.setMinimumWidth(minimum_width)
    if dialog.exec():
        QtCore.QCoreApplication.processEvents()
        QtWidgets.QApplication.processEvents()
        return dialog.get()
    return None
