import contextlib
import os
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum, auto

import psutil
from PySide6 import QtCore

import Code
from Code.Base import Game
from Code.Engines import EngineResponse, Priorities
from Code.Z import Util

if __debug__:
    from Code.Z import Debug

    prln = Debug.prln


@dataclass
class StartEngineParams:
    name: str = ""
    path_exe: str = ""
    li_options_uci: list | None = None
    num_multipv: int = 0
    priority: int | None = None
    args: list | None = None
    path_log: str | None = None
    emulate_movetime: bool = False
    faster_mode_always: bool = False


@dataclass
class RunEngineParams:
    timems_white: int = 0
    timems_black: int = 0
    inc_timems_move: int = 0
    fixed_ms: int = 0
    fixed_depth: int = 0
    fixed_nodes: int = 0
    multipv: int = 1
    infinite: bool = False

    def clone(self) -> "RunEngineParams":
        return replace(self)

    def update_from_engine(self, engine):
        self.fixed_ms = int(engine.max_time * 1000)
        self.fixed_depth = engine.max_depth
        if engine.min_fixed_depth > 0 and 0 < self.fixed_depth < engine.min_fixed_depth:
            self.fixed_depth = engine.min_fixed_depth
        self.fixed_nodes = engine.nodes
        self.multipv = engine.multiPV

    def update(self, engine, fixed_ms: int, fixed_depth: int, fixed_nodes: int, multipv: int | str):
        engine.set_multipv_var(multipv)
        if engine.min_fixed_depth > 0 and 0 < fixed_depth < engine.min_fixed_depth:
            fixed_depth = engine.min_fixed_depth

        self.fixed_ms = int(fixed_ms)
        self.fixed_depth = fixed_depth
        self.fixed_nodes = fixed_nodes
        self.multipv = int(multipv) if isinstance(multipv, (int, str)) and str(multipv).isdigit() else engine.multiPV
        if self.fixed_ms == 0 and self.fixed_depth == 0 and self.fixed_nodes == 0:
            self.infinite = True

    def update_var_time(self, time_secs_white, time_secs_black, inc_time_secs_move):
        self.timems_white = int(time_secs_white * 1000)
        self.timems_black = int(time_secs_black * 1000)
        self.inc_timems_move = int(inc_time_secs_move * 1000)

    def is_fixed(self):
        return self.fixed_ms > 0 or self.fixed_depth > 0 or self.fixed_nodes > 0

    def is_fast(self):
        return 0 < self.fixed_ms < 2000 or 0 < self.fixed_depth < 8 or 0 < self.fixed_nodes < 5000


class EngineState(Enum):
    OFF = auto()
    STARTED = auto()
    OK = auto()
    THINKING = auto()
    ERROR = auto()
    READING_EVAL_STOCKFISH = auto()
    READING_MATE_STOCKFISH = auto()
    INVALID_ENGINE = auto()
    PENDING_UCIOK = auto()
    PENDING_READYOK = auto()
    CLOSED = auto()


_PENDING_MAX_BYTES = 65536

# Tiempo máximo (ms) para esperar "uciok" tras "uci" o "readyok" tras "isready".
# Si se supera, se considera que el motor no responde y se pasa a EngineState.ERROR.
_HANDSHAKE_TIMEOUT_MS = 8000


class StreamLineProcessor:
    def __init__(self):
        self._pending = ""

    def convert(self, salida_bytes: QtCore.QByteArray) -> list[str]:
        salida_str = salida_bytes.data().decode("utf-8", errors="ignore")
        salida_str = self._pending + salida_str
        self._pending = ""
        lineas = salida_str.splitlines()
        if not salida_str.endswith("\n"):
            self._pending = lineas.pop() if lineas else salida_str
            if len(self._pending) > _PENDING_MAX_BYTES:
                self._pending = ""
        return lineas


class EngineRun(QtCore.QObject):
    depth_changed = QtCore.Signal()
    bestmove_found = QtCore.Signal(str)
    eval_stockfish_found = QtCore.Signal(str)
    engine_terminated = QtCore.Signal()
    engine_error = QtCore.Signal(str)  # emitida si el motor no responde a "uci"/"isready" a tiempo

    def __init__(self, config: StartEngineParams):
        super().__init__()

        # Atributos de instancia
        self.is_white = False
        self.last_depth_emit: int = 0
        self.last_time_depth_emit: int = 0
        self.time_interval_depth_emit: int = 500
        self.timerstop: QtCore.QTimer | None = None
        self.handshake_timeout: QtCore.QTimer | None = None  # para readyok y uciok

        self.log = None
        if config.path_log:
            self._log_open(config.path_log)

        self.control_ponder: None | Ponder = None

        if __debug__:
            if Debug.DEBUG_ENGINES or Debug.DEBUG_ENGINES_SEND:
                self.color_debug = "green" if "stock" in config.name.lower() else "cyan"

        self.config = config
        self.stream_line_processor = StreamLineProcessor()

        self.mode_timer_poll = Code.configuration.x_msrefresh_poll_engines > 0 and not config.faster_mode_always

        if self.mode_timer_poll:
            # Configuración del Timer de Polling (Queue virtual)
            # Se inicia solo cuando es necesario leer.
            self._timer_poll = QtCore.QTimer(self)
            mstimer_poll = Util.clamp(Code.configuration.x_msrefresh_poll_engines, 20, 500)
            self._timer_poll.setInterval(mstimer_poll)  # Revisar cada x ms
            self._timer_poll.timeout.connect(self._poll_output)
        else:
            self._timer_poll = None

        self.process: QtCore.QProcess | None = QtCore.QProcess(self)

        if not self.mode_timer_poll:
            # noinspection PyUnresolvedReferences
            self.process.readyReadStandardOutput.connect(self._read_output)

        # noinspection PyUnresolvedReferences
        self.process.finished.connect(self._engine_terminated)

        self.state = EngineState.OFF
        self.bestmove = ""

        path_exe = os.path.abspath(self.config.path_exe)
        engine_dir = os.path.dirname(path_exe)

        self.process.setWorkingDirectory(engine_dir)
        args = self.config.args or []

        if Util.is_posix():
            if os.path.isfile(path_exe) and not os.access(path_exe, os.X_OK):
                import stat

                try:
                    current_mode = os.stat(path_exe).st_mode
                    os.chmod(path_exe, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    if __debug__:
                        Debug.prln(f"{path_exe} Permission execution added", color="yellow")
                except Exception:
                    self._log_exception(f"Could not add execution permission to {path_exe}")

            # para los motores linux que cargan librerías
            # (macOS uses DYLD_LIBRARY_PATH for the same purpose)
            var_library_path = "DYLD_LIBRARY_PATH" if Util.is_macos() else "LD_LIBRARY_PATH"
            env = QtCore.QProcessEnvironment.systemEnvironment()
            if env.contains(var_library_path):
                new_path = f"{engine_dir}:{env.value(var_library_path)}"
            else:
                new_path = engine_dir
            env.insert(var_library_path, new_path)
            self.process.setProcessEnvironment(env)

        # Acumula ordenes mientras está pendiente un uciok o readyok
        self.cmd_queue: list[tuple[str, EngineState]] = []

        # Atributos que deben existir siempre, incluso si el motor no llega a arrancar
        # (estado INVALID_ENGINE más abajo), para que get_mrm(), uci_lines(),
        # time_played(), play(), etc. no fallen con AttributeError si se invocan
        # sobre una instancia cuyo proceso no pudo iniciarse.
        self.mrm: EngineResponse.MultiEngineResponse | None = None
        self.li_uci: list[str] = []
        self.li_cache: list[str] = []
        self.play_time_begin = None
        self.emit_enabled = True

        self.process.start(path_exe, arguments=args)

        size = Util.filesize(path_exe)
        # Timeout proporcional al tamaño del binario: más tiempo para binarios grandes.
        # Mínimo 10s; ~1s adicional por cada 500 KB por encima de 5 MB.
        ms = max(10000, size * 10000 // 5000000)

        if not self.process.waitForStarted(ms):
            self.state = EngineState.INVALID_ENGINE
            try:
                self.process.kill()
            except Exception:
                self._log_exception("Process kill failed")
            self.process = None
            return
        self._state = EngineState.STARTED
        self.state = EngineState.STARTED

        # set priority if requested
        if self.config.priority is not None:
            try:
                p = psutil.Process(int(self.process.processId()))
                p.nice(Priorities.priorities.value(self.config.priority))
            except Exception:
                self._log_exception("Set priority failed")

        # Iniciar lectura de UCI
        # Los comandos enviados antes de recibir "uciok" se encolan en self.li_waiting
        # y se vuelcan al proceso cuando llega "uciok". Evita que motores estrictos
        # descarten setoption/ucinewgame recibidos antes del handshake, sin bloquear
        # la GUI (los motores lentos en responder uciok simplemente reciben todo al final).
        self.state = EngineState.OK
        if self.mode_timer_poll:
            self._start_polling()
        self._send_command("uci", EngineState.PENDING_UCIOK)  # para los motores que han de decidir si uci o WinBoard

        if config.li_options_uci:
            self._set_options_uci(config.li_options_uci)
        if config.num_multipv > 0:
            self.set_multipv(config.num_multipv)

        self._ucinewgame()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    def _start_polling(self):
        """Activa la lectura periódica si no está activada."""
        if self._timer_poll is not None and not self._timer_poll.isActive():
            self._timer_poll.start()

    def _stop_polling(self):
        """Detiene la lectura periódica."""
        if self._timer_poll is not None and self._timer_poll.isActive():
            self._timer_poll.stop()

    def is_waiting_handshake(self):
        return self.state in (EngineState.PENDING_UCIOK, EngineState.PENDING_READYOK)

    @QtCore.Slot()
    def _poll_output(self):
        """Llamado por el timer. Si hay datos, procesa."""
        if self.process is not None:
            try:
                if self.process.bytesAvailable() > 0:
                    self._read_output()
            except Exception:
                self._log_exception("Poll output error")

    # --- logging ---
    def _log_open(self, file: str):
        try:
            self.log = open(file, "at", encoding="utf-8")
            self.log.write(f"{Util.today()!s}       {'-' * 70}\n\n")
        except Exception:
            self._log_exception("Log open failed")
            self.log = None

    def _log_close(self):
        if self.log:
            try:
                self.log.close()
            except Exception:
                self._log_exception("Log close failed")
            self.log = None

    # --- utils ---
    @staticmethod
    def _safe_disconnect(signal, slot):
        try:
            signal.disconnect(slot)
        except Exception:
            pass

    @staticmethod
    def _log_exception(context: str, color=None):
        """
        Registra la excepción y su traceback solo en modo debug.
        ⚠️ Debe invocarse SIEMPRE dentro de un bloque `except`.
        """
        if __debug__:
            xcolor = "red" if color is None else color
            Debug.prln(f"{context}:\n{traceback.format_exc()}", color=xcolor)

    def _kill_process_tree(self, pid: int, including_parent: bool = True, timeout: int = 3):
        """
        Cierra un proceso y sus hijos de manera segura.

        Args:
            pid: ID del proceso a cerrar
            including_parent: Si True, también cierra el proceso padre
            timeout: Tiempo en segundos para esperar cierre normal antes de forzar
        """
        try:
            parent = psutil.Process(pid)
        except psutil.NoSuchProcess:
            # El proceso ya no existe
            return
        except psutil.AccessDenied:
            self._log_exception(f"AccessDenied al acceder al proceso {pid}", color="yellow")
            return
        except Exception:
            self._log_exception(f"Error al obtener proceso {pid}: {traceback.format_exc()}")
            return

        # Verificar si el proceso ya está terminado
        try:
            if not parent.is_running():
                return
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

        # Obtener todos los procesos hijos
        children = []
        with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            children = parent.children(recursive=True)

        # Primero intentar cierre normal de los hijos
        for child in children:
            try:
                if child.is_running():
                    child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            except Exception:
                self._log_exception(
                    f"Error al finalizar proceso hijo {child.pid}: {traceback.format_exc()}", color="yellow"
                )

        # Esperar a que los hijos terminen
        gone, alive = psutil.wait_procs(children, timeout=timeout)

        # Forzar cierre de los que siguen vivos
        for child in alive:
            try:
                if child.is_running():
                    child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            except Exception:
                self._log_exception(
                    f"Error al matar proceso hijo {child.pid}: {traceback.format_exc()}", color="yellow"
                )

        # Ahora cerrar el proceso padre si se solicita
        if including_parent:
            try:
                if parent.is_running():
                    parent.terminate()
                    # Esperar cierre
                    parent.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                # Si no termina a tiempo, forzar
                try:
                    parent.kill()
                    parent.wait(timeout=1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                except Exception:
                    self._log_exception(f"Error al matar proceso padre {pid}: {traceback.format_exc()}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            except Exception:
                self._log_exception(f"Error al finalizar proceso padre {pid}: {traceback.format_exc()}")

    # --- protected send command ---
    def _send_command(self, command: str, state: EngineState) -> bool:
        """Encola el comando y procesa la cola."""
        if self.state == EngineState.CLOSED or self.process is None:
            self.cmd_queue.clear()
            return False
        self.cmd_queue.append((command, state))
        return self._process_queue()

    def _process_queue(self) -> bool:
        """Procesa y escribe en el motor las órdenes encoladas mientras no haya un handshake pendiente."""
        if not self.cmd_queue or self.process is None:
            return False

        while self.cmd_queue and not self.is_waiting_handshake():
            command, state = self.cmd_queue.pop(0)

            self.state = state
            success = self._write_command(command)
            if not success:
                return False
            if state in (EngineState.PENDING_UCIOK, EngineState.PENDING_READYOK):
                self._handshake_timeout_run()
                self._start_polling()
                return True
            elif command.startswith("go "):
                self._start_polling()
                return True

        return True

    def _write_command(self, command: str) -> bool:
        """Escribe directamente en el stdin del proceso QProcess."""
        try:
            if self.process is None:
                return False
            running = self.process.state() == QtCore.QProcess.ProcessState.Running

            if running:
                self.process.write(f"{command}\n".encode())

                if self.control_ponder:
                    self.control_ponder.check_command(command)

                if __debug__ and Debug.DEBUG_ENGINES_SEND:
                    Debug.prln(f"->{self.config.name}: {command} {self.state}")
                    Debug.prln(f"->{self.cmd_queue=}")
                if self.log is not None:
                    try:
                        self.log.write(f"-> {command}\n")
                    except Exception:
                        self._log_exception("Log write failed")
                return True
            return False
        except Exception:
            self._log_exception("Unexpected _write_command error")
            return False

    # --- Procesamiento de Respuestas del Motor ---

    def _process_line(self, line: str):
        if __debug__ and Debug.DEBUG_ENGINES:
            Debug.prln(f"{self.config.name}: {line} {self.state}")

        if self.log is not None:
            try:
                self.log.write(f"{line}\n")
            except Exception:
                self._log_exception("Log write line failed")

        st = self.state
        if st == EngineState.PENDING_UCIOK:
            self._handle_reading_uci(line)
        elif st == EngineState.PENDING_READYOK:
            self._handle_pending_readyok(line)
        elif st == EngineState.READING_EVAL_STOCKFISH:
            self._handle_eval_stockfish(line)
        elif st == EngineState.THINKING:
            self._handle_thinking(line)

    def _handle_reading_uci(self, line: str):
        line = line.strip()
        if line == "uciok":
            self._handshake_timeout_off()
            self.state = EngineState.OK
            self._process_queue()  # Procesa los comandos acumulados durante el uciok
        elif line.startswith(("id ", "option ")):
            self.li_uci.append(line)

    def _handle_pending_readyok(self, line: str):
        line = line.strip()
        if line == "readyok":
            self._handshake_timeout_off()
            self.state = EngineState.OK
            self._process_queue()

    # --- read output safely ---
    @QtCore.Slot()
    def _read_output(self):
        try:
            if self.process is None:
                return
            try:
                output = self.process.readAllStandardOutput()
                if not self.emit_enabled:
                    return
            except (RuntimeError, AttributeError):
                return
            except Exception as e:
                self._log_exception(f"readAllStandardOutput failed: {e}")
                return

            if output.isEmpty():
                return

            lines = self.stream_line_processor.convert(output)
            for line in lines:
                try:
                    self._process_line(line)
                except Exception:
                    self._log_exception("Unhandled error processing engine line")
                    continue
        except Exception:
            self._log_exception("Critical error in _read_output")

    def _handle_eval_stockfish(self, line: str):
        self.li_cache.append(line)
        if line.startswith("Final "):
            self.state = EngineState.OK
            if self.mode_timer_poll:
                self._stop_polling()
            if self.emit_enabled:
                try:
                    self.eval_stockfish_found.emit("\n".join(self.li_cache))
                except Exception:
                    self._log_exception("eval_stockfish_found emit failed")
            self.li_cache = []

    def _handle_thinking(self, line: str):
        emited_depth = False
        new_depth = 0
        current_time = int(time.monotonic() * 1000)
        if self.mrm is not None:
            try:
                self.mrm.dispatch(line)
            except Exception:
                self._log_exception("mrm.dispatch error")
            new_depth = self.mrm.get_current_depth()
            if new_depth > self.last_depth_emit:
                self.mrm.ordena()
                if self.emit_enabled:
                    if current_time - self.last_time_depth_emit >= self.time_interval_depth_emit:
                        self.last_depth_emit = new_depth
                        self.last_time_depth_emit = current_time
                        try:
                            self.depth_changed.emit()
                            emited_depth = True
                        except Exception:
                            self._log_exception("depth_changed emit failed")
        li = line.split()
        if line.startswith("bestmove") and len(li) > 1:
            self.state = EngineState.OK
            if self.mode_timer_poll:
                self._stop_polling()

            self.bestmove = li[1]
            if self.emit_enabled and self.bestmove:
                try:
                    if not emited_depth:
                        self.last_depth_emit = new_depth
                        self.last_time_depth_emit = current_time
                        self.depth_changed.emit()
                    self.bestmove_found.emit(self.bestmove)
                except Exception:
                    self._log_exception("bestmove_found emit failed")

            if self.control_ponder and self.bestmove:
                self.control_ponder.received_bestmove(line)

    # --- terminated handler ---
    @QtCore.Slot(int, QtCore.QProcess.ExitStatus)
    def _engine_terminated(self, exit_code: int, exit_status: QtCore.QProcess.ExitStatus):
        try:
            self.state = EngineState.OFF
            self._handshake_timeout_off()
            if self.mode_timer_poll:
                # APAGAMOS POLLING
                self._stop_polling()

            if self.emit_enabled:
                try:
                    self.engine_terminated.emit()
                except Exception:
                    self._log_exception("engine_terminated emit failed")
            if __debug__:
                status_msg = (
                    "normalmente" if exit_status == QtCore.QProcess.ExitStatus.NormalExit else "inesperadamente"
                )
                Debug.prln(f"process del motor terminado {status_msg} con código: {exit_code}", color="red")
        except Exception:
            self._log_exception("Error handling engine termination")

    # --- public API ---
    def path_exe(self):
        return self.config.path_exe

    def uci_lines(self):
        return self.li_uci

    def isready(self):
        self._send_command("isready", EngineState.PENDING_READYOK)

    def log_open(self, file):
        self._log_open(file)

    def log_close(self):
        self._log_close()

    def stop(self):
        try:
            self._timerstop_off()
            is_pondering = self.control_ponder and self.control_ponder.ponder
            if self.state not in (EngineState.OFF, EngineState.OK) or is_pondering:
                self._write_command("stop")
                # No se vacía toda la cola (perdería los "setoption" aún pendientes de
                # aplicar durante un handshake). Se descartan solo las órdenes que ya
                # no tienen sentido tras un stop (go, position, etc.); "setoption" se
                # conserva para que se aplique en cuanto termine el handshake.
                self.cmd_queue = [
                    (command, state) for command, state in self.cmd_queue if command.startswith("setoption")
                ]
        except Exception:
            self._log_exception("Error in stop()")

    def time_played(self):
        return (time.monotonic() - self.play_time_begin) if self.play_time_begin else 0.0

    def set_multipv(self, num_multipv: int):
        self._set_option("MultiPV", str(num_multipv))

    def set_option(self, option: str, value: str):
        self._set_option(option, value)

    def _set_option(self, option, value):
        if value:
            self._send_command(f"setoption name {option} value {value}", EngineState.OK)
            if option == "Ponder" and value == "true":
                self.control_ponder = Ponder(
                    self, self._send_command, self._start_polling if self.mode_timer_poll else None
                )
        else:
            self._send_command(f"setoption name {option}", EngineState.OK)

    def _set_options_uci(self, li_options_uci):
        for opcion, valor in li_options_uci:
            if isinstance(valor, bool):
                valor = str(valor).lower()
            self._set_option(opcion, valor)

    def _ucinewgame(self):
        self._timerstop_off()
        self._send_command("ucinewgame", EngineState.OK)

    def _timerstop_off(self, remove: bool = False):
        if self.timerstop is not None:
            try:
                if self.timerstop.isActive():
                    self.timerstop.stop()
                if remove:
                    self.timerstop = None
            except Exception:
                self._log_exception("timerstop_off failed")

    def _timerstop_run(self, mstime: int):
        if self.timerstop is None:
            self.timerstop = QtCore.QTimer(self)
            self.timerstop.setSingleShot(True)
            # noinspection PyUnresolvedReferences
            self.timerstop.timeout.connect(self._on_timeout_timerstop)
        try:
            if self.timerstop.isActive():
                self.timerstop.stop()
            self.timerstop.start(mstime)
        except Exception:
            self._log_exception("timerstop_run failed")

    @QtCore.Slot()
    def _on_timeout_timerstop(self):
        self.stop()

    # --- handshake timeout (uci -> uciok / isready -> readyok) ---
    def _handshake_timeout_off(self, remove: bool = False):
        if self.handshake_timeout is not None:
            try:
                if self.handshake_timeout.isActive():
                    self.handshake_timeout.stop()
                if remove:
                    self.handshake_timeout = None
            except Exception:
                self._log_exception("handshake_timeout_off failed")

    def _handshake_timeout_run(self, mstime: int = _HANDSHAKE_TIMEOUT_MS):
        if self.handshake_timeout is None:
            self.handshake_timeout = QtCore.QTimer(self)
            self.handshake_timeout.setSingleShot(True)
            # noinspection PyUnresolvedReferences
            self.handshake_timeout.timeout.connect(self._on_handshake_timeout)
        try:
            if self.handshake_timeout.isActive():
                self.handshake_timeout.stop()
            self.handshake_timeout.start(mstime)
        except Exception:
            self._log_exception("handshake_timeout_run failed")

    @QtCore.Slot()
    def _on_handshake_timeout(self):
        """Se dispara si el motor no respondió 'uciok'/'readyok' a tiempo."""
        if not self.is_waiting_handshake():
            return  # se resolvió justo antes de disparar; nada que hacer
        estado_esperado = self.state
        if __debug__:
            Debug.prln(
                f"{self.config.name}: timeout esperando respuesta a {estado_esperado} (motor no responde)",
                color="red",
            )
        self.cmd_queue.clear()
        self.state = EngineState.ERROR
        if self.mode_timer_poll:
            self._stop_polling()
        if self.emit_enabled:
            try:
                self.engine_error.emit(f"El motor '{self.config.name}' no respondió a tiempo ({estado_esperado.name})")
            except Exception:
                self._log_exception("engine_error emit failed")

    def stop_and_wait(self, timeout_ms: int = 3000) -> bool:
        try:
            self._send_command("stop", EngineState.OK)
            return self.process.waitForFinished(timeout_ms) if self.process else True
        except Exception:
            self._log_exception("stop_and_wait failed")
            return False

    def close(self):
        """
        Fuerza cierre inmediato asegurando que no queden procesos ni bucles de eventos colgados.
        """
        if self.state == EngineState.CLOSED:
            return
        self.emit_enabled = False

        if self.mode_timer_poll:
            # --- CRUCIAL: Parar polling antes de tocar el proceso ---
            try:
                self._stop_polling()
                if self._timer_poll:
                    self._timer_poll.stop()
                    try:
                        self._timer_poll.timeout.disconnect(self._poll_output)
                    except Exception:
                        self._log_exception("timer_poll disconnect failed")
                    self._timer_poll.setParent(None)
                    self._timer_poll.deleteLater()
            except Exception:
                self._log_exception("polling cleanup failed")
            self._timer_poll = None

        # Bloquear señales para evitar eventos durante el cierre
        with contextlib.suppress(RuntimeError, AttributeError):
            self.blockSignals(True)
        self.state = EngineState.OFF

        # Detener timer si existe
        try:
            self._timerstop_off(True)
        except Exception:
            self._log_exception("timerstop_off failed")

        # Detener timeout de handshake si existe
        try:
            self._handshake_timeout_off(True)
        except Exception:
            self._log_exception("handshake_timeout_off failed")

        # Desconectar señales Qt
        if self.process is not None:
            try:
                self._safe_disconnect(self.process.readyReadStandardOutput, self._read_output)
                self._safe_disconnect(self.process.finished, self._engine_terminated)
            except Exception:
                self._log_exception("signal disconnect failed")

        # Cerrar log
        try:
            self._log_close()
        except Exception:
            self._log_exception("log_close failed")

        # Intentar cierre del proceso
        if self.process is not None:
            try:
                pid = -1
                with contextlib.suppress(RuntimeError, AttributeError, ValueError, TypeError):
                    pid = int(self.process.processId())
                if pid > 0:
                    # Estrategia 1: Intento de cierre normal
                    try:
                        self._send_command("quit", EngineState.OK)
                    except Exception:
                        self._log_exception("quit command failed")

                    # Terminar con QProcess
                    try:
                        # Usar psutil directamente si es posible, es más fiable para forzar
                        self._kill_process_tree(pid, including_parent=True, timeout=1)
                    except (RuntimeError, AttributeError):
                        pass
                    except Exception as e:
                        if __debug__:
                            Debug.prln(f"Error en cierre con psutil: {e}", color="yellow")
            except Exception:
                self._log_exception("process close failed")

            # Cerrar QProcess internamente
            try:
                if QtCore.QCoreApplication.instance():
                    self.process.waitForFinished(200)
                self.process.close()
            except Exception:
                self._log_exception("QProcess close failed")

        self.cmd_queue.clear()

        # Limpiar referencias
        self.process = None

        # Desbloquear señales
        try:
            self.blockSignals(False)
        except Exception:
            self._log_exception("blockSignals failed")
        self.state = EngineState.CLOSED

    # --- positions / play ---
    def set_game_position(self, game: Game.Game, movement: int | None, pre_move: bool):
        self.stop()
        self.isready()
        order = "startpos" if game.is_fen_initial() else f"fen {game.first_position.fen()}"

        if movement is None:
            pv = game.pv()
            if pv:
                order += f" moves {pv}"
            self.is_white = game.is_white()
        else:
            move = game.move(movement)
            if pre_move:
                self.is_white = move.is_white()
                if movement > 0:
                    order += f" moves {game.pv_hasta(movement - 1)}"
            else:
                self.is_white = not move.is_white()
                order += f" moves {game.pv_hasta(movement)}"
        order = f"position {order}"

        if self.control_ponder:
            self.control_ponder.send_command(order)
        else:
            self._send_command(order, EngineState.OK)

    def set_fen_position(self, fen: str):
        self.stop()
        self.isready()
        self.is_white = fen.split()[1] == "w"
        order = f"position fen {fen}"

        if self.control_ponder:
            self.control_ponder.send_command(order)
        else:
            self._send_command(order, EngineState.OK)

    def play(self, run_engine_params: RunEngineParams):

        def send_go(args: str):
            self.last_depth_emit = 0
            self.last_time_depth_emit = 0

            self.play_time_begin = time.monotonic()

            if self.mode_timer_poll:
                # ACTIVAMOS POLLING
                self._start_polling()

            xorder = f"go {args}"

            if self.control_ponder:
                self.control_ponder.send_command(xorder)
            else:
                self._send_command(xorder, EngineState.THINKING)

            if run_engine_params.fixed_ms or run_engine_params.fixed_depth:
                if self.mrm:
                    self.mrm.set_time_depth(run_engine_params.fixed_ms, run_engine_params.fixed_depth)
            if run_engine_params.fixed_nodes and self.mrm:
                self.mrm.set_nodes(run_engine_params.fixed_nodes)

        self.mrm = EngineResponse.MultiEngineResponse(self.config.name, self.is_white)

        if run_engine_params.fixed_ms > 0:
            self._timerstop_run(int(run_engine_params.fixed_ms + 100))

        if run_engine_params.fixed_depth > 0:
            send_go(f"depth {run_engine_params.fixed_depth}")
            return

        if run_engine_params.fixed_nodes > 0:
            send_go(f"nodes {run_engine_params.fixed_nodes}")
            return

        if run_engine_params.fixed_ms > 0:
            if self.config.emulate_movetime:
                send_go("infinite")
                return
            send_go(f"movetime {int(run_engine_params.fixed_ms)}")
            return

        if run_engine_params.timems_white > 0 or run_engine_params.timems_black > 0:
            order = f"wtime {run_engine_params.timems_white} btime {run_engine_params.timems_black}"
            if run_engine_params.inc_timems_move:
                order += f" winc {run_engine_params.inc_timems_move} binc {run_engine_params.inc_timems_move}"
            send_go(order)
            return

        send_go("infinite")

    def set_mrm_cached(self, mrm: EngineResponse.MultiEngineResponse):
        self.mrm = mrm

    def get_mrm(self):
        return self.mrm.clone() if self.mrm else None

    def run_eval_stockfish(self, fen: str):
        """Envía el comando 'eval' a Stockfish para obtener una evaluación de la posición FEN dada.

        Método específico de Stockfish. No usar con otros motores UCI.
        Requiere que el motor esté en estado OK y que tenga habilitado el comando 'EvalFile'.
        """
        self.set_fen_position(fen)
        self.li_cache = []

        if self.mode_timer_poll:
            # ACTIVAMOS POLLING
            self._start_polling()

        self._send_command("eval", EngineState.READING_EVAL_STOCKFISH)


class Ponder:
    def __init__(self, engine_run: EngineRun, send_command_engine: Callable, start_polling: Callable | None):
        self.engine_run: EngineRun = engine_run
        self._send_command_engine: Callable = send_command_engine
        self._start_polling: Callable | None = start_polling  # si es none es porque el mode no es polling
        self.last_position_sent = ""
        self.last_go_sent = ""
        self.last_time = 0.0
        self.ponder: str = ""
        self.post_ponderhit: bool = False  # True después de enviar ponderhit, el próximo go debe descartarse
        self.lock = False  # para que no se mezclen los chequeos de las ordenes con las de la clase

    def reset(self):
        self.last_position_sent = ""
        self.last_go_sent = ""
        self.last_time = 0.0
        self.ponder: str = ""
        self.post_ponderhit: bool = False
        self.lock = False  # para que no se mezclen los chequeos de las ordenes con las de la clase

    def check_command(self, command):
        if self.lock:
            return
        elif command.startswith("position"):
            self.last_position_sent = command
        elif command.startswith("go"):
            self.last_go_sent = command
            self.last_time = time.monotonic()
        elif command.startswith("stop"):
            self.reset()

    def send_command(self, command):
        if not self.ponder:
            self._send_command_engine(command)
            return

        if command.startswith("go"):  # no se lanza el go tras ponderhit
            if self.post_ponderhit:
                # Motor ya está pensando tras ponderhit, no enviar go
                return
            self.reset()
            self._send_command_engine(command)
            return

        li = command.split()
        if li and li[-1] == self.ponder:
            self.send_command_lock("ponderhit")
            self.post_ponderhit = True  # El motor continuará pensando, no enviar próximo go
            if self._start_polling:
                self._start_polling()
        else:
            self.reset()
            self.send_command_lock("stop")
            self._send_command_engine(command)

    def send_command_lock(self, command):
        self.lock = True
        try:
            self._send_command_engine(command)
        finally:
            self.lock = False

    def received_bestmove(self, line):
        # Reset post_ponderhit cuando se recibe bestmove (motor terminó de pensar)
        self.post_ponderhit = False

        li = line.split()
        if len(li) >= 4 and li[2] == "ponder":
            self.ponder = li[3]
            if "fen" in self.last_position_sent and "moves" not in self.last_position_sent:
                command = f"{self.last_position_sent} moves"
            else:
                command = self.last_position_sent
            command_position = f"{command.strip()} {li[1]} {li[3]}"

            li_go = self.last_go_sent.split()
            if "wtime" in self.last_go_sent:
                try:
                    mstime_used = int((time.monotonic() - self.last_time) * 1000)
                    is_white = self.engine_run.is_white
                    token_time = "wtime" if is_white else "btime"
                    if token_time in li_go:
                        idx = li_go.index(token_time) + 1
                        if idx < len(li_go):
                            ms = int(li_go[idx]) - mstime_used
                            if ms <= 0:
                                ms = 1
                            li_go[idx] = str(ms)
                except Exception:
                    pass

            li_go.insert(1, "ponder")
            command_go = " ".join(li_go)

            self.send_command_lock(command_position)
            # Actualizar last_position_sent con la nueva posición enviada
            self.last_position_sent = command_position
            self.send_command_lock(command_go)

            if self._start_polling:
                self._start_polling()
