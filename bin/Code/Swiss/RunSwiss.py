import sys

from PySide6 import QtWidgets

import Code
from Code.Z import Util
from Code.Base import Game
from Code.Config import Configuration
from Code.MainWindow import InitApp
from Code.Openings import OpeningsStd
from Code.QT import Piezas
from Code.Swiss import Swiss, SwissWork
from Code.Workers import RunWorker, Worker


class SwissWorker(RunWorker.RunWorker):
    def __init__(self, file_swiss_work):
        super().__init__()
        self.swiss = Swiss.Swiss(file_swiss_work)
        self.swiss_work = SwissWork.SwissWork(self.swiss)
        self.name = self.swiss.name()
        self.key_video = "SWISSPLAY"
        self.arbiter_active = self.swiss.arbiter_active()
        self.move_evaluator = self.swiss.move_evaluator
        self.arbiter_time = self.swiss.arbiter_time
        self.draw_range = self.swiss.draw_range
        self.draw_min_ply = self.swiss.draw_min_ply
        self.resign = self.swiss.resign
        self.time_engine_engine = self.swiss.time_engine_engine
        self.book_path = self.swiss.book.path if self.swiss.book else None
        self.book_depth = self.swiss.book_depth
        self.book_rr = self.swiss.book_rr
        self.slow_pieces = self.swiss.slow_pieces

        self.match: Swiss.Match | None = None

    def start(self):
        w = Worker.Worker(self)
        w.show()
        w.looking_for_work()

    def get_other_match(self):
        self.match = self.swiss_work.get_other_match()
        if self.match:
            self.engine_white = self.swiss.opponent_by_xid(self.match.xid_white).thinker
            self.engine_black = self.swiss.opponent_by_xid(self.match.xid_black).thinker
        return self.match

    def add_tags_game(self, game: Game.Game):
        game.set_tag("Season", str(self.swiss.current_num_season + 1))
        journey = self.swiss_work.get_journey_match(self.match)
        game.set_tag("Round", str(journey + 1))

    def put_match_done(self, game: Game.Game):
        self.swiss_work.put_match_done(self.match, game)

    def cancel_match(self):
        if self.match is not None:
            self.swiss_work.cancel_match(self.match.xid)


def run(user, file_swiss_work):
    if not __debug__:
        sys.stderr = Util.Log("./bug.swiss")

    app = QtWidgets.QApplication([])

    configuration = Configuration.Configuration(user)
    configuration.start()
    configuration.load_translation()
    OpeningsStd.ap.reset()
    Code.all_pieces = Piezas.AllPieces()

    InitApp.init_app_style(app, configuration)

    lw = SwissWorker(file_swiss_work)
    lw.start()

    app.exec()
