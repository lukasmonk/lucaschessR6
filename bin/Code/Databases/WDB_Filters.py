import fnmatch
import webbrowser

from PySide6 import QtCore, QtWidgets

import Code
from Code.QT import Colocacion, Controles, Iconos, LCDialog, QTDialogs, QTMessages
from Code.SQL import UtilSQL


class WFiltrar(QtWidgets.QDialog):
    def __init__(self, w_parent, li_filter, db_save_nom=None):
        super(WFiltrar, self).__init__(w_parent)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        if db_save_nom is None:
            db_save_nom = Code.configuration.paths.file_filters_pgn()

        self.setWindowTitle(_("Filter"))
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
        )
        self.setWindowIcon(Iconos.Filtrar())

        self.li_filter = li_filter
        n_filtro = len(li_filter)
        self.db_save_nom = db_save_nom

        li_cols = w_parent.grid.list_columns(True)
        st = {col.key for col in li_cols}
        st.add("__num__")
        st.add("opening")
        li_fields: list = [
            ("", None),
        ]
        li_fields.extend([(x.head.strip("+-"), f'"{x.key}"') for x in li_cols if x.key not in ("__num__", "opening")])

        li_cols.append(None)
        ok_sep = True
        li = []
        for col in w_parent.grid.o_columns.li_columns:
            if col.key not in st:
                if ok_sep:
                    li.append(("", ""))
                    ok_sep = False
                li.append((col.head.strip("+-"), f'"{col.key}"'))
        if not ok_sep:
            li.sort()
            li_fields.extend(li)

        li_condicion = [
            ("", None),
            (_("Equal"), "="),
            (_("Not equal"), "<>"),
            (_("Greater than"), ">"),
            (_("Less than"), "<"),
            (_("Greater than or equal"), ">="),
            (_("Less than or equal"), "<="),
            (_("Like (wildcard = *)"), "LIKE"),
            (_("Not like (wildcard = *)"), "NOT LIKE"),
            (_("Is empty"), "EMPTY"),
            (_("Is not empty"), "NOT EMPTY"),
        ]

        li_union = [("", None), (_("AND"), "AND"), (_("OR"), "OR")]

        f = Controles.FontType(puntos=12)  # 0, peso=75 )

        lb_col = Controles.LB(self, _("Column")).set_font(f)
        lb_par0 = Controles.LB(self, "(").set_font(f)
        lb_par1 = Controles.LB(self, ")").set_font(f)
        lb_con = Controles.LB(self, _("Condition")).set_font(f)
        lb_val = Controles.LB(self, _("Value")).set_font(f)
        lb_uni = Controles.LB(self, "+").set_font(f)

        ly = Colocacion.G()
        ly.controlc(lb_uni, 0, 0).controlc(lb_par0, 0, 1).controlc(lb_col, 0, 2)
        ly.controlc(lb_con, 0, 3).controlc(lb_val, 0, 4).controlc(lb_par1, 0, 5)

        self.numC = 8
        li_c = []

        union, par0, campo, condicion, valor, par1 = None, False, None, None, "", False
        for i in range(self.numC):
            if i > 0:
                c_union = Controles.CB(self, li_union, union)
                ly.controlc(c_union, i + 1, 0)
            else:
                c_union = None

            c_par0 = Controles.CHB(self, "", par0).relative_width(20)
            ly.controlc(c_par0, i + 1, 1)
            c_campo = Controles.CB(self, li_fields, campo)
            ly.controlc(c_campo, i + 1, 2)
            c_condicion = Controles.CB(self, li_condicion, condicion)
            ly.controlc(c_condicion, i + 1, 3)
            c_valor = Controles.ED(self, valor)
            ly.controlc(c_valor, i + 1, 4)
            c_par1 = Controles.CHB(self, "", par1).relative_width(20)
            ly.controlc(c_par1, i + 1, 5)

            li_c.append((c_union, c_par0, c_campo, c_condicion, c_valor, c_par1))

        self.liC = li_c

        # Toolbar
        def ayuda():
            url = "https://lucaschess.blogspot.com/2025/05/game-list-filter-button-practical-uses.html"
            webbrowser.open(url)

        tb = QTDialogs.LCTB(self)
        tb.new(_("Accept"), Iconos.Aceptar(), self.aceptar)
        tb.new(_("Cancel"), Iconos.Cancelar(), self.reject)
        tb.new(_("Reinit"), Iconos.Reiniciar(), self.reiniciar)
        tb.new(_("Save/Restore"), Iconos.Grabar(), self.grabar)
        tb.new(_("Help"), Iconos.AyudaGR(), ayuda)

        # Layout
        layout = Colocacion.V().control(tb).otro(ly).margen(3)
        self.setLayout(layout)

        li_c[0][2].setFocus()

        if n_filtro > 0:
            self.lee_filtro(self.li_filter)

        for widget in (
            lb_col,
            lb_par0,
            lb_par1,
            lb_con,
            lb_val,
            lb_uni,
        ):
            widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

    def grabar(self):
        if not self.lee_filtro_actual():
            return
        with UtilSQL.DictSQL(self.db_save_nom, tabla="Filters") as dbc:
            li_conf = dbc.keys(si_ordenados=True)
            if len(li_conf) == 0 and len(self.li_filter) == 0:
                return
            menu = QTDialogs.LCMenu(self)
            kselecciona, kborra, kgraba = range(3)
            for x in li_conf:
                menu.opcion((kselecciona, x), x, Iconos.PuntoAzul())
            menu.separador()

            if len(self.li_filter) > 0:
                submenu = menu.submenu(_("Save current"), Iconos.Mas())
                if li_conf:
                    for x in li_conf:
                        submenu.opcion((kgraba, x), x, Iconos.PuntoAmarillo())
                submenu.separador()
                submenu.opcion((kgraba, None), _("New"), Iconos.NuevoMas())

            if li_conf:
                menu.separador()
                submenu = menu.submenu(_("Remove"), Iconos.Delete())
                for x in li_conf:
                    submenu.opcion((kborra, x), x, Iconos.PuntoRojo())
            resp = menu.lanza()

            if resp:
                op, name = resp

                if op == kselecciona:
                    li_filter = dbc[name]
                    self.lee_filtro(li_filter)
                elif op == kborra:
                    if QTMessages.pregunta(self, _X(_("Delete %1?"), name)):
                        del dbc[name]
                elif op == kgraba:
                    if self.lee_filtro_actual():
                        if name is None:
                            name = QTMessages.read_simple(self, _("Filter"), _("Name"), "")
                            if name:
                                dbc[name] = self.li_filter
                        else:
                            dbc[name] = self.li_filter

    def lee_filtro(self, li_filter):
        self.li_filter = li_filter
        n_filtro = len(li_filter)

        for i in range(self.numC):
            if n_filtro > i:
                union, par0, campo, condicion, valor, par1 = li_filter[i]
            else:
                union, par0, campo, condicion, valor, par1 = (
                    None,
                    False,
                    None,
                    None,
                    "",
                    False,
                )
            c_union, c_par0, c_campo, c_condicion, c_valor, c_par1 = self.liC[i]
            if c_union:
                c_union.set_value(union)
            c_par0.set_value(par0)
            c_campo.set_value(campo)
            c_condicion.set_value(condicion)
            c_valor.set_text(valor)
            c_par1.set_value(par1)

    def reiniciar(self):
        for i in range(self.numC):
            self.liC[i][1].set_value(False)
            self.liC[i][2].setCurrentIndex(0)
            self.liC[i][3].setCurrentIndex(0)
            self.liC[i][4].set_text("")
            self.liC[i][5].set_value(False)
            if i > 0:
                self.liC[i][0].setCurrentIndex(0)

    def lee_filtro_actual(self):
        self.li_filter = []

        npar = 0

        for i in range(self.numC):
            par0 = self.liC[i][1].valor()
            campo = self.liC[i][2].valor()
            condicion = self.liC[i][3].valor()
            valor = self.liC[i][4].texto()
            par1 = self.liC[i][5].valor()

            if campo and condicion:
                if campo == "PLIES":
                    valor = valor.strip()
                    if valor.isdigit():
                        valor = f"{int(valor)}"  # fonkap patch %3d -> %d
                if par0:
                    npar += 1
                if par1:
                    npar -= 1
                if npar < 0:
                    break
                if i > 0:
                    union = self.liC[i][0].valor()
                    if union:
                        self.li_filter.append([union, par0, campo, condicion, valor, par1])
                else:
                    self.li_filter.append([None, par0, campo, condicion, valor, par1])
            else:
                break
        if npar:
            QTMessages.message_error(self, _("The parentheses are unbalanced."))
            return False
        return True

    def aceptar(self):
        if self.lee_filtro_actual():
            self.accept()

    def where(self):
        where = ""
        for union, par0, campo, condicion, valor, par1 in self.li_filter:
            valor = valor.upper()
            if condicion in ("LIKE", "NOT LIKE"):
                valor = valor.replace("*", "%")
                if not valor:
                    continue
                if "%" not in valor:
                    valor = f"%{valor}%"
                if condicion == "NOT LIKE":
                    par0 = par1 = True  # para que "OR CAMPO is NULL" esté unido al resto con paréntesis

            if union:
                where += f" {union} "
            if par0:
                where += "("
            if condicion in ("=", "<>") and not valor:
                where += (
                    f"(( {campo} {'IS NULL' if condicion == '=' else 'IS NOT NULL'} ) "
                    f"{'OR' if condicion == '=' else 'AND'} ({campo} {condicion} ''))"
                )
            elif condicion == "EMPTY":
                where += f"({campo} IS NULL OR TRIM({campo}) = '')"
            elif condicion == "NOT EMPTY":
                where += f"({campo} IS NOT NULL AND TRIM({campo}) != '')"
            else:
                valor = valor.upper()
                if valor.isupper():
                    # where += "UPPER(%s) %s '%s'" % (campo, condicion, valor)  # fonkap patch
                    where += "%s %s '%s' COLLATE NOCASE" % (
                        campo,
                        condicion,
                        valor,
                    )  # fonkap patch
                elif valor.isdigit():  # fonkap patch
                    where += "CAST(%s as decimal) %s %s" % (
                        campo,
                        condicion,
                        valor,
                    )  # fonkap patch
                else:
                    where += f"{campo} {condicion} '{valor}'"  # fonkap patch
            if condicion == "NOT LIKE":
                where += f" OR {campo} IS NULL"
            if par1:
                where += ")"
        return where


class EMSQL(Controles.EM):
    def __init__(self, owner, where, li_fields):
        self.li_fields = li_fields
        Controles.EM.__init__(self, owner, where, is_html=False)

    def mousePressEvent(self, event):
        Controles.EM.mousePressEvent(self, event)
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            menu = QTDialogs.LCMenu(self)
            rondo = QTDialogs.rondo_puntos()
            for txt, key in self.li_fields:
                menu.opcion(key, txt, rondo.otro())
            resp = menu.lanza()
            if resp:
                self.insert_text(resp)


class WFiltrarRaw(LCDialog.LCDialog):
    def __init__(self, w_parent, o_columns, where):
        LCDialog.LCDialog.__init__(self, w_parent, _("Filter"), Iconos.Filtrar(), "rawfilter")

        self.where = ""
        li_fields = [(x.head, x.key) for x in o_columns.li_columns if x.key != "__num__"]
        f = Controles.FontType(puntos=12)  # 0, peso=75 )

        lb_raw = Controles.LB(self, f"{_('Raw SQL')}:").set_font(f)
        self.edRaw = EMSQL(self, where, li_fields).fixed_height(72).minimum_width(512).set_font(f)

        lb_help = Controles.LB(self, _("Right button to select a column of database")).set_font(f)
        ly_help = Colocacion.H().relleno().control(lb_help).relleno()

        ly = Colocacion.H().control(lb_raw).control(self.edRaw)

        # Toolbar
        li_acciones = [
            (_("Accept"), Iconos.Aceptar(), self.aceptar),
            None,
            (_("Cancel"), Iconos.Cancelar(), self.reject),
            None,
        ]
        tb = QTDialogs.LCTB(self, li_acciones)

        # Layout
        layout = Colocacion.V().control(tb).otro(ly).otro(ly_help).margen(3)
        self.setLayout(layout)

        self.edRaw.setFocus()

        self.restore_video(with_tam=False)

    def aceptar(self):
        self.where = self.edRaw.texto()
        self.save_video()
        self.accept()


def make_filter_func(li_filter):
    """Crea una función filtro a partir de la lista de condiciones de WFiltrarPGN.

    Args:
        li_filter: lista de [union, campo, condicion, valor]
            union: None | "AND" | "OR"
            campo: nombre de la etiqueta PGN (str)
            condicion: "=" | "<>" | ">" | "<" | ">=" | "<=" | "LIKE" | "NOT LIKE" | "EMPTY" | "NOT EMPTY"
            valor: str

    Returns:
        función filter_func(d_cab) -> bool
    """

    def _match_one(d_cab, campo, condicion, valor):
        v = d_cab.get(campo, "") or ""
        if condicion == "EMPTY":
            return v.strip() == ""
        if condicion == "NOT EMPTY":
            return v.strip() != ""
        if condicion in ("LIKE", "NOT LIKE"):
            pattern = valor.replace("*", "*").upper()
            if "%" in pattern:
                pattern = pattern.replace("%", "*")
            matched = fnmatch.fnmatch(v.upper(), f"*{pattern}*" if "*" not in pattern else pattern)
            return matched if condicion == "LIKE" else not matched
        # Comparaciones
        try:
            vi = int(v)
            va = int(valor)
            if condicion == "=":
                return vi == va
            if condicion == "<>":
                return vi != va
            if condicion == ">":
                return vi > va
            if condicion == "<":
                return vi < va
            if condicion == ">=":
                return vi >= va
            if condicion == "<=":
                return vi <= va
        except (ValueError, TypeError):
            pass
        v_up = v.upper()
        valor_up = valor.upper()
        if condicion == "=":
            return v_up == valor_up
        if condicion == "<>":
            return v_up != valor_up
        if condicion == ">":
            return v_up > valor_up
        if condicion == "<":
            return v_up < valor_up
        if condicion == ">=":
            return v_up >= valor_up
        if condicion == "<=":
            return v_up <= valor_up
        return True

    def filter_func(d_cab):
        result = None
        for union, campo, condicion, valor in li_filter:
            if not campo or not condicion:
                continue
            matched = _match_one(d_cab, campo, condicion, valor)
            if result is None:
                result = matched
            elif union == "OR":
                result = result or matched
            else:  # AND (default)
                result = result and matched
        return result if result is not None else True

    return filter_func


class WFiltrarPGN(LCDialog.LCDialog):
    """Diálogo de filtro previo para importación de PGN.

    Permite definir hasta 6 condiciones sobre las etiquetas encontradas en el escaneo.
    """

    NUM_ROWS = 6

    def __init__(self, w_parent, st_tags, dic_tags):
        LCDialog.LCDialog.__init__(self, w_parent, _("Pre-filter for PGN import"), Iconos.Filtrar(), "filtrar_pgn")

        self.li_filter = []

        # --- Listas para los combos ---
        # Campos disponibles: etiquetas encontradas, ordenadas
        li_fields = [("", None), (_("Movements"), "PLYCOUNT")]
        # Etiquetas estándar primero, luego el resto
        standard_first = ["WHITE", "BLACK", "RESULT", "WHITEELO", "BLACKELO", "EVENT", "SITE", "DATE", "ECO"]
        all_tags = sorted(st_tags.keys(), key=lambda t: (0 if t.upper() in standard_first else 1, t.upper()))
        for tag in all_tags:
            li_fields.append((dic_tags[tag], tag))

        li_condicion = [
            ("", None),
            (_("Equal"), "="),
            (_("Not equal"), "<>"),
            (_("Greater than"), ">"),
            (_("Less than"), "<"),
            (_("Greater than or equal"), ">="),
            (_("Less than or equal"), "<="),
            (_("Like (wildcard = *)"), "LIKE"),
            (_("Not like (wildcard = *)"), "NOT LIKE"),
            (_("Is empty"), "EMPTY"),
            (_("Is not empty"), "NOT EMPTY"),
        ]
        li_union = [("", None), (_("AND"), "AND"), (_("OR"), "OR")]

        f = Controles.FontType(puntos=11)
        lb_col = Controles.LB(self, _("Column")).set_font(f)
        lb_con = Controles.LB(self, _("Condition")).set_font(f)
        lb_val = Controles.LB(self, _("Value")).set_font(f)
        lb_uni = Controles.LB(self, "+").set_font(f)

        ly = Colocacion.G()
        ly.controlc(lb_uni, 0, 0).controlc(lb_col, 0, 1).controlc(lb_con, 0, 2).controlc(lb_val, 0, 3)

        self._li_c = []
        for i in range(self.NUM_ROWS):
            if i > 0:
                c_union = Controles.CB(self, li_union, None)
                ly.controlc(c_union, i + 1, 0)
            else:
                c_union = None

            c_campo = Controles.CB(self, li_fields, None)
            ly.controlc(c_campo, i + 1, 1)

            c_condicion = Controles.CB(self, li_condicion, None)
            ly.controlc(c_condicion, i + 1, 2)

            # Valor: combo box editable
            c_valor = Controles.CB(self, [], "", extend_seek=True).set_font(f)
            c_valor.setFixedWidth(Controles.calc_fixed_width(240))
            ly.controlc(c_valor, i + 1, 3)

            # Al cambiar el campo, rellenar el combobox de valor
            c_campo.currentIndexChanged.connect(lambda idx, row=i: self._on_campo_changed(row))

            self._li_c.append((c_union, c_campo, c_condicion, c_valor))

        # Guardamos st_tags para rellenar valores en _on_campo_changed
        self._st_tags = st_tags

        # --- Toolbar ---
        tb = QTDialogs.LCTB(self)
        tb.new(_("Accept"), Iconos.Aceptar(), self.aceptar)
        tb.new(_("Cancel"), Iconos.Cancelar(), self.reject)
        tb.new(_("Reinit"), Iconos.Reiniciar(), self.reiniciar)

        layout = Colocacion.V().control(tb).espacio(6).otro(ly).margen(6)
        self.setLayout(layout)

        self.restore_video(with_tam=False)
        self._li_c[0][1].setFocus()

        for w in (lb_col, lb_con, lb_val, lb_uni):
            w.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

    def _on_campo_changed(self, row):
        """Al cambiar el campo, rellenar el combo de valor con los valores únicos."""
        __, c_campo, __, c_valor = self._li_c[row]
        tag = c_campo.valor()
        if tag and tag in self._st_tags:
            vals = list(self._st_tags[tag])
            li_options = [("", "")] + [(v, v) for v in vals]
            c_valor.rehacer(li_options, "")
            c_valor.setCurrentText("")
            c_valor.setToolTip("\n".join(v for v in vals[:20]) + ("\n..." if len(vals) > 20 else ""))
        else:
            c_valor.rehacer([], "")
            c_valor.setCurrentText("")
            c_valor.setToolTip("")

    def reiniciar(self):
        for i in range(self.NUM_ROWS):
            c_union, c_campo, c_condicion, c_valor = self._li_c[i]
            if c_union:
                c_union.setCurrentIndex(0)
            c_campo.setCurrentIndex(0)
            c_condicion.setCurrentIndex(0)
            c_valor.setCurrentText("")
            c_valor.rehacer([], "")

    def lee_filtro_actual(self):
        self.li_filter = []
        for i in range(self.NUM_ROWS):
            c_union, c_campo, c_condicion, c_valor = self._li_c[i]
            union = c_union.valor() if c_union else None
            campo = c_campo.valor()
            condicion = c_condicion.valor()
            valor = c_valor.currentText().strip()
            if campo and condicion:
                self.li_filter.append([union, campo, condicion, valor])
        return True

    def aceptar(self):
        if self.lee_filtro_actual():
            self.save_video()
            self.accept()
