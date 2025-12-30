from typing import Optional

from PySide6 import QtCore

import Code
from Code.Engines import EngineRun
from Code.Kibitzers import WKibCommon
from Code.QT import Colocacion, Controles, Iconos, QTUtils


class WStockfishEval(WKibCommon.WKibCommon):
    engine_run: Optional[EngineRun.EngineRun]

    def __init__(self, cpu):
        WKibCommon.WKibCommon.__init__(self, cpu, Iconos.Book())

        self.em = Controles.EM(self, siHTML=False).read_only()
        f = Controles.FontType(name=Code.font_mono, puntos=10)
        self.em.set_font(f)

        li_acciones = (
            (_("Quit"), Iconos.Kibitzer_Close(), self.terminar),
            (_("Continue"), Iconos.Kibitzer_Play(), self.play),
            (_("Pause"), Iconos.Kibitzer_Pause(), self.pause),
            (_("Original position"), Iconos.HomeBlack(), self.home),
            (_("Takeback"), Iconos.Kibitzer_Back(), self.takeback),
            (_("Show/hide board"), Iconos.Kibitzer_Board(), self.config_board),
            (
                "%s: %s" % (_("Enable"), _("window on top")),
                Iconos.Pin(),
                self.window_top,
            ),
            (
                "%s: %s" % (_("Disable"), _("window on top")),
                Iconos.Unpin(),
                self.window_bottom,
            ),
        )
        self.tb = Controles.TBrutina(self, li_acciones, with_text=False, icon_size=24)
        self.tb.set_action_visible(self.play, False)

        ly1 = Colocacion.H().control(self.board).control(self.em).margen(3)
        layout = Colocacion.V().control(self.tb).espacio(-10).otro(ly1).margen(3)
        self.setLayout(layout)

        self.launch_engine()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.cpu.check_input)
        self.timer.start(200)

        self.restore_video(self.dicVideo)
        self.set_flags()

    def stop(self):
        self.siPlay = False

    def whether_to_analyse(self):
        si_w = self.game.last_position.is_white
        if not self.siPlay or (si_w and (not self.is_white)) or ((not si_w) and (not self.is_black)):
            return False
        return True

    def finalizar(self):
        self.save_video()
        if self.engine_run:
            self.engine_run.close()
            self.engine_run = None
            self.siPlay = False

    def launch_engine(self):
        run_param = EngineRun.StartEngineParams()
        run_param.name = self.kibitzer.name
        run_param.path_exe = self.kibitzer.path_exe
        run_param.li_options_uci = self.kibitzer.liUCI
        run_param.args = self.kibitzer.args
        run_param.num_multipv = 1
        self.engine_run = EngineRun.EngineRun(run_param)
        self.engine_run.eval_stockfish_found.connect(self.from_engine)

    def from_engine(self, txt_eval):
        self.em.set_text(txt_eval)

    def orden_game(self, game):
        self.siPlay = True
        self.game = game
        posicion = game.last_position

        is_white = posicion.is_white

        self.board.set_position(posicion)
        self.board.activate_side(is_white)
        if self.whether_to_analyse():
            self.engine_run.run_eval_stockfish(posicion.fen())
        else:
            self.em.set_text("")

        self.test_tb_home()

        QTUtils.refresh_gui()
