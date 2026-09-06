import OSEngines
from PySide6 import QtCore, QtGui, QtWidgets

import Code
from Code.Competitions.ManagerGrid import GridDB
from Code.QT import Colocacion, Controles, Iconos, LCDialog, QTDialogs, QTMessages
from Code.Z import Util

# -- Palette (warm theme, contrast-tuned) --------------------------------------
C_BG_TOP = "#ded3bd"  # scene bg gradient (top)
C_BG_BOT = "#c9bca3"  # scene bg gradient (bottom)
C_BORDER = "#b8a889"  # warm border
C_TITLE_ACCENT = "#9e6f22"  # amber accent
C_HEAD_TEXT = "#3d321a"  # title text
C_HEAD_SUB = "#7a6a4a"  # subtitle text
C_ROW = "#efe8d8"  # row fill - más claro que el fondo (antes casi igual)
C_ROW_ALT = "#e2d8c2"  # alternate row fill - ahora sí se distingue de C_ROW
C_ROW_BORDER = "#c9bca6"  # row border
C_TRACK_BASE = "#b0a084"  # track line
C_FILL_A = "#d9a53a"  # progress gradient start (amber)
C_FILL_B = "#b17f24"  # progress gradient end
C_DONE_A = "#3f8f5c"  # progress/dot when maxed - verde, distinto semánticamente del ámbar "en progreso"
C_DONE_B = "#2c6f45"
C_DOT = "#b87a18"  # user dot
C_DOT_DONE = "#3f8f5c"  # coincide con C_DONE_A
C_HOVER = "#e8b64a"  # dot hover glow
C_TEXT = "#2e2413"  # primary labels
C_TEXT_DIM = "#6b5c3e"  # secondary labels - más oscuro, mejora legibilidad sobre C_ROW
C_ENDPT = "#9e8a66"  # track endpoint dots
C_SHADOW = QtGui.QColor(60, 45, 20, 70)  # sombra cálida, no gris frío


# -- Layout constants
NAME_COL_W = 132  # px reserved for engine name
RIGHT_MARGIN = 22  # px right margin after track
ROW_H = 80  # px per engine row
ROW_GAP = 6  # px between rows
TRACK_H = 8  # track line thickness
DOT_R = 9  # user dot radius
ENDPT_R = 4  # endpoint dot radius


def li_engines_fixed():
    li = []
    for alias, min_elo, max_elo in OSEngines.li_engines_fixed_elo():
        li.append((alias, min_elo, max_elo))
    return li


def _br(color: str) -> QtGui.QBrush:
    return QtGui.QBrush(QtGui.QColor(color))


def _rounded_rect(x, y, w, h, r, brush=None, pen=None):
    path = QtGui.QPainterPath()
    path.addRoundedRect(QtCore.QRectF(x, y, w, h), r, r)
    item = QtWidgets.QGraphicsPathItem(path)
    if brush is not None:
        item.setBrush(brush)
    item.setPen(pen if pen is not None else QtGui.QPen(QtCore.Qt.PenStyle.NoPen))
    return item


def _add_pill(scene, cx, cy, main_text, font_main, font_sub, accent):
    """Simple flat pill: main (elo) + sub (win/loss deltas), centred on (cx, cy)."""
    m = QtWidgets.QGraphicsSimpleTextItem(main_text)
    m.setFont(font_main)
    m.setBrush(_br(C_TEXT))
    mb = m.boundingRect()

    pad_x = 4
    radius = 3
    pw = pad_x * 2 + mb.width()
    ph = mb.height() + 6

    chip_col = QtGui.QColor(accent)
    bg = QtGui.QColor(chip_col)
    bg.setAlpha(22)
    border = QtGui.QColor(chip_col)
    border.setAlpha(120)

    chip = _rounded_rect(cx - pw / 2, cy - ph / 2, pw, ph, radius, QtGui.QBrush(bg), QtGui.QPen(border, 1))
    _apply_shadow(chip, blur=8, dy=1)
    scene.addItem(chip)

    m.setPos(cx - pw / 2 + pad_x, cy - mb.height() / 2)
    scene.addItem(m)


def _apply_shadow(item, blur=18, dx=0, dy=3, color=None):
    """Sombra suave y cálida para dar profundidad a filas, píldoras y tarjetas."""
    eff = QtWidgets.QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    eff.setOffset(dx, dy)
    eff.setColor(color if color is not None else C_SHADOW)
    item.setGraphicsEffect(eff)
    return eff


def _scene_gradient(h):
    grad = QtGui.QLinearGradient(0, 0, 0, h)
    grad.setColorAt(0.0, QtGui.QColor(C_BG_TOP))
    grad.setColorAt(1.0, QtGui.QColor(C_BG_BOT))
    return grad


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
        self._r = DOT_R + 4  # hit-test radius (slightly larger than visual)
        color_name = _("White") if is_white else _("Black")
        self.tooltip_text = f"{_('Click to play')} ({color_name})"

        self.setAcceptHoverEvents(True)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        _apply_shadow(self, blur=10, dy=1)

    # Qt overrides
    def boundingRect(self):
        r = self._r + 3
        return QtCore.QRectF(self.cx - r, self.cy - r, 2 * r, 2 * r)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        base = QtGui.QColor(C_DOT_DONE) if self.is_completed else QtGui.QColor(C_DOT)

        if self._hovered:
            glow = QtGui.QColor(C_HOVER)
            glow.setAlpha(120)
            painter.setPen(QtGui.QPen(glow, 3))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QtCore.QPointF(self.cx, self.cy), DOT_R + 3, DOT_R + 3)

        painter.setBrush(QtGui.QBrush(base))
        painter.setPen(QtGui.QPen(QtGui.QColor("#fdf6e3"), 1.2))
        painter.drawEllipse(QtCore.QPointF(self.cx, self.cy), DOT_R, DOT_R)

        if self.is_completed:
            check_pen = QtGui.QPen(
                QtGui.QColor("#fdf6e3"),
                1.6,
                QtCore.Qt.PenStyle.SolidLine,
                QtCore.Qt.PenCapStyle.RoundCap,
                QtCore.Qt.PenJoinStyle.RoundJoin,
            )
            painter.setPen(check_pen)
            path = QtGui.QPainterPath()
            path.moveTo(self.cx - 4, self.cy)
            path.lineTo(self.cx - 1, self.cy + 3)
            path.lineTo(self.cx + 4, self.cy - 3.5)
            painter.drawPath(path)

    def mousePressEvent(self, event):
        self.parent_window.hide_dot_tooltip()
        self.parent_window.start_game(self.engine_alias)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        self.parent_window.show_dot_tooltip(self)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        self.parent_window.hide_dot_tooltip()


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

        self.key_var = "THEGRID"
        if default_grid_id is None:
            dic = Code.configuration.read_variables(self.key_var)
            default_grid_id = dic.get("GRID_ID", None)
        self.grid_id = default_grid_id

        LCDialog.LCDialog.__init__(self, procesador.main_window, _("The Grid"), Iconos.Parrilla(), "thegrid")

        self.li_acciones = [
            (_("Close"), Iconos.MainMenu(), self.finalize),
            None,
            (_("New Grid"), Iconos.NuevoMas(), self.grid_new),
            (_("Delete Grid"), Iconos.Borrar(), self.grid_delete),
        ]

        self.init_header()

        # Scene + resizable view
        self.scene = QtWidgets.QGraphicsScene(self)
        self.view = GridView(self.scene, self)
        self.view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.resized.connect(self.draw_grid)
        self._dot_tooltip = None

        layout = Colocacion.V().control(self.header).control(self.view).margen(0)
        self.setLayout(layout)

        self.reload_grids()

        n = len(li_engines_fixed())
        default_height = 96 + ROW_H * n + ROW_GAP * (n - 1) + 30
        self.restore_video(default_width=700, default_height=default_height)

    # -- Header
    def init_header(self):
        self.header = QtWidgets.QWidget(self)
        self.header.setObjectName("gridHeader")

        self.cb_grids = QtWidgets.QComboBox(self.header)
        self.cb_grids.setMinimumWidth(150)
        self.cb_grids.currentIndexChanged.connect(self.grid_selected_changed)
        self.cb_grids.setStyleSheet(
            f"QComboBox {{ background:{C_ROW}; color:{C_HEAD_TEXT}; border:1px solid {C_BORDER};"
            f" border-radius:6px; padding:3px 8px; }}"
            f"QComboBox::drop-down {{ border:none; width:20px; }}"
            f"QComboBox QAbstractItemView {{ background:{C_ROW}; color:{C_HEAD_TEXT};"
            f" selection-background-color:{C_FILL_A}; selection-color:{C_ROW}; outline:0; }}"
        )

        tb = QTDialogs.LCTB(self.header, self.li_acciones, icon_size=24)
        ly = Colocacion.H().control(tb).relleno().control(self.cb_grids)
        self.header.setLayout(ly)

        self.header.setStyleSheet(
            f"#gridHeader {{ background: transparent; border-bottom: 1px solid {C_BORDER}; }}"
            f"#lbTitle {{ color:{C_HEAD_TEXT}; }}"
            f"#lbSub {{ color:{C_HEAD_SUB}; }}"
        )

    # -- Window lifecycle
    def finalize(self):
        self.save_video()
        self.reject()

    def closeEvent(self, event):
        self.hide_dot_tooltip()
        self.save_video()
        super().closeEvent(event)

    def show_dot_tooltip(self, dot):
        if self._dot_tooltip is None:
            self._dot_tooltip = QtWidgets.QLabel(self.view, QtCore.Qt.WindowType.ToolTip)
            self._dot_tooltip.setStyleSheet(
                f"background: #fdf6e3; color: {C_TEXT}; border: 3px solid {C_FILL_B};"
                " border-radius: 8px; padding: 8px 14px;"
            )
            self._dot_tooltip.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self._dot_tooltip.setText(dot.tooltip_text)
        self._dot_tooltip.adjustSize()
        dot_pos = self.view.mapFromScene(QtCore.QPointF(dot.cx, dot.cy))
        global_pos = self.view.mapToGlobal(dot_pos)
        x = global_pos.x() - self._dot_tooltip.width() // 2
        y = global_pos.y() - self._dot_tooltip.height() - 12
        self._dot_tooltip.move(x, y)
        self._dot_tooltip.show()

    def hide_dot_tooltip(self):
        if self._dot_tooltip is not None:
            self._dot_tooltip.hide()

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
        self.save_grid_id()

    def save_grid_id(self):
        dic = Code.configuration.read_variables(self.key_var)
        dic["GRID_ID"] = self.grid_id
        Code.configuration.write_variables(self.key_var, dic)

    def grid_selected_changed(self, idx):
        if idx >= 0:
            self.grid_id = self.cb_grids.itemData(idx)
            self.draw_grid()
            self.save_grid_id()

    def grid_new(self):
        resp_t = QTDialogs.vtime(
            self,
            min_minutes=0,
            min_seconds=0,
            max_minutes=999,
            max_seconds=999,
            default_minutes=5,
            default_seconds=3,
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

        vw = max(self.view.width() - 4, 420)
        vh = max(self.view.height() - 4, 320)
        self.scene.setSceneRect(0, 0, vw, vh)
        self.scene.setBackgroundBrush(QtGui.QBrush(_scene_gradient(vh)))

        box_w, box_h = 440, 230
        bx = (vw - box_w) / 2
        by = (vh - box_h) / 2 - 20
        card = _rounded_rect(
            bx,
            by,
            box_w,
            box_h,
            18,
            _br(C_ROW),
            QtGui.QPen(QtGui.QColor(C_ROW_BORDER), 1),
        )
        _apply_shadow(card, blur=24, dy=4)
        self.scene.addItem(card)

        # -- Mini-preview decorativo de un track, para anticipar visualmente qué es "The Grid"
        prev_y = by + 34
        prev_x0, prev_x1 = bx + 60, bx + box_w - 60
        prev_pen = QtGui.QPen(
            QtGui.QColor(C_TRACK_BASE), TRACK_H, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap
        )
        prev_line = QtWidgets.QGraphicsLineItem(prev_x0, prev_y, prev_x1, prev_y)
        prev_line.setPen(prev_pen)
        self.scene.addItem(prev_line)
        prev_grad = QtGui.QLinearGradient(prev_x0, prev_y, prev_x0 + (prev_x1 - prev_x0) * 0.4, prev_y)
        prev_grad.setColorAt(0.0, QtGui.QColor(C_FILL_A))
        prev_grad.setColorAt(1.0, QtGui.QColor(C_FILL_B))
        prev_fill = QtWidgets.QGraphicsLineItem(prev_x0, prev_y, prev_x0 + (prev_x1 - prev_x0) * 0.4, prev_y)
        prev_fill.setPen(
            QtGui.QPen(QtGui.QBrush(prev_grad), TRACK_H, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap)
        )
        self.scene.addItem(prev_fill)
        prev_dot = QtWidgets.QGraphicsEllipseItem(
            prev_x0 + (prev_x1 - prev_x0) * 0.4 - DOT_R, prev_y - DOT_R, 2 * DOT_R, 2 * DOT_R
        )
        prev_dot.setBrush(_br(C_DOT))
        prev_dot.setPen(QtGui.QPen(QtGui.QColor("#fdf6e3"), 1.2))
        self.scene.addItem(prev_dot)

        text_item = QtWidgets.QGraphicsTextItem()
        text_item.setTextWidth(box_w - 60)
        text_item.setHtml(
            f"<div align='center'>"
            f"<h2 style='color:{C_TITLE_ACCENT};'>{_('Welcome to The Grid!')}</h2>"
            f"<p style='color:{C_TEXT_DIM};'>{_('No competition grids exist yet.')}</p>"
            f"<p style='color:{C_TEXT_DIM};'>"
            f"{_('Click')} <b style='color:{C_TITLE_ACCENT};'>{_('New Grid')}</b> {_('to create one for your chosen time control.')}"
            f"</p></div>"
        )
        tw = text_item.boundingRect().width()
        text_item.setPos(bx + (box_w - tw) / 2, prev_y + 22)
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
        vw = max(self.view.width() - 4, 420)
        x_start = NAME_COL_W
        x_end = vw - RIGHT_MARGIN

        def get_x_local(elo, min_elo, max_elo):
            """Posición dentro del track de ESTA fila (todos los tracks miden lo mismo,
            min_elo->x_start y max_elo->x_end, sea cual sea el rango real del motor)."""
            span = max_elo - min_elo
            t = 0.0 if span <= 0 else (elo - min_elo) / span
            t = max(0.0, min(1.0, t))
            return x_start + t * (x_end - x_start)

        sorted_engines = sorted(li_engines_fixed(), key=lambda x: (x[1], x[2], x[0]))
        n_engines = len(sorted_engines)
        scene_h = n_engines * (ROW_H + ROW_GAP) + 24

        # -- Scene background rect (in case view is larger than content)
        total_h = max(scene_h, self.view.height() - 4)
        self.scene.setSceneRect(0, 0, vw, total_h)
        self.scene.setBackgroundBrush(QtGui.QBrush(_scene_gradient(total_h)))

        # -- Fonts
        name_font = Controles.FontTypeNew(point_size_delta=0, bold=True)
        sub_font = Controles.FontTypeNew(point_size_delta=-2)
        tick_font = Controles.FontTypeNew(point_size_delta=-2)
        elo_font = Controles.FontTypeNew(point_size_delta=0, bold=True)

        for idx, (alias, min_elo, max_elo) in enumerate(sorted_engines):
            state = engines_state.get(
                alias,
                {"current_elo": min_elo, "min_elo": min_elo, "max_elo": max_elo, "last_color": None, "games": 0},
            )
            current_elo = state["current_elo"]
            is_completed = current_elo >= max_elo
            next_color = self.get_next_color(state)

            row_y = 12 + idx * (ROW_H + ROW_GAP)
            cy = row_y + ROW_H / 2  # vertical centre of this row

            # -- Row background (rounded card)
            fill = _br(C_ROW_ALT if idx % 2 == 1 else C_ROW)
            row_bg = _rounded_rect(6, row_y, vw - 12, ROW_H, 12, fill, QtGui.QPen(QtGui.QColor(C_ROW_BORDER), 1))
            _apply_shadow(row_bg, blur=14, dy=2)
            self.scene.addItem(row_bg)

            # -- Engine name + next-color hint
            name_item = QtWidgets.QGraphicsSimpleTextItem(Util.primera_mayuscula(alias))
            name_item.setFont(name_font)
            name_item.setBrush(_br(C_TEXT))
            nbr = name_item.boundingRect()

            # color_name = _("White") if next_color else _("Black")
            sub_item = QtWidgets.QGraphicsSimpleTextItem(f"{_('Games')}: {state.get('games', 0)}")
            sub_item.setFont(sub_font)
            sub_item.setBrush(_br(C_TEXT_DIM))
            sbr = sub_item.boundingRect()

            unit_h = nbr.height() + 4 + sbr.height()
            name_item.setPos(16, cy - unit_h / 2)
            sub_item.setPos(16, cy - unit_h / 2 + nbr.height() + 4)
            self.scene.addItem(name_item)
            self.scene.addItem(sub_item)

            x_min = x_start
            x_max = x_end
            x_curr = get_x_local(current_elo, min_elo, max_elo)

            # -- Track
            base_pen = QtGui.QPen(
                QtGui.QColor(C_TRACK_BASE),
                TRACK_H,
                QtCore.Qt.PenStyle.SolidLine,
                QtCore.Qt.PenCapStyle.RoundCap,
            )
            base_line = QtWidgets.QGraphicsLineItem(x_min, cy, x_max, cy)
            base_line.setPen(base_pen)
            self.scene.addItem(base_line)

            # Endpoint dots
            for xdot in (x_min, x_max):
                ep = QtWidgets.QGraphicsEllipseItem(xdot - ENDPT_R, cy - ENDPT_R, 2 * ENDPT_R, 2 * ENDPT_R)
                ep.setBrush(_br(C_ENDPT))
                ep.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))
                self.scene.addItem(ep)

            # Min / max labels above track, flanking the information line
            for xlbl, lbl in ((x_min, str(min_elo)), (x_max, str(max_elo))):
                tick = QtWidgets.QGraphicsSimpleTextItem(lbl)
                tick.setFont(tick_font)
                tick.setBrush(_br(C_TEXT_DIM))
                tbr = tick.boundingRect()
                tick.setPos(xlbl - tbr.width() / 2, cy - TRACK_H / 2 - tbr.height() - 10)
                self.scene.addItem(tick)

            # -- User progress fill (gradient)
            if current_elo > min_elo:
                x_fill = x_max if is_completed else x_curr
                grad = QtGui.QLinearGradient(x_min, cy, x_fill, cy)
                if is_completed:
                    grad.setColorAt(0.0, QtGui.QColor(C_DONE_A))
                    grad.setColorAt(1.0, QtGui.QColor(C_DONE_B))
                else:
                    grad.setColorAt(0.0, QtGui.QColor(C_FILL_A))
                    grad.setColorAt(1.0, QtGui.QColor(C_FILL_B))
                fill_pen = QtGui.QPen(
                    QtGui.QBrush(grad),
                    TRACK_H,
                    QtCore.Qt.PenStyle.SolidLine,
                    QtCore.Qt.PenCapStyle.RoundCap,
                )
                fill_line = QtWidgets.QGraphicsLineItem(x_min, cy, x_fill, cy)
                fill_line.setPen(fill_pen)
                self.scene.addItem(fill_line)

            # -- Clickable user dot
            dot = UserDotItem(alias, next_color, x_curr, cy, is_completed, self)
            self.scene.addItem(dot)

            # -- Elo + win/loss pill (below the track, inside the row)
            accent = C_DONE_A if is_completed else C_DOT
            _add_pill(self.scene, x_curr, cy + 25, str(current_elo), elo_font, tick_font, accent)

    # -- Game launch
    def start_game(self, engine_alias):
        self.save_video()
        self.reject()

        all_grids = GridDB.load_all()
        grid = all_grids.get(self.grid_id)
        if not grid:
            return

        state = grid["engines"][engine_alias]
        player_elo = state["current_elo"]
        min_elo = state["min_elo"]
        max_elo = state["max_elo"]
        next_color = self.get_next_color(state)

        from Code.Competitions import ManagerGrid

        manager = ManagerGrid.ManagerGrid(self.procesador)
        manager.start(
            grid_id=self.grid_id,
            engine_alias=engine_alias,
            player_elo=player_elo,
            min_elo=min_elo,
            max_elo=max_elo,
            is_white=next_color,
            minutes=grid["minutes"],
            seconds=grid["seconds"],
        )


def play_grid(procesador, default_grid_id=None):
    w = WGrid(procesador, default_grid_id)
    w.exec()
