import math
from typing import Any

import FasterCode

import Code
from Code.Analysis.AnalysisShow import AnalysisIndexesShow
from Code.Base import Game
from Code.Base.Constantes import (
    GOOD_MOVE,
    INTERESTING_MOVE,
    VERY_GOOD_MOVE,
)

# Constante global: valores de material por pieza
PIECE_MATERIAL_VALUES = {"k": 3.0, "q": 9.9, "r": 5.5, "b": 3.5, "n": 3.1, "p": 1.0}


def _compute_material_balance(cp) -> tuple[float, float, float, int, int]:
    """Calcula material total, blanco, negro, y número de pieces."""
    total_material = white_material = black_material = 0.0
    white_pieces = black_pieces = 0

    for piece in cp.squares.values():
        if not piece:
            continue
        value = PIECE_MATERIAL_VALUES[piece.lower()]
        total_material += value
        if piece.isupper():
            white_pieces += 1
            white_material += value
        else:
            black_pieces += 1
            black_material += value

    return total_material, white_material, black_material, white_pieces, black_pieces


def _compute_gmo(mrm) -> float:
    """Calcula el factor GMO basado en la dispersión de evaluaciones."""
    if not mrm.li_rm:
        return 0.0

    base_eval = mrm.li_rm[0].centipawns_abs()
    gmo34 = gmo68 = gmo100 = 0

    for rm in mrm.li_rm:
        diff = abs(rm.centipawns_abs() - base_eval)
        if diff < 34:
            gmo34 += 1
        elif diff < 68:
            gmo68 += 1
        elif diff < 101:
            gmo100 += 1

    return float(gmo34) + (gmo68 ** 0.8) + (gmo100 ** 0.5)


def _compute_context_variables(cp, mrm, is_white: bool) -> dict[str, Any]:
    """Construye el diccionario de variables para la fórmula."""
    (
        total_material,
        white_material,
        black_material,
        white_pieces,
        black_pieces,
    ) = _compute_material_balance(cp)

    gmo = _compute_gmo(mrm)
    mov = FasterCode.set_fen(cp.fen())
    base_eval = mrm.li_rm[0].centipawns_abs() if mrm.li_rm else 0
    plm = (cp.num_moves - 1) * 2 + (0 if is_white else 1)
    xshow = 0.01 * (1 if is_white else -1)

    return {
        "xpiec": white_pieces if is_white else black_pieces,
        "xpie": white_pieces + black_pieces,
        "xmov": mov,
        "xeval": base_eval if is_white else -base_eval,
        "xstm": 1 if is_white else -1,
        "xplm": plm,
        "xshow": xshow,
        "xgmo": gmo,
        "xmat": total_material,
        "xpow": white_material if is_white else black_material,
    }


def calc_formula(cual: str, cp, mrm) -> float:
    """Evalúa una fórmula desde un archivo usando el contexto del tablero y análisis."""
    if not mrm.li_rm:
        return 0.0

    try:
        formula_path = Code.path_resource("IntFiles", "Formulas", f"{cual}.formula")
        with open(formula_path, "rt") as f:
            formula = f.read().strip()
    except (OSError, FileNotFoundError):
        return 0.0

    is_white = cp.is_white
    context = _compute_context_variables(cp, mrm, is_white)

    # Reemplazo de variables en la fórmula
    for key, value in context.items():
        if key in formula:
            formula = formula.replace(key, f"{float(value):.10f}")

    # Soporte para xcompl (recursivo)
    if "xcompl" in formula:
        compl_value = calc_formula("complexity", cp, mrm)
        formula = formula.replace("xcompl", f"{compl_value:.10f}")

    try:
        # Entorno restringido para eval por seguridad
        allowed_names = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "pow": pow,
            "sqrt": math.sqrt,
            "log": math.log,
            "exp": math.exp,
        }

        # Evaluar con entorno restringido
        result = eval(formula, {"__builtins__": {}}, allowed_names)
        return float(result)
    except Exception:
        return 0.0


def lb_levels(x):
    if x < 0:
        return _("Extremely low")
    elif x < 5.0:
        return _("Very low")
    elif x < 15.0:
        return _("Low")
    elif x < 35.0:
        return _("Moderate")
    elif x < 55.0:
        return _("High")
    elif x < 85.0:
        return _("Very high")
    else:
        return _("Extreme")


def txt_levels(x):
    return f"{lb_levels(x)} ({x:.02f}%)"


def txt_formula(titulo, funcion, cp, mrm):
    x = funcion(cp, mrm)
    return f"{titulo}: {txt_levels(x)}"


def tp_formula(titulo, funcion, cp, mrm):
    x = funcion(cp, mrm)
    return titulo, x, lb_levels(x)


def calc_complexity(cp, mrm):
    return calc_formula("complexity", cp, mrm)


def get_complexity(cp, mrm):
    return txt_formula(_("Complexity"), calc_complexity, cp, mrm)


def tp_complexity(cp, mrm):
    return tp_formula(_("Complexity"), calc_complexity, cp, mrm)


def calc_winprobability(cp, mrm):
    return calc_formula("winprobability", cp, mrm)  # , limit=100.0)


def get_winprobability(cp, mrm):
    return txt_formula(_("Win probability"), calc_winprobability, cp, mrm)


def tp_winprobability(cp, mrm):
    return tp_formula(_("Win probability"), calc_winprobability, cp, mrm)


def calc_narrowness(cp, mrm):
    return calc_formula("narrowness", cp, mrm)


def get_narrowness(cp, mrm):
    return txt_formula(_("Narrowness"), calc_narrowness, cp, mrm)


def tp_narrowness(cp, mrm):
    return tp_formula(_("Narrowness"), calc_narrowness, cp, mrm)


def calc_efficientmobility(cp, mrm):
    return calc_formula("efficientmobility", cp, mrm)


def get_efficientmobility(cp, mrm):
    return txt_formula(_("Efficient mobility"), calc_efficientmobility, cp, mrm)


def tp_efficientmobility(cp, mrm):
    return tp_formula(_("Efficient mobility"), calc_efficientmobility, cp, mrm)


def calc_piecesactivity(cp, mrm):
    return calc_formula("piecesactivity", cp, mrm)


def get_piecesactivity(cp, mrm):
    return txt_formula(_("Pieces activity"), calc_piecesactivity, cp, mrm)


def tp_piecesactivity(cp, mrm):
    return tp_formula(_("Pieces activity"), calc_piecesactivity, cp, mrm)


def calc_exchangetendency(cp, mrm):
    return calc_formula("simplification", cp, mrm)


def get_exchangetendency(cp, mrm):
    return txt_formula(_("Exchange tendency"), calc_exchangetendency, cp, mrm)


def tp_exchangetendency(cp, mrm):
    return tp_formula(_("Exchange tendency"), calc_exchangetendency, cp, mrm)


def calc_positionalpressure(cp, mrm):
    return calc_formula("positionalpressure", cp, mrm)


def get_positionalpressure(cp, mrm):
    return txt_formula(_("Positional pressure"), calc_positionalpressure, cp, mrm)


def tp_positionalpressure(cp, mrm):
    return tp_formula(_("Positional pressure"), calc_positionalpressure, cp, mrm)


def calc_materialasymmetry(cp, mrm):
    return calc_formula("materialasymmetry", cp, mrm)


def get_materialasymmetry(cp, mrm):
    return txt_formula(_("Material asymmetry"), calc_materialasymmetry, cp, mrm)


def tp_materialasymmetry(cp, mrm):
    return tp_formula(_("Material asymmetry"), calc_materialasymmetry, cp, mrm)


def calc_gamestage(cp, mrm):
    return calc_formula("gamestage", cp, mrm)


def get_gamestage(cp, mrm):
    xgst = calc_gamestage(cp, mrm)
    if xgst >= 50:
        gst = 1
    elif 50 > xgst >= 40:
        gst = 2
    elif 40 > xgst >= 10:
        gst = 3
    elif 10 > xgst >= 5:
        gst = 4
    else:
        gst = 5
    dic = {
        1: _("Opening"),
        2: _("Transition to middlegame"),
        3: _("Middlegame"),
        4: _("Transition to endgame"),
        5: _("Endgame"),
    }
    return dic[gst]


def tp_gamestage(cp, mrm):
    return _("Game stage"), calc_gamestage(cp, mrm), get_gamestage(cp, mrm)


def gen_indexes(game, elos, alm):
    average = {True: 0.0, False: 0.0}
    domination = {True: 0.0, False: 0.0}
    complexity = {True: 0.0, False: 0.0}
    narrowness = {True: 0.0, False: 0.0}
    efficientmobility = {True: 0.0, False: 0.0}
    piecesactivity = {True: 0.0, False: 0.0}
    exchangetendency = {True: 0.0, False: 0.0}

    n = {True: 0, False: 0}
    nmoves_analyzed = {True: 0, False: 0}
    for move in game.li_moves:
        is_white = move.is_white()
        if move.analysis:
            mrm, pos = move.analysis
            rm = mrm.li_rm[pos]
            if (
                    not hasattr(mrm, "dic_depth") or len(mrm.dic_depth) == 0
            ):  # Generación de gráficos sin un análisis previo con su depth
                if INTERESTING_MOVE in move.li_nags:
                    nag_move, nag_color = INTERESTING_MOVE, INTERESTING_MOVE
                elif VERY_GOOD_MOVE in move.li_nags:
                    nag_move, nag_color = VERY_GOOD_MOVE, VERY_GOOD_MOVE
                elif GOOD_MOVE in move.li_nags:
                    nag_move, nag_color = GOOD_MOVE, GOOD_MOVE
                else:
                    nag_move, nag_color = mrm.set_nag_color(rm)

            else:
                nag_move, nag_color = mrm.set_nag_color(rm)
            move.nag_color = nag_move, nag_color

            nmoves_analyzed[is_white] += 1
            pts = mrm.li_rm[pos].centipawns_abs()
            if pts > 100:
                domination[is_white] += 1
            elif pts < -100:
                domination[not is_white] += 1
            average[is_white] += mrm.li_rm[0].centipawns_abs() - pts

            if not hasattr(move, "complexity"):
                cp = move.position_before
                move.complexity = calc_complexity(cp, mrm)
                move.winprobability = calc_winprobability(cp, mrm)
                move.narrowness = calc_narrowness(cp, mrm)
                move.efficientmobility = calc_efficientmobility(cp, mrm)
                move.piecesactivity = calc_piecesactivity(cp, mrm)
                move.exchangetendency = calc_exchangetendency(cp, mrm)
            complexity[is_white] += move.complexity
            narrowness[is_white] += move.narrowness
            efficientmobility[is_white] += move.efficientmobility
            piecesactivity[is_white] += move.piecesactivity
            n[is_white] += 1
            exchangetendency[is_white] += move.exchangetendency

    t = n[True] + n[False]
    for color in (True, False):
        b1 = n[color]
        if b1:
            average[color] = average[color] * 1.0 / b1
            complexity[color] = complexity[color] * 1.0 / b1
            narrowness[color] = narrowness[color] * 1.0 / b1
            efficientmobility[color] = efficientmobility[color] * 1.0 / b1
            piecesactivity[color] = piecesactivity[color] * 1.0 / b1
            exchangetendency[color] = exchangetendency[color] * 1.0 / b1
        if t:
            domination[color] = domination[color] * 100.0 / t

    complexity_t = (complexity[True] + complexity[False]) / 2.0
    narrowness_t = (narrowness[True] + narrowness[False]) / 2.0
    efficientmobility_t = (efficientmobility[True] + efficientmobility[False]) / 2.0
    piecesactivity_t = (piecesactivity[True] + piecesactivity[False]) / 2.0
    exchangetendency_t = (exchangetendency[True] + exchangetendency[False]) / 2.0

    average[True] /= 100.0
    average[False] /= 100.0
    average_t = (average[True] + average[False]) / 2.0

    cpt = _("pws")
    xac = txt_levels
    prc = "%"

    li_indices = [
        (
            _("Average lost scores"),
            f"{average[True]:.02f} {cpt}",
            f"{average[False]:0.02f} {cpt}",
            f"{average_t:0.02f} {cpt}",
        ),
        (
            _("Domination"),
            f"{domination[True]:.02f}%",
            f"{domination[False]:.02f}%",
            "",
        ),
        (
            _("Complexity"),
            xac(complexity[True]),
            xac(complexity[False]),
            xac(complexity_t),
        ),
        (
            _("Efficient mobility"),
            xac(efficientmobility[True]),
            xac(efficientmobility[False]),
            xac(efficientmobility_t),
        ),
        (
            _("Narrowness"),
            xac(narrowness[True]),
            xac(narrowness[False]),
            xac(narrowness_t),
        ),
        (
            _("Pieces activity"),
            xac(piecesactivity[True]),
            xac(piecesactivity[False]),
            xac(piecesactivity_t),
        ),
        (
            _("Exchange tendency"),
            xac(exchangetendency[True]),
            xac(exchangetendency[False]),
            xac(exchangetendency_t),
        ),
        (
            _("Accuracy"),
            f"{alm.porcW:.02f} {prc}",
            f"{alm.porcB:.02f} {prc}",
            f"{alm.porcT:.02f} {prc}",
        ),
    ]

    txt_indices_raw = f"{_('Result of analysis')}:"
    w = _("W ||White")
    b = _("B ||Black")
    t = _("Total")
    for label, cw, cb, ct in li_indices:
        txt_indices_raw += f"\n {label}: {w}={cw} {b}={cb}"
        if ct:
            txt_indices_raw += f" {t}={ct}"

    sh = AnalysisIndexesShow.ShowHtml(nmoves_analyzed)
    txt_html_elo = sh.elo_html(elos)
    txt_indices = sh.indices_html(li_indices)

    return (
        txt_indices,
        txt_html_elo,
        txt_indices_raw,
        elos[True][Game.ALLGAME],
        elos[False][Game.ALLGAME],
        elos[None][Game.ALLGAME],
    )
