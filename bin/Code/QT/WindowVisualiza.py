import os.path
import time
from typing import List

import FasterCode
from PySide6 import QtCore

import Code
from Code import Util
from Code.Base import Position
from Code.Board import Board
from Code.QT import Colocacion, Columnas, Controles, FormLayout, Grid, Iconos, LCDialog, QTDialogs, QTMessages
from Code.SQL import UtilSQL


class WControl(LCDialog.LCDialog):
    def __init__(self, procesador, path_bloque):

        LCDialog.LCDialog.__init__(
            self,
            procesador.main_window,
            _("The board at a glance"),
            Iconos.Gafas(),
            "visualizaBase",
        )

        self.procesador = procesador
        self.configuration = Code.configuration

        self.path_bloque = path_bloque

        file = Util.opj(self.configuration.paths.folder_results, os.path.basename(path_bloque) + "db")
        self.historico = UtilSQL.DictSQL(file)
        self.li_histo = self.calc_lista_historico()

        # Historico
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("SITE", _("Site"), 100, align_center=True)
        o_columns.nueva("DATE", _("Date"), 100, align_center=True)
        o_columns.nueva("LEVEL", _("Level"), 80, align_center=True)
        o_columns.nueva("TIME", _("Time used"), 80, align_center=True)
        o_columns.nueva("ERRORS", _("Errors"), 80, align_center=True)
        o_columns.nueva("INTERVAL", _("Interval"), 100, align_center=True)
        o_columns.nueva("POSITION", _("Position"), 80, align_center=True)
        o_columns.nueva("COLOR", _("Square color"), 80, align_center=True)
        o_columns.nueva("ISATTACKED", _("Is attacked?"), 80, align_center=True)
        o_columns.nueva("ISATTACKING", _("Is attacking?"), 80, align_center=True)
        self.ghistorico = Grid.Grid(self, o_columns, siSelecFilas=True, siSeleccionMultiple=True)
        self.ghistorico.setMinimumWidth(self.ghistorico.anchoColumnas() + 20)

        # Toolbar
        li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.terminar),
            None,
            (_("Play"), Iconos.Empezar(), self.play),
            None,
            (_("New"), Iconos.Nuevo(), self.new),
            None,
            (_("Remove"), Iconos.Borrar(), self.remove),
            None,
        )
        self.tb = QTDialogs.LCTB(self, li_acciones)

        # Colocamos
        ly = Colocacion.V().control(self.tb).control(self.ghistorico).margen(3)

        self.setLayout(ly)

        self.register_grid(self.ghistorico)
        self.restore_video()
        self.ghistorico.gotop()

    def grid_num_datos(self, _grid):
        return len(self.li_histo)

    def grid_dato(self, _grid, row, o_column):
        col = o_column.key
        key = self.li_histo[row]
        reg = self.historico[key]
        v = reg[col]
        if col == "DATE":
            v = Util.local_date(reg[col])
        elif col == "ERRORS":
            v = "%d" % v
        elif col == "TIME":
            if v > 60:
                m = v / 60
                s = v % 60
                v = "%d'%d\"" % (m, s)
            else:
                v = '%d"' % v
        elif col == "INTERVAL":
            v = '%d"' % v
            if reg["INTERVALPIECE"]:
                v = "x %s" % v
        elif col == "LEVEL":
            v = _("Finished") if v == 0 else str(v)
        elif col in ("POSITION", "COLOR", "ISATTACKED", "ISATTACKING"):
            v = _("Yes") if v else _("No")
        return v

    def calc_lista_historico(self):
        return self.historico.keys(si_ordenados=True, si_reverse=True)

    def terminar(self):
        self.save_video()
        self.historico.close()
        self.reject()

    def play(self):
        if not self.li_histo:
            return self.new()

        recno = self.ghistorico.recno()
        if recno >= 0:
            key = self.li_histo[recno]
            reg = self.historico[key]
            if reg["LEVEL"] > 0:
                return self.work(recno)
        return None

    def new(self):
        recno = self.ghistorico.recno()
        if recno >= 0:
            key = self.li_histo[recno]
            reg = self.historico[key]
            site_pre = reg["SITE"]
            intervalo_pre = reg["INTERVAL"]
            intervalo_por_pieza_pre = reg["INTERVALPIECE"]
            esatacada_pre = reg["ISATTACKED"]
            esatacante_pre = reg["ISATTACKING"]
            posicion_pre = reg["POSITION"]
            color_pre = reg["COLOR"]
        else:
            recno = 0
            site_pre = None
            intervalo_pre = 3
            intervalo_por_pieza_pre = True
            esatacada_pre = False
            esatacante_pre = False
            posicion_pre = False
            color_pre = False

        # Datos
        li_gen: list[tuple] = [(None, None)]

        # # Site
        f = open(self.path_bloque)
        li_data: List = [x.split("|") for x in f.read().split("\n")]
        f.close()
        li_sites = []
        site_pre_num = -1
        for n, uno in enumerate(li_data):
            site = uno[0]
            if site:
                if site_pre and site == site_pre:
                    site_pre_num = n
                li_sites.append((site, n))
        li_sites = sorted(li_sites, key=lambda st: st[0])
        config = FormLayout.Combobox(_("Site"), li_sites)
        if site_pre_num == -1:
            site_pre_num = li_sites[0][0]
        li_gen.append((config, site_pre_num))

        li_gen.append((None, None))

        # # Intervals
        li_gen.append((None, _("Seconds of every glance") + ":"))
        li_gen.append((FormLayout.Spinbox(_("Second(s)"), 1, 100, 50), intervalo_pre))

        li_types = ((_("By piece"), True), (_("Time fixed"), False))
        config = FormLayout.Combobox(_("Type"), li_types)
        li_gen.append((config, intervalo_por_pieza_pre))

        li_gen.append((None, None))

        li_gen.append((None, _("Ask for") + ":"))
        li_gen.append((_("Position") + ":", posicion_pre))
        li_gen.append((_("Square color") + ":", color_pre))
        li_gen.append((_("Is attacked?") + ":", esatacada_pre))
        li_gen.append((_("Is attacking?") + ":", esatacante_pre))

        resultado = FormLayout.fedit(
            li_gen,
            title=_("Configuration"),
            parent=self,
            icon=Iconos.Gafas(),
            anchoMinimo=360,
        )
        if resultado:
            accion, li_gen = resultado

            (
                site_num,
                intervalo,
                intervalo_por_pieza,
                position,
                color,
                esatacada,
                esatacante,
            ) = li_gen

            dicdatos = {}
            f = dicdatos["DATE"] = Util.today()
            dicdatos["FENS"] = li_data[site_num][1:]
            dicdatos["SITE"] = li_data[site_num][0]
            dicdatos["INTERVAL"] = intervalo
            dicdatos["INTERVALPIECE"] = intervalo_por_pieza
            dicdatos["ISATTACKED"] = esatacada
            dicdatos["ISATTACKING"] = esatacante
            dicdatos["POSITION"] = position
            dicdatos["COLOR"] = color
            dicdatos["ERRORS"] = 0
            dicdatos["TIME"] = 0
            dicdatos["LEVEL"] = 1

            key = Util.dtosext(f)
            self.historico[key] = dicdatos
            self.li_histo.insert(0, key)
            self.ghistorico.refresh()
            self.ghistorico.gotop()

            self.work(recno)

    def work(self, recno):
        key = self.li_histo[recno]
        dicdatos = self.historico[key]

        w = WPlay(self, dicdatos)
        w.exec()

        self.historico[key] = dicdatos
        self.ghistorico.refresh()

    def grid_doble_click(self, _grid, row, _column):
        key = self.li_histo[row]
        dicdatos = self.historico[key]
        if dicdatos["LEVEL"]:
            self.work(row)

    def remove(self):
        li = self.ghistorico.recnosSeleccionados()
        if len(li) > 0:
            if QTMessages.pregunta(self, _("Do you want to delete all selected records?")):
                with QTMessages.one_moment_please(self):
                    for row in li:
                        key = self.li_histo[row]
                        del self.historico[key]
                    self.historico.pack()
                    self.li_histo = self.calc_lista_historico()
                self.ghistorico.refresh()


class WPlay(LCDialog.LCDialog):
    ini_time: float | None
    ini_time_board: float | None
    intervalo_max: int | None
    position: Position.Position
    rotulo_board: str

    def __init__(self, owner, dicdatos):

        self.dicdatos = dicdatos

        site = dicdatos["SITE"]
        self.level = dicdatos["LEVEL"]
        self.intervalo = dicdatos["INTERVAL"]
        self.intervalo_por_pieza = dicdatos["INTERVALPIECE"]
        self.esatacada = dicdatos["ISATTACKED"]
        self.esatacante = dicdatos["ISATTACKING"]
        self.position = dicdatos["POSITION"]
        self.color = dicdatos["COLOR"]
        self.errors = dicdatos["ERRORS"]
        self.time = dicdatos["TIME"]
        self.liFENs = dicdatos["FENS"]

        mas = "x" if self.intervalo_por_pieza else ""
        titulo = '%s (%s%d")' % (site, mas, self.intervalo)

        super(WPlay, self).__init__(owner, titulo, Iconos.Gafas(), "visualplay")

        self.procesador = owner.procesador
        self.configuration = Code.configuration

        # Tiempo en board
        intervalo_max = self.intervalo
        if self.intervalo_por_pieza:
            intervalo_max *= 32

        # Board
        config_board = self.configuration.config_board("VISUALPLAY", 48)
        self.board = Board.Board(self, config_board)
        self.board.crea()

        ly_t = Colocacion.V().control(self.board)

        self.gbBoard = Controles.GB(self, "", ly_t)

        # entradas
        ly = Colocacion.G()

        self.posPosicion = None
        self.posColor = None
        self.posIsAttacked = None
        self.posIsAttacking = None

        lista = [_("Piece")]
        if self.position:
            lista.append(_("Position"))
        if self.color:
            lista.append(_("Square color"))
        if self.esatacada:
            lista.append(_("Is attacked?"))
        if self.esatacante:
            lista.append(_("Is attacking?"))
        self.liLB2 = []
        for col, eti in enumerate(lista):
            ly.control(Controles.LB(self, eti), 0, col + 1)
            lb2 = Controles.LB(self, eti)
            ly.control(lb2, 0, col + len(lista) + 2)
            self.liLB2.append(lb2)
        elementos = len(lista) + 1

        li_combo_pieces = []
        for c in "PNBRQKpnbrqk":
            li_combo_pieces.append(("", c, self.board.piezas.icono(c)))

        self.pmBien = Iconos.pmAceptarPeque()
        self.pmMal = Iconos.pmCancelarPeque()
        self.pmNada = Iconos.pmPuntoAmarillo()

        self.liBloques = []
        for x in range(32):
            row = x % 16 + 1
            col_pos = elementos if x > 15 else 0

            un_bloque = []
            self.liBloques.append(un_bloque)

            # # Solucion
            lb = Controles.LB(self, "").put_image(self.pmNada)
            ly.control(lb, row, col_pos)
            un_bloque.append(lb)

            # # Piezas
            col_pos += 1
            cb = Controles.CB(self, li_combo_pieces, "P")
            # cb.setStyleSheet("* { min-height:32px }")
            cb.setIconSize(QtCore.QSize(20, 20))

            ly.control(cb, row, col_pos)
            un_bloque.append(cb)

            if self.position:
                ec = Controles.ED(self, "").caracteres(2).controlrx("(|[a-h][1-8])").relative_width(24).align_center()
                col_pos += 1
                ly.controlc(ec, row, col_pos)
                un_bloque.append(ec)

            if self.color:
                cl = QTDialogs.TwoImages(Iconos.pmBlancas(), Iconos.pmNegras())
                col_pos += 1
                ly.controlc(cl, row, col_pos)
                un_bloque.append(cl)

            if self.esatacada:
                isat = QTDialogs.TwoImages(Iconos.pmAtacada().scaledToWidth(24), Iconos.pmPuntoNegro())
                col_pos += 1
                ly.controlc(isat, row, col_pos)
                un_bloque.append(isat)

            if self.esatacante:
                at = QTDialogs.TwoImages(Iconos.pmAtacante().scaledToWidth(24), Iconos.pmPuntoNegro())
                col_pos += 1
                ly.controlc(at, row, col_pos)
                un_bloque.append(at)

        ly1 = Colocacion.H().otro(ly).relleno()
        ly2 = Colocacion.V().otro(ly1).relleno()
        self.gbSolucion = Controles.GB(self, "", ly2)

        f = Controles.FontType("", 11, 80, False, False, False, None)

        bt = Controles.PB(self, _("Close"), self.terminar, plano=False).ponIcono(Iconos.MainMenu()).set_font(f)
        self.btBoard = (
            Controles.PB(self, _("Go to board"), self.activa_board, plano=False).ponIcono(Iconos.Board()).set_font(f)
        )
        self.btComprueba = (
            Controles.PB(self, _("Verify"), self.comprueba_solucion, plano=False)
            .ponIcono(Iconos.Check())
            .set_font(f)
        )
        self.btGotoNextLevel = (
            Controles.PB(self, _("Go to next level"), self.goto_next_level, plano=False)
            .ponIcono(Iconos.GoToNext())
            .set_font(f)
        )
        ly0 = (
            Colocacion.H()
            .control(bt)
            .relleno()
            .control(self.btBoard)
            .control(self.btComprueba)
            .control(self.btGotoNextLevel)
        )

        ly_base = Colocacion.H().control(self.gbBoard).control(self.gbSolucion)

        layout = Colocacion.V().otro(ly0).otro(ly_base)

        self.setLayout(layout)

        self.restore_video()

        self.goto_next_level()

    def check_time(self):
        if self.ini_time:
            t = int(time.time() - self.ini_time)
            self.ini_time = None
            self.dicdatos["TIME"] += t

    def terminar(self):
        self.check_time()
        self.accept()

    def closeEvent(self, event):
        self.check_time()

    def goto_next_level(self):
        label = _("Level %d") % self.level
        self.gbSolucion.setTitle(label)

        fen = self.liFENs[self.level - 1]

        position = Position.Position()
        position.read_fen(fen)
        position.legal()
        self.board.set_side_bottom(position.is_white)
        self.board.set_position(position)

        mens = ""
        if position.castles:
            if ("K" if position.is_white else "k") in position.castles:
                mens = "O-O"
            if ("Q" if position.is_white else "q") in position.castles:
                if mens:
                    mens += " + "
                mens += "O-O-O"
            if mens:
                mens = _("Castling moves possible") + ": " + mens
        if position.en_passant != "-":
            mens += " " + _("En passant") + ": " + position.en_passant
        self.rotulo_board = _("White") if position.is_white else _("Black")
        if mens:
            self.rotulo_board += " " + mens

        self.position = position

        self.intervalo_max = self.intervalo
        if self.intervalo_por_pieza:
            self.intervalo_max *= self.level + 2
        self.set_time(self.intervalo_max)

        for x in range(32):
            bloque = self.liBloques[x]
            si_visible = x < self.level + 2
            for elem in bloque:
                elem.setVisible(si_visible)
            if si_visible:
                bloque[0].put_image(self.pmNada)
                pz = "K" if x == 0 else ("k" if x == 1 else "P")
                bloque[1].set_value(pz)
                pos = 1
                if self.position:
                    pos += 1
                    bloque[pos].set_text("")
                if self.color:
                    pos += 1
                    bloque[pos].valor(True)
                if self.esatacada:
                    pos += 1
                    bloque[pos].valor(False)
                if self.esatacante:
                    pos += 1
                    bloque[pos].valor(False)

        for lb in self.liLB2:
            lb.setVisible(self.level >= 16)

        self.activa_board()
        QtCore.QTimer.singleShot(1000, self.comprueba_tiempo)
        self.ini_time = time.time()

    def comprueba_tiempo(self):
        t = round(time.time() - self.ini_time_board, 0)
        r = self.intervalo_max - int(t)

        if r <= 0:
            self.activa_solucion()
        else:
            self.set_time(r)
            QtCore.QTimer.singleShot(1000, self.comprueba_tiempo)

    def activa_board(self):
        self.ini_time_board = time.time()
        self.gbSolucion.hide()
        self.btBoard.hide()
        self.btComprueba.hide()
        self.btGotoNextLevel.hide()
        self.comprueba_tiempo()
        self.gbBoard.show()
        self.gbBoard.adjustSize()
        self.adjustSize()

    def activa_solucion(self):
        self.gbBoard.hide()
        self.btBoard.show()
        self.btComprueba.show()
        self.btGotoNextLevel.hide()
        self.gbSolucion.show()
        self.adjustSize()

    def comprueba_solucion(self):
        li_solucion = self.calcula_solucion()
        n_errores = 0
        for x in range(self.level + 2):
            bloque = self.liBloques[x]

            pieza = bloque[1].valor()
            position = None
            pos = 1
            color = None
            atacada = None
            atacante = None
            if self.position:
                pos += 1
                position = bloque[pos].texto()
            if self.color:
                pos += 1
                color = bloque[pos].valor()
            if self.esatacada:
                pos += 1
                atacada = bloque[pos].valor()
            if self.esatacante:
                pos += 1
                atacante = bloque[pos].valor()

            correcta = False
            for rsol in li_solucion:
                if rsol.comprobada:
                    continue
                if rsol.pieza != pieza:
                    continue
                if self.position:
                    if rsol.position != position:
                        continue
                if self.color:
                    if rsol.color != color:
                        continue
                if self.esatacada:
                    if rsol.atacada != atacada:
                        continue
                if self.esatacante:
                    if rsol.atacante != atacante:
                        continue
                correcta = True
                rsol.comprobada = True
                break

            bloque[0].put_image(self.pmBien if correcta else self.pmMal)
            if not correcta:
                n_errores += 1
        if n_errores == 0:
            self.check_time()
            self.gbSolucion.show()
            self.set_time(0)
            self.gbBoard.show()
            self.btComprueba.hide()
            self.btBoard.hide()
            self.level += 1
            if self.level > 32:
                self.level = 0
            else:
                self.btGotoNextLevel.show()
            self.dicdatos["LEVEL"] = self.level
        else:
            self.dicdatos["ERRORS"] += n_errores

    def set_time(self, num):
        titulo = self.rotulo_board
        if num:
            titulo += "[ %s ]" % num
        self.gbBoard.setTitle(titulo)

    def calcula_solucion(self):
        fen_mb = self.position.fen()
        fen_ob = fen_mb.replace(" w ", " b ") if "w" in fen_mb else fen_mb.replace(" b ", " w ")
        st_attac_king = set()
        st_attacked = set()
        for fen in (fen_mb, fen_ob):
            FasterCode.set_fen(fen)
            li_mv = FasterCode.get_exmoves()
            for mv in li_mv:
                if mv.capture():
                    st_attac_king.add(mv.xfrom())
                    st_attacked.add(mv.xto())

        li_solucion = []
        for position, pieza in self.position.squares.items():
            if pieza:
                reg = Util.Record()
                reg.pieza = pieza
                reg.position = position

                lt = position[0]
                nm = int(position[1])
                iswhite = nm % 2 == 0
                if lt in "bdfh":
                    iswhite = not iswhite
                reg.color = iswhite

                reg.atacante = position in st_attac_king
                reg.atacada = position in st_attacked
                reg.comprobada = False
                li_solucion.append(reg)
        return li_solucion


def window_visualiza(procesador):
    w = WControl(procesador, Code.path_resource("IntFiles", "Visual/R50-01.vis"))
    w.exec()
