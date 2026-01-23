import sys

from PySide6 import QtWidgets

import Code
from Code.Z import Util
from Code.Base import Game
from Code.Base.Constantes import BOOK_RANDOM_UNIFORM
from Code.Config import Configuration
from Code.MainWindow import InitApp
from Code.Openings import OpeningsStd
from Code.QT import Piezas
from Code.Tournaments import Tournament, TournamentWork
from Code.Workers import RunWorker, Worker


class TournamentWorker(RunWorker.RunWorker):
    def __init__(self, file_tournament, file_tournament_work):
        super().__init__()
        self.tournament_work = TournamentWork.TournamentWork(file_tournament)
        self.file_tournament_work = file_tournament_work
        self.name = self.tournament_work.run_name
        self.key_video = "TOURNAMENTPLAY"
        self.adjudicator_active = self.tournament_work.adjudicator_active()
        self.move_evaluator = self.tournament_work.move_evaluator()
        self.adjudicator_time = self.tournament_work.adjudicator_time()
        self.draw_range = self.tournament_work.run_drawRange
        self.draw_min_ply = self.tournament_work.run_drawMinPly
        self.resign = self.tournament_work.run_resign
        book = self.tournament_work.book()
        if book is None or book == "-":
            book = None
        self.book_path = book
        self.book_depth = self.tournament_work.run_bookDepth
        self.book_rr = BOOK_RANDOM_UNIFORM
        self.slow_pieces = self.tournament_work.slow_pieces()
        self.time_engine_engine = 3, 0

        self.tgame: Tournament.GameTournament | None = None

    def start(self):
        w = Worker.Worker(self)
        w.show()
        w.looking_for_work()

    def get_other_match(self):
        self.tgame: Tournament.GameTournament = self.tournament_work.get_tgame_queued(self.file_tournament_work)
        if self.tgame:
            self.engine_white, self.engine_black = self.tournament_work.get_engines(self.tgame)
            self.time_engine_engine = self.tgame.minutos, self.tgame.seconds_per_move
            self.initial_fen = self.tournament_work.fen_norman()

        return self.tgame

    def add_tags_game(self, game: Game.Game):
        # Nothing to add
        pass

    def put_match_done(self, game: Game.Game):
        self.tgame.save_game(game)
        self.tournament_work.game_done(self.tgame)

    def cancel_match(self):
        pass


def run(user, file_tournament, file_work):
    if not __debug__:
        sys.stderr = Util.Log("./bug.tournaments")

    app = QtWidgets.QApplication([])

    configuration = Configuration.Configuration(user)
    configuration.start()
    configuration.load_translation()
    OpeningsStd.ap.reset()
    Code.all_pieces = Piezas.AllPieces()

    InitApp.init_app_style(app, configuration)

    lw = TournamentWorker(file_tournament, file_work)
    lw.start()

    app.exec()
