import sys

from PySide6 import QtWidgets

import Code
from Code.Z import Util
from Code.Base import Game
from Code.Config import Configuration
from Code.Leagues import Leagues, LeaguesWork
from Code.MainWindow import InitApp
from Code.Openings import OpeningsStd
from Code.QT import Piezas
from Code.Workers import RunWorker, Worker


class LeagueWorker(RunWorker.RunWorker):
    def __init__(self, file_league_work):
        super().__init__()
        self.league = Leagues.League(file_league_work)
        self.league_work = LeaguesWork.LeaguesWork(self.league)
        self.name = self.league.name()
        self.key_video = "LEAGUEYPLAY"
        self.adjudicator_active = self.league.adjudicator_active()
        self.move_evaluator = self.league.move_evaluator
        self.adjudicator_time = self.league.adjudicator_time
        self.draw_range = self.league.draw_range
        self.draw_min_ply = self.league.draw_min_ply
        self.resign = self.league.resign
        self.time_engine_engine = self.league.time_engine_engine
        self.book_path = self.league.book
        self.book_depth = self.league.book_depth
        self.book_rr = self.league.book_rr
        self.slow_pieces = self.league.slow_pieces

        self.match: Leagues.Match | None = None

    def start(self):
        w = Worker.Worker(self)
        w.show()
        w.looking_for_work()

    def get_other_match(self):
        self.match = self.league_work.get_other_match()
        if self.match:
            self.engine_white = self.league.opponent_by_xid(self.match.xid_white).thinker
            self.engine_black = self.league.opponent_by_xid(self.match.xid_black).thinker
        return self.match

    def add_tags_game(self, game: Game.Game):
        game.set_tag("Season", str(self.league.current_num_season + 1))
        num_division, journey = self.league_work.get_division_journey_match(self.match)
        game.set_tag("Division", str(num_division + 1))
        game.set_tag("Journey", str(journey + 1))

    def put_match_done(self, game: Game.Game):
        self.league_work.put_match_done(self.match, game)

    def cancel_match(self):
        if self.match is not None:
            self.league_work.cancel_match(self.match.xid)


def run(user, file_league_work):
    if not __debug__:
        sys.stderr = Util.Log("./bug.league")

    app = QtWidgets.QApplication([])

    configuration = Configuration.Configuration(user)
    configuration.start()
    configuration.load_translation()
    OpeningsStd.ap.reset()
    Code.all_pieces = Piezas.AllPieces()

    InitApp.init_app_style(app, configuration)

    lw = LeagueWorker(file_league_work)
    lw.start()

    app.exec()
