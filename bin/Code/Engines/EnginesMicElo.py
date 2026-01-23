import Code
from Code.Z import Util
from Code.Base.Constantes import ENG_MICGM, ENG_MICPER
from Code.Engines import Engines


class EngineTourneys(Engines.Engine):
    points_win: int
    points_draw: int
    points_lose: int

    def read_engine(self, engine: Engines.Engine):
        self.restore(engine.save())


def read_mic_engines():
    configuration = Code.configuration
    file = Code.path_resource("IntFiles", "mic_tourney.ini")

    dic_mic = Util.ini2dic(file)
    li = []
    for alias, dic in dic_mic.items():
        nom_base_engine = dic["ENGINE"]
        id_info = dic["IDINFO"]
        li_info = [_F(x.strip()) for x in id_info.split(",")]
        id_info = "\n".join(li_info)
        elo = int(dic["ELO"])
        li_uci = [v.split(":") for k, v in dic.items() if k.startswith("OPTION")]

        engine = configuration.engines.dic_engines().get(nom_base_engine)
        if engine:
            eng = EngineTourneys()
            eng.read_engine(engine)
            eng.name = Util.primeras_mayusculas(alias)
            eng.id_info = id_info
            eng.key = alias
            eng.elo = elo
            eng.liUCI = li_uci
            if alias.isupper():
                eng.name = Util.primera_mayuscula(alias)
                eng.key = eng.name
                eng.book = Code.path_resource("Openings", "Players", f"{alias.lower()}.bin")
                eng.type = ENG_MICGM
            else:
                eng.book = None
                eng.type = ENG_MICPER
            li.append(eng)
    return li


def only_gm_engines():
    li = [mtl for mtl in read_mic_engines() if mtl.book]
    li.sort(key=lambda uno: uno.name)
    return li


def all_engines():
    li = read_mic_engines()
    li.sort(key=lambda uno: uno.elo)
    return li


def separated_engines():
    li = read_mic_engines()
    li_gm = []
    li_per = []
    for eng in li:
        if eng.book:
            li_gm.append(eng)
        else:
            li_per.append(eng)
    return li_gm, li_per
