from PySide6 import QtCore, QtWidgets


class BloqueEspSC(QtWidgets.QGraphicsItem):
    is_activated: bool
    is_selected: bool
    exp_x: float
    exp_y: float

    def __init__(self, escena, block_data):

        super(BloqueEspSC, self).__init__()

        self.block_data = block_data

        self.board = escena.parent()

        p = self.board.baseCasillasSC.block_data.physical_pos
        margen = p.x
        self.setPos(margen, margen)

        # self.rect = QtCore.QRectF( p.x, p.y, p.ancho, p.alto )
        self.rect = QtCore.QRectF(0, 0, p.ancho, p.alto)
        self.angulo = block_data.physical_pos.angulo
        if self.angulo:
            self.rotate(self.angulo)

        escena.clearSelection()
        escena.addItem(self)
        self.escena = escena

        if block_data.siMovible:
            self.board.register_movable(self)

        self.setZValue(block_data.physical_pos.orden)
        self.setOpacity(block_data.opacity)

        self.activate(False)

        self.id_movable = None

    def activate(self, ok):
        self.is_activated = ok
        if ok:
            self.setSelected(True)
            self.is_selected = False
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
            self.setFocus()
        else:
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, False)

    def tipo(self):
        return self.__class__.__name__[6:-2]

    def boundingRect(self):
        return self.rect

    def rotate(self, angle: float):
        pass
