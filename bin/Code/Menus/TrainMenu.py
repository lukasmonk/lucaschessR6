import os
from pathlib import Path

import Code
from Code import Util
from Code.Base.Constantes import (
    TACTICS_BASIC,
    TACTICS_PERSONAL,
)
from Code.CompetitionWithTutor import CompetitionWithTutor
from Code.Memory import Memory
from Code.Menus import BaseMenu, TrainMenuRun
from Code.QT import Iconos, QTDialogs
from Code.Tactics import Tactics
from Code.Translations import TrListas


class TrainMenu(BaseMenu.RootMenu):
    name = "Train"
    submenu_training_positions: BaseMenu.SubMenu

    def add_options(self):
        self.basics()
        self.tactics()
        self.games()
        self.openings()
        self.endings()
        self.longterm()

    def longterm(self):
        submenu_longterm = self.new_submenu(_("Long-term trainings"), Iconos.Longhaul())

        submenu_maps = submenu_longterm.new_submenu(_("Training on a map"), Iconos.Maps())
        submenu_maps.new("map_Africa", _("Africa map"), Iconos.Africa())
        submenu_maps.new("map_WorldMap", _("World map"), Iconos.WorldMap())

        submenu_longterm.new("transsiberian", _("Transsiberian Railway"), Iconos.Train())
        submenu_longterm.new("everest", _("Expeditions to the Everest"), Iconos.Trekking())
        submenu_longterm.new("washing_machine", _("The Washing Machine"), Iconos.WashingMachine())

    def openings(self):
        submenu_openings = self.new_submenu(_("Openings"), Iconos.Openings())
        submenu_openings.new("train_book_ol", _("Train the opening lines of a book"), Iconos.Libros())
        submenu_openings.new("train_book", _("Training with a book"), Iconos.Book())

    def endings(self):
        submenu_endings = self.new_submenu(_("Endings"), Iconos.Training_Endings())

        submenu_mates = submenu_endings.new_submenu(_("Training mates"), Iconos.Mate())
        for mate in range(1, 8):
            submenu_mates.new(f"mate{mate}", _X(_("Mate in %1"), str(mate)), Iconos.PuntoAzul())

        submenu_endings.new("15mate", _X(_("Mate in %1"), "1½"), Iconos.Mate15())

        submenu_endings.new("endings_gtb", _("Endings with Gaviota Tablebases"), Iconos.Finales())

    def games(self):
        submenu_games = self.new_submenu(_("Games"), Iconos.Training_Games())

        submenu_games.new("gm", _("Play like a Grandmaster"), Iconos.GranMaestro())

        submenu_games.new("captures", _("Captures and threats in a game"), Iconos.Captures())

        submenu_games.new("counts", _("Count moves"), Iconos.Count())

        submenu_resistence = submenu_games.new_submenu(_("Resistance Test"), Iconos.Resistencia())
        nico = Util.Rondo(Iconos.Verde(), Iconos.Azul(), Iconos.Amarillo(), Iconos.Naranja())
        submenu_resistence.new("resistance", _("Normal"), nico.otro())
        submenu_resistence.new("resistancec", _("Blindfold chess"), nico.otro())
        submenu_resistence.new("resistancep1", _("Hide only our pieces"), nico.otro())
        submenu_resistence.new("resistancep2", _("Hide only opponent pieces"), nico.otro())

        submenu_learn = submenu_games.new_submenu(_("Learn a game"), Iconos.School())
        submenu_learn.new("learnGame", _("Memorizing their moves"), Iconos.LearnGame())
        submenu_learn.new("playGame", _("Playing against"), Iconos.Law())

    def basics(self):
        submenu_basic = self.new_submenu(_("Basics"), Iconos.Training_Basic())

        self.memory(submenu_basic)

        self.find_all_moves(submenu_basic)

        self.horses(submenu_basic)

        self.moves_between(submenu_basic)

        submenu_basic.new("visualiza", _("The board at a glance"), Iconos.Gafas())

        self.coordinates(submenu_basic)

        submenu_basic.new("anotar", _("Writing down moves of a game"), Iconos.Write())

    def memory(self, submenu_basic):
        submenu_memory = submenu_basic.new_submenu(_("Check your memory on a chessboard"), Iconos.Memoria())
        mem = Memory.Memoria(self.procesador)
        categorias = CompetitionWithTutor.Categorias()
        for x in range(6):
            cat = categorias.number(x)
            txt = cat.name()

            nm = mem.nivel(x)
            if nm >= 0:
                txt += " " + TrListas.level(nm + 1)

            submenu_memory.new(f"memory_{x}", txt, cat.icono(), enabled=mem.is_active(x), sep=False)
        submenu_memory.new("memory_results", _("Results"), Iconos.Estadisticas2())

    @staticmethod
    def find_all_moves(submenu_basic):
        submenu_find_all_moves = submenu_basic.new_submenu(_("Find all moves"), Iconos.FindAllMoves())
        submenu_find_all_moves.new("find_all_moves_player", _("Player"), Iconos.PuntoAzul())
        submenu_find_all_moves.new("find_all_moves_rival", _("Opponent"), Iconos.PuntoNaranja())

    @staticmethod
    def horses_ico():
        return {
            1: ("N", "Alpha", _("By default")),
            2: ("p", "Fantasy", _("Four pawns test")),
            3: ("Q", "Pirat", _("Jonathan Levitt test")),
            4: ("n", "Spatial", "a1"),
            5: ("N", "Cburnett", "e4"),
        }

    def horses(self, submenu_basic):
        submenu_horses = submenu_basic.new_submenu(_("Becoming a knight tamer"), Iconos.Knight())
        vicon = Code.all_pieces.icono

        hd = self.horses_ico()
        icl, icn, tit = hd[1]
        submenu_basic = submenu_horses.new_submenu(_("Basic test"), vicon(icl, icn))
        submenu_basic.new("horses_1", tit, vicon(icl, icn))
        icl, icn, tit = hd[4]
        submenu_basic.new("horses_4", tit, vicon(icl, icn))
        icl, icn, tit = hd[5]
        submenu_basic.new("horses_5", tit, vicon(icl, icn))

        icl, icn, tit = hd[2]
        submenu_horses.new("horses_2", tit, vicon(icl, icn))
        icl, icn, tit = hd[3]
        submenu_horses.new("horses_3", tit, vicon(icl, icn))

    @staticmethod
    def moves_between(submenu_basic):
        submenu_moves_between = submenu_basic.new_submenu(_("Moves between two positions"), Iconos.Puente())
        rp = QTDialogs.rondo_puntos()
        for x in range(1, 11):
            submenu_moves_between.new("puente_%d" % x, TrListas.level(x), rp.otro())

    @staticmethod
    def coordinates(submenu_basic):
        submenu_coordinates = submenu_basic.new_submenu(_("Coordinates"), Iconos.Coordinates())
        submenu_coordinates.new("coordinates_basic", _("Basic"), Iconos.West())
        submenu_coordinates.new("coordinates_blocks", _("By blocks"), Iconos.Blocks())
        submenu_coordinates.new("coordinates_write", _("Visualise and write"), Iconos.CoordinatesWrite())

    def tactics(self):
        submenu_tactics = self.new_submenu(_("Tactics"), Iconos.Training_Tactics())

        self.training_positions(submenu_tactics)

        self.tactics_by_repetition(submenu_tactics)

        submenu_tactics.new("bmt", _("Find best move"), Iconos.BMT())

        submenu_tactics.new("dailytest", _("Your daily test"), Iconos.DailyTest())

        submenu_tactics.new("potencia", _("Determine your calculating power"), Iconos.Potencia())

        self.turn_on_the_lights(submenu_tactics)

    @staticmethod
    def turn_on_the_lights(submenu_tactics):
        submenu_turn_on_the_ligths = submenu_tactics.new_submenu(_("Turn on the lights"), Iconos.TOL())

        submenu_memory_mode = submenu_turn_on_the_ligths.new_submenu(_("Memory mode"), Iconos.TOL())
        submenu_memory_mode.new("tol_uned_easy", f'{_("UNED chess school")} ({_("Initial")})', Iconos.Uned())
        submenu_memory_mode.new(
            "tol_uned",
            f'{_("UNED chess school")} ({_("Complete")})',
            Iconos.Uned(),
            sep=False,
        )
        submenu_memory_mode.new("tol_uwe_easy", f'{_("Uwe Auerswald")} ({_("Initial")})', Iconos.Uwe())
        submenu_memory_mode.new(
            "tol_uwe",
            f'{_("Uwe Auerswald")} ({_("Complete")})',
            Iconos.Uned(),
            sep=False,
        )

        submenu_memory_mode = submenu_turn_on_the_ligths.new_submenu(_("Calculation mode"), Iconos.TOL())
        submenu_memory_mode.new(
            "tol_uned_easy_calc",
            f'{_("UNED chess school")} ({_("Initial")})',
            Iconos.Uned(),
        )
        submenu_memory_mode.new(
            "tol_uned_calc",
            f'{_("UNED chess school")} ({_("Complete")})',
            Iconos.Uned(),
            sep=False,
        )
        submenu_memory_mode.new("tol_uwe_easy_calc", f'{_("Uwe Auerswald")} ({_("Initial")})', Iconos.Uwe())
        submenu_memory_mode.new(
            "tol_uwe_calc",
            f'{_("Uwe Auerswald")} ({_("Complete")})',
            Iconos.Uned(),
            sep=False,
        )

        submenu_turn_on_the_ligths.new("tol_oneline", _("Turn on lights in one line"), Iconos.TOLline())

    def training_positions(self, submenu_tactics):
        icono_fns = Iconos.Kibitzer_Board()
        icono_base = Iconos.FolderGreen()

        icono_personal = Iconos.Carpeta()

        self.submenu_training_positions = submenu_tactics.new_submenu(_("Training positions"), icono_base)

        def gen_folder(folder: str, submenu, icono):
            base_path = Path(folder)
            archivos_fns = list(base_path.rglob('*.fns'))
            archivos_fns.sort()
            rutas_relativas = []
            for archivo_path in archivos_fns:
                ruta_relativa = str(archivo_path.relative_to(base_path))
                rutas_relativas.append((archivo_path, ruta_relativa))

            estructura_menu = {}

            for path, ruta in rutas_relativas:
                # Divide la ruta en partes usando el separador del sistema operativo
                partes = ruta.split(os.sep)

                # 'puntero' es el diccionario actual donde estamos añadiendo el elemento
                puntero = estructura_menu

                for i, parte in enumerate(partes):
                    # Si es la última parte, es el nombre del archivo
                    if i == len(partes) - 1:
                        # Esto diferencia un archivo de una carpeta (que es otro dict)
                        puntero[parte] = str(path)
                    else:
                        # Si la parte no está en el diccionario, la inicializamos como un nuevo diccionario (carpeta)
                        if parte not in puntero:
                            puntero[parte] = {}
                        # Movemos el puntero al sub-diccionario (la siguiente carpeta)
                        puntero = puntero[parte]

            def crear_menu_recursivo(xestructura_menu, xsubmenu):
                for clave, valor in xestructura_menu.items():
                    if isinstance(valor, dict):
                        # Si el valor es un diccionario, es una carpeta (submenú)
                        rsubmenu = xsubmenu.new_submenu(clave, icono)
                        crear_menu_recursivo(valor, rsubmenu)
                    else:
                        xsubmenu.new(valor, _F(clave[:-4]), icono_fns)

            crear_menu_recursivo(estructura_menu, submenu)

        gen_folder(Code.path_resource("Trainings"), self.submenu_training_positions, icono_base)

        submenu_personal = self.submenu_training_positions.new_submenu(_("Personal training"), icono_personal)
        gen_folder(
            Code.configuration.paths.folder_personal_trainings(),
            submenu_personal,
            icono_personal,
        )
        submenu_tactics = self.submenu_training_positions.new_submenu(_("Personal tactics"), icono_personal)
        gen_folder(Code.configuration.paths.folder_tactics(), submenu_tactics, icono_personal)

    def add_menu_positions(self, menu):
        self.check_pending()
        for option in self.submenu_training_positions.li_options:
            option.add_to_menu(menu)

    @staticmethod
    def tactics_by_repetition(submenu_tactics):
        submenu_tactics_by_repetition = submenu_tactics.new_submenu(_("Learn tactics by repetition"), Iconos.Tacticas())
        nico_submenu = QTDialogs.rondo_colores(False)
        nico_opcion = QTDialogs.rondo_puntos(False)
        dic_training = TrListas.dic_training()

        def tr_training(txt):
            return dic_training.get(txt, _F(txt))

        def menu_tacticas(submenu, tipo, carpeta_base, xlista):
            if os.path.isdir(carpeta_base):
                entry: os.DirEntry
                for entry in os.scandir(carpeta_base):
                    if entry.is_dir():
                        xcarpeta = entry.path
                        ini = Util.opj(xcarpeta, "Config.ini")
                        if os.path.isfile(ini):
                            xname = entry.name
                            tacticas = Tactics.Tactics(tipo, xname, xcarpeta, ini)
                            li_menus = tacticas.listaMenus()
                            n_menus = len(li_menus)
                            if n_menus == 0:
                                continue
                            if n_menus == 1:
                                submenu.new(
                                    f"tactica|{tipo}|{xname}|{xcarpeta}|{ini}|{li_menus[0][0]}",
                                    tr_training(xname),
                                    nico_opcion.otro(),
                                )
                            else:
                                submenu_tactica = submenu.new_submenu(tr_training(xname), nico_submenu.otro())

                                dmenu = {}
                                for valor, tlista in li_menus:
                                    actmenu = submenu_tactica
                                    if len(tlista) > 1:
                                        t = ""
                                        for x in range(len(tlista) - 1):
                                            t += "|%s" % tlista[x]
                                            if t not in dmenu:
                                                v_trad = dic_training.get(tlista[x], _F(tlista[x]))
                                                dmenu[t] = actmenu.new_submenu(v_trad, nico_submenu.otro())
                                            actmenu = dmenu[t]
                                    tname = _F(dic_training.get(tlista[-1], tlista[-1]))
                                    actmenu.new(
                                        f"tactica|{tipo}|{xname}|{xcarpeta}|{ini}|{valor}",
                                        tname,
                                        nico_opcion.otro(),
                                    )

                            xlista.append((xcarpeta, xname))
            return xlista

        menu_tacticas(
            submenu_tactics_by_repetition,
            TACTICS_BASIC,
            Code.path_resource("Tactics"),
            [],
        )
        lista = []
        carpeta_tacticas_p = Code.configuration.paths.folder_tactics()
        if os.path.isdir(carpeta_tacticas_p):
            submenu1 = submenu_tactics_by_repetition.new_submenu(_("Personal tactics"), nico_submenu.otro())
            lista = menu_tacticas(submenu1, TACTICS_PERSONAL, carpeta_tacticas_p, lista)
            if lista:
                ico = Iconos.Delete()
                submenu_remove = submenu_tactics_by_repetition.new_submenu(_("Remove"), ico)
                for carpeta, name in lista:
                    submenu_remove.new("remtactica|%s|%s" % (carpeta, name), tr_training(name), ico)

    def run_select(self, resp):
        tm = TrainMenuRun.TrainMenuRun(self)
        tm.run(resp)
