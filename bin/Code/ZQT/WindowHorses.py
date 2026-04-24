import datetime
import random
import time

import FasterCode

import Code
from Code.Base import Position
from Code.Board import Board
from Code.QT import Colocacion, Columnas, Controles, Grid, Iconos, LCDialog, QTDialogs, QTMessages
from Code.SQL import Base
from Code.Z import Util


class HorsesHistorico:
    def __init__(self, file, test):
        self.file = file
        self.db = Base.DBBase(file)
        self.tabla = test

        if not self.db.existeTabla(self.tabla):
            self.create_table()

        self.dbf = self.db.dbf(self.tabla, "FECHA,MOVES,SECONDS,HINTS", orden="FECHA DESC")
        self.dbf.leer()

        self.orden = "FECHA", "DESC"

    def close(self):
        if self.dbf:
            self.dbf.cerrar()
            self.dbf = None
        self.db.cerrar()

    def create_table(self):
        tb = Base.TablaBase(self.tabla)
        tb.nuevoCampo("FECHA", "VARCHAR", notNull=True, primaryKey=True)
        tb.nuevoCampo("MOVES", "INTEGER")
        tb.nuevoCampo("SECONDS", "INTEGER")
        tb.nuevoCampo("HINTS", "INTEGER")
        self.db.generarTabla(tb)

    def __len__(self):
        return self.dbf.reccount()

    def goto(self, num):
        self.dbf.goto(num)

    def put_order(self, key):
        nat, orden = self.orden
        if key == nat:
            orden = "DESC" if orden == "ASC" else "ASC"
        else:
            nat = key
            orden = "DESC" if key == "FECHA" else "ASC"
        self.dbf.put_order(f"{nat} {orden}")
        self.orden = nat, orden

        self.dbf.leer()
        self.dbf.gotop()

    @staticmethod
    def fecha2txt(fecha):
        return f"{fecha.year:04d}{fecha.month:02d}{fecha.day:02d}{fecha.hour:02d}{fecha.minute:02d}{fecha.second:02d}"

    @staticmethod
    def txt2fecha(txt):
        def x(d, h):
            return int(txt[d:h])

        year = x(0, 4)
        month = x(4, 6)
        day = x(6, 8)
        hour = x(8, 10)
        minute = x(10, 12)
        second = x(12, 14)
        fecha = datetime.datetime(year, month, day, hour, minute, second)
        return fecha

    def append(self, fecha, moves, seconds, hints):
        br = self.dbf.baseRegistro()
        br.FECHA = self.fecha2txt(fecha)
        br.MOVES = moves
        br.SECONDS = seconds
        br.HINTS = hints
        self.dbf.insertar(br)

    def __getitem__(self, num):
        self.dbf.goto(num)
        reg = self.dbf.registroActual()
        reg.FECHA = self.txt2fecha(reg.FECHA)
        return reg

    def remove_list_recnos(self, li_num):
        self.dbf.remove_list_recnos(li_num)
        self.dbf.pack()
        self.dbf.leer()


class WHorsesBase(LCDialog.LCDialog):
    def __init__(self, procesador, test, titulo, tabla, icono):

        LCDialog.LCDialog.__init__(self, procesador.main_window, titulo, icono, "horsesBase")

        self.procesador = procesador
        self.configuration = Code.configuration
        self.tabla = tabla
        self.icono = icono
        self.test = test
        self.titulo = titulo

        self.historico = HorsesHistorico(self.configuration.paths.file_horses(), tabla)

        # Historico
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("FECHA", _("Date"), 120, align_center=True)
        o_columns.nueva("MOVES", _("Moves"), 100, align_center=True)
        o_columns.nueva("SECONDS", _("Second(s)"), 80, align_center=True)
        o_columns.nueva("HINTS", _("Hints"), 90, align_center=True)
        self.ghistorico = Grid.Grid(self, o_columns, complete_row_select=True, select_multiple=True)
        self.ghistorico.fix_min_width()

        # Tool bar
        li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.finalize),
            None,
            (_("Start"), Iconos.Empezar(), self.empezar),
            None,
            (_("Remove"), Iconos.Borrar(), self.borrar),
            None,
        )
        self.tb = QTDialogs.LCTB(self, li_acciones)

        # Colocamos
        ly_tb = Colocacion.H().control(self.tb).margen(0)
        ly = Colocacion.V().otro(ly_tb).control(self.ghistorico).margen(3)

        self.setLayout(ly)

        self.register_grid(self.ghistorico)
        self.restore_video(with_tam=False)

        self.ghistorico.gotop()

    def grid_doubleclick_header(self, _grid, obj_column):
        key = obj_column.key
        if key in ("FECHA", "MOVES", "HINTS"):
            self.historico.put_order(key)
            self.ghistorico.gotop()
            self.ghistorico.refresh()

    def grid_num_datos(self, _grid):
        return len(self.historico)

    def grid_dato(self, _grid, row, obj_column):
        col = obj_column.key
        reg = self.historico[row]
        if col == "FECHA":
            return Util.local_date_time(reg.FECHA)
        elif col == "MOVES":
            return f"{reg.MOVES}"
        elif col == "SECONDS":
            return f"{reg.SECONDS}"
        elif col == "HINTS":
            return f"{reg.HINTS}"
        return None

    def finalize(self):
        self.save_video()
        self.historico.close()
        self.reject()

    def borrar(self):
        li = self.ghistorico.list_selected_recnos()
        if len(li) > 0:
            if QTMessages.pregunta(self, _("Do you want to delete all selected records?")):
                self.historico.remove_list_recnos(li)
        self.ghistorico.gotop()
        self.ghistorico.refresh()

    def empezar(self):
        w = WHorses(self, self.test, self.titulo, self.icono)
        w.exec()
        self.ghistorico.gotop()
        self.ghistorico.refresh()


class WHorses(LCDialog.LCDialog):
    dic_min_moves: dict
    timer: float
    moves: int
    hints: int
    nayuda: int
    num_moves: int
    moves_parcial: int
    pos_temporal: int
    cp_activo: Position.Position
    cp_inicial: Position.Position
    base_unica: bool
    is_white: bool
    camino: list
    current_position: int
    celdas_ocupadas: list

    def __init__(self, owner, test, titulo, icono):
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, "horses")

        self.historico = owner.historico
        self.procesador = Code.procesador
        self.configuration = Code.configuration

        self.dic_min_moves = {}  # celda->min_moves

        self.test = test

        # Board
        config_board = self.configuration.config_board("HORSES", 48)

        self.board = Board.Board(self, config_board)
        self.board.draw_window()
        self.board.side_indicator_sc.setOpacity(0.01)
        self.board.set_dispatcher(self.player_has_moved_dispatcher)

        # Rotulo vtime
        self.lbInformacion = Controles.LB(self, _("Goal: to capture the king up to the square a8")).align_center()
        self.lbMoves = Controles.LB(self, "")

        # Tool bar
        li_acciones = (
            (_("Cancel"), Iconos.Cancelar(), self.cancelar),
            None,
            (_("Reinit"), Iconos.Reiniciar(), self.reiniciar),
            None,
            (_("Help"), Iconos.AyudaGR(), self.get_help),
        )
        self.tb = QTDialogs.LCTB(self, li_acciones)

        # Layout
        ly_info = Colocacion.H().control(self.lbInformacion).relleno().control(self.lbMoves)
        ly_t = Colocacion.V().relleno().control(self.board).otro(ly_info).relleno().margen(10)

        ly = Colocacion.V().control(self.tb).otro(ly_t).relleno().margen(0)

        self.setLayout(ly)

        self.restore_video()
        self.adjustSize()

        self.reset()

    def reset(self):
        self.prepara_test()
        self.board.set_side_bottom(True)
        self.board.set_position(self.cp_inicial)
        self.board.remove_arrows()
        self.timer = time.time()
        self.moves = 0
        self.hints = 0
        self.nayuda = 0  # para que haga un rondo al elegir en la get_help de todos los caminos uno de ellos
        self.pon_siguiente()

    def pon_num_moves(self):
        color = "red" if self.num_moves <= self.moves_parcial else "green"
        self.lbMoves.set_text(f'<font color="{color}">{self.moves_parcial}/{self.num_moves}</font>')

    def pon_siguiente(self):
        pos_desde = self.camino[0 if self.base_unica else self.current_position]
        pos_hasta = self.camino[self.current_position + 1]
        tlist = FasterCode.li_n_min(pos_desde, pos_hasta, self.celdas_ocupadas)
        self.num_moves = len(tlist[0]) - 1
        self.dic_min_moves[pos_hasta] = self.num_moves
        self.moves_parcial = 0

        cp = self.cp_inicial.copia()

        self.pos_temporal = pos_desde
        ca = FasterCode.pos_a1(pos_desde)
        cp.squares[ca] = "N" if self.is_white else "n"
        cs = FasterCode.pos_a1(pos_hasta)
        cp.squares[cs] = "k" if self.is_white else "K"

        self.cp_activo = cp

        self.board.set_position(cp)
        self.board.activate_side(self.is_white)

        self.pon_num_moves()

    def avanza(self):
        self.board.remove_arrows()
        self.current_position += 1
        if self.current_position == len(self.camino) - 1:
            self.final()
            return
        self.pon_siguiente()

    def final(self):
        seconds = int(time.time() - self.timer)
        self.historico.append(Util.today(), self.moves, seconds, self.hints)

        min_moves = sum(value for value in self.dic_min_moves.values())

        QTMessages.message_bold(
            self,
            f"<b>{_('Congratulations, goal achieved')}<b>"
            f"<ul><li>{_('Moves')}: <b>{self.moves}</b> ({_('Minimum')}={min_moves}) </li>"
            f"<li>{_('Hints')}: <b>{self.hints}</b></li>"
            f"<li>{_('Time')}: <b>{seconds}</b></li></ul>",
        )

        self.save_video()
        self.accept()

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        p0 = FasterCode.a1_pos(from_sq)
        p1 = FasterCode.a1_pos(to_sq)
        if p1 in FasterCode.dict_n[p0]:
            self.moves += 1
            self.moves_parcial += 1
            self.pon_num_moves()
            if p1 not in self.camino:
                return False
            self.cp_activo.squares[from_sq] = None
            self.cp_activo.squares[to_sq] = "N" if self.is_white else "n"
            self.board.set_position(self.cp_activo)
            self.board.activate_side(self.is_white)
            self.pos_temporal = p1
            if p1 == self.camino[self.current_position + 1]:
                self.avanza()
                return True
            return True
        return False

    def prepara_test(self):
        self.cp_inicial = Position.Position()
        self.cp_inicial.read_fen("8/8/8/8/8/8/8/8 w - - 0 1")
        squares = self.cp_inicial.squares
        self.base_unica = self.test > 3
        self.is_white = random.randint(1, 2) == 1

        celdas_ocupadas = []
        if self.test == 2:  # 4 peones
            if self.is_white:
                celdas_ocupadas = [18, 21, 9, 11, 12, 14, 42, 45, 33, 35, 36, 38]
            else:
                celdas_ocupadas = [18, 21, 25, 27, 28, 30, 42, 45, 49, 51, 52, 54]
            for a1 in ("c3", "c6", "f3", "f6"):
                squares[a1] = "p" if self.is_white else "P"
        elif self.test == 3:  # levitt
            ch = celdas_ocupadas = [27]
            for li in FasterCode.dict_q[27]:
                for x in li:
                    ch.append(x)

            squares["d4"] = "q" if self.is_white else "Q"

        self.camino = []
        p, f, s = 0, 7, 1
        for x in range(8):
            li = list(range(p, f + s, s))
            for t in range(7, -1, -1):
                if li[t] in celdas_ocupadas:
                    del li[t]
            self.camino.extend(li)
            if s == 1:
                s = -1
                p += 15
                f += 1
            else:
                s = +1
                p += 1
                f += 15

        if self.test == 5:  # empieza en e4
            for n, x in enumerate(self.camino):
                if x == 28:
                    del self.camino[n]
                    self.camino.insert(0, 28)
                    break

        self.current_position = 0
        self.celdas_ocupadas = celdas_ocupadas

    def closeEvent(self, event):
        self.save_video()
        event.accept()

    def cancelar(self):
        self.save_video()
        self.reject()

    def reiniciar(self):
        # Si no esta en la position actual, le lleva a la misma
        pa = self.pos_temporal
        pi = self.camino[0 if self.base_unica else self.current_position]

        if pa == pi:
            self.reset()
        else:
            self.pon_siguiente()

    def get_help(self):
        self.hints += 1
        self.board.remove_arrows()
        pa = self.pos_temporal
        ps = self.camino[self.current_position + 1]
        tlist = FasterCode.li_n_min(pa, ps, self.celdas_ocupadas)
        if self.nayuda >= len(tlist):
            self.nayuda = 0

        li = tlist[self.nayuda]
        for x in range(len(li) - 1):
            d = FasterCode.pos_a1(li[x])
            h = FasterCode.pos_a1(li[x + 1])
            self.board.show_arrow_mov(d, h, "2")
        self.nayuda += 1
        self.board.refresh()


def window_horses(procesador, test, titulo, icono):
    tabla = f"TEST{test}"
    w = WHorsesBase(procesador, test, titulo, tabla, icono)
    w.exec()
