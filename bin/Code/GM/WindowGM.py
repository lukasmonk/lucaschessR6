import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Any

import Code
from Code.Z import Util
from Code.Books import Books
from Code.GM import GM
from Code.Openings import WindowOpenings
from Code.QT import Colocacion, Columnas, Controles, Grid, Iconos, LCDialog, QTDialogs, QTMessages, ScreenUtils
from Code.SQL import UtilSQL
from Code.Engines import Engines


@dataclass
class GMConfiguration:
    gm: Optional[str] = None
    modo: GM.GameMode = GM.GameMode.STANDARD
    gameElegida: Optional[int] = None
    is_white: bool = True
    with_adjudicator: bool = True
    show_evals: bool = False
    engine: Optional[str] = None
    vtime: int = 10
    mostrar: GM.ShowOption = GM.ShowOption.WHEN_DIFFERENT
    depth: int = 0
    multiPV: str = "PD"
    select_rival_move: bool = False
    jugInicial: int = 1
    bypass_book: Optional[Any] = None
    opening: Optional[Any] = None
    li_preferred_openings: List[Any] = None

    def __post_init__(self):
        if self.li_preferred_openings is None:
            self.li_preferred_openings = []


class WGM(LCDialog.LCDialog):
    record: GMConfiguration
    ogm: GM.GM

    def __init__(self, procesador):
        self.configuration = Code.configuration

        self.procesador = procesador

        self.db_histo = UtilSQL.DictSQL(self.configuration.paths.file_gm_histo())
        self.opening_block = None
        self.li_preferred_openings = []

        w_parent = procesador.main_window
        titulo = _("Play like a Grandmaster")
        icono = Iconos.GranMaestro()

        extparam = "gm"
        LCDialog.LCDialog.__init__(self, w_parent, titulo, icono, extparam)

        flb = Controles.FontType(puntos=Code.configuration.x_font_points)

        # Toolbar
        li_acciones = [
            (_("Accept"), Iconos.Aceptar(), self.aceptar),
            None,
            (_("Cancel"), Iconos.Cancelar(), self.cancelar),
            None,
            (_("One game"), Iconos.Uno(), self.one_game),
            None,
            (_("Import"), Iconos.ImportarGM(), self.importar),
        ]
        tb = QTDialogs.LCTB(self, li_acciones)

        # Grandes maestros
        self.li_gm = GM.lista_gm()
        li = [(x[0], x[1]) for x in self.li_gm]
        li.insert(0, ("-", None))
        self.cb_gm = QTMessages.combobox_lb(self, li, li[0][1] if len(self.li_gm) == 0 else li[1][1])
        self.cb_gm.capture_changes(self.check_gm)
        hbox = Colocacion.H().relleno().control(self.cb_gm).relleno()
        gb_gm = Controles.GB(self, _("Choose a Grandmaster"), hbox).set_font(flb)
        self.configuration.set_property(gb_gm, "1")

        # Personales
        self.li_personal = GM.lista_gm_personal(Code.configuration.paths.folder_personal_trainings())
        if self.li_personal:
            li = [(x[0], x[1]) for x in self.li_personal]
            li.insert(0, ("-", None))
            self.cbPersonal = QTMessages.combobox_lb(self, li, li[0][1])
            self.cbPersonal.capture_changes(self.check_personal)
            self.cbPersonal.setFont(flb)
            bt_borrar = Controles.PB(self, "", self.remove_personal).set_icono(Iconos.Borrar(), icon_size=24)
            hbox = Colocacion.H().relleno().control(self.cbPersonal).control(bt_borrar).relleno()
            gb_personal = Controles.GB(self, _("Personal games"), hbox).set_font(flb)
            self.configuration.set_property(gb_personal, "1")

        # Color
        self.rb_white = Controles.RB(self, _("White"), rutina=self.check_color)
        self.rb_white.setFont(flb)
        self.rb_white.activate(True)
        self.rb_black = Controles.RB(self, _("Black"), rutina=self.check_color)
        self.rb_black.setFont(flb)
        self.rb_black.activate(False)

        # Contrario
        self.ch_select_rival_move = Controles.CHB(
            self,
            _("Choose the opponent's move, when there are multiple possible answers"),
            False,
        )

        # Juez
        li_depths = [("--", 0)]
        for x in range(1, 31):
            li_depths.append((str(x), x))
        self.list_engines = self.configuration.engines.list_name_alias_multipv10()
        self.cbJmotor, self.lbJmotor = QTMessages.combobox_lb(
            self, self.list_engines, self.configuration.tutor_default, _("Engine")
        )
        self.edJtiempo = Controles.ED(self).type_float().set_float(1.0).relative_width(50)
        self.lbJtiempo = Controles.LB2P(self, _("Time in seconds"))
        self.cbJdepth = Controles.CB(self, li_depths, 0).capture_changes(self.change_depth)
        self.lbJdepth = Controles.LB2P(self, _("Depth"))
        self.lbJshow = Controles.LB2P(self, _("Show rating"))
        self.chbEvals = Controles.CHB(self, _("Show all evaluations"), False)
        li_options = [
            (_("Always"), GM.ShowOption.ALWAYS.value),
            (_("When moves are different"), GM.ShowOption.WHEN_DIFFERENT.value),
            (_("Never"), GM.ShowOption.NEVER.value),
        ]
        self.cbJshow = Controles.CB(self, li_options, GM.ShowOption.WHEN_DIFFERENT.value)
        self.lbJmultiPV = Controles.LB2P(self, _("Number of variations evaluated by the engine (MultiPV)"))
        li = Engines.list_depths_to_cb()
        self.cbJmultiPV = Controles.CB(self, li, "PD")

        self.li_adjudicator_controls = (
            self.cbJmotor,
            self.lbJmotor,
            self.edJtiempo,
            self.lbJtiempo,
            self.lbJdepth,
            self.cbJdepth,
            self.lbJshow,
            self.cbJshow,
            self.lbJmultiPV,
            self.cbJmultiPV,
            self.chbEvals,
        )

        for control in self.li_adjudicator_controls:
            control.setFont(flb)
        self.cb_gm.setFont(flb)

        # Inicial
        self.edJugInicial, lbInicial = QTMessages.spinbox_lb(self, 1, 1, 99, etiqueta=_("Initial move"), max_width=40)

        # Libros
        self.list_books = Books.ListBooks()
        li = [(x.name, x) for x in self.list_books.lista]
        li.insert(0, ("--", None))
        self.cbBooks, lbBooks = QTMessages.combobox_lb(self, li, None, _("Bypass moves in the book"))

        # Openings
        self.btOpening = Controles.PB(self, " " * 5 + _("Undetermined") + " " * 5, self.openings_edit).set_flat(False)
        self.btOpeningsFavoritas = (
            Controles.PB(self, "", self.preferred_openings).set_icono(Iconos.Favoritos()).relative_width(24)
        )
        self.btOpeningsQuitar = (
            Controles.PB(self, "", self.openings_remove).set_icono(Iconos.Motor_No()).relative_width(24)
        )
        hbox = Colocacion.H().control(self.btOpeningsQuitar).control(self.btOpening).control(self.btOpeningsFavoritas)
        gb_opening = Controles.GB(self, _("Opening"), hbox)

        # gb_basic
        # # Color
        hbox = Colocacion.H().relleno().control(self.rb_white).espacio(10).control(self.rb_black).relleno()
        gb_color = Controles.GB(self, _("Side you play with"), hbox).set_font(flb)
        self.configuration.set_property(gb_color, "1")

        # Tiempo
        ly1 = (
            Colocacion.H()
            .control(self.lbJmotor)
            .control(self.cbJmotor)
            .relleno()
            .control(self.lbJshow)
            .control(self.cbJshow)
        )
        ly2 = Colocacion.H().control(self.lbJtiempo).control(self.edJtiempo)
        ly2.control(self.lbJdepth).control(self.cbJdepth).relleno().control(self.chbEvals)
        ly3 = Colocacion.H().control(self.lbJmultiPV).control(self.cbJmultiPV).relleno()
        ly = Colocacion.V().otro(ly1).otro(ly2).otro(ly3)
        self.gbJ = Controles.GB(self, _("Adjudicator"), ly).to_connect(self.change_adjudicator)
        self.configuration.set_property(self.gbJ, "1")

        # Opciones
        vlayout = Colocacion.V().control(gb_color)
        vlayout.espacio(5).control(self.gbJ)
        vlayout.margen(20)
        gb_basic = Controles.GB(self, "", vlayout)
        gb_basic.setFlat(True)

        # Opciones avanzadas
        ly_inicial = (
            Colocacion.H()
            .control(lbInicial)
            .control(self.edJugInicial)
            .relleno()
            .control(lbBooks)
            .control(self.cbBooks)
            .relleno()
        )
        vlayout = Colocacion.V().otro(ly_inicial).control(gb_opening)
        vlayout.espacio(5).control(self.ch_select_rival_move).margen(20).relleno()
        gb_advanced = Controles.GB(self, "", vlayout)
        gb_advanced.setFlat(True)

        # Historico
        self.liHisto = []
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("FECHA", _("Date"), 100, align_center=True)
        o_columns.nueva("PACIERTOS", _("Hints"), 90, align_center=True)
        o_columns.nueva("PUNTOS", _("Centipawns accumulated"), 140, align_center=True)
        o_columns.nueva("ENGINE", _("Adjudicator"), 100, align_center=True)
        o_columns.nueva("RESUMEN", _("Game played"), 280)

        self.grid = grid = Grid.Grid(self, o_columns, complete_row_select=True, background=None)
        self.grid.alternate_colors()
        self.register_grid(grid)

        # Tabs
        self.tab = Controles.Tab().set_position_south()
        self.tab.new_tab(gb_basic, _("Basic"))
        self.tab.new_tab(gb_advanced, _("Advanced"))
        self.tab.new_tab(self.grid, _("History"))
        self.tab.setFont(flb)

        # Header
        ly_cab = Colocacion.H().control(gb_gm)
        if self.li_personal:
            ly_cab.control(gb_personal)

        layout = Colocacion.V().control(tb).otro(ly_cab).control(self.tab).margen(6)

        self.setLayout(layout)

        self.restore_dic()
        self.change_adjudicator()
        self.check_gm()
        self.check_personal()
        self.check_histo()
        self.opening_show()
        if not self.li_preferred_openings:
            self.btOpeningsFavoritas.hide()

        self.restore_video(default_width=750)

    def change_depth(self, num):
        vtime = self.edJtiempo.text_to_float()
        if int(vtime) * 10 == 0:
            vtime = 3.0
        self.edJtiempo.set_float(0.0 if num > 0 else vtime)
        self.edJtiempo.setEnabled(num == 0)

    def closeEvent(self, event):
        self.save_video()
        self.db_histo.close()

    def check_gm_personal(self, li_gmp, tgm):
        tsiw = self.rb_white.isChecked()

        for nom, gm, siw, sib in li_gmp:
            if gm == tgm:
                self.rb_white.setEnabled(siw)
                self.rb_black.setEnabled(sib)
                if tsiw:
                    if not siw:
                        self.rb_white.activate(False)
                        self.rb_black.activate(True)
                else:
                    if not sib:
                        self.rb_white.activate(True)
                        self.rb_black.activate(False)
                break
        self.check_histo()

    def check_gm(self):
        tgm = self.cb_gm.valor()
        if tgm:
            if self.li_personal:
                self.cbPersonal.set_value(None)
            self.check_gm_personal(self.li_gm, tgm)

    def check_personal(self):
        if not self.li_personal:
            return
        tgm = self.cbPersonal.valor()
        if tgm:
            if self.li_gm:
                self.cb_gm.set_value(None)
            self.check_gm_personal(self.li_personal, tgm)

    def check_histo(self):
        tgm_gm = self.cb_gm.valor()
        tgm_p = self.cbPersonal.valor() if self.li_personal else None

        if tgm_gm is None and tgm_p is None:
            if len(self.li_gm) > 1:
                tgm_gm = self.li_gm[1][1]
                self.cb_gm.set_value(tgm_gm)
            else:
                self.liHisto = []
                return

        if tgm_gm and tgm_p:
            self.cbPersonal.set_value(None)
            tgm_p = None

        if tgm_gm:
            tgm = tgm_gm
        else:
            tgm = f"P_{tgm_p}"

        self.liHisto = self.db_histo[tgm]
        if self.liHisto is None:
            self.liHisto = []
        self.grid.refresh()

    def grid_num_datos(self, _grid):
        return len(self.liHisto)

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        dic: dict = self.liHisto[row]
        if key == "FECHA":
            f = dic["FECHA"]
            return f"{f.day}/{f.month:02d}/{f.year}"
        elif key == "PACIERTOS":
            return f"{dic["PACIERTOS"]}%"
        elif key == "PUNTOS":
            return str(dic["PUNTOS"])
        elif key == "ENGINE":
            s = f"{dic['TIEMPO'] / 10.0:.02f}"
            s = s.rstrip("0").rstrip(".")
            return f"{dic['JUEZ']} {s}\""
        elif key == "RESUMEN":
            return dic.get("RESUMEN", "")
        return None

    def remove_personal(self):
        tgm = self.cbPersonal.valor()
        if tgm is None:
            return
        if not QTMessages.pregunta(self, _X(_("Delete %1?"), tgm)):
            return

        base = Path(self.configuration.paths.folder_personal_trainings()) / f"{tgm}.xgm"
        base.unlink(missing_ok=True)

        self.li_personal = GM.lista_gm_personal(self.configuration.paths.folder_personal_trainings())

        li = [(x[0], x[1]) for x in self.li_personal]
        li.insert(0, ("-", None))
        self.cbPersonal.rehacer(li, li[0][1])

        self.check_personal()

    def check_color(self):
        tgm = self.cb_gm.valor()
        tsiw = self.rb_white.isChecked()

        for nom, gm, siw, sib in self.li_gm:
            if gm == tgm:
                if tsiw:
                    if not siw:
                        self.rb_white.activate(False)
                        self.rb_black.activate(True)
                else:
                    if not sib:
                        self.rb_white.activate(True)
                        self.rb_black.activate(False)

    def aceptar(self):
        if self.save_dict():
            self.accept()
        else:
            self.reject()

    def one_game(self):
        if not self.save_dict():  # crea self.ogm
            return

        w = SelectGame(self, self.ogm)
        if w.exec():
            if w.gameElegida is not None:
                self.record.gameElegida = w.gameElegida

                self.accept()

    def cancelar(self):
        self.reject()

    def importar(self):
        if importar_gm(self):
            li_c = GM.lista_gm()
            self.cb_gm.clear()
            for tp in li_c:
                self.cb_gm.addItem(tp[0], tp[1])
            self.cb_gm.setCurrentIndex(0)

    def change_adjudicator(self):
        if self.li_personal:
            si = self.gbJ.isChecked()
            for control in self.li_adjudicator_controls:
                control.setVisible(si)

    def save_dict(self) -> bool:
        config = GMConfiguration()
        config.gm = self.cb_gm.valor()
        if config.gm is None:
            config.modo = GM.GameMode.PERSONAL
            config.gm = self.cbPersonal.valor()
            if config.gm is None:
                return False
        else:
            config.modo = GM.GameMode.STANDARD

        config.gameElegida = None
        config.is_white = self.rb_white.isChecked()
        config.with_adjudicator = self.gbJ.isChecked()
        config.show_evals = self.chbEvals.valor()
        config.engine = self.cbJmotor.valor()
        config.vtime = int(self.edJtiempo.text_to_float() * 10)
        config.mostrar = GM.ShowOption(self.cbJshow.valor())
        config.depth = self.cbJdepth.valor()
        config.multiPV = self.cbJmultiPV.valor()
        config.select_rival_move = self.ch_select_rival_move.isChecked()
        config.jugInicial = self.edJugInicial.valor()
        config.bypass_book = self.cbBooks.valor()
        config.opening = self.opening_block
        config.li_preferred_openings = self.li_preferred_openings

        if config.with_adjudicator and config.vtime <= 0 and config.depth == 0:
            config.with_adjudicator = False

        default = GM.get_folder_gm()
        carpeta = (
            default
            if config.modo == GM.GameMode.STANDARD
            else Path(self.configuration.paths.folder_personal_trainings())
        )
        self.ogm = GM.GM(str(carpeta), config.gm)
        self.ogm.filter_side(config.is_white)
        if not len(self.ogm):
            QTMessages.message_error(self, _("There are no games to play with this color"))
            return False

        self.ogm.isErasable = config.modo == GM.GameMode.PERSONAL
        self.record = config

        dic = {
            "GM": config.gm,
            "MODO": config.modo.value,
            "IS_WHITE": config.is_white,
            "WITH_ADJUDICATOR": config.with_adjudicator,
            "SHOW_EVALS": config.show_evals,
            "ENGINE": config.engine,
            "VTIME": config.vtime,
            "MOSTRAR": config.mostrar.value,
            "DEPTH": config.depth,
            "MULTIPV": config.multiPV,
            "JUGCONTRARIO": config.select_rival_move,
            "JUGINICIAL": config.jugInicial,
            "BYPASSBOOK": config.bypass_book,
            "OPENING": config.opening,
            "APERTURASFAVORITAS": config.li_preferred_openings,
        }

        Util.save_pickle(self.configuration.paths.file_gms(), dic)
        return True

    def restore_dic(self):
        dic = Util.restore_pickle(self.configuration.paths.file_gms())
        if not dic:
            return

        config = GMConfiguration()
        config.gm = dic["GM"]
        config.modo = GM.GameMode(dic.get("MODO", GM.GameMode.STANDARD.value))
        config.is_white = dic.get("IS_WHITE", True)
        config.with_adjudicator = dic.get("WITH_ADJUDICATOR", True)
        config.show_evals = dic.get("SHOW_EVALS", False)
        config.engine = dic["ENGINE"]
        config.vtime = dic["VTIME"]
        config.depth = dic.get("DEPTH", 0)
        config.multiPV = dic.get("MULTIPV", "PD")
        config.mostrar = GM.ShowOption(dic["MOSTRAR"])
        config.select_rival_move = dic.get("JUGCONTRARIO", False)
        config.jugInicial = dic.get("JUGINICIAL", 1)
        config.li_preferred_openings = dic.get("APERTURASFAVORITAS", [])
        config.opening = dic.get("OPENING", None)

        self.li_preferred_openings = config.li_preferred_openings
        self.opening_block = config.opening

        if self.opening_block:
            n_esta = -1
            for npos, bl in enumerate(self.li_preferred_openings):
                if bl.a1h8 == self.opening_block.a1h8:
                    n_esta = npos
                    break
            if n_esta != 0:
                if n_esta != -1:
                    del self.li_preferred_openings[n_esta]
                self.li_preferred_openings.insert(0, self.opening_block)
            while len(self.li_preferred_openings) > 10:
                del self.li_preferred_openings[10]
        if len(self.li_preferred_openings):
            self.btOpeningsFavoritas.show()

        bypass_book = dic.get("BYPASSBOOK", None)

        self.rb_white.setChecked(config.is_white)
        self.rb_black.setChecked(not config.is_white)

        self.gbJ.setChecked(config.with_adjudicator)
        self.cbJmotor.set_value(config.engine)
        self.edJtiempo.set_float(float(config.vtime / 10.0))
        self.cbJshow.set_value(config.mostrar.value)
        self.chbEvals.set_value(config.show_evals)
        self.cbJdepth.set_value(config.depth)
        self.change_depth(config.depth)
        self.cbJmultiPV.set_value(config.multiPV)

        self.ch_select_rival_move.setChecked(config.select_rival_move)

        self.edJugInicial.set_value(config.jugInicial)

        li = self.li_gm
        cb = self.cb_gm
        if config.modo == GM.GameMode.PERSONAL:
            if self.li_personal:
                li = self.li_personal
                cb = self.cb_gm
        for v in li:
            if v[1] == config.gm:
                cb.set_value(config.gm)
                break
        if bypass_book:
            for book in self.list_books.lista:
                if book.path == bypass_book.path:
                    self.cbBooks.set_value(book)
                    break
        self.opening_show()

    def openings_edit(self):
        self.btOpening.setDisabled(True)  # Puede tardar bastante vtime
        with QTMessages.one_moment_please(self):
            w = WindowOpenings.WOpenings(self, self.opening_block)
        self.btOpening.setDisabled(False)
        if w.exec():
            self.opening_block = w.resultado()
            self.opening_show()

    def preferred_openings(self):
        if len(self.li_preferred_openings) == 0:
            return
        menu = QTDialogs.LCMenu(self)
        menu.setToolTip(_("To choose: <b>left button</b> <br>To erase: <b>right button</b>"))
        f = Controles.FontType(puntos=8, peso=75)
        menu.set_font(f)
        n_pos = 0
        for nli, bloque in enumerate(self.li_preferred_openings):
            if isinstance(bloque, tuple):  # compatibilidad con versiones anteriores
                bloque = bloque[0]
                self.li_preferred_openings[nli] = bloque
            menu.opcion((n_pos, bloque), bloque.tr_name, Iconos.PuntoVerde())
            n_pos += 1

        resp = menu.lanza()
        if resp:
            n_pos, bloque = resp
            if menu.is_left:
                self.opening_block = bloque
                self.opening_show()
            elif menu.is_right:
                opening_block = bloque
                if QTMessages.pregunta(
                    self,
                    _X(
                        _("Do you want to delete the opening %1 from the list of favourite openings?"),
                        opening_block.tr_name,
                    ),
                ):
                    del self.li_preferred_openings[n_pos]

    def opening_show(self):
        if self.opening_block:
            label = f"{self.opening_block.tr_name}\n{self.opening_block.pgn}"
            self.btOpeningsQuitar.show()
        else:
            label = f"  {_('Undetermined')}  "
            self.btOpeningsQuitar.hide()
        self.btOpening.set_text(label)

    def openings_remove(self):
        self.opening_block = None
        self.opening_show()


def select_move(manager, li_moves, is_gm):
    menu = QTDialogs.LCMenu(manager.main_window)

    if is_gm:
        titulo = manager.nombreGM
        icono = Iconos.GranMaestro()
    else:
        titulo = _("Opponent's move")
        icono = Iconos.Carpeta()
    menu.opcion(None, titulo, icono)
    menu.separador()

    icono = Iconos.PuntoAzul() if is_gm else Iconos.PuntoNaranja()

    for from_sq, to_sq, promotion, label, pgn, num in li_moves:
        if label and (len(li_moves) > 1):
            txt = f"{pgn} - {label}"
        else:
            txt = pgn
        menu.opcion((from_sq, to_sq, promotion), txt, icono)
        menu.separador()

    resp = menu.lanza()
    if resp:
        return resp
    else:
        from_sq, to_sq, promotion, label, pgn, num = li_moves[0]
        return from_sq, to_sq, promotion


class WImportar(LCDialog.LCDialog):
    def __init__(self, w_parent, li_gm):

        self.li_gm = li_gm

        titulo = _("Import")
        icono = Iconos.ImportarGM()

        self.qtColor_woman = ScreenUtils.qt_color_rgb(221, 255, 221)

        extparam = "imp_gm"
        LCDialog.LCDialog.__init__(self, w_parent, titulo, icono, extparam)

        li_acciones = [
            (_("Import"), Iconos.Aceptar(), self.importar),
            None,
            (_("Cancel"), Iconos.Cancelar(), self.reject),
            None,
            (_("Mark"), Iconos.Marcar(), self.marcar),
            None,
        ]
        tb = QTDialogs.LCTB(self, li_acciones)

        # Lista
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("ELEGIDO", "", 22, is_checked=True)
        o_columns.nueva("NOMBRE", _("Grandmaster"), 140)
        o_columns.nueva("PARTIDAS", _("Games"), 60, align_right=True)
        o_columns.nueva("BORN", _("Birth date"), 80, align_center=True)

        self.grid = Grid.Grid(self, o_columns, alternate=False)
        n = self.grid.width_columns_displayables()
        self.grid.setMinimumWidth(n + 20)

        self.register_grid(self.grid)

        # Layout
        layout = Colocacion.V().control(tb).control(self.grid).margen(3)
        self.setLayout(layout)

        self.last_order = "NOMBRE", False

        self.restore_video(default_width=n + 26, default_height=400)

    def importar(self):
        self.save_video()
        self.accept()

    def marcar(self):
        menu = QTDialogs.LCMenu(self)
        f = Controles.FontType(puntos=8, peso=75)
        menu.set_font(f)
        menu.opcion(1, _("All"), Iconos.PuntoVerde())
        menu.opcion(2, _("None"), Iconos.PuntoNaranja())
        resp = menu.lanza()
        if resp:
            for obj in self.li_gm:
                obj["ELEGIDO"] = resp == 1
            self.grid.refresh()

    def grid_num_datos(self, _grid):
        return len(self.li_gm)

    def grid_setvalue(self, _grid, row, column, valor):
        self.li_gm[row][column.key] = valor

    def grid_dato(self, _grid, row, obj_column):
        return self.li_gm[row][obj_column.key]

    def grid_color_fondo(self, _grid, row, _col):
        if self.li_gm[row]["WM"] == "w":
            return self.qtColor_woman
        return None

    def grid_doubleclick_header(self, _grid, obj_column):
        cab, si_rev = self.last_order
        col_clave = obj_column.key

        def key(x):
            return str(x[col_clave]) if col_clave != "PARTIDAS" else int(x[col_clave])

        if cab == col_clave:
            si_rev = not si_rev
        else:
            si_rev = False
        self.li_gm.sort(key=key, reverse=si_rev)
        self.last_order = col_clave, si_rev
        self.grid.refresh()
        self.grid.gotop()


def importar_gm(owner_gm):
    web = "https://lucaschess.pythonanywhere.com/static/gm_mw"

    with QTMessages.WaitingMessage(owner_gm, _("Reading the list of Grandmasters from the web")):
        fich_name = "_listaGM.txt"
        url_lista = f"{web}/{fich_name}"
        fich_tmp = Code.configuration.temporary_file("txt")
        fich_lista = GM.get_folder_gm() / fich_name
        si_bien = Util.urlretrieve(url_lista, fich_tmp)

    if not si_bien:
        QTMessages.message_error(
            owner_gm,
            _("List of Grandmasters currently unavailable; please check Internet connectivity"),
        )
        return False

    with open(fich_tmp, "rt", encoding="utf-8", errors="ignore") as f:
        li_gm = []
        for linea in f:
            linea = linea.strip()
            if linea:
                gm, name, ctam, cpart, wm, cyear = linea.split("|")
                file = GM.get_folder_gm() / f"{gm}.xgm"
                if file.stat().st_size != int(ctam):  # si no existe tam = -1
                    dic = {
                        "GM": gm,
                        "NOMBRE": name,
                        "PARTIDAS": cpart,
                        "ELEGIDO": False,
                        "BORN": cyear,
                        "WM": wm,
                    }
                    li_gm.append(dic)

        if len(li_gm) == 0:
            QTMessages.message_bold(owner_gm, _("You have all Grandmasters installed."))
            return False

    fich_lista.unlink(missing_ok=True)
    shutil.copy2(fich_tmp, fich_lista)

    w = WImportar(owner_gm, li_gm)
    if w.exec():
        for dic in li_gm:
            if dic["ELEGIDO"]:
                gm = dic["GM"]
                gm_display = f"{gm[0].upper()}{gm[1:].lower()}"
                with QTMessages.WaitingMessage(owner_gm, _X(_("Import %1"), gm_display), opacity=1.0):
                    # Descargamos
                    fzip = f"{gm}.zip"
                    si_bien = Util.urlretrieve(f"{web}/{gm}.zip", fzip)

                    if si_bien:
                        with zipfile.ZipFile(fzip) as zfobj:
                            for name in zfobj.namelist():
                                file = GM.get_folder_gm() / name
                                with file.open("wb") as outfile:
                                    outfile.write(zfobj.read(name))
                        Path(fzip).unlink(missing_ok=True)

        return True

    return False


class SelectGame(LCDialog.LCDialog):
    def __init__(self, wgm, ogm):
        self.ogm = ogm
        self.liRegs = ogm.gen_toselect()
        self.si_reverse = False
        self.claveSort = None

        dgm = GM.dic_gm()
        name = dgm.get(ogm.gm, ogm.gm)
        titulo = f"{_('One game')} - {name}"
        icono = Iconos.Uno()
        extparam = "gm1g_1"
        LCDialog.LCDialog.__init__(self, wgm, titulo, icono, extparam)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NOMBRE", _("Opponent"), 180)
        o_columns.nueva("FECHA", _("Date"), 90, align_center=True)
        o_columns.nueva("EVENT", _("Event"), 140, align_center=True)
        o_columns.nueva("ECO", _("ECO"), 40, align_center=True)
        o_columns.nueva("RESULT", _("Result"), 64, align_center=True)
        o_columns.nueva("NUMMOVES", _("Moves"), 64, align_center=True)
        self.grid = Grid.Grid(self, o_columns, complete_row_select=True, select_multiple=True)
        width_pgn = self.grid.width_columns_displayables() + 20
        self.grid.setMinimumWidth(width_pgn)
        self.grid.alternate_colors()

        self.register_grid(self.grid)

        li_acciones = [
            (_("Accept"), Iconos.Aceptar(), self.aceptar),
            None,
            (_("Cancel"), Iconos.Cancelar(), self.cancelar),
            None,
        ]
        if ogm.isErasable:
            li_acciones.append((_("Remove"), Iconos.Borrar(), self.remove))
            li_acciones.append(None)

        tb = QTDialogs.LCTB(self, li_acciones)

        layout = Colocacion.V().control(tb).control(self.grid).margen(3)
        self.setLayout(layout)

        self.restore_video(default_width=400, default_height=400)
        self.gameElegida = None

    def grid_num_datos(self, _grid):
        return len(self.liRegs)

    def grid_dato(self, _grid, row, obj_column):
        return self.liRegs[row][obj_column.key]

    def grid_doble_click(self, _grid, _row, _obj_column):
        self.aceptar()

    def grid_doubleclick_header(self, _grid, obj_column):
        key = obj_column.key

        self.liRegs = sorted(self.liRegs, key=lambda x: x[key].upper())

        if self.claveSort == key:
            if self.si_reverse:
                self.liRegs.reverse()

            self.si_reverse = not self.si_reverse
        else:
            self.si_reverse = True

        self.grid.refresh()
        self.grid.gotop()

    def aceptar(self):
        self.gameElegida = self.liRegs[self.grid.recno()]["NUMBER"]
        self.save_video()
        self.accept()

    def cancelar(self):
        self.save_video()
        self.reject()

    def remove(self):
        li = self.grid.list_selected_recnos()
        if len(li) > 0:
            if QTMessages.pregunta(self, _("Do you want to delete all selected records?")):
                li.sort(reverse=True)
                for x in li:
                    self.ogm.remove(x)
                    del self.liRegs[x]
                self.grid.refresh()
