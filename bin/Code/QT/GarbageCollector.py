import gc
import threading
import time
from typing import Optional, List

from PySide6 import QtCore


class GarbageCollector(QtCore.QObject):
    """
    A class that runs garbage collection periodically in a separate thread.
    """

    def __init__(self, parent: Optional[QtCore.QObject] = None, interval_seconds: int = 30, use_threading: bool = True):
        """
        Initialize the GarbageCollector.

        Args:
            parent: The parent QObject.
            interval_seconds: The interval in seconds between garbage collections.
            use_threading: If True, run collection in a separate thread.
        """
        super().__init__(parent)
        self.interval_seconds: int = int(interval_seconds)
        self.use_threading: bool = use_threading
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self.interval_seconds * 1000)
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self._on_timeout)
        self._running: bool = False
        self._lock = threading.Lock()
        self._worker_threads: List[threading.Thread] = []
        self._is_collecting: bool = False

    @QtCore.Slot()
    def _on_timeout(self) -> None:
        """
        Called when the timer times out.
        """
        if self.use_threading:
            # Clean up finished threads
            self._worker_threads = [t for t in self._worker_threads if t.is_alive()]

            with self._lock:
                if self._is_collecting:
                    return
                self._is_collecting = True

            t = threading.Thread(target=self._run_collect_safe, daemon=True)
            t.start()
            self._worker_threads.append(t)
        else:
            self._run_collect_safe()

    def _run_collect_safe(self) -> None:
        """
        Runs garbage collection safely, catching any exceptions.
        """
        try:
            gc.collect()
        except Exception:
            pass
        finally:
            if self.use_threading:
                with self._lock:
                    self._is_collecting = False

    def start(self) -> None:
        """
        Starts the garbage collector timer.
        """
        with self._lock:
            if self._running:
                return
            self._running = True
            self._timer.start()

    def stop(self, wait_workers_seconds: float = 2.0) -> None:
        """
        Stops the garbage collector timer and waits for active threads to finish.

        Args:
            wait_workers_seconds: Maximum time to wait for worker threads to finish.
        """
        with self._lock:
            if not self._running:
                return
            self._timer.stop()
            self._running = False

        if self.use_threading:
            # Wait for threads outside the lock to avoid deadlocks
            deadline = time.time() + wait_workers_seconds
            for t in list(self._worker_threads):
                if not t.is_alive():
                    continue
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                t.join(timeout=remaining)
            self._worker_threads.clear()
