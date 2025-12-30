from typing import Optional

from PySide6 import QtCore, QtWidgets

import Code
from Code.Analysis import WindowAnalysisConfig
from Code.Base.Constantes import (
    BLUNDER,
    INACCURACY,
    MISTAKE,
    POS_TUTOR_HORIZONTAL,
    POS_TUTOR_HORIZONTAL_1_2,
    POS_TUTOR_HORIZONTAL_2_1,
    POS_TUTOR_VERTICAL,
)
from Code.Engines import CheckEngines, Priorities
from Code.QT import (
    Colocacion,
    Columnas,
    Controles,
    Delegados,
    Grid,
    Iconos,
    LCDialog,
    QTDialogs,
    SelectFiles,
)


class WConfEngines(LCDialog.LCDialog):
    me_control: Optional[str]
    me_key: Optional[str]

    def __init__(self, owner):
        icono = Iconos.ConfEngines()
        titulo = _("Engines configuration")
        extparam = "confEngines1"
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, extparam)

        self.configuration = Code.configuration
        self.engine = None
        self.li_uci_options = []
        self.grid_conf = None

        li_acciones = [(_("Close"), Iconos.MainMenu(), self.terminar), None]
        tb = QTDialogs.LCTB(
            self,
            li_acciones,
            style=QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
            icon_size=24,
        )

        self.wconf_tutor = WConfTutor(self)
        self.wconf_analyzer = WConfAnalyzer(self)
        self.wothers = WOthers(self)

        self.w_current = None

        self.tab = Controles.Tab(self)
        self.tab.new_tab(self.wconf_tutor, _("Tutor"))
        self.tab.new_tab(self.wconf_analyzer, _("Analyzer"))
        self.tab.new_tab(self.wothers, _("Others"))
        self.tab.dispatchChange(self.cambiada_tab)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("OPTION", _("UCI option"), 180)
        o_columns.nueva("VALUE", _("Value"), 200, edicion=Delegados.MultiEditor(self))
        o_columns.nueva("DEFAULT", _("By default"), 90)
        self.grid_conf = Grid.Grid(self, o_columns, siSelecFilas=False, is_editable=True)
        self.register_grid(self.grid_conf)

        # Layout
        ly_left = Colocacion.V().control(tb).control(self.tab).margen(0)
        w = QtWidgets.QWidget()
        w.setLayout(ly_left)

        self.splitter = QtWidgets.QSplitter(self)
        self.splitter.addWidget(w)
        self.splitter.addWidget(self.grid_conf)
        self.register_splitter(self.splitter, "conf")
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)

        layout = Colocacion.H().control(self.splitter)
        self.setLayout(layout)

        dic_def = {"_SIZE_": "1209,540", "SP_conf": [719, 463]}
        self.restore_video(with_tam=True, default_dic=dic_def)
        self.cambiada_tab(0)

    def cambiada_tab(self, num):
        if self.w_current:
            self.w_current.save()

        if num == 0:
            w = self.wconf_tutor
        elif num == 1:
            w = self.wconf_analyzer
        else:
            self.engine = None
            self.li_uci_options = None
            self.grid_conf.refresh()
            return
        w.activate_this()
        self.w_current = w

    def me_set_editor(self, parent):
        recno = self.grid_conf.recno()
        opcion = self.li_uci_options[recno]
        key = opcion.name
        value = opcion.valor
        for xkey, xvalue in self.engine.liUCI:
            if xkey == key:
                value = xvalue
                break
        if key is None:
            return None

        control = lista = minimo = maximo = None
        tipo = opcion.tipo
        if tipo == "spin":
            control = "sb"
            minimo = opcion.minimo
            maximo = opcion.maximo
        elif tipo in ("check", "button"):
            if value == "true":
                value = "false"
            else:
                value = "true"
            self.engine.set_uci_option(key, value)
            self.w_current.set_changed()
            self.grid_conf.refresh()
        elif tipo == "combo":
            lista = [(var, var) for var in opcion.li_vars]
            control = "cb"
        elif tipo == "string":
            control = "ed"

        self.me_control = control
        self.me_key = key

        if control == "ed":
            return Controles.ED(parent, value)
        elif control == "cb":
            return Controles.CB(parent, lista, value)
        elif control == "sb":
            return Controles.SB(parent, value, minimo, maximo)
        return None

    def set_engine(self, engine, with_multipv=True):
        self.engine = engine
        if self.grid_conf:
            if self.engine:
                self.li_uci_options = self.engine.li_uci_options_editable()
                if not with_multipv:
                    self.li_uci_options = [op for op in self.li_uci_options if op.name != "MultiPV"]
                self.grid_conf.refresh()
                self.grid_conf.gotop()
                self.grid_conf.show()
            else:
                self.grid_conf.refresh()

    def me_set_value(self, editor, valor):
        if self.me_control == "ed":
            editor.setText(str(valor))
        elif self.me_control in ("cb", "sb"):
            editor.set_value(valor)

    def me_readvalue(self, editor):
        if self.me_control == "ed":
            return editor.texto()
        elif self.me_control in ("cb", "sb"):
            return editor.valor()
        return None

    def grid_setvalue(self, _grid, nfila, _column, valor):
        opcion = self.li_uci_options[nfila]
        self.engine.set_uci_option(opcion.name, valor)
        self.w_current.set_changed()

    def save(self):
        self.wconf_tutor.save()
        self.wconf_analyzer.save()
        self.configuration.graba()
        self.save_video()

    def terminar(self):
        self.save()
        self.accept()

    def closeEvent(self, event):
        self.save()

    def grid_num_datos(self, _grid):
        return len(self.li_uci_options) if self.engine else 0

    def grid_dato(self, _grid, row, o_column):
        key = o_column.key
        op = self.li_uci_options[row]
        if key == "OPTION":
            if op.minimo != op.maximo:
                if op.minimo < 0:
                    return op.name + " (%d - %+d)" % (op.minimo, op.maximo)
                else:
                    return op.name + " (%d - %d)" % (op.minimo, op.maximo)
            else:
                return op.name
        elif key == "DEFAULT":
            df = str(op.default)
            return df.lower() if op.tipo == "check" else df
        else:
            name = op.name
            valor = op.valor
            for xname, xvalue in self.engine.liUCI:
                if xname == name:
                    valor = xvalue
                    break
            valor = str(valor)
            return valor.lower() if op.tipo == "check" else valor

    def grid_bold(self, _grid, row, _o_column):
        op = self.li_uci_options[row]
        return str(op.default).strip().lower() != str(op.valor).strip().lower()


class WConfTutor(QtWidgets.QWidget):
    def __init__(self, owner):
        QtWidgets.QWidget.__init__(self, owner)

        self.configuration = Code.configuration

        self.owner = owner
        self.engine = self.configuration.engines.engine_tutor()

        lb_engine = Controles.LB2P(self, _("Engine"))
        self.cb_engine = Controles.CB(self, self.configuration.engines.list_name_alias_multipv(), self.engine.alias)
        self.cb_engine.capture_changes(self.changed_engine)

        lb_time = Controles.LB2P(self, _("Duration of tutor analysis (secs)"))
        self.ed_time = Controles.ED(self).tipoFloat(self.configuration.x_tutor_mstime / 1000.0).relative_width(50)

        lb_depth = Controles.LB2P(self, _("Depth"))
        self.ed_depth = Controles.ED(self).tipoInt(self.configuration.x_tutor_depth).relative_width(30)

        lb_multipv = Controles.LB2P(self, _("Number of variations evaluated by the engine (MultiPV)"))
        self.ed_multipv = Controles.ED(self).tipoIntPositive(self.configuration.x_tutor_multipv).relative_width(30)
        lb_maximum = Controles.LB(self, _("0 = Maximum"))
        ly_multi = Colocacion.H().control(self.ed_multipv).control(lb_maximum).relleno()

        self.chb_disabled = Controles.CHB(
            self,
            _("Disabled at the beginning of the game"),
            not self.configuration.x_default_tutor_active,
        )
        self.chb_background = Controles.CHB(
            self,
            _("Work in the background, when possible"),
            not self.configuration.x_engine_notbackground,
        )
        lb_priority = Controles.LB2P(self, _("Process priority"))
        self.cb_priority = Controles.CB(self, Priorities.priorities.combo(), self.configuration.x_tutor_priority)
        lb_tutor_position = Controles.LB2P(self, _("Tutor boards position"))
        li_pos_tutor = [
            (_("Horizontal"), POS_TUTOR_HORIZONTAL),
            (_("Horizontal") + " 2+1", POS_TUTOR_HORIZONTAL_2_1),
            (_("Horizontal") + " 1+2", POS_TUTOR_HORIZONTAL_1_2),
            (_("Vertical"), POS_TUTOR_VERTICAL),
        ]
        self.cb_board_position = Controles.CB(self, li_pos_tutor, self.configuration.x_tutor_view)

        lb_sensitivity = Controles.LB2P(self, _("Tutor appearance condition"))
        li_types = [
            (_("Always"), 0),
            (_("Dubious move") + " (?!)", INACCURACY),
            (_("Mistake") + " (?)", MISTAKE),
            (_("Blunder") + " (??)", BLUNDER),
        ]
        self.cb_type = Controles.CB(self, li_types, self.configuration.x_tutor_diftype)

        layout = Colocacion.G()
        layout.controld(lb_engine, 0, 0).control(self.cb_engine, 0, 1)
        layout.controld(lb_time, 1, 0).control(self.ed_time, 1, 1)
        layout.controld(lb_depth, 2, 0).control(self.ed_depth, 2, 1)
        layout.controld(lb_multipv, 3, 0).otro(ly_multi, 3, 1)
        layout.controld(lb_priority, 4, 0).control(self.cb_priority, 4, 1)
        layout.controld(lb_tutor_position, 5, 0).control(self.cb_board_position, 5, 1)
        layout.filaVacia(6, 30)
        layout.controld(lb_sensitivity, 7, 0).control(self.cb_type, 7, 1)
        layout.filaVacia(8, 30)
        layout.control(self.chb_disabled, 9, 0, num_columns=2)
        layout.control(self.chb_background, 10, 0, num_columns=2)

        ly = Colocacion.V().otro(layout).relleno(1)
        lyh = Colocacion.H().otro(ly).relleno(1).margen(30)

        self.setLayout(lyh)

        self.changed_engine()
        self.is_changed = False

        for control in (self.chb_background, self.chb_disabled):
            control.capture_changes(self, self.set_changed)

        for control in (
                self.cb_priority,
                self.cb_board_position,
                self.ed_time,
                self.ed_depth,
                self.ed_multipv,
                self.cb_type,
        ):
            control.capture_changes(self.set_changed)

    def changed_engine(self):
        key = self.cb_engine.valor()
        if key is None or key not in self.configuration.engines.dic_engines():
            key = "stockfish"
        self.engine = self.configuration.engines.dic_engines()[key].clone()
        self.engine.reset_uci_options()
        dic = self.configuration.read_variables("TUTOR_ANALYZER")
        for name, valor in dic.get("TUTOR", []):
            self.engine.set_uci_option(name, valor)
        self.owner.set_engine(self.engine, False)
        self.set_changed()

    def set_changed(self):
        self.is_changed = True

    def save(self):
        if self.is_changed:
            self.is_changed = False
            self.configuration.x_tutor_clave = self.engine.alias
            self.configuration.x_tutor_mstime = self.ed_time.textoFloat() * 1000
            self.configuration.x_tutor_depth = self.ed_depth.textoInt()
            self.configuration.x_tutor_multipv = self.ed_multipv.textoInt()
            self.configuration.x_tutor_priority = self.cb_priority.valor()

            self.configuration.x_tutor_view = self.cb_board_position.valor()
            self.configuration.x_engine_notbackground = not self.chb_background.valor()
            self.configuration.x_default_tutor_active = not self.chb_disabled.valor()
            self.configuration.x_tutor_diftype = self.cb_type.valor()

            self.configuration.graba()

            dic = self.configuration.read_variables("TUTOR_ANALYZER")
            dic["TUTOR"] = self.engine.list_uci_changed()
            self.configuration.write_variables("TUTOR_ANALYZER", dic)
            Code.procesador.change_manager_tutor()

    def activate_this(self):
        self.cb_engine.rehacer(self.configuration.engines.list_name_alias_multipv(), self.engine.alias)
        self.owner.set_engine(self.engine, False)


class WConfAnalyzer(QtWidgets.QWidget):
    def __init__(self, owner):
        QtWidgets.QWidget.__init__(self, owner)

        self.configuration = Code.configuration

        self.owner = owner
        self.engine = self.configuration.engines.engine_analyzer()
        self.is_changed = False

        lb_engine = Controles.LB2P(self, _("Engine"))
        self.cb_engine = Controles.CB(self, self.configuration.engines.list_name_alias_multipv(), self.engine.alias)
        self.cb_engine.capture_changes(self.changed_engine)

        lb_time = Controles.LB2P(self, _("Duration of analysis (secs)"))
        self.ed_time = Controles.ED(self).tipoFloat(self.configuration.x_analyzer_mstime / 1000.0).relative_width(40)

        lb_depth = Controles.LB2P(self, _("Depth"))
        self.ed_depth = Controles.ED(self).tipoInt(self.configuration.x_analyzer_depth).relative_width(30)

        lb_multipv = Controles.LB2P(self, _("Number of variations evaluated by the engine (MultiPV)"))
        self.ed_multipv = Controles.ED(self).tipoIntPositive(self.configuration.x_analyzer_multipv).relative_width(30)
        lb_maximum = Controles.LB(self, _("0 = Maximum"))
        ly_multi = Colocacion.H().control(self.ed_multipv).control(lb_maximum).relleno()

        lb_priority = Controles.LB2P(self, _("Process priority"))
        self.cb_priority = Controles.CB(self, Priorities.priorities.combo(), self.configuration.x_analyzer_priority)

        bt_analysis_parameters = Controles.PB(
            self,
            _("Analysis configuration parameters"),
            rutina=self.config_analysis_parameters,
            plano=False,
        ).ponIcono(Iconos.ConfAnalysis())

        lb_analysis_bar = Controles.LB2P(self, _("Limits in the Analysis Bar (0=no limit)")).set_font_type(
            puntos=12, peso=700
        )
        lb_depth_ab = Controles.LB2P(self, _("Depth"))
        self.ed_depth_ab = Controles.ED(self).tipoInt(self.configuration.x_analyzer_depth_ab).relative_width(30)
        lb_time_ab = Controles.LB2P(self, _("Time in seconds"))
        self.ed_time_ab = (
            Controles.ED(self).tipoFloat(self.configuration.x_analyzer_mstime_ab / 1000.0).relative_width(40)
        )

        layout = Colocacion.G()
        layout.controld(lb_engine, 0, 0).control(self.cb_engine, 0, 1)
        layout.controld(lb_time, 1, 0).control(self.ed_time, 1, 1)
        layout.controld(lb_depth, 2, 0).control(self.ed_depth, 2, 1)
        layout.controld(lb_multipv, 3, 0).otro(ly_multi, 3, 1)
        layout.controld(lb_priority, 4, 0).control(self.cb_priority, 4, 1)
        layout.filaVacia(5, 20)
        layout.controld(lb_analysis_bar, 6, 0)
        layout.controld(lb_time_ab, 7, 0).control(self.ed_time_ab, 7, 1)
        layout.controld(lb_depth_ab, 8, 0).control(self.ed_depth_ab, 8, 1)

        ly = Colocacion.V().otro(layout).espacio(30).control(bt_analysis_parameters).relleno(1)
        lyh = Colocacion.H().otro(ly).relleno(1).margen(30)

        self.setLayout(lyh)

        for control in (
                self.cb_priority,
                self.ed_multipv,
                self.ed_depth,
                self.ed_time,
                self.ed_depth_ab,
                self.ed_time_ab,
        ):
            control.capture_changes(self.set_changed)

    def config_analysis_parameters(self):
        w = WindowAnalysisConfig.WConfAnalysis(self, self)
        w.exec()

    def refresh_analysis(self):  # llamado por WConfAnalysis
        pass

    def changed_engine(self):
        key = self.cb_engine.valor()
        if key is None:
            key = self.configuration.x_analyzer_clave
        self.engine = self.configuration.engines.dic_engines()[key].clone()
        self.engine.reset_uci_options()
        dic = self.configuration.read_variables("TUTOR_ANALYZER")
        for name, valor in dic.get("ANALYZER", []):
            self.engine.set_uci_option(name, valor)
        self.owner.set_engine(self.engine, False)
        self.set_changed()

    def set_changed(self):
        self.is_changed = True

    def save(self):
        if self.is_changed:
            self.is_changed = False

            self.configuration.x_analyzer_clave = self.engine.alias
            self.configuration.x_analyzer_mstime = self.ed_time.textoFloat() * 1000
            self.configuration.x_analyzer_depth = self.ed_depth.textoInt()
            self.configuration.x_analyzer_multipv = self.ed_multipv.textoInt()
            self.configuration.x_analyzer_priority = self.cb_priority.valor()
            self.configuration.x_analyzer_mstime_ab = self.ed_time_ab.textoFloat() * 1000
            self.configuration.x_analyzer_depth_ab = self.ed_depth_ab.textoInt()

            dic = self.configuration.read_variables("TUTOR_ANALYZER")
            dic["ANALYZER"] = self.engine.list_uci_changed()
            self.configuration.write_variables("TUTOR_ANALYZER", dic)
            Code.procesador.change_manager_analyzer()

    def activate_this(self):
        self.cb_engine.rehacer(self.configuration.engines.list_name_alias_multipv(), self.engine.alias)
        self.owner.set_engine(self.engine, False)


class WOthers(QtWidgets.QWidget):
    def __init__(self, owner):
        QtWidgets.QWidget.__init__(self, owner)

        self.configuration = Code.configuration

        self.owner = owner
        self.is_changed = False

        lb_refresh_engines = Controles.LB2P(self, _("Engine Refresh Rate"))
        self.sld_refresh_engines = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self.sld_refresh_engines.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.sld_refresh_engines.setMinimum(0)
        self.sld_refresh_engines.setMaximum(5)
        self.sld_refresh_engines.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        self.sld_refresh_engines.setTickInterval(1)
        self.sld_refresh_engines.setSingleStep(1)
        self.sld_refresh_engines.setPageStep(1)
        self.sld_refresh_engines.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )

        refresh_label = [_("No limit"), _("Very fast"), _("Fast"), _("Normal"), _("Slow"), _("Very slow")]
        refresh_table = [0, 20, 50, 100, 200, 500]

        value = Code.configuration.x_msrefresh_poll_engines
        result = 0
        for pos, ref in enumerate(refresh_table):
            if ref >= value:
                result = pos
                break
        self.sld_refresh_engines.setValue(result)

        self.lb_refresh_value = Controles.LB(self).anchoMinimo(100)

        def on_slider_moved(index):
            ms_actual = refresh_table[index]
            tooltip = refresh_label[index]

            self.sld_refresh_engines.setToolTip(tooltip)
            self.lb_refresh_value.set_text(tooltip)

            self.configuration.x_msrefresh_poll_engines = ms_actual
            Code.configuration.graba()

        self.sld_refresh_engines.valueChanged.connect(on_slider_moved)
        on_slider_moved(self.sld_refresh_engines.value())

        ly_refresh = Colocacion.H().control(self.sld_refresh_engines, stretch=1).control(self.lb_refresh_value)

        lb_maia = Controles.LB2P(self, _("Nodes used with Maia engines"))
        li_options = [
            (_("1 node as advised by the authors"), False),
            (
                _("From 1 (1100) to 450 nodes (1900), similar strength as other engines")
                .replace("1900", "2200")
                .replace("450", "800"),
                True,
            ),
        ]
        self.cb_maia = Controles.CB(self, li_options, Code.configuration.x_maia_nodes_exponential).capture_changes(
            self.save
        )
        self.cb_maia.set_multiline(400)

        lb_gaviota = Controles.LB2P(self, _("Gaviota Tablebases"))
        self.gaviota = Code.configuration.folder_gaviota()
        self.bt_gaviota = Controles.PB(self, self.gaviota, self.change_gaviota, plano=False)
        self.bt_gaviota_remove = Controles.PB(self, "", self.remove_gaviota).ponIcono(Iconos.Delete())
        ly_gav = Colocacion.H().control(self.bt_gaviota).control(self.bt_gaviota_remove).relleno()

        lb_stockfish = Controles.LB2P(self, "Stockfish")
        self.lb_stockfish_version = Controles.LB(self, CheckEngines.current_stockfish()).set_font_type(
            peso=500, puntos=11
        )
        self.lb_stockfish_version.setStyleSheet("border:1px solid gray;padding:3px")
        bt_stockfish = (
            Controles.PB(self, "", self.change_stockfish).ponIcono(Iconos.Reiniciar()).ponToolTip(_("Update"))
        )
        ly_stk = Colocacion.H().control(self.lb_stockfish_version).control(bt_stockfish).relleno()

        sep = 40
        layout = Colocacion.G()
        layout.rellenoColumna(1, 1)
        layout.controld(lb_refresh_engines, 0, 0)
        layout.otro(ly_refresh, 0, 1)
        layout.filaVacia(1, sep)
        layout.controld(lb_maia, 2, 0)
        layout.control(self.cb_maia, 2, 1)
        layout.filaVacia(3, sep)
        layout.controld(lb_gaviota, 4, 0)
        layout.otro(ly_gav, 4, 1)
        layout.filaVacia(5, sep)
        layout.controld(lb_stockfish, 6, 0)
        layout.otro(ly_stk, 6, 1)

        layoutg = Colocacion.V().espacio(sep).otro(layout).relleno().margen(30)

        self.setLayout(layoutg)

        self.set_gaviota()

    def set_gaviota(self):
        self.bt_gaviota.set_text("   %s   " % Code.relative_root(self.gaviota))

    def change_gaviota(self):
        folder = SelectFiles.get_existing_directory(self, self.gaviota, _("Gaviota Tablebases"))
        if folder:
            self.gaviota = folder
            self.set_gaviota()
            self.save()

    def remove_gaviota(self):
        self.gaviota = Code.configuration.carpeta_gaviota_defecto()
        self.set_gaviota()
        self.save()

    def change_stockfish(self):
        self.lb_stockfish_version.set_text(" ? ")
        CheckEngines.check_stockfish(self.owner, True)
        self.lb_stockfish_version.set_text(CheckEngines.current_stockfish())

    def save(self):
        self.configuration.x_carpeta_gaviota = self.gaviota

        previo = self.configuration.x_maia_nodes_exponential
        actual = self.cb_maia.valor()
        if previo != actual:
            self.configuration.x_maia_nodes_exponential = actual
            self.configuration.engines.reset()

        Code.configuration.graba()
