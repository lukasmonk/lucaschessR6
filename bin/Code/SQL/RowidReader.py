from __future__ import annotations

import os
import time
import sqlite3

from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal


class RowidReader(QThread):
    """Lector incremental de ROWIDs sobre bases sqlite grandes.

    Diseño:
      - La cancelación se propaga a SQLite mediante set_progress_handler, de forma
        que también aborta un ORDER BY en curso (que es donde se va el tiempo).
      - No se usa terminate() en ningún caso: el hilo siempre sale por su
        propio finally, cerrando cursor y conexión.
      - Los rowids se emiten agrupados por tiempo, no por chunk, para no inundar
        la cola de eventos del hilo principal en bases de millones de registros.
    """

    # Señal para emitir nuevos rowids
    rowids_received = Signal(list)
    # Señal de fin de lectura: True si se completó, False si se canceló o hubo error
    finished_reading = Signal(bool)
    # Señal para errores
    error_occurred = Signal(str)

    # Instrucciones de la VM de SQLite entre llamadas al progress handler.
    # Más bajo = cancelación más rápida, algo más de overhead.
    VM_STEPS = 2000
    # Intervalo mínimo entre emisiones a la GUI (segundos)
    EMIT_INTERVAL = 0.10
    # Primer bloque pequeño: pinta resultados de inmediato
    FIRST_CHUNK = 64

    def __init__(self, path_file: str, tabla: str, parent=None):
        super().__init__(parent)
        self.path_file = path_file
        self.tabla = tabla
        self.where: str | None = None
        self.order: str | None = None
        self.li_row_ids: list[int] = []
        self.chunk = 4096
        self.connect_timeout = 30.0
        self._stop_flag = True  # hasta que no se llama a start_reading no hay lectura válida
        self._completed = False
        self._mutex = QMutex()

        # temp_store en memoria acelera mucho el ORDER BY, pero un sort de
        # millones de filas puede dispararse de RAM; SPILL deja que desborde a disco. -> FILE vs MEMORY
        max_memory_threshold_bytes = 100 * 1024 * 1024  # 100 MB
        if os.path.exists(path_file) and os.path.getsize(path_file) < max_memory_threshold_bytes:
            self._temp_store = "MEMORY"
        else:
            self._temp_store = "FILE"
        self._temp_store = "MEMORY"

    # ------------------------------------------------------------------ API

    def start_reading(
            self,
            li_row_ids: list[int] | None = None,
            where: str | None = None,
            order: str | None = None,
            priority: QThread.Priority = QThread.Priority.LowPriority,
    ) -> bool:
        """Detiene la lectura anterior (esperándola) y lanza una nueva.

        Devuelve False si el hilo anterior no pudo detenerse; en ese caso NO se
        relanza, porque reutilizar el objeto con el run() antiguo todavía vivo
        corrompería li_row_ids.
        """
        if not self.stopnow():
            return False

        with QMutexLocker(self._mutex):
            self.li_row_ids = li_row_ids if li_row_ids is not None else []

        self.where = where
        self.order = order
        self._stop_flag = False
        self._completed = False

        # start() resetea internamente el flag de isInterruptionRequested()
        self.start(priority)
        return True

    def setup(self, li_row_ids: list[int], where: str | None, order: str | None) -> None:
        """Prepara pero no lanza."""
        self.stopnow()
        with QMutexLocker(self._mutex):
            self.li_row_ids = li_row_ids
        self.where = where
        self.order = order
        self._stop_flag = False
        self._completed = False

    def stopnow(self, timeout_ms: int = 10000) -> bool:
        """Detiene la lectura y espera a que el hilo termine de verdad.

        Devuelve True si el hilo está parado. Nunca llama a terminate().
        """
        self._stop_flag = True
        self.requestInterruption()

        if not self.isRunning():
            return True

        if self.wait(timeout_ms):
            return True

        # Si se llega aquí hay un bug: run() se ha quedado bloqueado en algo que
        # el progress handler no cubre. Matar el hilo dejaría la conexión sqlite
        # y el mutex en un estado indefinido, así que solo se informa.
        self.error_occurred.emit(f"RowidReader: el hilo no respondió en {timeout_ms} ms")
        return False

    def terminado(self) -> bool:
        return not self.isRunning()

    def is_complete(self) -> bool:
        """True si la última lectura llegó al final de la consulta."""
        return self._completed

    def reccount(self) -> int:
        with QMutexLocker(self._mutex):
            return len(self.li_row_ids)

    def get_rowids(self) -> list[int]:
        """Copia de los rowids leídos."""
        with QMutexLocker(self._mutex):
            return self.li_row_ids.copy()

    def rowid_at(self, pos: int) -> int | None:
        """Acceso puntual sin copiar toda la lista."""
        with QMutexLocker(self._mutex):
            if 0 <= pos < len(self.li_row_ids):
                return self.li_row_ids[pos]
        return None

    def close(self) -> None:
        """Cierra y limpia el objeto completamente."""
        self._stop_flag = True
        self.requestInterruption()

        for signal in (self.rowids_received, self.finished_reading, self.error_occurred):
            try:
                signal.disconnect()
            except (RuntimeError, TypeError):
                pass  # ya estaba desconectada o no tenía conexiones

        self.stopnow()

    # -------------------------------------------------------------- interno

    def _must_stop(self) -> bool:
        return self._stop_flag or self.isInterruptionRequested()

    def _progress_handler(self) -> int:
        # Lo ejecuta SQLite dentro de este mismo hilo cada VM_STEPS instrucciones.
        # Devolver != 0 aborta la sentencia en curso, incluido un ORDER BY a medias.
        return 1 if self._must_stop() else 0

    def _build_sql(self) -> str:
        sql = f'SELECT ROWID FROM "{self.tabla}"'
        if self.where:
            sql += f" WHERE {self.where}"
        sql += f" ORDER BY {self.order}" if self.order else " ORDER BY ROWID"
        return sql

    def _apply_pragmas(self, conexion: sqlite3.Connection) -> None:
        # Solo pragmas de conexión, y ninguno que necesite escribir en el fichero:
        # este hilo es un lector puro y puede coexistir con el hilo principal.
        conexion.execute("PRAGMA query_only = ON")
        conexion.execute("PRAGMA cache_size = -16000")  # 16 MB
        conexion.execute("PRAGMA mmap_size = 268435456")  # 256 MB
        conexion.execute("PRAGMA busy_timeout = 15000")
        conexion.execute(f"PRAGMA temp_store = {self._temp_store}")

    def run(self) -> None:
        """Método principal del QThread (no llamar directamente, usar start_reading())"""
        conexion = None
        cursor = None
        completed = False

        try:
            conexion = sqlite3.connect(self.path_file, timeout=self.connect_timeout)
            self._apply_pragmas(conexion)
            conexion.set_progress_handler(self._progress_handler, self.VM_STEPS)

            cursor = conexion.cursor()
            cursor.execute(self._build_sql())

            chunk = self.FIRST_CHUNK
            pending: list[int] = []
            last_emit = 0.0

            while not self._must_stop():
                li = cursor.fetchmany(chunk)
                if not li:
                    completed = True
                    break

                new_rowids = [x[0] for x in li]
                with QMutexLocker(self._mutex):
                    self.li_row_ids.extend(new_rowids)
                pending.extend(new_rowids)

                now = time.monotonic()
                if now - last_emit >= self.EMIT_INTERVAL:
                    self.rowids_received.emit(pending)
                    pending = []
                    last_emit = now

                if len(li) < chunk:
                    completed = True
                    break

                # Rampa: arranque rápido para la primera pantalla, luego bloques grandes
                chunk = min(chunk * 4, self.chunk)

            if pending and not self._must_stop():
                self.rowids_received.emit(pending)

        except sqlite3.OperationalError as e:
            # "interrupted" es la cancelación esperada, no un error que mostrar
            if not (self._must_stop() and "interrupt" in str(e).lower()):
                self.error_occurred.emit(str(e))
        except sqlite3.DatabaseError as e:
            self.error_occurred.emit(str(e))
        except Exception as e:  # noqa: BLE001
            self.error_occurred.emit(f"Unexpected error: {e!s}")
        finally:
            if conexion is not None:
                try:
                    conexion.set_progress_handler(None, 0)
                except Exception:  # noqa: BLE001
                    pass
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:  # noqa: BLE001
                    pass
            if conexion is not None:
                try:
                    conexion.close()
                except Exception:  # noqa: BLE001
                    pass

            self._completed = completed
            self.finished_reading.emit(completed)
