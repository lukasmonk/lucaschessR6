import os.path
import pickle

from PySide6 import QtWidgets
from PySide6.QtCore import Qt

import Code
from Code.Z import Util
from Code.Analysis import AnalysisEval
from Code.Base.Constantes import (
    DBSHOW_INITIAL_POSITION,
    DBSHOW_LAST_MOVE,
    DICT_GAME_TYPES,
    GO_FORWARD,
    INACCURACY,
    MENU_PLAY_BOTH,
    POS_TUTOR_HORIZONTAL,
)
from Code.Board import ConfBoards
from Code.Config import ConfigEngines, ConfigPaths
from Code.Engines import Priorities
from Code.QT import IconosBase, ScreenUtils
from Code.SQL import UtilSQL
from Code.Translations import Translate, TrListas


def int_toolbutton(xint):
    return next(
        (
            tbi
            for tbi in (
                Qt.ToolButtonStyle.ToolButtonIconOnly,
                Qt.ToolButtonStyle.ToolButtonTextOnly,
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
                Qt.ToolButtonStyle.ToolButtonTextUnderIcon,
            )
            if xint == tbi.value
        ),
        Qt.ToolButtonStyle.ToolButtonTextUnderIcon,
    )


def toolbutton_int(qt_tbi):
    if qt_tbi in (
        Qt.ToolButtonStyle.ToolButtonIconOnly,
        Qt.ToolButtonStyle.ToolButtonTextOnly,
        Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
        Qt.ToolButtonStyle.ToolButtonTextUnderIcon,
    ):
        return qt_tbi.value
    return Qt.ToolButtonStyle.ToolButtonTextUnderIcon.value


class BoxRooms:
    def __init__(self, configuration):
        self.file = Util.opj(configuration.paths.folder_config(), "boxrooms.pk")
        self._list = self.read()

    def read(self):
        obj = Util.restore_pickle(self.file)
        return [] if obj is None else obj

    def write(self):
        Util.save_pickle(self.file, self._list)

    def lista(self):
        return self._list

    def delete(self, num):
        del self._list[num]
        self.write()

    def append(self, carpeta, boxroom):
        self._list.append((carpeta, boxroom))
        self.write()


class Configuration:
    def __init__(self, user):

        Code.configuration = self

        self.paths = ConfigPaths.ConfigPaths(self)

        self.user = user

        self.is_main = user == "" or user is None

        self.version = ""

        self.x_id = Util.huella()
        self.x_player = ""
        self.x_save_folder = "UserData"
        self.x_save_pgn_folder = ""
        self.x_save_lcsb = ""
        self.x_translator = ""

        self.x_show_effects = False
        self.x_pieces_speed = 100
        self.x_save_tutor_variations = True

        self.x_mouse_shortcuts = False
        self.x_show_candidates = False

        self.x_captures_activate = True
        self.x_captures_mode_diferences = True
        self.x_info_activate = False
        self.x_show_bestmove = True
        self.x_show_rating = False

        self.x_default_tutor_active = True

        self.x_elo = 0
        self.x_michelo = 1500
        self.x_wicker = 400
        self.x_fics = 1200
        self.x_fide = 1600
        self.x_lichess = 1600

        self.x_digital_board = ""
        self.x_wheel_board = GO_FORWARD
        self.x_wheel_pgn = GO_FORWARD

        self.x_menu_play = MENU_PLAY_BOTH
        self.x_menu_play_config = True

        self.x_opacity_tool_board = 10
        self.x_position_tool_board = "T"

        self.x_movement_doublebox_board = False

        self.x_director_icon = False
        self.x_direct_graphics = False

        self.x_sizefont_messages = 14

        self.x_sizefont_infolabels = 11
        self.x_sizefont_players = 16

        self.x_pgn_width = 348
        self.x_pgn_fontpoints = 11
        self.x_pgn_rowheight = 24
        self.x_pgn_withfigurines = True

        self.x_databases_rowheight = 24

        self.x_pgn_english = False

        self.x_autopromotion_q = False

        self.x_copy_ctrl = True  # False = Alt C

        self.x_font_family = ""
        self.x_font_points = 11

        self.x_menu_points = 11
        self.x_menu_bold = False

        self.x_tb_fontpoints = 11
        self.x_tb_bold = False
        self.x_tb_icons = toolbutton_int(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.x_tb_orientation_horizontal = True

        self.x_cursor_thinking = True

        self.x_rival_inicial = "rocinante" if Util.is_linux() else "irina"

        self.tutor_default = "stockfish"
        self.x_tutor_clave = self.tutor_default
        self.x_tutor_multipv = 10  # 0: maximo
        self.x_tutor_diftype = INACCURACY
        self.x_tutor_mstime = 3000
        self.x_tutor_depth = 0
        self.x_tutor_priority = Priorities.priorities.low
        self.x_tutor_view = POS_TUTOR_HORIZONTAL

        self.analyzer_default = "stockfish"
        self.x_analyzer_clave = self.analyzer_default
        self.x_analyzer_multipv = 10  # 0: maximo
        self.x_analyzer_mstime = 3000
        self.x_analyzer_depth = 0
        self.x_analyzer_priority = Priorities.priorities.low

        self.x_analyzer_depth_ab = 24
        self.x_analyzer_mstime_ab = 0
        self.x_analyzer_autorotate_ab = True
        self.x_analyzer_mstime_refresh_ab = 200
        self.x_analyzer_activate_ab = False

        self.x_maia_nodes_exponential = False

        self.x_eval_limit_score = 2000  # Score in cps means 100% Win
        self.x_eval_curve_degree = 30  # Degree of curve cps and probability of win

        self.x_eval_difmate_inaccuracy = 3  # Dif mate considered an inaccuracy
        self.x_eval_difmate_mistake = 12  # Dif mate considered a mistake
        self.x_eval_difmate_blunder = 20  # Dif mate considered a blunder

        self.x_eval_mate_human = 15  # Max mate to consider

        self.x_eval_blunder = 15.5  #
        self.x_eval_mistake = 7.5
        self.x_eval_inaccuracy = 3.3

        self.x_eval_very_good_depth = 8
        self.x_eval_good_depth = 5
        self.x_eval_speculative_depth = 3

        self.x_eval_max_elo = 3300.0
        self.x_eval_min_elo = 200.0

        self.x_eval_elo_blunder_factor = 12
        self.x_eval_elo_mistake_factor = 6
        self.x_eval_elo_inaccuracy_factor = 2

        self.dic_eval_default = self.read_eval()

        self.x_sound_beep = False
        self.x_sound_our = False
        self.x_sound_move = False
        self.x_sound_results = False
        self.x_sound_error = False
        self.x_sound_tournements = False

        self.x_interval_replay = 1400
        self.x_beep_replay = False

        self.x_margin_pieces = 10

        self.x_engine_notbackground = False

        self.x_check_for_update = False

        self.x_carpeta_gaviota = self.carpeta_gaviota_defecto()

        self.x_captures_showall = True
        self.x_counts_showall = True

        self.li_shortcuts = None

        self.li_personalities = []

        self.rival = None

        self.x_translation_mode = False
        self.x_use_googletranslator = False

        self.x_style = "Fusion"
        self.x_style_mode = "By default"
        self.x_style_icons = IconosBase.icons.NORMAL
        self.style_sheet_default = None  # temporary var

        self.x_mode_select_lc = False

        self.x_show_puzzles_on_startup = True

        self.x_prevention_crashes = True

        self.x_dbshow_positions = DBSHOW_INITIAL_POSITION
        self.x_dbshow_completegames = DBSHOW_LAST_MOVE

        self.x_msrefresh_poll_engines = 50

        self._dic_books = None

        self.__theme_num = 1  # 1=red 2=old

        self.engines: ConfigEngines.ConfigEngines = ConfigEngines.ConfigEngines(self)
        self.dic_conf_boards_pk = {}

    def get_folder_default(self, folder):
        return folder or self.paths.folder_userdata()

    def save_folder(self):
        return self.get_folder_default(self.x_save_folder)

    def set_save_folder(self, folder):
        self.x_save_folder = folder
        self.graba()

    @property
    def dic_books(self):
        if self._dic_books is None:
            self._dic_books = {}

            def add_folder(folder):
                entry: os.DirEntry
                for entry in os.scandir(folder):
                    if entry.is_dir():
                        add_folder(entry.path)
                    elif entry.name.endswith(".bin"):
                        self._dic_books[entry.name] = entry.path

            add_folder(Code.path_resource("Openings"))
            for engine in ("foxcub", "fox", "maia", "irina", "rodentii"):
                add_folder(Util.opj(Code.folder_engines, engine))
        return self._dic_books

    def path_book(self, alias):
        return self.dic_books[alias]

    def read_eval(self):
        return {key[7:]: getattr(self, key) for key in dir(self) if key.startswith("x_eval_")}

    @staticmethod
    def dic_eval_keys():
        return {
            "limit_score": (1000, 4000, "int"),
            "curve_degree": (1, 100, "%"),
            "difmate_inaccuracy": (1, 99, "int"),
            "difmate_mistake": (1, 99, "int"),
            "difmate_blunder": (1, 99, "int"),
            "mate_human": (10, 99, "int"),
            "blunder": (1.0, 99.0, "dec"),
            "mistake": (1.0, 99.0, "dec"),
            "inaccuracy": (1.0, 99.0, "dec"),
            "very_good_depth": (1, 128, "int"),
            "good_depth": (1, 128, "int"),
            "speculative_depth": (1, 128, "int"),
            "max_elo": (2000, 4000, "int"),
            "min_elo": (0, 2000, "int"),
            "elo_blunder_factor": (1, 99, "dec"),
            "elo_mistake_factor": (1, 99, "dec"),
            "elo_inaccuracy_factor": (1, 99, "dec"),
        }

    def boxrooms(self):
        return BoxRooms(self)

    def nom_player(self):
        return self.x_player or _("Player")

    @staticmethod
    def carpeta_gaviota_defecto():
        return Code.path_resource("Gaviota")

    def folder_gaviota(self):
        if not Util.exist_file(Util.opj(self.x_carpeta_gaviota, "kbbk.gtb.cp4")):
            self.x_carpeta_gaviota = self.carpeta_gaviota_defecto()
            self.graba()
        return self.x_carpeta_gaviota

    def pieces_gaviota(self):
        if Util.exist_file(Util.opj(self.folder_gaviota(), "kbbkb.gtb.cp4")):
            return 5
        return 4

    def pieces_speed_porc(self):
        sp = min(self.x_pieces_speed, 300)
        return sp / 100.0

    def set_player(self, value):
        self.x_player = value

    def translator(self):
        return self.x_translator or "en"

    def language(self):
        tr_actual = self.translator()
        dlang = Code.path_resource("Locale")
        fini = Util.opj(dlang, tr_actual, "lang.ini")
        dic = Util.ini_dic(fini)
        return dic["NAME"]

    def set_translator(self, xtranslator):
        self.x_translator = xtranslator

    def type_icons(self):
        return int_toolbutton(self.x_tb_icons)

    def set_type_icons(self, qtv):
        self.x_tb_icons = toolbutton_int(qtv)

    def start(self):
        self.lee()
        self.engines.reset()
        # TODO para qué sirve rival?
        self.rival = self.engines.search(self.x_rival_inicial)
        self.read_conf_boards()

    def create_base_folder(self, folder):
        folder = os.path.realpath(Util.opj(self.paths.folder_userdata(), folder))
        Util.create_folder(folder)
        return folder

    def limpia(self, name):
        self.x_elo = 0
        self.x_michelo = 1600
        self.x_fics = 1200
        self.x_fide = 1600
        self.x_id = Util.huella()
        self.x_player = name
        self.x_save_folder = ""
        self.x_save_pgn_folder = ""
        self.x_save_lcsb = ""

        self.x_captures_activate = False
        self.x_info_activate = False
        self.x_mouse_shortcuts = False
        self.x_show_candidates = False

        self.rival = self.engines.search(self.x_rival_inicial)

    @staticmethod
    def estilos():
        return [(x, x) for x in QtWidgets.QStyleFactory.keys()]

    def graba(self):
        dic = {x: getattr(self, x) for x in dir(self) if x.startswith("x_")}
        # dic["PALETTE"] = self.palette
        dic["PERSONALITIES"] = self.li_personalities
        Util.save_pickle(self.paths.file, dic)

    def lee(self):
        if dic := Util.restore_pickle(self.paths.file):
            for x in dir(self):
                if x.startswith("x_") and x in dic:
                    setattr(self, x, dic[x])
            if "x_sizefont_players" not in dic:
                self.x_sizefont_players = self.x_sizefont_infolabels + 2
            # self.palette = dic.get("PALETTE", self.palette)
            self.li_personalities = dic.get("PERSONALITIES", self.li_personalities)

        for x in os.listdir(Code.current_dir):
            if x.endswith(".pon"):
                os.remove(os.path.join(Code.current_dir, x))
                self.x_translator = x[:2]
        self.load_translation()

        TrListas.pon_pieces_lng(self.x_pgn_english or self.translator() == "en")

        Code.analysis_eval = AnalysisEval.AnalysisEval()

        IconosBase.icons.reset(self.x_style_icons)

    def get_last_database(self):
        dic = self.read_variables("DATABASE")
        return dic.get("LAST_DATABASE", "")

    def set_last_database(self, last_database):
        self._write_variables_key("DATABASE", "LAST_DATABASE", last_database)

    def load_translation(self):
        dlang = Code.path_resource("Locale")
        fini = Util.opj(dlang, self.x_translator, "lang.ini")
        if not os.path.isfile(fini):
            self.x_translator = "en"
        Translate.install(self.x_translator)

    @staticmethod
    def list_translations(others=False):
        li = []
        dlang = Code.path_resource("Locale")
        for uno in Util.listdir(dlang):
            fini = Util.opj(dlang, uno.name, "lang.ini")
            if os.path.isfile(fini):
                dic = Util.ini_dic(fini)
                if others:
                    li.append(
                        (
                            uno.name,
                            dic["NAME"],
                            int(dic["%"]),
                            dic.get("AUTHOR", ""),
                            dic.get("PREVIOUS", ""),
                        )
                    )
                else:
                    li.append((uno.name, dic["NAME"], int(dic["%"]), dic.get("AUTHOR", "")))
        return sorted(li, key=lambda lng: f"AAA{lng[0]}" if lng[1] > "Z" else lng[1])

    def elo_current(self):
        return self.x_elo

    def micelo_current(self):
        return self.x_michelo

    def wicker_current(self):
        return self.x_wicker

    def fics_current(self):
        return self.x_fics

    def fide_current(self):
        return self.x_fide

    def lichess_current(self):
        return self.x_lichess

    def set_current_elo(self, elo):
        self.x_elo = elo

    def set_current_micelo(self, elo):
        self.x_michelo = elo

    def set_wicker(self, elo):
        self.x_wicker = elo

    def set_current_fics(self, elo):
        self.x_fics = elo

    def set_current_fide(self, elo):
        self.x_fide = elo

    def set_current_lichess(self, elo):
        self.x_lichess = elo

    def po_saved(self):
        return Util.opj(self.paths.folder_translations(), f"{self.x_translator}.po")

    def temporary_folder(self):
        dir_tmp = Util.opj(self.paths.folder_userdata(), "tmp")
        Util.create_folder(dir_tmp)
        return dir_tmp

    def temporary_file(self, extension):
        dir_tmp = Util.opj(self.paths.folder_userdata(), "tmp")
        return Util.temporary_file(dir_tmp, extension)

    def clean_tmp_folder(self):
        try:

            def remove_folder(folder, root):
                if "UserData" in folder and "tmp" in folder:
                    entry: os.DirEntry
                    for entry in Util.listdir(folder):
                        if entry.is_dir():
                            remove_folder(entry.path, False)
                        elif entry.is_file():
                            Util.remove_file(entry.path)
                    if not root:
                        os.rmdir(folder)

            remove_folder(self.temporary_folder(), True)
        except:
            pass

    def read_variables(self, key_var):
        with UtilSQL.DictSQL(self.paths.file_vars()) as db:
            resp = db[key_var]
        return resp or {}

    def write_variables(self, key_var, dic_valores):
        with UtilSQL.DictSQL(self.paths.file_vars()) as db:
            db[key_var] = dic_valores

    def _write_variables_key(self, key_var, key_val, value):
        dic = self.read_variables(key_var)
        dic[key_val] = value
        self.write_variables(key_var, dic)

    def change_theme_num(self, num):
        self.__theme_num = num

    def read_conf_boards(self):
        with UtilSQL.DictSQL(self.paths.file_conf_boards()) as db:
            self.dic_conf_boards_pk = db.as_dictionary()
            if "BASE" not in self.dic_conf_boards_pk:
                with open(
                    Code.path_resource("IntFiles", f"basepk{self.__theme_num}.board"),
                    "rb",
                ) as f:
                    var = pickle.loads(f.read())
                    alto = ScreenUtils.desktop_height()
                    ancho = ScreenUtils.desktop_width()
                    if Code.procesador:
                        ancho_extra = Code.procesador.main_window.get_noboard_width() + 40
                    else:
                        ancho_extra = 660
                    max_ancho_pieza = (ancho - ancho_extra) // 8
                    max_alto_pieza = ((alto - 200) * 86 / 100) // 8
                    alt_ancho_pieza = min(max_ancho_pieza, max_alto_pieza)
                    if alt_ancho_pieza > 10:
                        ancho_pieza = alt_ancho_pieza
                    else:
                        base = ancho * 950 / 1495
                        if alto > base:
                            alto = base
                        ancho_pieza = int(alto * 8 / 100)

                    var["x_anchoPieza"] = ancho_pieza
                    db["BASE"] = self.dic_conf_boards_pk["BASE"] = var
            # Para cambiar el tema por defecto por el actual
            # with open("../resources/IntFiles/basepk(((1,2,3))).board", "wb") as f:
            #       f.write(pickle.dumps(db["BASE"], protocol=4))

    def size_base(self):
        return self.dic_conf_boards_pk["BASE"]["x_anchoPieza"]

    def reset_conf_board(self, key, size_default):
        db = UtilSQL.DictSQL(self.paths.file_conf_boards())
        del db[key]
        db.close()
        self.read_conf_boards()
        return self.config_board(key, size_default)

    def change_conf_board(self, config_board):
        if xid := config_board.id():
            db = UtilSQL.DictSQL(self.paths.file_conf_boards())
            self.dic_conf_boards_pk[xid] = db[xid] = config_board.graba()
            db.close()
            self.read_conf_boards()

    def config_board(self, xid, tam_def, father="BASE"):
        if xid == "BASE":
            ct = ConfBoards.ConfigBoard(xid, tam_def)
        else:
            ct = ConfBoards.ConfigBoard(xid, tam_def, father=father)
            ct.width_piece(tam_def)

        if xid in self.dic_conf_boards_pk:
            ct.lee(self.dic_conf_boards_pk[xid])
        else:
            db = UtilSQL.DictSQL(self.paths.file_conf_boards())
            self.dic_conf_boards_pk[xid] = db[xid] = ct.graba()
            db.close()

        ct._anchoPiezaDef = tam_def

        return ct

    def save_video(self, key, dic):
        db = UtilSQL.DictSQL(self.paths.file_video())
        db[key] = dic
        db.close()

    def restore_video(self, key):
        db = UtilSQL.DictSQL(self.paths.file_video())
        dic = db[key]
        db.close()
        return dic

    def pgn_folder(self):
        return self.get_folder_default(self.x_save_pgn_folder)

    def save_pgn_folder(self, new_folder):
        if self.x_save_pgn_folder != new_folder:
            self.x_save_pgn_folder = new_folder
            self.graba()

    def set_property(self, owner, valor):
        if self.x_style_mode == "By default":
            owner.setStyleSheet(self.style_sheet_default)
        owner.setProperty("type", valor)

    def get_auto_rotate(self, game_type):
        key = DICT_GAME_TYPES[game_type]
        dic = self.read_variables("AUTO_ROTATE")
        return dic.get(key, False)

    def set_auto_rotate(self, game_type, auto_rotate):
        key = DICT_GAME_TYPES[game_type]
        dic = self.read_variables("AUTO_ROTATE")
        dic[key] = auto_rotate
        self.write_variables("AUTO_ROTATE", dic)

    def wheel_board(self, forward):
        return forward if self.x_wheel_board == GO_FORWARD else not forward

    def wheel_pgn(self, forward):
        return forward if self.x_wheel_pgn != GO_FORWARD else not forward
