import Code
from Code import Util
from Code.Base import Game, Position
from Code.Base.Constantes import BOOK_RANDOM_UNIFORM, ENG_WICKER


def read_wicker_engines():
    configuration = Code.configuration
    file = Code.path_resource("IntFiles", "wicker.ini")

    dic_wicker = Util.ini2dic(file)
    li = []
    for alias, dic in dic_wicker.items():
        nom_base_engine = dic["ENGINE"]
        id_info = dic["IDINFO"]
        li_info = [_F(x.strip()) for x in id_info.split(",")]
        id_info = "\n".join(li_info)
        elo = int(dic["ELO"])
        li_uci = [v.split(":") for k, v in dic.items() if k.startswith("OPTION")]
        nom_book = dic["BOOK"]
        book_rr = dic.get("BOOKRR", BOOK_RANDOM_UNIFORM)
        book = configuration.path_book(nom_book)
        max_plies = int(dic.get("BOOKMAXPLY", 0))
        if max_plies == 0:
            if elo >= 2200:
                max_plies = 9999
            else:
                max_plies = round((elo / 1000) + 3.5 * (elo / 1000) * (elo / 1000))

        engine = configuration.engines.dic_engines().get(nom_base_engine)
        if engine:
            eng = engine.clone()
            eng.name = _SP(alias)
            eng.id_info = id_info
            eng.alias = alias
            eng.elo = elo
            eng.liUCI = li_uci
            eng.book = book
            eng.book_max_plies = max_plies
            eng.book_rr = book_rr
            eng.type = ENG_WICKER
            li.append(eng)

    li.sort(key=lambda uno: uno.elo)
    return li


class WickerCtrl:
    """
    To control Wicker engines that do not lose by time
    Used in EngineManagerPlay
    """

    def __init__(self, engine_run):
        self.engine_run = engine_run

    def check(self, game: Game.Game | None = None, movement: int | None = None, fen: str | None = None) -> bool:

        if game is not None:
            position = game.last_position if movement is None else game.move(movement).position
        else:
            position = Position.Position()
            position.read_fen(fen)

        dic_pieces = position.dic_pieces()

        def count(str_pz):
            return sum(dic_pieces.get(pz, 0) for pz in str_pz)

        ok = False

        if position.is_white:
            if count("pnbrq") == 0:
                ok = count('QR') >= 1
        else:
            if count("PNBRQ") == 0:
                ok = count('qr') >= 1

        if ok:
            engine_run = self.engine_run

            engine_run.set_option("UCI_LimitStrength", "true")
            engine_run.set_option("UCI_Elo", "2300")
            engine_run.set_option("Hash", "16")
            exe = self.engine_run.path_exe()
            if "rodentii" in exe:
                engine_run.set_option("NpsLimit", "10000")
            elif "greko98" in exe:
                # Greko98 cannot mate when RandomEval or MultiPV are too high.
                engine_run.set_option("RandomEval", "2")
                engine_run.set_option("MultiPV", "1")
            elif "maia" in exe:
                # Maia doesn't understand UCI_Elo and needs a high NPS value.
                engine_run.set_option("NodesPerSecondLimit", "170")
            elif "irina" in exe:
                # Irina doesn't understand UCI_Elo.
                engine_run.set_option("NpsLimit", "25000")
            engine_run.isready()
            return True
        else:
            return False


def check_is_wicker(engine, engine_run) -> WickerCtrl | None:
    return WickerCtrl(engine_run) if engine.type == ENG_WICKER else None
