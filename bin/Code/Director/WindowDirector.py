from PySide6 import QtCore, QtGui, QtWidgets

import Code
from Code.Z import Util
from Code.Board import BoardTypes
from Code.Director import (
    TabVisual,
    WindowTab,
    WindowTabVArrows,
    WindowTabVCircles,
    WindowTabVMarcos,
    WindowTabVMarkers,
    WindowTabVSVGs,
)
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
    QTUtils,
)
from Code.SQL import UtilSQL
from Code.Translations import TrListas


class WPanelDirector(LCDialog.LCDialog):
    db_config: UtilSQL.DictSQL
    db_arrows: UtilSQL.DictSQL
    db_marcos: UtilSQL.DictSQL
    db_circles: UtilSQL.DictSQL
    db_svgs: UtilSQL.DictSQL
    db_markers: UtilSQL.DictSQL

    def __init__(self, owner, board):
        self.owner = owner
        self.position = board.last_position
        self.board = board
        self.configuration = board.configuration
        self.fenm2 = self.position.fenm2()
        self.origin_new = None

        self.dbManager = board.dbVisual
        self.read_resources()

        titulo = _("Director")
        icono = Iconos.Script()
        extparam = "tabvisualscript1"
        LCDialog.LCDialog.__init__(self, board, titulo, icono, extparam)

        self.ant_foto = None

        self.guion = TabVisual.Guion(board, self)

        # Guion
        li_acciones = [
            (_("Close"), Iconos.MainMenu(), self.finalize),
            (_("Save"), Iconos.Grabar(), self.grabar),
            (_("New"), Iconos.Nuevo(), self.gnuevo),
            (_("Insert"), Iconos.Insertar(), self.ginsertar),
            (
                _("Remove"),
                Iconos.Remove1(),
                self.gborrar,
                f"{_("Remove")} - {_("Backspace key")}",
            ),
            (
                _("Remove all"),
                Iconos.Borrar(),
                self.remove_all,
                f"{_("Remove all")} - {_("Delete key")}",
            ),
            None,
            (_("Up"), Iconos.Arriba(), self.garriba),
            (_("Down"), Iconos.Abajo(), self.gabajo),
            None,
            (_("Mark"), Iconos.Marcar(), self.gmarcar),
            None,
            (_("Config"), Iconos.Configurar(), self.gconfig),
            None,
        ]
        self.tb = Controles.TBrutina(self, li_acciones, icon_size=24)
        if self.guion is None:
            self.tb.set_action_visible(self.grabar, False)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NUMBER", _("N."), 20, align_center=True)
        o_columns.nueva("MARCADO", "", 20, align_center=True, is_checked=True)
        o_columns.nueva("TYPE", _("Type"), 50, align_center=True)
        o_columns.nueva(
            "NOMBRE",
            _("Name"),
            100,
            align_center=True,
            edicion=Delegados.LineaTextoUTF8(),
        )
        o_columns.nueva("INFO", _("Information"), 100, align_center=True)
        self.g_guion = Grid.Grid(
            self,
            o_columns,
            is_column_header_movable=False,
            is_editable=True,
            select_multiple=True,
        )

        self.register_grid(self.g_guion)

        self.chbSaveWhenFinished = Controles.CHB(
            self, _("Save when finished"), self.db_config.get("SAVEWHENFINISHED", False)
        )

        # Visuales
        self.selectBanda = WindowTab.SelectBanda(self)

        ly_g = Colocacion.V().control(self.g_guion).control(self.chbSaveWhenFinished)
        ly_sg = Colocacion.H().control(self.selectBanda).otro(ly_g)
        layout = Colocacion.V().control(self.tb).otro(ly_sg).margen(3)

        self.setLayout(layout)

        self.restore_video()

        self.recuperar()
        self.ant_foto = self.foto()

        self.update_bands()
        li = self.db_config["SELECTBANDA"]
        if li:
            self.selectBanda.recuperar(li)
        num_lb = self.db_config["SELECTBANDANUM"]
        if num_lb is not None:
            self.selectBanda.select_number(num_lb)

        self.ultDesde = "d4"
        self.ultHasta = "e5"

        self.g_guion.gotop()

    def add_text(self):
        self.guion.close_pizarra()
        tarea = TabVisual.GTTexto(self.guion)
        row = self.guion.new_task(tarea, -1)
        self.set_marked(row, True)
        self.guion.pizarra.show()
        self.guion.pizarra.mensaje.setFocus()

    def position_changed(self):
        self.position = self.board.last_position
        self.fenm2 = self.position.fenm2()
        self.origin_new = None
        self.recuperar()

    def seleccionar(self, lb):
        if lb is None:
            self.owner.set_change(True)
            self.board.enable_all()
        else:
            self.owner.set_change(False)
            self.board.disable_all()

    def funcion(self, number, is_ctrl=False):
        if number == 9:
            if is_ctrl:
                self.selectBanda.seleccionar(None)
            else:
                if self.guion.pizarra:
                    self.guion.close_pizarra()
                else:
                    self.add_text()
        elif number == 0 and is_ctrl:  # Ctrl+F1
            self.remove_last()
        elif number == 1 and is_ctrl:  # Ctrl+F2
            self.remove_all()
        else:
            self.selectBanda.select_number(number)

    def save(self):
        if self.guion is not None:
            li = self.guion.guarda()
        else:
            li = None
        self.board.dbvisual_save(self.fenm2, li)

    def grabar(self):
        self.save()
        QTMessages.temporary_message(self, _("Saved"), 1.0)

    def recuperar(self):
        self.guion.recupera()
        self.ant_foto = self.foto()
        self.refresh_guion()

    # def boardCambiadoTam(self):
    #     self.layout().setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
    #     self.show()
    #     QTUtils.refresh_gui()
    #     self.layout().setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinAndMaxSize)

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        if key == "NUMBER":
            return f"{row + 1}"
        if key == "MARCADO":
            return self.guion.marcado(row)
        elif key == "TYPE":
            return self.guion.txt_tipo(row)
        elif key == "NOMBRE":
            return self.guion.name(row)
        elif key == "INFO":
            return self.guion.info(row)
        return None

    def create_task_base(self, tp, xid, a1h8, row):
        tpid = tp, xid
        if tp == "P":
            tarea = TabVisual.GTPieceMove(self.guion)
            from_sq, to_sq = a1h8[:2], a1h8[2:]
            borra = self.board.get_name_piece_at(to_sq)
            tarea.remove_from_to(from_sq, to_sq, borra)
            self.board.enable_all()
        elif tp == "C":
            tarea = TabVisual.GTPieceCreate(self.guion)
            borra = self.board.get_name_piece_at(a1h8)
            tarea.from_sq(a1h8, borra)
            tarea.pieza(xid)
            self.board.enable_all()
        elif tp == "B":
            tarea = TabVisual.GTPieceRemove(self.guion)
            tarea.from_sq(a1h8)
            tarea.pieza(xid)
        else:
            xid = str(xid)
            if tp == TabVisual.TP_FLECHA:
                dic_arrow = self.db_arrows[xid]
                if dic_arrow is None:
                    return None, None
                reg_arrow = BoardTypes.Flecha()
                reg_arrow.restore_dic(dic_arrow)
                reg_arrow.tpid = tpid
                reg_arrow.a1h8 = a1h8
                sc = self.board.create_arrow(reg_arrow)
                tarea = TabVisual.GTArrow(self.guion)
            elif tp == TabVisual.TP_MARCO:
                dic_marco = self.db_marcos[xid]
                if dic_marco is None:
                    return None, None
                reg_marco = BoardTypes.Marco()
                reg_marco.restore_dic(dic_marco)
                reg_marco.tpid = tpid
                reg_marco.a1h8 = a1h8
                sc = self.board.create_marco(reg_marco)
                tarea = TabVisual.GTMarco(self.guion)
            elif tp == TabVisual.TP_CIRCLE:
                dic_circle = self.db_circles[xid]
                if dic_circle is None:
                    return None, None
                reg_circle = BoardTypes.Circle()
                reg_circle.restore_dic(dic_circle)
                reg_circle.tpid = tpid
                reg_circle.a1h8 = a1h8
                sc = self.board.create_circle(reg_circle)
                tarea = TabVisual.GTCircle(self.guion)
            elif tp == TabVisual.TP_SVG:
                dic_svg = self.db_svgs[xid]
                if dic_svg is None:
                    return None, None
                reg_svg = BoardTypes.SVG()
                reg_svg.restore_dic(dic_svg)
                reg_svg.tpid = tpid
                reg_svg.a1h8 = a1h8
                sc = self.board.create_svg(reg_svg, is_editing=True)
                tarea = TabVisual.GTSvg(self.guion)
            elif tp == TabVisual.TP_MARKER:
                dic_marker = self.db_markers[xid]
                if dic_marker is None:
                    return None, None
                reg_marker = BoardTypes.Marker()
                reg_marker.restore_dic(dic_marker)
                reg_marker.tpid = tpid
                reg_marker.a1h8 = a1h8
                sc = self.board.create_marker(reg_marker, is_editing=True)
                tarea = TabVisual.GTMarker(self.guion)
            else:
                return None, None
            sc.set_routine_if_pressed(None, tarea.id())
            tarea.item_sc(sc)

        tarea.marcado(True)
        tarea.registro((tp, xid, a1h8))
        if self.guion is None:
            row = 0
        else:
            row = self.guion.new_task(tarea, row)

        return tarea, row

    def create_task(self, tp, xid, a1h8, row):
        tarea, row = self.create_task_base(tp, xid, a1h8, row)
        if tarea is None:
            return None, None
        tarea.registro((tp, xid, a1h8))

        self.g_guion.goto(row, 0)

        self.set_marked(row, True)

        return tarea, row

    # def editaNombre(self, name):
    #     li_gen: List[Tuple[Any, Any]] = [(None, None)]
    #     config = FormLayout.Editbox(_("Name"), ancho=160)
    #     li_gen.append((config, name))
    #     ico = Iconos.Grabar()
    #
    #     resultado = FormLayout.fedit(li_gen, title=_("Name"), parent=self, icon=ico)
    #     if resultado:
    #         accion, li_resp = resultado
    #         name = li_resp[0]
    #         return name
    #     return None

    def remove_pizarra_active(self):
        for n in range(len(self.guion)):
            tarea = self.guion.tarea(n)
            if tarea and tarea.tp() == TabVisual.TP_TEXTO:
                if tarea.marcado():
                    self.borrar_lista([n])

    def gmarcar(self):
        if len(self.guion):
            menu = QTDialogs.LCMenu(self)
            f = Controles.FontType(puntos=8, peso=75)
            menu.set_font(f)
            menu.opcion(1, _("All"), Iconos.PuntoVerde())
            menu.opcion(2, _("None"), Iconos.PuntoNaranja())
            resp = menu.lanza()
            if resp:
                si_todos = resp == 1
                for n in range(len(self.guion)):
                    tarea = self.guion.tarea(n)
                    if tarea.tp() in (
                        TabVisual.TP_TEXTO,
                        TabVisual.TP_ACTION,
                        TabVisual.TP_CONFIGURATION,
                    ):
                        continue
                    si_marcado = tarea.marcado()
                    if si_todos:
                        if not si_marcado:
                            self.grid_setvalue(None, n, None, True)
                    else:
                        if si_marcado:
                            self.grid_setvalue(None, n, None, False)
                self.refresh_guion()

    def fromsq_tosq(self, titulo, from_sq, to_sq):
        li_gen = [(None, None)]

        config = FormLayout.Casillabox(_("From square"))
        li_gen.append((config, from_sq))

        config = FormLayout.Casillabox(_("To square"))
        li_gen.append((config, to_sq))

        resultado = FormLayout.fedit(li_gen, title=titulo, parent=self)
        if resultado:
            resp = resultado[1]
            self.ultDesde = from_sq = resp[0]
            self.ultHasta = to_sq = resp[1]
            return from_sq, to_sq
        else:
            return None, None

    def gconfig(self):
        menu = QTDialogs.LCMenu(self)
        menu.opcion("remall", _("Reset everything to factory defaults"), Iconos.Delete())
        menu.separador()
        menu.opcion(
            "remfen",
            _("Remove all graphics associated with positions"),
            Iconos.Borrar(),
        )
        resp = menu.lanza()
        if resp == "remall":
            if QTMessages.pregunta(
                self,
                _("Are you sure you want to reset graphics in Director to factory defaults?"),
            ):
                # self.close_resources()
                fich_recursos = Code.configuration.paths.file_resources()
                fmt_recursos = fich_recursos.replace(".dbl", "%d.dbl")
                pos = 0
                while Util.exist_file(fmt_recursos % pos):
                    pos += 1
                Util.file_copy(Code.configuration.paths.file_resources(), fmt_recursos % pos)
                self.close()
                self.board.dbVisual.reset()
                self.board.launch_director()

        if resp == "remfen":
            if QTMessages.pregunta(
                self,
                _("Are you sure you want to remove all graphics associated with positions?"),
            ):
                self.remove_all()
                self.close_resources()
                self.close()
                self.board.dbVisual.remove_fens()
                self.board.launch_director()

    def gmas(self, insert):
        ta = TabVisual.GTAction(None)
        li_actions = [(_F(txt), Iconos.PuntoRojo(), f"GTA_{action}") for action, txt in ta.dicTxt.items()]

        li_more = [
            (_("Text"), Iconos.Texto(), TabVisual.TP_TEXTO),
            (_("Actions"), Iconos.Run(), li_actions),
        ]
        resp = self.selectBanda.menu_for_extern(li_more)
        if resp:
            xid = resp
            row = self.g_guion.recno() if insert else -1
            if xid == TabVisual.TP_TEXTO:
                tarea = TabVisual.GTTexto(self.guion)
                row = self.guion.new_task(tarea, row)
                self.set_marked(row, True)
            elif resp.startswith("GTA_"):
                self.create_action(resp[4:], row)
            else:
                li = xid.split("_")
                tp = li[1]
                xid = li[2]
                from_sq, to_sq = self.fromsq_tosq(_("Director"), self.ultDesde, self.ultHasta)
                if from_sq:
                    self.create_task(tp, xid, from_sq + to_sq, row)
            if insert:
                self.g_guion.goto(row, 0)
            else:
                self.g_guion.gobottom()

    def create_action(self, action, row):
        tarea = TabVisual.GTAction(self.guion)
        tarea.action(action)
        self.guion.new_task(tarea, row)
        self.refresh_guion()

    def gnuevo(self):
        self.gmas(False)

    def ginsertar(self):
        self.gmas(True)

    def remove_last(self):
        row = len(self.guion) - 1
        if row >= 0:
            lista = [row]
            self.borrar_lista(lista)

    def remove_all(self):
        num = len(self.guion)
        if num:
            self.borrar_lista(list(range(num)))

    def borrar_lista(self, lista=None):
        li = self.g_guion.list_selected_recnos() if lista is None else lista
        if li:
            li.sort(reverse=True)
            for row in li:
                self.set_marked(row, False)
                sc = self.guion.item_of_task(row)
                if sc:
                    self.board.remove_movable(sc)
                else:
                    tarea = self.guion.tarea(row)
                    if tarea and tarea.tp() == TabVisual.TP_TEXTO:
                        self.guion.close_pizarra()
                self.guion.borra(row)
            row = len(li)
            if row >= len(self.guion):
                row = len(self.guion) - 1
            self.g_guion.goto(row, 0)
            self.refresh_guion()

    def gborrar(self):
        li = self.g_guion.list_selected_recnos()
        if li:
            self.borrar_lista(li)

    def garriba(self):
        row = self.g_guion.recno()
        if self.guion.arriba(row):
            self.g_guion.goto(row - 1, 0)
            self.refresh_guion()

    def gabajo(self):
        row = self.g_guion.recno()
        if self.guion.abajo(row):
            self.g_guion.goto(row + 1, 0)
            self.refresh_guion()

    def grid_doble_click(self, _grid, row, col):
        key = col.key
        if key == "INFO":
            tarea = self.guion.tarea(row)
            if tarea is None:
                return
            sc = self.guion.item_of_task(row)
            if sc:
                if tarea.tp() == TabVisual.TP_SVG:
                    return

                else:
                    a1h8 = tarea.a1h8()
                    from_sq, to_sq = self.fromsq_tosq(f"{tarea.txt_tipo()} {tarea.name()}", a1h8[:2], a1h8[2:])
                    if from_sq:
                        sc = tarea.item_sc()
                        sc.set_a1h8(from_sq + to_sq)
                        self.board.refresh()

            tarea.marked_owner()
            # mo = tarea.marked_owner()
            # if mo:
            #     self.ponMarcadoOwner(row, mo)
            self.refresh_guion()

    def keyPressEvent(self, event):
        self.owner.keyPressEvent(event)

    def foto(self):
        gn = self.guion.name
        gi = self.guion.info
        gt = self.guion.txt_tipo
        return [(gn(f), gi(f), gt(f)) for f in range(len(self.guion))]

    def refresh_guion(self):
        self.g_guion.refresh()
        nueva = self.foto()
        nv = len(nueva)
        if self.ant_foto is None or nv != len(self.ant_foto):
            self.ant_foto = nueva
        else:
            for n in range(nv):
                if self.ant_foto[n] != nueva[n]:
                    self.ant_foto = nueva
                    break

    def grid_num_datos(self, _grid):
        return len(self.guion) if self.guion else 0

    # def clonaItemTarea(self, row):
    #     tarea = self.guion.tarea(row)
    #     block_data = tarea.block_data()
    #     tp = tarea.tp()
    #     if tp == TabVisual.TP_FLECHA:
    #         sc = self.board.create_arrow(block_data)
    #     elif tp == TabVisual.TP_MARCO:
    #         sc = self.board.create_marco(block_data)
    #     elif tp == TabVisual.TP_CIRCLE:
    #         sc = self.board.create_circle(block_data)
    #     elif tp == TabVisual.TP_SVG:
    #         sc = self.board.create_svg(block_data)
    #     elif tp == TabVisual.TP_MARKER:
    #         sc = self.board.create_marker(block_data)
    #     else:
    #         return None
    #     return sc

    def set_marked(self, row, si_marcado):
        if self.guion:
            if row < len(self.guion.liGTareas):
                self.guion.change_mark_task(row, si_marcado)
                item_sc = self.guion.item_of_task(row)
                self.set_marked_item(row, self.board, item_sc, si_marcado)
            self.refresh_guion()

    def set_marked_item(self, row, board, item_sc, is_marked):
        if item_sc:
            item_sc.setVisible(is_marked)

        else:
            tarea = self.guion.tarea(row)
            if isinstance(tarea, TabVisual.GTPieceMove):
                from_sq, to_sq, borra = tarea.remove_from_to()
                if is_marked:
                    board.move_piece(from_sq, to_sq)
                    board.put_arrow_sc(from_sq, to_sq)
                else:
                    board.move_piece(to_sq, from_sq)
                    if borra:
                        board.create_piece(borra, to_sq)
                    if board.arrow_sc:
                        board.arrow_sc.hide()
                board.enable_all()

            elif isinstance(tarea, TabVisual.GTPieceCreate):
                from_sq, pz_borrada = tarea.from_sq()
                if is_marked:
                    board.change_piece(from_sq, tarea.pieza())
                else:
                    board.remove_piece(from_sq)
                    if pz_borrada:
                        board.create_piece(pz_borrada, from_sq)
                board.enable_all()

            elif isinstance(tarea, TabVisual.GTPieceRemove):
                if is_marked:
                    board.remove_piece(tarea.from_sq())
                else:
                    board.change_piece(tarea.from_sq(), tarea.pieza())
                board.enable_all()

            elif isinstance(tarea, TabVisual.GTTexto):
                self.guion.close_pizarra()
                if is_marked:
                    self.guion.write_pizarra(tarea)
                for recno in range(len(self.guion)):
                    tarea = self.guion.tarea(recno)
                    if tarea.tp() == TabVisual.TP_TEXTO and row != recno:
                        self.guion.change_mark_task(recno, False)

            elif isinstance(tarea, TabVisual.GTAction):
                if is_marked:
                    tarea.run()
                    self.guion.change_mark_task(row, False)

    def grid_setvalue(self, _grid, row, obj_column, valor):
        key = obj_column.key if obj_column else "MARCADO"
        if key == "MARCADO":
            self.set_marked(row, valor > 0)
        elif key == "NOMBRE":
            tarea = self.guion.tarea(row)
            tarea.name(valor.strip())

    def edit_band(self, cid):
        li = cid.split("_")
        tp = li[1]
        xid = li[2]
        if tp == TabVisual.TP_FLECHA:
            reg_arrow = BoardTypes.Flecha(dic=self.db_arrows[xid])
            w = WindowTabVArrows.WTVArrow(self, reg_arrow, True)
            if w.exec():
                self.db_arrows[xid] = w.reg_arrow.save_dic()
        elif tp == TabVisual.TP_MARCO:
            reg_marco = BoardTypes.Marco(dic=self.db_marcos[xid])
            w = WindowTabVMarcos.WTVMarco(self, reg_marco)
            if w.exec():
                self.db_marcos[xid] = w.reg_marco.save_dic()
        elif tp == TabVisual.TP_CIRCLE:
            reg_circle = BoardTypes.Circle(dic=self.db_circles[xid])
            w = WindowTabVCircles.WTVCircle(self, reg_circle)
            if w.exec():
                self.db_circles[xid] = w.reg_circle.save_dic()
        elif tp == TabVisual.TP_SVG:
            reg_svg = BoardTypes.SVG(dic=self.db_svgs[xid])
            w = WindowTabVSVGs.WTVSvg(self, reg_svg)
            if w.exec():
                self.db_svgs[xid] = w.regSVG.save_dic()
        elif tp == TabVisual.TP_MARKER:
            reg_marker = BoardTypes.Marker(dic=self.db_markers[xid])
            w = WindowTabVMarkers.WTVMarker(self, reg_marker)
            if w.exec():
                self.db_markers[xid] = w.regMarker.save_dic()

    def check_if_save(self):
        if self.chbSaveWhenFinished.valor():
            self.save()

    def closeEvent(self, event):
        self.close_resources()

    def finalize(self):
        self.close_resources()
        self.close()

    def cancelar(self):
        self.finalize()

    def portapapeles(self):
        self.board.save_as_img()
        txt = _("Clipboard")
        QTMessages.temporary_message(self, _X(_("Saved to %1"), txt), 0.8)

    # def grabarFichero(self):
    #     dir_salvados = self.configuration.save_folder()
    #     resp = SelectFiles.salvaFichero(self, _("File to save"), dir_salvados, "png", False)
    #     if resp:
    #         self.board.save_as_img(resp, "png")
    #         txt = resp
    #         QTMessages.temporary_message(self, _X(_("Saved to %1"), txt), 0.8)
    #         direc = os.path.dirname(resp)
    #         if direc != dir_salvados:
    #             self.configuration.set_save_folder(direc)

    def flechas(self):
        w = WindowTabVArrows.WTVArrows(self, self.db_arrows)
        w.exec()
        self.update_bands()
        QTUtils.refresh_gui()

    def list_arrows(self):
        dic = self.db_arrows.as_dictionary()
        li = []
        for k, dicFlecha in dic.items():
            arrow = BoardTypes.Flecha(dic=dicFlecha)
            arrow.id = k
            li.append(arrow)

        li.sort(key=lambda x: x.ordenVista)
        return li

    def marcos(self):
        w = WindowTabVMarcos.WTVMarcos(self, self.list_boxes(), self.db_marcos)
        w.exec()
        self.update_bands()
        QTUtils.refresh_gui()

    def circles(self):
        w = WindowTabVCircles.WTVCircles(self, self.list_circles(), self.db_circles)
        w.exec()
        self.update_bands()
        QTUtils.refresh_gui()

    def list_boxes(self):
        dic = self.db_marcos.as_dictionary()
        li = []
        for k, dicMarco in dic.items():
            box = BoardTypes.Marco(dic=dicMarco)
            box.id = k
            li.append(box)
        li.sort(key=lambda x: x.ordenVista)
        return li

    def list_circles(self):
        dic = self.db_circles.as_dictionary()
        li = []
        for k, dicCircle in dic.items():
            circle = BoardTypes.Circle(dic=dicCircle)
            circle.id = k
            li.append(circle)
        li.sort(key=lambda x: x.ordenVista)
        return li

    def svgs(self):
        w = WindowTabVSVGs.WTVSvgs(self, self.list_svgs(), self.db_svgs)
        w.exec()
        self.update_bands()
        QTUtils.refresh_gui()

    def list_svgs(self):
        dic = self.db_svgs.as_dictionary()
        li = []
        for k, dicSVG in dic.items():
            if not isinstance(dicSVG, dict):
                continue
            svg = BoardTypes.SVG(dic=dicSVG)
            svg.id = k
            li.append(svg)
        li.sort(key=lambda x: x.ordenVista)
        return li

    def markers(self):
        w = WindowTabVMarkers.WTVMarkers(self, self.list_markers(), self.db_markers)
        w.exec()
        self.update_bands()
        QTUtils.refresh_gui()

    def list_markers(self):
        dic = self.db_markers.as_dictionary()
        li = []
        for k, dic_marker in dic.items():
            marker = BoardTypes.Marker(dic=dic_marker)
            marker.id = k
            li.append(marker)
        li.sort(key=lambda x: x.ordenVista)
        return li

    def read_resources(self):
        self.db_config = self.dbManager.db_config
        self.db_arrows = self.dbManager.db_arrows
        self.db_marcos = self.dbManager.db_marcos
        self.db_circles = self.dbManager.db_circles
        self.db_svgs = self.dbManager.db_svgs
        self.db_markers = self.dbManager.db_markers

    def close_resources(self):
        if self.guion is not None:
            self.guion.close_pizarra()
            if not self.db_config.is_closed():
                self.db_config["SELECTBANDA"] = self.selectBanda.guardar()
                self.db_config["SELECTBANDANUM"] = self.selectBanda.num_selected()
                self.db_config["SAVEWHENFINISHED"] = self.chbSaveWhenFinished.valor()
            self.dbManager.close()

            self.check_if_save()
            self.save_video()
            self.guion.restore_board()
            self.guion = None

    def update_bands(self):
        self.selectBanda.init_update()

        tipo = _("Arrows")
        for arrow in self.list_arrows():
            pm = QtGui.QPixmap()
            pm.loadFromData(arrow.png, "PNG")
            xid = f"_F_{arrow.id}"
            name = arrow.name
            self.selectBanda.actualiza(xid, name, pm, tipo)

        tipo = _("Boxes")
        for box in self.list_boxes():
            pm = QtGui.QPixmap()
            pm.loadFromData(box.png, "PNG")
            xid = f"_M_{box.id}"
            name = box.name
            self.selectBanda.actualiza(xid, name, pm, tipo)

        tipo = _("Circles")
        for circle in self.list_circles():
            pm = QtGui.QPixmap()
            pm.loadFromData(circle.png, "PNG")
            xid = f"_D_{circle.id}"
            name = circle.name
            self.selectBanda.actualiza(xid, name, pm, tipo)

        tipo = _("Images")
        for svg in self.list_svgs():
            pm = QtGui.QPixmap()
            pm.loadFromData(svg.png, "PNG")
            xid = f"_S_{svg.id}"
            name = svg.name
            self.selectBanda.actualiza(xid, name, pm, tipo)

        tipo = _("Markers")
        for marker in self.list_markers():
            pm = QtGui.QPixmap()
            pm.loadFromData(marker.png, "PNG")
            xid = f"_X_{marker.id}"
            name = marker.name
            self.selectBanda.actualiza(xid, name, pm, tipo)

        self.selectBanda.end_update()

        dic_campos = {
            TabVisual.TP_FLECHA: (
                "name",
                "altocabeza",
                "tipo",
                "destino",
                "color",
                "colorinterior",
                "colorinterior2",
                "opacity",
                "redondeos",
                "forma",
                "ancho",
                "vuelo",
                "descuelgue",
            ),
            TabVisual.TP_MARCO: (
                "name",
                "color",
                "colorinterior",
                "colorinterior2",
                "grosor",
                "redEsquina",
                "tipo",
                "opacity",
            ),
            TabVisual.TP_CIRCLE: (
                "name",
                "color",
                "colorinterior",
                "colorinterior2",
                "grosor",
                "tipo",
                "opacity",
            ),
            TabVisual.TP_SVG: ("name", "opacity"),
            TabVisual.TP_MARKER: ("name", "opacity"),
        }
        dic_db = {
            TabVisual.TP_FLECHA: self.db_arrows,
            TabVisual.TP_MARCO: self.db_marcos,
            TabVisual.TP_CIRCLE: self.db_circles,
            TabVisual.TP_SVG: self.db_svgs,
            TabVisual.TP_MARKER: self.db_markers,
        }
        for k, sc in self.board.dic_movables.items():
            bd = sc.block_data
            try:
                tp, xid = bd.tpid
                bdn = dic_db[tp][xid]
                for campo in dic_campos[tp]:
                    setattr(bd, campo, getattr(bdn, campo))
                sc.update()
            except:
                pass
        self.refresh_guion()

    def move_piece(self, from_sq, to_sq):
        self.create_task("P", None, from_sq + to_sq, -1)
        self.board.move_piece(from_sq, to_sq)

    def board_press(self, event, origin, is_right, is_shift, is_alt, is_ctrl):
        if origin:
            if not is_right:
                lb_sel = self.selectBanda.seleccionada
            else:
                if is_ctrl:
                    if is_alt:
                        pos = 4
                    elif is_shift:
                        pos = 5
                    else:
                        pos = 3
                else:
                    if is_alt:
                        pos = 1
                    elif is_shift:
                        pos = 2
                    else:
                        pos = 0
                lb_sel = self.selectBanda.get_pos(pos)
            if lb_sel and lb_sel.id:
                nada, tp, nid = lb_sel.id.split("_")
                if nid.isdigit():
                    nid = int(nid)
                # if tp == TabVisual.TP_FLECHA:
                #     self.siGrabarInicio = True
                self.datos_new = self.create_task(tp, nid, origin + origin, -1)
                self.tp_new = tp
                if tp in (TabVisual.TP_FLECHA, TabVisual.TP_MARCO):
                    self.origin_new = origin
                    sc = self.datos_new[0].item_sc()
                    sc.mouse_press_ext(event)
                else:
                    self.origin_new = None

    def board_move(self, event):
        if self.origin_new:
            sc = self.datos_new[0].item_sc()
            sc.mouse_move_ext(event)

    def board_release(self, a1, is_right, is_shift, is_alt, is_ctrl):
        if self.origin_new:
            tarea, row = self.datos_new
            sc = tarea.item_sc()
            sc.mouse_release_ext()
            self.g_guion.goto(row, 0)
            if is_right:
                if a1 == self.origin_new and not is_ctrl:
                    if is_shift:
                        pos = 8
                    elif is_alt:
                        pos = 7
                    else:
                        pos = 6
                    self.borrar_lista()
                    lb = self.selectBanda.get_pos(pos)
                    if not lb.id:
                        return
                    nada, tp, nid = lb.id.split("_")
                    nid = int(nid)
                    self.datos_new = self.create_task(tp, nid, a1 + a1, -1)
                    self.tp_new = tp
                self.refresh_guion()

            else:
                if a1 is None or (a1 == self.origin_new and self.tp_new == TabVisual.TP_FLECHA):
                    self.borrar_lista()

                else:
                    self.refresh_guion()

            self.origin_new = None

    # def boardRemove(self, item_sc):
    #     tarea, n = self.guion.tasks_item(item_sc)
    #     if tarea:
    #         self.g_guion.goto(n, 0)
    #         self.borrar_lista()


class Director:
    def __init__(self, board):
        self.board = board
        self.ultTareaSelect = None
        self.director = False
        self.directorItemSC = None
        self.w = WPanelDirector(self, board)
        self.w.show()
        self.guion = self.w.guion

    def show(self):
        self.w.show()

    def changed_position_before(self):
        self.guion.close_pizarra()
        self.w.check_if_save()

    def changed_position_after(self):
        self.w.position_changed()
        self.guion.save_board()

    def mensajero_changed(self):
        self.w.check_if_save()
        self.w.finalize()

    def move_piece(self, from_sq, to_sq, promotion=""):
        self.w.create_task("P", None, from_sq + to_sq, -1)
        self.board.move_piece(from_sq, to_sq)
        return True

    def set_change(self, ok):
        self.director = ok
        self.ultTareaSelect = None
        self.directorItemSC = None

    def keyPressEvent(self, event):
        m = event.modifiers().value
        is_ctrl = (m & QtCore.Qt.KeyboardModifier.ControlModifier.value) > 0
        k = event.key()
        if k == QtCore.Qt.Key.Key_Backspace:
            self.w.remove_last()
            return True
        if k == QtCore.Qt.Key.Key_Delete:
            self.w.remove_all()
            return True
        if QtCore.Qt.Key.Key_F1 <= k <= QtCore.Qt.Key.Key_F10:
            f = k - QtCore.Qt.Key.Key_F1
            self.w.funcion(f, is_ctrl)
            return True
        else:
            return False

    def mousePressEvent(self, event):
        is_right = event.button() == QtCore.Qt.MouseButton.RightButton
        is_left = event.button() == QtCore.Qt.MouseButton.LeftButton

        if is_left:
            if self.board.event2a1h8(event) is None:
                return False
            if self.director:
                QtWidgets.QGraphicsView.mousePressEvent(self.board, event)

        p = event.pos()
        a1h8 = self.punto2a1h8(p)
        m = event.modifiers().value
        is_ctrl = (m & QtCore.Qt.KeyboardModifier.ControlModifier.value) > 0
        is_shift = (m & QtCore.Qt.KeyboardModifier.ShiftModifier.value) > 0
        is_alt = (m & QtCore.Qt.KeyboardModifier.AltModifier.value) > 0

        li_tareas = self.guion.tasks_in_position(p)

        if is_right and is_shift and is_alt:
            pz_borrar = self.board.get_name_piece_at(a1h8)
            menu = QTDialogs.LCMenu(self.board)
            dic_pieces = TrListas.dic_nom_pieces()
            ico_piece = self.board.pieces.icono

            if pz_borrar or len(li_tareas):
                mrem = menu.submenu(_("Remove"), Iconos.Delete())
                if pz_borrar:
                    label = dic_pieces[pz_borrar.upper()]
                    mrem.opcion(("rem_pz", None), label, ico_piece(pz_borrar))
                    mrem.separador()
                for pos_guion, tarea in li_tareas:
                    label = f"{tarea.txt_tipo()} - {tarea.name()} - {tarea.info()}"
                    mrem.opcion(("rem_gr", pos_guion), label, Iconos.Delete())
                    mrem.separador()
                menu.separador()

            for pz in "KQRBNPkqrbnp":
                if pz != pz_borrar:
                    if pz == "k":
                        menu.separador()
                    menu.opcion(("create", pz), dic_pieces[pz.upper()], ico_piece(pz))
            resp = menu.lanza()
            if resp is not None:
                orden, arg = resp
                if orden == "rem_gr":
                    self.w.g_guion.goto(arg, 0)
                    self.w.borrar_lista()
                elif orden == "rem_pz":
                    self.w.create_task("B", pz_borrar, a1h8, -1)

                elif orden == "create":
                    self.w.create_task("C", arg, a1h8, -1)
            return True

        if self.director:
            return self.mouse_press_event_drop(event)

        self.w.board_press(event, a1h8, is_right, is_shift, is_alt, is_ctrl)

        return True

    def mouse_press_event_drop(self, event):
        p = event.pos()
        li_tareas = self.guion.tasks_in_position(p)  # (pos_guion, tarea)...
        nli_tareas = len(li_tareas)
        if nli_tareas > 0:
            if nli_tareas > 1:  # Guerra
                posic = None
                for x in range(nli_tareas):
                    if self.ultTareaSelect == li_tareas[x][1]:
                        posic = x
                        break
                if posic is None:
                    posic = 0
                else:
                    posic += 1
                    if posic >= nli_tareas:
                        posic = 0
            else:
                posic = 0

            tarea_elegida = li_tareas[posic][1]

            if self.ultTareaSelect:
                self.ultTareaSelect.item_sc().activate(False)
            self.ultTareaSelect = tarea_elegida
            item_sc = self.ultTareaSelect.item_sc()
            item_sc.activate(True)
            item_sc.mouse_press_ext(event)
            self.directorItemSC = item_sc

            return True
        else:
            self.ultTareaSelect = None
            return False

    def punto2a1h8(self, punto):
        xc = 1 + int(float(punto.x() - self.board.margin_center) / self.board.width_square)
        yc = 1 + int(float(punto.y() - self.board.margin_center) / self.board.width_square)

        if self.board.is_white_bottom:
            yc = 9 - yc
        else:
            xc = 9 - xc

        if not ((1 <= xc <= 8) and (1 <= yc <= 8)):
            return None

        f = chr(48 + yc)
        c = chr(96 + xc)
        a1h8 = c + f
        return a1h8

    def mouseMoveEvent(self, event):
        if self.director:
            if self.directorItemSC:
                self.directorItemSC.mouseMoveEvent(event)
            return False
        self.w.board_move(event)
        return True

    def mouseReleaseEvent(self, event):
        if self.director:
            if self.directorItemSC:
                self.directorItemSC.mouse_release_ext()
                self.directorItemSC.activate(False)
                self.directorItemSC = None
                self.w.refresh_guion()
                return True
            else:
                return False

        a1h8 = self.punto2a1h8(event.pos())
        if a1h8:
            is_right = event.button() == QtCore.Qt.MouseButton.RightButton
            m = event.modifiers().value
            is_shift = (m & QtCore.Qt.KeyboardModifier.ShiftModifier.value) > 0
            is_alt = (m & QtCore.Qt.KeyboardModifier.AltModifier.value) > 0
            is_ctrl = (m & QtCore.Qt.KeyboardModifier.ControlModifier.value) > 0
            self.w.board_release(a1h8, is_right, is_shift, is_alt, is_ctrl)
        return True

    def finalize(self):
        if self.w:
            self.w.finalize()
            self.w = None
