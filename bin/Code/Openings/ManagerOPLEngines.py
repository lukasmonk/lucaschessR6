import random
import time
from typing import Optional

from PySide6.QtCore import Qt

from Code.Base import Game, Move
from Code.Base.Constantes import (
    BOOK_BEST_MOVE,
    GOOD_MOVE,
    GT_OPENING_LINES,
    ST_ENDGAME,
    ST_PLAYING,
    TB_CLOSE,
    TB_CONFIG,
    TB_NEXT,
    TB_REINIT,
    TB_REPEAT,
    TB_RESIGN,
    TB_UTILITIES,
    TOP_RIGHT,
)
from Code.Books import Books
from Code.Engines import EngineManagerAnalysis, EngineManagerPlay, EngineRun
from Code.Engines import EngineResponse
from Code.ManagerBase import Manager
from Code.Openings import OpeningLines
from Code.QT import Iconos, QTDialogs, QTMessages


class ManagerOpeningEngines(Manager.Manager):
    file_path: str
    numengine: int
    level: int
    ask_movesdifferent: bool
    auto_analysis: bool
    plies_pendientes: int
    error: str
    ini_time: float
    with_help: bool
    dict_fenm2: dict
    errores: int
    li_info: list
    plies_mandatory: int
    plies_control: int
    lost_points: int
    key_rival: str
    key_rival_cache: str
    time: float
    is_approved: bool
    is_human_side_white: bool
    book: Books.Book | None
    keybook_engine: str
    manager_adjudicator: EngineManagerAnalysis.EngineManagerAnalysis
    manager_rival: Optional[EngineManagerPlay.EngineManagerPlay] = None
    um: Optional[QTMessages.WaitingMessage] = None
    mstime_adjudicator: int
    key_adjudicator_cache: str
    training_engines: dict
    dbop: OpeningLines.Opening
    mstime_rival: int

    def start(self, path):
        self.board.save_visual_state()
        self.file_path = path
        dbop = OpeningLines.Opening(path)
        self.board.dbvisual_set_file(dbop.path_file)
        self.reinicio(dbop)

    def reinicio(self, dbop):
        self.dbop = dbop
        self.dbop.open_cache_engines()
        self.game_type = GT_OPENING_LINES

        self.level = self.dbop.getconfig("ENG_LEVEL", 0)
        self.numengine = self.dbop.getconfig("ENG_ENGINE", 0)

        self.training_engines = self.dbop.training_engines()

        self.auto_analysis = self.training_engines.get("AUTO_ANALYSIS", True)
        self.ask_movesdifferent = self.training_engines.get("ASK_MOVESDIFFERENT", False)

        li_times = self.training_engines.get("TIMES")
        if not li_times:
            li_times = [500, 1000, 2000, 4000, 8000]
        li_books = self.training_engines.get("BOOKS")
        if not li_books:
            li_books = ["", "", "", "", ""]
        li_books_sel = self.training_engines.get("BOOKS_SEL")
        if not li_books_sel:
            li_books_sel = ["", "", "", "", ""]
        li_engines = self.training_engines["ENGINES"]
        num_engines_base = len(li_engines)
        li_engines_ext = [key for key in self.training_engines.get("EXT_ENGINES", []) if key not in li_engines]
        num_engines = num_engines_base + len(li_engines_ext)

        if self.numengine >= num_engines:
            self.level += 1
            self.numengine = 0
            self.dbop.setconfig("ENG_LEVEL", self.level)
            self.dbop.setconfig("ENG_ENGINE", 0)
        num_levels = len(li_times)
        if self.level >= num_levels:
            if QTMessages.pregunta(
                self.main_window,
                f"{_('Training finished')}.\n{_('Do you want to reinit?')}",
            ):
                self.dbop.setconfig("ENG_LEVEL", 0)
                self.dbop.setconfig("ENG_ENGINE", 0)
                self.reinicio(dbop)
            return

        if self.numengine < num_engines_base:
            self.key_rival = li_engines[self.numengine]
        else:
            self.key_rival = li_engines_ext[self.numengine - num_engines_base]
        self.key_rival_cache = f"RIVAL{self.key_rival}"

        self.mstime_rival = li_times[self.level]
        nombook = li_books[self.level]
        if nombook:
            list_books = Books.ListBooks()
            self.book = list_books.seek_book(nombook)
            if self.book:
                self.book.polyglot()
                self.book.mode = li_books_sel[self.level]
                if not self.book.mode:
                    self.book.mode = BOOK_BEST_MOVE
                self.key_rival_cache = self.key_rival_cache + nombook
        else:
            self.book = None

        self.plies_mandatory = self.training_engines["MANDATORY"]
        self.plies_control = self.training_engines["CONTROL"]
        self.plies_pendientes = self.plies_control
        self.lost_points = self.training_engines["LOST_POINTS"]

        self.is_human_side_white = self.training_engines["COLOR"] == "WHITE"
        self.is_engine_side_white = not self.is_human_side_white

        self.is_approved = False

        rival = self.configuration.engines.search(self.key_rival)
        self.manager_rival = self.procesador.create_manager_engine(rival, self.mstime_rival, 0, 0)
        self.manager_rival.is_white = self.is_engine_side_white

        engine_adjudicator = self.configuration.engines.search(self.training_engines["ENGINE_CONTROL"])
        self.mstime_adjudicator = int(self.training_engines["ENGINE_TIME"] * 1000)
        run_engine_params = EngineRun.RunEngineParams()
        run_engine_params.update(engine_adjudicator, self.mstime_adjudicator, 0, 0, 10)
        self.manager_adjudicator = EngineManagerAnalysis.EngineManagerAnalysis(engine_adjudicator, run_engine_params)
        self.key_adjudicator_cache = f"adjudicator{engine_adjudicator.name}"

        self.li_info = [
            f"<b>{_('Engine')}</b>: {self.numengine + 1}/{num_engines} - {self.manager_rival.engine.name}",
            f'<b>{_('Level')}</b>: {self.level + 1}/{num_levels} - {self.mstime_rival / 1000.0:.1f}"',
        ]

        self.dict_fenm2 = self.training_engines["DICFENM2"]

        self.with_help = False
        self.board.dbvisual_set_show_always(False)
        self.hints = 9999  # Para que analice sin problemas

        self.game = Game.Game()

        self.set_toolbar((TB_CLOSE, TB_RESIGN, TB_REINIT))
        self.main_window.active_game(True, False)
        self.set_dispatcher(self.player_has_moved_dispatcher)
        self.set_position(self.game.last_position)
        self.show_side_indicator(True)
        self.remove_hints()
        self.put_pieces_bottom(self.is_human_side_white)
        self.pgn_refresh(True)

        self.show_info_extra()

        self.state = ST_PLAYING

        self.check_boards_setposition()

        self.errores = 0
        self.ini_time = time.time()
        self.show_labels()
        self.play_next_move()

    def play_next_move(self):
        self.show_labels()
        if self.state == ST_ENDGAME:
            return

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.put_view()

        is_white = self.game.last_position.is_white

        self.set_side_indicator(is_white)
        self.refresh()

        is_rival = is_white == self.is_engine_side_white

        if not self.run_control():
            if is_rival:
                self.disable_all()
                if self.play_rival():
                    self.play_next_move()
            else:
                self.activate_side(is_white)
                self.human_is_playing = True

    def play_rival(self):
        fen = self.game.last_position.fen()
        fenm2 = self.game.last_position.fenm2()
        li_a1h8 = self.dict_fenm2.get(fenm2, set())
        if len(li_a1h8) == 0:
            si_obligatorio = False
        else:
            si_obligatorio = len(self.game) <= self.plies_mandatory

        a1h8 = None

        if si_obligatorio:
            # Para los movimientos del rival,guardamos el movimiento, para los de análisis el mrm
            # por si se repite que repita los mismos movimientos
            a1h8 = self.dbop.get_cache_engines(self.key_rival_cache, self.mstime_rival, fen)
            if a1h8 is None:
                if self.book:
                    a1h8_book = self.book.select_move_type(fen, self.book.mode)
                    if a1h8_book in list(li_a1h8):
                        a1h8 = a1h8_book
                if a1h8 is None:
                    a1h8 = random.choice(list(li_a1h8))

        if a1h8 is None:
            a1h8 = self.dbop.get_cache_engines(self.key_rival_cache, self.mstime_rival, fen)
            if a1h8 is None and self.book:
                fen = self.game.last_position.fen()
                a1h8 = self.book.select_move_type(fen, self.book.mode)
            if a1h8 is None:
                rm_rival = self.manager_rival.play_game(self.game)
                a1h8 = rm_rival.movimiento()

        self.dbop.set_cache_engines(self.key_rival_cache, self.mstime_rival, fen, a1h8)

        from_sq, to_sq, promotion = a1h8[:2], a1h8[2:4], a1h8[4:]
        ok, mens, move = Move.get_game_move(self.game, self.game.last_position, from_sq, to_sq, promotion)
        if ok:
            self.add_move(move, False)
            self.move_the_pieces(move.list_piece_moves, True)

            self.error = ""

            return True
        else:
            self.error = mens
            return False

    def player_has_moved_dispatcher(self, from_sq, to_sq, promotion=""):
        move = self.check_human_move(from_sq, to_sq, promotion)
        if not move:
            self.beep_error()
            return False

        fenm2 = self.game.last_position.fenm2()
        li_mv = self.dict_fenm2.get(fenm2, [])
        nmv = len(li_mv)
        if nmv > 0:
            if move.movimiento() not in li_mv:
                for mv in li_mv:
                    self.board.create_arrow_multi(mv, False)
                self.board.create_arrow_multi(move.movimiento(), True)
                if self.ask_movesdifferent:
                    mensaje = (
                        f"{_('This is not the move in the opening lines')}\n"
                        f"{_('Do you want to go on with this move?')}"
                    )
                    if not QTMessages.pregunta(self.main_window, mensaje):
                        self.set_end_game_opl()
                        return True
                else:
                    self.message_on_pgn(_("This is not the move in the opening lines, you must repeat the game"))
                    self.set_end_game_opl()
                    return True

        self.move_the_pieces(move.list_piece_moves)

        self.add_move(move, True)
        self.play_next_move()
        return True

    def add_move(self, move, is_player_move):
        fenm2 = move.position_before.fenm2()
        move.is_line = False
        if fenm2 in self.dict_fenm2:
            if move.movimiento() in self.dict_fenm2[fenm2]:
                move.add_nag(GOOD_MOVE)
                move.is_line = True
        self.game.add_move(move)
        self.check_boards_setposition()

        self.put_arrow_sc(move.from_sq, move.to_sq)
        self.beep_extended(is_player_move)

        self.pgn_refresh(self.game.last_position.is_white)
        self.refresh()

    def show_labels(self):
        li = []
        li.extend(self.li_info)

        si_obligatorio = len(self.game) < self.plies_mandatory
        if si_obligatorio and self.state != ST_ENDGAME:
            fenm2 = self.game.last_position.fenm2()
            moves = self.dict_fenm2.get(fenm2, [])
            if len(moves) > 0:
                li.append(f"<b>{_('Mandatory movements')}</b>: {len(self.game) + 1}/{self.plies_mandatory}")
            else:
                si_obligatorio = False

        if not si_obligatorio and self.state != ST_ENDGAME:
            tm = self.plies_pendientes
            if tm > 1 and len(self.game) and not self.game.move(-1).is_line:
                li.append(f"{_('Moves until the control')}: {tm - 1}")

        self.set_label1("<br>".join(li))

    def run_auto_analysis(self):
        list_num_moves = []
        for num_move in range(self.game.num_moves()):
            move = self.game.move(num_move)
            if move.is_white() == self.is_human_side_white:
                fenm2 = move.position.fenm2()
                if fenm2 not in self.dict_fenm2:
                    list_num_moves.append(num_move)
        total = len(list_num_moves)
        move_max = 0
        for pos, num_move in enumerate(list_num_moves, 1):
            if self.is_canceled():
                break
            self.place_in_movement(num_move)
            self.waiting_message(add_to_title=f"{pos}/{total}")
            move = self.game.move(num_move)
            mrm, rm, pos = self.analyze_move(num_move)

            move.analysis = mrm, pos
            self.main_window.base.pgn_refresh()
            if pos == 0:
                move_max += 1

        return move_max < total  # si todos son lo máximo aunque pierda algo hay que darlo por aprobado

    def place_in_movement(self, movenum):
        row = (movenum + 1) // 2 if self.game.starts_with_black else movenum // 2
        move: Move.Move = self.game.move(movenum)
        is_white = move.position_before.is_white
        self.main_window.place_on_pgn_table(row, is_white)
        self.set_position(move.position)
        self.put_view()

    def waiting_message(self, is_end=False, add_to_title=None):
        if is_end:
            if self.um:
                self.um.final()
        else:
            if self.um is None:
                self.um = QTMessages.temporary_message(
                    self.main_window,
                    _("Analyzing"),
                    0,
                    physical_pos=TOP_RIGHT,
                    with_cancel=True,
                    tit_cancel=_("Cancel"),
                )
            if add_to_title:
                self.um.label(f"{_('Analyzing')} {add_to_title}")

    def is_canceled(self):
        si = self.um.is_canceled()
        if si:
            self.um.final()
        return si

    def analyze_move(self, num_move):
        move: Move.Move = self.game.move(num_move)
        fen: str = move.position_before.fen()
        vtime: float = self.mstime_adjudicator
        mrm: Optional[EngineResponse.MultiEngineResponse] = self.dbop.get_cache_engines(
            self.key_adjudicator_cache, vtime, fen
        )
        if mrm is not None:
            rm, pos = mrm.search_rm(move.movimiento())
            if rm is None:
                mrm = None

        if mrm is None:
            self.waiting_message()
            mrm, pos = self.manager_adjudicator.analyze_move(self.game, num_move, None)

        rm, pos = mrm.search_rm(move.movimiento())
        move.analysis = mrm, pos
        self.dbop.set_cache_engines(self.key_adjudicator_cache, vtime, fen, mrm)
        return mrm, rm, pos

    def run_control(self):
        # puntos_final, mate_final = 0, 0
        num_moves = len(self.game)
        if num_moves == 0:
            return False

        self.um = None  # controla one_moment_please

        def aprobado():
            menst = f"<b><span style=\"color:green\">{_('Congratulations, goal achieved')}</span></b>"
            self.li_info.append("")
            self.li_info.append(menst)
            self.show_labels()
            self.dbop.setconfig("ENG_ENGINE", self.numengine + 1)
            self.message_on_pgn(menst)
            self.is_approved = True

        def suspendido():
            menst = f"<b><span style=\"color:red\">{_('You must repeat the game')}</span></b>"
            self.li_info.append("")
            self.li_info.append(menst)
            self.show_labels()
            self.message_on_pgn(menst)

        move = self.game.move(-1)
        if self.game.is_finished():
            self.set_end_game_opl()
            if move.is_mate:
                if move.is_white() == self.is_human_side_white:
                    aprobado()
                else:
                    suspendido()
                self.set_end_game_opl()
                return True
            puntos_final, mate_final = 0, 0

        else:
            if move.is_line:
                return False

            self.plies_pendientes = self.plies_control
            for num in range(len(self.game) - 1, -1, -1):
                if self.game.move(num).is_line:
                    break
                else:
                    self.plies_pendientes -= 1
            self.plies_pendientes = max(self.plies_pendientes, 0)
            # si el último movimiento no es nuestro, esperamos
            if self.plies_pendientes > 0 or move.is_white() != self.is_human_side_white:
                return False
            self.waiting_message()
            mrm, rm, pos = self.analyze_move(len(self.game) - 1)
            puntos_final, mate_final = rm.puntos, rm.mate

        # Calculamos el score de inicio
        num_move = next((num for num in range(len(self.game) - 1, -1, -1) if self.game.move(num).is_line), -1)
        if num_move == -1:
            puntos_inicio, mate_inicio = 0, 0
        else:
            mrm, rm, pos = self.analyze_move(num_move)
            puntos_inicio, mate_inicio = rm.puntos, rm.mate
            last_move = self.game.move(num_move)
            if self.is_human_side_white != last_move.is_white():
                puntos_inicio, mate_inicio = -puntos_inicio, -mate_inicio

        self.li_info.append(f"<b>{_('Score')}:</b>")
        template = "&nbsp;&nbsp;&nbsp;&nbsp;<b>%s</b>: %d"

        def append_info(label, puntos, mate):
            menst = f"{template % (label, puntos)}"
            if mate:
                menst += f' {_("Mate")} {mate}'
            self.li_info.append(menst)

        append_info(_("Begin"), puntos_inicio, mate_inicio)
        append_info(_("End"), puntos_final, mate_final)
        perdidos = puntos_inicio - puntos_final
        ok = perdidos < self.lost_points
        if mate_inicio or mate_final:
            ok = mate_final > mate_inicio
        mens = template % ('(%d)-(%d)' % (puntos_inicio, puntos_final), perdidos)
        mens = f"{mens} %s %d" % ('&lt;' if ok else '&gt;', self.lost_points)
        self.li_info.append(mens)

        if not ok:
            if self.auto_analysis:
                si_suspendido = self.run_auto_analysis()
            else:
                si_suspendido = True
            self.waiting_message(is_end=True)
            if si_suspendido:
                suspendido()
            else:
                aprobado()
        else:
            self.waiting_message(is_end=True)
            aprobado()

        self.set_end_game_opl()
        return True

    def run_action(self, key):
        if key == TB_CLOSE:
            self.end_game()

        elif key in (TB_REINIT, TB_NEXT):
            self.reiniciar()

        elif key == TB_REPEAT:
            self.dbop.setconfig("ENG_ENGINE", self.numengine)
            self.reiniciar()

        elif key == TB_RESIGN:
            self.set_end_game_opl()

        elif key == TB_CONFIG:
            self.configurar(with_sounds=True)

        elif key == TB_UTILITIES:
            li_extra_options = [
                ("books", _("Consult a book"), Iconos.Libros()),
                (None, None, None),
                (None, _("Options"), Iconos.Opciones()),
            ]
            mens = _("Cancel") if self.auto_analysis else _("Enable")
            li_extra_options.append(
                (
                    "auto_analysis",
                    f"{_('Automatic analysis')}: {mens}",
                    Iconos.Analizar(),
                )
            )
            li_extra_options.append((None, None, None))
            mens = _("Cancel") if self.ask_movesdifferent else _("Enable")
            li_extra_options.append(
                (
                    "ask_movesdifferent",
                    f"{_('Ask when the moves are different from the line')}: {mens}",
                    Iconos.Pelicula_Seguir(),
                )
            )
            li_extra_options.append((None, None, True))  # Para salir del submenu
            li_extra_options.append((None, None, None))
            li_extra_options.append(("run_analysis", _("Specific analysis"), Iconos.Analizar()))
            li_extra_options.append((None, None, None))
            li_extra_options.append(("add_line", _("Add this line"), Iconos.OpeningLines()))

            resp = self.utilities(li_extra_options)
            if resp == "books":
                self.consult_books(False)

            elif resp == "add_line":
                num_moves, nj, row, is_white = self.current_move()
                game = self.game
                if num_moves != nj + 1:
                    menu = QTDialogs.LCMenu(self.main_window)
                    menu.opcion("all", _("Add all moves"), Iconos.PuntoAzul())
                    menu.separador()
                    menu.opcion("parcial", _("Add until current move"), Iconos.PuntoVerde())
                    resp = menu.lanza()
                    if resp is None:
                        return
                    if resp == "parcial":
                        game = self.game.copia(nj)

                self.dbop.append(game)
                self.dbop.update_training_engines()
                QTMessages.message_bold(self.main_window, _("Done"))

            elif resp == "auto_analysis":
                self.auto_analysis = not self.auto_analysis
                self.training_engines["AUTO_ANALYSIS"] = self.auto_analysis
                self.dbop.set_training_engines(self.training_engines)

            elif resp == "ask_movesdifferent":
                self.ask_movesdifferent = not self.ask_movesdifferent
                self.training_engines["ASK_MOVESDIFFERENT"] = self.ask_movesdifferent
                self.dbop.set_training_engines(self.training_engines)

            elif resp == "run_analysis":
                self.um = None
                self.waiting_message()
                self.run_auto_analysis()
                self.waiting_message(is_end=True)

        else:
            self.routine_default(key)

    def final_x(self):
        return self.end_game()

    def end_game(self):
        self.dbop.close()
        self.board.restore_visual_state()
        self.procesador.start()
        self.procesador.openings_lines()
        return False

    def reiniciar(self):
        self.procesador.close_engines()
        self.main_window.active_information_pgn(False)
        self.reinicio(self.dbop)

    def set_end_game_opl(self):
        self.state = ST_ENDGAME
        self.disable_all()
        li_options = [TB_CLOSE]
        if self.is_approved:
            li_options.append(TB_NEXT)
            li_options.append(TB_REPEAT)
        else:
            li_options.append(TB_REINIT)
        li_options.append(TB_CONFIG)
        li_options.append(TB_UTILITIES)
        self.set_toolbar(li_options)

    def control_teclado(self, nkey):
        if nkey in (Qt.Key.Key_Plus, Qt.Key.Key_PageDown):
            if self.main_window.is_enabled_option_toolbar(TB_NEXT):
                self.run_action(TB_NEXT)
