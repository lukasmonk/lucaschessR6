import shutil

import Code
from Code.FindAllMoves import ManagerFindAllMoves
from Code.Base.Constantes import (
    GT_AGAINST_GM,
    GT_TACTICS,
    GT_TURN_ON_LIGHTS,
    ST_PLAYING,
)
from Code.BestMoveTraining import WindowBMT
from Code.Coordinates import WCoordinatesBasic, WCoordinatesBlocks, WCoordinatesWrite
from Code.CountsCaptures import WCountsCaptures
from Code.Endings import ManagerMate, WEndingsGTB
from Code.Expeditions import WindowEverest
from Code.GM import ManagerGM, WindowGM
from Code.Mate15 import WMate15
from Code.Memory import Memory
from Code.QT import Iconos, QTMessages
from Code.ZQT import WindowVisualiza, WindowPuente, WindowPotencia, WindowHorses, WindowDailyTest
from Code.Resistance import ManagerResistance, Resistance, WindowResistance
from Code.Tactics import ManagerTactics, Tactics, WindowTactics
from Code.TrainPositions import TrainPositions
from Code.TurnOnLights import ManagerTurnOnLights, TurnOnLights, WindowTurnOnLights


class TrainMenuRun:
    def __init__(self, train_menu):
        self.train_menu = train_menu
        self.procesador = train_menu.procesador
        self.parent = self.procesador.main_window

    def run(self, resp: str):
        if resp == "gm":
            self.train_gm()

        elif resp.startswith("mate"):
            self.play_mate(int(resp[-1]))

        elif resp == "bmt":
            self.bmt()

        elif resp.startswith("resistance"):
            self.resistance(resp[10:])

        elif resp in ["find_all_moves_rival", "find_all_moves_player"]:
            self.find_all_moves(resp == "find_all_moves_player")

        elif resp == "dailytest":
            self.daily_test()

        elif resp == "potencia":
            self.potencia()

        elif resp == "visualiza":
            self.visualiza()

        elif resp == "anotar":
            self.procesador.show_anotar()

        elif resp == "train_book":
            self.train_book()

        elif resp == "train_book_ol":
            self.train_book_ol()

        elif resp == "endings_gtb":
            self.gaviota_endings()

        elif resp.startswith("tactica|"):
            nada, tipo, name, carpeta, ini, ntactic = resp.split("|")
            self.tacticas(tipo, name, carpeta, ini, ntactic)

        elif resp.startswith("remtactica|"):
            nada, carpeta, name = resp.split("|")
            self.tactics_remove(carpeta, name)

        elif resp.startswith("puente_"):
            self.puente(int(resp[7:]))

        elif resp.startswith("horses_"):
            test = int(resp[7])
            icl, icn, tit = self.train_menu.horses_ico()[test]
            icon = Code.all_pieces.icono(icl, icn)
            self.horses(test, tit, icon)

        elif resp.endswith(".fns"):
            self.positions(resp)

        elif resp == "learnGame":
            self.procesador.learn_game()

        elif resp == "playGame":
            self.procesador.play_game()

        elif resp.startswith("map_"):
            nada, mapa = resp.split("_")
            self.procesador.trainingMap(mapa)

        elif resp == "transsiberian":
            self.procesador.show_route()

        elif resp == "everest":
            self.everest()

        elif resp.startswith("tol_"):
            self.turn_on_lights(resp[4:])

        elif resp == "washing_machine":
            self.washing_machine()

        elif resp == "captures":
            self.captures()

        elif resp == "counts":
            self.counts()

        elif resp == "15mate":
            self.mate15()

        elif resp == "coordinates_blocks":
            self.coordinates_blocks()

        elif resp == "coordinates_basic":
            self.coordinates_basic()

        elif resp == "coordinates_write":
            self.coordinates_write()

        elif resp.startswith("memory"):
            mem = Memory.Memoria(self.procesador)
            if resp == "memory_results":
                mem.show_results()
            else:
                cat = int(resp[7:])
                mem.lanza(cat)

    def tacticas(self, tipo, name, carpeta, ini, ntactic):
        tacticas = Tactics.Tactics(tipo, name, carpeta, ini)
        tactica = tacticas.eligeTactica(ntactic, Code.configuration.paths.folder_results())
        if tactica:
            self.tactics_train(tactica)

    def tactics_remove(self, carpeta, name):
        if QTMessages.pregunta(self.parent, _X(_("Delete %1?"), name)):
            shutil.rmtree(carpeta)

    def tactics_train(self, tactica):
        icono = Iconos.PuntoMagenta()
        resp = WindowTactics.historical_consult(self.parent, tactica, icono)
        if resp:
            if resp != "seguir":
                if resp != "auto":
                    if resp.startswith("copia"):
                        ncopia = int(resp[5:])
                    else:
                        ncopia = None
                    if not WindowTactics.edit1tactica(self.parent, tactica, ncopia):
                        return
                with QTMessages.one_moment_please(self.parent):
                    tactica.genera()
            self.procesador.game_type = GT_TACTICS
            self.procesador.state = ST_PLAYING
            self.procesador.manager = ManagerTactics.ManagerTactics(self.procesador)
            self.procesador.manager.start(tactica)

    def train_gm(self):
        w = WindowGM.WGM(self.procesador)
        if w.exec():
            self.procesador.game_type = GT_AGAINST_GM
            self.procesador.state = ST_PLAYING
            self.procesador.manager = ManagerGM.ManagerGM(self.procesador)
            self.procesador.manager.start(w.record)

    def find_all_moves(self, si_jugador):
        self.procesador.manager = ManagerFindAllMoves.ManagerFindAllMoves(self.procesador)
        self.procesador.manager.start(si_jugador)

    def play_mate(self, tipo):
        self.procesador.manager = ManagerMate.ManagerMate(self.procesador)
        self.procesador.manager.start(tipo)

    def daily_test(self):
        WindowDailyTest.daily_test(self.procesador)

    def potencia(self):
        WindowPotencia.windowPotencia(self.procesador)

    def visualiza(self):
        WindowVisualiza.window_visualiza(self.procesador)

    def train_book(self):
        self.train_book()

    def train_book_ol(self):
        self.procesador.train_book_ol()

    def gaviota_endings(self):
        WEndingsGTB.train_gtb(self.procesador.main_window)

    def puente(self, nivel):
        WindowPuente.window_puente(self.procesador, nivel)

    def horses(self, test, titulo, icono):
        WindowHorses.windowHorses(self.procesador, test, titulo, icono)

    def bmt(self):
        WindowBMT.window_bmt(self.procesador)

    def resistance(self, tipo):
        resistance = Resistance.Resistance(self.procesador, tipo)
        resp = WindowResistance.windowResistance(self.parent, resistance)
        if resp is not None:
            num_engine, key = resp
            self.procesador.manager = ManagerResistance.ManagerResistance(self.procesador)
            self.procesador.manager.start(resistance, num_engine, key)

    def everest(self):
        WindowEverest.everest(self.procesador)

    def turn_on_lights(self, name):
        one_line = False
        if name.startswith("uned_easy"):
            title = f"{_('UNED chess school')} ({_('Initial')})"
            folder = Code.path_resource("Trainings", "Tactics by UNED chess school")
            icono = Iconos.Uned()
            li_tam_blocks = (4, 6, 9, 12, 18, 36)
        elif name.startswith("uned"):
            title = _("UNED chess school")
            folder = Code.path_resource("Trainings", "Tactics by UNED chess school")
            icono = Iconos.Uned()
            li_tam_blocks = (6, 12, 20, 30, 60)
        elif name.startswith("uwe_easy"):
            title = f"{_('Uwe Auerswald')} ({_('Initial')})"
            TurnOnLights.compruebaUweEasy(Code.configuration, name)
            folder = Code.configuration.temporary_folder()
            icono = Iconos.Uwe()
            li_tam_blocks = (4, 6, 9, 12, 18, 36)
        elif name.startswith("uwe"):
            title = _("Uwe Auerswald")
            folder = Code.path_resource("Trainings", "Tactics by Uwe Auerswald")
            icono = Iconos.Uwe()
            li_tam_blocks = (5, 10, 20, 40, 80)
        elif name == "oneline":
            title = _("In one line")
            folder = None
            icono = Iconos.TOLline()
            li_tam_blocks = None
            one_line = True
        else:
            return

        resp = WindowTurnOnLights.window_turn_on_ligths(
            self.procesador, name, title, icono, folder, li_tam_blocks, one_line
        )
        if resp:
            num_theme, num_block, tol = resp
            self.procesador.game_type = GT_TURN_ON_LIGHTS
            self.procesador.state = ST_PLAYING
            self.procesador.manager = ManagerTurnOnLights.ManagerTurnOnLights(self.procesador)
            self.procesador.manager.start(num_theme, num_block, tol)

    def washing_machine(self):
        self.procesador.showWashing()

    def captures(self):
        w = WCountsCaptures.WCountsCaptures(self.procesador, True)
        w.exec()

    def counts(self):
        w = WCountsCaptures.WCountsCaptures(self.procesador, False)
        w.exec()

    def mate15(self):
        w = WMate15.WMate15(self.procesador)
        w.exec()

    def coordinates_blocks(self):
        w = WCoordinatesBlocks.WCoordinatesBlocks(self.procesador)
        w.exec()

    def coordinates_basic(self):
        w = WCoordinatesBasic.WCoordinatesBasic(self.procesador)
        w.exec()

    def coordinates_write(self):
        w = WCoordinatesWrite.WCoordinatesWrite(self.procesador)
        w.exec()

    def positions(self, resp):
        tp = TrainPositions.TrainPositions(self.procesador.main_window)
        tp.train_position(resp)
