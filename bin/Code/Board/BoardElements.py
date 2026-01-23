import base64

from PySide6 import QtCore, QtGui, QtWidgets

from Code.Base.Constantes import ZVALUE_PIECE, ZVALUE_PIECE_MOVING
from Code.QT import Controles, ScreenUtils


class BloqueSC(QtWidgets.QGraphicsItem):
    def __init__(self, escena, physical_pos):

        super(BloqueSC, self).__init__()

        self.setPos(physical_pos.x, physical_pos.y)
        self.rect = QtCore.QRectF(0, 0, physical_pos.ancho, physical_pos.alto)

        self.angulo = physical_pos.angulo
        if self.angulo:
            self.rotate(self.angulo)

        escena.clearSelection()
        escena.addItem(self)
        self.escena = escena
        self.owner = self.escena.views()[0].parent()

        self.siRecuadro = False

        self.setZValue(physical_pos.orden)

    def boundingRect(self):
        return self.rect

    def activate(self, ok: bool):
        if ok:
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
            self.setFocus()
        else:
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, False)

    def rotate(self, angle):
        pass


class CajaSC(BloqueSC):
    def __init__(self, escena, block_caja):

        physical_pos = block_caja.physical_pos

        super(CajaSC, self).__init__(escena, physical_pos)

        self.block_data = self.bloqueCaja = block_caja

    def paint(self, painter, option, widget=None):
        bl = self.bloqueCaja
        pen = QtGui.QPen()
        pen.setColor(ScreenUtils.qt_color(bl.color))
        pen.setWidth(bl.grosor)
        pen.setStyle(bl.tipoqt())
        painter.setPen(pen)
        if bl.colorRelleno != -1:
            painter.setBrush(ScreenUtils.qt_brush(bl.colorRelleno))
        if bl.redEsquina:
            painter.drawRoundedRect(self.rect, bl.redEsquina, bl.redEsquina)
        else:
            painter.drawRect(self.rect)


class CirculoSC(BloqueSC):
    def __init__(self, escena, block_circulo, rutina=None):

        physical_pos = block_circulo.physical_pos

        super(CirculoSC, self).__init__(escena, physical_pos)

        self.block_data = self.bloqueCirculo = block_circulo

        self.rutina = rutina

    def paint(self, painter, option, widget=None):
        bl = self.bloqueCirculo
        pen = QtGui.QPen()
        pen.setColor(QtGui.QColor(bl.color))
        pen.setWidth(bl.grosor)
        pen.setStyle(bl.tipoqt())
        painter.setPen(pen)
        if bl.colorRelleno != -1:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(bl.colorRelleno)))
        if bl.grados in [360, 0]:
            painter.drawEllipse(self.rect)
        else:
            painter.drawPie(self.rect, 0 * 16, bl.grados * 16)

    def mostrar(self):
        physical_pos = self.block_data.physical_pos
        self.setPos(physical_pos.x, physical_pos.y)
        self.show()
        self.update()

    def mousePressEvent(self, event):
        if self.rutina and self.contains(event.pos()):
            self.rutina(event.button() == QtCore.Qt.MouseButton.LeftButton)


class PuntoSC(CirculoSC):
    def __init__(self, escena, block_circle, rutina, cursor=None):
        CirculoSC.__init__(self, escena, block_circle, rutina)

        self.cursor = QtCore.Qt.CursorShape.WhatsThisCursor if cursor is None else cursor

        self.setAcceptHoverEvents(True)

    def hoverLeaveEvent(self, event):
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def hoverMoveEvent(self, event):
        self.setCursor(self.cursor)


class TextoSC(BloqueSC):
    def __init__(self, escena, block_texto, rutina=None):

        super(TextoSC, self).__init__(escena, block_texto.physical_pos)

        self.block_data = self.bloqueTexto = block_texto

        self.font = Controles.FontType(txt=str(block_texto.font_type))
        self.font.setPixelSize(block_texto.font_type.puntos)
        self.textOption = QtGui.QTextOption(ScreenUtils.qt_alignment(block_texto.alineacion))
        self.rutina = rutina

    def paint(self, painter, option, widget=None):

        pen = QtGui.QPen()

        if self.bloqueTexto.colorFondo != -1:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(self.bloqueTexto.colorFondo)))

        num_color = self.bloqueTexto.colorTexto if self.bloqueTexto.colorTexto != -1 else 0
        if self.bloqueTexto.colorFondo != -1:
            painter.setBrush(QtGui.QBrush())
        pen.setColor(ScreenUtils.qt_color(num_color))
        painter.setPen(pen)
        painter.setFont(self.font)
        painter.drawText(self.rect, self.bloqueTexto.valor, self.textOption)

        if self.siRecuadro:
            pen = QtGui.QPen()
            pen.setColor(QtGui.QColor("blue"))
            pen.setWidth(1)
            pen.setStyle(QtCore.Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.rect)

    def mousePressEvent(self, event):
        event.accept()
        if self.rutina:
            self.rutina(
                event.button() == QtCore.Qt.MouseButton.LeftButton,
                True,
                self.bloqueTexto.valor,
            )

    def mouseReleaseEvent(self, event):
        event.ignore()
        if self.rutina:
            self.rutina(
                event.button() == QtCore.Qt.MouseButton.LeftButton,
                False,
                self.bloqueTexto.valor,
            )


class PiezaSC(BloqueSC):
    def __init__(self, escena, block_pieza, board):

        self.board = board

        physical_pos = block_pieza.physical_pos

        super(PiezaSC, self).__init__(escena, physical_pos)

        self.block_data = self.bloquePieza = block_pieza

        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

        pz = block_pieza.pieza
        self.pixmap = board.pieces.render(pz)

        self.ini_pos = None

        self.pmRect = QtCore.QRectF(0, 0, physical_pos.ancho, physical_pos.ancho)
        self.is_active = False
        self.is_dragging = False
        self.setAcceptHoverEvents(True)

        ancho = physical_pos.ancho
        self.limL = -10  # ancho * 20 / 100
        self.limH = ancho - self.limL
        self.dragable = False

        self.dispatchMove = None

        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def redo_position(self):
        physical_pos = self.bloquePieza.physical_pos
        self.setPos(physical_pos.x, physical_pos.y)
        self.update()

    def paint(self, painter, option, widget=None):
        self.pixmap.render(painter, self.rect)

    def hoverMoveEvent(self, event):
        if self.is_active:
            pos = event.pos()
            x = pos.x()
            y = pos.y()
            self.dragable = (self.limL <= x <= self.limH) and (self.limL <= y <= self.limH)
            self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor if self.dragable else QtCore.Qt.CursorShape.ArrowCursor)
            self.setFocus()
        else:
            self.dragable = False
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def hoverLeaveEvent(self, event):
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        if self.dragable:
            self.ini_pos = event.scenePos()
            self.setZValue(ZVALUE_PIECE_MOVING)
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            QtWidgets.QGraphicsItem.mousePressEvent(self, event)
            if self.dispatchMove:
                self.dispatchMove()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if self.dragable:
            current_pos = event.scenePos()
            physical_pos = self.bloquePieza.physical_pos
            punto = QtCore.QPointF(
                current_pos.x() - physical_pos.ancho / 2,
                current_pos.y() - physical_pos.alto / 2,
            )
            self.setPos(punto)
            self.update()
            event.ignore()
        else:
            QtWidgets.QGraphicsItem.mouseMoveEvent(self, event)

    def set_dispatch_move(self, rutina):
        self.dispatchMove = rutina

    def mouseReleaseEvent(self, event):
        QtWidgets.QGraphicsItem.mouseReleaseEvent(self, event)
        if self.dragable:
            self.setZValue(ZVALUE_PIECE)
            self.board.try_to_move(self, event.scenePos())

    def activate(self, activate):
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, activate)
        self.is_active = activate
        if activate:
            self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            self.setFocus()
        else:
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def reload_graphics(self):
        """
        Recarga el renderer gráfico de la pieza
        según la configuración actual del board.
        """
        pz = self.bloquePieza.pieza

        # Pedir de nuevo el renderer al proveedor de piezas
        self.pixmap = self.board.pieces.render(pz)

        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.DeviceCoordinateCache)

        # Forzar repaint
        self.update()


class TiempoSC(BloqueSC):
    chunk: float
    exp_x: float

    def __init__(self, escena, block_texto, rutina=None):

        BloqueSC.__init__(self, escena, block_texto.physical_pos)

        self.block_data = self.bloqueTexto = block_texto

        self.font = Controles.FontType(txt=str(block_texto.font_type))
        self.textOption = QtGui.QTextOption(ScreenUtils.qt_alignment("c"))
        self.rutina = rutina
        self.minimo = block_texto.min
        self.maximo = block_texto.max
        self.inicialx = block_texto.physical_pos.x
        self.rutina = block_texto.rutina

        self.is_end = self.maximo == self.inicialx

        self.hundreds_of_second = 0

    def initial_position(self):
        physical_pos = self.block_data.physical_pos
        physical_pos.x = self.inicialx
        self.setPos(physical_pos.x, physical_pos.y)

    def texto(self):
        t = self.calc_hundreds_of_second()
        cent = t % 100
        t //= 100
        mins = t // 60
        t -= mins * 60
        seg = t
        return "%02d:%02d:%02d" % (mins, seg, cent)

    def set_hundreds_of_second(self, hundreds_of_second):
        self.hundreds_of_second = hundreds_of_second
        self.chunk = hundreds_of_second * 1.0 / 400.0

    def setphysical_pos(self, hundreds_of_second):
        physical_pos = self.block_data.physical_pos
        physical_pos.x = int(round(1.0 * hundreds_of_second / self.chunk, 0) + self.inicialx)
        self.setPos(physical_pos.x, physical_pos.y)

    def has_moved(self):
        return self.block_data.physical_pos.x != self.inicialx

    def calc_hundreds_of_second(self):
        return (
            int(round(self.chunk * (self.block_data.physical_pos.x - self.inicialx + 400), 0))
            if self.is_end
            else int(round(self.chunk * (self.block_data.physical_pos.x - self.inicialx), 0))
        )

    def paint(self, painter, option, widget=None):

        pen = QtGui.QPen()

        painter.setBrush(QtGui.QBrush(QtGui.QColor(self.block_data.colorFondo)))
        painter.drawRect(self.rect)

        num_color = self.block_data.colorTexto if self.block_data.colorTexto != -1 else 0
        if self.block_data.colorFondo != -1:
            painter.setBrush(QtGui.QBrush())
        pen.setColor(ScreenUtils.qt_color(num_color))
        painter.setPen(pen)
        painter.setFont(self.font)
        painter.drawText(self.rect, self.texto(), self.textOption)
        if linea := self.block_data.linea:
            r = self.rect
            x, y, w, h = r.x(), r.y(), r.width(), r.height()
            if linea == "a":
                y = y + h
                w = 1
                h = 50
            elif linea == "d":
                x += w
                y -= 10
                w = 1
                h = 32
            elif linea == "i":
                y -= 10
                w = 1
                h = 32
            rect = QtCore.QRectF(x, y, w, h)
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        QtWidgets.QGraphicsItem.mousePressEvent(self, event)
        p = event.scenePos()
        self.exp_x = p.x()

    def mouseMoveEvent(self, event):
        event.ignore()

        p = event.scenePos()
        x = p.x()

        dx = x - self.exp_x

        self.exp_x = x

        bd = self.block_data
        physical_pos = bd.physical_pos
        nx = physical_pos.x + dx
        if self.minimo <= nx <= self.maximo:
            physical_pos.x += dx

            self.setPos(physical_pos.x, physical_pos.y)
            if self.rutina:
                self.rutina(int(physical_pos.x - self.inicialx))

            self.escena.update()

    def check_position(self):
        bd = self.block_data
        physical_pos = bd.physical_pos
        mal = False
        if physical_pos.x < self.minimo:
            physical_pos.x = self.minimo
            mal = True
        elif physical_pos.x > self.maximo:
            physical_pos.x = self.maximo
            mal = True
        if mal:
            self.setPos(physical_pos.x, physical_pos.y)
            self.escena.update()

    def activate(self, ok):
        if ok:
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.setFocus()
        else:
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)


class PixmapSC(BloqueSC):
    def __init__(self, escena, block_imagen, pixmap=None, rutina=None):

        physical_pos = block_imagen.physical_pos

        BloqueSC.__init__(self, escena, physical_pos)

        self.block_data = self.bloqueImagen = block_imagen

        if pixmap:
            self.pixmap = pixmap
        else:
            self.pixmap = QtGui.QPixmap()
            self.pixmap.loadFromData(base64.b64decode(block_imagen.pixmap), "PNG")

        r = self.pixmap.rect()
        self.pmRect = QtCore.QRectF(0, 0, r.width(), r.height())

        self.rutina = rutina

    def paint(self, painter, option, widget=None):
        painter.drawPixmap(self.rect, self.pixmap, self.pmRect)

    def mousePressEvent(self, event):
        if self.rutina and self.contains(event.pos()):
            self.rutina()
