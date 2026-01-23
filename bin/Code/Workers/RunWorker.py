import Code
from Code.Base import Game
from Code.Engines import Engines


class RunWorker:
    slow_pieces: bool
    name: str
    key_video: str
    move_evaluator: str
    adjudicator_time: float
    adjudicator_active: bool
    draw_range: int
    draw_min_ply: int
    resign: int
    time_engine_engine: tuple
    engine_white: Engines.Engine
    engine_black: Engines.Engine
    book_path: str | None
    book_rr: str | None
    book_depth: int | None
    initial_fen: str | None

    def __init__(self):
        Code.procesador = ProcesadorBar()  # necesario para la barra de analisis
        self.initial_fen = None

    def get_other_match(self):
        pass

    def add_tags_game(self, game: Game.Game):
        pass

    def put_match_done(self, game: Game.Game):
        pass

    def cancel_match(self):
        pass


class ProcesadorBar:

    @staticmethod
    def analyzer_clone_new(mstime: int, depth: int, nodes: int, multipv: str | int):
        from Code.Engines import EngineManagerPlay, EngineRun, Engines

        engine: Engines.Engine = Code.configuration.engines.engine_analyzer()
        engine.set_multipv_var(multipv)

        run_engine_params = EngineRun.RunEngineParams()
        run_engine_params.update(engine, mstime, depth, nodes, engine.multiPV)
        engine_manager = EngineManagerPlay.EngineManagerPlay(engine, run_engine_params)
        return engine_manager
