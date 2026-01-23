import copy

from PySide6 import QtCore, QtGui, QtWidgets

from Code.Base.Constantes import INFINITE
from Code.Board import BoardBlocks


class ArrowSC(BoardBlocks.BloqueEspSC):
    siSizeTop: bool
    siSizeBottom: bool
    is_move: bool
    exp_x: float
    exp_y: float

    def __init__(self, escena, block_arrow, routine_if_pressed=None):
        super(ArrowSC, self).__init__(escena, block_arrow)
        self.routine_if_pressed = routine_if_pressed
        self.routine_if_pressed_argum = None

        self.poligonoSizeTop = None
        self.poligonoSizeBottom = None
        self.poligonoMove = None

        self.physical_pos2xy()

    def set_routine_if_pressed(self, rutina, carga):
        self.routine_if_pressed = rutina
        self.routine_if_pressed_argum = carga

    def set_a1h8(self, a1h8):
        self.block_data.a1h8 = a1h8
        self.physical_pos2xy()

    def get_a1h8(self):
        return self.block_data.a1h8

    def reset(self):
        self.physical_pos2xy()
        bf = self.block_data
        self.setOpacity(bf.opacity)
        self.setZValue(bf.physical_pos.orden)
        self.update()

    def physical_pos2xy(self):
        bf = self.block_data
        physical_pos = bf.physical_pos
        ac = self.board.width_square
        tf = self.board.tamFrontera

        df, dc, hf, hc = self.board.a1h8_fc(bf.a1h8)

        # siempre sale del centro
        dx = physical_pos.x = dc * ac - ac / 2 + tf / 2 - 1
        dy = physical_pos.y = df * ac - ac / 2 + tf / 2

        if bf.destino == "c":
            hx = hc * ac - ac / 2
            hy = hf * ac - ac / 2
        else:  # if bf.destino == "m":  # minimo
            min_v = INFINITE
            min_hx = min_hy = 0
            for x in (3, 2, 1):  # 3/4 = izquierda 1/2 y 1/4 izquierda
                for y in (3, 2, 1):  # 3/4 = arriba 1/2 y 1/4
                    hx = hc * ac - ac * x / 4
                    hy = hf * ac - ac * y / 4
                    v = (hx - dx) ** 2 + (hy - dy) ** 2
                    if v < min_v:
                        min_hx = hx
                        min_hy = hy
                        min_v = v
            hx = min_hx
            hy = min_hy

        physical_pos.ancho = hx + tf / 2 if dc != hc else dx
        physical_pos.alto = hy + tf / 2 if df != hf else dy

    def xy2physical_pos(self):
        bf = self.block_data
        physical_pos = bf.physical_pos
        ac = bf.width_square
        tf = self.board.tamFrontera

        def f(xy):
            return int(round((float(xy) + ac / 2.0) / float(ac), 0))

        dc = f(physical_pos.x - tf / 2)
        df = f(physical_pos.y - tf / 2)
        hc = f(physical_pos.ancho)
        hf = f(physical_pos.alto)

        def bien(fc):
            return (fc < 9) and (fc > 0)

        if bien(dc) and bien(df) and bien(hc) and bien(hf) and (dc != hc or df != hf):
            bf.a1h8 = self.board.fc_a1h8(df, dc, hf, hc)

        self.physical_pos2xy()

    def contain(self, p):
        p = self.mapFromScene(p)
        return any(
            x and x.containsPoint(p, QtCore.Qt.FillRule.OddEvenFill)
            for x in (
                self.poligonoSizeTop,
                self.poligonoSizeBottom,
                self.poligonoMove,
            )
        )

    @staticmethod
    def name():
        return _("Arrow")

    def mousePressEvent(self, event):
        QtWidgets.QGraphicsItem.mousePressEvent(self, event)
        if self.poligonoSizeTop:
            self.siSizeTop = self.poligonoSizeTop.containsPoint(event.pos(), QtCore.Qt.FillRule.OddEvenFill)
            self.siSizeBottom = self.poligonoSizeBottom.containsPoint(event.pos(), QtCore.Qt.FillRule.OddEvenFill)
            self.is_move = self.poligonoMove.containsPoint(event.pos(), QtCore.Qt.FillRule.OddEvenFill)

        p = event.scenePos()
        self.exp_x = p.x()
        self.exp_y = p.y()

    def mouse_press_ext(self, event):
        p = event.pos()
        p = self.mapFromScene(p)
        if self.poligonoSizeTop:
            self.siSizeTop = self.poligonoSizeTop.containsPoint(p, QtCore.Qt.FillRule.OddEvenFill)
            self.siSizeBottom = self.poligonoSizeBottom.containsPoint(p, QtCore.Qt.FillRule.OddEvenFill)
            self.is_move = self.poligonoMove.containsPoint(p, QtCore.Qt.FillRule.OddEvenFill)

        self.exp_x = p.x()
        self.exp_y = p.y()

    def mouseMoveEvent(self, event):
        event.ignore()
        if not (self.is_move or self.siSizeTop or self.siSizeBottom):
            return

        p = event.pos()
        p = self.mapFromScene(p)

        x = p.x()
        y = p.y()

        dx = x - self.exp_x
        dy = y - self.exp_y

        self.exp_x = x
        self.exp_y = y

        physical_pos = self.block_data.physical_pos
        if self.is_move:
            physical_pos.x += dx
            physical_pos.y += dy
            physical_pos.ancho += dx
            physical_pos.alto += dy
        elif self.siSizeTop:
            physical_pos.ancho += dx
            physical_pos.alto += dy
        elif self.siSizeBottom:
            physical_pos.x += dx
            physical_pos.y += dy

        self.escena.update()

    def mouse_move_ext(self, event):
        p = event.pos()
        p = self.mapFromScene(p)
        x = p.x()
        y = p.y()

        dx = x - self.exp_x
        dy = y - self.exp_y

        self.exp_x = x
        self.exp_y = y

        physical_pos = self.block_data.physical_pos
        physical_pos.ancho += dx
        physical_pos.alto += dy

        self.escena.update()

    def mouseReleaseEvent(self, event):
        QtWidgets.QGraphicsItem.mouseReleaseEvent(self, event)
        if self.is_activated:
            if self.is_move or self.siSizeTop or self.siSizeBottom:
                self.xy2physical_pos()
                self.escena.update()
                self.is_move = self.siSizeTop = self.siSizeBottom = False
            self.activate(False)

        if self.routine_if_pressed:
            if self.routine_if_pressed_argum:
                self.routine_if_pressed(self.routine_if_pressed_argum)
            else:
                self.routine_if_pressed()

    def mouse_release_ext(self):
        self.xy2physical_pos()
        self.escena.update()
        self.is_move = self.siSizeTop = self.siSizeBottom = False
        self.activate(False)

    def pixmap(self):
        bf = self.block_data

        a1h8 = bf.a1h8
        destino = bf.destino
        width_square = bf.width_square

        bf.width_square = 8
        bf.destino = "c"
        self.set_a1h8("a8d5")

        pm = QtGui.QPixmap(self.rect.width(), self.rect.height())
        pm.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter()
        painter.begin(pm)
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)
        painter.setRenderHint(painter.RenderHint.SmoothPixmapTransform, True)
        self.paint(painter, None, None)
        painter.end()

        pm1 = pm.copy(0, 0, 32, 32)

        bf.destino = destino
        bf.width_square = width_square
        self.set_a1h8(a1h8)

        return pm1

    def paint(self, painter, option, widget=None):

        bf = self.block_data

        if resp := paint_arrow(painter, bf):
            self.poligonoSizeBottom, self.poligonoMove, self.poligonoSizeTop = resp
            if self.is_activated:
                pen = QtGui.QPen()
                pen.setColor(QtGui.QColor("blue"))
                pen.setWidth(2)
                pen.setStyle(QtCore.Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(QtGui.QBrush())
                painter.drawPolygon(self.poligonoSizeBottom)
                painter.drawPolygon(self.poligonoMove)
                painter.drawPolygon(self.poligonoSizeTop)


def paint_arrow(painter, bf):
    physical_pos = bf.physical_pos
    dx = physical_pos.x
    dy = physical_pos.y
    hx = physical_pos.ancho
    hy = physical_pos.alto

    p_ini = QtCore.QPointF(dx, dy)
    p_fin = QtCore.QPointF(hx, hy)
    linea = QtCore.QLineF(p_ini, p_fin)
    line_size = linea.length()
    if linea.isNull():
        return None

    color = QtGui.QColor(bf.color)
    pen = QtGui.QPen()
    pen.setWidth(bf.grosor)
    pen.setColor(color)
    pen.setStyle(bf.tipoqt())
    if bf.redondeos:
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    xk = bf.width_square / 32.0

    ancho = float(bf.ancho) * xk
    vuelo = float(bf.vuelo) * xk

    alto_cab = float(bf.altocabeza) * xk
    if line_size * 0.65 < alto_cab:
        nv = line_size * 0.65
        prc = nv / alto_cab
        alto_cab = nv
        ancho *= prc
        vuelo *= prc

    xp = 1.0 - float(alto_cab) / line_size
    pbc = linea.pointAt(xp)  # base de la cabeza

    # Usamos una linea a 90 grados para calcular los puntos del final de la cabeza de arrow
    l90 = linea.normalVector()
    l90.setLength(ancho + vuelo * 2)
    l90.translate(pbc - p_ini)  # la llevamos a la base de la cabeza
    p_ala1 = l90.pointAt(0.5)  # final del ala de un lado
    l90.translate(p_ala1 - l90.p2())  # La colocamos que empiece en ala1
    p_ala2 = l90.p1()  # final del ala de un lado

    xp = 1.0 - float(alto_cab - bf.descuelgue) / line_size
    p_basecab = linea.pointAt(xp)  # Punto teniendo en cuenta el angulo en la base de la cabeza, valido para tipo c y p

    # Puntos de la base, se calculan aunque no se dibujen para determinar el poligono de control
    l90 = linea.normalVector()
    l90.setLength(ancho)
    p_base1 = l90.pointAt(0.5)  # final de la base de un lado
    l90.translate(p_base1 - l90.p2())
    p_base2 = l90.p1()  # final de la base de un lado

    lf = QtCore.QLineF(p_ini, p_basecab)
    lf.translate(p_base1 - p_ini)
    p_cab1 = lf.p2()
    lf.translate(p_base2 - p_base1)
    p_cab2 = lf.p2()

    # Poligonos para determinar si se ha pulsado sobre la arrow
    xancho = max(ancho + vuelo * 2.0, 16.0)
    xl90 = linea.normalVector()
    xl90.setLength(xancho)
    xp_base2 = xl90.pointAt(0.5)
    xl90.translate(xp_base2 - xl90.p2())  # La colocamos que empiece en base1
    xp_base1 = xl90.p1()
    xpbb = linea.pointAt(0.15)  # Siempre un 15% para cambiar de tamaño por el pie
    xl90.translate(xpbb - p_ini)  # la llevamos a la base de la cabeza
    xp_medio1b = xl90.p1()
    xp_medio2b = xl90.p2()
    xl90.translate(p_ini - xpbb)  # la llevamos a la base para poderla trasladar
    xpbc = linea.pointAt(0.85)  # Siempre un 15% para cambiar de tama_o por la cabeza
    xl90.translate(xpbc - p_ini)  # la llevamos a la base de la cabeza
    xp_medio1t = xl90.p1()
    xp_medio2t = xl90.p2()
    xl90.translate(p_fin - xpbc)  # la llevamos al final
    xp_final1 = xl90.p1()
    xp_final2 = xl90.p2()

    poligono_size_bottom = QtGui.QPolygonF([xp_base1, xp_medio1b, xp_medio2b, xp_base2, xp_base1])
    poligono_move = QtGui.QPolygonF([xp_medio1b, xp_medio1t, xp_medio2t, xp_medio2b, xp_medio1b])
    poligono_size_top = QtGui.QPolygonF([xp_medio1t, xp_final1, xp_final2, xp_medio2t, xp_medio1t])

    forma = bf.forma
    # Abierta, forma normal
    if forma == "a":
        painter.drawLine(linea)

        if alto_cab:
            lf = QtCore.QLineF(p_fin, p_ala1)
            painter.drawLine(lf)

            lf = QtCore.QLineF(p_fin, p_ala2)
            painter.drawLine(lf)

    else:
        if bf.colorinterior >= 0:
            color = QtGui.QColor(bf.colorinterior)
            if bf.colorinterior2 >= 0:
                color2 = QtGui.QColor(bf.colorinterior2)
                x, y = p_ini.x(), p_ini.y()
                gradient = QtGui.QLinearGradient(x, y, x, y - line_size - alto_cab)
                gradient.setColorAt(0.0, color)
                gradient.setColorAt(1.0, color2)
                painter.setBrush(QtGui.QBrush(gradient))
            else:
                painter.setBrush(color)

        # Cabeza cerrada
        if forma == "c":
            lf = QtCore.QLineF(p_ini, p_basecab)
            painter.drawLine(lf)
            painter.drawPolygon(QtGui.QPolygonF([p_fin, p_ala1, p_basecab, p_ala2, p_fin]))

        # Poligonal
        elif forma in "123":

            # tipo 1
            if forma == "1":
                painter.drawPolygon(
                    QtGui.QPolygonF(
                        [
                            p_base1,
                            p_cab1,
                            p_ala1,
                            p_fin,
                            p_ala2,
                            p_cab2,
                            p_base2,
                            p_base1,
                        ]
                    )
                )
            # tipo 2 base = un punto
            elif forma == "2":
                painter.drawPolygon(QtGui.QPolygonF([p_ini, p_cab1, p_ala1, p_fin, p_ala2, p_cab2, p_ini]))
            # tipo 3 base cabeza = un punto
            elif forma == "3":
                painter.drawPolygon(
                    QtGui.QPolygonF(
                        [
                            p_base1,
                            p_basecab,
                            p_ala1,
                            p_fin,
                            p_ala2,
                            p_basecab,
                            p_base2,
                            p_base1,
                        ]
                    )
                )

    return poligono_size_bottom, poligono_move, poligono_size_top


def pixmap_arrow(bf, width, height):
    bf = copy.deepcopy(bf)

    pm = QtGui.QPixmap(width, height)
    pm.fill(QtCore.Qt.GlobalColor.transparent)

    painter = QtGui.QPainter()
    painter.begin(pm)
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)
    painter.setRenderHint(painter.RenderHint.SmoothPixmapTransform, True)
    paint_arrow(painter, bf)
    painter.end()

    return pm
