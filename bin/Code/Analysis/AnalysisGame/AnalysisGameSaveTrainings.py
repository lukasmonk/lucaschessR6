import copy
import os

import Code
from Code import Util
from Code.Base import Game
from Code.Base.Constantes import INFINITE
from Code.BestMoveTraining import BMT


def terminar_bmt(bmt_lista, name):
    """
    Si se estan creando registros para el entrenamiento BMT (Best move Training), al final hay que grabarlos
    @param bmt_lista: lista a grabar
    @param name: name del entrenamiento
    """
    if bmt_lista and len(bmt_lista) > 0:
        bmt = BMT.BMT(Code.configuration.path.file_bmt())
        dbf = bmt.read_dbf(False)

        reg = dbf.baseRegistro()
        reg.ESTADO = "0"
        reg.NOMBRE = name
        reg.EXTRA = ""
        reg.TOTAL = len(bmt_lista)
        reg.HECHOS = 0
        reg.PUNTOS = 0
        reg.MAXPUNTOS = bmt_lista.max_puntos()
        reg.FINICIAL = Util.dtos(Util.today())
        reg.FFINAL = ""
        reg.SEGUNDOS = 0
        reg.BMT_LISTA = Util.var2zip(bmt_lista)
        reg.HISTORIAL = Util.var2zip([])
        reg.REPE = 0
        reg.ORDEN = 0

        dbf.insertarReg(reg, siReleer=False)

        bmt.cerrar()


def save_brilliancies_fns(file, fen, mrm, game: Game.Game, njg):
    """
    Graba cada fen encontrado en el file "file"
    """
    if not file:
        return

    cab = ""
    for k, v in game.dic_tags().items():
        ku = k.upper()
        if ku not in ("RESULT", "FEN"):
            cab += '[%s "%s"]' % (k, v)

    game_raw = Game.game_without_variations(game)
    p = Game.Game(fen=fen)
    rm = mrm.li_rm[0]
    p.read_pv(rm.pv)
    with open(file, "at", encoding="utf-8", errors="ignore") as f:
        f.write(f"{fen}||{p.pgn_base_raw()}|{cab} {game_raw.pgn_base_raw_copy(None, njg - 1)}")


def graba_tactic(tacticblunders, game, njg, mrm, pos_act) -> bool:
    if not tacticblunders:
        return False

    # Esta creado el folder
    before = "%s.fns" % _("Avoid the blunder")
    after = "%s.fns" % _("Take advantage of blunder")
    if not os.path.isdir(tacticblunders):
        dtactics = Util.opj(Code.configuration.paths.folder_personal_trainings(), "../Tactics")
        if not os.path.isdir(dtactics):
            Util.create_folder(dtactics)
        Util.create_folder(tacticblunders)
        with open(
            Util.opj(tacticblunders, "Config.ini"),
            "wt",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            f.write(
                """[COMMON]
ed_reference=20
REPEAT=0
SHOWTEXT=1
[TACTIC1]
MENU=%s
FILESW=%s:100
[TACTIC2]
MENU=%s
FILESW=%s:100
"""
                % (
                    _("Avoid the blunder"),
                    before,
                    _("Take advantage of blunder"),
                    after,
                )
            )

    cab = ""
    for k, v in game.dic_tags().items():
        ku = k.upper()
        if ku not in ("RESULT", "FEN"):
            cab += '[%s "%s"]' % (k, v)
    move = game.move(njg)

    fen = move.position_before.fen()
    p = Game.Game(fen=fen)
    rm = mrm.li_rm[0]
    p.read_pv(rm.pv)
    game_raw = Game.game_without_variations(game)
    with open(Util.opj(tacticblunders, before), "at", encoding="utf-8", errors="ignore") as f:
        f.write("%s||%s|%s%s\n" % (fen, p.pgn_base_raw(), cab, game_raw.pgn_base_raw_copy(None, njg - 1)))

    fen = move.position.fen()
    p = Game.Game(fen=fen)
    rm = mrm.li_rm[pos_act]
    li = rm.pv.split(" ")
    p.read_pv(" ".join(li[1:]))
    with open(Util.opj(tacticblunders, after), "at", encoding="utf-8", errors="ignore") as f:
        f.write("%s||%s|%s%s\n" % (fen, p.pgn_base_raw(), cab, game_raw.pgn_base_raw_copy(None, njg)))

    return True


def save_pgn(file, name, dic_cab, fen, move, rm, mj):
    """
    Graba un game en un pgn

    @param file: pgn donde grabar
    @param name: name del engine que hace el analysis
    @param dic_cab: etiquetas de head del PGN
    @param fen: fen de la position
    @param move: move analizada
    @param rm: respuesta engine
    @param mj: respuesta engine con la mejor move, usado en caso de blunders, para incluirla
    """
    if not file:
        return False

    if mj:  # blunder
        game_blunder = Game.Game()
        game_blunder.set_position(move.position_before)
        game_blunder.read_pv(rm.pv)
        jg0 = game_blunder.move(0)
        jg0.set_comment(rm.texto())
    else:
        game_blunder = None

    p = Game.Game()
    p.set_position(move.position_before)
    if mj:  # blunder
        rm = mj
    p.read_pv(rm.pv)
    if p.is_finished():
        result = p.resultado()
        mas = ""  # ya lo anade en la ultima move
    else:
        mas = " *"
        result = "*"

    jg0 = p.move(0)
    # t = "%0.2f" % (float(self.params_play.fixed_ms) / 1000.0,)
    # t = t.rstrip("0")
    # if t[-1] == ".":
    #     t = t[:-1]
    # eti_t = "%s %s" % (t, _("Second(s)"))

    jg0.set_comment(f"{name}: {rm.texto()}\n")
    if mj:
        jg0.add_variation(game_blunder)

    cab = ""
    for k, v in dic_cab.items():
        ku = k.upper()
        if ku not in ("RESULT", "FEN"):
            cab += '[%s "%s"]\n' % (k, v)
    # Nos protegemos de que se hayan escrito en el pgn original de otra forma
    cab += '[FEN "%s"]\n' % fen
    cab += '[Result "%s"]\n' % result

    with open(file, "at", encoding="utf-8", errors="ignore") as q:
        texto = cab + "\n" + p.pgn_base() + mas + "\n\n"
        q.write(texto)

    return True


def save_bmt(
    si_blunder,
    fen,
    mrm,
    pos_act,
    cl_game,
    txt_game,
    bmt_lista_blunders,
    bmt_lista_brilliancies,
):
    """
    Se graba una position en un entrenamiento BMT
    @param si_blunder: si es blunder o brilliancie
    @param fen: position
    @param mrm: multirespuesta del engine
    @param pos_act: position de la position elegida en mrm
    @param cl_game: key de la game
    @param txt_game: la game completa en texto
    """

    previa = INFINITE
    nprevia = -1
    tniv = 0
    game_bmt = Game.Game()
    cp = game_bmt.first_position
    cp.read_fen(fen)

    if len(mrm.li_rm) > 16:
        mrm_bmt = copy.deepcopy(mrm)
        if pos_act > 15:
            mrm_bmt.li_rm[15] = mrm_bmt.li_rm[pos_act]
            pos_act = 15
        mrm_bmt.li_rm = mrm_bmt.li_rm[:16]
    else:
        mrm_bmt = mrm

    for n, rm in enumerate(mrm_bmt.li_rm):
        pts = rm.centipawns_abs()
        if pts != previa:
            previa = pts
            nprevia += 1
        tniv += nprevia
        rm.nivelBMT = nprevia
        rm.siElegida = False
        rm.siPrimero = n == pos_act
        game_bmt.set_position(cp)
        game_bmt.read_pv(rm.pv)
        rm.txtPartida = game_bmt.save()

    bmt_uno = BMT.BMTUno(fen, mrm_bmt, tniv, cl_game)

    bmt_lista = bmt_lista_blunders if si_blunder else bmt_lista_brilliancies
    bmt_lista.nuevo(bmt_uno)
    bmt_lista.check_game(cl_game, txt_game)
