import locale

from PySide6 import QtWidgets

import Code
from Code.Base.Constantes import ExitProgram
from Code.QT import Colocacion, Iconos, QTDialogs
from Code.QT import Controles, LCDialog, ScreenUtils, QTUtils


class SelectLanguage(LCDialog.LCDialog):
    pbar_labels: QtWidgets.QProgressBar
    pbar_openings: QtWidgets.QProgressBar
    labels_group: QtWidgets.QGroupBox
    openings_group: QtWidgets.QGroupBox
    translators_group: QtWidgets.QGroupBox
    chb_google_labels: Controles.CHB
    chb_google_openings: Controles.CHB
    lb_current_translators: Controles.LB
    lb_previous_translators: Controles.LB
    chb_help_mode: Controles.CHB
    chb_use_local: Controles.CHB
    lb_aviso: Controles.LB
    lb_aviso_openings: Controles.LB
    desc_label: Controles.LB

    def __init__(self, parent):
        self.parent = parent
        extparam = "sel_lng"
        titulo = _("Language")
        if titulo != "Language":
            titulo += " (Language)"
        icono = Iconos.Language()

        LCDialog.LCDialog.__init__(self, parent, titulo, icono, extparam)

        self.apply_styles()

        # Toolbar
        self.tb = QTDialogs.LCTB(self)

        # Selector de idioma
        self.dic_translations = Code.configuration.dic_translations()
        lng_default = Code.configuration.translator()
        self.lng_current = lng_default

        self.pb_lang = Controles.PB(self, " " * 5 + self.dic_translations[lng_default]["NAME"], rutina=self.select_lang)
        self.pb_lang.set_icono(Iconos.Language(), 32)
        self.pb_lang.setObjectName("PbLang")

        # Pestañas
        self.tabs = Controles.Tab(self)
        self.tabs.addTab(self.create_main_config_tab(), _("Labels translation"))
        self.tabs.addTab(self.create_translation_help_tab(), _("Translation Help Mode"))
        self.tabs.set_position_south()

        # Main Layout
        main_layout = Colocacion.V()

        main_layout.control(self.tb)

        # Area de seleccion (Más prominente)
        main_layout.control(self.pb_lang)
        main_layout.control(self.tabs)
        main_layout.margen(15)

        self.setLayout(main_layout)
        self.setMinimumWidth(560)
        self.on_language_changed()

    def apply_styles(self):
        self.setStyleSheet(
            """
/* Selector de idioma */
QPushButton#PbLang {
    padding: 18px 15px;
    min-width: 340px;
    border: 2px solid #d1d1d6;
    border-radius: 8px;
    font-weight: bold;
    font-size: 18px;
}

QGroupBox {
    font-weight: bold;
    border: 2px solid #d1d1d6;
    border-radius: 8px;
    margin-top: 25px;
    padding-top: 15px;
}

QGroupBox::title {
    subcontrol-origin: border;
    subcontrol-position: top left;
    top: -10px;
    left: 15px;
    padding: 0 5px;
    color: gray;
}""")

    def _create_horizontal_section(self, title, content_layout):
        """Helper to create a horizontal section with title and content inside the same frame"""
        section_frame = QtWidgets.QFrame()
        section_frame.setProperty("class", "GroupSection")

        layout = Colocacion.H(section_frame)

        lb_title = Controles.LB(self, title)
        lb_title.setProperty("class", "GroupTitle")
        lb_title.setFixedWidth(140)
        lb_title.align_right()

        content_widget = QtWidgets.QWidget()
        content_widget.setLayout(content_layout)

        layout.control(lb_title).control(content_widget)
        layout.setContentsMargins(0, 5, 10, 5)

        return section_frame

    def create_main_config_tab(self):
        widget = QtWidgets.QWidget()
        layout = Colocacion.V()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        font_avisos = Controles.FontType(more_puntos=-1)

        # Standard Labels Group
        self.labels_group = QtWidgets.QGroupBox(_("Standard Labels"))
        normal_layout = Colocacion.V()
        self.pbar_labels = QtWidgets.QProgressBar(self)
        self.pbar_labels.setFormat("%p%")
        with_google = Code.configuration.x_translator_google
        self.chb_google_labels = Controles.CHB(
            self, _("Use Google translation (offline) to complete missing translations"), with_google
        )
        self.lb_aviso = Controles.LB(self, _("Please note that Google translations may be inaccurate"))
        self.lb_aviso.set_foreground("red").set_font(font_avisos)

        normal_layout.control(self.pbar_labels).espacio(8).control(self.chb_google_labels).control(self.lb_aviso)
        normal_layout.margen(12)
        self.labels_group.setLayout(normal_layout)
        layout.control(self.labels_group)

        # Openings Group
        self.openings_group = QtWidgets.QGroupBox(_("Openings"))
        openings_layout = Colocacion.V()
        self.pbar_openings = QtWidgets.QProgressBar(self)
        self.pbar_openings.setFormat("%p%")
        with_google = Code.configuration.x_translator_google_openings
        self.chb_google_openings = Controles.CHB(
            self, _("Use Google translation (offline) to complete missing translations"), with_google
        )
        self.lb_aviso_openings = Controles.LB(self, _("Please note that Google translations may be inaccurate"))
        self.lb_aviso_openings.set_foreground("red").set_font(font_avisos)

        openings_layout.control(self.pbar_openings).espacio(8).control(self.chb_google_openings)
        openings_layout.control(self.lb_aviso_openings)
        openings_layout.margen(12)
        self.openings_group.setLayout(openings_layout)
        layout.control(self.openings_group)

        # Translators Group
        self.translators_group = QtWidgets.QGroupBox(_("Translators"))
        info_layout = Colocacion.V()
        self.lb_current_translators = Controles.LB(self, "")
        self.lb_current_translators.setWordWrap(True)
        self.lb_current_translators.set_font_type(peso=75)

        self.lb_previous_translators = Controles.LB(self, "")
        self.lb_previous_translators.setWordWrap(True)

        info_layout.control(self.lb_current_translators).espacio(5).control(self.lb_previous_translators).margen(12)
        self.translators_group.setLayout(info_layout)
        layout.control(self.translators_group)

        layout.relleno()
        widget.setLayout(layout)
        return widget

    def create_translation_help_tab(self):
        widget = QtWidgets.QWidget()
        layout = Colocacion.V(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Description with better formatting
        desc_text = (
            f"<h2>{_('Translation Help Mode')}</h2>"
            'Enable this mode if you want to help improve translations:'
        )
        self.desc_label = Controles.LB(self, desc_text)
        self.desc_label.setWordWrap(True)
        layout.control(self.desc_label)

        # Card for Checkbox
        card_check = QtWidgets.QFrame()
        card_check.setStyleSheet("background-color: #f2f2f7; border-radius: 10px; border: 1px solid #d1d1d6;")
        check_layout = Colocacion.V(card_check)
        self.chb_help_mode = Controles.CHB(
            self, _("Activate translator help mode"), Code.configuration.x_translation_mode
        )
        self.chb_help_mode.setStyleSheet("border: none; font-weight: bold; font-size: 14px; color: #007aff;")
        check_layout.control(self.chb_help_mode).margen(15)
        layout.control(card_check)

        # Note
        info_label = QtWidgets.QLabel(
            "<i>Note: This mode is intended for translators and advanced users.<br>"
            "It is designed to facilitate translation by allowing it to be performed "
            "in parallel with the execution of the program, with changes applied immediately.<br>"
            "Translations can be exported to Transifex (the official platform for program translations) "
            "or sent to lukasmonk@gmail.com. Please include the preferred alias/name so authorship can be assigned.<br>"
            "An additional window will open to manage the translation process.</i>"
        )

        info_label.setWordWrap(True)
        layout.control(info_label)

        self.chb_use_local = Controles.CHB(
            self, _("Use locally translated content for everyday operations"), Code.configuration.x_translation_local
        )

        layout.espacio(30).control(self.chb_use_local)

        layout.relleno()

        return widget

    def select_lang(self):
        lng = menu_select_language(self)
        if lng != self.lng_current:
            self.lng_current = lng
            self.on_language_changed()

    def on_language_changed(self):
        """Actualiza la información cuando cambia el idioma seleccionado"""
        english = self.lng_current == "en"
        dic = self.dic_translations[self.lng_current]

        if english:
            porc_labels = 100
            porc_openings = 100
        else:
            porc_labels = int(dic.get("%", 0))
            porc_openings = int(dic.get("%OP", 0))

        self.pbar_labels.setValue(porc_labels)
        self.pbar_openings.setValue(porc_openings)

        self.chb_google_labels.setVisible(porc_labels < 100)
        self.lb_aviso.setVisible(porc_labels < 100)
        self.chb_google_openings.setVisible(porc_openings < 100)
        self.lb_aviso_openings.setVisible(porc_openings < 100)

        # Toolbar
        self.tb.clear()
        self.tb.new(_("Accept"), Iconos.Aceptar(), self.accept_selection)
        self.tb.new(_("Cancel"), Iconos.Cancelar(), self.reject)

        # Button language
        self.pb_lang.set_text(" " * 5 + dic["NAME"])

        # Tabs
        self.tabs.set_value(0, _("Labels translation"))
        self.tabs.set_value(1, _("Translation Help Mode"))

        # Openings group
        self.openings_group.setTitle(_("Openings"))
        self.chb_google_openings.setText(_("Use Google translation (offline) to complete missing translations"))
        self.lb_aviso_openings.setText(_("Please note that Google translations may be inaccurate"))

        # Labels group
        self.labels_group.setTitle(_("Standard Labels"))
        self.chb_google_labels.setText(_("Use Google translation (offline) to complete missing translations"))
        self.lb_aviso.setText(_("Please note that Google translations may be inaccurate"))

        # Translators Group
        self.translators_group.setTitle(_("Translators"))
        current = dic.get("AUTHOR")
        if not current:
            current = _("nobody")
        previous = dic.get("PREVIOUS")
        self.lb_current_translators.set_text(
            f'{_("Current translators")}: <span style="color: #007aff;">{current}</span>'
        )
        if previous:
            self.lb_previous_translators.set_text(f'{_("Previous translators")}: {previous}')
        self.lb_previous_translators.setVisible(bool(previous))

        # Tab help mode
        self.chb_help_mode.setText(_("Activate translator help mode"))
        desc_text = (
            f"<h2>{_('Translation Help Mode')}</h2>"
            'Enable this mode if you want to help improve translations:'
        )
        self.desc_label.set_text(desc_text)
        self.chb_use_local.setText(_("Use locally translated content for everyday operations"))

        ScreenUtils.shrink(self)

    def accept_selection(self):
        configuration = Code.configuration
        lng = self.lng_current
        activate_help_mode = self.chb_help_mode.valor()
        use_local = self.chb_use_local.valor()
        google_labels = self.chb_google_labels.valor()
        google_openings = self.chb_google_openings.valor()
        configuration.set_translation_values(lng, activate_help_mode, use_local, google_labels, google_openings)
        configuration.graba()
        self.accept()
        self.parent.final_processes()
        self.parent.accept()
        QTUtils.exit_application(ExitProgram.REINIT)


def menu_select_language(owner):
    configuration = Code.configuration
    li = configuration.list_translations(True)

    lng_default = Code.configuration.translator()
    name_default = Code.configuration.language()
    li_info = locale.getdefaultlocale()
    if len(li_info) == 2:
        lng = li_info[0][:2]
        for k, name, porc, author, others in li:
            if k == lng:
                name_default = name
                lng_default = lng

    menu = QTDialogs.LCMenuRondo(owner)
    menu.set_font_type(Code.font_mono, puntos=10, peso=700)
    menu.opcion(lng_default, f"By default: {name_default}", Iconos.AceptarPeque())
    menu.separador()

    for k, name, porc, author, others in li:
        option = name
        tam = len(name)
        if k == "zh":  # chinese ocupa el doble
            tam = tam * 2 - 1
        if porc == 100:
            tam += 1
        spaces = " " * (15 - tam)
        if k == "ar":
            option = chr(0x202D) + option
            spaces += " "

        if k != "en":
            if not author:
                author = "      "
            option = f"{option}{spaces}({porc}%) {author}"

        if k == lng_default:
            menu.opcion(k, option, Iconos.AceptarPeque())
        else:
            menu.opcion(k, option)

    menu.separador()
    resp = menu.lanza()
    if resp:
        lng = resp
    else:
        lng = lng_default
    configuration.set_translator(lng)
    configuration.graba()
    configuration.load_translation()
    return lng
