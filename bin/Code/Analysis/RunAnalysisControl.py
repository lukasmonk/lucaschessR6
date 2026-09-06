import collections
import contextlib
import os
import threading
import time

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Signal

import Code
from Code.Analysis.AnalysisGame import AnalysisGameSaveTrainings
from Code.Base.Constantes import (
    RUNA_CONFIGURATION,
    RUNA_GAME_DONE,
    RUNA_GAME_ROWID,
    RUNA_HALT,
    RUNA_PAUSE,
    RUNA_PROGRESS,
    RUNA_RESUME,
    RUNA_TERMINATE,
    TACTICTHEMES,
)
from Code.BestMoveTraining import BMT
from Code.QT import Colocacion, Controles, Iconos, LCDialog, QTMessages, ScreenUtils
from Code.SQL import UtilSQL
from Code.Z import Util, XRun


class Orden:
    def __init__(self):
        self.key = ""
        self.dv = {}

    def set(self, name, valor):
        self.dv[name] = valor

    def block(self):
        self.dv["__CLAVE__"] = self.key
        return self.dv

    def get(self, name):
        return self.dv.get(name)

    def __str__(self):
        return f"{self.key}: {self.dv}"


class IPCAnalysis:
    def __init__(self, alm, huella, path_db=None):
        self.closed = False
        self.is_paused = False
        self.huella = huella
        configuration = Code.configuration

        folder_tmp = Code.configuration.temporary_folder()
        filebase = Util.opj(folder_tmp, huella)
        file_send = f"{filebase}_send.sqlite"
        file_receive = f"{filebase}_receive.sqlite"

        self.ipc_send = UtilSQL.IPC(file_send, True)
        self.ipc_receive = UtilSQL.IPC(file_receive, True)

        orden = Orden()
        orden.key = RUNA_CONFIGURATION
        orden.set("USER", configuration.user)
        orden.set("HUELLA", huella)
        orden.set("ALM", alm)
        orden.set("SHOW_WINDOW", False)
        if path_db:
            orden.set("PATH_DB", path_db)

        self.send(orden)

        self.popen = XRun.run_lucas("-analysis", filebase)

    def send(self, orden):
        if not self.closed:
            self.ipc_send.push(orden.block())

    def receive(self):
        return self.ipc_receive.pop()

    def working(self):
        if self.popen is None or self.closed:
            return False
        return self.popen.poll() is None

    def _send_orden(self, key):
        orden = Orden()
        orden.key = key
        self.send(orden)

    def send_halt(self):
        self._send_orden(RUNA_HALT)

    def send_pause(self):
        self.is_paused = True
        self._send_orden(RUNA_PAUSE)

    def send_resume(self):
        self.is_paused = False
        self._send_orden(RUNA_RESUME)

    def send_terminate(self):
        self._send_orden(RUNA_TERMINATE)

    def close(self, graceful_timeout: float = 0.0):
        if not self.closed:
            if graceful_timeout > 0 and self.popen and self.popen.poll() is None:
                t0 = time.monotonic()
                while self.popen and self.popen.poll() is None and time.monotonic() - t0 < graceful_timeout:
                    time.sleep(0.05)
            self.ipc_send.close()
            self.ipc_receive.close()
            if self.popen:
                if self.popen.poll() is None:
                    with contextlib.suppress(Exception):
                        self.popen.terminate()
                    with contextlib.suppress(Exception):
                        self.popen.wait(timeout=2)
                else:
                    self.popen.poll()
                self.popen = None
            self.closed = True


class Worker:
    def __init__(self, alm, path_db=None):
        self.huella = Util.huella()
        self.ipc = IPCAnalysis(alm, self.huella, path_db)

    def send_game(self, rowid, recno, num):
        orden = Orden()
        orden.key = RUNA_GAME_ROWID
        orden.dv["ROWID"] = rowid
        orden.dv["RECNO"] = recno
        orden.dv["NUM"] = num
        self.ipc.send(orden)

    def close(self, graceful_timeout: float = 2.0):
        if not self.ipc.closed:
            self.ipc.send_halt()
            self.ipc.close(graceful_timeout=graceful_timeout)

    def is_closed(self):
        return self.ipc.closed

    def is_working(self):
        return self.ipc.working()

    def receive(self):
        return self.ipc.receive()

    def is_paused(self):
        return self.ipc.is_paused

    def send_resume(self):
        self.ipc.send_resume()

    def send_pause(self):
        self.ipc.send_pause()

    def send_terminate(self):
        self.ipc.send_terminate()


class ListRegs:
    def __init__(self, db_games, nregs: int, li_seleccionadas):
        self.db_games = db_games
        self.li_recnos = li_seleccionadas if li_seleccionadas else list(range(nregs))
        self.dic_ordinales = {}
        for i, recno in enumerate(self.li_recnos):
            self.dic_ordinales.setdefault(recno, i + 1)
        self._lock = threading.Lock()
        self.dic_worker = {}

    def assign_to_worker(self, worker, recno):
        self.dic_worker[worker.huella] = recno

    def return_to_queue(self, recno):
        with self._lock:
            self.li_recnos.insert(0, recno)

    def get_game(self, worker):
        with self._lock:
            if not self.li_recnos:
                return None, None
            recno = self.li_recnos.pop(0)
            self.dic_worker[worker.huella] = recno
            return self.dic_ordinales.get(recno, recno + 1), recno

    def received_game(self, worker):
        self.dic_worker[worker.huella] = None

    def is_finished(self):
        with self._lock:
            return len(self.li_recnos) == 0

    def pending(self):
        with self._lock:
            return len(self.li_recnos)

    def remove_worker(self, worker: Worker):
        recno = self.dic_worker.get(worker.huella)
        if recno is not None:
            self.return_to_queue(recno)
            self.dic_worker[worker.huella] = None


class AnalysisMassive(QtCore.QThread):
    game_analyzed = Signal(int, int)
    worker_progress_changed = Signal(object, int, int, int, str)
    worker_added = Signal(object)
    worker_finished = Signal(object)
    finished_successfully = Signal()

    def __init__(self, wowner, alm, nregs, li_seleccionadas):
        super().__init__()
        self.db_games = wowner.db_games
        self.grid = wowner.grid
        self.wowner = wowner
        self.li_seleccionadas = li_seleccionadas
        self.nregs = nregs
        self.num_games_analyzed = 0

        self.bmt_blunders = None
        self.bmt_brillancies = None

        alm.lni = Util.ListaNumerosImpresion(alm.num_moves) if alm.num_moves else None
        self.alm = alm

        self.li_workers = []
        self.dic_huellas_workers = {}

        self.li_extra = []

        self.list_regs = ListRegs(self.db_games, nregs, li_seleccionadas)

        self._is_canceled = False
        self._is_paused = False
        self._pause_cond = threading.Condition()

        self._precreate_columns()
        self.gen_workers()

    def _precreate_columns(self):
        if self.alm.accuracy_tags:
            for tag in ("WhiteAccuracy", "BlackAccuracy", "TotalAccuracy"):
                self.db_games.add_column(tag)
        if self.alm.themes_tags or self.alm.themes_assign or self.alm.themes_reset:
            self.db_games.add_column(TACTICTHEMES)

    def gen_workers(self):
        num_workers = min(self.alm.workers, self.nregs)
        for num_worker in range(num_workers):
            worker = Worker(self.alm, self.db_games.path_file)
            self.li_workers.append(worker)
            if not self.send_game_worker(worker):
                break
            self.dic_huellas_workers[worker.huella] = worker

    def get_worker(self, huella):
        return self.dic_huellas_workers.get(huella)

    def add_worker_from_gui(self):
        worker = Worker(self.alm, self.db_games.path_file)
        self.li_workers.append(worker)
        self.dic_huellas_workers[worker.huella] = worker
        self.send_game_worker(worker)
        self.worker_added.emit(worker)

    def remove_worker(self, worker: Worker):
        if worker.huella in self.dic_huellas_workers:
            del self.dic_huellas_workers[worker.huella]
        if worker in self.li_workers:
            self.li_workers.remove(worker)
        self.list_regs.remove_worker(worker)

    def send_game_worker(self, worker: Worker):
        num, recno = self.list_regs.get_game(worker)
        if recno is None:
            worker.send_terminate()
            return False
        rowid = self.db_games.li_row_ids[recno]
        worker.send_game(rowid, recno, num)
        return True

    def cancel_process(self):
        self._is_canceled = True
        with self._pause_cond:
            self._is_paused = False
            self._pause_cond.notify_all()

    def set_paused(self, is_paused):
        with self._pause_cond:
            self._is_paused = is_paused
            for worker in self.li_workers:
                if is_paused:
                    worker.send_pause()
                else:
                    worker.send_resume()
            if not is_paused:
                self._pause_cond.notify_all()

    def run(self):
        """Bucle principal de control asíncrono"""

        while not self._is_canceled:
            with self._pause_cond:
                while self._is_paused and not self._is_canceled:
                    self._pause_cond.wait(timeout=0.1)

            if self._is_canceled:
                break

            actives = 0
            for worker in list(self.li_workers):
                if worker.is_closed():
                    continue
                if not worker.is_working():
                    worker.close()
                    continue

                actives += 1
                order: Orden = worker.receive()

                if order is None:
                    pass

                elif order.key == RUNA_GAME_DONE:
                    self.run_game_done(worker, order)

                elif order.key == RUNA_TERMINATE:
                    self.worker_finished.emit(worker)
                    worker.close()
                    actives -= 1
                    continue

                elif order.key == RUNA_PROGRESS:
                    huella = order.get("HUELLA")
                    num = order.get("NUM") or 0
                    current = order.get("CURRENT") or 0
                    total = order.get("TOTAL") or 0
                    text = order.get("TEXT") or ""
                    w = self.get_worker(huella)
                    if w:
                        self.worker_progress_changed.emit(w, current, total, num, text)

            if actives == 0:
                break

            self.msleep(30)

        for worker in self.li_workers:
            worker.close()

        if not self._is_canceled:
            self.finished_successfully.emit()

    def run_game_done(self, worker: Worker, order: Orden):
        self.list_regs.received_game(worker)
        self.send_game_worker(worker)

        recno = order.get("RECNO")

        self.num_games_analyzed += 1
        self.game_analyzed.emit(recno, self.num_games_analyzed)

        li_extra = order.get("EXTRA")
        if li_extra:
            self.li_extra.extend(li_extra)

    def save_extra_data(self):
        if not self.li_extra:
            return []

        folder_personal = Code.configuration.paths.folder_personal_trainings()
        Util.create_folder(folder_personal)

        dic_files = {
            "tactic before": [],
            "tactic after": [],
            "brilliancies_fns": [],
            "mate": [],
            "pgn": {},
        }

        bmt_blunders_lista = BMT.BMTLista()
        bmt_brilliancies_lista = BMT.BMTLista()

        for tipo, par1, par2, par3 in self.li_extra:
            if tipo in ("tactic before", "tactic after", "brilliancies_fns"):
                dic_files[tipo].append(par1)
            elif tipo == "mate":
                dic_files[tipo].append((par1, par2))
            elif tipo == "pgn":
                file_path = par1
                if file_path not in dic_files["pgn"]:
                    dic_files["pgn"][file_path] = []
                dic_files["pgn"][file_path].append(par2)
            elif tipo == "bmt_blunders":
                bmt_blunders_lista.nuevo(par1)
                if par2 and par3:
                    bmt_blunders_lista.check_game(par2, par3)
            elif tipo == "bmt_brilliancies":
                bmt_brilliancies_lista.nuevo(par1)
                if par2 and par3:
                    bmt_brilliancies_lista.check_game(par2, par3)

        li_created = []

        # Guardar tácticas (tactic before/after) usando ruta configurada
        if dic_files["tactic before"] or dic_files["tactic after"]:
            li_before = dic_files["tactic before"]
            li_after = dic_files["tactic after"]
            folder_tacticblunders = Util.opj(
                Code.configuration.paths.folder_personal_tactics(), self.alm.tacticblunders
            )
            if AnalysisGameSaveTrainings.save_massive_tactics(folder_tacticblunders, li_before, li_after):
                li_created.append(f"{_('Tactics')}: {os.path.basename(folder_tacticblunders)}")

        # Guardar brilliancies usando ruta configurada
        if dic_files["brilliancies_fns"]:
            brilliancies_file = self.alm.fnsbrilliancies
            with open(brilliancies_file, "at", encoding="utf-8") as f:
                f.writelines(dic_files["brilliancies_fns"])
            li_created.append(f"{_('Brilliancies')}: {os.path.basename(self.alm.fnsbrilliancies)}")

        # Guardar mates usando ruta configurada
        if dic_files["mate"]:
            dic_mate = collections.defaultdict(list)
            for path_mate, mate_line in dic_files["mate"]:
                dic_mate[path_mate].append(mate_line)
            for path_mate, lines in dic_mate.items():
                AnalysisGameSaveTrainings.save_in(path_mate, lines)
                li_created.append(f"{os.path.basename(path_mate)}")

        if dic_files["pgn"]:
            for file_path, li_pgn in dic_files["pgn"].items():
                if not file_path:
                    file_path = str(Util.file_next(folder_personal, "analysis_pgn", "pgn"))
                Util.create_folder(os.path.dirname(file_path))
                with open(file_path, "a", encoding="utf-8") as f:
                    for pgn in li_pgn:
                        f.writelines(pgn)
                li_created.append(f"{_('PGN')}: {os.path.basename(file_path)}")

        if len(bmt_blunders_lista) > 0:
            self._save_bmt_lista(bmt_blunders_lista, self.alm.bmtblunders)
            li_created.append(f"{_('Find best move')}: {self.alm.bmtblunders}")

        if len(bmt_brilliancies_lista) > 0:
            self._save_bmt_lista(bmt_brilliancies_lista, self.alm.bmtbrilliancies)
            li_created.append(f"{_('Find best move')}: {self.alm.bmtbrillancies}")

        return li_created

    @staticmethod
    def _save_bmt_lista(bmt_lista, name):
        bmt = BMT.BMT(Code.configuration.paths.file_bmt())
        dbf = bmt.read_dbf(False)

        reg = dbf.baseRegistro()
        reg.ESTADO = "0"
        reg.NOMBRE = name
        reg.EXTRA = ""
        reg.TOTAL = len(bmt_lista)
        reg.HECHOS = 0
        reg.PUNTOS = 0
        reg.MAXPUNTOS = bmt_lista.max_puntos()
        reg.FINICIAL = Util.dtos(Util.today())
        reg.FFINAL = ""
        reg.SEGUNDOS = 0
        reg.BMT_LISTA = Util.var2zip(bmt_lista)
        reg.HISTORIAL = Util.var2zip([])
        reg.REPE = 0
        reg.ORDEN = 0

        dbf.insertarReg(reg, siReleer=False)
        bmt.cerrar()

    def save_bmt_data(self):
        pass


class WProgress(LCDialog.LCDialog):
    def __init__(self, w_parent, analysis_massive: AnalysisMassive, nregs: int):
        LCDialog.LCDialog.__init__(self, w_parent, _("Analyzing"), Iconos.Analizar(), "massive_progress")

        self.analysis_massive: AnalysisMassive = analysis_massive
        self.lb_game = Controles.LB(self)

        self.pb_moves = QtWidgets.QProgressBar(self)
        self.pb_moves.setFormat(f"{_('Analyzed')} %v/%m")
        self.pb_moves.setRange(0, nregs)
        self.pb_moves.setValue(0)
        self.pb_moves.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                text-align: center;
                height: 28px;
                background-color: #f5f5f5;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #42a5f5, stop:1 #2196F3);
                border-radius: 5px;
            }
        """)

        self.lb_time = Controles.LB(self, "")
        self.lb_time.setStyleSheet("font-size: 10px; color: #666;")

        self._is_paused = False
        self.bt_pause = Controles.PB(self, "", self.pause_resume, plano=True)
        self.icon_pause_resume()
        pb_cancel = Controles.PB(self, _("Cancel"), self.xcancel, plano=False)
        font = Controles.FontTypeNew(point_size_delta=-2)
        pb_cancel.setFont(font)

        self._create_workers_panel(analysis_massive)

        bt_add_worker = Controles.PB(self, _("Add worker"), self.add_worker, plano=True).set_icono(Iconos.Mas())

        lay = Colocacion.H().control(self.lb_game).control(self.pb_moves).control(self.bt_pause)
        lay_time = Colocacion.H().relleno().control(self.lb_time)
        lay2 = Colocacion.H().control(bt_add_worker).relleno().control(pb_cancel)
        layout = Colocacion.V().otro(lay).otro(lay_time).espacio(10).control(self.frame_workers).otro(lay2)
        self.setLayout(layout)

        self._is_canceled = False
        self._is_closed = False
        self._estimator = Util.SmoothedEstimator(total=self.pb_moves.maximum())

        # CONEXIONES DE SEÑALES
        self.analysis_massive.game_analyzed.connect(self.set_pos)
        self.analysis_massive.worker_progress_changed.connect(self.update_worker_progress)
        self.analysis_massive.worker_added.connect(self._add_worker_widget)
        self.analysis_massive.worker_finished.connect(self._remove_worker_widget)
        self.analysis_massive.finished_successfully.connect(self.xfinished)

        self.restore_video(default_width=550, default_height=220)

    def _create_workers_panel(self, analysis_massive: "AnalysisMassive"):
        self.workers_layout = QtWidgets.QVBoxLayout()
        self.workers_layout.setSpacing(4)
        self.frame_workers = QtWidgets.QGroupBox(_("Workers"), self)
        self.frame_workers.setLayout(self.workers_layout)
        self.frame_workers.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ced4da;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #495057;
                background-color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                text-align: center;
                height: 20px;
                background-color: #f8f9fa;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #66bb6a, stop:1 #4CAF50);
                border-radius: 3px;
            }
        """)

        self.dic_worker_widgets = {}
        for worker in analysis_massive.li_workers:
            self._add_worker_widget(worker)

    def _add_worker_widget(self, worker):
        worker_frame = QtWidgets.QFrame(self)
        worker_layout = QtWidgets.QHBoxLayout(worker_frame)
        worker_layout.setContentsMargins(5, 2, 5, 2)

        pb_worker = QtWidgets.QProgressBar(worker_frame)
        # pb_worker.setFormat(f"{_('Movement')} %v/%m")
        pb_worker.setFont(Controles.FontTypeNew(extra_bold=True))
        pb_worker.setStyleSheet("""
            QProgressBar {
                text-align: left;
            }
            QProgressBar::chunk {
                margin: 0px; /* Asegura que la barra empiece desde el borde 0px */
            }
        """)
        pb_worker.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)

        bt_pause_worker = Controles.PB(worker_frame, "", lambda checked, w=worker: self.pause_worker(w), plano=True)
        bt_pause_worker.set_icono(Iconos.PauseColor())

        bt_close_worker = Controles.PB(worker_frame, "", lambda checked, w=worker: self.close_worker(w), plano=True)
        bt_close_worker.set_icono(Iconos.Borrar())

        worker_layout.addWidget(pb_worker, 1)
        worker_layout.addWidget(bt_pause_worker)
        worker_layout.addWidget(bt_close_worker)

        self.workers_layout.addWidget(worker_frame)

        self.dic_worker_widgets[worker.huella] = {
            "frame": worker_frame,
            "progress_bar": pb_worker,
            "pause_button": bt_pause_worker,
            "close_button": bt_close_worker,
            "current_game": 0,
            "total_moves": 0,
        }

    def _remove_worker_widget(self, worker: Worker):
        if worker.huella in self.dic_worker_widgets:
            widget_info = self.dic_worker_widgets[worker.huella]
            widget_info["frame"].hide()
            self.workers_layout.removeWidget(widget_info["frame"])
            widget_info["frame"].deleteLater()
            self.dic_worker_widgets.pop(worker.huella)
            if not self.dic_worker_widgets:
                self.frame_workers.hide()
            self.adjustSize()

    def add_worker(self):
        self.analysis_massive.add_worker_from_gui()

    def pause_worker(self, worker: Worker):
        if worker.is_paused():
            worker.send_resume()
            self.dic_worker_widgets[worker.huella]["pause_button"].set_icono(Iconos.PauseColor())
        else:
            worker.send_pause()
            self.dic_worker_widgets[worker.huella]["pause_button"].set_icono(Iconos.ContinueColor())

    def close_worker(self, worker: Worker):
        if not worker.is_closed():
            widget_info = self.dic_worker_widgets.get(worker.huella)
            if widget_info:
                pb = widget_info["progress_bar"]
                pb.setFormat(f" {_('Closing')}...")
                pb.setRange(0, 1)
                pb.setValue(0)
                widget_info["close_button"].setEnabled(False)
                widget_info["pause_button"].setEnabled(False)
                QtWidgets.QApplication.processEvents()
            worker.send_terminate()
            worker.close()

        self._remove_worker_widget(worker)
        self.analysis_massive.remove_worker(worker)

    def update_worker_progress(self, worker: Worker, current_move: int, total_moves: int, num: int = 0, text: str = ""):
        if worker.huella in self.dic_worker_widgets:
            widget = self.dic_worker_widgets[worker.huella]
            pb = widget["progress_bar"]
            if text:
                pb.setFormat(f"  {text}")
                pb.setRange(0, 1)
                pb.setValue(0)
            else:
                pb.setFormat(f"  {_('Game')} {num} → {_('Movement')} %v/%m ")
                widget["current_game"] = current_move
                widget["total_moves"] = total_moves
                if total_moves > 0:
                    pb.setRange(0, total_moves)
                    pb.setValue(current_move)

    def xcancel(self):
        if not self._is_canceled:
            with QTMessages.one_moment_please(self, mensaje=f"{_('Closing')}..."):
                self.hide()
                self._is_canceled = True
                self.analysis_massive.cancel_process()
                self.analysis_massive.wait()
                self.xclose()

    def pause_resume(self):
        self._is_paused = not self._is_paused
        self.icon_pause_resume()
        self.analysis_massive.set_paused(self._is_paused)

    def icon_pause_resume(self):
        self.bt_pause.set_icono(Iconos.ContinueColor() if self._is_paused else Iconos.PauseColor())

    def is_canceled(self):
        return self._is_canceled

    def is_paused(self):
        return self._is_paused

    def set_pos(self, recno, pos):
        if not self._is_canceled:
            self.pb_moves.setValue(pos)
            str_estimate = self._estimator.estimated(pos)
            if str_estimate is not None:
                self.lb_time.set_text(f"{_('Pending time')}: {str_estimate}")
            else:
                self.lb_time.set_text("")

    def xfinished(self):
        self.analysis_massive.wait()
        li_created = self.analysis_massive.save_extra_data()
        if li_created:
            message = f"{_('Created')}:<ul>"
            for line in li_created:
                message += f"<li>{line}</li>"
            message += "</ul>"
            QTMessages.message(self, message)
        self.xclose()

    def xclose(self):
        if not self._is_closed:
            self._is_closed = True
            self.accept()

    def closeEvent(self, event) -> None:
        self.xcancel()


def lanzar_analisis_masivo(wowner, alm, nregs, li_seleccionadas):
    procesador_hilo = AnalysisMassive(wowner, alm, nregs, li_seleccionadas)

    ventana = WProgress(wowner, procesador_hilo, nregs)
    ventana.hilo_controlador = procesador_hilo

    procesador_hilo.start()

    ventana.setMinimumWidth(360)
    ScreenUtils.shrink(ventana)
    ventana.exec()
