import operator
import os

from PySide6 import QtCore, QtWidgets

import Code
from Code import Util
from Code.Engines import Engines, WEngines
from Code.QT import (
    Colocacion,
    Columnas,
    Controles,
    Delegados,
    FormLayout,
    Grid,
    Iconos,
    LCDialog,
    QTDialogs,
    QTMessages,
)


class WExternalEngines(LCDialog.LCDialog):
    def __init__(self, owner):
        icono = Iconos.Engine()
        titulo = _("External engines")
        extparam = "external_engines"
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, extparam)

        self.configuration = Code.configuration
        self.engine = None
        self.li_uci_options = []
        self.grid_conf = None

        self.wexternals = WConfExternals(self)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("OPTION", _("UCI option"), 180)
        o_columns.nueva("VALUE", _("Value"), 200, edicion=Delegados.MultiEditor(self))
        o_columns.nueva("DEFAULT", _("By default"), 90)
        self.grid_conf = Grid.Grid(self, o_columns, siSelecFilas=False, is_editable=True)
        self.register_grid(self.grid_conf)

        # Layout
        ly_left = Colocacion.V().control(self.wexternals).margen(0)
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

        self.wexternals.activate_this()

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
            self.wexternals.set_changed()
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

    def grid_setvalue(self, grid, nfila, column, valor):
        opcion = self.li_uci_options[nfila]
        self.engine.set_uci_option(opcion.name, valor)
        self.wexternals.set_changed()

    def save(self):
        self.wexternals.save()
        self.save_video()

    def terminar(self):
        self.save()
        self.accept()

    def closeEvent(self, event):
        self.save()

    def grid_num_datos(self, grid):
        return len(self.li_uci_options) if self.engine else 0

    def grid_dato(self, grid, row, o_column):
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

    def grid_bold(self, grid, row, o_column):
        op = self.li_uci_options[row]
        return str(op.default).strip().lower() != str(op.valor).strip().lower()


class WConfExternals(QtWidgets.QWidget):
    def __init__(self, owner):
        QtWidgets.QWidget.__init__(self, owner)

        self.owner = owner

        Code.configuration.engines.reset_external()
        self.lista_motores = Code.configuration.engines.list_name_external()
        self.is_changed = False

        # Toolbar
        tb = QTDialogs.LCTB(self)
        tb.new(_("Close"), Iconos.MainMenu(), owner.terminar)
        tb.new(_("New"), Iconos.TutorialesCrear(), self.nuevo)
        tb.new(_("Modify"), Iconos.Modificar(), self.modificar)
        tb.new(_("Remove"), Iconos.Borrar(), self.borrar)
        tb.new(_("Copy"), Iconos.Copiar(), self.copiar)
        tb.new(_("Internal engines"), Iconos.MasDoc(), self.importar)
        tb.new(_("Up"), Iconos.Arriba(), self.arriba)
        tb.new(_("Down"), Iconos.Abajo(), self.abajo)
        tb.new(_("Command"), Iconos.Terminal(), self.command)

        # Lista
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("ALIAS", _("Alias"), 114)
        o_columns.nueva("ENGINE", _("Engine"), 128)
        o_columns.nueva("AUTOR", _("Author"), 132)
        o_columns.nueva("INFO", _("Information"), 205)
        o_columns.nueva("ELO", _("Elo"), 64, align_center=True)

        self.grid = None

        self.grid = Grid.Grid(self, o_columns, siSelecFilas=True)
        self.owner.register_grid(self.grid)

        layout = Colocacion.V().control(tb).control(self.grid).margen(0)
        self.setLayout(layout)

        self.grid.gotop()
        self.grid.setFocus()

    def activate_this(self):
        row = self.grid.recno()
        if row >= 0:
            self.owner.set_engine(self.lista_motores[row])
        else:
            self.owner.set_engine(None)
        self.grid.setFocus()

    def set_changed(self):
        self.is_changed = True

    def grid_setvalue(self, grid, nfila, column, valor):
        opcion = self.engine.li_uci_options_editable()[nfila]
        self.engine.set_uci_option(opcion.name, valor)
        self.set_changed()

    def save(self):
        if self.is_changed:
            self.is_changed = False
            li = [eng.save() for eng in self.lista_motores]
            Util.save_pickle(Code.configuration.paths.file_external_engines(), li)
            Code.configuration.relee_engines()

    def grid_cambiado_registro(self, grid, row, o_column):
        if grid == self.grid:
            if row >= 0:
                self.owner.set_engine(self.lista_motores[row])

    def grid_num_datos(self, grid):
        return len(self.lista_motores)

    def grid_dato(self, grid, row, o_column):
        key = o_column.key
        me = self.lista_motores[row]
        if key == "AUTOR":
            return me.autor
        elif key == "ALIAS":
            return me.alias
        elif key == "ENGINE":
            return me.name
        elif key == "INFO":
            return me.id_info.replace("\n", ", ")
        elif key == "ELO":
            return str(me.elo) if me.elo else "-"

    def command(self):
        separador = FormLayout.separador
        li_gen = [
            separador,
        ]
        config = FormLayout.Fichero(_("File"), "exe" if Util.is_windows() else "*", False)
        li_gen.append((config, ""))

        for num in range(1, 11):
            li_gen.append(("%s:" % (_("Argument %d") % num), ""))
        li_gen.append(separador)
        resultado = FormLayout.fedit(
            li_gen,
            title=_("Command"),
            parent=self,
            anchoMinimo=600,
            icon=Iconos.Terminal(),
        )
        if resultado:
            nada, resp = resultado
            command = resp[0]
            liArgs = []
            if not command or not os.path.isfile(command):
                return
            for x in range(1, len(resp)):
                arg = resp[x].strip()
                if arg:
                    liArgs.append(arg)

            with QTMessages.one_moment_please(self):
                me = Engines.Engine(path_exe=command, args=liArgs)
                me.read_uci_options()

            if not me.li_uci_options_editable() and not me.id_name:
                QTMessages.message_bold(
                    self,
                    _X(
                        _("The file %1 does not correspond to a UCI engine type."),
                        command,
                    ),
                )
                return None

            # Editamos
            w = WEngineFast(self, self.lista_motores, me)
            if w.exec():
                self.lista_motores.append(me)
                self.grid.refresh()
                self.grid.gobottom(0)
                self.set_changed()

    def nuevo(self):
        me = WEngines.select_engine(self)
        if not me:
            return

        w = WEngineFast(self, self.lista_motores, me)
        if w.exec():
            self.lista_motores.append(me)

            self.grid.refresh()
            self.grid.gobottom(0)
            self.set_changed()

    def grid_doubleclick_header(self, grid, o_column):
        key = o_column.key
        if key == "ALIAS":
            key = "key"
        elif key == "ENGINE":
            key = "name"
        elif key == "ELO":
            key = "elo"
        else:
            return
        self.lista_motores.sort(key=operator.attrgetter(key))
        self.grid.refresh()
        self.grid.gotop()
        self.set_changed()

    def modificar(self):
        if len(self.lista_motores):
            row = self.grid.recno()
            if row >= 0:
                me = self.lista_motores[row]
                # Editamos, y graba si hace falta
                w = WEngineFast(self, self.lista_motores, me)
                if w.exec():
                    self.grid.refresh()
                    self.set_changed()

    def grid_doble_click(self, grid, row, o_column):
        self.modificar()

    def arriba(self):
        row = self.grid.recno()
        if row > 0:
            li = self.lista_motores
            a, b = li[row], li[row - 1]
            li[row], li[row - 1] = b, a
            self.grid.goto(row - 1, 0)
            self.grid.refresh()
            self.set_changed()

    def abajo(self):
        row = self.grid.recno()
        li = self.lista_motores
        if row < len(li) - 1:
            a, b = li[row], li[row + 1]
            li[row], li[row + 1] = b, a
            self.grid.goto(row + 1, 0)
            self.grid.refresh()
            self.set_changed()

    def borrar(self):
        row = self.grid.recno()
        if row >= 0:
            if QTMessages.pregunta(self, _X(_("Delete %1?"), self.lista_motores[row].key)):
                self.lista_motores[row].remove_uci_options()
                del self.lista_motores[row]
                if row < len(self.lista_motores):
                    self.grid_cambiado_registro(self.grid, row, None)
                else:
                    self.grid.refresh()
                    self.grid.gobottom()
                self.set_changed()
            self.grid.setFocus()

    def copiar(self):
        row = self.grid.recno()
        if row >= 0:
            me = self.lista_motores[row].clone()
            w = WEngineFast(self, self.lista_motores, me)
            if w.exec():
                self.lista_motores.append(me)
                self.grid.refresh()
                self.grid.gobottom(0)
                self.set_changed()

    def importar(self):
        menu = QTDialogs.LCMenu(self)
        lista = Code.configuration.engines.list_name_alias()
        nico = QTDialogs.rondo_puntos()
        for name, key in lista:
            menu.opcion(key, name, nico.otro())

        resp = menu.lanza()
        if not resp:
            return

        me = Code.configuration.engines.search(resp).clone()
        me.set_extern()
        w = WEngineFast(self, self.lista_motores, me)
        if w.exec():
            me.parent_external = me.key
            self.lista_motores.append(me)
            self.grid.refresh()
            self.grid.gobottom(0)
            self.set_changed()


class WEngineFast(QtWidgets.QDialog):
    def __init__(self, w_parent, list_engines, engine, is_tournament=False):

        super(WEngineFast, self).__init__(w_parent)

        self.setWindowTitle(engine.version)
        self.setWindowIcon(Iconos.Engine())
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowMinimizeButtonHint
            | QtCore.Qt.WindowType.WindowMaximizeButtonHint
        )

        self.external_engine = engine
        self.list_engines = list_engines
        self.is_tournament = is_tournament
        self.imported = engine.parent_external is not None

        # Toolbar
        tb = QTDialogs.tb_accept_cancel(self)

        lb_alias = Controles.LB2P(self, _("Alias"))
        self.edAlias = Controles.ED(self, engine.alias).anchoMinimo(360)

        if not self.imported:
            lb_nombre = Controles.LB2P(self, _("Name"))
            self.edNombre = Controles.ED(self, engine.name).anchoMinimo(360)

        lb_info = Controles.LB(self, _("Information") + ": ")
        self.emInfo = Controles.EM(self, engine.id_info, siHTML=False).anchoMinimo(360).altoFijo(60)

        lb_elo = Controles.LB(self, "ELO: ")
        self.sbElo = Controles.SB(self, engine.elo, 0, 4000)

        lb_exe = Controles.LB(self, "%s: %s" % (_("File"), Code.relative_root(engine.path_exe)))

        # Layout
        ly = Colocacion.G()
        ly.controld(lb_alias, 0, 0).control(self.edAlias, 0, 1)
        if not self.imported:
            ly.controld(lb_nombre, 1, 0).control(self.edNombre, 1, 1)
        ly.controld(lb_info, 2, 0).control(self.emInfo, 2, 1)
        ly.controld(lb_elo, 3, 0).control(self.sbElo, 3, 1)
        ly.control(lb_exe, 7, 0, 1, 2)

        layout = Colocacion.V().control(tb).otro(ly)

        self.setLayout(layout)

        self.edAlias.setFocus()

    def aceptar(self):
        alias = self.edAlias.texto().strip()
        if not alias:
            QTMessages.message_error(self, _("You have not indicated any alias"))
            return

        # Comprobamos que no se repita el alias
        for engine in self.list_engines:
            if (self.external_engine != engine) and (engine.alias == alias):
                QTMessages.message_error(
                    self,
                    _(
                        "There is already another engine with the same alias, the alias must change in order to have both."
                    ),
                )
                return
        self.external_engine.key = alias
        if not self.imported:
            name = self.edNombre.texto().strip()
            self.external_engine.name = name if name else alias
        self.external_engine.id_info = self.emInfo.texto()
        self.external_engine.elo = self.sbElo.valor()

        self.accept()
