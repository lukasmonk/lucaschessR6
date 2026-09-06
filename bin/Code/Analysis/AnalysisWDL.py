import math

AS = (-72.32565836, 185.93832038, -144.58862193, 416.44950446)
BS = (83.86794042, -136.06112997, 69.98820887, 47.62901433)
_PIECE_VALUES = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9}


def _win_rate_params(fen: str) -> tuple[float, float]:
    material = 0
    for ch in fen.strip().split(' ')[0]:
        low = ch.lower()
        if low in _PIECE_VALUES:
            material += _PIECE_VALUES[low]
    m = max(17, min(78, material)) / 58.0
    a = (((AS[0] * m + AS[1]) * m + AS[2]) * m) + AS[3]
    b = (((BS[0] * m + BS[1]) * m + BS[2]) * m) + BS[3]
    return a, b


def cp_to_wdl(cp: int, mate: int, fen: str) -> tuple[int, int, int]:
    """
    Convierte evaluación de motor a probabilidades WDL (0-1000).
    fen: posición exacta que analizó el motor (la de 'position fen ...').
    """
    if mate:
        return (1000, 0, 0) if mate > 0 else (0, 0, 1000)

    if cp >= 2000:
        return 1000, 0, 0
    if cp <= -2000:
        return 0, 0, 1000

    a, b = _win_rate_params(fen)
    v = cp * a / 100.0

    def _wr(x: float) -> int:
        return int(0.5 + 1000 / (1 + math.exp((a - x) / b)))

    win = _wr(v)
    loss = _wr(-v)
    draw = 1000 - win - loss
    return win, draw, loss


# if __name__ == "__main__":
#     fen_tras_a2a3 = "rnbqk1nr/pp3ppp/2pbp3/3p4/3PP3/P1N2N2/1PP2PPP/R1BQKB1R b KQkq - 0 5"
#
#     # (depth, cp, wdl real reportado por Stockfish: W D L)
#     datos = [
#         (1, -88, (1, 614, 385)), (2, -108, (0, 421, 579)), (3, -111, (0, 391, 609)),
#         (4, -110, (0, 401, 599)), (5, -110, (0, 397, 603)), (6, -115, (0, 355, 645)),
#         (7, -102, (0, 480, 520)), (8, -108, (0, 418, 582)), (9, -100, (0, 505, 495)),
#         (10, -111, (0, 391, 609)), (11, -113, (0, 374, 626)), (12, -115, (0, 351, 649)),
#         (13, -108, (0, 421, 579)), (14, -106, (0, 438, 562)), (15, -109, (0, 407, 593)),
#         (16, -105, (0, 449, 551)), (17, -106, (0, 438, 562)), (18, -116, (0, 348, 652)),
#         (19, -122, (0, 296, 704)), (20, -125, (0, 270, 730)),
#     ]
#
#     print(f"{'depth':>5} {'cp':>5} | {'SF (W D L)':^16} | {'función (W D L)':^18} | max_diff")
#     for depth, cp, sf in datos:
#         w, d, l = cp_to_wdl(cp, 0, fen_tras_a2a3)
#         diff = max(abs(w - sf[0]), abs(d - sf[1]), abs(l - sf[2]))
#         print(f"{depth:>5} {cp:>5} | {str(sf):^16} | {str((w, d, l)):^18} | {diff}")
