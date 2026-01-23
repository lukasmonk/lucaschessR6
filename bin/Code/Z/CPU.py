import collections
from typing import Any, Dict, Optional

from PySide6 import QtCore

from Code.MainWindow import Tareas


class CPU(QtCore.QObject):
    finished = QtCore.Signal()

    def __init__(self, main_window: Any) -> None:
        super().__init__()
        self.main_window = main_window
        self.board = main_window.board
        self.ms_step = 10
        self.last_id = 0
        self.timer: Optional[QtCore.QTimer] = None
        self.tasks: Dict[int, Any] = collections.OrderedDict()

    def reset(self) -> None:
        self.last_id = 0
        self.timer = None
        self.tasks = collections.OrderedDict()

    def new_id(self) -> int:
        self.last_id += 1
        return self.last_id

    def add_task(self, task: Any, parent_id: int, is_exclusive: bool) -> int:
        tid = task.id
        self.tasks[tid] = task
        task.father = parent_id
        task.is_exclusive = is_exclusive
        return tid

    def wait(self, seconds: float, parent_id: int = 0, is_exclusive: bool = False) -> int:
        task = Tareas.TareaDuerme(seconds)
        task.enlaza(self)
        return self.add_task(task, parent_id, is_exclusive)

    def show_tooltip(self, text: str, parent_id: int = 0, is_exclusive: bool = False) -> int:
        task = Tareas.TareaToolTip(text)
        task.enlaza(self)
        return self.add_task(task, parent_id, is_exclusive)

    def move_piece(
            self,
            from_a1h8: str,
            to_a1h8: str,
            seconds: float = 1.0,
            parent_id: int = 0,
            is_exclusive: bool = False,
    ) -> int:
        task = Tareas.TaskMovePiece(from_a1h8, to_a1h8, seconds)
        task.enlaza(self)
        return self.add_task(task, parent_id, is_exclusive)

    def remove_piece(
            self,
            a1h8: str,
            parent_id: int = 0,
            is_exclusive: bool = False,
            piece_type: Optional[str] = None,
    ) -> int:
        task = Tareas.TareaBorraPieza(a1h8, piece_type)
        task.enlaza(self)
        return self.add_task(task, parent_id, is_exclusive)

    def remove_piece_in_seconds(self, a1h8: str, seconds: float) -> int:
        task = Tareas.TareaBorraPiezaSecs(a1h8, seconds)
        task.enlaza(self)
        return self.add_task(task, 0, False)

    def change_piece(self, a1h8: str, piece: str, parent_id: int = 0, is_exclusive: bool = False) -> int:
        task = Tareas.TareaCambiaPieza(a1h8, piece)
        task.enlaza(self)
        return self.add_task(task, parent_id, is_exclusive)

    def set_position(self, position: Any, parent_id: int = 0) -> int:
        task = Tareas.TareaPonPosicion(position)
        task.enlaza(self)
        return self.add_task(task, parent_id, True)

    def start(self) -> None:
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.timer = QtCore.QTimer(self.main_window)
        self.timer.timeout.connect(self.run)
        self.timer.start(self.ms_step)

    def stop(self) -> None:
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.reset()
        self.finished.emit()

    def run_linear(self) -> None:
        self.start()
        if self.tasks:
            loop = QtCore.QEventLoop()
            self.finished.connect(loop.quit)
            loop.exec()

    def run(self) -> None:
        li = sorted(self.tasks.keys())
        n_steps = 0
        for tid in li:
            task = self.tasks[tid]

            if task.father and task.father in self.tasks:
                continue  # Not finished yet

            is_exclusive = task.is_exclusive
            if is_exclusive:
                if n_steps:
                    continue  # Must wait for all previous tasks to finish

            is_the_last = task.one_step()
            n_steps += 1
            if is_the_last:
                del self.tasks[tid]

            if is_exclusive:
                break

        if len(self.tasks) == 0:
            self.stop()
