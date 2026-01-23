from typing import TYPE_CHECKING
import copy

from PySide6 import QtCore

from Code.Base.Constantes import ZVALUE_PIECE, ZVALUE_PIECE_MOVING

if TYPE_CHECKING:
    from Code.Z.CPU import CPU
    from Code.Board import Board

VTEXTO = 0
VENTERO = 1
VDECIMAL = 2


class Variable:
    def __init__(self, name, tipo, inicial):
        self.id = None
        self.name = name
        self.tipo = tipo
        self.inicial = inicial
        self.valor = inicial
        self.id = None


class Tarea:
    father: int
    cpu: "CPU"
    id: int
    total_steps: int
    current_step: int
    li_steps: list
    board: "Board.Board"
    li_puntos: list
    num_step: int

    def __init__(self):
        self.is_exclusive = False

    def enlaza(self, cpu):
        self.cpu = cpu
        self.id = cpu.new_id()
        self.father = 0


class TareaDuerme(Tarea):
    def __init__(self, seconds):
        super().__init__()
        self.seconds = seconds

    def enlaza(self, cpu):
        Tarea.enlaza(self, cpu)
        self.total_steps = int(self.seconds * 1000 / 40)

        self.current_step = 0

    def one_step(self):
        self.current_step += 1
        return self.current_step >= self.total_steps  # si es ultimo

    def __str__(self):
        return f"DUERME {self.seconds:0.2f}"


class TareaToolTip(Tarea):
    def __init__(self, texto):
        super().__init__()
        self.texto = texto

    def one_step(self):
        self.cpu.board.setToolTip(self.texto)
        return True

    def __str__(self):
        return f"TOOLTIP {self.texto}"


class TareaPonPosicion(Tarea):
    def __init__(self, position):
        super().__init__()
        self.position = position

    def one_step(self):
        self.cpu.board.set_position(self.position)
        return True

    def __str__(self):
        return self.position.fen()


class TareaCambiaPieza(Tarea):
    def __init__(self, a1h8, pieza):
        super().__init__()
        self.a1h8 = a1h8
        self.pieza = pieza

    def one_step(self):
        self.cpu.board.change_piece(self.a1h8, self.pieza)
        return True

    def __str__(self):
        return _X(_("Change piece in %1 to %2"), self.a1h8, self.pieza)

    def directo(self, board):
        return board.change_piece(self.a1h8, self.pieza)


class TareaBorraPieza(Tarea):
    def __init__(self, a1h8, tipo=None):
        super().__init__()
        self.a1h8 = a1h8
        self.tipo = tipo

    def one_step(self):
        if self.tipo:
            self.cpu.board.remove_piece_type(self.a1h8, self.tipo)
        else:
            self.cpu.board.remove_piece(self.a1h8)
        return True

    def __str__(self):
        return _X(_("Remove piece on %1"), self.a1h8)

    def directo(self, board):
        board.remove_piece(self.a1h8)


class TareaBorraPiezaSecs(Tarea):
    def __init__(self, a1h8, secs, tipo=None):
        super().__init__()
        self.a1h8 = a1h8
        self.seconds = secs
        self.tipo = tipo

    def enlaza(self, cpu):
        Tarea.enlaza(self, cpu)

        pasos = int(self.seconds * 1000.0 / cpu.ms_step)
        self.li_steps = [False] * pasos
        self.li_steps[int(pasos * 0.9)] = True
        self.total_steps = len(self.li_steps)
        self.current_step = 0

    def one_step(self):
        if self.li_steps[self.current_step]:
            if self.tipo:
                self.cpu.board.remove_piece_type(self.a1h8, self.tipo)
            else:
                self.cpu.board.remove_piece(self.a1h8)

        self.current_step += 1
        return self.current_step >= self.total_steps  # si es ultimo

    def __str__(self):
        return _X(_("Remove piece on %1"), self.a1h8)

    def directo(self, board):
        board.remove_piece(self.a1h8)


class TaskMovePiece(Tarea):
    def __init__(self, from_a1h8, to_a1h8, seconds=0.0):
        super().__init__()
        self.pieza = None
        self.from_a1h8 = from_a1h8
        self.to_a1h8 = to_a1h8
        self.seconds = seconds

    def enlaza(self, cpu):
        Tarea.enlaza(self, cpu)

        self.board = self.cpu.board

        dx, dy = self.a1h8_xy(self.from_a1h8)
        hx, hy = self.a1h8_xy(self.to_a1h8)

        linea = QtCore.QLineF(dx, dy, hx, hy)

        pasos = int(self.seconds * 1000.0 / cpu.ms_step)
        self.li_puntos = []
        for x in range(1, pasos + 1):
            self.li_puntos.append(linea.pointAt(float(x) / pasos))
        self.num_step = 0
        self.total_steps = len(self.li_puntos)

    def a1h8_xy(self, a1h8):
        row = int(a1h8[1])
        column = ord(a1h8[0]) - 96
        x = self.board.columna2punto(column)
        y = self.board.fila2punto(row)
        return x, y

    def one_step(self):
        if self.pieza is None:
            self.pieza = self.board.get_piece_at(self.from_a1h8)
            if self.pieza is None:
                return True
            self.pieza.setZValue(ZVALUE_PIECE_MOVING)
        npuntos = len(self.li_puntos)
        if npuntos == 0:
            return True
        if self.num_step >= npuntos:
            self.num_step = npuntos - 1
        p = self.li_puntos[self.num_step]
        bp = self.pieza.bloquePieza
        bp.physical_pos.x = p.x()
        bp.physical_pos.y = p.y()
        self.pieza.redo_position()
        self.num_step += 1
        is_last = self.num_step >= self.total_steps
        if is_last:
            # Para que este al final en la physical_pos correcta
            self.board.place_the_piece(bp, self.to_a1h8)
            self.pieza.setZValue(ZVALUE_PIECE)
        return is_last

    def __str__(self):
        return _X(
            _("Move piece from %1 to %2 on %3 second (s)"),
            self.from_a1h8,
            self.to_a1h8,
            f"{self.seconds:0.2f}",
        )

    def directo(self, board):
        board.move_piece(self.from_a1h8, self.to_a1h8)


class TaskCreateArrow(Tarea):
    def __init__(self, tutorial, from_sq, to_sq, id_arrow):
        super().__init__()
        self.tutorial = tutorial
        self.id_arrow = id_arrow
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.scFlecha = None

    def one_step(self):
        reg_arrow = copy.deepcopy(self.tutorial.dameFlecha(self.id_arrow))
        reg_arrow.siMovible = True
        reg_arrow.a1h8 = self.from_sq + self.to_sq
        self.scFlecha = self.cpu.board.create_arrow(reg_arrow)
        return True

    def __str__(self):
        v_arrow = self.tutorial.dameFlecha(self.id_arrow)
        return f"{_('Arrow')} {v_arrow.name} {self.from_sq}{self.to_sq}"

    def directo(self, board):
        reg_arrow = copy.deepcopy(self.tutorial.dameFlecha(self.id_arrow))
        reg_arrow.siMovible = True
        reg_arrow.a1h8 = self.from_sq + self.to_sq
        self.scFlecha = board.create_arrow(reg_arrow)
        return True


class TareaCreaMarco(Tarea):
    def __init__(self, tutorial, from_sq, to_sq, id_marco):
        super().__init__()
        self.tutorial = tutorial
        self.id_marco = id_marco
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.marco_sc = None

    def one_step(self):
        reg_marco = copy.deepcopy(self.tutorial.dameMarco(self.id_marco))
        reg_marco.siMovible = True
        reg_marco.a1h8 = self.from_sq + self.to_sq
        self.marco_sc = self.cpu.board.create_marco(reg_marco)
        return True

    def __str__(self):
        v_marco = self.tutorial.dameMarco(self.id_marco)
        return f"{_('Box')} {v_marco.name} {self.from_sq}{self.to_sq}"

    def directo(self, board):
        reg_marco = copy.deepcopy(self.tutorial.dameMarco(self.id_marco))
        reg_marco.siMovible = True
        reg_marco.a1h8 = self.from_sq + self.to_sq
        self.marco_sc = board.create_marco(reg_marco)
        return True


class TareaCreaSVG(Tarea):
    def __init__(self, tutorial, from_sq, to_sq, id_svg):
        super().__init__()
        self.tutorial = tutorial
        self.id_svg = id_svg
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.svg_sc = None

    def one_step(self):
        reg_svg = copy.deepcopy(self.tutorial.dameSVG(self.id_svg))
        reg_svg.siMovible = True
        reg_svg.a1h8 = self.from_sq + self.to_sq
        self.svg_sc = self.cpu.board.create_svg(reg_svg)
        return True

    def __str__(self):
        v_svg = self.tutorial.dameSVG(self.id_svg)
        return f"{_('Image')} {v_svg.name} {self.from_sq}{self.to_sq}"

    def directo(self, board):
        reg_svg = copy.deepcopy(self.tutorial.dameSVG(self.id_svg))
        reg_svg.siMovible = True
        reg_svg.a1h8 = self.from_sq + self.to_sq
        self.svg_sc = board.create_svg(reg_svg)
        return True
