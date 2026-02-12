import random
import sys

import Code
from Code import Update
from Code.Z import Adjournments, CPU, ManagerGame, ManagerSolo, Util
from Code.Base import Position
from Code.Base.Constantes import (
    GT_AGAINST_CHILD_ENGINE,
    GT_AGAINST_ENGINE,
    GT_AGAINST_ENGINE_LEAGUE,
    GT_AGAINST_ENGINE_SWISS,
    GT_AGAINST_GM,
    GT_ALBUM,
    GT_BOOK,
    GT_COMPETITION_WITH_TUTOR,
    GT_ELO,
    GT_FICS,
    GT_FIDE,
    GT_HUMAN,
    GT_LICHESS,
    GT_MICELO,
    GT_WICKER,
    ST_PLAYING,
    TB_ADJOURNMENTS,
    TB_COMPETE,
    TB_ENGINES,
    TB_INFORMATION,
    TB_OPTIONS,
    TB_PLAY,
    TB_QUIT,
    TB_REPLAY,
    TB_TOOLS,
    TB_TRAIN,
)
from Code.BestMoveTraining import WindowBMT
from Code.Board import Eboard
from Code.Books import (
    ManagerTrainBooks,
    ManagerTrainBooksOL,
    WBooksTrain,
    WBooksTrainOL,
)
from Code.CompetitionWithTutor import ManagerCompeticion
from Code.Competitions import ManagerElo, ManagerFideFicsLichess, ManagerMicElo, ManagerWicker
from Code.Config import Configuration, WindowConfig
from Code.Databases import DBgames
from Code.Engines import (
    CheckEngines,
    EngineManagerAnalysis,
    EngineManagerPlay,
    EngineRun,
    Engines,
    ListEngineManagers,
    WExternalEngines,
)
from Code.Expeditions import ManagerEverest, WindowEverest
from Code.GM import ManagerGM
from Code.Kibitzers import KibitzersManager
from Code.Leagues import ManagerLeague
from Code.LearnGame import ManagerPlayGame, WindowLearnGame, WindowPlayGame
from Code.MainWindow import MainWindow, Presentacion
from Code.Maps import ManagerMateMap, WindowWorkMap
from Code.Menus import (
    CompeteMenu,
    EnginesMenu,
    InformationMenu,
    OptionsMenu,
    PlayMenu,
    ToolsMenu,
    ToolsMenuRun,
    TrainMenu,
)
from Code.Openings import OpeningsStd
from Code.PlayAgainstEngine import ManagerAlbum, ManagerPerson, ManagerPlayAgainstEngine, WPlayAgainstEngine
from Code.PlayHuman import ManagerPlayHuman
from Code.QT import Iconos, Piezas, QTDialogs
from Code.Routes import ManagerRoutes, Routes, WindowRoutes
from Code.SQL import UtilSQL
from Code.Shortcuts import Shortcuts
from Code.Swiss import ManagerSwiss
from Code.Washing import ManagerWashing, WindowWashing
from Code.WritingDown import ManagerWritingDown, WritingDown


class Procesador:
    user = None
    li_opciones_inicio = None
    configuration = None
    manager = None
    version = None
    board = None
    is_first_time = None
    manager_tutor: EngineManagerAnalysis.EngineManagerAnalysis | None
    manager_analyzer: EngineManagerAnalysis.EngineManagerAnalysis | None

    def __init__(self):
        if Code.list_engine_managers is None:
            Code.list_engine_managers = ListEngineManagers.ListEngineManagers()

        self.main_window = None
        # self.kibitzers_manager = KibitzersManager(self)

    def start_with_user(self, user):
        self.user = user

        self.li_opciones_inicio = [
            TB_QUIT,
            TB_PLAY,
            TB_TRAIN,
            TB_COMPETE,
            TB_TOOLS,
            TB_ENGINES,
            TB_OPTIONS,
            TB_INFORMATION,
        ]  # Lo incluimos aqui porque sino no lo lee, en caso de aplazada

        self.configuration = Configuration.Configuration(user)
        self.configuration.start()
        Code.procesador = self
        Code.runSound.read_sounds()
        OpeningsStd.ap.reset()

        if Code.configuration.x_digital_board:
            Code.eboard = Eboard.Eboard()

        if len(sys.argv) == 1:  # si no no funcionan los kibitzers en linux
            self.configuration.clean_tmp_folder()

        # Tras crear configuración miramos si hay Adjournments
        self.test_opcion_Adjournments()

        Code.all_pieces = Piezas.AllPieces()

        self.manager = None

        self.is_first_time = True
        self.siPresentacion = False  # si esta funcionando la presentacion

        self.posicionInicial = Position.Position()
        self.posicionInicial.set_pos_initial()

        self.manager_rival = None
        self.manager_tutor = None  # creaTutor lo usa asi que hay que definirlo antes
        self.manager_analyzer = None  # cuando se juega ManagerEntMaq y el tutor danzando a toda maquina,
        # se necesita otro diferente
        self.replay = None
        self.replayBeep = None

    def test_opcion_Adjournments(self):
        must_adjourn = len(Adjournments.Adjournments()) > 0
        if TB_ADJOURNMENTS in self.li_opciones_inicio:
            if not must_adjourn:
                pos = self.li_opciones_inicio.index(TB_ADJOURNMENTS)
                del self.li_opciones_inicio[pos]
        else:
            if must_adjourn:
                self.li_opciones_inicio.insert(1, TB_ADJOURNMENTS)

    def set_version(self, version):
        self.version = version

    def iniciar_gui(self):
        if len(sys.argv) > 1:
            comando = sys.argv[1]
            if comando.lower().endswith(".pgn"):
                self.main_window = None
                self.read_pgn(comando)
                return

        # Importante: debe estar antes de la definición de main_window, sino al lanzar ayuda traducción,
        # la reposiciona continuamente con todos las etiquetas traducidas

        self.main_window = MainWindow.MainWindow(self)
        self.main_window.set_manager_active(self)  # antes que muestra
        self.main_window.muestra()
        self.main_window.check_translated_help_mode()
        self.kibitzers_manager = KibitzersManager.Manager(self)

        self.board = self.main_window.board

        self.cpu = CPU.CPU(self.main_window)

        if self.configuration.x_check_for_update:
            Update.test_update(self)

        if len(sys.argv) > 1:
            comando = sys.argv[1]
            comando_l = comando.lower()
            if comando_l.endswith(".lcsb"):
                self.jugarSoloExtern(comando)
                return
            elif comando_l.endswith(".lcdb"):
                self.extern_database(comando)
                return
            elif comando_l.endswith(".bmt"):
                self.start()
                self.externBMT(comando)
                return
            elif comando == "-play":
                fich_tmp = sys.argv[2]
                self.juegaExterno(fich_tmp)
                return

            elif comando == "-playagainst":
                recplay = sys.argv[2]
                self.juegaExternoAgainst(recplay)

        else:
            self.start()

    def extern_database(self, file):
        tm = ToolsMenu.ToolsMenu(self)
        tmr = ToolsMenuRun.ToolsMenuRun(tm)
        tmr.extern_database(file)
        self.run_action(TB_QUIT)

    def openings_lines(self):
        tm = ToolsMenu.ToolsMenu(self)
        tmr = ToolsMenuRun.ToolsMenuRun(tm)
        tmr.openings_lines()

    def externBMT(self, file):
        self.configuration.paths.set_file_bmt(file)
        WindowBMT.window_bmt(self)

    def reset(self):
        self.main_window.activate_analysis_bar(False)
        self.main_window.deactivate_eboard(0)
        self.main_window.activate_captures(False)
        self.main_window.active_information_pgn(False)
        if self.manager:
            self.manager.end_manager()
            self.manager = None
        self.main_window.set_manager_active(self)  # Necesario, no borrar
        self.board.side_indicator_sc.setVisible(False)
        self.board.blindfold_remove()
        self.test_opcion_Adjournments()
        self.main_window.pon_toolbar(self.li_opciones_inicio, shortcuts=True)
        self.main_window.active_game(False, False)
        self.main_window.thinking(False)
        self.board.do_pressed_number = None
        self.board.set_position(self.posicionInicial)
        self.board.remove_movables()
        self.board.remove_arrows()
        self.main_window.adjust_size()
        self.main_window.set_title()
        self.close_engines()

        self.main_window.current_height = self.main_window.height()

    def start(self):
        Code.runSound.close()
        if self.manager:
            self.manager.end_manager()
            del self.manager
            self.manager = None
        self.reset()
        if self.configuration.paths.is_first_time:
            self.cambiaconfigurationPrimeraVez()
            self.configuration.paths.is_first_time = False
            self.main_window.set_title()
        if self.is_first_time:
            self.is_first_time = False
            if self.configuration.x_show_puzzles_on_startup:
                self.presentacion()
        self.kibitzers_manager.stop()

    def presentacion(self, siEmpezar=True):
        self.siPresentacion = siEmpezar
        if not siEmpezar:
            self.cpu.stop()
            self.board.set_side_bottom(True)
            self.board.activa_menu_visual(True)
            self.board.set_position(self.posicionInicial)
            self.board.setToolTip("")
            self.board.lock_rotation(False)

        else:
            self.board.lock_rotation(True)
            self.board.setToolTip("")
            self.board.activa_menu_visual(True)
            Presentacion.ManagerChallenge101(self)

    def get_manager_tutor(self):
        if self.manager_tutor is None:
            self.manager_tutor = self.create_manager_tutor()
        return self.manager_tutor

    def create_manager_tutor(self):
        engine = self.configuration.engines.engine_tutor()
        if engine is None:
            from Code.Engines import CheckEngines
            CheckEngines.check_engines(self.main_window)
            engine = self.configuration.engines.engine_tutor()
        if engine is None:
            return None
        engine.set_multipv_var(self.configuration.x_tutor_multipv)
        run_engine_params = EngineRun.RunEngineParams()
        run_engine_params.update(
            engine, self.configuration.x_tutor_mstime, self.configuration.x_tutor_depth, 0, engine.multiPV
        )
        manager_tutor = EngineManagerAnalysis.EngineManagerAnalysis(engine, run_engine_params)
        manager_tutor.set_priority(self.configuration.x_tutor_priority)
        return manager_tutor

    def change_manager_tutor(self):
        if self.manager_tutor is not None:
            self.manager_tutor.close()
            self.manager_tutor = None
        return self.get_manager_tutor()

    def get_manager_analyzer(self):
        if self.manager_analyzer is None:
            self.manager_analyzer = self.create_manager_analyzer_default()
        return self.manager_analyzer

    def create_manager_analyzer(self, mstime, depth, nodes, multipv):
        engine = self.configuration.engines.engine_analyzer()
        if engine is None:
            from Code.Engines import CheckEngines
            CheckEngines.check_engines(self.main_window)
            engine = self.configuration.engines.engine_analyzer()
        if engine is None:
            return None
        engine.set_multipv_var(self.configuration.x_analyzer_multipv if multipv is None else multipv)
        run_engine_params = EngineRun.RunEngineParams()
        run_engine_params.update(engine, mstime, depth, nodes, engine.multiPV)
        xanalyzer = EngineManagerAnalysis.EngineManagerAnalysis(engine, run_engine_params)
        xanalyzer.set_priority(self.configuration.x_analyzer_priority)
        return xanalyzer

    def create_manager_analyzer_default(self):
        return self.create_manager_analyzer(
            self.configuration.x_analyzer_mstime, self.configuration.x_analyzer_depth, 0, None
        )

    def analyzer_clone(self, mstime, depth, nodes, multipv):
        return self.create_manager_analyzer(mstime, depth, nodes, multipv)

    def change_manager_analyzer(self):
        if self.manager_analyzer is not None:
            self.manager_analyzer.close()
            self.manager_analyzer = None
        return self.get_manager_analyzer()

    @staticmethod
    def create_manager_analysis(
        engine: Engines.Engine, mstime: int, depth: int, nodes: int, multipv: int | str, priority=None
    ):
        assert type(mstime) is int and mstime >= 0
        assert type(depth) is int and depth >= 0
        assert type(nodes) is int and nodes >= 0

        engine.set_multipv_var(multipv)
        run_engine_params = EngineRun.RunEngineParams()
        run_engine_params.update(engine, mstime, depth, nodes, engine.multiPV)
        manager_analysis = EngineManagerAnalysis.EngineManagerAnalysis(engine, run_engine_params)
        if priority is not None:
            manager_analysis.set_priority(priority)
        return manager_analysis

    @staticmethod
    def create_manager_engine(
        engine: Engines.Engine, mstime: int, depth: int, nodes: int, has_multipv=False, priority=None
    ):
        assert type(mstime) is int and mstime >= 0
        assert type(depth) is int and depth >= 0
        assert type(nodes) is int and nodes >= 0

        run_engine_params = EngineRun.RunEngineParams()
        multipv = engine.multiPV if has_multipv else 1
        run_engine_params.update(engine, mstime, depth, nodes, multipv)
        engine_manager = EngineManagerPlay.EngineManagerPlay(engine, run_engine_params)
        if priority is not None:
            engine_manager.set_priority(priority)
        return engine_manager

    def close_engines(self):
        Code.list_engine_managers.close_all()
        self.manager_tutor = None
        self.manager_analyzer = None

    def menu_play(self):
        menu = PlayMenu.PlayMenu(self)
        menu.run()

    def reopen_album(self, album):
        menuplay = PlayMenu.PlayMenu(self)
        tipo, name = album.claveDB.split("_")
        if tipo == "animales":
            menuplay.animals(name)
        elif tipo == "vehicles":
            menuplay.vehicles(name)

    def menu_train(self):
        menu = TrainMenu.TrainMenu(self)
        menu.run()

    def menu_compete(self):
        menu = CompeteMenu.CompeteMenu(self)
        menu.run()

    def menu_tools(self):
        menu = ToolsMenu.ToolsMenu(self)
        menu.run()

    def menu_engines(self):
        menu = EnginesMenu.EnginesMenu(self)
        menu.run()

    def menu_options(self):
        om = OptionsMenu.OptionsMenu(self)
        om.run()

    def menu_information(self):
        im = InformationMenu.InformationMenu(self)
        im.run()

    def run_action(self, key):
        self.main_window.deactivate_eboard(0)

        if self.siPresentacion:
            self.presentacion(False)

        if key == TB_QUIT:
            self.close_engines()
            if hasattr(self, "cpu"):
                self.cpu.stop()
            self.main_window.final_processes()
            self.main_window.accept()

        elif key == TB_PLAY:
            self.check_engines()
            self.menu_play()

        elif key == TB_COMPETE:
            self.check_engines()
            self.menu_compete()

        elif key == TB_TRAIN:
            self.check_engines()
            self.menu_train()

        elif key == TB_ENGINES:
            self.check_engines()
            self.menu_engines()

        elif key == TB_OPTIONS:
            self.check_engines()
            self.menu_options()

        elif key == TB_TOOLS:
            self.check_engines()
            self.menu_tools()

        elif key == TB_INFORMATION:
            self.check_engines()
            self.menu_information()

        elif key == TB_ADJOURNMENTS:
            self.adjournments()

        elif key == TB_REPLAY:
            self.manager.replay_direct()

    def adjournments(self):
        menu = QTDialogs.LCMenu(self.main_window)
        li_adjournments = Adjournments.Adjournments().list_menu()
        for key, label, tp in li_adjournments:
            menu.opcion((True, key, tp), label, Iconos.PuntoMagenta())
            menu.addSeparator()
        menu.addSeparator()
        mr = menu.submenu(_("Remove"), Iconos.Borrar())
        for key, label, tp in li_adjournments:
            mr.opcion((False, key, tp), label, Iconos.Delete())

        resp = menu.lanza()
        if resp:
            si_run, key, tp = resp
            if si_run:
                dic = Adjournments.Adjournments().get(key)

                Adjournments.Adjournments().remove(key)
                if tp == GT_AGAINST_ENGINE:
                    self.manager = ManagerPlayAgainstEngine.ManagerPlayAgainstEngine(self)
                elif tp == GT_ALBUM:
                    self.manager = ManagerAlbum.ManagerAlbum(self)
                elif tp == GT_AGAINST_CHILD_ENGINE:
                    self.manager = ManagerPerson.ManagerPerson(self)
                elif tp == GT_MICELO:
                    self.manager = ManagerMicElo.ManagerMicElo(self)
                elif tp == GT_WICKER:
                    self.manager = ManagerWicker.ManagerWicker(self)
                elif tp == GT_COMPETITION_WITH_TUTOR:
                    self.manager = ManagerCompeticion.ManagerCompeticion(self)
                elif tp == GT_ELO:
                    self.manager = ManagerElo.ManagerElo(self)
                elif tp == GT_AGAINST_GM:
                    self.manager = ManagerGM.ManagerGM(self)
                elif tp in (GT_FIDE, GT_FICS, GT_LICHESS):
                    self.manager = ManagerFideFicsLichess.ManagerFideFicsLichess(self)
                    self.manager.selecciona(tp)
                elif tp == GT_AGAINST_ENGINE_LEAGUE:
                    self.manager = ManagerLeague.ManagerLeague(self)
                elif tp == GT_AGAINST_ENGINE_SWISS:
                    self.manager = ManagerSwiss.ManagerSwiss(self)
                elif tp == GT_HUMAN:
                    self.manager = ManagerPlayHuman.ManagerPlayHuman(self)
                else:
                    return
                self.manager.run_adjourn(dic)
                return

            else:
                Adjournments.Adjournments().remove(key)

            self.test_opcion_Adjournments()
            self.main_window.pon_toolbar(self.li_opciones_inicio, shortcuts=True)

    def launch_shortcuts(self):
        shortcuts = Shortcuts.Shortcuts(self)
        shortcuts.menu()

    def launch_shortcut_with_alt(self, key):
        shortcuts = Shortcuts.Shortcuts(self)
        shortcuts.launch_alt(key)

    def cambiaconfigurationPrimeraVez(self):
        if WindowConfig.options_first_time(self.main_window, self.configuration):
            self.configuration.graba()

    def external_engines(self):
        w = WExternalEngines.WExternalEngines(self.main_window)
        w.exec()
        self.change_manager_tutor()
        self.change_manager_analyzer()

    def show_anotar(self):
        w = WritingDown.WritingDown(self)
        if w.exec():
            game, if_white_below = w.resultado
            if game is None:
                game = DBgames.get_random_game()
            manager = ManagerWritingDown.ManagerWritingDown(self)
            manager.start(game, if_white_below)

    def trainingMap(self, mapa):
        resp = WindowWorkMap.train_map(self, mapa)
        if resp:
            self.manager = ManagerMateMap.ManagerMateMap(self)
            self.manager.start(resp)

    def train_book(self):
        w = WBooksTrain.WBooksTrain(self)
        if w.exec() and w.book_player:
            self.type_play = GT_BOOK
            self.estado = ST_PLAYING
            self.manager = ManagerTrainBooks.ManagerTrainBooks(self)
            self.manager.start(
                w.book_player,
                w.player_highest,
                w.book_rival,
                w.rival_resp,
                w.is_white,
                w.show_menu,
            )

    def train_book_ol(self):
        dbli_books_train = UtilSQL.ListObjSQL(
            Code.configuration.paths.file_train_books_ol(),
            WBooksTrainOL.BooksTrainOL,
            tabla="data",
            is_reversed=True,
        )
        # No es posible con with porque self.manager termina y deja el control en main_window
        w = WBooksTrainOL.WBooksTrainOL(self.main_window, dbli_books_train)
        if w.exec():
            if w.train_rowid is None:
                dbli_books_train.close()
                return
            self.manager = ManagerTrainBooksOL.ManagerTrainBooksOL(self)
            self.manager.start(dbli_books_train, w.train_rowid)
        else:
            dbli_books_train.close()

    def juegaExterno(self, fich_tmp):
        dic_sended = Util.restore_pickle(fich_tmp)
        dic = WPlayAgainstEngine.play_position(self, _("Play a position"), dic_sended["ISWHITE"])
        if dic is None:
            self.run_action(TB_QUIT)
        else:
            side = dic["SIDE"]
            if side == "R":
                side = "B" if random.randint(1, 2) == 1 else "N"
            dic["ISWHITE"] = side == "B"
            self.manager = ManagerPlayAgainstEngine.ManagerPlayAgainstEngine(self)
            self.manager.play_position(dic, dic_sended["GAME"])

    def jugarSoloExtern(self, file_lcsb):
        self.manager = ManagerSolo.ManagerSolo(self)
        self.manager.leeFichero(file_lcsb)

    def juegaExternoAgainst(self, recplay):
        recplay = int(recplay)
        db = WindowPlayGame.DBPlayGame(self.configuration.paths.file_play_game())
        w = WindowPlayGame.WPlay1(self.main_window, self.configuration, db, recplay)
        if w.exec():
            db.close()
            if w.recno is not None:
                is_white = w.is_white
                is_black = w.is_black
                if is_white or is_black:
                    self.manager = ManagerPlayGame.ManagerPlayGame(self)
                    self.manager.start(w.recno, is_white, is_black, close_on_exit=True)
        else:
            db.close()
        return

    def playRoute(self, route):
        if route.state == Routes.BETWEEN:
            self.manager = ManagerRoutes.ManagerRoutesTactics(self)
            self.manager.start(route)
        elif route.state == Routes.ENDING:
            self.manager = ManagerRoutes.ManagerRoutesEndings(self)
            self.manager.start(route)
        elif route.state == Routes.PLAYING:
            self.manager = ManagerRoutes.ManagerRoutesPlay(self)
            self.manager.start(route)

    def show_route(self):
        WindowRoutes.train_train(self)

    def playEverest(self, recno):
        self.manager = ManagerEverest.ManagerEverest(self)
        self.manager.start(recno)

    def showEverest(self, recno):
        if WindowEverest.show_expedition(self.main_window, self.configuration, recno):
            self.playEverest(recno)

    def play_game(self):
        w = WindowPlayGame.WPlayGameBase(self)
        if w.exec():
            recno = w.recno
            if recno is not None:
                is_white = w.is_white
                is_black = w.is_black
                if is_white or is_black:
                    self.manager = ManagerPlayGame.ManagerPlayGame(self)
                    self.manager.start(recno, is_white, is_black)

    def play_game_show(self, recno):
        db = WindowPlayGame.DBPlayGame(self.configuration.paths.file_play_game())
        w = WindowPlayGame.WPlay1(self.main_window, self.configuration, db, recno)
        if w.exec():
            db.close()
            if w.recno is not None:
                is_white = w.is_white
                is_black = w.is_black
                if is_white or is_black:
                    self.manager = ManagerPlayGame.ManagerPlayGame(self)
                    self.manager.start(w.recno, is_white, is_black)
        else:
            db.close()

    def learn_game(self, game=None):
        if game:
            with WindowLearnGame.DBLearnGame() as db:
                db.append_game(game)

        w = WindowLearnGame.WLearnBase(self.main_window)
        w.exec()

    def showTurnOnLigths(self, name):
        tm = TrainMenu.TrainMenu(self)
        tm.run_exec(f"tol_{name}")

    def playWashing(self):
        ManagerWashing.manager_washing(self)

    def showWashing(self):
        if WindowWashing.window_washing(self):
            self.playWashing()

    def read_pgn(self, pgn):
        tm = ToolsMenu.ToolsMenu(self)
        tmr = ToolsMenuRun.ToolsMenuRun(tm)
        tmr.pgn_read(pgn)

    def strenght101(self):
        tm = CompeteMenu.CompeteMenu(self)
        tm.strenght101()

    @staticmethod
    def num_rows():
        return 0

    @staticmethod
    def final_x():
        return True

    @staticmethod
    def final_x0():
        return True

    def clonVariations(self, window, manager_tutor=None, is_competitive=False):
        return ProcesadorVariations(
            window,
            manager_tutor,
            is_competitive=is_competitive,
            kibitzers_manager=self.kibitzers_manager,
        )

    def manager_game(
        self,
        window,
        game,
        is_complete,
        only_consult,
        father_board,
        with_previous_next=None,
        save_routine=None,
    ):
        clon_procesador = ProcesadorVariations(
            window,
            self.manager_tutor,
            is_competitive=False,
            kibitzers_manager=self.kibitzers_manager,
        )
        clon_procesador.manager = ManagerGame.ManagerGame(clon_procesador)
        clon_procesador.manager.start(game, is_complete, only_consult, with_previous_next, save_routine)

        board = clon_procesador.main_window.board
        if father_board:
            board.dbvisual_set_file(father_board.dbVisual.file)
            board.dbvisual_set_show_always(father_board.dbVisual.show_always())

        resp = clon_procesador.main_window.show_variations(game.window_title())
        if father_board:
            father_board.dbvisual_set_file(father_board.dbVisual.file)
            father_board.dbvisual_set_show_always(father_board.dbVisual.show_always())

        if resp:
            return clon_procesador.manager.game
        else:
            return None

    def play_league_human(self, league, xmatch, division):
        self.manager = ManagerLeague.ManagerLeague(self)
        adj = Adjournments.Adjournments()
        key_dic = adj.key_match_league(xmatch)
        if key_dic:
            key, dic_adjourn = key_dic
            adj.remove(key)
            self.manager.run_adjourn(dic_adjourn)
        else:
            self.manager.start(league, xmatch, division)

    def play_swiss_human(self, swiss, xmatch):
        self.manager = ManagerSwiss.ManagerSwiss(self)
        adj = Adjournments.Adjournments()
        key_dic = adj.key_match_swiss(xmatch)
        if key_dic:
            key, dic_adjourn = key_dic
            adj.remove(key)
            self.manager.run_adjourn(dic_adjourn)
        else:
            self.manager.start(swiss, xmatch)

    def check_engines(self):
        return CheckEngines.check_engines(self.main_window)


class ProcesadorVariations(Procesador):
    def __init__(self, window, manager_tutor, is_competitive=False, kibitzers_manager=None):
        self.kibitzers_manager = kibitzers_manager
        self.is_competitive = is_competitive

        self.configuration = Code.configuration

        self.li_opciones_inicio = [
            TB_QUIT,
            TB_PLAY,
            TB_TRAIN,
            TB_COMPETE,
            TB_TOOLS,
            TB_ENGINES,
            TB_OPTIONS,
            TB_INFORMATION,
        ]  # Lo incluimos aqui porque sino no lo lee, en caso de aplazada

        self.siPresentacion = False

        self.main_window = MainWindow.MainWindow(self, window, extparam="mainv")
        self.main_window.set_manager_active(self)
        self.main_window.xrestore_video()

        self.board = self.main_window.board

        self.manager_tutor = manager_tutor
        self.manager_rival = None
        self.manager_analyzer = None

        self.replayBeep = None

        self.posicionInicial = None

        self.cpu = CPU.CPU(self.main_window)
