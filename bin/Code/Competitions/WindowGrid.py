import OSEngines
from PySide6 import QtWidgets, QtCore, QtGui

import Code
from Code.Competitions.ManagerGrid import GridDB
from Code.QT import LCDialog, QTDialogs, Iconos, Colocacion, QTMessages, Controles
from Code.Z import Util

# -- Palette  (soft & airy light theme) ----------------------------------------
C_BG = "#f0f4fa"  # very light blue-white background
C_ROW_ALT = "#e4ecf7"  # subtle alternate row tint
C_TRACK = "#b8cfe0"  # soft steel-blue  (engine fixed range)
C_PROGRESS = "#5b9bd5"  # cornflower blue   (user progress bar)
C_DONE = "#f5a623"  # warm amber        (maxed out)
C_DOT = "#4a90d9"  # clear sky-blue    (user position dot)
C_DOT_DONE = "#e8920a"  # warm orange       (dot when maxed)
C_DOT_HOVER = "#aaccf0"  # pale sky          (hover tint)
C_TEXT = "#1e3a5f"  # deep navy         (primary labels)
C_TEXT_DIM = "#7a99b8"  # muted blue-grey   (min/max numbers)
C_ENDPT = "#9ab4cb"  # soft grey-blue    (endpoint dots)
TITLE_BG = "#4a7fc1"  # medium periwinkle (title bar)

# -- Layout constants
NAME_COL_W = 100  # px reserved for engine name
RIGHT_MARGIN = 20  # px right margin after track
ROW_H = 54  # px per engine row
TRACK_H = 7  # track line thickness
DOT_R = 9  # user dot radius
ENDPT_R = 5  # endpoint dot radius


def li_engines_fixed():
    li = []
    for alias, min_elo, max_elo in OSEngines.li_engines_fixed_elo():
        li.append((alias, min_elo, max_elo))
    return li


# -- Clickable user-position dot ------------------------------------------------
class UserDotItem(QtWidgets.QGraphicsObject):
    """The moving dot that shows current Elo and, when clicked, starts a game."""

    def __init__(self, engine_alias, is_white, cx, cy, is_completed, parent_window):
        super().__init__()
        self.engine_alias = engine_alias
        self.is_white = is_white
        self.cx = cx
        self.cy = cy
        self.is_completed = is_completed
        self.parent_window = parent_window
        self._hovered = False
        self._r = DOT_R + 3  # hit-test radius (slightly larger than visual)

        self.setAcceptHoverEvents(True)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        color_name = _("White") if is_white else _("Black")
        self.setToolTip(f"{_('Click to play')} ({color_name})")

    # Qt overrides
    def boundingRect(self):
        r = self._r
        return QtCore.QRectF(self.cx - r, self.cy - r, 2 * r, 2 * r)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        if self.is_completed:
            base = QtGui.QColor(C_DOT_DONE)
            glow = QtGui.QColor(C_DONE)
        else:
            base = QtGui.QColor(C_DOT)
            glow = QtGui.QColor(C_PROGRESS)

        if self._hovered:
            # Outer glow ring
            glow.setAlpha(80)
            painter.setPen(QtGui.QPen(glow, 4))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QtCore.QPointF(self.cx, self.cy), DOT_R + 5, DOT_R + 5)
            # Bright fill
            bright = QtGui.QColor(C_DOT_HOVER) if not self.is_completed else QtGui.QColor("#fef9c3")
            painter.setBrush(QtGui.QBrush(bright))
            painter.setPen(QtGui.QPen(QtGui.QColor("#ffffff"), 2))
        else:
            painter.setBrush(QtGui.QBrush(base))
            painter.setPen(QtGui.QPen(QtGui.QColor("#ffffff"), 1.5))

        painter.drawEllipse(QtCore.QPointF(self.cx, self.cy), DOT_R, DOT_R)

    def mousePressEvent(self, event):
        self.parent_window.start_game(self.engine_alias)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()


# -- Resizable QGraphicsView ----------------------------------------------------
class GridView(QtWidgets.QGraphicsView):
    resized = QtCore.Signal()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()


# -- Main dialog ----------------------------------------------------------------
class WGrid(LCDialog.LCDialog):
    def __init__(self, procesador, default_grid_id=None):
        self.procesador = procesador
        self.configuration = Code.configuration

        title = _("The Grid")
        icono = Iconos.Parrilla()

        LCDialog.LCDialog.__init__(self, procesador.main_window, title, icono, "thegrid3")

        self.grid_id = default_grid_id

        # Toolbar
        self.li_acciones = [
            (_("Close"), Iconos.MainMenu(), self.finalize),
            None,
            (_("New Grid"), Iconos.NuevoMas(), self.grid_new),
            (_("Delete Grid"), Iconos.Borrar(), self.grid_delete),
        ]
        self.tb = QTDialogs.LCTB(self, self.li_acciones, icon_size=24)

        # Grid selector
        font = Controles.FontTypeNew(point_size_delta=+4, bold=True)
        self.cb_grids = QtWidgets.QComboBox(self)
        self.cb_grids.setMinimumWidth(130)
        self.cb_grids.currentIndexChanged.connect(self.grid_selected_changed)
        self.cb_grids.setFont(font)

        ly_tb = Colocacion.H().control(self.tb).relleno().control(self.cb_grids).relleno()

        # Scene + resizable view
        self.scene = QtWidgets.QGraphicsScene(self)
        self.scene.setBackgroundBrush(QtGui.QColor(C_BG))

        self.view = GridView(self.scene, self)
        self.view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.resized.connect(self.draw_grid)

        layout = Colocacion.V().otro(ly_tb).control(self.view).margen(2)
        self.setLayout(layout)

        self.reload_grids()
        default_height = self.tb.height() + ROW_H * len(li_engines_fixed()) + 60
        self.restore_video(default_width=640, default_height=default_height)

    # -- Window lifecycle
    def finalize(self):
        self.save_video()
        self.reject()

    def closeEvent(self, event):
        self.save_video()
        super().closeEvent(event)

    # -- Grid management
    def reload_grids(self):
        self.cb_grids.blockSignals(True)
        self.cb_grids.clear()

        all_grids = GridDB.load_all()
        sorted_keys = sorted(all_grids.keys())

        for k in sorted_keys:
            g = all_grids[k]
            label = f"{g['minutes']}m + {g['seconds']}s"
            self.cb_grids.addItem(label, k)

        self.cb_grids.blockSignals(False)

        if sorted_keys:
            if self.grid_id in sorted_keys:
                idx = sorted_keys.index(self.grid_id)
            else:
                idx = 0
                self.grid_id = sorted_keys[0]
            self.cb_grids.setCurrentIndex(idx)
            self.draw_grid()
        else:
            self.grid_id = None
            self.draw_empty_placeholder()

    def grid_selected_changed(self, idx):
        if idx >= 0:
            self.grid_id = self.cb_grids.itemData(idx)
            self.draw_grid()

    def grid_new(self):
        resp_t = QTDialogs.vtime(
            self,
            min_minutes=0, min_seconds=0,
            max_minutes=999, max_seconds=999,
            default_minutes=5, default_seconds=3,
        )
        if resp_t:
            minutes, seconds = resp_t
            grid_id = f"{minutes}+{seconds}"

            all_grids = GridDB.load_all()
            if grid_id in all_grids:
                QTMessages.message_bold(self, _("This Grid already exists!"))
                self.grid_id = grid_id
                self.reload_grids()
                return

            grid = {"minutes": minutes, "seconds": seconds, "engines": {}}
            for alias, min_elo, max_elo in li_engines_fixed():
                grid["engines"][alias] = {
                    "current_elo": min_elo,
                    "min_elo": min_elo,
                    "max_elo": max_elo,
                    "last_color": None,
                }
            all_grids[grid_id] = grid
            GridDB.save_all(all_grids)
            self.grid_id = grid_id
            self.reload_grids()

    def grid_delete(self):
        if not self.grid_id:
            return
        if QTMessages.pregunta(self, _("Are you sure you want to delete this Grid?")):
            all_grids = GridDB.load_all()
            if self.grid_id in all_grids:
                del all_grids[self.grid_id]
                GridDB.save_all(all_grids)
            self.grid_id = None
            self.reload_grids()

    # -- Helpers
    @staticmethod
    def get_next_color(engine_data):
        last = engine_data.get("last_color")
        return True if last is None else not last

    # -- Drawing
    def draw_empty_placeholder(self):
        self.scene.clear()
        text_item = QtWidgets.QGraphicsTextItem()
        text_item.setHtml(
            f"<center>"
            f"<h2 style='color:{C_TEXT};'>{_('Welcome to The Grid!')}</h2>"
            f"<p style='color:{C_TEXT_DIM};'>{_('No competition grids exist yet.')}</p>"
            f"<p style='color:{C_TEXT_DIM};'>{_('Click <b>New Grid</b> to create one for your chosen time control.')}</p>"
            f"</center>"
        )
        text_item.setTextWidth(500)
        w = max(self.view.width(), 520)
        h = max(self.view.height(), 300)
        text_item.setPos((w - 500) / 2, h / 2 - 60)
        self.scene.addItem(text_item)

    def draw_grid(self):
        self.scene.clear()

        all_grids = GridDB.load_all()
        grid = all_grids.get(self.grid_id)
        if not grid:
            self.draw_empty_placeholder()
            return

        engines_state = grid["engines"]

        # Dynamic layout from current view width
        vw = max(self.view.width() - 4, 400)  # usable pixels
        x_start = NAME_COL_W
        x_end = vw - RIGHT_MARGIN
        track_w = x_end - x_start

        min_global = 500
        max_global = 3000

        def get_x(elo):
            t = (elo - min_global) / (max_global - min_global)
            t = max(0.0, min(1.0, t))
            return x_start + t * track_w

        sorted_engines = sorted(li_engines_fixed(), key=lambda x: (x[1], x[2], x[0]))
        n_engines = len(sorted_engines)
        scene_h = n_engines * ROW_H + 16

        # -- Scene background rect (in case view is larger than content)
        self.scene.setSceneRect(0, 0, vw, max(scene_h, self.view.height() - 4))

        # -- Engine rows
        name_font = Controles.FontTypeNew(point_size_delta=0, bold=True)
        tick_font = Controles.FontTypeNew(point_size_delta=-2)
        elo_font = Controles.FontTypeNew(point_size_delta=-1, bold=True)

        for idx, (alias, min_elo, max_elo) in enumerate(sorted_engines):
            state = engines_state.get(alias, {
                "current_elo": min_elo,
                "min_elo": min_elo,
                "max_elo": max_elo,
                "last_color": None,
            })
            current_elo = state["current_elo"]
            is_completed = current_elo >= max_elo
            next_color = self.get_next_color(state)

            row_y = 10 + idx * ROW_H
            cy = row_y + ROW_H / 2  # vertical centre of this row

            # Alternating row background
            if idx % 2 == 1:
                row_bg = QtWidgets.QGraphicsRectItem(0, row_y, vw, ROW_H)
                row_bg.setBrush(QtGui.QBrush(QtGui.QColor(C_ROW_ALT)))
                row_bg.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))
                self.scene.addItem(row_bg)

            # Engine name (left column, vertically centred)
            name_item = QtWidgets.QGraphicsSimpleTextItem(Util.primera_mayuscula(alias))
            name_item.setFont(name_font)
            name_item.setBrush(QtGui.QBrush(QtGui.QColor(C_TEXT)))
            nbr = name_item.boundingRect()
            name_item.setPos(10, cy - nbr.height() / 2)
            self.scene.addItem(name_item)

            x_min = get_x(min_elo)
            x_max = get_x(max_elo)
            x_curr = get_x(current_elo)

            # -- Fixed engine track
            track_pen = QtGui.QPen(
                QtGui.QColor(C_TRACK), TRACK_H,
                QtCore.Qt.PenStyle.SolidLine,
                QtCore.Qt.PenCapStyle.FlatCap,
            )
            track_line = QtWidgets.QGraphicsLineItem(x_min, cy, x_max, cy)
            track_line.setPen(track_pen)
            self.scene.addItem(track_line)

            # Endpoint dots (fixed positions)
            for xdot in (x_min, x_max):
                ep = QtWidgets.QGraphicsEllipseItem(
                    xdot - ENDPT_R, cy - ENDPT_R, 2 * ENDPT_R, 2 * ENDPT_R
                )
                ep.setBrush(QtGui.QBrush(QtGui.QColor(C_ENDPT)))
                ep.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))
                self.scene.addItem(ep)

            # Min / max labels below endpoints
            min_lbl = QtWidgets.QGraphicsSimpleTextItem(str(min_elo))
            min_lbl.setFont(tick_font)
            min_lbl.setBrush(QtGui.QBrush(QtGui.QColor(C_TEXT_DIM)))
            min_lbl.setPos(x_min - min_lbl.boundingRect().width() / 2, cy + ENDPT_R + 3)
            self.scene.addItem(min_lbl)

            max_lbl = QtWidgets.QGraphicsSimpleTextItem(str(max_elo))
            max_lbl.setFont(tick_font)
            max_lbl.setBrush(QtGui.QBrush(QtGui.QColor(C_TEXT_DIM)))
            max_lbl.setPos(x_max - max_lbl.boundingRect().width() / 2, cy + ENDPT_R + 3)
            self.scene.addItem(max_lbl)

            # -- User progress fill
            prog_color = QtGui.QColor(C_DONE if is_completed else C_PROGRESS)
            if current_elo > min_elo:
                prog_pen = QtGui.QPen(
                    prog_color, TRACK_H,
                    QtCore.Qt.PenStyle.SolidLine,
                    QtCore.Qt.PenCapStyle.FlatCap,
                )
                prog_line = QtWidgets.QGraphicsLineItem(x_min, cy, x_curr, cy)
                prog_line.setPen(prog_pen)
                self.scene.addItem(prog_line)

            # -- Clickable user dot
            dot = UserDotItem(alias, next_color, x_curr, cy, is_completed, self)
            self.scene.addItem(dot)

            # Current Elo label above user dot
            elo_lbl = QtWidgets.QGraphicsSimpleTextItem(str(current_elo))
            elo_lbl.setFont(elo_font)
            dot_color = QtGui.QColor(C_DOT_DONE if is_completed else C_DOT)
            elo_lbl.setBrush(QtGui.QBrush(dot_color))
            elr = elo_lbl.boundingRect()
            elo_lbl.setPos(x_curr - elr.width() / 2, cy - DOT_R - elr.height() - 2)
            self.scene.addItem(elo_lbl)

    # -- Game launch
    def start_game(self, engine_alias):
        self.save_video()
        self.reject()

        all_grids = GridDB.load_all()
        grid = all_grids.get(self.grid_id)
        if not grid:
            return

        state = grid["engines"][engine_alias]
        elo_level = state["current_elo"]
        min_elo = state["min_elo"]
        max_elo = state["max_elo"]
        next_color = self.get_next_color(state)

        from Code.Competitions import ManagerGrid
        manager = ManagerGrid.ManagerGrid(self.procesador)
        manager.start(
            grid_id=self.grid_id,
            engine_alias=engine_alias,
            elo_level=elo_level,
            min_elo=min_elo,
            max_elo=max_elo,
            is_white=next_color,
            minutes=grid["minutes"],
            seconds=grid["seconds"],
        )


def play_grid(procesador, default_grid_id=None):
    w = WGrid(procesador, default_grid_id)
    w.exec()
