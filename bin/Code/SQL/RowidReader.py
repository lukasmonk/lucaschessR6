import random
import sqlite3
from typing import Optional, List

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker


class RowidReader(QThread):
    # Señal para emitir nuevos rowids
    rowids_received = Signal(list)
    # Señal para indicar que la lectura ha terminado
    finished_reading = Signal()
    # Señal para errores
    error_occurred = Signal(str)

    def __init__(self, path_file: str, tabla: str, parent=None):
        super().__init__(parent)
        self.path_file = path_file
        self.tabla = tabla
        self.where: Optional[str] = None
        self.order: Optional[str] = None
        self.li_row_ids: List[int] = []
        self.chunk = 2024
        self._stop_flag = False
        self._mutex = QMutex()

    def setup(self, li_row_ids: List[int], where: Optional[str], order: Optional[str]) -> None:
        """Prepara los parámetros para la lectura"""
        self.stopnow()
        self.where = where
        self.order = order
        self.li_row_ids = li_row_ids
        self._stop_flag = False

    def run(self) -> None:
        """Método principal del QThread (no llamar directamente, usar start())"""
        conexion = None
        cursor = None
        try:
            conexion = sqlite3.connect(self.path_file)
            sql = f'SELECT ROWID FROM "{self.tabla}"'
            if self.where:
                sql += f" WHERE {self.where}"
            if self.order:
                sql += f" ORDER BY {self.order}"
            else:
                sql += " ORDER BY ROWID"
            cursor = conexion.cursor()
            cursor.execute(sql)
            ch = random.randint(1000, 3000)

            while not self._stop_flag:
                li = cursor.fetchmany(ch)
                if li:
                    new_rowids = [x[0] for x in li]
                    # Usar mutex para proteger el acceso a li_row_ids
                    with QMutexLocker(self._mutex):
                        self.li_row_ids.extend(new_rowids)
                    # Emitir señal con los nuevos rowids
                    self.rowids_received.emit(new_rowids)

                    if len(li) < ch:
                        break
                else:
                    break
                ch = self.chunk

        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            self.error_occurred.emit(str(e))
        finally:
            if cursor:
                cursor.close()
            if conexion:
                conexion.close()
            self.finished_reading.emit()

    def stopnow(self) -> None:
        """Detiene la ejecución del hilo"""
        self._stop_flag = True
        if self.isRunning():
            if not self.wait(500):  # Timeout de 500ms (más agresivo)
                self.terminate()  # Forzar terminación si no responde
                self.wait(100)  # Esperar solo 100ms después de terminate

    def terminado(self) -> bool:
        """Verifica si el hilo ha terminado"""
        return not self.isRunning()

    def reccount(self) -> int:
        """Retorna el número de rowids leídos"""
        with QMutexLocker(self._mutex):
            return len(self.li_row_ids)

    def get_rowids(self) -> List[int]:
        """Retorna una copia de los rowids leídos"""
        with QMutexLocker(self._mutex):
            return self.li_row_ids.copy()

    def close(self) -> None:
        """Cierra y limpia el objeto completamente"""
        # Desconectar todas las señales PRIMERO (antes de detener el hilo)
        # para evitar que se emitan señales durante la limpieza
        try:
            self.rowids_received.disconnect()
        except (RuntimeError, TypeError):
            pass  # Ya estaba desconectado o no hay conexiones

        try:
            self.finished_reading.disconnect()
        except (RuntimeError, TypeError):
            pass

        try:
            self.error_occurred.disconnect()
        except (RuntimeError, TypeError):
            pass

        # Ahora detener el hilo
        self.stopnow()
