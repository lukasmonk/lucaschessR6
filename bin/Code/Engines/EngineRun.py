import contextlib
import os
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import List, Optional

import psutil
from PySide6 import QtCore

import Code
from Code.Base import Game
from Code.Engines import EngineResponse, Priorities
from Code.Z import Util, Debug

if __debug__:
    prln = Debug.prln


@dataclass
class StartEngineParams:
    name: str = ""
    path_exe: str = ""
    li_options_uci: Optional[list] = None
    num_multipv: int = 0
    priority: Optional[int] = None
    args: Optional[list] = None
    path_log: Optional[str] = None
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
        self.multipv = engine.multiPV
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
    READING_UCI = auto()
    READING_EVAL_STOCKFISH = auto()
    READING_MATE_STOCKFISH = auto()
    INVALID_ENGINE = auto()
    PENDING_READYOK = auto()
    CLOSED = auto()


class StreamLineProcessor:
    def __init__(self):
        self._pending = ""

    def convert(self, salida_bytes: QtCore.QByteArray) -> List[str]:
        salida_str = salida_bytes.data().decode("utf-8", errors="ignore")
        salida_str = self._pending + salida_str
        self._pending = ""
        lineas = salida_str.splitlines()
        if not salida_str.endswith("\n"):
            self._pending = lineas.pop() if lineas else salida_str
        return lineas


class EngineRun(QtCore.QObject):
    depth_changed = QtCore.Signal()
    bestmove_found = QtCore.Signal(str)
    eval_stockfish_found = QtCore.Signal(str)
    engine_terminated = QtCore.Signal()

    # Atributos de instancia — se inicializan en __init__

    def __init__(self, config: StartEngineParams):
        super().__init__()

        # Atributos de instancia
        self.is_white = False
        self.last_depth_emit: int = 0
        self.last_time_depth_emit: int = 0
        self.time_interval_depth_emit: int = 500
        self.timerstop: Optional[QtCore.QTimer] = None

        self.control_ponder: None | Ponder = None

        if __debug__:
            if Debug.DEBUG_ENGINES or Debug.DEBUG_ENGINES_SEND:
                self.color_debug = "green" if "stock" in config.name.lower() else "cyan"

        self.config = config
        self._wait_loop: Optional[QtCore.QEventLoop] = None
        self.stream_line_processor = StreamLineProcessor()

        self.mode_timer_poll = Code.configuration.x_msrefresh_poll_engines > 0 and not config.faster_mode_always

        if self.mode_timer_poll:
            # Configuración del Timer de Polling (Queue virtual)
            # Se inicia solo cuando es necesario leer.
            self._timer_poll = QtCore.QTimer()
            mstimer_poll = Util.clamp(Code.configuration.x_msrefresh_poll_engines, 20, 500)
            self._timer_poll.setInterval(mstimer_poll)  # Revisar cada x ms
            self._timer_poll.timeout.connect(self._poll_output)

        self.process: Optional[QtCore.QProcess] = QtCore.QProcess(self)

        if not self.mode_timer_poll:
            self.process.readyReadStandardOutput.connect(self._read_output)

        self.process.finished.connect(self._engine_terminated)

        self.state = EngineState.OFF
        self.process.setWorkingDirectory(os.path.dirname(self.config.path_exe))
        args = self.config.args or []
        self.process.start(self.config.path_exe, arguments=args)

        if not self.process.waitForStarted(10000):
            self.state = EngineState.INVALID_ENGINE
            try:
                self.process.kill()
            except Exception:
                self._log_exception("Process kill failed")
            self.process = None
            return
        self.state = EngineState.STARTED

        # set priority if requested
        if self.config.priority is not None:
            try:
                p = psutil.Process(int(self.process.processId()))
                p.nice(Priorities.priorities.value(self.config.priority))
            except Exception:
                self._log_exception("Set priority failed")

        self.mrm: Optional[EngineResponse.MultiEngineResponse] = None

        self.log = None
        if self.config.path_log:
            self._log_open(self.config.path_log)

        self.li_uci: List[str] = []
        self.li_cache: List[str] = []
        self.uci_ok = False

        # Iniciar lectura de UCI
        self._read_uci()

        if config.li_options_uci:
            self._set_options_uci(config.li_options_uci)
        if config.num_multipv > 0:
            self.set_multipv(config.num_multipv)

        self._ucinewgame()
        self.play_time_begin = None
        self.emit = True

    def _start_polling(self):
        """Activa la lectura periódica si no está activada."""
        timer = getattr(self, "_timer_poll", None)
        if timer is not None and not timer.isActive():
            timer.start()

    def _stop_polling(self):
        """Detiene la lectura periódica."""
        timer = getattr(self, "_timer_poll", None)
        if timer is not None and timer.isActive():
            timer.stop()

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
            self.log.write(f"{str(Util.today())}       {'-' * 70}\n\n")
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

        # Asegurar que esté muerto (solo para el padre)
        if including_parent:
            try:
                if parent.is_running():
                    parent.kill()
                    parent.wait(timeout=1)
            except Exception:
                pass

    # --- protected send command ---
    def _send_command(self, command: str) -> bool:
        try:
            if self.process is None:
                return False
            try:
                running = self.process.state() == QtCore.QProcess.ProcessState.Running
            except (RuntimeError, AttributeError):
                return False

            if running:
                try:
                    self.process.write(f"{command}\n".encode("utf-8"))

                    if self.control_ponder:
                        self.control_ponder.check_command(command)
                except (RuntimeError, OSError) as e:
                    self._log_exception(f"write failed [{self.config.name}] '{command}': {e}")
                    return False

                if __debug__ and Debug.DEBUG_ENGINES_SEND:
                    Debug.prln(f"->{self.config.name}: {command}")
                if self.log is not None:
                    try:
                        self.log.write(f"-> {command}\n")
                    except Exception:
                        self._log_exception("Log write failed")
                return True
            return False
        except Exception:
            self._log_exception("Unexpected _send_command error")
            return False

    # --- read output safely ---
    @QtCore.Slot()
    def _read_output(self):
        try:
            if self.process is None:
                return
            try:
                output = self.process.readAllStandardOutput()
                if not self.emit:
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
                    if __debug__ and Debug.DEBUG_ENGINES:
                        Debug.prln(f"{self.config.name}: {line}")
                    if self.log is not None:
                        try:
                            self.log.write(f"{line}\n")
                        except Exception:
                            self._log_exception("Log write line failed")

                    st = self.state

                    if st == EngineState.READING_UCI:
                        if line == "uciok":
                            self.state = EngineState.OK
                            if self.mode_timer_poll:
                                # APAGAMOS POLLING
                                self._stop_polling()
                            if self._wait_loop:
                                self._wait_loop.quit()
                        else:
                            if line.startswith(("id ", "option ")):
                                self.li_uci.append(line.strip())

                    elif st == EngineState.PENDING_READYOK:
                        if line == "readyok":
                            self.state = EngineState.OK
                            if self.mode_timer_poll:
                                # APAGAMOS POLLING
                                self._stop_polling()

                            if self._wait_loop:
                                self._wait_loop.quit()

                    elif st == EngineState.READING_EVAL_STOCKFISH:
                        self.li_cache.append(line)
                        if line.startswith("Final "):
                            self.state = EngineState.OK
                            if self.mode_timer_poll:
                                # APAGAMOS POLLING
                                self._stop_polling()

                            if self.emit:
                                try:
                                    self.eval_stockfish_found.emit("\n".join(self.li_cache))
                                except Exception:
                                    self._log_exception("eval_stockfish_found emit failed")
                            self.li_cache = []

                    elif st == EngineState.THINKING:
                        emited_depth = False
                        new_depth = 0
                        current_time = int(time.time() * 1000)
                        if self.mrm is not None:
                            try:
                                self.mrm.dispatch(line)
                            except Exception:
                                self._log_exception("mrm.dispatch error")
                            new_depth = self.mrm.get_current_depth()
                            if new_depth > self.last_depth_emit:
                                self.mrm.ordena()
                                if self.emit:
                                    if current_time - self.last_time_depth_emit >= self.time_interval_depth_emit:
                                        self.last_depth_emit = new_depth
                                        self.last_time_depth_emit = current_time
                                        try:
                                            self.depth_changed.emit()
                                            emited_depth = True
                                        except Exception:
                                            self._log_exception("depth_changed emit failed")

                        if line.startswith("bestmove"):
                            self.state = EngineState.OK
                            if self.mode_timer_poll:
                                # APAGAMOS POLLING
                                self._stop_polling()

                            li = line.split(" ")
                            self.bestmove = li[1] if len(li) > 1 else ""
                            if self.emit:
                                try:
                                    if not emited_depth:  # si no se ha emitido el depth, lo emitimos
                                        self.last_depth_emit = new_depth
                                        self.last_time_depth_emit = current_time
                                        self.depth_changed.emit()  # sino no se ve la ultima depth
                                    self.bestmove_found.emit(self.bestmove)
                                except Exception:
                                    self._log_exception("bestmove_found emit failed")

                            if self.control_ponder and self.bestmove:
                                self.control_ponder.received_bestmove(line)
                except Exception:
                    self._log_exception("Unhandled error processing engine line")
                    continue
        except Exception:
            self._log_exception("Critical error in _read_output")

    # --- terminated handler ---
    @QtCore.Slot(int, QtCore.QProcess.ExitStatus)
    def _engine_terminated(self, exit_code: int, exit_status: QtCore.QProcess.ExitStatus):
        try:
            self.state = EngineState.OFF
            if self.mode_timer_poll:
                # APAGAMOS POLLING
                self._stop_polling()

            if self._wait_loop:
                try:
                    self._wait_loop.quit()
                except Exception:
                    self._log_exception("wait_loop quit failed")
            if self.emit:
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

    # --- wait helper ---
    def _wait_for(self, command: str, wait_state: EngineState, timeout_ms: int = 3000) -> bool:
        self.state = wait_state

        self._wait_loop = QtCore.QEventLoop()

        if self.mode_timer_poll:
            # ACTIVAR POLLING para esperar la respuesta
            self._start_polling()

        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(self._wait_loop.quit)
        timer.start(timeout_ms)
        QtCore.QTimer.singleShot(0, lambda: self._send_command(command))

        # ELIMINADO: QtCore.QCoreApplication.processEvents()  # Causa reentrancia peligrosa
        self._wait_loop.exec()
        timer.stop()

        ok = self.state == EngineState.OK
        if self.mode_timer_poll:
            # Si salimos por timeout, apagar polling manualmente
            if not ok:
                self._stop_polling()

        self._wait_loop = None
        return ok

    def _read_uci(self) -> str:
        self.uci_ok = self._wait_for("uci", EngineState.READING_UCI)
        return "\n".join(self.li_uci)

    # --- public API ---
    def path_exe(self):
        return self.config.path_exe

    def uci_lines(self):
        return self.li_uci

    def isready(self):
        return self._wait_for("isready", EngineState.PENDING_READYOK)

    def log_open(self, file):
        self._log_open(file)

    def log_close(self):
        self._log_close()

    def stop(self):
        try:
            self._timerstop_off()
            is_pondering = self.control_ponder and self.control_ponder.ponder
            if self.state not in (EngineState.OFF, EngineState.OK) or is_pondering:
                self._send_command("stop")
        except Exception:
            self._log_exception("Error in stop()")

    def time_played(self):
        return (time.time() - self.play_time_begin) if self.play_time_begin else 0.0

    def set_multipv(self, num_multipv: int):
        self._set_option("MultiPV", str(num_multipv))

    def set_option(self, option: str, value: str):
        self._set_option(option, value)

    def _set_option(self, option, value):
        if value:
            self._send_command(f"setoption name {option} value {value}")
            if option == "Ponder" and value == "true":
                self.control_ponder = Ponder(self, self._send_command,
                                             self._start_polling if self.mode_timer_poll else None)
        else:
            self._send_command(f"setoption name {option}")

    def _set_options_uci(self, li_options_uci):
        for opcion, valor in li_options_uci:
            if isinstance(valor, bool):
                valor = str(valor).lower()
            self._set_option(opcion, valor)

    def _ucinewgame(self):
        self._timerstop_off()
        self._send_command("ucinewgame")

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
            self.timerstop = QtCore.QTimer()
            self.timerstop.setSingleShot(True)
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

    def stop_and_wait(self, timeout_ms: int = 3000) -> bool:
        try:
            self._send_command("stop")
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
        self.emit = False

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

        # Terminar bucles de eventos pendientes
        if self._wait_loop:
            try:
                self._wait_loop.quit()
            except Exception:
                self._log_exception("wait_loop quit failed")

        # Bloquear señales para evitar eventos durante el cierre
        with contextlib.suppress(RuntimeError, AttributeError):
            self.blockSignals(True)
        self.state = EngineState.OFF

        # Detener timer si existe
        try:
            self._timerstop_off(True)
        except Exception:
            self._log_exception("timerstop_off failed")

        # Desconectar señales Qt
        if self.process is not None:
            try:
                if self.mode_timer_poll:
                    self._safe_disconnect(self.process.finished, self._engine_terminated)
                else:
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
                        self._send_command("quit")
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

        # Limpiar referencias
        self.process = None

        # Desbloquear señales
        try:
            self.blockSignals(False)
        except Exception:
            self._log_exception("blockSignals failed")
        self.state = EngineState.CLOSED

    # --- positions / play ---
    def set_game_position(self, game: Game.Game, movement: Optional[int], pre_move: bool):
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
            self._send_command(order)

    def set_fen_position(self, fen: str):
        self.stop()
        self.isready()
        self.is_white = fen.split()[1] == "w"
        order = f"position fen {fen}"

        if self.control_ponder:
            self.control_ponder.send_command(order)
        else:
            self._send_command(order)

    def play(self, run_engine_params: RunEngineParams):

        def send_go(args: str):
            self.last_depth_emit = 0
            self.last_time_depth_emit = 0

            self.play_time_begin = time.time()
            self.state = EngineState.THINKING

            if self.mode_timer_poll:
                # ACTIVAMOS POLLING
                self._start_polling()

            xorder = f"go {args}"

            if self.control_ponder:
                self.control_ponder.send_command(xorder)
            else:
                self._send_command(xorder)

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

        if run_engine_params.timems_white > 0:
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
        self.set_fen_position(fen)
        self.li_cache = []
        self.state = EngineState.READING_EVAL_STOCKFISH

        if self.mode_timer_poll:
            # ACTIVAMOS POLLING
            self._start_polling()

        self._send_command("eval")


class Ponder:
    def __init__(self, engine_run: EngineRun, send_command_engine: Callable, start_polling: Callable | None):
        self.engine_run: EngineRun = engine_run
        self._send_command_engine: Callable = send_command_engine
        self._start_polling: Callable | None = start_polling  # si es none es porque el mode no es polling
        self.last_position_sent = ""
        self.last_go_sent = ""
        self.last_time = 0
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
            self.last_time = time.time()
        elif command.startswith('stop'):
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
                command = f'{self.last_position_sent} moves'
            else:
                command = self.last_position_sent
            command_position = f'{command.strip()} {li[1]} {li[3]}'

            li_go = self.last_go_sent.split()
            if "wtime" in self.last_go_sent:
                try:
                    mstime_used = int((time.time() - self.last_time) * 1000)
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
