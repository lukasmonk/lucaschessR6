import collections

import FasterCode
from PySide6 import QtGui

import Code
from Code.Base import Position
from Code.Board import BoardTypes
from Code.QT import ScreenUtils


class SpaceControlLayer:
    """Crea 64 MarcoSC persistentes para visualizar el espacio controlado."""

    def __init__(self, board):
        self.board = board
        self.marcos = {}  # sq -> MarcoSC
        self._dic_colors = {}
        for side in "WB":
            self._dic_colors[side == "W"] = {
                pos: ScreenUtils.qt_int(Code.dic_colors[f"SQUARED_CONTROLLED_{side}_{pos}"]) for pos in range(1, 6)
            }
            self._dic_colors[side == "W"][0] = ScreenUtils.qt_int(Code.dic_colors["SQUARED_CONTROLLED_0"])
        self._create_marcos()

    def _create_marcos(self):
        reg_marco = BoardTypes.Marco()
        reg_marco.siMovible = False
        color0 = self._dic_colors[True][0]
        for c in "abcdefgh":
            for r in "12345678":
                sq = f"{c}{r}"
                reg_marco.a1h8 = sq + sq
                reg_marco.color = color0
                reg_marco.grosor = 1
                reg_marco.redEsquina = 0
                reg_marco.colorinterior = color0
                box = self.board.create_marco(reg_marco)
                box.setZValue(5)
                box.setVisible(False)
                self.marcos[sq] = box

    def mezclar_con_pesos(self, peso1, peso2):
        # Convertimos las entradas a objetos QColor de PySide6
        color1_val = self._dic_colors[True][min(peso1, 5)]
        color2_val = self._dic_colors[False][min(peso2, 5)]
        c1 = QtGui.QColor(color1_val)
        c2 = QtGui.QColor(color2_val)

        peso_total = peso1 + peso2

        # Calculamos los nuevos canales ponderados
        # Usamos division entera // para obtener valores validos de 0-255
        r = (c1.red() * peso1 + c2.red() * peso2) // peso_total
        g = (c1.green() * peso1 + c2.green() * peso2) // peso_total
        b = (c1.blue() * peso1 + c2.blue() * peso2) // peso_total
        a = (c1.alpha() * peso1 + c2.alpha() * peso2) // peso_total

        return QtGui.QColor(r, g, b, a).rgba()

    def update(self, fen, number):
        """Recalcula frecuencias y actualiza colores (sin crear/destruir items).
        number=2,3 -> casillas controladas por blancas, 7,6 -> por negras."""
        try:
            cp = Position.Position()
            cp.read_fen(fen)
            is_white = " w " in fen
            dic_movs_side = {is_white: cp.aura()}

            fen2 = FasterCode.fen_other(fen)
            cp.read_fen(fen2)
            dic_movs_side[not is_white] = cp.aura()

            if number in (2, 7):
                li_movs = dic_movs_side[number == 2]
                dic_frec = collections.Counter(li_movs)

                for sq, box in self.marcos.items():
                    try:
                        box.physical_pos2xy()
                        frec = min(dic_frec.get(sq, 0), 5)
                        color = self._dic_colors[number == 2][frec]
                        box.block_data.color = color
                        box.block_data.colorinterior = color

                        box.setVisible(True)
                        box.update()
                    except RuntimeError:
                        # El objeto fue eliminado, lo ignoramos
                        pass

            elif number in (3, 6):
                dic_frec_w = collections.Counter(dic_movs_side[True])
                dic_frec_b = collections.Counter(dic_movs_side[False])

                for sq, box in self.marcos.items():
                    try:
                        box.physical_pos2xy()
                        fw = dic_frec_w.get(sq, 0)
                        fb = dic_frec_b.get(sq, 0)
                        fw = min(fw, 5)
                        fb = min(fb, 5)
                        if fw and fb:
                            color = self.mezclar_con_pesos(fw, fb)
                        else:
                            if fw:
                                color = self._dic_colors[True][fw]
                            elif fb:
                                color = self._dic_colors[False][fb]
                            else:
                                color = self._dic_colors[False][0]

                        box.block_data.color = color
                        box.block_data.colorinterior = color
                        box.setVisible(True)
                        box.update()
                    except RuntimeError:
                        # El objeto fue eliminado, lo ignoramos
                        pass

            try:
                self.board.escena.update()
            except RuntimeError:
                pass
        except RuntimeError:
            # El objeto fue eliminado, lo ignoramos
            pass

    def reposition(self):
        try:
            for box in self.marcos.values():
                try:
                    box.physical_pos2xy()
                    box.update()
                except RuntimeError:
                    # El objeto fue eliminado, lo ignoramos
                    pass
            try:
                self.board.escena.update()
            except RuntimeError:
                pass
        except RuntimeError:
            # El objeto fue eliminado, lo ignoramos
            pass

    def hide(self):
        try:
            for box in self.marcos.values():
                try:
                    box.setVisible(False)
                except RuntimeError:
                    # El objeto fue eliminado, lo ignoramos
                    pass
            try:
                self.board.escena.update()
            except RuntimeError:
                pass
        except RuntimeError:
            # El objeto fue eliminado, lo ignoramos
            pass

    def remove(self):
        try:
            for box in self.marcos.values():
                try:
                    self.board.xremove_item(box)
                except RuntimeError:
                    # El objeto fue eliminado, lo ignoramos
                    pass
            self.marcos = {}
            try:
                self.board.escena.update()
            except RuntimeError:
                pass
        except RuntimeError:
            # El objeto fue eliminado, lo ignoramos
            pass
