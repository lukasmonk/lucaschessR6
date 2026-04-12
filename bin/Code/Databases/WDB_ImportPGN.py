import re
import time

from PySide6 import QtWidgets

import Code
from Code.Databases import WDB_Filters, WDB_RemComVariations
from Code.QT import Colocacion, Controles, Iconos, LCDialog, QTDialogs, QTMessages, QTUtils, SelectFiles, ScreenUtils
from Code.Z import Util


class WImportPGN(LCDialog.LCDialog):
    def __init__(self, owner):
        LCDialog.LCDialog.__init__(self, owner, _("Import PGN"), Iconos.Import8(), "import_pgn")

        self.rem = WDB_RemComVariations.RemoveCommentsVariations("databases_import_remove")
        self.files = []
        self.filter_func = None

        # ==== LAYOUT PRINCIPAL ====
        ly = Colocacion.V()

        # Toolbar
        tb = QTDialogs.LCTB(self)
        tb.new(_("Accept"), Iconos.Aceptar(), self.aceptar)
        tb.new(_("Cancel"), Iconos.Cancelar(), self.reject)
        ly.control(tb)
        ly.espacio(15)

        # ==== SECCIÓN 1: ORIGEN ====
        gb_source = self._create_source_section()
        ly.control(gb_source)
        ly.espacio(15)

        # ==== SECCIÓN 2: FILTRO ====
        gb_filter = self._create_filter_section()
        ly.control(gb_filter)
        ly.espacio(15)

        # ==== SECCIÓN 3: REMOVER ELEMENTOS ====
        gb_remove = self._create_remove_section()
        ly.control(gb_remove)

        ly.espacio(10)
        ly.relleno()

        self.setLayout(ly)

        self.setMinimumWidth(480)
        self.changes_done()
        self._on_remove_toggled(False)

    def _create_source_section(self):
        """Crea la sección de selección de origen."""
        gb = QtWidgets.QGroupBox("1. " + _("Source"))
        Code.configuration.set_property(gb, "title")

        ly = Colocacion.V().margen(10)

        self.rb_file = Controles.RB(self, f"{_('Select file(s)')}  (.pgn)", init_value=True)
        self.rb_file.setIcon(Iconos.Fichero())

        self.rb_paste = Controles.RB(self, _("Paste from clipboard"), init_value=False)
        self.rb_paste.setIcon(Iconos.Pegar())

        ly.control(self.rb_file)
        ly.control(self.rb_paste)

        gb.setLayout(ly)
        return gb

    def _create_filter_section(self):
        """Crea la sección de pre-filtro."""
        gb = QtWidgets.QGroupBox("2. " + _("Filter"))
        Code.configuration.set_property(gb, "title")

        ly = Colocacion.V().margen(10)

        self.chb_filter = Controles.CHB(self, _("Use pre-filter"), False)
        self.chb_filter.setIcon(Iconos.Filtrar())

        lb_info = Controles.LB(self, _("Scan games and filter by: Event, White, Black, Result, Elo, Year, etc."))
        font = Controles.FontTypeNew(point_size_delta=-2)
        lb_info.setFont(font)

        lb_info.setStyleSheet("color: gray;")

        ly.control(self.chb_filter)
        ly.control(lb_info)

        gb.setLayout(ly)
        return gb

    def _create_remove_section(self):
        """Crea la sección de eliminación de elementos."""
        self.chb_all = Controles.CHB(self, _("All elements"), False)
        self.chb_all.capture_changes(self.on_all_changed)

        self.chb_variations = Controles.CHB(self, _("Variations"), self.rem.rem_variations)
        self.chb_nags = Controles.CHB(self, f"{_('Ratings')} (NAGs)", self.rem.rem_nags)
        self.chb_analysis = Controles.CHB(self, _("Analysis"), self.rem.rem_analysis)
        self.chb_themes = Controles.CHB(self, _("Themes"), self.rem.rem_themes)
        self.chb_comments = Controles.CHB(self, _("Comments"), self.rem.rem_comments)
        self.chb_comments.capture_changes(self.changes_done)
        self.chb_brackets = Controles.CHB(self, _("Brackets in comments"), self.rem.rem_brackets)
        self.chb_brackets.capture_changes(self.changes_done)
        self.chb_clk = Controles.CHB(self, "[%clk ...]", self.rem.rem_clk)
        self.chb_emt = Controles.CHB(self, "[%emt ...]", self.rem.rem_emt)
        self.chb_eval = Controles.CHB(self, "[%eval ...]", self.rem.rem_eval)
        self.chb_csl = Controles.CHB(self, "[%csl ...]", self.rem.rem_csl)
        self.chb_cal = Controles.CHB(self, "[%cal ...]", self.rem.rem_cal)
        self.chb_other = Controles.CHB(self, "[%<?> ...] → ", self.rem.rem_other)
        self.ed_other = Controles.ED(self, self.rem.val_other)
        self.ed_other.setMinimumWidth(80)

        # Widgets que se ocultan cuando chb_all está activo
        self.li_chbs = (
            self.chb_variations,
            self.chb_analysis,
            self.chb_themes,
            self.chb_nags,
            self.chb_comments,
            self.chb_brackets,
            self.chb_clk,
            self.chb_emt,
            self.chb_eval,
            self.chb_csl,
            self.chb_cal,
            self.chb_other,
        )

        # Widgets que se ocultan cuando chb_comments está desactivado
        self.li_comment_detail = (
            self.chb_brackets,
            self.chb_clk,
            self.chb_emt,
            self.chb_eval,
            self.chb_csl,
            self.chb_cal,
            self.chb_other,
        )

        # Crear GroupBox collapsible
        self.gb_remove = gb = QtWidgets.QGroupBox("3. " + _("Remove elements"))
        gb.setCheckable(True)
        gb.setChecked(False)
        # Code.configuration.set_property(gb, "1")
        gb.toggled.connect(self._on_remove_toggled)

        ly = Colocacion.V().margen(10)

        # Opción "Todos"
        ly.control(self.chb_all)
        ly.espacio(5)

        # Grid con opciones individuales
        grid = Colocacion.G()
        opciones = [
            (self.chb_variations, Iconos.Variations()),
            (self.chb_nags, Iconos.NAGs()),
            (self.chb_analysis, Iconos.Analisis()),
            (self.chb_themes, Iconos.Temas()),
            (self.chb_comments, Iconos.Comment()),
        ]
        for i, (chb, ico) in enumerate(opciones):
            row = i
            col = 0
            chb.setIcon(ico)
            grid.control(chb, row, col)

        # Segunda columna
        opciones2 = [
            (self.chb_brackets, None),
            (self.chb_clk, None),
            (self.chb_emt, None),
            (self.chb_eval, None),
            (self.chb_csl, None),
        ]
        for i, (chb, ico) in enumerate(opciones2):
            row = i
            col = 1
            grid.control(chb, row, col)

        ly.otro(grid)
        ly.espacio(5)

        # Última fila: CAL y Other
        ly_last = Colocacion.H().control(self.chb_cal).control(self.chb_other).control(self.ed_other)
        ly.otro(ly_last)

        gb.setLayout(ly)
        return gb

    def _on_remove_toggled(self, checked):
        """Maneja el toggle del groupbox de removal."""
        for chb in self.li_chbs:
            chb.setVisible(checked)
        self.ed_other.setVisible(checked)
        ScreenUtils.shrink(self)

    def on_all_changed(self):
        val = self.chb_all.valor()
        for chb in self.li_chbs:
            chb.set_value(val)
        show_individual = not val
        for chb in self.li_chbs:
            chb.setVisible(show_individual and self.gb_remove.isChecked())
        self.ed_other.setVisible(show_individual and self.gb_remove.isChecked())
        self.changes_done()
        ScreenUtils.shrink(self)

    def changes_done(self):
        all_active = self.chb_all.valor()
        if all_active:
            return

        comments_active = self.chb_comments.valor()

        for widget in self.li_comment_detail:
            widget.setVisible(comments_active)
        self.ed_other.setVisible(comments_active and self.gb_remove.isChecked())

        if not comments_active:
            for chb in self.li_comment_detail:
                chb.set_value(False)
            return

        disable_subcomments = self.chb_comments.valor() or self.chb_brackets.valor()
        for chb in (self.chb_clk, self.chb_emt, self.chb_eval, self.chb_csl, self.chb_cal, self.chb_other):
            if disable_subcomments:
                chb.set_value(False)
                chb.setEnabled(False)
            else:
                chb.setEnabled(True)
        self.ed_other.setEnabled(not disable_subcomments)

        if self.chb_comments.valor():
            self.chb_brackets.set_value(False)
            self.chb_brackets.setEnabled(False)
        else:
            self.chb_brackets.setEnabled(True)

    def aceptar(self):
        # 1. Source selection
        if self.rb_file.isChecked():
            files = SelectFiles.select_pgns(self)
            if not files:
                return
            self.files = files
        else:
            texto = QTUtils.get_txt_clipboard()
            if not texto:
                QTMessages.message_error(
                    self,
                    _("The text from the clipboard does not contain a chess game in PGN format"),
                )
                return
            path_temp = Code.configuration.temporary_file("pgn")
            try:
                with open(path_temp, "wt", encoding="utf-8") as q:
                    q.write(texto)
                self.files = [path_temp]
            except Exception:
                return

        # 2. Filtering
        self.filter_func = None
        if self.chb_filter.valor():
            st_tags = {}

            max_time = 5.0
            min_time = 1.0
            ini_time = time.time()

            dic_tags_complete = {}
            with QTMessages.one_moment_please(self, _("Working...")):
                for file in self.files:
                    elapsed = time.time() - ini_time
                    max_time -= elapsed
                    file_time = max(max_time, min_time)
                    st, dic_tags = self.scan_pgn_tags(file, file_time)
                    dic_tags_complete.update(dic_tags)
                    for tag, vals in st.items():
                        st_tags.setdefault(tag, set()).update(vals)

            if st_tags:
                w_filter = WDB_Filters.WFiltrarPGN(
                    self,
                    st_tags,
                    dic_tags_complete
                )
                if w_filter.exec():
                    self.filter_func = WDB_Filters.make_filter_func(w_filter.li_filter)
                else:
                    return

        # 3. Element removal options
        if self.gb_remove.isChecked():
            self.rem.remove_all(self.chb_all.valor())
            self.rem.remove_variations(self.chb_variations.valor())
            self.rem.remove_nags(self.chb_nags.valor())
            self.rem.remove_comments(self.chb_comments.valor())
            self.rem.remove_brackets(self.chb_brackets.valor())
            self.rem.remove_clk(self.chb_clk.valor())
            self.rem.remove_emt(self.chb_emt.valor())
            self.rem.remove_eval(self.chb_eval.valor())
            self.rem.remove_csl(self.chb_csl.valor())
            self.rem.remove_cal(self.chb_cal.valor())
            self.rem.remove_analysis(self.chb_analysis.valor())
            self.rem.remove_themes(self.chb_themes.valor())
            self.rem.remove_other(self.chb_other.valor(), self.ed_other.texto().strip())
            self.rem.save()

        self.accept()

    def get_rem_run(self):
        return self.rem.run if self.rem.ok else None

    @staticmethod
    def scan_pgn_tags(file, max_time):
        """Escanea un ficheor PGN y devuelve los valores únicos por etiqueta.

        Args:
            file: ruta al fichero PGN.
            max_time: tiempo que queda.

        Returns:
            st_tags: dict {tag_name: sorted list of unique values}
            dic_tags: dict {tag_upper: tag}
        """
        re_tag = re.compile(r'^\[(\w+)\s+"(.*)"]')
        dic_st_tags = {}
        dic_tags = {}
        tags_saturated = set()

        start_time = time.time()
        # Frecuencia de control de tiempo (cada 500 líneas) para no saturar con time.time()
        check_interval = 500

        try:
            with Util.OpenCodec(file, "rt") as fh:
                for i, line in enumerate(fh):
                    # Solo comprobamos el tiempo cada X líneas para ahorrar ciclos de CPU
                    if i % check_interval == 0 and (time.time() - start_time) > max_time:
                        break

                    if not line.startswith("["):
                        continue

                    m = re_tag.match(line)
                    if not m:
                        continue

                    tag_name, val = m.groups()
                    val = val.strip()

                    if not val or val == "?":
                        continue

                    upper_tag = tag_name.upper()

                    if upper_tag not in tags_saturated:
                        if upper_tag not in dic_st_tags:
                            dic_st_tags[upper_tag] = set()
                            dic_tags[upper_tag] = tag_name

                        st = dic_st_tags[upper_tag]
                        st.add(val)

                        if len(st) > 100:
                            tags_saturated.add(upper_tag)

        except Exception:
            return {}, {}

        # Procesamiento final de resultados
        result = {}
        for upper_tag, vals in dic_st_tags.items():
            # Intentamos ordenar numéricamente, si falla, alfabéticamente
            try:
                result[upper_tag] = sorted(vals, key=int)
            except (ValueError, TypeError):
                result[upper_tag] = sorted(vals, key=str.upper)

        return result, dic_tags
