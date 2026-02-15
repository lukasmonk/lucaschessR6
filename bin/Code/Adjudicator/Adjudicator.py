from enum import Enum, auto
from typing import Optional, Callable

import Code
from Code.Base import Game, Move, Position
from Code.Engines import EngineManagerAnalysis, EngineResponse, Engines
from Code.Openings import OpeningsStd
from Code.QT import FormLayout, Iconos
from Code.QT import QTMessages


class AdjudicatorState(Enum):
    analysing = auto()  # Análizando
    active = auto()  # No hace nada el motor, a la espera de ordenes
    closing = auto()  # Cerrando, si está analizando se lanza un stop y bestmove se encarga de cerrar


class Adjudicator:
    book_active: bool
    manager_analyzer: Optional[EngineManagerAnalysis.EngineManagerAnalysis]
    mrm: Optional[EngineResponse.MultiEngineResponse]
    move_played: Optional[Move.Move]
    _rut_player_move: Optional[Callable]
    obj_move: Optional[Move.Move]
    user_move: Optional[Move.Move]
    state: AdjudicatorState

    def __init__(self, owner, wowner, name_obj: str, rut_player_move: Callable):
        self.key = "ADJUDICATION"
        self.owner = owner
        self.wowner = wowner
        self.name_obj: str = name_obj
        self._rut_player_move: Callable = rut_player_move

        self.nom_engine, self.multipv, self.ms_time, self.show_all = self.get_adjudicator_options()

        self.manager_analyzer = self.open_manager_analyzer()

        self.move_played = None
        self.mrm = None
        self.game = None
        self.book_active: bool = True
        self.state: AdjudicatorState = AdjudicatorState.active
        self._message_same_book_moves = True

    def disable_message_same_book_moves(self):
        self._message_same_book_moves = False

    def open_manager_analyzer(self):
        engine = Code.configuration.engines.search(self.nom_engine, defecto="stockfish")
        return Code.procesador.create_manager_analysis(engine, self.ms_time, 0, 0, self.multipv)

    def analyze_begin(self, game: Game.Game):
        self.game = game
        self.state = AdjudicatorState.analysing
        self.mrm = None
        self.move_played = None
        self.obj_move = None
        self.user_move = None
        dispatcher_bestmove = self.bestmove_found if self.ms_time > 0 else None
        # Si el tiempo es cero = indeterminado, donde se mantiene el análisis
        self.manager_analyzer.analyze_tutor(
            game, dispacher_bestmove=dispatcher_bestmove, dispacher_changedepth=self.changedepth
        )

    def analyze_end(self):
        if self.is_analysing():
            self.manager_analyzer.stop()

    def is_analysing(self):
        return self.state == AdjudicatorState.analysing

    def changedepth(self, mrm):
        self.mrm = mrm
        return True

    def get_mrm(self):
        return self.mrm

    def is_time_fixed(self):
        return self.ms_time > 0

    def set_move_played(self, move_played):
        self.move_played = move_played

    def close(self):
        if self.manager_analyzer is not None:
            if self.is_analysing():
                # Está trabajando, esperamos a que se cierre en bestmove, tras parar con stop
                self.manager_analyzer.connect_bestmove(self.bestmove_found)  # Aseguramos que exista
                self.state = AdjudicatorState.closing
                self.manager_analyzer.stop()

            else:
                # No está trabajando, cerramos directamente
                self.manager_analyzer.close()
                self.manager_analyzer = None

    def bestmove_found(self, _bestmove):
        # Solo para cuando el tiempo de análisis es un tiempo fijo y para cerrar el motor cuando está trabajando

        if self.state == AdjudicatorState.analysing:
            self.mrm = self.manager_analyzer.get_current_mrm()
            self.state = AdjudicatorState.active
            if self.user_move is not None:
                self.ensure_moves()
                user_move = self.user_move
                self.user_move = None
                self._rut_player_move(user_move)
            return

        # Si está cerrando, ya podemos cerrar bien
        if self.state == AdjudicatorState.closing:
            self.close()

    def check_moves(self, obj_move: Move.Move, user_move: Move.Move):
        self.obj_move = obj_move
        self.user_move = user_move
        self.mrm = self.manager_analyzer.get_current_mrm()

        if self.book_active:
            if self.check_both_are_bookmoves():
                self._rut_player_move(user_move, book_moves=True)
                return

        if self.is_analysing():
            if self.manager_analyzer.is_run_fixed():
                # sigue por bestmove_found cuando llegue
                return
            else:
                self.ensure_moves()
                self._rut_player_move(user_move)
                return
        else:
            self.manager_analyzer.connect_bestmove(None)  # que no haya interferencias
            self.ensure_moves()
            self._rut_player_move(user_move)

    def check_both_are_bookmoves(self) -> bool:
        fen = self.obj_move.position_before.fen()

        def check_move(from_sq: str, to_sq: str) -> bool:
            p = Position.Position()
            p.read_fen(fen)
            p.play(from_sq, to_sq)
            fenm2 = p.fenm2()
            return OpeningsStd.ap.is_book_fenm2(fenm2)

        si_book_obj: bool = check_move(self.obj_move.from_sq, self.obj_move.to_sq)
        si_book_usu: bool = check_move(self.user_move.from_sq, self.user_move.to_sq)
        if si_book_usu and si_book_obj:
            same = self.obj_move.from_sq == self.user_move.from_sq and self.obj_move.to_sq == self.user_move.to_sq
            self.owner.thinking(False)
            self.analyze_end()
            self.state = AdjudicatorState.active
            bmove = _("book move")
            comment = (
                f"{self.name_obj}: {self.obj_move.pgn_translated()} {bmove}<br>"
                f"{Code.configuration.x_player}: {self.user_move.pgn_translated()} {bmove}"
            )
            if self._message_same_book_moves or not same:
                QTMessages.message_information(self.wowner, comment.replace("\n", "<br>"))
            return True

        elif not si_book_obj:
            self.book_active = False

        return False

    def ensure_moves(self):
        for move in (self.user_move, self.obj_move):
            a1h8 = move.movimiento()
            rm, pos = self.mrm.search_rm(a1h8)
            if rm is None:
                self.analyze_end()
                self.state = AdjudicatorState.active
                self.mrm = self.manager_analyzer.analyze_tutor_move(self.game, move.movimiento())

    def get_adjudicator_options(self) -> tuple:
        dic = Code.configuration.read_variables(self.key)
        nom_engine = dic.get("ENGINE", Code.configuration.x_analyzer_clave)
        conf_multipv = dic.get("MULTIPV", "PD")
        conf_seconds = dic.get("SECONDS", 5.0)
        show_all = dic.get("SHOW_ALL", False)
        if conf_multipv == "PD":
            multipv = Code.configuration.x_analyzer_multipv
        else:
            multipv = conf_multipv
        return nom_engine, multipv, int(conf_seconds * 1000), show_all

    def change_adjudicator_options(self):
        self.manager_analyzer.connect_bestmove(None)  # para que no haya interferencias al hacer stop si analiza
        self.analyze_end()
        self.mrm = None

        dic = Code.configuration.read_variables(self.key)

        nom_engine = dic.get("ENGINE", Code.configuration.x_analyzer_clave)
        multipv = dic.get("MULTIPV", "PD")
        seconds = dic.get("SECONDS", 5.0)
        show_all = dic.get("SHOW_ALL", False)

        form = FormLayout.FormLayout(
            self.wowner, f"{_('Adjudicator')} - {_('Options')}", Iconos.Engines(), with_default=True
        )
        form.separador()
        form.combobox(_("Engine"), Code.configuration.engines.list_name_alias_multipv10(), nom_engine)
        form.separador()
        form.editbox(
            f'{_("Duration of engine analysis (secs)")}<br>{_("0.00=The same time used to move by you")}',
            ancho=60,
            decimales=2,
            tipo=float,
            init_value=seconds,
        )
        form.separador()
        li = Engines.list_depths_to_cb()
        form.combobox(_("Number of variations evaluated by the engine (MultiPV)"), li, multipv)
        form.separador()
        form.checkbox(_("Show all evaluations"), show_all)
        form.separador()
        resp = form.run()
        if resp is not None:
            control, values = resp

            if control == "defecto":
                nom_engine = Code.configuration.x_analyzer_clave
                seconds = 5.0
                multipv = "PD"
                show_all = False
            else:
                nom_engine, seconds, multipv, show_all = values
                seconds = max(seconds, 0.0)

            dic["ENGINE"] = nom_engine
            dic["MULTIPV"] = multipv
            dic["SECONDS"] = seconds
            dic["SHOW_ALL"] = show_all
            Code.configuration.write_variables(self.key, dic)

            self.nom_engine, self.multipv, self.ms_time, self.show_all = self.get_adjudicator_options()
            self.manager_analyzer.close()
            self.manager_analyzer = self.open_manager_analyzer()

        self.analyze_begin(self.game)
