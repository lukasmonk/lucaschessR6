import datetime
import random
import webbrowser
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

import Code
from Code.Base import Game, Move
from Code.Board import Board2
from Code.Databases import DBgames
from Code.QT import Colocacion, Controles, Iconos, LCDialog, QTDialogs, QTMessages
from Code.Translations import TrListas
from Code.UnscrambleMoves import HistoryUnscrambleMoves
from Code.Z import Util

MOVE_MIME_TYPE = "application/x-unscramble-move"


class DraggableMoveButton(QtWidgets.QPushButton):
    """A move of the game: it can be dragged to its slot, or clicked to send it to the next empty slot."""

    def __init__(self, owner, move_index, text):
        super().__init__(text, owner)
        self.owner = owner
        self.move_index = move_index
        self.drag_start_position = None
        self.drag_started = False
        self.clicked.connect(self.send_to_next_empty_slot)

    def send_to_next_empty_slot(self):
        self.owner.place_in_next_empty_slot(self.move_index)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start_position is None:
            return
        if not (event.buttons() & QtCore.Qt.MouseButton.LeftButton):
            return
        moved = event.position().toPoint() - self.drag_start_position
        if moved.manhattanLength() < QtWidgets.QApplication.startDragDistance():
            return

        self.drag_started = True
        mime_data = QtCore.QMimeData()
        mime_data.setData(MOVE_MIME_TYPE, QtCore.QByteArray(str(self.move_index).encode()))
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(self.grab())
        drag.exec(QtCore.Qt.DropAction.CopyAction)

    def mouseReleaseEvent(self, event):
        if self.drag_started:
            self.drag_started = False
            self.drag_start_position = None
            self.setDown(False)
            event.accept()
            return
        self.drag_start_position = None
        super().mouseReleaseEvent(event)


class MoveDropSlot(QtWidgets.QWidget):
    """A position of the sequence. Its only box is the one that receives the move and, on its right, the result."""

    def __init__(self, owner, move_index, box_height):
        super().__init__(owner)
        self.owner = owner
        self.move_index = move_index
        self.button = None

        self.button_layout = Colocacion.H(self).margen(0).set_separation(owner.slot_spacing)

        self.number_label = Controles.LB(self, owner.sequence_text(move_index))
        self.number_label.align_right().relative_width(owner.number_width)
        self.button_layout.control(self.number_label)

        # The box that receives the move: the button takes its place when the move is placed.
        self.target = Controles.LB(self)
        self.target.setFixedSize(owner.move_button_width, box_height)
        self.target.setStyleSheet("QLabel { border: 1px dashed gray; }")
        self.button_layout.control(self.target)

        self.result_label = Controles.LB(self)
        self.result_label.setFixedWidth(owner.result_width)
        self.result_label.align_center()
        self.button_layout.control(self.result_label)

        self.setAcceptDrops(True)
        self.setFixedWidth(owner.slot_width)
        self.setFixedHeight(box_height)

    def dragEnterEvent(self, event):
        if self.owner.can_place_on_slot(event.mimeData(), self.move_index):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if self.owner.can_place_on_slot(event.mimeData(), self.move_index):
            event.acceptProposedAction()

    def dropEvent(self, event):
        move_index = self.owner.mime_move_index(event.mimeData())
        if move_index is None:
            return
        if self.owner.move_to_slot(move_index, self.move_index):
            event.acceptProposedAction()

    def show_button(self, button):
        self.target.hide()
        self.button = button
        button.setFixedWidth(self.owner.move_button_width)
        button.setFixedHeight(self.target.height())
        self.button_layout.insertWidget(1, button)
        button.show()

    def take_button(self):
        """Takes the move button out of the slot, ready to be placed somewhere else."""
        button = self.button
        if button is not None:
            self.button_layout.removeWidget(button)
            button.hide()
        self.button = None
        self.target.show()
        return button

    def mark_result(self, is_correct):
        color = "green" if is_correct else "red"
        icon = Iconos.pmAceptarPeque() if is_correct else Iconos.pmCancelarPeque()
        self.result_label.setPixmap(icon)
        if self.button is not None:
            self.button.setStyleSheet(f"QPushButton {{ color: {color}; font-weight: bold; }}")

    def clear_result(self):
        self.result_label.clear()
        self.result_label.setToolTip("")
        if self.button is not None:
            self.button.setStyleSheet("")


class MoveDropArea(QtWidgets.QWidget):
    """Container of the shuffled moves or of the sequence: the drops are delegated to the window."""

    def __init__(self, owner, return_moves, parent=None):
        super().__init__(parent)
        self.owner = owner
        self.return_moves = return_moves
        self.setAcceptDrops(True)

    def accepts(self, mime_data):
        move_index = self.owner.mime_move_index(mime_data)
        if move_index is None:
            return False
        if self.return_moves:
            return self.owner.can_return_to_shuffled(move_index)
        return self.owner.can_place_in_next_empty_slot(move_index)

    def dragEnterEvent(self, event):
        if self.accepts(event.mimeData()):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if self.accepts(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        move_index = self.owner.mime_move_index(event.mimeData())
        if move_index is None:
            return
        if self.return_moves:
            accepted = self.owner.return_to_shuffled(move_index)
        else:
            accepted = self.owner.place_in_next_empty_slot(move_index)
        if accepted:
            event.acceptProposedAction()


class WUnscrambleMoves(LCDialog.LCDialog):
    STARTING_LEVEL = 1
    MINIMUM_PIECES = 10
    MAX_ERRORS = 16

    @classmethod
    def start_training(cls, parent):
        saved_state, game, error = cls.read_saved_progress()
        if game is None:
            game, error = cls.choose_game(cls.STARTING_LEVEL)

        window = cls(parent, game, saved_state)
        window.exec()

    @classmethod
    def read_saved_progress(cls):
        file_path = Code.configuration.paths.file_unscramble_moves_state()
        if not Util.exist_file(file_path):
            return None, None, None

        state = Util.restore_pickle(file_path)
        required_keys = {
            "game",
            "level",
            "errors",
            "level_errors",
            "slot_moves",
            "pile_order",
            "answer_checked",
            "move_count",
        }
        if not isinstance(state, dict) or not required_keys.issubset(state):
            return None, None, "The saved training state is invalid and cannot be restored."

        if (
                not isinstance(state["game"], bytes)
                or type(state["level"]) is not int
                or state["level"] < cls.STARTING_LEVEL
                or type(state["errors"]) is not int
                or state["errors"] < 0
                or type(state["level_errors"]) is not int
                or state["level_errors"] < 0
                or state["level_errors"] > state["errors"]
                or type(state["move_count"]) is not int
                or state["move_count"] <= 0
                or type(state["answer_checked"]) is not bool
                or not isinstance(state["slot_moves"], list)
                or not isinstance(state["pile_order"], list)
        ):
            return None, None, "The saved training state is invalid and cannot be restored."

        game = Game.Game()
        game.restore(state["game"])
        if len(game) != state["move_count"] or len(state["slot_moves"]) != len(game):
            return None, None, "The saved game is incomplete and cannot be restored."

        slot_moves = state["slot_moves"]
        pile_order = state["pile_order"]
        placed_moves = [move_index for move_index in slot_moves if move_index is not None]
        if (
                any(
                    type(move_index) is not int or not 0 <= move_index < len(game)
                    for move_index in placed_moves
                )
                or any(
            type(move_index) is not int or not 0 <= move_index < len(game)
            for move_index in pile_order
        )
                or len(set(placed_moves)) != len(placed_moves)
                or len(set(pile_order)) != len(pile_order)
                or set(placed_moves).intersection(pile_order)
                or set(placed_moves).union(pile_order) != set(range(len(game)))
        ):
            return None, None, "The saved move positions are invalid and cannot be restored."

        if state["answer_checked"] and (
                any(move_index is None for move_index in slot_moves)
                or any(
            game.move(move_index).base_pgn() != game.move(slot_index).base_pgn()
            for slot_index, move_index in enumerate(slot_moves)
        )
        ):
            return None, None, "The saved training state is inconsistent and cannot be restored."

        return state, game, None

    @classmethod
    def choose_game(cls, level):
        """Returns (game, None), or (None, reason) when there is no game with that number of moves."""
        try:
            return DBgames.get_random_game(cls.MINIMUM_PIECES, level + 1), None
        except ValueError as error:
            return None, str(error)

    def __init__(self, parent, game: Game.Game, saved_state=None):
        LCDialog.LCDialog.__init__(
            self, parent, _("Unscramble the moves"), Iconos.UnscrambleMoves(), "unscramblemoves1"
        )

        self.configuration = Code.configuration
        base_font = QtWidgets.QApplication.font()
        font_size = base_font.pointSizeF()
        if font_size <= 0:
            font_size = base_font.pixelSize() if base_font.pixelSize() > 0 else 15
            font_scale = font_size / 15
        else:
            font_scale = font_size / 11
        self.move_button_width = max(1, round(100 * font_scale))
        self.number_width = max(1, round(34 * font_scale))
        self.result_width = max(1, round(18 * font_scale))
        self.slot_spacing = max(1, round(3 * font_scale))
        self.slot_width = (
                self.number_width + self.move_button_width + self.result_width + 2 * self.slot_spacing
        )
        self.game = game
        self.level = saved_state["level"] if saved_state else self.STARTING_LEVEL
        self.errors = saved_state["errors"] if saved_state else 0
        self.level_errors = saved_state["level_errors"] if saved_state else 0
        self.result_saved = False
        self.move_buttons = {}
        self.move_locations = {}
        self.slot_moves = []
        self.shuffled_positions = {}
        self.sequence_labels = []
        self.answer_checked = False
        self.results_shown = False
        self._boards_refreshed = False

        config_board = self.configuration.config_board("UNSCRAMBLE", 42)

        self.board_inicial = Board2.BoardEstatico(self, config_board)
        self.prepare_board(self.board_inicial)
        self.board_inicial.set_dispatch_size(self.change_size_board_inicial)

        self.board_final = Board2.BoardEstatico(self, config_board)
        self.prepare_board(self.board_final)
        self.board_final.set_dispatch_size(self.change_size_board_final)

        self.lb_level = Controles.LB(self).set_font_type(puntos=32 * font_scale, peso=700)
        self.lb_level.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.lb_game = Controles.LB(self, self.game_label()).align_center()
        self.lb_game.setWordWrap(True)

        font_bold = Controles.FontTypeNew(bold=True)
        font_bold10 = Controles.FontTypeNew(bold=True, point_size_delta=10)

        self.lb_total_errors = Controles.LB(self).set_font(font_bold10).align_right()
        self.lb_shuffled = Controles.LB(self, _("Shuffled moves")).set_font(font_bold).align_center()
        self.lb_initial = Controles.LB(self, _("Initial position")).set_font(font_bold).align_center()
        self.lb_final = Controles.LB(self, _("Final position")).set_font(font_bold).align_center()
        self.lb_sequence = Controles.LB(self, _("Moves in order")).set_font(font_bold).align_center()
        self.lb_level_errors = Controles.LB(self).align_right()

        self.shuffled_area, self.shuffled_layout = self.scroll_grid(return_moves=True)
        self.sequence_area, self.sequence_layout = self.scroll_grid(return_moves=False)
        self.tb = QTDialogs.LCTB(
            self,
            style=QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
            icon_size=24,
        )
        # The actions of the sequence are inside its own box, at the top left.
        self.tb_moves = QTDialogs.LCTB(
            self,
            style=QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
            icon_size=16,
        )
        self.sequence_toolbar = QtWidgets.QFrame(self)
        self.sequence_toolbar.setFrameStyle(self.sequence_area.frameStyle())
        sequence_toolbar_layout = Colocacion.H().control(self.tb_moves).relleno(1).control(self.lb_level_errors)
        sequence_toolbar_layout.setContentsMargins(4, 4, 4, 4)
        self.sequence_toolbar.setLayout(sequence_toolbar_layout)

        self.tb.new(_("Close"), Iconos.MainMenu(), self.finalize, sep=False)
        self.tb.new(_("History"), Iconos.Historial(), self.show_history, sep=False)
        self.tb.new(_("New"), Iconos.Nuevo(), self.new_training, sep=False)

        tb_ayuda = QTDialogs.LCTB(
            self,
            style=QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
            icon_size=16,
        )
        tb_ayuda.new("", Iconos.Ayuda(), self.help, sep=False)

        self.tb_moves.new(_("Continue"), Iconos.Pelicula_Seguir(), self.continue_training, sep=False)
        self.tb_moves.new(_("Verify"), Iconos.Check(), self.verify_solution, sep=False)
        self.tb_moves.new(_("Restart"), Iconos.Reset(), self.reset_game, sep=False)

        # Two equal columns: the boards on top and the move boxes below, each one under its board.
        initial_panel = Colocacion.V().control(self.lb_initial).control(self.board_inicial).margen(3)
        final_panel = Colocacion.V().control(self.lb_final).control(self.board_final).margen(3)
        shuffled_panel = Colocacion.V().control(self.lb_shuffled).control(self.shuffled_area).margen(3)
        sequence_panel = (
            Colocacion.V()
            .control(self.lb_sequence)
            .control(self.sequence_toolbar)
            .control(self.sequence_area)
            .margen(3)
        )
        initial_panel.setAlignment(self.board_inicial, QtCore.Qt.AlignmentFlag.AlignHCenter)
        final_panel.setAlignment(self.board_final, QtCore.Qt.AlignmentFlag.AlignHCenter)

        shuffled_panel.setStretchFactor(self.shuffled_area, 1)
        sequence_panel.setStretchFactor(self.sequence_area, 1)
        
        row_boards = Colocacion.H().otro(initial_panel).otro(final_panel).margen(3)
        row_boards.setStretch(0, 1)
        row_boards.setStretch(1, 1)

        row_moves = Colocacion.H().otro(shuffled_panel).otro(sequence_panel).margen(3)
        row_moves.setStretch(0, 1)
        row_moves.setStretch(1, 1)

        header = Colocacion.G().margen(3)
        header.addWidget(
            self.lb_level,
            0,
            0,
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
        )
        header.addWidget(self.lb_game, 0, 1)
        header.addWidget(
            self.lb_total_errors,
            0,
            2,
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter,
        )
        header.setColumnStretch(0, 1)
        header.setColumnStretch(1, 2)
        header.setColumnStretch(2, 1)

        layout_up = Colocacion.H().control(self.tb).relleno().control(tb_ayuda)

        layout = (
            Colocacion.V()
            .otro(layout_up)
            .otro(header)
            .otro(row_boards)
            .otro(row_moves)
            .margen(5)
        )
        # Todo lo de arriba se queda en su tamaño natural; el espacio sobrante va a las jugadas
        layout.setStretchFactor(layout_up, 0)
        layout.setStretchFactor(header, 0)
        layout.setStretchFactor(row_boards, 0)
        layout.setStretchFactor(row_moves, 1)

        self.setLayout(layout)

        self.restore_video(default_width=1060, default_height=800)
        # self.setMinimumSize(max(780, layout.minimumSize().width()), 660)
        self.update_toolbar("playing")
        self.load_game(game, saved_state)
        if self.errors > self.MAX_ERRORS:
            self.finish_run_exceeded()

    def change_size_board_inicial(self):
        with_piece = self.board_inicial.width_piece
        self.board_final.set_dispatch_size(None)
        self.board_final.change_the_width(with_piece)
        self.board_final.set_dispatch_size(self.change_size_board_final)
        self.adjust_width_to_boards()

    def change_size_board_final(self):
        with_piece = self.board_final.width_piece
        self.board_inicial.set_dispatch_size(None)
        self.board_inicial.change_the_width(with_piece)
        self.board_inicial.set_dispatch_size(self.change_size_board_inicial)
        self.adjust_width_to_boards()

    def adjust_width_to_boards(self):
        """Ajusta el ancho de la ventana al que pide el layout con los tableros actuales."""
        if self.isMaximized() or self.isFullScreen():
            return
        # En el siguiente ciclo, cuando el layout ya ha procesado el setFixedSize de los tableros
        QtCore.QTimer.singleShot(0, self._apply_width_to_boards)

    def _apply_width_to_boards(self):
        layout = self.layout()
        layout.invalidate()
        layout.activate()
        self.resize(self.sizeHint().width(), self.height())        

    def update_toolbar(self, context):
        playing = (
            self.finalize,
            self.show_history,
            self.new_training,
            self.verify_solution,
            self.reset_game
        )
        visible = {
            "playing": playing,
            "correct": (self.finalize, self.show_history, self.continue_training),
            "ended": (self.finalize, self.show_history, self.new_training),
        }[context]
        for tb in (self.tb, self.tb_moves):
            for key in tb.dic_toolbar:
                tb.set_action_visible(key, key in visible)
            tb.update()

    def update_verify_action(self):
        """Verify is only possible when every slot of the sequence is filled."""
        complete = bool(self.slot_moves) and all(move_index is not None for move_index in self.slot_moves)
        self.tb_moves.set_action_enabled(self.verify_solution, complete)

    def game_label(self):
        white = self.game.get_tag("WHITE")
        black = self.game.get_tag("BLACK")
        event = self.game.get_tag("EVENT")
        players = f"{white} - {black}"
        return f"{players}<br>{event}" if event else players

    @staticmethod
    def prepare_board(board):
        board.draw_window()
        board.disable_eboard_here()
        board.disable_all()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._boards_refreshed:
            self._boards_refreshed = True
            QtCore.QTimer.singleShot(0, self.refresh_boards)

    def refresh_boards(self):
        """The boards need the size already fixed by the layout, and on the first show it is calculated again."""
        self.layout().activate()
        for board in (self.board_inicial, self.board_final):
            self.prepare_board(board)
        self.update_boards()
        self.layout().activate()
        for board in (self.board_inicial, self.board_final):
            board.viewport().update()

    def update_boards(self):
        initial_position = self.game.first_position
        for board in (self.board_inicial, self.board_final):
            board.set_side_bottom(initial_position.is_white)
        self.board_inicial.set_position(initial_position)
        self.board_final.set_position(self.game.last_position)

    def scroll_grid(self, return_moves):
        container = MoveDropArea(self, return_moves)
        layout = QtWidgets.QGridLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        # layout.setSpacing(5)

        area = QtWidgets.QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(container)
        return area, layout

    def move_label(self, move: Move.Move):
        resp = move.base_pgn()
        if self.configuration.x_pgn_english:
            return resp
        dic = TrListas.dConvTR[0]
        li = []
        for c in resp:
            if c in dic:
                c = dic.get(c, c)
            li.append(c)
        return "".join(li)

    @staticmethod
    def shuffled_order(num_moves):
        """Random order of the moves, never the order of the solution: it would already be solved."""
        solution = list(range(num_moves))
        order = list(solution)
        if num_moves < 2:
            return order

        for _ in range(10):
            random.shuffle(order)
            if order != solution:
                return order

        order[0], order[1] = order[1], order[0]
        return order

    def create_move_buttons(self, move_order=None):
        if move_order is None:
            move_order = self.shuffled_order(len(self.game))
        for shuffled_position, move_index in enumerate(move_order):
            move = self.game.move(move_index)
            button = DraggableMoveButton(self, move_index, self.move_label(move))
            button.setFixedWidth(self.move_button_width)
            self.move_buttons[move_index] = button
            self.move_locations[move_index] = None
            self.shuffled_positions[move_index] = shuffled_position
            self.shuffled_layout.addWidget(button, shuffled_position // 2, shuffled_position % 2)

    def move_button_height(self):
        """Height of the move buttons, so the box that receives them has exactly the same size."""
        if self.move_buttons:
            return next(iter(self.move_buttons.values())).sizeHint().height()
        return 24

    def create_sequence_slots(self):
        """One row per move number: white in the left column and black in the right one, so a game that
        begins with black leaves the first cell of its row empty."""
        self.slot_moves = [None] * len(self.game)
        box_height = self.move_button_height()
        row = -1
        previous_number = None
        for move_index in range(len(self.game)):
            move = self.game.move(move_index)
            move_number = move.num_move()
            if move_number != previous_number:
                row += 1
                previous_number = move_number
            column = 0 if move.is_white() else 1
            label = MoveDropSlot(self, move_index, box_height)
            self.sequence_labels.append(label)
            self.sequence_layout.addWidget(label, row, column)

    def sequence_text(self, move_index):
        move = self.game.move(move_index)
        move_number = move.num_move()
        return f"{move_number}." if move.is_white() else f"{move_number}..."

    @staticmethod
    def mime_move_index(mime_data):
        if not mime_data.hasFormat(MOVE_MIME_TYPE):
            return None
        try:
            return int(bytes(mime_data.data(MOVE_MIME_TYPE)).decode())
        except ValueError:
            return None

    def is_playing(self):
        return not self.result_saved and not self.answer_checked

    def can_place_on_slot(self, mime_data, slot_index):
        move_index = self.mime_move_index(mime_data)
        if move_index is None or not self.is_playing():
            return False
        if not 0 <= move_index < len(self.game):
            return False
        if not 0 <= slot_index < len(self.slot_moves):
            return False
        return self.move_locations[move_index] != slot_index

    def is_move_placed(self, move_index):
        return self.move_locations.get(move_index) is not None

    def can_place_in_next_empty_slot(self, move_index):
        if not self.is_playing():
            return False
        if not 0 <= move_index < len(self.game):
            return False
        if self.is_move_placed(move_index):
            return False
        return any(slot_move is None for slot_move in self.slot_moves)

    def can_return_to_shuffled(self, move_index):
        if not self.is_playing():
            return False
        return self.move_locations.get(move_index) is not None

    def place_in_next_empty_slot(self, move_index):
        if self.is_move_placed(move_index):
            return False
        for slot_index, slot_move in enumerate(self.slot_moves):
            if slot_move is None:
                return self.move_to_slot(move_index, slot_index)
        return False

    def take_from_slot(self, slot_index):
        """Takes the move out of a slot, leaving it empty."""
        move_index = self.slot_moves[slot_index]
        if move_index is None:
            return None
        self.sequence_labels[slot_index].take_button()
        self.slot_moves[slot_index] = None
        self.move_locations[move_index] = None
        return move_index

    def take_from_shuffled(self, move_index):
        self.shuffled_positions.pop(move_index, None)
        self.shuffled_layout.removeWidget(self.move_buttons[move_index])
        self.move_buttons[move_index].hide()

    def put_in_slot(self, move_index, slot_index):
        self.sequence_labels[slot_index].show_button(self.move_buttons[move_index])
        self.slot_moves[slot_index] = move_index
        self.move_locations[move_index] = slot_index

    def put_in_shuffled(self, move_index):
        occupied_positions = set(self.shuffled_positions.values())
        position = 0
        while position in occupied_positions:
            position += 1
        self.shuffled_positions[move_index] = position
        button = self.move_buttons[move_index]
        self.shuffled_layout.addWidget(button, position // 2, position % 2)
        button.show()

    def move_to_slot(self, move_index, slot_index):
        """Places the move in the slot. If it is occupied, the two moves swap or the displaced one goes to the pile."""
        if not self.is_playing():
            return False
        if not 0 <= move_index < len(self.game):
            return False
        if not 0 <= slot_index < len(self.slot_moves):
            return False

        source_slot = self.move_locations[move_index]
        if source_slot == slot_index:
            return False
        destination_move = self.slot_moves[slot_index]
        if destination_move == move_index:
            return False

        if source_slot is None:
            self.take_from_shuffled(move_index)
        else:
            self.take_from_slot(source_slot)

        if destination_move is None:
            self.put_in_slot(move_index, slot_index)
        elif source_slot is None:
            # the move that was in the slot is replaced and goes back to the shuffled moves
            self.take_from_slot(slot_index)
            self.put_in_slot(move_index, slot_index)
            self.put_in_shuffled(destination_move)
        else:
            # the two moves of the sequence exchange their positions
            self.take_from_slot(slot_index)
            self.put_in_slot(move_index, slot_index)
            self.put_in_slot(destination_move, source_slot)

        self.update_verify_action()
        return True

    def return_to_shuffled(self, move_index):
        if not self.can_return_to_shuffled(move_index):
            return False

        self.take_from_slot(self.move_locations[move_index])
        self.put_in_shuffled(move_index)

        self.update_verify_action()
        return True

    def reset_game(self):
        """Shuffles the moves of the current game again: the level and the errors are kept."""
        self.deal_moves()

    def show_results(self, correct):
        """Marks which moves are right and which are wrong.

        The marks are only a glance: they disappear as soon as the mouse is pressed, and the moves stay
        where they are so the sequence can be corrected in place.
        """
        for slot, is_correct in zip(self.sequence_labels, correct):
            slot.mark_result(is_correct)
        self.results_shown = True
        QtWidgets.QApplication.instance().installEventFilter(self)

    def clear_results(self):
        if not self.results_shown:
            return
        self.results_shown = False
        QtWidgets.QApplication.instance().removeEventFilter(self)
        for slot in self.sequence_labels:
            slot.clear_result()

    def eventFilter(self, _obj, event):
        if self.results_shown and event.type() == QtCore.QEvent.Type.MouseButtonPress:
            self.clear_results()
        return False

    def verify_solution(self):
        if not self.is_playing():
            return
        if any(move_index is None for move_index in self.slot_moves):
            return

        correct = [
            self.move_label(self.game.move(move_index)) == self.move_label(self.game.move(slot_index))
            for slot_index, move_index in enumerate(self.slot_moves)
        ]
        self.show_results(correct)

        if all(correct):
            self.answer_checked = True
            for button in self.move_buttons.values():
                button.setEnabled(False)
            self.update_toolbar("correct")
        else:
            wrong_moves = correct.count(False)
            self.errors += wrong_moves
            self.level_errors += wrong_moves
            self.update_error_labels()
            if self.errors > self.MAX_ERRORS:
                self.finish_run_exceeded()
                return
            self.update_toolbar("playing")

    def continue_training(self):
        if not self.answer_checked or self.result_saved:
            return
        next_level = self.level + 1
        game, _error = self.choose_game(next_level)
        if game is None:
            self.finish_run_no_more_games()
            return
        self.level = next_level
        self.level_errors = 0
        self.load_game(game)

    def new_training(self):
        """Stores the run that ends here and starts another one."""
        self.save_result()
        game, error = self.choose_game(self.STARTING_LEVEL)
        if game is None:
            QTMessages.message_error(self, error)
            return

        self.level = self.STARTING_LEVEL
        self.errors = 0
        self.level_errors = 0
        self.result_saved = False
        self.load_game(game)

    def load_game(self, game, saved_state=None):
        self.game = game
        self.lb_level.set_text(f"{_('Level')} {self.level}")
        self.lb_game.set_text(self.game_label())
        self.update_error_labels()
        self.update_boards()
        if saved_state is None:
            self.deal_moves()
            return

        move_order = saved_state["pile_order"] + [
            move_index
            for move_index in range(len(game))
            if move_index not in saved_state["pile_order"]
        ]
        self.deal_moves(move_order)
        for slot_index, move_index in enumerate(saved_state["slot_moves"]):
            if move_index is not None:
                self.move_to_slot(move_index, slot_index)
        self.answer_checked = saved_state["answer_checked"]
        if self.answer_checked:
            for button in self.move_buttons.values():
                button.setEnabled(False)
            self.update_toolbar("correct")
        self.update_verify_action()

    def update_error_labels(self):
        self.lb_total_errors.set_text(f"{_('Errors')}: {self.errors}/{self.MAX_ERRORS}")
        self.lb_level_errors.set_text(f"{_('Level')}: {self.level_errors} {_('Errors')}")

    def deal_moves(self, move_order=None):
        """Shuffles the moves of the current game again and empties the sequence."""
        self.clear_results()
        self.clear_layout(self.shuffled_layout)
        self.clear_layout(self.sequence_layout)
        self.move_buttons = {}
        self.move_locations = {}
        self.slot_moves = []
        self.shuffled_positions = {}
        self.sequence_labels = []
        self.answer_checked = False
        self.create_move_buttons(move_order)
        self.create_sequence_slots()
        self.update_toolbar("playing")
        self.update_verify_action()

    @staticmethod
    def clear_layout(layout):
        while item := layout.takeAt(0):
            if widget := item.widget():
                widget.deleteLater()

    def _finish_run(self, message):
        """The training ends: there is no game available for the next level."""
        self.save_result()
        self.answer_checked = True
        for button in self.move_buttons.values():
            button.setEnabled(False)
        self.update_toolbar("ended")
        QTMessages.message_information(self,f'{message}<br><br>{_("The training has ended.")}')

    def finish_run_exceeded(self):
        self._finish_run(_("The maximum number of errors has been exceeded."))

    def finish_run_no_more_games(self):
        self._finish_run(_("No more suitable games are available."))

    def save_result(self):
        """Stores the level that was being played and how many wrong distributions the run has accumulated."""
        if self.result_saved:
            return
        if self.level > 1:
            HistoryUnscrambleMoves.save_result(
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.level - 1,
                self.errors - self.level_errors,
            )
        self.result_saved = True
        Path(self.configuration.paths.file_unscramble_moves_state()).unlink(missing_ok=True)

    def save_progress(self):
        if self.result_saved:
            return
        move_count = len(self.game)
        pile_order = sorted(self.shuffled_positions, key=self.shuffled_positions.__getitem__)
        state = {
            "game": self.game.save(),
            "level": self.level,
            "errors": self.errors,
            "level_errors": self.level_errors,
            "slot_moves": self.slot_moves.copy(),
            "pile_order": pile_order,
            "answer_checked": self.answer_checked,
            "move_count": move_count,
        }
        Util.save_pickle(self.configuration.paths.file_unscramble_moves_state(), state)

    def show_history(self):
        HistoryUnscrambleMoves.show_history(self)

    @staticmethod
    def help():
        webbrowser.open("https://lucaschess.blogspot.com/2026/10/unscramble-the-moves.html")

    def finalize(self):
        self.clear_results()
        self.save_progress()
        self.accept()

    def closeEvent(self, event):
        self.clear_results()
        self.save_progress()
        self.save_video()
        event.accept()


def start_training(parent):
    WUnscrambleMoves.start_training(parent)
