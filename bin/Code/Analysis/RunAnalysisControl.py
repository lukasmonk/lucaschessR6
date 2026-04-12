import contextlib

from PySide6 import QtCore, QtWidgets

import Code
from Code.Base import Game
from Code.Base.Constantes import (
    RUNA_CONFIGURATION,
    RUNA_GAME,
    RUNA_HALT,
    RUNA_TERMINATE,
    RUNA_PAUSE,
    RUNA_RESUME,
    RUNA_PROGRESS,
)
from Code.BestMoveTraining import BMT
from Code.QT import Colocacion, Controles, Iconos, LCDialog, QTUtils, ScreenUtils
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


class IPCAnalysis:
    def __init__(self, alm, huella):
        self.closed = False
        self.is_paused = False
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

    def close(self):
        if not self.closed:
            self.ipc_send.close()
            self.ipc_receive.close()
            if self.popen:
                with contextlib.suppress(Exception):
                    self.popen.terminate()
                self.popen = None
            self.closed = True


class Worker:
    def __init__(self, alm):
        self.huella = Util.huella()
        self.ipc = IPCAnalysis(alm, self.huella)

    def send_game(self, game, recno):
        orden = Orden()
        orden.key = RUNA_GAME
        orden.dv["GAME"] = game
        orden.dv["RECNO"] = recno
        self.ipc.send(orden)

    def close(self):
        if not self.ipc.closed:
            self.ipc.send_halt()
            self.ipc.close()

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
        self.dic_worker = {}

    def get_game(self, worker):
        if self.is_finished():
            return None
        recno = self.li_recnos.pop(0)
        self.dic_worker[worker.huella] = recno
        return recno

    def received_game(self, worker):
        self.dic_worker[worker.huella] = None

    def is_finished(self):
        return len(self.li_recnos) == 0

    def pending(self):
        return len(self.li_recnos)

    def remove_worker(self, worker: Worker):
        recno = self.dic_worker.get(worker.huella)
        if recno is not None:
            self.li_recnos.insert(0, recno)
            self.dic_worker[worker.huella] = None


class AnalysisMassiveWithWorkers:
    def __init__(self, wowner, alm, nregs, li_seleccionadas):
        self.db_games = wowner.db_games
        self.grid = wowner.grid
        self.wowner = wowner
        self.li_seleccionadas = li_seleccionadas
        self.nregs = nregs
        self.pos_reg = -1
        self.num_games_analyzed = 0

        self.bmt_blunders = None
        self.bmt_brillancies = None

        alm.lni = Util.ListaNumerosImpresion(alm.num_moves) if alm.num_moves else None
        self.alm = alm

        self.li_workers = []
        self.dic_huellas_workers = {}

        self.window = None

        self.list_regs = ListRegs(self.db_games, nregs, li_seleccionadas)

    def gen_workers(self):
        num_workers = min(self.alm.workers, self.nregs)
        for num_worker in range(num_workers):
            worker = Worker(self.alm)
            self.li_workers.append(worker)
            if not self.send_game_worker(worker):
                break
            self.dic_huellas_workers[worker.huella] = worker

    def get_worker(self, huella):
        return self.dic_huellas_workers.get(huella)

    def add_worker(self, worker: Worker):
        self.li_workers.append(worker)
        self.dic_huellas_workers[worker.huella] = worker

    def remove_worker(self, worker: Worker):
        del self.dic_huellas_workers[worker.huella]
        self.li_workers.remove(worker)
        self.list_regs.remove_worker(worker)

    def send_game_worker(self, worker: Worker):
        recno = self.list_regs.get_game(worker)
        if recno is None:
            worker.send_terminate()
            return False

        game = self.db_games.read_game_recno(recno)
        worker.send_game(game, recno)
        return True

    def close(self):
        worker: Worker
        for worker in self.li_workers:
            worker.close()
        self.window.xclose()

    def run_game(self, worker: Worker, order: Orden):
        self.list_regs.received_game(worker)
        self.send_game_worker(worker)

        game: Game.Game = order.get("GAME")
        if self.alm.accuracy_tags:
            game.add_accuracy_tags()
        recno = order.get("RECNO")
        self.db_games.save_game_recno(recno, game)
        self.num_games_analyzed += 1
        self.window.set_pos(self.num_games_analyzed)

        if li_extra := order.get("EXTRA"):
            for tipo, par1, par2, par3 in li_extra:
                if tipo == "bmt_blunders":
                    if self.bmt_blunders is None:
                        self.bmt_blunders = BMT.BMTLista()
                    self.bmt_blunders.nuevo(par1)
                    self.bmt_blunders.check_game(par2, par3)
                elif tipo == "bmt_brilliancies":
                    if self.bmt_brillancies is None:
                        self.bmt_brillancies = BMT.BMTLista()
                    self.bmt_brillancies.nuevo(par1)
                    self.bmt_brillancies.check_game(par2, par3)
                elif tipo == "file":
                    with open(par1, "at", encoding="utf-8", errors="ignore") as f:
                        f.write(par2)

    def processing(self):
        QTUtils.refresh_gui()
        if self.window.is_canceled():
            self.close()
            return

        if self.window.is_paused():
            return

        actives = 0

        worker: Worker
        for worker in self.li_workers:
            if worker.is_closed():
                continue
            if not worker.is_working():
                worker.close()
                continue

            actives += 1

            order: Orden = worker.receive()
            if order is None:
                pass

            elif order.key == RUNA_GAME:
                self.run_game(worker, order)

            elif order.key == RUNA_TERMINATE:
                worker.close()
                actives -= 1
                continue

            elif order.key == RUNA_PROGRESS:
                huella = order.get("HUELLA")
                current = order.get("CURRENT")
                total = order.get("TOTAL")
                if self.window:
                    worker = self.get_worker(huella)
                    if worker:
                        self.window.update_worker_progress(worker, current, total)

        if actives == 0:
            self.close()

    def send_pause_resume(self, is_paused):
        for worker in self.li_workers:
            if is_paused:
                worker.send_pause()
            else:
                worker.send_resume()

    @staticmethod
    def save_bmt(bmt):
        if bmt is None:
            return

    def run(self):
        self.gen_workers()
        self.window = WProgress(self.wowner, self, self.nregs)
        self.window.show()
        self.window.setMinimumWidth(360)
        ScreenUtils.shrink(self.window)
        self.window.exec()

        for bmt_lista, name in (
            (self.bmt_blunders, self.alm.bmtblunders),
            (self.bmt_brillancies, self.alm.bmtbrilliancies),
        ):
            if bmt_lista and len(bmt_lista) > 0:
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


class WProgress(LCDialog.LCDialog):
    def __init__(self, w_parent, amww: AnalysisMassiveWithWorkers, nregs: int):
        LCDialog.LCDialog.__init__(self, w_parent, _("Analyzing"), Iconos.Analizar(), "massive_progress")

        self.lb_game = Controles.LB(self)

        self.pb_moves = QtWidgets.QProgressBar(self)
        self.pb_moves.setFormat(f"{_('Game')} %v/%m")
        self.pb_moves.setRange(0, nregs)
        self.pb_moves.setValue(0)
        self.pb_moves.setStyleSheet("""
            QProgressBar {
                border: 1px solid #aaa;
                border-radius: 4px;
                text-align: center;
                height: 24px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
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

        self._create_workers_panel(amww)

        bt_add_worker = Controles.PB(self, _("Add worker"), self.add_worker, plano=True).set_icono(Iconos.Mas())

        lay = Colocacion.H().control(self.lb_game).control(self.pb_moves).control(self.bt_pause)
        lay_time = Colocacion.H().relleno().control(self.lb_time)
        lay2 = Colocacion.H().control(bt_add_worker).relleno().control(pb_cancel)
        layout = Colocacion.V().otro(lay).otro(lay_time).espacio(10).control(self.frame_workers).otro(lay2)
        self.setLayout(layout)

        self.amww: AnalysisMassiveWithWorkers = amww
        self._is_canceled = False
        self._is_closed = False

        self._games_done = 0
        self._estimator = Util.SmoothedEstimator(total=self.pb_moves.maximum())

        self.restore_video(default_width=550, default_height=220)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.xreceive)
        self.timer.start(200)

        self.restore_video()
        self.working = False

    def _create_workers_panel(self, amww: "AnalysisMassiveWithWorkers"):
        self.workers_layout = QtWidgets.QVBoxLayout()
        self.workers_layout.setSpacing(4)
        self.frame_workers = QtWidgets.QGroupBox(_("Workers"), self)
        self.frame_workers.setLayout(self.workers_layout)
        self.frame_workers.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #888;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #333;
            }
            QProgressBar {
                border: 1px solid #aaa;
                border-radius: 3px;
                text-align: center;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)

        self.dic_worker_widgets = {}

        worker: Worker
        for worker in amww.li_workers:
            self._add_worker_widget(worker)

    def _add_worker_widget(self, worker):
        worker_frame = QtWidgets.QFrame(self)
        worker_layout = QtWidgets.QHBoxLayout(worker_frame)
        worker_layout.setContentsMargins(5, 2, 5, 2)

        pb_worker = QtWidgets.QProgressBar(worker_frame)
        pb_worker.setFormat(f"{_('Movement')} %v/%m")
        # pb_worker.setRange(0, 100)
        # pb_worker.setValue(0)
        pb_worker.setFont(Controles.FontTypeNew(extra_bold=True))

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

    def add_worker(self):
        worker = Worker(self.amww.alm)
        self.amww.add_worker(worker)
        self._add_worker_widget(worker)

        self.amww.send_game_worker(worker)

    def pause_worker(self, worker: Worker):
        if worker.is_paused():
            worker.send_resume()
            self.dic_worker_widgets[worker.huella]["pause_button"].set_icono(Iconos.PauseColor())
        else:
            worker.send_pause()
            self.dic_worker_widgets[worker.huella]["pause_button"].set_icono(Iconos.ContinueColor())

    def close_worker(self, worker: Worker):
        if not worker.is_closed():
            worker.send_terminate()
            worker.close()

        widget_info = self.dic_worker_widgets[worker.huella]
        widget_info["frame"].hide()
        self.workers_layout.removeWidget(widget_info["frame"])
        widget_info["frame"].deleteLater()

        self.dic_worker_widgets.pop(worker.huella)

        self.amww.remove_worker(worker)

    def update_worker_progress(self, worker: Worker, current_move: int, total_moves: int):
        widget = self.dic_worker_widgets[worker.huella]
        widget["current_game"] = current_move
        widget["total_moves"] = total_moves
        if total_moves > 0:
            widget["progress_bar"].setRange(0, total_moves)
            widget["progress_bar"].setValue(current_move)

    def xreceive(self):
        QTUtils.refresh_gui()
        if self.working:
            return
        self.working = True
        self.amww.processing()
        self.working = False

    def xcancel(self):
        self._is_canceled = True
        self.amww.close()

    def pause_resume(self):
        self._is_paused = not self._is_paused
        self.icon_pause_resume()
        self.amww.send_pause_resume(self._is_paused)

    def icon_pause_resume(self):
        self.bt_pause.set_icono(Iconos.ContinueColor() if self._is_paused else Iconos.PauseColor())

    def is_canceled(self):
        return self._is_canceled

    def is_paused(self):
        return self._is_paused

    def set_pos(self, pos):
        if not self._is_canceled:
            self.pb_moves.setValue(pos)
            str_estimate = self._estimator.estimated(pos)
            if str_estimate is not None:
                self.lb_time.set_text(f"{_('Estimated time')}: {str_estimate}")
            else:
                self.lb_time.set_text("")

    def xclose(self):
        if not self._is_closed:
            self._is_closed = True
            self.timer.stop()
            self.timer = None
            self.accept()
