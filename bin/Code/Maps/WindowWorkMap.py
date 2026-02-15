from PySide6 import QtWidgets
from PySide6.QtSvgWidgets import QSvgWidget

import Code
from Code.Analysis import Analysis
from Code.Base import Game, Move, Position
from Code.Board import Board
from Code.Maps import WorkMap
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
    ScreenUtils,
)


class WMap(LCDialog.LCDialog):
    def __init__(self, procesador, mapa):
        self.workmap = WorkMap.WorkMap(mapa)
        titulo = self.workmap.name_map()
        icono = getattr(Iconos, mapa)()

        LCDialog.LCDialog.__init__(self, procesador.main_window, titulo, icono, f"{mapa}01")

        self.procesador = procesador

        self.playCurrent = None

        o_columns = Columnas.ListaColumnas()

        dic_iconos = {"1": Iconos.pmPuntoRojo(), "5": Iconos.pmApproval()}

        o_columns.nueva(
            "TYPE",
            "",
            24,
            edicion=Delegados.PmIconosBMT(dict_icons=dic_iconos),
            align_center=True,
        )
        o_columns.nueva("SELECT", _("Select a country"), 140)

        self.grid = Grid.Grid(self, o_columns, complete_row_select=True, xid="W")

        self.register_grid(self.grid)

        li_acciones = [
            (_("Close"), Iconos.MainMenu(), self.finalize),
            None,
            (_("Play"), Iconos.Empezar(), self.play),
            None,
            (_("Pending"), Iconos.Check(), self.pending),
        ]

        self.tb_work = QTDialogs.LCTB(self, li_acciones, icon_size=24)

        self.lbInfo = Controles.LB(self)

        self.wsvg = wsvg = QSvgWidget()

        ly = Colocacion.V().control(self.tb_work).control(self.lbInfo).control(self.grid)
        w = QtWidgets.QWidget()
        w.setLayout(ly)

        splitter = QtWidgets.QSplitter(self)
        splitter.addWidget(w)
        splitter.addWidget(wsvg)
        self.register_splitter(splitter, "splitter")

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("ACTIVE", _("Active"), 80, align_center=True)
        o_columns.nueva("TYPE", _("Type"), 110, align_center=True)
        o_columns.nueva("DCREATION", _("Creation date"), 140, align_center=True)
        o_columns.nueva("DONE", _("Done"), 110, align_center=True)
        o_columns.nueva("DEND", _("End date"), 110, align_center=True)
        o_columns.nueva("RESULT", _("Result"), 110, align_center=True)

        self.gridData = Grid.Grid(self, o_columns, complete_row_select=True, xid="H", is_column_header_movable=False)
        self.register_grid(self.gridData)

        li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.finalize),
            None,
            (_("Select"), Iconos.Seleccionar(), self.data_select),
            None,
            (_("New"), Iconos.NuevoMas(), self.data_new),
            None,
            (_("Remove"), Iconos.Borrar(), self.data_remove),
            None,
        )
        tb = QTDialogs.LCTB(self, li_acciones)

        ly = Colocacion.V().control(tb).control(self.gridData)
        w = QtWidgets.QWidget()
        w.setLayout(ly)

        self.tab = Controles.Tab()
        self.tab.set_position_west()
        self.tab.new_tab(splitter, _("Map"))
        self.tab.new_tab(w, _("Data"))

        ly = Colocacion.H().control(self.tab).margen(0)
        self.setLayout(ly)

        self.restore_video(with_tam=True, default_width=960, default_height=600)

        self.workmap.set_widget(wsvg)
        self.workmap.reset_widget()
        self.grid.gotop()
        self.gridData.gotop()

        self.informacion()

        self.check_pending()

    def check_pending(self):
        nli = len(self.list_pending())
        self.tb_work.set_action_visible(self.pending, 0 < nli < 10)
        self.tb_work.set_action_visible(self.play, nli > 0)

    def list_pending(self):
        return [reg for reg in self.workmap.dic.values() if not len(reg.donePV.strip())]

    def pending(self):
        li = self.list_pending()
        menu = QTDialogs.LCMenuRondo(self)
        for reg in li:
            menu.opcion(None, reg.name)
            menu.separador()
        menu.lanza()

    def data_new(self):
        menu = QTDialogs.LCMenu(self)

        menu1 = menu.submenu(_("Checkmates in GM games"), Iconos.GranMaestro())
        menu1.opcion("mate_basic", _("Basic"), Iconos.PuntoAzul())
        menu1.separador()
        menu1.opcion("mate_easy", _("Easy"), Iconos.PuntoAmarillo())
        menu1.opcion("mate_medium", _("Medium"), Iconos.PuntoNaranja())
        menu1.opcion("mate_hard", _("Hard"), Iconos.PuntoRojo())

        menu.separador()
        menu.opcion("sts_basic", _("STS: Strategic Test Suite"), Iconos.STS())

        resp = menu.lanza()
        if resp:
            tipo, model = resp.split("_")
            if tipo == "sts":
                li_gen: list = [(None, None)]
                li_r = [(str(x), x) for x in range(1, 100)]
                config = FormLayout.Combobox(_("Model"), li_r)
                li_gen.append((config, "1"))
                resultado = FormLayout.fedit(
                    li_gen,
                    title=_("STS: Strategic Test Suite"),
                    parent=self,
                    minimum_width=160,
                    icon=Iconos.Maps(),
                )
                if resultado is None:
                    return
                accion, li_resp = resultado
                model = li_resp[0]
            self.workmap.nuevo(tipo, model)
            self.active_workmap()

    def do_work(self):
        tipo = self.workmap.tipo
        if tipo == "mate":
            self.playCurrent = self.workmap
            self.save_video()
            self.accept()

        elif tipo == "sts":
            w = WUnSTSMap(self)
            w.exec()
            self.gridData.refresh()
            self.workmap.reset_widget()
            self.informacion()
            self.grid.refresh()

    def data_select(self):
        row = self.gridData.recno()
        self.workmap.activa_rowid(row)
        self.active_workmap(gotop=False)
        self.check_pending()

    def active_workmap(self, gotop=True):
        self.workmap.set_widget(self.wsvg)
        self.workmap.reset_widget()
        self.grid.refresh()
        self.gridData.refresh()

        self.grid.gotop()
        if gotop:
            self.gridData.gotop()

        self.informacion()

    def data_remove(self):
        raw = self.workmap.db.list_raws[self.gridData.recno()]
        if raw["ACTIVE"] != "X":
            if QTMessages.pregunta(self, _X(_("Delete %1?"), _("this work"))):
                self.workmap.db.borra(raw["ROWID"])
                self.gridData.refresh()

    def informacion(self):
        current = self.workmap.name_current()
        hechos, total = self.workmap.get_done()
        info = self.workmap.get_info()
        tipo = self.workmap.get_tipo()
        txt = f"<b><span style=\"color:#C156F8\">{_('Active')}: {current}</span>" if current else ""
        txt += (
            f"<br><span style=\"color:brown\">{_('Type')}: {tipo}</span></b>"
            + '<br><span style="color:teal">%s: %d/%d</span></b>' % (_("Done"), hechos, total)
            + f"<br><span style=\"color:blue\">{_('Result')}: {info if info else ''}</span></b>"
        )
        self.lbInfo.set_text(txt)

    def lanza(self, row):
        si_hecho = self.workmap.set_aim_row(row)
        if si_hecho:
            self.workmap.reset_widget()
            self.informacion()
            self.grid.gotop()
            self.grid.refresh()
        else:
            self.do_work()

    def grid_doble_click(self, grid, row, _obj_column):
        if grid == self.grid:
            self.lanza(row)
        else:
            self.data_select()
            self.tab.activate(0)

    def play(self):
        row = self.grid.recno()
        self.lanza(row)

    def finalize(self):
        self.save_video()
        self.reject()

    def grid_num_datos(self, grid):
        return self.workmap.num_rows() if grid.id == "W" else self.workmap.db.num_rows()

    def grid_dato(self, grid, row, obj_column):
        key = obj_column.key
        return self.workmap.dato(row, key) if grid.id == "W" else self.workmap.db.dato(row, key)


class WUnSTSMap(LCDialog.LCDialog):
    def __init__(self, owner):

        self.workmap = owner.workmap
        self.procesador = owner.procesador
        self.configuration = Code.configuration
        self.alm = self.workmap.get_aim()
        self.position = None
        self.move_pv = None

        LCDialog.LCDialog.__init__(self, owner, _("STS: Strategic Test Suite"), Iconos.STS(), "stsmap")

        # Board
        config_board = self.configuration.config_board("STSMAP", 48)

        self.board = Board.Board(self, config_board)
        self.board.draw_window()
        self.board.set_dispatcher(self.player_has_moved_dispatcher)

        # Rotulos informacion
        self.lbJuego = Controles.LB(self).set_wrap().minimum_width(200).align_center()

        # Tool bar
        self.li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.seguir),
            (_("Cancel"), Iconos.Cancelar(), self.cancelar),
            (_("Analysis"), Iconos.Tutor(), self.analizar),
        )
        self.tb = QTDialogs.LCTB(self, self.li_acciones)

        ly_t = Colocacion.V().control(self.board).relleno()
        ly_v = Colocacion.V().control(self.tb).relleno().control(self.lbJuego).relleno(2)
        ly = Colocacion.H().otro(ly_t).otro(ly_v)

        self.setLayout(ly)

        self.restore_video()

        self.pon_toolbar(self.cancelar)
        self.pon_juego()
        ScreenUtils.shrink(self)

    def cancelar(self):
        self.save_video()
        self.reject()

    def seguir(self):
        self.cancelar()

    def pon_toolbar(self, *li_current):
        for txt, ico, rut in self.li_acciones:
            self.tb.set_action_visible(rut, rut in li_current)

    def pon_juego(self):
        self.pon_toolbar(self.cancelar)

        self.position = cp = Position.Position()
        cp.read_fen(self.alm.fen)

        mens = f"<h2>{self.alm.name}</h2><br>"

        si_w = cp.is_white
        color, color_r = _("White"), _("Black")
        c_k, c_q, c_kr, c_qr = "K", "Q", "k", "q"
        if not si_w:
            color, color_r = color_r, color
            c_k, c_q, c_kr, c_qr = c_kr, c_qr, c_k, c_q

        if cp.castles:

            def menr(ck, cq):
                xenr = ""
                if ck in cp.castles:
                    xenr += "O-O"
                if cq in cp.castles:
                    if xenr:
                        xenr += "  +  "
                    xenr += "O-O-O"
                return xenr

            enr = menr(c_k, c_q)
            if enr:
                mens += f"<br>{color} : {enr}"
            enr = menr(c_kr, c_qr)
            if enr:
                mens += f"<br>{color_r} : {enr}"
        if cp.en_passant != "-":
            mens += f"<br>     {_('En passant')} : {cp.en_passant}"
        self.lbJuego.set_text(mens)

        si_w = cp.is_white
        self.board.set_position(cp)
        self.board.set_side_bottom(si_w)
        self.board.set_side_indicator(si_w)
        self.board.activate_side(si_w)

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        self.board.disable_all()

        # Peon coronando
        if not promotion and self.position.pawn_can_promote(from_sq, to_sq):
            promotion = self.board.pawn_promoting(self.position.is_white)

        ok, mens, move = Move.get_game_move(None, self.position, from_sq, to_sq, promotion)
        if ok:
            self.board.set_position(move.position)
            self.board.put_arrow_sc(from_sq, to_sq)
            self.move_done(move)
        else:
            self.pon_juego()
            return False
        return True

    def move_done(self, move):
        self.board.disable_all()
        game = Game.Game(first_position=move.position_before)
        game.add_move(move)
        move.game = game
        self.move_pv = move

        self.pon_toolbar(self.seguir, self.analizar)

        done_pv = move.movimiento().lower()
        dic_results = self.alm.dic_results

        mens = f"<h2>{self.alm.name}</h2><br>"

        mens += f"<table><tr><th>{_('Move')}</th><th>{_('Score')}</th></tr>"
        mx = 0
        ok = False
        style_pv = ' style="color:red;"'
        for pv, points in dic_results.items():
            if done_pv == pv.lower():
                ok = True
                mas = style_pv
            else:
                mas = ""
            san = Game.pv_san(self.alm.fen, pv)
            mens += '<tr%s><td align="center">%s</td><td align="right">%d</td></tr>' % (
                mas,
                san,
                points,
            )
            if points > mx:
                mx = points
        if not ok:
            san = Game.pv_san(self.alm.fen, done_pv)
            mens += '<tr%s><td align="center">%s</td><td align="right">%d</td></tr>' % (
                style_pv,
                san,
                0,
            )
        mens += "</table>"

        self.alm.donePV = done_pv
        self.alm.puntos = dic_results.get(done_pv, 0)
        self.alm.total = mx

        mens += "<br><h2>%s: %d/%d</h2>" % (_("Score"), self.alm.puntos, self.alm.total)
        self.lbJuego.set_text(mens)

        self.workmap.win_aim(self, done_pv)

    def analizar(self):
        manager_tutor = self.procesador.get_manager_tutor()
        Analysis.show_analysis(
            manager_tutor,
            self.move_pv,
            self.position.is_white,
            1,
            main_window=self,
            must_save=False,
        )


def train_map(procesador, mapa):
    w = WMap(procesador, mapa)
    w.exec()
    return w.playCurrent
