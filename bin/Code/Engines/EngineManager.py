import os
from typing import Callable, Optional

from PySide6 import QtCore

import Code
from Code import Util
from Code.Engines import EngineResponse, EngineRun, Engines, Priorities
from Code.SQL import UtilSQL


class EngineManager:
    def __init__(self, engine, run_engine_params: EngineRun.RunEngineParams, with_cache: bool):

        self.engine_run: Optional[EngineRun.EngineRun] = None
        self.engine: Engines.Engine = engine

        self.starting_the_engine = False
        self.multipv: int = engine.multiPV
        self.priority: int = Priorities.priorities.normal

        self.run_engine_params = run_engine_params

        self.is_canceled = False
        self.elapsed_time = QtCore.QElapsedTimer()

        self.fichero_log: Optional[str] = None

        self.mrm: Optional[EngineResponse.MultiEngineResponse] = None
        self.bestmove: Optional[str] = None
        self.depthchanged_connected_to: Optional[Callable] = None
        self.bestmove_connected_to: Optional[Callable] = None

        self.ms_refresh: int = 325

        self.cache_analysis = UtilSQL.DictBig() if with_cache else None

        self.enabled_emit_depth_changed = False
        self.enabled_emit_bestmove_found = False

        self.is_closed = False
        self.is_disabled = False  # util al analizar un movimiento que se espera hasta que termine

        self.active_loop: Optional[QtCore.QEventLoop] = None

        self.huella = Util.huella()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def disable(self):
        self.is_disabled = True

    def change_multipv(self, multipv: int):
        self.run_engine_params.multipv = multipv
        if self.engine_run:
            self.engine_run.set_multipv(multipv)

    def set_option(self, name, value):
        if self.check_engine():
            self.engine_run.set_option(name, value)

    def set_priority_very_low(self):
        self.priority = Priorities.priorities.verylow

    def set_priority(self, priority: int):
        self.priority = priority

    @QtCore.Slot()
    def depth_changed(self):
        if (
            self.enabled_emit_depth_changed
            and self.depthchanged_connected_to is not None
            and self.engine_run is not None
            and self.engine_run.mrm is not None
        ):
            mrm = self.engine_run.get_mrm()
            if mrm:
                mrm = mrm.clone()
                if self.depthchanged_connected_to(mrm) is False:
                    self.engine_run.stop()

    def connect_depthchanged(self, rutina):
        self.depthchanged_connected_to = rutina
        self.enabled_emit_depth_changed = rutina is not None

    @QtCore.Slot()
    def bestmove_found(self, bestmove):
        self.bestmove = bestmove
        if (
            self.enabled_emit_bestmove_found
            and self.bestmove_connected_to is not None
            and self.engine_run
            and self.engine_run.mrm
        ):
            self.bestmove_connected_to(bestmove)

    def connect_bestmove(self, rutina):
        self.bestmove_connected_to = rutina
        self.enabled_emit_bestmove_found = rutina is not None

    def disconnect(self):
        self.bestmove_connected_to = None
        self.depthchanged_connected_to = None
        self.enabled_emit_depth_changed = False
        self.enabled_emit_bestmove_found = False

    def check_engine(self) -> bool:
        if self.starting_the_engine:
            return True
        if self.engine_run is not None:
            return True

        self.starting_the_engine = True

        if __debug__:
            from Code import Debug

            Debug.prln(f"EngineManager.open called for {self.engine.name} {self.huella}", color="yellow")

        config_enginerun = EngineRun.StartEngineParams()
        config_enginerun.name = self.engine.name
        config_enginerun.path_exe = self.engine.ejecutable()
        config_enginerun.args = self.engine.argumentos()
        config_enginerun.li_options_uci = self.engine.liUCI
        if self.engine.emulate_movetime:
            config_enginerun.emulate_movetime = True

        self.engine_run = EngineRun.EngineRun(config_enginerun)
        if self.engine_run.state == EngineRun.EngineState.INVALID_ENGINE:
            self.starting_the_engine = False
            self.close()
            return False
        self.engine_run.bestmove_found.connect(self.bestmove_found)
        self.engine_run.depth_changed.connect(self.depth_changed)

        Code.list_engine_managers.append(self)

        if self.multipv > 0:
            self.engine_run.set_multipv(self.multipv)

        self.starting_the_engine = False
        return True

    def stop(self):
        if self.engine_run:
            if __debug__:
                from Code import Debug

                Debug.prln(f"EngineManager.stop() called for {self.engine.name}", color="yellow")
            self.engine_run.stop()

    def close(self):
        if self.is_closed:
            return
        if __debug__:
            from Code import Debug

            Debug.prln(f"EngineManager.close() called for {self.engine.name} {self.huella}", color="yellow")
        self.is_closed = True

        if self.active_loop:
            try:
                self.active_loop.quit()
            except:
                pass
            self.active_loop = None

        if self.engine_run:
            try:
                self.engine_run.close()
            except:
                pass
            self.engine_run = None

        if self.cache_analysis is not None:
            try:
                self.cache_analysis.close()
            except:
                pass
            self.cache_analysis = None

    def log_open(self):
        if self.fichero_log:
            return
        carpeta = Util.opj(Code.configuration.paths.folder_userdata(), "EngineLogs")
        if not os.path.isdir(carpeta):
            Util.create_folder(carpeta)
        plantlog = f"{Util.opj(carpeta, self.engine.name)}_%05d"
        pos = 1
        nomlog = plantlog % pos

        while os.path.isfile(nomlog):
            pos += 1
            nomlog = plantlog % pos
        self.fichero_log = nomlog

        if self.engine_run:
            self.engine_run.log_open(nomlog)

    def log_close(self):
        self.fichero_log = None
        if self.engine_run:
            self.engine_run.log_close()

    def li_uci(self) -> list:
        if self.check_engine():
            return self.engine_run.li_uci
        return []

    def get_current_mrm(self) -> EngineResponse.MultiEngineResponse | None:
        if self.engine_run:
            mrm = self.engine_run.get_mrm()
            return mrm.clone() if mrm is not None else None
        return None

    def is_run_fixed(self):
        return self.run_engine_params.is_fixed()

    def is_run_fast(self):
        return self.run_engine_params.is_fast()
