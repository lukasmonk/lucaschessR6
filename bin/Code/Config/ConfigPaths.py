import os.path

import Code
from Code.Z import Util


class ConfigPaths:
    LCFILEFOLDER: str = os.path.realpath("../lc.folder")
    LCBASEFOLDER: str = os.path.realpath("../UserData")

    def __init__(self, configuration):
        self.configuration = configuration
        self.userdata_folder = self._get_userdata_folder()
        if not os.path.isdir(self.userdata_folder):
            Util.create_folder(self.userdata_folder)
        self.file = self._to_config("lk.pk2")
        self.is_first_time = not Util.exist_file(self.file)

        self._file_bmt = self._to_results("lucas.bmt")

        self.check_resources_sounds()

    def _get_userdata_folder(self):
        if os.path.isfile(self.LCFILEFOLDER):
            with open(self.LCFILEFOLDER, "rt", encoding="utf-8", errors="ignore") as f:
                x = f.read()
                if os.path.isdir(x):
                    return x
        return self.LCBASEFOLDER

    def folder_userdata(self):
        return self.userdata_folder

    def is_default_folder(self):
        return Util.same_path(self.userdata_folder, self.LCBASEFOLDER)

    def change_userdata_folder(self, new_userdata_folder):
        if new_userdata_folder:
            if Util.same_path(new_userdata_folder, self.LCBASEFOLDER):
                self.change_userdata_folder(None)
                return

            with open(self.LCFILEFOLDER, "wt", encoding="utf-8", errors="ignore") as f:
                f.write(new_userdata_folder)
        else:
            Util.remove_file(self.LCFILEFOLDER)

    def change_active_folder(self, nueva):
        self.change_userdata_folder(nueva)
        self.configuration.lee()

    def folder_from_userdata(self, folder):
        folder = os.path.realpath(Util.opj(self.userdata_folder, folder))
        if not Util.exist_folder(folder):
            Util.create_folder(folder)
        return folder

    # ------------------------------------------------------------------------------------- TRANSLATIONS

    def folder_translations(self):
        folder = Util.opj(self.LCBASEFOLDER, "Translations")
        if not os.path.isdir(folder):
            Util.create_folder(folder)
        return folder

    # ------------------------------------------------------------------------------------- CONFIG

    def folder_config(self):
        return self.folder_from_userdata("__Config__")

    def _to_config(self, file):
        return os.path.join(self.folder_config(), file)

    def file_external_engines(self):
        return self._to_config("ExtEngines.pk")

    def file_kibitzers(self):
        return self._to_config("kibitzers.pk")

    def file_adjournments(self):
        return self._to_config("Adjournments.ddb")

    def file_index_polyglots(self):
        return self._to_config("index_polyglots.pk")

    def file_pers_openings(self):
        return self._to_config("persaperturas.pkd")

    def file_video(self):
        return self._to_config("confvid.pkd")

    def file_sounds(self):
        return self._to_config("sounds.pkd")

    def file_param_analysis(self):
        return self._to_config("paranalisis.pkd")

    def file_analysis(self):
        return self._to_config("analisis.db")

    def file_prompts(self):
        return self._to_config("Prompts.db")

    def file_shortcuts(self):
        return self._to_config("Shortcuts.pkd")

    def file_colors(self):
        return self._to_config("personal.colors")

    def file_gms(self):
        return self._to_config("gm.pke")

    def file_books(self):
        return self._to_config("books.lkv")

    def file_conf_play_engine(self):
        return self._to_config("entmaquinaconf.pkd")

    def file_direct_sounds(self):
        return self._to_config("direc.pkv")

    def file_themes(self):
        return self._to_config("themes.pkd")

    def file_resources(self):
        return self._to_config("recursos.dbl")

    def file_writing_down(self):
        return self._to_config("anotar.db")

    def file_filters_pgn(self):
        return self._to_config("pgnFilters.db")

    def file_vars(self):
        return self._to_config("Variables.pk")

    def file_conf_boards(self):
        return self._to_config("confBoards.pk")

    # ------------------------------------------------------------------------------------- PERSONAL TRAINING

    def folder_personal_trainings(self):
        return self.folder_from_userdata("Personal Training")

    def file_singular_moves_save(self):
        return os.path.join(self.folder_personal_trainings(), "Challenge 101.fns")

    # ------------------------------------------------------------------------------------- STS

    def folder_sts(self):
        return self.folder_from_userdata("STS")

    # ------------------------------------------------------------------------------------- SCANNERS

    def folder_scanners(self):
        return self.folder_from_userdata("Scanners")

    # -------------------------------------------------------------------------------------  RESULTS

    def folder_results(self):
        return self.folder_from_userdata("Results")

    def _to_results(self, file):
        return os.path.join(self.folder_results(), file)

    def file_competition_with_tutor(self):
        return self._to_results("CompetitionWithTutor.db")

    def file_mate(self, mate):
        return self._to_results(f"Mate{mate}.pk")

    def file_endings_gtb(self):
        return self._to_results("EndingsGTB.db")

    def file_captures(self):
        return self._to_results("Captures.db")

    def file_counts(self):
        return self._to_results("Counts.db")

    def file_mate15(self):
        return self._to_results("Mate15.db")

    def file_coordinates(self):
        return self._to_results("Coordinates.db")

    def file_coordinates_write(self):
        return self._to_results("CoordinatesWrite.db")

    def file_play_game(self):
        return self._to_results("PlayGame.db")

    def file_learn_game(self):
        return self._to_results("LearnPGN.db")

    def file_train_books_ol(self):
        return self._to_results("booksTrainOL.liobj")

    def file_estad_elo(self):
        return self._to_results("estad.pkli")

    def file_estad_mic_elo(self):
        return self._to_results("estadMic.pkli")

    def file_estad_wicker_elo(self):
        return self._to_results("estadWicker.pkli")

    def file_estad_fics_elo(self):
        return self._to_results("estadFics.pkli")

    def file_estad_fide_elo(self):
        return self._to_results("estadFide.pkli")

    def file_estad_lichess_elo(self):
        return self._to_results("estadLichess.pkli")

    def file_train_books(self):
        return self._to_results("booksTrain.lkv")

    def file_train_memory(self):
        return self._to_results("memo.pk")

    def file_play_engine(self):
        return self._to_results("entmaquina.pke")

    def file_play_engine_extern(self):
        return self._to_results("entmaquinaplay.pke")

    def file_gm_histo(self):
        return self._to_results("gmh.db")

    def file_daily_test(self):
        return self._to_results("nivel.pkd")

    def file_power(self):
        return self._to_results("power.db")

    def file_bridge(self):
        return self._to_results("bridge.db")

    def file_moves(self):
        return self._to_results("moves.dbl")

    def file_boxing(self):
        return self._to_results("boxing.pk")

    def file_trainings(self):
        return self._to_results("trainings.pk")

    def file_horses(self):
        return self._to_results("horses.db")

    def file_albums(self):
        return self._to_results("albumes.pkd")

    def file_expeditions(self):
        return self._to_results("Expeditions.db")

    def file_singular_moves(self):
        return self._to_results("SingularMoves.db")

    def file_washing_machine(self):
        return self._to_results("washing.wsm")

    # -------------------------------------------------------------------------------------  BMT

    def file_bmt(self):
        return self._file_bmt

    def set_file_bmt(self, file):
        if Util.exist_file(file):
            self._file_bmt = file

    def check_file_bmt(self):
        if not Util.exist_file(self._file_bmt):
            self._file_bmt = self._to_results("lucas.bmt")

    # -------------------------------------------------------------------------------------  TACTICS

    def folder_tactics(self):
        return self.folder_from_userdata("Tactics")

    # -------------------------------------------------------------------------------------  TOURNAMENTS

    def folder_tournaments(self):
        return self.folder_from_userdata("Tournaments")

    def folder_tournaments_workers(self):
        return self.folder_from_userdata("Tournaments/Workers")

    def folder_leagues(self):
        return self.folder_from_userdata("Leagues")

    def folder_swisses(self):
        return self.folder_from_userdata("Swiss")

    # -------------------------------------------------------------------------------------  DATABASES

    def folder_databases(self):
        return self.folder_from_userdata("Databases")

    def folder_databases_pgn(self):
        return self.folder_from_userdata("TemporaryDatabases")

    def to_databases(self, file):
        return os.path.join(self.folder_databases(), file)

    def file_autosave(self):
        return self.to_databases("__Autosave__.lcdb")

    def file_selected_positions(self):
        return self.to_databases("__Selected Positions__.lcdb")

    # -------------------------------------------------------------------------------------  OPENINGS

    def folder_pieces_png(self):
        return self.folder_from_userdata("Figs")

    def folder_base_openings(self):
        return self.folder_from_userdata("OpeningLines")

    def folder_openings(self):
        dic = self.configuration.read_variables("OPENING_LINES")
        folder = dic.get("FOLDER", self.folder_base_openings())
        return folder if os.path.isdir(folder) else self.folder_base_openings

    def set_folder_openings(self, new_folder):
        new_folder = Util.relative_path(os.path.realpath(new_folder))
        dic = self.configuration.read_variables("OPENING_LINES")
        dic["FOLDER"] = new_folder
        self.configuration.write_variables("OPENING_LINES", dic)

    # -------------------------------------------------------------------------------------  SOUNDS

    def folder_sounds(self):
        return self.folder_from_userdata("Sounds")

    # -------------------------------------------------------------------------------------  POLYGLOTS

    def folder_polyglots_factory(self):
        return self.folder_from_userdata("PolyglotsFactory")

    # -------------------------------------------------------------------------------------  CHECKS

    def check_resources_sounds(self):
        if not Util.exist_file(self.file_resources()):
            Util.file_copy(Code.path_resource("IntFiles", "recursos.dbl"), self.file_resources())

        if not Util.exist_file(self.file_sounds()):
            Util.file_copy(Code.path_resource("IntFiles", "sounds.pkd"), self.file_sounds())

    # -----------------------------------------------------------------------------------

    def folder_save_lcsb(self, nuevo=None):
        if nuevo:
            self.configuration.x_save_lcsb = nuevo
            self.configuration.graba()
        return self.configuration.x_save_lcsb or self.folder_userdata()
