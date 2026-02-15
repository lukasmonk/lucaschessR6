import os
import sys

from PySide6 import QtWidgets

import Code
from Code.Base import Game
from Code.Base.Constantes import BOOK_RANDOM_UNIFORM
from Code.Config import Configuration
from Code.MainWindow import InitApp
from Code.Openings import OpeningsStd
from Code.QT import Piezas, Iconos
from Code.SQL import UtilSQL
from Code.Tournaments import Tournament, TournamentWork
from Code.Workers import RunWorker, Worker
from Code.Z import Util


class TournamentWorker(RunWorker.RunWorker):
    def __init__(self, file_tournament):
        super().__init__()
        self.file_tournament = file_tournament
        self.tournament_work = TournamentWork.TournamentWork(file_tournament)
        self.num_worker = os.getpid()
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
        self.icon = Iconos.Torneos()

        self.get_game_queued = GetGameQueuedTournament(self.tournament_work)

        self.tgame: Tournament.GameTournament | None = self._get_match()
        self.first_request = True

    def start(self):
        w = Worker.Worker(self)
        w.show()
        w.looking_for_work()

    def get_other_match(self):
        if self.first_request:
            self.first_request = False
            return self.tgame
        return self._get_match()

    def _get_match(self):
        self.tgame: Tournament.GameTournament | None = self.get_game_queued.get_game()
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


def run(user, file_tournament):
    if not __debug__:
        sys.stderr = Util.Log("./bug.tournaments")

    app = QtWidgets.QApplication([])

    configuration = Configuration.Configuration(user)
    configuration.start()
    configuration.load_translation()
    OpeningsStd.ap.reset()
    Code.all_pieces = Piezas.AllPieces()

    InitApp.init_app_style(app, configuration)

    lw = TournamentWorker(file_tournament)
    lw.start()

    app.exec()


class GetGameQueuedTournament:
    def __init__(self, tw: TournamentWork.TournamentWork):
        path_work = Util.opj(Code.configuration.temporary_folder(), f"{os.path.basename(tw.file_tournament)}")
        self.tickets = UtilSQL.Tickets(path_work, tw.get_dic_queues)

    def get_game(self):
        return self.tickets.get_ticket()
        # with UtilSQL.ListObjSQL(self.path_tournament, Tournament.GameTournament, tabla="games_queued") as dbqueued, \
        #         UtilSQL.DictSQLMultiProcess(self.path_work) as dbwork:
        #     if len(dbqueued) == 0:
        #         return None
        #
        #     game_tournament: Tournament.GameTournament
        #     dic_games = {}
        #     for game_tournament in dbqueued:
        #         if game_tournament.id_game in dbwork:
        #             dic_games[game_tournament.id_game] = game_tournament
        #             continue
        #         dbwork[game_tournament.id_game] = os.getpid()
        #         return game_tournament
        #
        #     for id_game in dic_games:
        #         pid = dbwork[id_game]
        #         if not psutil.pid_exists(pid):
        #             dbwork[id_game] = os.getpid()
        #             return dic_games[id_game]
        #     return None
