import collections
import string

import FasterCode

import Code
import contextlib
import itertools
from Code.Base.Constantes import (
    BLACK,
    FEN_INITIAL,
    INFINITE,
    PZ_VALUES,
    WHITE,
    OPENING,
    MIDDLEGAME,
    ENDGAME,
    PHASE_KNIGHT,
    PHASE_BISHOP,
    PHASE_ROOK,
    PHASE_QUEEN,
)
from Code.Translations import TrListas


class Position:
    __slots__ = (
        "li_extras",
        "squares",
        "castles",
        "en_passant",
        "is_white",
        "num_moves",
        "mov_pawn_capt",
    )

    def __init__(self):
        self.li_extras = []
        self.squares = {}
        self.castles = ""
        self.en_passant = ""
        self.is_white = True
        self.num_moves = 0
        self.mov_pawn_capt = 0

    def set_pos_initial(self):
        return self.read_fen(FEN_INITIAL)

    def is_initial(self):
        return self.fen() == FEN_INITIAL

    def logo(self):
        #  self.leeFen( "8/4q1k1/1R2bpn1/1N2n1b1/1B2r1r1/1Q6/1PKNBR2/8 w - - 0 1" )
        self.read_fen("8/4Q1K1/1r2BPN1/1n2N1B1/1b2R1R1/1q6/1pknbr2/8 w - - 0 1")
        return self

    def copia(self):
        p = Position()
        p.squares = self.squares.copy()
        p.castles = self.castles
        p.en_passant = self.en_passant
        p.is_white = self.is_white
        p.num_moves = self.num_moves
        p.mov_pawn_capt = self.mov_pawn_capt
        return p

    def __eq__(self, other: "Position"):
        return self.fen() == other.fen() if other else False

    def legal(self):
        if self.castles != "-":
            dic = {
                "K": ("K", "R", "e1", "h1"),
                "k": ("k", "r", "e8", "h8"),
                "Q": ("K", "R", "e1", "a1"),
                "q": ("k", "r", "e8", "a8"),
            }
            enr = ""
            for tipo in self.castles:
                with contextlib.suppress(KeyError):
                    king, rook, pos_king, pos_rook = dic[tipo]
                    if self.squares.get(pos_king) == king and self.squares.get(pos_rook) == rook:
                        enr += tipo
            self.castles = enr or "-"

        # https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation#:~:text=En%20passant%20target%20square%20in,make%20an%20en%20passant%20capture.
        # En passant target square in algebraic notation. If there's no en passant target square, this is -.
        # If a pawn has just made a two-square move, this is the position "behind" the pawn. This is recorded
        # regardless of whether there is a pawn in position to make an en passant capture
        ok = len(self.en_passant) == 2
        if ok:
            lt, nm = self.en_passant[0], self.en_passant[1]
            ok = False
            if nm in "36":
                pawn = "P" if nm == "6" else "p"
                bq_nm = "4" if nm == "3" else "5"
                if lt > "a":
                    pz = self.squares.get(chr(ord(lt) - 1) + bq_nm)
                    ok = pz == pawn
                if not ok and lt < "h":
                    pz = self.squares.get(chr(ord(lt) + 1) + bq_nm)
                    ok = pz == pawn
        if not ok:
            self.en_passant = "-"

    def is_valid_fen(self, fen):
        fen = fen.strip()
        if fen.count("/") != 7:
            return False
        try:
            self.read_fen(fen)
            return True
        except Exception:
            return False

    def read_fen(self, fen):
        fen = fen.strip()
        if fen.count("/") != 7:
            return self.set_pos_initial()

        li = fen.split(" ")
        nli = len(li)
        if nli < 6:
            lid = ["w", "-", "-", "0", "1"]
            li.extend(lid[nli - 1 :])
        position, color, self.castles, self.en_passant, mp, move = li[:6]

        self.is_white = color == "w"
        self.num_moves = int(move)
        self.num_moves = max(self.num_moves, 1)
        self.mov_pawn_capt = int(mp)

        d = {}
        for x, linea in enumerate(position.split("/")):
            c_fil = chr(48 + 8 - x)
            nc = 0
            for c in linea:
                if c.isdigit():
                    nc += int(c)
                elif c in "KQRBNPkqrbnp":
                    c_col = chr(nc + 97)
                    d[c_col + c_fil] = c
                    nc += 1
                else:
                    return self.set_pos_initial()
        self.squares = d
        self.legal()
        return self

    def set_lce(self):
        return FasterCode.set_fen(self.fen())

    def get_exmoves(self):
        self.set_lce()
        return FasterCode.get_exmoves()

    def fen_base(self):
        n_sin = 0
        position = ""
        for i in range(8, 0, -1):
            c_fil = chr(i + 48)
            row = ""
            for j in range(8):
                c_col = chr(j + 97)
                key = c_col + c_fil
                v = self.squares.get(key)
                if v is None:
                    n_sin += 1
                else:
                    if n_sin:
                        row += "%d" % n_sin
                        n_sin = 0
                    row += v
            if n_sin:
                row += "%d" % n_sin
                n_sin = 0

            position += row
            if i > 1:
                position += "/"
        color = "w" if self.is_white else "b"
        return f"{position} {color}"

    def fen_dgt(self):
        n_sin = 0
        resp = ""
        for i in range(8, 0, -1):
            c_fil = chr(i + 48)
            for j in range(8):
                c_col = chr(j + 97)
                key = c_col + c_fil
                v = self.squares.get(key)
                if v is None:
                    n_sin += 1
                else:
                    if n_sin:
                        resp += "%d" % n_sin
                        n_sin = 0
                    resp += v
        return resp

    def fen(self):
        position = self.fen_base()
        self.legal()
        return "%s %s %s %d %d" % (
            position,
            self.castles,
            self.en_passant,
            self.mov_pawn_capt,
            self.num_moves,
        )

    def fenm2(self):
        position = self.fen_base()
        self.legal()
        return f"{position} {self.castles} {self.en_passant}"

    # def siExistePieza(self, pieza, a1h8=None):
    #     if a1h8:
    #         return self.squares.get(a1h8) == pieza
    #     else:
    #         n = 0
    #         for k, v in self.squares.items():
    #             if v == pieza:
    #                 n += 1
    #         return n

    def get_pz(self, a1h8):
        return self.squares.get(a1h8)

    def get_pos_king(self, is_white):
        king = "K" if is_white else "k"
        return next((pos for pos, pz in self.squares.items() if pz == king), None)

    def pzs_key(self):
        td = "KQRBNPkqrbnp"
        key = ""
        for pz in td:
            for k, c in self.squares.items():
                if c == pz:
                    key += c
        return key

    def capturas(self):
        dic = {}
        for pieza, num in (("P", 8), ("R", 2), ("N", 2), ("B", 2), ("Q", 1), ("K", 1)):
            dic[pieza] = num
            dic[pieza.lower()] = num

        for pieza in self.squares.values():
            if pieza and dic[pieza] > 0:
                dic[pieza] -= 1
        return {pieza.upper() if pieza.islower() else pieza.lower(): value for pieza, value in dic.items()}

    def capturas_diferencia(self):
        """
        Devuelve las pieces capturadas, liNuestro, liOponente. ( pieza, number )
        """
        pieces = "PRNBQK"
        dic = {pz: 0 for pz in (pieces + pieces.lower())}
        for pieza in self.squares.values():
            if pieza:
                dic[pieza] += 1
        dif = {}
        for pieza in "PRNBQK":
            d = dic[pieza] - dic[pieza.lower()]
            if d < 0:
                dif[pieza.lower()] = -d
            elif d > 0:
                dif[pieza] = d
        return dif

    def play_pv(self, pv):
        return self.play(pv[:2], pv[2:4], pv[4:])

    def play(self, from_a1h8, to_a1h8, promotion=""):
        self.set_lce()
        if promotion is None:
            promotion = ""
        mv = FasterCode.move_expv(from_a1h8, to_a1h8, promotion)
        if not mv:
            return False, "Error"

        self.li_extras = []

        enr_k = mv.iscastle_k()
        enr_q = mv.iscastle_q()
        en_pa = mv.is_enpassant()

        if promotion:
            promotion = promotion.upper() if self.is_white else promotion.lower()
            self.li_extras.append(("c", to_a1h8, promotion))

        elif enr_k:
            if self.is_white:
                self.li_extras.append(("m", "h1", "f1"))
            else:
                self.li_extras.append(("m", "h8", "f8"))

        elif enr_q:
            if self.is_white:
                self.li_extras.append(("m", "a1", "d1"))
            else:
                self.li_extras.append(("m", "a8", "d8"))

        elif en_pa:
            capt = self.en_passant.replace("6", "5").replace("3", "4")
            self.li_extras.append(("b", capt))

        self.read_fen(FasterCode.get_fen())  # despues de li_extras, por si enpassant

        return True, self.li_extras

    def pr_board(self):
        resp = f"   {'+---' * 8}+\n"
        for row in "87654321":
            resp += f" {row} |"
            for column in "abcdefgh":
                pieza = self.squares.get(column + row)
                resp += "   |" if pieza is None else f" {pieza} |"
            resp += f" {row}\n"
            resp += f"   {'+---' * 8}+\n"
        resp += "    "
        for column in "abcdefgh":
            resp += f" {column}  "

        return resp

    def pgn(self, from_sq, to_sq, promotion=""):
        self.set_lce()
        return FasterCode.get_pgn(from_sq, to_sq, '' if promotion is None else promotion)

    def get_fenm2(self):
        self.set_lce()
        fen = FasterCode.get_fen()
        return FasterCode.fen_fenm2(fen)

    def html(self, mv: str):
        pgn = self.pgn(mv[:2], mv[2:4], mv[4:])
        li = []
        tp = "w" if self.is_white else "b"
        for c in pgn:
            if c in "NBRQK":
                li.append(
                    f'<img src="{Code.configuration.paths.folder_pieces_png()}/{tp}{c.lower()}.png" '
                    'width="20" height="20" style="vertical-align:bottom">'
                )
            else:
                li.append(c)
        return "".join(li)

    def pv2dgt(self, from_sq, to_sq, promotion=""):
        p_ori = self.squares.get(from_sq)

        # Enroque
        if p_ori in "Kk":
            n = ord(from_sq[0]) - ord(to_sq[0])
            if abs(n) == 2:
                orden = "ke8kc8ra8rd8" if n == 2 else "ke8kg8rh8rf8"
                return orden if p_ori == "k" else orden.replace("k", "K").replace("8", "1")
        # Promotion
        if promotion:
            promotion = promotion.upper() if self.is_white else promotion.lower()
            return p_ori + from_sq + promotion + to_sq

        # Al paso
        if p_ori in "Pp" and to_sq == self.en_passant:
            if self.is_white:
                otro = "p"
                dif = -1
            else:
                otro = "P"
                dif = +1
            square = "%s%d" % (to_sq[0], int(to_sq[1]) + dif)
            return f"{p_ori}{from_sq}{p_ori}{to_sq}{otro}{square}.{square}"

        return p_ori + from_sq + p_ori + to_sq

    def pgn_translated(self, from_sq, to_sq, promotion=""):
        d_conv = TrListas.dic_conv()
        li = []
        cpgn = self.pgn(from_sq, to_sq, promotion)
        if not cpgn:
            return ""
        for c in cpgn:
            if c in d_conv:
                c = d_conv[c]
            li.append(c)
        return "".join(li)

    def is_check(self):
        self.set_lce()
        return FasterCode.ischeck()

    def is_finished(self):
        return self.set_lce() == 0

    def is_mate(self):
        n = self.set_lce()
        return n == 0 if FasterCode.ischeck() else False

    def valor_material(self):
        return sum(PZ_VALUES[v.upper()] for v in self.squares.values() if v)

    def valor_material_side(self, is_white):
        if is_white:
            d = PZ_VALUES
        else:
            d = {key.lower(): value for key, value in PZ_VALUES.items()}
        return sum(d[v] for v in self.squares.values() if v and v in d)

    def not_enough_material(self):
        # FIDE rules for "dead positions" (insufficient material)
        # Rey y Rey
        # Rey + Caballo y Rey
        # Rey + Alfil y Rey
        # Rey + Alfil y Rey + Alfil (mismo color de casillas)

        li_white = []
        li_black = []
        for v, piece in self.squares.items():
            if not piece:
                continue
            p_upper = piece.upper()
            if p_upper in "PQR":
                return False
            if p_upper == "K":
                continue
            if piece.isupper():
                li_white.append((v, p_upper))
            else:
                li_black.append((v, p_upper))

        nw = len(li_white)
        nb = len(li_black)

        if nw == 0 and nb == 0:
            return True

        if nw + nb == 1:
            return True  # K+N vs K or K+B vs K

        if nw == 1 and nb == 1:
            v_w, p_w = li_white[0]
            v_b, p_b = li_black[0]
            if p_w == "B" and p_b == "B":
                # K+B vs K+B same color?
                # (ord(col)-97 + int(row)-1) % 2
                color_w = (ord(v_w[0]) - 97 + int(v_w[1]) - 1) % 2
                color_b = (ord(v_b[0]) - 97 + int(v_b[1]) - 1) % 2
                return color_w == color_b

        return False

    def not_enough_material_side(self, is_white):
        pieces = ""
        nb = "nb"
        prq = "prq"
        if is_white:
            nb = nb.upper()
            prq = prq.upper()
        for v in self.squares.values():
            if v:
                if v in prq:
                    return False
                if v in nb:
                    if pieces:
                        return False
                    else:
                        pieces = v
        return False

    def num_pieces(self, pieza):
        num = 0
        for i, j in itertools.product(range(8), range(8)):
            c_col = chr(i + 97)
            c_fil = chr(j + 49)
            if self.squares.get(c_col + c_fil) == pieza:
                num += 1
        return num

    def __len__(self):
        return sum(bool(self.squares[pos]) for pos in self.squares)

    def num_piezas_wb(self):
        n_white = n_black = 0
        for i, j in itertools.product(range(8), range(8)):
            c_col = chr(i + 97)
            c_fil = chr(j + 49)
            pz = self.squares.get(c_col + c_fil)
            if pz and pz not in "pkPK":
                if pz.islower():
                    n_black += 1
                else:
                    n_white += 1
        return n_white, n_black

    def num_allpiezas_wb(self):
        n_white = n_black = 0
        for col in string.ascii_lowercase[:8]:
            for row in '12345678':
                if piece := self.squares.get(f"{col}{row}"):
                    if piece.islower():
                        n_black += 1
                    else:
                        n_white += 1
        return n_white, n_black

    def dic_pieces(self):
        dic = collections.defaultdict(int)
        for i, j in itertools.product(range(8), range(8)):
            c_col = chr(i + 97)
            c_fil = chr(j + 49)
            pz = self.squares.get(c_col + c_fil)
            dic[pz] += 1
        return dic

    def label(self):
        d = {x: [] for x in "KQRBNPkqrbnp"}
        for pos, pz in self.squares.items():
            d[pz].append(pos)

        li = []
        for pz in "KQRBNPkqrbnp":
            li.extend(f"{pz}{pos}" for pos in d[pz])
        return " ".join(li)

    def proximity_final(self, side: bool) -> float:
        dic_weights = {"K": 110, "Q": 100, "N": 30, "B": 32, "R": 50, "P": 40}
        result = 0
        val_pieces = 0
        for a1h8, piece in self.squares.items():
            if side == BLACK and piece in "kqrbnp":
                if piece == "p":
                    result += int(a1h8[1]) * dic_weights[piece.upper()]
                else:
                    result += self.distance_king(a1h8, WHITE) * dic_weights[piece.upper()]
                val_pieces += dic_weights[piece.upper()]
            elif side == WHITE and piece in "KQRBNP":
                if piece == "P":
                    result += (9 - int(a1h8[1])) * dic_weights[piece]
                else:
                    result += self.distance_king(a1h8, BLACK) * dic_weights[piece]
                val_pieces += dic_weights[piece.upper()]
        return result / val_pieces

    def proximity_middle(self, side: bool) -> float:
        dic_weights = {"Q": 100, "N": 30, "B": 32, "R": 50, "P": 10}
        result = 0
        val_pieces = 0
        for a1h8, piece in self.squares.items():
            if side == BLACK and piece in "qrbnp":
                result += int(a1h8[1]) * dic_weights[piece.upper()]
                val_pieces += dic_weights[piece.upper()]
            elif side and piece in "QRBNP":
                result += (9 - int(a1h8[1])) * dic_weights[piece]
                val_pieces += dic_weights[piece]
        return result / val_pieces if val_pieces else INFINITE

    def distance_king(self, a1, side_king_rival):
        k = "K" if side_king_rival == WHITE else "k"
        return next(
            (
                ((i - (ord(a1[0]) - 97)) ** 2 + (j - (int(a1[1]) - 1)) ** 2) ** 0.5
                for i, j in itertools.product(range(8), range(8))
                if self.squares.get(chr(i + 97) + chr(j + 49)) == k
            ),
            0,
        )

    def pawn_can_promote(self, from_a1h8, to_a1h8):
        pieza = self.squares.get(from_a1h8)
        if (not pieza) or (pieza.upper() != "P"):  # or self.squares[to_a1h8] is not None:
            return False
        if pieza == "P":
            ori = 7
            dest = 8
        else:
            ori = 2
            dest = 1

        return int(from_a1h8[1]) == ori and int(to_a1h8[1]) == dest

    def aura(self):
        lista = []

        def add(lipos):
            for pos in lipos:
                lista.append(FasterCode.pos_a1(pos))

        def list_pos_bishop_rook(n_pos, fi, ci):
            """Collect reachable squares for sliding pieces in a given direction.
            This helper walks from a start square until the board edge or a blocking piece is found.

            The function is used to model rook, bishop, and queen movement rays for aura calculations.
            It records each traversed square and stops when another piece is encountered.

            Args:
                n_pos: Starting square index in the internal numeric representation.
                fi: Rank (row) increment per step along the ray.
                ci: File (column) increment per step along the ray.
            """
            fil, col = FasterCode.pos_rc(n_pos)
            li_m = []
            ft = fil + fi
            ct = col + ci
            while 0 <= ft <= 7 and 0 <= ct <= 7:
                t = FasterCode.rc_pos(ft, ct)
                li_m.append(t)

                if self.squares.get(FasterCode.pos_a1(t)):
                    break
                ft += fi
                ct += ci
            add(li_m)

        pzs = "KQRBNP" if self.is_white else "kqrbnp"

        for i in range(8):
            for j in range(8):
                a1 = chr(i + 97) + chr(j + 49)
                pz = self.squares.get(a1)
                if pz and pz in pzs:
                    pz = pz.upper()
                    npos = FasterCode.a1_pos(a1)
                    if pz == "K":
                        add(FasterCode.li_k(npos))
                    elif pz == "Q":
                        for f_i, c_i in (
                            (1, 1),
                            (1, -1),
                            (-1, 1),
                            (-1, -1),
                            (1, 0),
                            (-1, 0),
                            (0, 1),
                            (0, -1),
                        ):
                            list_pos_bishop_rook(npos, f_i, c_i)
                    elif pz == "R":
                        for f_i, c_i in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            list_pos_bishop_rook(npos, f_i, c_i)
                    elif pz == "B":
                        for f_i, c_i in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                            list_pos_bishop_rook(npos, f_i, c_i)
                    elif pz == "N":
                        add(FasterCode.li_n(npos))
                    elif pz == "P":
                        lim, lix = FasterCode.li_p(npos, self.is_white)
                        add(lix)
        return lista

    def cohesion(self):
        lipos = [k for k, v in self.squares.items() if v]
        d = 0
        for n, a in enumerate(lipos[:-1]):
            for b in lipos[n + 1 :]:
                d += distancia(a, b)
        return d

    def mirror(self):
        def cp(a1):
            if a1.islower():
                c, f = a1[0], a1[1]
                f = str(9 - int(f))
                return c + f
            return a1

        def mp(xpz):
            return xpz.upper() if xpz.islower() else xpz.lower()

        p = Position()
        p.squares = {}
        for square, pz in self.squares.items():
            p.squares[cp(square)] = mp(pz)
        p.castles = "".join([mp(pz) for pz in self.castles])
        p.en_passant = cp(self.en_passant)
        p.is_white = not self.is_white
        p.num_moves = self.num_moves
        p.mov_pawn_capt = self.mov_pawn_capt

        return p

    def phase(self):
        dic_pieces = self.dic_pieces()

        def calc_piece(pz_lower: str):
            return dic_pieces.get(pz_lower, 0) + dic_pieces.get(pz_lower.upper(), 0)

        phase_value = (
            calc_piece("n") * PHASE_KNIGHT
            + calc_piece("b") * PHASE_BISHOP
            + calc_piece("r") * PHASE_ROOK
            + calc_piece("q") * PHASE_QUEEN
        )

        # 24 - 20	Apertura	La mayoría de las pieces menores y mayores están en el tablero.
        # 19 - 10	Medio Juego	Se han producido intercambios (ej: un par de torres y algunas pieces menores fuera).
        # 9 - 1	    Final	    Quedan pocas pieces; el Rey empieza a ser una pieza activate.
        # 0	        Final Puro	Solo quedan peones y Reyes (o material insuficiente).

        if phase_value > 20:
            return OPENING
        elif phase_value > 10:
            return MIDDLEGAME
        else:
            return ENDGAME


def distancia(from_sq, to_sq):
    return ((ord(from_sq[0]) - ord(to_sq[0])) ** 2 + (ord(from_sq[1]) - ord(to_sq[1])) ** 2) ** 0.5


def legal_fenm2(fen):
    p = Position()
    p.read_fen(fen)
    return p.fenm2()
