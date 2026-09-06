"""
Centralized piece animation engine for ChessR.

Uses Qt's native QVariantAnimation for smooth, compositing-friendly
rendering. Fixes from the original implementation:
  - Always starts from square center (not scene pos)
  - Syncs physical_pos during animation (no desync)
  - Does NOT update bp.row/column (callers handle the board model)

Usage:
    animator = PieceAnimator(board)
    animator.animate_moves([("e2","e4")], rapidez=1.0)
"""

from PySide6 import QtCore, QtWidgets

import Code
from Code.Base.Constantes import ZVALUE_PIECE, ZVALUE_PIECE_MOVING


class PieceAnimator(QtCore.QObject):
    """Piece animation controller using Qt's native QVariantAnimation.

    QVariantAnimation integrates with Qt's rendering pipeline, producing
    smooth sub-pixel rendering and proper compositing that manual QTimer
    approaches cannot match.
    """

    def __init__(self, board, parent=None):
        super().__init__(parent)
        self.board = board
        self._animations: list[QtCore.QVariantAnimation] = []
        self._prev_viewport_mode = None
        self._easing_name = "InOutQuad"
        self._event_loop = None

    def set_easing(self, name: str):
        self._easing_name = name

    def _get_easing_curve(self):
        mapping = {
            "InOutQuad": QtCore.QEasingCurve.Type.InOutQuad,
            "Linear": QtCore.QEasingCurve.Type.Linear,
        }
        return mapping.get(self._easing_name, QtCore.QEasingCurve.Type.InOutQuad)

    def animate_moves(self, li_moves, rapidez=1.0, active_animations_out=None, finished_callback=None):
        rapidez_conf = Code.configuration.pieces_speed_porc()
        if not rapidez_conf:
            rapidez_conf = 1.0
        rp = max(rapidez, 0.01)

        animations = []
        for movim in li_moves:
            if movim[0] != "m":
                continue
            from_sq, to_sq = movim[1], movim[2]

            pieza_sc = self.board.get_piece_at(from_sq)
            if pieza_sc is None:
                continue

            dc = ord(from_sq[0]) - ord(to_sq[0])
            df = int(from_sq[1]) - int(to_sq[1])
            dist = (dc**2 + df**2) ** 0.5
            duration_ms = int(max(250, 4000.0 * dist / (11.9 * rp * rapidez_conf)))

            from_col = ord(from_sq[0]) - 96
            from_row = int(from_sq[1])
            to_col = ord(to_sq[0]) - 96
            to_row = int(to_sq[1])

            start = QtCore.QPointF(
                self.board.columna2punto(from_col),
                self.board.fila2punto(from_row),
            )
            end = QtCore.QPointF(
                self.board.columna2punto(to_col),
                self.board.fila2punto(to_row),
            )

            pieza_sc.setZValue(ZVALUE_PIECE_MOVING)

            anim = QtCore.QVariantAnimation(self)
            anim.setDuration(duration_ms)
            anim.setStartValue(start)
            anim.setEndValue(end)
            anim.setEasingCurve(self._get_easing_curve())

            def _on_value(value, p=pieza_sc):
                p.setPos(value)
                bp = p.bloquePieza
                bp.physical_pos.x = value.x()
                bp.physical_pos.y = value.y()

            def _on_finished(p=pieza_sc):
                p.setZValue(ZVALUE_PIECE)

            anim.valueChanged.connect(_on_value)
            anim.finished.connect(_on_finished)
            animations.append(anim)

        if not animations:
            return False

        if active_animations_out is not None:
            active_animations_out.extend(animations)

        self._prev_viewport_mode = self.board.viewportUpdateMode()
        self.board.setViewportUpdateMode(QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        self._animations = animations
        remaining = len(animations)

        def _on_all_finished():
            nonlocal remaining
            remaining -= 1
            if remaining <= 0:
                self._restore_viewport()
                if finished_callback:
                    finished_callback()
                if self._event_loop and self._event_loop.isRunning():
                    self._event_loop.quit()

        for anim in animations:
            anim.finished.connect(_on_all_finished)
            anim.start()

        return True

    def cancel_all(self):
        for anim in self._animations:
            anim.stop()
        self._animations.clear()
        self._restore_viewport()

    @property
    def is_running(self):
        return any(a.state() == QtCore.QAbstractAnimation.State.Running for a in self._animations)

    def _restore_viewport(self):
        if self._prev_viewport_mode is not None:
            self.board.setViewportUpdateMode(self._prev_viewport_mode)
            self._prev_viewport_mode = None

    def wait_for_finish(self):
        if not self._animations:
            return
        if not self.is_running:
            return
        self._event_loop = QtCore.QEventLoop()
        self._event_loop.exec()
        self._event_loop = None
