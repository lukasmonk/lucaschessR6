import copy
from pathlib import Path
from typing import Optional, Dict, List, Any

from PySide6 import QtCore, QtWidgets

import Code.Procesador
from Code.Z import Util, Variations
from Code.Base import Game, Move
from Code.Board import Board
from Code.Openings import OpeningsStd
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


class WOpenings(LCDialog.LCDialog):
    def __init__(self, owner, opening_block: Optional[OpeningsStd.Opening]):
        icono = Iconos.Opening()
        titulo = _("Select an opening")
        extparam = "selectOpening"
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, extparam)

        # Variables--------------------------------------------------------------------------
        self.ap_std = OpeningsStd.ap
        self.game = Game.Game()
        self.opening_block: Optional[OpeningsStd.Opening] = opening_block
        self.liActivas: List[OpeningsStd.Opening] = []
        self.configuration = Code.configuration
        self.posCurrent: int = -1
        self.is_moving_time: bool = False
        self.dicPGNSP: Dict[str, str] = {}

        # Board
        config_board = self.configuration.config_board("APERTURAS", 32)
        self.board = Board.Board(self, config_board)
        self.board.draw_window()
        self.board.set_dispatcher(self.player_has_moved_dispatcher)

        # Current pgn
        self.lbPGN = Controles.LB(self, "").set_wrap().set_font_type(puntos=10, peso=75)
        ly = Colocacion.H().control(self.lbPGN)
        gb = Controles.GB(self, _("Selected opening"), ly).set_font_type(puntos=11, peso=75).align_center()
        self.configuration.set_property(gb, "selop")

        # Movimiento
        self.is_moving_time = False

        ly_bm, tb_bm = QTDialogs.ly_mini_buttons(self, "", siLibre=False, icon_size=24)
        self.tbBM = tb_bm

        # Tool bar
        tb = QTDialogs.LCTB(self, icon_size=24)
        tb.new(_("Select"), Iconos.Aceptar(), self.aceptar)
        tb.new(_("Cancel"), Iconos.Cancelar(), self.cancelar)
        tb.new(_("Reinit"), Iconos.Reiniciar(), self.reset_partida)
        tb.new(_("Takeback"), Iconos.Atras(), self.atras)
        tb.new(_("Remove"), Iconos.Borrar(), self.borrar)
        tb.new(_("Read PGN file"), Iconos.PGN(), self.read_pgn)

        # Lista Openings
        o_columns = Columnas.ListaColumnas()
        dic_tipos = {
            "b": Iconos.pmSun(),
            "n": Iconos.pmPuntoAzul(),
            "l": Iconos.pmNaranja(),
        }
        o_columns.nueva("TYPE", "", 24, edicion=Delegados.PmIconosBMT(dict_icons=dic_tipos))
        o_columns.nueva("OPENING", _("Possible continuation"), 480)

        row_high = int(3.6 * self.configuration.x_pgn_fontpoints)

        self.grid = Grid.Grid(self, o_columns, complete_row_select=True, heigh_row=row_high)
        self.grid.setFont(Controles.FontType(puntos=self.configuration.x_pgn_fontpoints))
        self.register_grid(self.grid)

        # # Derecha
        ly_d = Colocacion.V().control(tb).control(gb).control(self.grid)
        gb_derecha = Controles.GB(self, "", ly_d)

        # # Izquierda
        ly_i = Colocacion.V().control(self.board).otro(ly_bm).relleno()
        gb_izquierda = Controles.GB(self, "", ly_i)

        splitter = QtWidgets.QSplitter(self)
        splitter.addWidget(gb_izquierda)
        splitter.addWidget(gb_derecha)
        self.register_splitter(splitter, "splitter")

        # Completo
        ly = Colocacion.H().control(splitter).margen(3)
        self.setLayout(ly)

        self.pon_activas()
        self.reset_partida()
        self.actualiza_posicion()

        dic = {"_SIZE_": "916,444", "SP_splitter": [356, 548]}
        self.restore_video(default_dic=dic)

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        self.board.disable_all()

        movimiento = from_sq + to_sq

        position = self.game.move(self.posCurrent).position if self.posCurrent >= 0 else self.game.last_position

        # Peon coronando
        if not promotion and position.pawn_can_promote(from_sq, to_sq):
            promotion = self.board.pawn_promoting(position.is_white)
        if promotion:
            movimiento += promotion

        ok, mens, move = Move.get_game_move(self.game, position, from_sq, to_sq, promotion)
        if ok:
            self.new_move(move)
        else:
            self.actualiza_posicion()

    def grid_num_datos(self, _grid):
        return len(self.liActivas)

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        ap = self.liActivas[row]
        if key == "TYPE":
            return "b" if ap.is_basic else "n"
        else:
            return f"{ap.tr_name}\n{ap.tr_pgn()}"

    def grid_doble_click(self, _grid, row, _obj_column):
        if -1 < row < len(self.liActivas):
            ap = self.liActivas[row]
            self.game.set_position()
            self.game.read_pv(ap.a1h8)
            self.pon_activas()

    def new_move(self, move):
        self.posCurrent += 1
        if self.posCurrent < len(self.game):
            self.game.li_moves = self.game.li_moves[: self.posCurrent]
        self.game.add_move(move)
        self.pon_activas()

    def pon_activas(self):
        self.liActivas = self.ap_std.list_possible_openings(self.game)

        self.board.set_position(self.game.last_position)

        self.game.assign_opening()
        txt = self.game.pgn_translated()
        if not txt:
            txt = _("None")
        if self.game.opening:
            txt = f'{txt}<br><span style="color:gray;">{self.game.opening.tr_name}</span>'

        self.lbPGN.set_text(txt)
        self.posCurrent = len(self.game) - 1

        self.actualiza_posicion()
        self.grid.refresh()
        self.grid.gotop()

        # w = self.width()
        # self.adjustSize()
        # if self.width() != w:
        #     self.resize(w, self.height())

    def actualiza_posicion(self):
        if self.posCurrent > -1:
            move = self.game.move(self.posCurrent)
            position = move.position
        else:
            position = self.game.first_position
            move = None

        self.board.set_position(position)
        self.board.activate_side(position.is_white)
        if move:
            self.board.put_arrow_sc(move.from_sq, move.to_sq)

    def reset_partida(self):
        self.game.set_position()
        if self.opening_block:
            self.game.read_pv(self.opening_block.a1h8)
        self.pon_activas()
        self.mueve(is_end=True)

    def finalize(self):
        self.is_moving_time = False
        self.save_video()

    def closeEvent(self, event):
        self.finalize()

    def aceptar(self):
        self.finalize()
        self.accept()

    def cancelar(self):
        self.finalize()
        self.reject()

    def atras(self):
        self.game.remove_only_last_movement()
        self.pon_activas()

    def borrar(self):
        self.game.set_position()
        self.pon_activas()

    def process_toolbar(self):
        accion = self.sender().key
        if accion == "move_forward":
            self.mueve(n_saltar=1)
        elif accion == "move_back":
            self.mueve(n_saltar=-1)
        elif accion == "move_to_beginning":
            self.mueve(si_inicio=True)
        elif accion == "move_to_end":
            self.mueve(is_end=True)
        elif accion == "move_timed":
            self.move_timed()

    def mueve(self, si_inicio=False, n_saltar=0, is_end=False):
        num_moves = len(self.game)
        if n_saltar:
            pos = self.posCurrent + n_saltar
            if 0 <= pos < num_moves:
                self.posCurrent = pos
            else:
                return
        elif si_inicio:
            self.posCurrent = -1
        elif is_end:
            self.posCurrent = num_moves - 1
        else:
            return
        self.actualiza_posicion()

    def move_timed(self):
        if self.is_moving_time:
            self.is_moving_time = False

        else:
            self.is_moving_time = True
            self.mueve(si_inicio=True)
            QtCore.QTimer.singleShot(1000, self.next_time)

    def next_time(self):
        if self.is_moving_time:
            if self.posCurrent < len(self.game) - 1:
                self.mueve(n_saltar=1)
                QtCore.QTimer.singleShot(Code.configuration.x_interval_replay, self.next_time)
            else:
                self.is_moving_time = False

    def resultado(self):
        if len(self.game) == 0:
            return None
        ap = self.game.opening
        if ap is None:
            ap = OpeningsStd.Opening(_("Unknown"))

        ap.a1h8 = self.game.pv()
        ap.pgn = self.game.pgn_translated()
        return ap

    def read_pgn(self):
        game = Code.procesador.select_1_pgn(self)
        if game and len(game) > 1 and game.is_fen_initial():
            self.game = game
            if not self.opening_block:
                self.opening_block = OpeningsStd.Opening(_("Unknown"))
            self.opening_block.a1h8 = game.pv()
            self.pon_activas()
            self.mueve(is_end=True)


class OpeningsCustom(LCDialog.LCDialog):
    def __init__(self, procesador, owner=None):
        self.procesador = procesador
        self.ficheroDatos: Path = Code.configuration.paths.file_pers_openings()
        self.lista: List[Dict[str, Any]] = self.leer()

        if owner is None:
            owner = procesador.main_window
        icono = Iconos.Opening()
        titulo = _("Custom openings")
        extparam = "customopen"
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, extparam)

        # Toolbar
        tb = QTDialogs.LCTB(self)
        tb.new(_("Close"), Iconos.MainMenu(), self.finalize)
        tb.new(_("New"), Iconos.TutorialesCrear(), self.nuevo)
        tb.new(_("Modify"), Iconos.Modificar(), self.modificar)
        tb.new(_("Remove"), Iconos.Borrar(), self.borrar)
        tb.new(_("Copy"), Iconos.Copiar(), self.copiar)
        tb.new(_("Up"), Iconos.Arriba(), self.arriba)
        tb.new(_("Down"), Iconos.Abajo(), self.abajo)

        # Lista
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NOMBRE", _("Name"), 240)
        o_columns.nueva("ECO", "ECO", 70, align_center=True)
        o_columns.nueva("PGN", "PGN", 280)
        # o_columns.nueva("ESTANDAR", _("Main"), 120, align_center=True)

        self.grid = Grid.Grid(self, o_columns, complete_row_select=True)
        n = self.grid.width_columns_displayables()
        self.grid.setMinimumWidth(n + 20)
        self.register_grid(self.grid)
        self.grid.gotop()

        # Layout
        layout = Colocacion.V().control(tb).control(self.grid).margen(8)
        self.setLayout(layout)

        self.restore_video(with_tam=True)

        self.dicPGNSP = {}

    def finalize(self):
        OpeningsStd.ap.reset()
        self.save_video()
        self.reject()
        return

    def grid_num_datos(self, _grid):
        return len(self.lista)

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        reg = self.lista[row]
        if key == "PGN":
            pgn = reg["PGN"]
            if pgn not in self.dicPGNSP:
                p = Game.Game()
                p.read_pv(reg["A1H8"])
                self.dicPGNSP[pgn] = p.pgn_translated()
            return self.dicPGNSP[pgn]
        return reg[key]

    def grid_doble_click(self, _grid, fil, _obj_column):
        self.edit(fil)

    def grid_doubleclick_header(self, _grid, obj_column):
        key = obj_column.key

        li = sorted(self.lista, key=lambda x: x[key].upper())

        self.lista = li

        self.grid.refresh()
        self.grid.gotop()

        self.grabar()

    def edit(self, row):
        is_basic = True
        if row is None:
            name = ""
            eco = ""
            pgn = ""

            titulo = _("New opening")

        else:
            reg = self.lista[row]

            name = reg["NOMBRE"]
            eco = reg["ECO"]
            pgn = reg["PGN"]
            # is_basic = reg["ESTANDAR"]

            titulo = name

        # Datos
        li_gen: list = [(None, None), (f"{_('Name')}:", name)]
        config = FormLayout.Editbox("ECO", ancho=30, rx="[A-Z, a-z][0-9][0-9]")
        li_gen.append((config, eco))

        # Editamos
        resultado = FormLayout.fedit(li_gen, title=titulo, parent=self, minimum_width=460, icon=Iconos.Opening())
        if resultado is None:
            return

        accion, li_resp = resultado
        name = li_resp[0].strip()
        if not name:
            return
        eco = li_resp[1].upper()

        self.procesador.procesador = self.procesador  # ya que edit_variation espera un manager

        if pgn:
            ok, game = Game.pgn_game(pgn)
            if not ok:
                game = Game.Game()
        else:
            game = Game.Game()

        resp = Variations.edit_variation(self.procesador, game, titulo=name, is_white_bottom=True)

        if resp:
            game = resp

            reg = {"NOMBRE": name, "ECO": eco, "PGN": game.pgn_base_raw(), "A1H8": game.pv(), "ESTANDAR": is_basic}

            if row is None:
                self.lista.append(reg)
                self.grid.refresh()
                self.grabar()
            else:
                self.lista[row] = reg
            self.grid.refresh()
            self.grabar()

    def nuevo(self):
        self.edit(None)

    def modificar(self):
        recno = self.grid.recno()
        if recno >= 0:
            self.edit(recno)

    def borrar(self):
        row = self.grid.recno()
        if row >= 0:
            if QTMessages.pregunta(
                self,
                _X(
                    _("Do you want to delete the opening %1?"),
                    self.lista[row]["NOMBRE"],
                ),
            ):
                del self.lista[row]
                self.grid.refresh()
                self.grabar()

    def copiar(self):
        row = self.grid.recno()
        if row >= 0:
            reg = self.lista[row]
            nreg = copy.deepcopy(reg)
            self.lista.append(nreg)
            self.grid.refresh()
            self.grabar()

    def leer(self):
        lista = Util.restore_pickle(self.ficheroDatos)
        if lista is None:
            lista = []

        return lista

    def grabar(self):
        Util.save_pickle(self.ficheroDatos, self.lista)

    def arriba(self):
        row = self.grid.recno()
        if row > 0:
            self.lista[row - 1], self.lista[row] = self.lista[row], self.lista[row - 1]
            self.grid.goto(row - 1, 0)
            self.grid.refresh()
            self.grid.setFocus()
            self.grabar()

    def abajo(self):
        row = self.grid.recno()
        if 0 <= row < (len(self.lista) - 1):
            self.lista[row + 1], self.lista[row] = self.lista[row], self.lista[row + 1]
            self.grid.goto(row + 1, 0)
            self.grid.refresh()
            self.grid.setFocus()
            self.grabar()
