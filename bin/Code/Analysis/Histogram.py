import math
import os

from PySide6 import QtCore, QtGui, QtWidgets

import Code
from Code.Z import Util
from Code.Base import Game
from Code.QT import Iconos, QTDialogs, QTUtils, SelectFiles

# Constantes
SCORE_MIN = -30.0
SCORE_MAX = 30.0
LOG_SCALE_FACTOR = 6.705
ELO_MIN = 0
ELO_MAX = 3600
POINT_RADIUS = 6
LOST_POINTS_THRESHOLD = 100


def escala_logaritmica(total_height, score):
    """
    Convierte un score en centipawns a coordenada Y usando escala logarítmica.

    Args:
        total_height: Altura total del gráfico
        score: Puntuación en el rango [-30, 30]

    Returns:
        Coordenada Y para el gráfico

    Raises:
        ValueError: Si score está fuera del rango válido
    """
    if not (SCORE_MIN <= score <= SCORE_MAX):
        raise ValueError(f"Score {score} fuera de rango [{SCORE_MIN}, {SCORE_MAX}]")

    # Convertimos 0...30 en 0...10
    # La mitad de altura = 10
    v = LOG_SCALE_FACTOR * math.log10(abs(score) + 1.0)
    mid = total_height / 2
    factor = 1.0 if score < 0 else -1.0
    return -(mid - v * mid * factor / 10)


class HSerie:
    factor: float
    factor_elo: float
    step: float

    def __init__(self):
        self.liPoints = []
        self.minimum = SCORE_MIN
        self.maximum = SCORE_MAX
        self.qcolor = {True: QtGui.QColor("#DACA99"), False: QtGui.QColor("#83C5F8")}

        # Elo para que 3400 - 1000 esten en los limites interiores
        self.maximum_elo = ELO_MAX
        self.minimum_elo = ELO_MIN

    def add_point(self, hpoint):
        hpoint.set_grid_pos(len(self.liPoints))
        self.liPoints.append(hpoint)

    def firstmove(self):
        return int(self.liPoints[0].nummove) if self.liPoints else 0

    def lastmove(self):
        return int(self.liPoints[-1].nummove) if self.liPoints else 0

    def lines(self):
        return list(zip(self.liPoints, self.liPoints[1:])) if self.liPoints else []

    def steps(self):
        return int(self.lastmove() - self.firstmove() + 1)

    def scene_points(self, sz_width, sz_height, sz_left):
        ntotal_y = self.maximum - self.minimum
        self.factor = sz_height * 1.0 / ntotal_y
        ntotal_y_elo = self.maximum_elo - self.minimum_elo
        self.factor_elo = sz_height * 1.0 / ntotal_y_elo
        firstmove = self.firstmove()
        self.step = sz_width * 1.0 / self.steps()
        nmedia_x = len(self.liPoints) / 2
        for npoint, point in enumerate(self.liPoints):
            point.minmax_rvalue(self.minimum, self.maximum)
            dr = ("s" if point.value > 0 else "n") + ("e" if npoint < nmedia_x else "w")
            point.set_dir_tooltip(dr)
            rx = (point.nummove - firstmove) * self.step - sz_left
            ry = escala_logaritmica(sz_height, point.rvalue)

            ry_elo = -(point.elo - self.minimum_elo) * self.factor_elo
            point.set_rxy(rx, ry, ry_elo)


class HPoint:
    rx: float
    ry: float
    ry_elo: float

    def __init__(self, nummove, value, lostp, lostp_abs, tooltip, elo):
        self.nummove = nummove
        self.rvalue = self.value = value
        self.tooltip = tooltip
        self.is_white = "..." not in tooltip
        self.dir_tooltip = ""
        self.rlostp = self.lostp = lostp
        self.lostp_abs = lostp_abs
        self.gridPos = None
        self.brush_color = self.set_color()
        self.elo = elo

    def set_color(self):
        """Retorna el color del brush y pen para el punto."""
        if self.is_white:
            return QtCore.Qt.GlobalColor.white, QtCore.Qt.GlobalColor.black
        return QtCore.Qt.GlobalColor.black, QtCore.Qt.GlobalColor.black

    def set_grid_pos(self, grid_pos):
        self.gridPos = grid_pos

    def minmax_rvalue(self, minimum, maximum):
        if minimum > self.value:
            self.rvalue = minimum
        elif maximum < self.value:
            self.rvalue = maximum
        self.rlostp = min(self.rlostp, maximum - minimum)

    def set_dir_tooltip(self, dr):
        self.dir_tooltip = dr

    def set_rxy(self, rx, ry, ry_elo):
        self.rx = rx
        self.ry = ry
        self.ry_elo = ry_elo

    def clone(self):
        return HPoint(self.nummove, self.value, self.lostp, self.lostp_abs, self.tooltip, self.elo)


class GraphPoint(QtWidgets.QGraphicsItem):
    def __init__(self, histogram, point, si_values):
        super(GraphPoint, self).__init__()

        self.histogram = histogram
        self.point = point

        self.setAcceptHoverEvents(True)

        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setZValue(2)

        self.tooltipping = False
        self.si_values = si_values

    def hoverLeaveEvent(self, event):
        self.histogram.hide_tooltip()
        self.tooltipping = False

    def hoverMoveEvent(self, event):
        if not self.tooltipping:
            self.tooltipping = True
            ry = self.point.ry if self.si_values else self.point.ry_elo
            self.histogram.show_tooltip(self.point.tooltip, self.point.rx, ry, self.point.dir_tooltip)
            self.tooltipping = False

    def set_pos(self):
        ry = self.point.ry if self.si_values else self.point.ry_elo
        self.setPos(self.point.rx + 4, ry + 4)

    def boundingRect(self):
        # Rectángulo que contiene el círculo de radio POINT_RADIUS
        diameter = POINT_RADIUS * 2
        return QtCore.QRectF(-POINT_RADIUS, -POINT_RADIUS, diameter, diameter)

    def paint(self, painter, option, widget=None) -> None:
        brush, color = self.point.brush_color
        painter.setPen(color)
        painter.setBrush(QtGui.QBrush(brush))
        painter.drawEllipse(-POINT_RADIUS, -POINT_RADIUS, POINT_RADIUS, POINT_RADIUS)

    def mousePressEvent(self, event):
        self.histogram.dispatch(self.point.gridPos)

    def mouseDoubleClickEvent(self, event):
        self.histogram.dispatch_enter(self.point.gridPos)


class GraphToolTip(QtWidgets.QGraphicsItem):
    dispatch = None
    font = None
    metrics = None
    dr = None
    x = None
    y = None
    xrect = None

    def __init__(self, graph):
        super(GraphToolTip, self).__init__()

        self.graph = graph
        self.texto = ""

        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setZValue(2)

    def set_dispatch(self, dispatch):
        self.dispatch = dispatch

    def set_text_pos(self, txt, x, y, dr):
        self.font = self.scene().font()
        self.font.setPointSize(12)
        self.metrics = QtGui.QFontMetrics(self.font)

        self.texto = txt
        self.dr = dr
        self.x = x
        self.y = y
        rancho = self.metrics.horizontalAdvance(self.texto) + 10
        ralto = self.metrics.height() + 12

        rx = 10 if "e" in self.dr else -rancho
        ry = -ralto if "n" in self.dr else +ralto

        self.xrect = QtCore.QRectF(rx, ry, rancho, ralto)

        if "w" in self.dr:
            x -= 10
        if "n" in self.dr:
            y -= 10

        self.setPos(x, y)
        self.show()

    def boundingRect(self):
        return self.xrect

    def paint(self, painter, option, widget=None):
        painter.setFont(self.font)
        painter.setPen(QtGui.QColor("#545454"))
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#F1EDED")))
        painter.drawRect(self.xrect)
        painter.drawText(self.xrect, QtCore.Qt.AlignmentFlag.AlignCenter, self.texto)


class Histogram(QtWidgets.QGraphicsView):
    def __init__(self, owner, hserie, grid, ancho, si_values, elo_medio=None):
        super(Histogram, self).__init__()

        self.hserie = hserie

        self.owner = owner
        self.grid = grid

        self.elo_medio = elo_medio

        self.steps = hserie.steps()
        self.step = ancho / self.steps

        sz_width = self.steps * self.step
        sz_height = sz_left = ancho * 300 / 900

        scene = QtWidgets.QGraphicsScene(self)
        scene.setItemIndexMethod(QtWidgets.QGraphicsScene.ItemIndexMethod.NoIndex)
        scene.setSceneRect(-sz_height, -sz_height, sz_width, sz_height)
        self.setScene(scene)
        self.scene = scene
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorViewCenter)

        hserie.scene_points(sz_width, sz_height, sz_left)

        self.si_values = si_values

        for point in hserie.liPoints:
            node = GraphPoint(self, point, si_values)
            scene.addItem(node)
            node.set_pos()

        self.pointActive = 0

        self.tooltip = GraphToolTip(self)
        scene.addItem(self.tooltip)
        self.tooltip.hide()

        self.set_point_active(0)

    def dispatch(self, grid_pos):
        self.grid.goto(grid_pos, 0)
        self.grid.setFocus()

    def set_point_active(self, num):
        self.pointActive = num
        self.scene.invalidate()

    def dispatch_enter(self, grid_pos):
        self.grid.setFocus()
        self.owner.grid_doble_click(self.grid, grid_pos, 0)

    def show_tooltip(self, txt, x, y, dr):
        self.tooltip.set_text_pos(txt, x, y, dr)

    def hide_tooltip(self):
        self.tooltip.hide()

    def drawBackground(self, painter, rect):
        sr = scene_rect = self.sceneRect()
        width = sr.width()
        height = sr.height()
        left = sr.left()
        right = sr.right()
        top = sr.top()
        bottom = sr.bottom()
        serie = self.hserie

        firstmove = self.hserie.firstmove()

        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        text_rect = QtCore.QRectF(left - 2, bottom + 4, width + 2, height)
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        njg = self.steps + 1
        step = self.step

        # Numeros de move, en dos lineas
        for x in range(njg - 1):
            num = firstmove + x
            if decimal := num // 10:
                painter.drawText(text_rect.translated(x * step, 0), str(decimal))
        for x in range(njg - 1):
            num = firstmove + x
            ent = num % 10
            painter.drawText(text_rect.translated(x * step, 12), str(ent))

        def set_pen_color(str_color, xwidth=None):
            xpen = painter.pen()
            if xwidth:
                xpen.setWidth(xwidth)
            xpen.setColor(QtGui.QColor(str_color))
            painter.setPen(xpen)

        # Lineas verticales de referencia
        set_pen_color("#D9D9D9")
        for x in range(1, njg - 1):
            t = left + step * x
            painter.drawLine(t, int(top), t, int(bottom))

        # Eje de las y a la izquierda
        painter.setPen(QtGui.QColor("#545454"))
        align_right = QtCore.Qt.AlignmentFlag.AlignRight
        h = 12
        x = left - 10
        w = 24
        if self.si_values:
            coord = [-15, -8, -4, -2, -0.8, 0, 0.8, +2, +4, +8, +15]
            plant = "%+0.1f"
            for d in coord:
                y = escala_logaritmica(height, d) - height / 42
                painter.drawText(int(x - 30), int(y), w + 10, h, align_right, plant % d)

            # Linea de referencia en la mitad-horizontal
            painter.setPen(QtCore.Qt.GlobalColor.black)
            t = top + height * 0.50
            painter.drawLine(int(left), int(t), int(right), int(t))

            # Lineas referencia horizontal
            set_pen_color("#D9D9D9")
            for d in coord:
                if d:
                    t = escala_logaritmica(height, d)
                    painter.drawLine(int(left), int(t), int(right), int(t))

        else:
            coord = range(0, 3800, 200)
            for d in coord:
                y = bottom - height * d / 3600 - height / 42
                rot = str(d)
                painter.drawText(int(x - 120), int(y), w + 100, h, align_right, rot)

            # Lineas referencia horizontal
            set_pen_color("#D9D9D9")
            for d in coord:
                if d:
                    t = bottom - height * d / 3600
                    painter.drawLine(int(left), int(t), int(right), int(t))

        # Barras de los puntos perdidos
        if self.owner.show_lost_points_value():
            n = max(serie.step / 2.0 - 2, 4) / 2.0
            color = QtGui.QColor("#FFCECE")
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(color)
            for p in serie.liPoints:
                if p.rlostp:
                    y = bottom - p.rlostp * serie.factor
                    rect = QtCore.QRectF(p.rx - n, bottom - 1, n * 2, y)
                    painter.drawRect(rect)
                    p.rect_lost = rect

            painter.setBrush(QtGui.QBrush())

        # Lineas que unen los puntos
        for is_white in (True, False):
            if self.si_values:
                set_pen_color(serie.qcolor[is_white], 4)
                for p, p1 in serie.lines():
                    if p.is_white == is_white:
                        ry = p.ry
                        ry1 = p1.ry
                        painter.drawLine(p.rx + 1, ry, p1.rx, ry1)

            else:
                set_pen_color(serie.qcolor[is_white], 4)
                previous = None
                next1 = None
                for p, p1 in serie.lines():
                    if p.is_white == is_white:
                        if previous:
                            painter.drawLine(previous.rx + 1, previous.ry_elo, p.rx, p.ry_elo)
                        previous = p
                    if p1:
                        next1 = p1

                if next1 and next1.is_white == is_white:
                    painter.drawLine(previous.rx + 1, previous.ry_elo, next1.rx, next1.ry_elo)

        painter.setBrush(QtGui.QBrush())

        # Caja exterior
        set_pen_color("#545454", 1)
        painter.drawRect(scene_rect)

        # Linea roja de la position actual
        set_pen_color("#DE5044", 2)
        if 0 <= self.pointActive < len(self.hserie.liPoints):
            p = serie.liPoints[self.pointActive]
            painter.drawLine(p.rx, int(bottom), p.rx, int(top))

    def mousePressEvent(self, event):
        super(Histogram, self).mousePressEvent(event)
        ep = self.mapToScene(event.pos())

        # Verificar click en barras de puntos perdidos
        if self.owner.show_lost_points_value():
            for p in self.hserie.liPoints:
                if p.rlostp and hasattr(p, 'rect_lost') and p.rect_lost.contains(ep):
                    self.dispatch(p.gridPos)

        # Menú contextual con click derecho
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            self._show_context_menu()

    def _show_context_menu(self):
        """Muestra el menú contextual para exportar el histograma."""
        menu = QTDialogs.LCMenu(self)
        menu.opcion("clip", _("Copy to clipboard"), Iconos.Clipboard())
        menu.separador()
        menu.opcion("file", f"{_('Save')} png", Iconos.GrabarFichero())
        if resp := menu.lanza():
            pm = self.grab()
            if resp == "clip":
                QTUtils.set_clipboard(pm, tipo="p")
            else:
                self._save_to_file(pm)

    def _save_to_file(self, pixmap):
        """Guarda el histograma como archivo PNG."""
        configuration = Code.configuration
        if path := SelectFiles.salvaFichero(
            self,
            _("File to save"),
            configuration.save_folder(),
            "png",
            False,
        ):
            pixmap.save(path, "png")
            configuration.set_save_folder(os.path.dirname(path))

    def mouseDoubleClickEvent(self, event):
        super(Histogram, self).mouseDoubleClickEvent(event)
        ep = self.mapToScene(event.pos())
        for p in self.hserie.liPoints:
            if p.rlostp and hasattr(p, 'rect_lost') and p.rect_lost.contains(ep):
                self.dispatch_enter(p.gridPos)

    def wheelEvent(self, event):
        k = QtCore.Qt.Key.Key_Left if event.angleDelta().y() > 0 else QtCore.Qt.Key.Key_Right
        self.owner.grid_tecla_control(self.grid, k, False, False, False)


def gen_histograms(game: Game.Game):
    def initial_position() -> int:
        if game.is_fen_initial():
            return 0
        xpos = (game.first_position.num_moves - 1) * 2
        return xpos + 1 if game.starts_with_black else xpos

    def safe_avg(total: float, count: int) -> float:
        return total / count if count else 0.0

    hgame = HSerie()
    hwhite = HSerie()
    hblack = HSerie()

    moves_all, moves_w, moves_b = [], [], []
    porc_t = porc_w = porc_b = 0.0

    pos_inicial = initial_position()

    for num, move in enumerate(game.li_moves, pos_inicial):
        if not move.analysis:
            continue

        mrm, pos = move.analysis
        is_white = move.is_white()

        pts = mrm.li_rm[pos].centipawns_abs()
        pts0 = mrm.li_rm[0].centipawns_abs()

        move.lostp_abs = lostp_abs = pts0 - pts
        porc = LOST_POINTS_THRESHOLD - lostp_abs if lostp_abs < LOST_POINTS_THRESHOLD else 0
        move.porcentaje = porc

        porc_t += porc
        moves_all.append(move)

        if is_white:
            moves_w.append(move)
            porc_w += porc
        else:
            pts, pts0 = -pts, -pts0
            moves_b.append(move)
            porc_b += porc

        pts /= 100.0
        pts0 /= 100.0
        lostp = abs(pts0 - pts)

        nj = num / 2.0 + 1.0
        label = f"{int(nj)}.{'' if is_white else '..'}"
        move.xnum = label
        move.xsiW = is_white

        label += move.pgn_translated()
        tooltip = f"{label} {pts:+0.02f}"
        if lostp:
            tooltip += f"  ↓{lostp:0.02f}"

        avg = getattr(move, "elo_avg", 0)
        hp = HPoint(nj, pts, lostp, lostp_abs, tooltip, avg)

        hgame.add_point(hp)
        (hwhite if is_white else hblack).add_point(hp.clone())

    alm = Util.Record()
    alm.hgame = hgame
    alm.hwhite = hwhite
    alm.hblack = hblack

    alm.lijg = moves_all
    alm.lijgW = moves_w
    alm.lijgB = moves_b

    alm.porcT = safe_avg(porc_t, len(moves_all))
    alm.porcW = safe_avg(porc_w, len(moves_w))
    alm.porcB = safe_avg(porc_b, len(moves_b))

    return alm
