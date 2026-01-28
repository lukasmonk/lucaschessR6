from Code.Tournaments import Tournament


class TournamentWork:
    def __init__(self, file_tournament):
        self.file_tournament = file_tournament
        with self.tournament() as torneo:
            self.run_name = torneo.name()
            self.run_drawRange = torneo.draw_range()
            self.run_drawMinPly = torneo.draw_min_ply()
            self.run_resign = torneo.resign()
            self.run_bookDepth = torneo.book_depth()

    def name(self):
        return self.run_name

    def draw_range(self):
        return self.run_drawRange

    def draw_min_ply(self):
        return self.run_drawMinPly

    def resign(self):
        return self.run_resign

    def book_depth(self):
        return self.run_bookDepth

    def tournament(self):
        return Tournament.Tournament(self.file_tournament)

    def get_tgame_queued(self, file_work):
        with self.tournament() as torneo:
            self.run_name = torneo.name()
            self.run_drawRange = torneo.draw_range()
            self.run_drawMinPly = torneo.draw_min_ply()
            self.run_resign = torneo.resign()
            self.run_bookDepth = torneo.book_depth()
            return torneo.get_tgame_queued(file_work)

    def fen_norman(self):
        with self.tournament() as torneo:
            return torneo.fen_norman()

    def slow_pieces(self):
        with self.tournament() as torneo:
            return torneo.slow_pieces()

    def arbiter_active(self):
        with self.tournament() as torneo:
            return torneo.arbiter_active()

    def move_evaluator(self):
        with self.tournament() as torneo:
            return torneo.move_evaluator()

    def arbiter_time(self):
        with self.tournament() as torneo:
            return torneo.arbiter_time()

    def search_hengine(self, h):
        with self.tournament() as torneo:
            return torneo.search_hengine(h)

    def book(self):
        with self.tournament() as torneo:
            return torneo.book()

    def game_done(self, game):
        with self.tournament() as torneo:
            return torneo.game_done(game)

    def close(self):
        pass

    def get_engines(self, tgame: Tournament.GameTournament):
        with self.tournament() as torneo:
            engine_white = torneo.search_hengine(tgame.hwhite)
            engine_black = torneo.search_hengine(tgame.hblack)
            return engine_white, engine_black
