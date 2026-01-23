from typing import Optional

import os

import FasterCode
from PySide6 import QtWidgets

from Code.Base import Game, Position
from Code.Books import Books, WBooks
from Code.Databases import DBgames, DBgamesST, WDB_Games, WDB_Summary
from Code.Openings import POLAnalisisTree
from Code.QT import Colocacion, Columnas, Controles, Delegados, FormLayout, Grid, Iconos, QTDialogs
from Code.Engines import EngineManagerAnalysis


class TabEngine(QtWidgets.QWidget):
    current_posicion: Position.Position | None

    def __init__(self, tabs_analisis, procesador, configuration):
        QtWidgets.QWidget.__init__(self)

        self.analyzing = False
        self.position = None
        self.li_analysis = []
        self.engine_manager: Optional[EngineManagerAnalysis.EngineManagerAnalysis] = None
        self.current_mrm = None
        self.pv = None

        self.dbop = tabs_analisis.dbop

        self.procesador = procesador
        self.configuration = configuration

        self.with_figurines = configuration.x_pgn_withfigurines

        self.tabsAnalisis = tabs_analisis
        self.bt_start = Controles.PB(self, "", self.start).set_icono(Iconos.Pelicula_Seguir(), 32)
        self.bt_stop = Controles.PB(self, "", self.stop).set_icono(Iconos.Pelicula_Pausa(), 32)
        self.bt_stop.hide()

        self.lb_engine = Controles.LB(self, f"{_('Engine')}:")
        list_engines = configuration.engines.list_name_alias()  # (name, key)
        default = configuration.x_tutor_clave
        engine = self.dbop.getconfig("ENGINE", default)
        if len([key for name, key in list_engines if key == engine]) == 0:
            engine = default
        self.cb_engine = Controles.CB(self, list_engines, engine).capture_changes(self.reset_engine)

        multipv = self.dbop.getconfig("ENGINE_MULTIPV", 5)
        lb_multipv = Controles.LB(self, f"{_('Multi PV')}: ")
        self.sb_multipv = Controles.SB(self, multipv, 1, 500).relative_width(50)

        self.chb_show_analysis = Controles.CHB(self, _("Show the analysis"), self.dbop.getconfig("SHOW_ANALYSIS", True))
        self.chb_show_analysis.capture_changes(self.check_show_analysis)

        self.lb_analisis = Controles.LB(self, "").set_font_type(puntos=configuration.x_pgn_fontpoints).set_wrap()
        self.configuration.set_property(self.lb_analisis, "pgn")

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("PDT", "", 120, align_center=True)
        delegado = Delegados.EtiquetaPOS(True, with_lines=False) if self.with_figurines else None
        o_columns.nueva("SOL", "", 100, align_center=True, edicion=delegado)
        o_columns.nueva("PGN", _("Solution"), 860)

        self.grid_analysis = Grid.Grid(self, o_columns, complete_row_select=True, header_heigh=4)
        self.grid_analysis.font_type(puntos=configuration.x_pgn_fontpoints)
        self.grid_analysis.set_height_row(configuration.x_pgn_rowheight)
        # self.register_grid(self.grid_analysis)

        ly_lin1 = Colocacion.H().control(self.bt_start).control(self.bt_stop).control(self.lb_engine)
        ly_lin1.control(self.cb_engine)
        ly_lin1.espacio(50).control(lb_multipv).control(self.sb_multipv).relleno().control(self.chb_show_analysis)
        ly = Colocacion.V().otro(ly_lin1).control(self.lb_analisis).control(self.grid_analysis).margen(3)

        self.setLayout(ly)

        self.reset_engine()

    def check_show_analysis(self):
        ok = self.chb_show_analysis.valor()
        self.dbop.setconfig("SHOW_ANALYSIS", ok)
        self.tabsAnalisis.wlines.check_show_analysis()

    def save_current(self):
        if self.current_mrm:
            fenm2 = self.current_posicion.fenm2()
            dic = self.dbop.getfenvalue(fenm2)
            if "ANALISIS" in dic:
                mrm_ant = dic["ANALISIS"]
                if mrm_ant.getdepth0() > self.current_mrm.getdepth0():
                    return
            dic["ANALISIS"] = self.current_mrm
            self.dbop.setfenvalue(fenm2, dic)

    def set_data(self, label, position, pv):
        self.save_current()
        self.position = position
        self.pv = pv
        self.lb_analisis.set_text(label)
        if self.analyzing:
            self.analyzing = False
            self.engine_manager.stop()
            game = Game.Game(self.position)
            self.engine_manager.analyze_nomodal(game)
            self.analyzing = True
        else:
            fenm2 = position.fenm2()
            dic = self.dbop.getfenvalue(fenm2)
            if "ANALISIS" in dic:
                self.show_analisis(dic["ANALISIS"])
            else:
                self.li_analysis = []
                self.grid_analysis.refresh()

    def start(self):
        self.current_mrm = None
        self.current_posicion = None
        self.sb_multipv.setDisabled(True)
        self.cb_engine.setDisabled(True)
        self.analyzing = True
        self.sb_multipv.setDisabled(True)
        self.show_stop()
        multipv = self.sb_multipv.valor()
        game = Game.Game(self.position)
        self.engine_manager.set_multipv_var(multipv)
        self.engine_manager.connect_depthchanged(self.lee_analisis)
        self.engine_manager.analyze_nomodal(game)

    def show_start(self):
        self.bt_stop.hide()
        self.bt_start.show()

    def show_stop(self):
        self.bt_start.hide()
        self.bt_stop.show()

    def show_analisis(self, mrm):
        self.current_mrm = mrm
        self.current_posicion = self.position
        li = []
        for rm in mrm.li_rm:
            game = Game.Game(self.position)
            game.read_pv(rm.pv)
            pgn = game.pgn_base_raw(translated=False)
            lit = pgn.split(" ")
            is_white = self.position.is_white
            if is_white:
                pgn0 = lit[0].split(".")[-1]
                pgn1 = " ".join(lit[1:])
            else:
                pgn0 = lit[1]
                pgn1 = " ".join(lit[2:])

            if self.with_figurines:
                game.ms_sol = pgn0, is_white, None, None, None, None, False, False
            else:
                game.ms_sol = pgn0
            game.ms_pgn = pgn1
            game.ms_pdt = rm.abbrev_text_pdt()
            li.append(game)
        self.li_analysis = li
        self.grid_analysis.refresh()

    def lee_analisis(self, mrm):
        if self.analyzing:
            self.show_analisis(mrm)

    def stop(self):
        self.save_current()
        self.sb_multipv.setDisabled(False)
        self.cb_engine.setDisabled(False)
        self.analyzing = False
        self.show_start()
        if self.engine_manager:
            self.engine_manager.stop()
        self.tabsAnalisis.refresh_lines()

    def reset_engine(self):
        self.save_current()
        key = self.cb_engine.valor()
        if not key:
            return
        self.analyzing = False
        if self.engine_manager:
            self.engine_manager.close()
        self.stop()
        engine = self.configuration.engines.search(key)

        multipv = self.sb_multipv.valor()
        self.engine_manager = self.procesador.create_manager_analysis(engine, 0, 0, 0, multipv)

    def grid_num_datos(self, _grid):
        return len(self.li_analysis)

    def grid_dato(self, _grid, row, obj_column):
        if obj_column.key == "PDT":
            return self.li_analysis[row].ms_pdt
        elif obj_column.key == "SOL":
            return self.li_analysis[row].ms_sol
        else:
            return self.li_analysis[row].ms_pgn

    def grid_right_button(self, _grid, row, _obj_column, _modif):
        if row < 0:
            return
        menu = QTDialogs.LCMenu(self)
        menu.opcion("current", _("Add current"), Iconos.This())
        menu.separador()
        if len(self.li_analysis) > 1:
            menu.opcion("all", _("Add all"), Iconos.All())
            menu.separador()
            if row > 1:
                menu.opcion("previous", _("Add previous"), Iconos.Previous())
                menu.separador()
        menu.separador()
        menu.opcion("more", _("More options"), Iconos.More())
        tp = menu.lanza()
        if tp is None:
            return
        plies = 1
        if tp == "more":
            dic = self.configuration.read_variables("OL_ENGINE_VAR")
            tp = dic.get("TYPE", "current")
            plies = dic.get("PLIES", 1)

            form = FormLayout.FormLayout(self, _("More options"), Iconos.More())
            form.separador()
            li_options = [(_("Current"), "current")]
            if len(self.li_analysis) > 1:
                li_options.append((_("All"), "all"))
                if len(self.li_analysis) > 2 and row > 0:
                    li_options.append((_("Previous"), "previous"))
            form.combobox(_("Variations to add"), li_options, tp)
            form.separador()
            form.spinbox(_("Movements to add in each variation"), 0, 999, 50, plies)
            form.apart_simple_np(f"    {_('Full line')} = 0")
            form.separador()
            resp = form.run()
            if resp is None:
                return

            x, li_gen = resp
            tp, plies = li_gen
            dic = {"TYPE": tp, "PLIES": plies}
            self.configuration.write_variables("OL_ENGINE_VAR", dic)

        if tp == "current":
            lst_rows = [row]
        elif tp == "all":
            lst_rows = list(range(len(self.li_analysis)))
        else:
            lst_rows = list(range(row))

        refresh = False
        for row in lst_rows:
            g = self.li_analysis[row]
            if len(g) > 0:
                pv = self.pv
                if plies == 0:
                    pv += f" {g.pv()}"
                else:
                    for n in range(plies):
                        pv += f" {g.move(n).movimiento()}"
                if self.dbop.append_pv(pv.strip()):
                    refresh = True

        if refresh:
            self.tabsAnalisis.refresh_lines()

    def save_config(self):
        self.dbop.setconfig("ENGINE", self.cb_engine.valor())
        self.dbop.setconfig("ENGINE_MULTIPV", self.sb_multipv.valor())


class TabBook(QtWidgets.QWidget):
    def __init__(self, tabs_analisis, book, configuration):
        QtWidgets.QWidget.__init__(self)

        self.tabsAnalisis = tabs_analisis
        self.position = None
        self.leido = False
        self.pv = None

        self.dbop = tabs_analisis.dbop

        self.book = book
        book.polyglot()
        self.li_moves = []

        self.with_figurines = configuration.x_pgn_withfigurines

        o_columns = Columnas.ListaColumnas()
        delegado = Delegados.EtiquetaPOS(True, with_lines=False) if self.with_figurines else None
        for x in range(20):
            o_columns.nueva(str(x), "", 80, align_center=True, edicion=delegado)
        self.grid_moves = Grid.Grid(
            self,
            o_columns,
            complete_row_select=True,
            is_column_header_movable=False,
            header_visible=False,
        )
        self.grid_moves.font_type(puntos=configuration.x_pgn_fontpoints)
        self.grid_moves.set_height_row(configuration.x_pgn_rowheight)

        ly = Colocacion.V().control(self.grid_moves).margen(3)

        self.setLayout(ly)

    def grid_num_datos(self, _grid):
        return len(self.li_moves)

    def grid_dato(self, _grid, row, obj_column):
        mv = self.li_moves[row]
        li = mv.dato
        key = int(obj_column.key)
        pgn = li[key]
        if self.with_figurines:
            is_white = " w " in mv.fen
            return pgn, is_white, None, None, None, None, False, True
        else:
            return pgn

    def grid_doble_click(self, _grid, row, _obj_column):
        alm_base = self.li_moves[row]
        if row != len(self.li_moves) - 1:
            alm_base1 = self.li_moves[row + 1]
            if alm_base.nivel < alm_base1.nivel:
                if self.borra_subnivel(row + 1):
                    self.grid_moves.refresh()
                return

        self.lee_subnivel(row)
        self.grid_moves.refresh()

    def grid_right_button(self, _grid, row, _obj_column, _modificadores):
        if row < 0:
            return
        menu = QTDialogs.LCMenu(self)
        menu.opcion("current", _("Add current"), Iconos.This())
        menu.separador()

        if len(self.li_moves) > 1:
            menu.opcion("all", _("Add all"), Iconos.All())
            menu.separador()

            if row > 1:
                menu.opcion("previous", _("Add previous"), Iconos.Previous())
                menu.separador()

            slevel = set()
            for alm in self.li_moves:
                slevel.add(alm.nivel)
            if len(slevel) > 1:
                menu.opcion("level", _("Add all of current level"), Iconos.Arbol())
                menu.separador()

        resp = menu.lanza()
        if resp is None:
            return

        if resp == "all":
            lst_rows = list(range(len(self.li_moves)))
        elif resp == "previous":
            lst_rows = list(range(row))
        elif resp == "level":
            lst_rows = [row]
            lv = self.li_moves[row].nivel
            for r in range(row - 1, -1, -1):
                alm = self.li_moves[r]
                if alm.nivel == lv:
                    lst_rows.append(r)
                elif alm.nivel < lv:
                    break
            for r in range(row + 1, len(self.li_moves)):
                alm = self.li_moves[r]
                if alm.nivel == lv:
                    lst_rows.append(r)
                elif alm.nivel < lv:
                    break
        else:
            lst_rows = [row]

        refresh = False
        for row in lst_rows:
            pv = self.li_moves[row].pv
            lv = self.li_moves[row].nivel
            for r in range(row - 1, -1, -1):
                alm = self.li_moves[r]
                if alm.nivel < lv:
                    pv = f"{alm.pv} {pv}"
                    lv = alm.nivel
            pv = f"{self.pv} {pv}"
            if self.dbop.append_pv(pv.strip()):
                refresh = True

        if refresh:
            self.tabsAnalisis.refresh_lines()

    def set_data(self, position, pv):
        self.position = position
        self.pv = pv
        self.start()

    def borra_subnivel(self, row):
        alm = self.li_moves[row]
        nv = alm.nivel
        if nv == 0:
            return False
        li = []
        for x in range(row, 0, -1):
            alm1 = self.li_moves[x]
            if alm1.nivel < nv:
                break
            li.append(x)
        for x in range(row + 1, len(self.li_moves)):
            alm1 = self.li_moves[x]
            if alm1.nivel < nv:
                break
            li.append(x)
        li.sort(reverse=True)
        for x in li:
            del self.li_moves[x]

        return True

    def lee_subnivel(self, row):
        alm_base = self.li_moves[row]
        if alm_base.nivel >= 17:
            return
        FasterCode.set_fen(alm_base.fen)
        if FasterCode.move_pv(alm_base.from_sq, alm_base.to_sq, alm_base.promotion):
            fen = FasterCode.get_fen()
            for alm in self.book.alm_list_moves(fen):
                nv = alm.nivel = alm_base.nivel + 1
                alm.dato = [""] * 20
                alm.dato[nv] = alm.pgn
                alm.dato[nv + 1] = alm.porc
                alm.dato[nv + 2] = "%d" % alm.weight
                row += 1
                self.li_moves.insert(row, alm)

    def lee(self):
        if not self.leido and self.position:
            fen = self.position.fen()
            self.li_moves = self.book.alm_list_moves(fen)
            for alm in self.li_moves:
                alm.nivel = 0
                alm.dato = [""] * 20
                alm.dato[0] = alm.pgn
                alm.dato[1] = alm.porc
                alm.dato[2] = "%d" % alm.weight
            self.leido = True

    def start(self):
        self.leido = False
        self.lee()
        self.grid_moves.refresh()

    def stop(self):
        pass


class TabDatabaseSummary(QtWidgets.QWidget):
    position: Position.Position

    def __init__(self, tabs_analisis, procesador, dbstat):
        QtWidgets.QWidget.__init__(self)

        self.tabsAnalisis = tabs_analisis

        self.pv = None

        self.dbstat = dbstat

        self.wsummary = WDB_Summary.WSummaryBase(procesador, dbstat)

        layout = Colocacion.H().control(self.wsummary)
        self.setLayout(layout)

    def set_data(self, position, pv):
        self.pv = pv
        self.position = position
        self.wsummary.update_pv(self.pv)

    def start(self):
        self.wsummary.update_pv(self.pv)

    def stop(self):
        self.dbstat.close()


class InfoMoveReplace:
    def __init__(self, owner):
        self.tab_database = owner
        self.board = self.tab_database.tabsAnalisis.wlines.pboard.board

    @staticmethod
    def game_mode(_x, _y):
        return True


class TabDatabase(QtWidgets.QWidget):
    position: Position.Position

    def __init__(self, tabs_analisis, db):
        QtWidgets.QWidget.__init__(self)

        self.tabsAnalisis = tabs_analisis
        self.is_temporary = False

        self.pv = None

        self.db = db

        self.wgames = WDB_Games.WGames(self, db, None, False)
        self.wgames.tbWork.hide()
        self.wgames.status.hide()
        self.wgames.infoMove = InfoMoveReplace(self)

        layout = Colocacion.H().control(self.wgames)
        self.setLayout(layout)

    def tw_terminar(self):
        return

    def set_data(self, position, pv):
        self.position = position
        self.set_pv(pv)

    def set_pv(self, pv):
        self.pv = pv
        self.db.filter_pv(pv)
        self.wgames.grid.refresh()
        self.wgames.grid.gotop()

    def start(self):
        self.set_pv(self.pv)

    def stop(self):
        self.db.close()


class TabsAnalisis(QtWidgets.QWidget):
    def __init__(self, wlines, procesador, configuration):
        QtWidgets.QWidget.__init__(self)

        self.wlines = wlines
        self.dbop = wlines.dbop

        self.procesador = procesador
        self.configuration = configuration
        self.game = None
        self.njg = None

        self.tabtree = POLAnalisisTree.TabTree(self, configuration)
        self.tabengine = TabEngine(self, procesador, configuration)

        self.li_tabs = [("engine", self.tabengine), ("tree", self.tabtree)]
        self.tabActive = 0

        self.tabs = Controles.Tab(wlines)
        self.tabs.set_font_type(puntos=self.configuration.x_pgn_fontpoints)
        self.tabs.setTabIcon(0, Iconos.Engine())
        self.tabs.new_tab(self.tabengine, _("Engine"))
        self.tabs.new_tab(self.tabtree, _("Tree"))
        self.tabs.setTabIcon(1, Iconos.Arbol())

        self.tabs.dispatch_change(self.tab_changed)

        tab_button = QtWidgets.QToolButton(self)
        tab_button.setIcon(Iconos.Nuevo())
        tab_button.clicked.connect(self.crea_tab)
        li = [
            (_("Analysis of next move"), True),
            (_("Analysis of current move"), False),
        ]
        self.cb_nextmove = Controles.CB(self, li, True).capture_changes(self.changed_next_move)

        corner_widget = QtWidgets.QWidget(self)
        ly_corner = Colocacion.H().control(self.cb_nextmove).control(tab_button).margen(0)
        corner_widget.setLayout(ly_corner)

        self.tabs.setCornerWidget(corner_widget)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.tab_close_requested)

        self.tabs.quita_x(0)
        self.tabs.quita_x(1)

        layout = Colocacion.V()
        layout.control(self.tabs).margen(0)
        self.setLayout(layout)

    def changed_next_move(self):
        if self.game is not None:
            self.set_position(self.game, self.njg)

    def tab_changed(self, ntab):
        self.tabActive = ntab
        if ntab > 0:
            tipo, wtab = self.li_tabs[ntab]
            wtab.start()

    def tab_close_requested(self, ntab):
        tipo, wtab = self.li_tabs[ntab]
        wtab.stop()
        if ntab > 1:
            del self.li_tabs[ntab]
            self.tabs.removeTab(ntab)
            del wtab

    def crea_tab(self):
        menu = QTDialogs.LCMenu(self)
        menu.opcion("book", _("Polyglot book"), Iconos.Libros())
        menu.separador()
        menu.opcion("database", _("Database"), Iconos.Database())
        menu.separador()
        menu.opcion("summary", _("Database opening explorer"), Iconos.Arbol())
        resp = menu.lanza()
        pos = 0
        if resp == "book":
            book = self.selecciona_libro()
            if book:
                tabbook = TabBook(self, book, self.configuration)
                self.li_tabs.append((resp, tabbook))
                pos = len(self.li_tabs) - 1
                self.tabs.new_tab(tabbook, book.name, pos)
                self.tabs.setTabIcon(pos, Iconos.Libros())
                self.set_position(self.game, self.njg, pos)

        elif resp == "summary":
            nomfichgames = QTDialogs.select_db(self, self.configuration, True, False)
            if nomfichgames:
                db_stat = DBgamesST.TreeSTAT(f"{nomfichgames}.st1")
                tabdb = TabDatabaseSummary(self, self.procesador, db_stat)
                self.li_tabs.append((resp, tabdb))
                pos = len(self.li_tabs) - 1
                self.set_position(self.game, self.njg, pos)
                name = os.path.basename(nomfichgames)[:-5]
                self.tabs.new_tab(tabdb, name, pos)
                self.tabs.setTabIcon(pos, Iconos.Arbol())

        elif resp == "database":
            nomfichgames = QTDialogs.select_db(self, self.configuration, True, False)
            if nomfichgames:
                db = DBgames.DBgames(nomfichgames)
                tabdb = TabDatabase(self, db)
                self.li_tabs.append((resp, tabdb))
                pos = len(self.li_tabs) - 1
                self.set_position(self.game, self.njg, pos)
                name = os.path.basename(nomfichgames)[:-5]
                self.tabs.new_tab(tabdb, name, pos)
                self.tabs.setTabIcon(pos, Iconos.Database())
        self.tabs.activate(pos)

    def set_position(self, game, njg, num_tab=None):
        if game is None:
            return
        move = game.move(njg)
        self.game = game
        self.njg = njg
        nextmove = self.cb_nextmove.valor()
        if move:
            if njg == 0:
                pv = game.pv_hasta(njg) if nextmove else ""
            else:
                pv = game.pv_hasta(njg if nextmove else njg - 1)
            position = move.position if nextmove else move.position_before
        else:
            position = Position.Position().set_pos_initial()
            pv = ""

        for ntab, (tipo, tab) in enumerate(self.li_tabs):
            if ntab == 0:
                p = Game.Game()
                p.read_pv(pv)
                tab.set_data(
                    p.pgn_html(with_figurines=self.configuration.x_pgn_withfigurines),
                    position,
                    pv,
                )
            else:
                if num_tab is not None:
                    if ntab != num_tab:
                        continue
                if ntab > 1:
                    tab.set_data(position, pv)
                    tab.start()

    def selecciona_libro(self):
        list_books = Books.ListBooks()
        menu = QTDialogs.LCMenu(self)
        rondo = QTDialogs.rondo_puntos()
        for book in list_books.lista:
            menu.opcion(("x", book), book.name, rondo.otro())
            menu.separador()
        menu.opcion(("n", None), _("Registered books"), Iconos.Nuevo())
        resp = menu.lanza()
        if resp:
            orden, book = resp
            if orden == "x":
                pass
            elif orden == "n":
                WBooks.registered_books(self)
        else:
            book = None
        return book

    def save_config(self):
        for tipo, wtab in self.li_tabs:
            if tipo == "engine":
                wtab.save_config()

    def refresh_lines(self):
        self.wlines.refresh_lines()
