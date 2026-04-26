# cython: language_level=3
cimport cython
import sys
import os.path
import os
import shutil
import tempfile
from collections import deque
from libc.stdio cimport FILE
from libc.stdlib cimport malloc, free
from typing import Dict, Tuple, Iterator, List, Optional

"""
PGNreader: class to read pgn files
    example:
    with PGNreader(filename, 0) as pgnreader:
        for body, is_raw, pv, fens, ulabels_values, ulabels_labels, pos in pgnreader:
            print(pv)

def xpgn_pv(pgn): convert pgn to a pv (list of moves separated by spaces)
def pos_rc(pos): convert a pos (0..63 begining from a1=0 to h8=63) to row,column
def rc_pos(f, c): convert row,col to a pos
def pos_a1(pos): convert pos to coords (a1,a2,)
def a1_pos(a1): convert coords to pos
def move_num(a1h8q): translate a move to an integer
def num_move(num): translate number to a move

dict_k = dictionary of all pos of k, returns moves that are possible
dict_q = dictionary of all pos of q, returns moves that are possible
dict_b = dictionary of all pos of b, returns moves that are possible
dict_r = dictionary of all pos of r, returns moves that are possible
dict_n = dictionary of all pos of n, returns moves that are possible
dict_pw = dictionary of all pos of white p, returns moves that are possible
dict_pb = dictionary of all pos of black p, returns moves that are possible

def li_n_min(x, y, occupied_squares): minimum path of a knight from x to y

>>> xpv = list of moves in a compressed form to reduce space un database

def xpv_lipv(xpv): convert xpv to a list of moves
def xpv_pv(xpv): convert xpv to a list of moves separated by spaces
def xpv_pgn(xpv): convert xpv to a pgn
def lipv_pgn(fen, lipv):
def pv_xpv(pv): convert list of moves to xpv
def run_fen( fen, depth, ms, level ): plays internal engine of a level during ms time and a depth
def set_fen(fen): internally fen is setted
def get_fen(): returns current fen
def get_moves(): returns possible moves with current fen
def get_pgn(from_a1h8, to_a1h8, promotion): return in current position the san
def ischeck(): test if current position is check
class InfoMove(object): moves in an extended form
    def xfrom(self):
    def xto(self):
    def promotion(self):
    def move(self):
    def check(self):
    def mate(self):
    def capture(self):
    def piece(self):
    def iscastle_k(self):
    def iscastle_q(self):
    def is_enpassant(self):

def get_exmoves(): returns a list of InfoMove moves
def move_expv(xfrom, xto, promotion): returns the InfoMove from
def move_pv(xfrom, xto, promotion): returns
def make_move(a1h8): do that move in current position
def fen_fenm2(fen): remove last two fields from a fen position
def set_init_fen(): internally set the fen initial
def make_pv(pv): from initial fen do all moves of a space list of them
def get_captures_fen(fen): returns all captures in a fen
def get_captures(fen, siMB): returns all captures in a fen, from one side or the other
def fen_other(fen): convert a fen of one side to the other side
def fen_ended(fen): returns if there are no moves from this fen
def xparse_body(fen, body): returns all moves separated by \n and all other information in line appart, used to read a pgn from Match
def xparse_pgn(pgn): returns all moves separated by \n and all other information in line appart, used to read a pgn from Match
def get_pgn_descriptive(is_white, from_sq, to_sq, promotion)
"""


cdef extern from "irina.h":
    ctypedef struct MoveBin:
        pass

    int is_bmi2()
    void init_board()
    void fen_board(char *fen)
    char *board_fen(char *fen)
    char *board_fenM2(char *fen)
    int movegen()
    int pgn2pv(char *pgn, char *pv)
    int make_nummove(int num)
    char * play_fen(char *fen, int depth, int time)
    int num_moves()
    void get_move(int num, char *pv)
    int num_base_move()
    int search_move(char *xfrom, char *xto, char *promotion)
    void get_move_ex(int num, char *info)
    char * to_san(int num, char *sanMove)
    char incheck()
    void set_level(int lv)

    void pgn_start(int depth)
    void pgn_stop()
    int pgn_read(char * body, char * fen)
    char * pgn_pv()
    int pgn_raw()
    char * pgn_fen(int num)
    int pgn_numfens()

    int parse_body(char *fen, char *body, char *resp )
    int parse_pgn(char *pgn, char *resp)

    unsigned long long hash_from_fen(char *fen)
    void write_integer(int size, unsigned long long n)
    unsigned int move_from_string(char move_s[6])
    int move_to_string(char move_s[6], unsigned int move)
    void open_poly_w(char * name)
    void close_poly()
    void set_ext_fen_body(char * ext_fen, char * ext_body, char * pv )
    void pv_xpv_c(const char* pv, char* res)


def bmi2():
    return is_bmi2()


class PGNreader:
    """
    Robust PGN reader designed for Cython integration.
    Safe, deterministic, production-ready.
    """

    def __init__(self, path_file: str, depth: int) -> None:
        if not isinstance(depth, int) or depth < 0:
            raise ValueError("depth must be a non-negative integer")

        self.original_path = path_file
        self.path_file = path_file
        self.depth = depth

        self.size: int = 0
        self.tmp_file: Optional[str] = None
        self.utf_bom: bool = False
        self.inicio: int = 0
        self.final: int = 0
        self.ok: bool = False
        self._started: bool = False  # FIX 1: rastrear si pgn_start() completó

        self._prepare_file()

    def _prepare_file(self) -> None:
        try:
            with open(self.path_file, "rb") as f:
                start = f.read(3)
                self.utf_bom = start.startswith(b"\xef\xbb\xbf")
                f.seek(0)
                sample = f.read(2048)
                has_lf = b"\n" in sample

                f.seek(0, os.SEEK_END)
                self.size = f.tell()

            self.ok = True
        except OSError:
            self.ok = False
            return

        if self.ok and not has_lf:
            self._normalize_line_endings()

    def _normalize_line_endings(self) -> None:
        fd, temp_path = tempfile.mkstemp(prefix="pgnreader_", suffix=".pgn")
        os.close(fd)

        with open(self.path_file, "rb") as src, open(temp_path, "wb") as dst:
            while True:
                chunk = src.read(65536)
                if not chunk:
                    break
                chunk = chunk.replace(b"\r\n", b"\n")
                chunk = chunk.replace(b"\r", b"\n")
                dst.write(chunk)

        self.path_file = temp_path
        self.tmp_file = temp_path

    def __enter__(self) -> "PGNreader":
        self.f = open(self.path_file, "rb")
        if self.utf_bom:
            self.f.seek(3)
        self._started = False
        pgn_start(self.depth)
        self._started = True
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        if hasattr(self, "f"):
            try:
                self.f.close()
            except Exception:
                pass

        if self.tmp_file:
            try:
                os.remove(self.tmp_file)
            except OSError:
                pass

        if self._started:
            try:
                pgn_stop()
            except Exception:
                pass
            self._started = False

        return False  # no suprimir excepciones del bloque with

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Tuple:
        self.inicio = self.f.tell()
        readline = self.f.readline

        labels_values: Dict[bytes, bytes] = {}
        labels_keys: Dict[bytes, bytes] = {}

        body_lines: List[bytes] = []

        while True:
            line = readline()
            if not line:
                raise StopIteration

            stripped = line.strip()

            if stripped.startswith(b"[") and stripped.endswith(b"]"):
                self._parse_label(stripped, labels_values, labels_keys)
                continue

            if stripped:
                body_lines.append(line)
                break

        while True:
            pos = self.f.tell()
            line = readline()
            if not line:
                break

            stripped = line.strip()

            if stripped.startswith(b"[") and stripped.endswith(b"]"):
                self.f.seek(pos)
                break

            body_lines.append(line)

        body = b"".join(body_lines)

        fen = labels_values.get(b"FEN", b"")

        try:
            pgn_read(body, fen)
        except Exception as e:
            return self.__next__()

        pv = pgn_pv()
        is_raw = pgn_raw()
        fens = [pgn_fen(i) for i in range(pgn_numfens())]

        self.final = self.f.tell()

        return (
            body,
            is_raw,
            pv.decode("utf-8", errors="ignore"),
            fens,
            labels_values,
            labels_keys,
            self.final,
        )

    @staticmethod
    def _parse_label(
        line: bytes,
        values: Dict[bytes, bytes],
        keys: Dict[bytes, bytes],
    ) -> None:

        cdef Py_ssize_t n = len(line)
        if n < 4:
            return
        content = line[1:n-1].strip()

        try:
            key, rest = content.split(b" ", 1)
            value = rest.strip().strip(b'"')
        except ValueError:
            return

        key_upper = key.upper()
        values[key_upper] = value
        keys[key_upper] = key

    def bpgn(self) -> bytes:
        if not hasattr(self, "f") or self.f.closed:
            return b""
        self.f.seek(self.inicio)
        return self.f.read(self.final - self.inicio)




def xpgn_pv(pgn: str) -> str:
    cdef char pv[10];
    bpgn = bytes(pgn, "utf-8")
    resp = pgn2pv(bpgn, pv)
    if resp == 9999:
        return ""
    else:
        return pv.decode("utf-8")


def pos_rc(pos: int) -> tuple:
    return pos // 8, pos % 8


def rc_pos(f: int, c: int) -> int:
    return f * 8 + c


def pos_a1(pos: int) -> str:
    return chr(pos % 8 + 97) + chr(pos // 8 + 49)


def a1_pos(a1: str) -> int:
    cdef int f, c
    f = ord(a1[1]) - 49
    c = ord(a1[0]) - 97
    return f * 8 + c


def move_num(a1h8q: str) ->int:
    num = a1_pos(a1h8q[:2]) + a1_pos(a1h8q[2:4])*64
    if len(a1h8q)>4:
        num += ({b"q":1, b"r":2, b"b":3, b"n":4}.get(a1h8q[4], 0))*64*64
    return num


def num_move(num: int) -> str:
    a1 = pos_a1(num%64)
    num //= 64
    h8 = pos_a1(num%64)
    num //= 64
    if num:
        q = {1:"q", 2:"r", 3:"b", 4:"n"}.get(num)
    else:
        q = ""
    return a1 + h8 + q


def li_k(npos: int) -> tuple:
    cdef int fil, col, ft, ct
    liM = []
    fil, col = pos_rc(npos)
    for fi, ci in ( (+1, +1), (+1, -1), (-1, +1), (-1, -1), (+1, 0), (-1, 0), (0, +1), (0, -1) ):
        ft = fil + fi
        ct = col + ci
        if ft < 0 or ft > 7 or ct < 0 or ct > 7:
            continue
        liM.append(rc_pos(ft, ct))
    return tuple(liM)


def li_br(npos: int, fi: int, ci: int) -> tuple:
    cdef int fil, col, ft, ct

    fil, col = pos_rc(npos)
    liM = []
    ft = fil + fi
    ct = col + ci
    while True:
        if ft < 0 or ft > 7 or ct < 0 or ct > 7:
            break

        t = rc_pos(ft, ct)
        liM.append(t)
        ft += fi
        ct += ci
    return tuple(liM)


def li_n(npos: int) -> tuple:
    cdef int fil, col, ft, ct

    fil, col = pos_rc(npos)
    liM = []
    for fi, ci in ( (+1, +2), (+1, -2), (-1, +2), (-1, -2), (+2, +1), (+2, -1), (-2, +1), (-2, -1) ):
        ft = fil + fi
        ct = col + ci
        if ft < 0 or ft > 7 or ct < 0 or ct > 7:
            continue

        t = rc_pos(ft, ct)
        liM.append(t)
    return tuple(liM)


def li_p(npos: int, is_white: bool) -> tuple:
    cdef int fil, col, ft, ct, inc

    fil, col = pos_rc(npos)
    liM = []
    liX = []
    if is_white:
        filaIni = 1
        salto = +1
    else:
        filaIni = 6
        salto = -1
    sig = rc_pos(fil + salto, col)
    liM.append(sig)

    if fil == filaIni:
        sig2 = rc_pos(fil + salto * 2, col)
        liM.append(sig2)

    for inc in ( +1, -1 ):
        ft = fil + salto
        ct = col + inc
        if not (ft < 0 or ft > 7 or ct < 0 or ct > 7):
            t = rc_pos(ft, ct)
            liX.append(t)

    return tuple(liM), tuple(liX)


dict_k = {}
for i in range(64):
    dict_k[i] = li_k(i)

dict_q = {}
for i in range(64):
    li = []
    for f_i, c_i in ( (1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1) ):
        lin = li_br(i, f_i, c_i)
        if lin:
            li.append(lin)
    dict_q[i] = tuple(li)

dict_b = {}
for i in range(64):
    li = []
    for f_i, c_i in ( (1, 1), (1, -1), (-1, 1), (-1, -1) ):
        lin = li_br(i, f_i, c_i)
        if lin:
            li.append(lin)
    dict_b[i] = tuple(li)

dict_r = {}
for i in range(64):
    li = []
    for f_i, c_i in ( (1, 0), (-1, 0), (0, 1), (0, -1) ):
        lin = li_br(i, f_i, c_i)
        if lin:
            li.append(lin)
    dict_r[i] = tuple(li)

dict_n = {}
for i in range(64):
    dict_n[i] = li_n(i)

dict_pw = {}
for i in range(8, 56):
    dict_pw[i] = li_p(i, True)

dict_pb = {}
for i in range(8, 56):
    dict_pb[i] = li_p(i, False)

def knightmoves(a, b, no, nv, mx):
    if nv > mx:
        return []
    lia = li_n(a)
    if b in lia:
        return [[a, b]]
    lib = li_n(b)
    li = []
    for x in lia:
        if x not in no and x in lib:
            li.append([a, x, b])
    if li:
        return li

    li = []

    for x in lia:
        for y in lib:
            if x not in no and y not in no:
                nx = no[:]
                nx.append(x)
                nx.append(y)
                f = knightmoves(x, y, nx, nv + 1, mx)
                if f:
                    li.extend(f)
    if not li:
        return li
    xmin = 9999
    for x in li:
        nx = len(x)
        if nx < xmin:
            xmin = nx
    lidef = []
    for x in li:
        if len(x) == xmin:
            x.insert(0, a)
            x.append(b)
            lidef.append(x)
    return lidef


def li_n_min(x, y, occupied_squares):
    cdef int nv
    ot = occupied_squares[:]
    ot.extend([x, y])
    nv = 1
    li = knightmoves(x, y, ot, 0, nv)
    while len(li) == 0:
        nv += 1
        li = knightmoves(x, y, ot, 0, nv)
    return li


def xpv_lipv(xpv: str):
    li = []
    is_white = True
    for x in xpv.encode("utf-8"):
        if x >= 58:
            move = pos_a1(x - 58)
            if is_white:
                base = move
            else:
                li.append(base + move)
            is_white = not is_white
        else:
            c = {50: "q", 51: "r", 52: "b", 53: "n"}.get(x, "")
            li[len(li) - 1] += c
    return li


def xpv_pv(xpv:str) -> str:
    return " ".join(xpv_lipv(xpv))


def pv_xpv(str pv):
    if not pv:
        return ""

    # Codificamos a bytes
    cdef bytes b_pv = pv.encode('ascii')
    cdef char* c_pv = b_pv

    # Cambiamos int por Py_ssize_t para evitar el warning C4244
    cdef Py_ssize_t n = len(b_pv)

    # El buffer de salida puede ser del mismo tamaño + 1 para el nulo
    cdef char* buffer = <char*>malloc((n + 1) * sizeof(char))

    try:
        pv_xpv_c(c_pv, buffer)
        # Convertimos de nuevo a string de Python
        return buffer.decode('ascii')
    finally:
        free(buffer)


def run_fen(fen: str, depth: int, ms: int, level: int):
    set_level(level)
    bfen = bytes(fen, "utf-8")
    x = play_fen(bfen, depth, ms)
    set_level(0)
    return x.decode("utf-8")


def set_fen(fen):
    fen = fen.encode("utf-8")
    fen_board(fen)
    return movegen()


def get_fen():
    cdef char fen[256]
    board_fen(fen)
    x = fen.decode("utf-8")
    return x

def get_fenm2():
    cdef char fen[256]
    board_fenM2(fen)
    x = fen.decode("utf-8")
    return x

def get_moves():
    cdef char pv[32]
    cdef int nmoves, x, nbase
    nmoves = num_moves()

    nbase = num_base_move()
    li = []
    for x in range(nmoves):
        get_move(x+nbase, pv)
        r = pv
        li.append(r.decode())
    return li


def get_pgn(from_a1h8: str, to_a1h8: str, promotion: str) -> str:
    cdef char san[32]

    bfrom_a1h8 = from_a1h8.encode("utf-8")
    bto_a1h8 = to_a1h8.encode("utf-8")
    bpromotion = promotion.encode("utf-8") if promotion else b""

    num = search_move(bfrom_a1h8, bto_a1h8, bpromotion)
    if num == -1:
        return None

    to_san(num, san)
    return san.decode("utf-8")


def get_pgn_b(bfrom_a1h8, bto_a1h8, bpromotion):
    cdef char san[32]

    num = search_move(bfrom_a1h8, bto_a1h8, bpromotion)
    if num == -1:
        return None

    to_san(num, san)
    return san.decode("utf-8")


def xpv_pgn(xpv):
    cdef char san[32]

    set_init_fen()
    is_white = True
    num = 1
    li = []
    tam = 0
    for pv in xpv_lipv(xpv):
        if is_white:
            x = b"%d." % num
            tam += len(x)
            li.append(x)
            num += 1
        is_white = not is_white

        num_move = search_move( pv[:2].encode("utf-8"), pv[2:4].encode("utf-8"), pv[4:].encode("utf-8") )
        if num_move == -1:
            break
        to_san(num_move, san)
        x = san + b""
        li.append(x)
        tam += len(x)
        if tam >= 80:
            li.append(b"\n")
            tam = 0
        else:
            li.append(b" ")
            tam += 1
        make_nummove(num_move)
    return (b"".join(li)).decode("utf-8")

def lipv_pgn(fen, lipv):
    cdef char san[32]
    set_fen(fen)
    is_white = " w " in fen
    li_pv = fen.split(" ")
    num = int(li_pv[len(li_pv) - 1])
    li = []
    tam = 0
    for pv in lipv:
        if is_white:
            x = b"%d." % num
            tam += len(x)
            li.append(x)
            num += 1
        is_white = not is_white

        num_move = search_move( pv[:2].encode("utf-8"), pv[2:4].encode("utf-8"), pv[4:].encode("utf-8") )
        if num_move == -1:
            break
        to_san(num_move, san)
        x = san + b""
        li.append(x)
        tam += len(x)
        if tam >= 80:
            li.append(b"\n")
            tam = 0
        else:
            li.append(b" ")
            tam += 1
        make_nummove(num_move)
    return (b"".join(li)).decode("utf-8")


def ischeck():
    return incheck()


class InfoMove(object):
    def __init__(self, num):
        cdef char pv[32]
        cdef char info[32]
        cdef char san[32]

        get_move(num, pv)
        get_move_ex(num, info)
        to_san(num, san)

        # info = P a1 h8 q [K|Q|]

        self._castle_K = info[6] == b"K"
        self._castle_Q = info[6] == b"Q"
        self._ep = info[7] == b"E"
        self._capt_piece = info[8]
        self._pv = pv
        self._san = san


        self._piece = info[0:1]
        self._from = info[1:3]
        self._to = info[3:5]
        self._promotion = info[5:6].strip()
        self._check = b"+" in san
        self._mate = b"#" in san
        self._capture = b"x" in san

    def xfrom(self):
        return self._from.decode("utf-8")

    def xto(self):
        return self._to.decode("utf-8")

    def promotion(self):
        return self._promotion.lower().decode("utf-8")

    def move(self):
        return (self._from + self._to + self._promotion.lower()).decode("utf-8")

    def bmove(self):
        return self._from + self._to + self._promotion.lower()

    def check(self):
        return self._check

    def mate(self):
        return self._mate

    def capture(self):
        return self._capture

    def piece(self):
        return self._piece.decode("utf-8")

    def piece_captured(self):
        return self._capt_piece.decode("utf-8")


    def iscastle_k(self):
        return self._castle_K

    def iscastle_q(self):
        return self._castle_Q

    def is_enpassant(self):
        return self._ep

    def san(self):
        return self._san.decode("utf-8")


def get_exmoves():
    nmoves = num_moves()

    nbase = num_base_move()
    li = []
    for x in range(nmoves):
        mv = InfoMove(x + nbase)
        li.append(mv)
    return li


def move_expv(xfrom: str, xto: str, promotion: str):
    bfrom = bytes(xfrom, "utf-8")
    bto = bytes(xto, "utf-8")
    bpromotion = bytes(promotion, "utf-8") if promotion else b""
    num = search_move( bfrom, bto, bpromotion )
    if num == -1:
        return None

    infoMove = InfoMove(num)
    make_nummove(num)

    return infoMove


def move_pv(xfrom: str, xto: str, promotion):
    bfrom = xfrom.encode("utf-8")
    bto = xto.encode("utf-8")
    bpromotion = bytes(promotion, "utf-8") if promotion else b""
    num = search_move( bfrom, bto, bpromotion )
    if num == -1:
        return False

    make_nummove(num)

    return True


def make_move(a1h8):
    xfrom = a1h8[:2]
    xto = a1h8[2:4]
    promotion = a1h8[4:]
    bfrom = bytes(xfrom, "utf-8")
    bto = bytes(xto, "utf-8")
    bpromotion = bytes(promotion, "utf-8")
    num = search_move( bfrom, bto, bpromotion )
    if num == -1:
        return False

    make_nummove(num)
    return True


def fen_fenm2(fen: str) -> str:
    sp1 = fen.rfind(" ")
    sp2 = fen.rfind(" ", 0, sp1)
    return fen[:sp2]


def set_init_fen():
    fen_board(b"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    movegen()


def make_pv(pv: str):
    set_init_fen()
    if pv:
        for move in pv.split(" "):
            make_move(move)
    return get_fen()


def get_exmoves_fen(fen):
    set_fen(fen)
    return get_exmoves()


def get_captures_fen(fen):
    set_fen(fen)
    nmoves = num_moves()
    nbase = num_base_move()
    li = []
    for x in range(nmoves):
        mv = InfoMove(x + nbase)
        if mv.capture():
            li.append(mv)
    return li


def get_captures(fen, siMB):
    if not siMB:
        fen = fen_other(fen)
    return get_captures_fen(fen)


def fen_other(fen):
    li = fen.split(" ")
    li[3] = "-"
    li[1] = "w" if li[1] == "b" else "b"
    return " ".join(li)


def fen_ended(fen):
    return set_fen(fen) == 0


def xparse_body(fen, body):
    body = bytes(body, "utf-8")
    fen = bytes(fen, "utf-8")
    resp = bytearray(len(body)*14//10)
    tam = parse_body( fen, body, resp )
    if tam:
        return resp[:tam].decode("utf-8").split("\n")
    else:
        return None

def xparse_pgn(pgn):
    pgn = pgn.strip()
    if len(pgn) == 0:
        return None
    if pgn[0] != "[":
        pgn = f'[Event "?"]\n{pgn}'
    pgn = bytes(pgn, "utf-8")
    resp = bytearray(len(pgn)*14//10)
    tam = parse_pgn( pgn, resp )
    if tam:
        return resp[:tam].decode("utf-8").split("\n")
    else:
        return None

def last_letter(x: str):
    return x[len(x)-1] if x else ""


def get_pgn_descriptive(is_white, from_sq, to_sq, promotion):
    # 1. Obtener la info del movimiento actual desde la lista de legales
    # para saber si es captura, jaque, etc.
    info_actual = None
    legal_moves = get_exmoves()
    move = from_sq + to_sq + promotion
    for m in legal_moves:
        if m.move() == move:
            info_actual = m
            break

    if not info_actual:
        return ""

    # 2. Manejo de Enroques
    if info_actual.iscastle_k():
        return "O-O"

    if info_actual.iscastle_q():
        return "O-O-O"

    piece_type = info_actual.piece().upper()  # N, B, R, Q, K, P

    # 3. Coordenadas de origen y destino en descriptiva
    FILES_DESC = ["QR", "QN", "QB", "Q", "K", "KB", "KN", "KR"]  # a-h

    def get_desc_coords(sq):
        """Convierte 'e4' a ('K', 4) desde la perspectiva del jugador"""
        col_idx = ord(sq[0]) - ord("a")
        rank = int(sq[1])

        desc_file = FILES_DESC[col_idx]
        # Si es blanco, fila 1 es 1. Si es negro, fila 8 es 1.
        desc_rank = rank if is_white else (9 - rank)

        return desc_file, desc_rank

    from_file_desc, from_rank_desc = get_desc_coords(from_sq)
    to_file_desc, to_rank_desc = get_desc_coords(to_sq)

    # Ala de la pieza que mueve: Q (columnas a-d) o K (columnas e-h)
    from_col_idx = ord(from_sq[0]) - ord("a")
    from_wing = "Q" if from_col_idx < 4 else "K"

    # 4. Resolución de Ambigüedades del PREFIJO (pieza que mueve)
    # Para movimientos simples: ¿otra pieza del mismo tipo va al mismo destino?
    # Para capturas: ¿otra pieza del mismo tipo puede capturar la misma clase de pieza?
    # Ambos casos → cualificar el ala de la pieza que mueve (ej: NQ, NK, BR...)

    def get_prefix(conflicts):
        """Desambiguación del prefijo en notación descriptiva.
        Nivel 1: ala distinta (Q vs K) → usar ala.
        Nivel 2: mismo ala, rango distinto → usar rango de origen.
        Nivel 3: mismo ala y mismo rango → usar nombre corto de columna origen."""
        conflict_list = list(conflicts)
        if not conflict_list:
            return piece_type

        def wing_of(sq):
            return "Q" if ord(sq[0]) - ord("a") < 4 else "K"

        def desc_rank_of(sq):
            return int(sq[1]) if is_white else 9 - int(sq[1])

        # Nivel 1: ¿algún conflicto en ala distinta?
        wing_conflicts = [m for m in conflict_list if wing_of(m.xfrom()) == from_wing]
        if not wing_conflicts:
            return f"{piece_type}{from_wing}"

        # Nivel 2: entre los del mismo ala, ¿alguno en el mismo rango?
        rank_conflicts = [
            m for m in wing_conflicts if desc_rank_of(m.xfrom()) == from_rank_desc
        ]
        if not rank_conflicts:
            return f"{piece_type}{from_rank_desc}"

        # Nivel 3: mismo ala y mismo rango → nombre corto de columna origen
        from_file_short = last_letter(FILES_DESC[from_col_idx])
        return f"{piece_type}{from_file_short}"

    # 5. Construcción del movimiento (Captura vs Movimiento simple)
    if info_actual.capture():
        piece_capt = info_actual.piece_captured()

        # Prefix: ¿otra pieza del mismo tipo TAMBIÉN puede capturar la misma clase de pieza?
        cap_conflicts = [
            m
            for m in legal_moves
            if m.piece().upper() == piece_type
            and m.xfrom() != from_sq
            and m.capture()
            and m.piece_captured().upper() == piece_capt.upper()
        ]
        prefix = get_prefix(cap_conflicts)

        # Sufijo: ¿esta misma pieza puede capturar otra pieza de la MISMA clase en otro escaque?
        cap_ambiguous = any(
            m.piece().upper() == piece_type
            and m.xfrom() == from_sq
            and m.xto() != to_sq
            and m.capture()
            and m.piece_captured().upper() == piece_capt.upper()
            for m in legal_moves
        )
        sufix = piece_capt.upper()
        if cap_ambiguous:
            sufix = f"{to_file_desc}{sufix}"
        move_str = f"{prefix}x{sufix}"
    else:
        # Prefix: ¿otra pieza del mismo tipo puede ir al mismo destino?
        simple_conflicts = [
            m
            for m in legal_moves
            if m.piece().upper() == piece_type
            and m.xto() == to_sq
            and m.xfrom() != from_sq
            and not m.capture()
        ]
        prefix = get_prefix(simple_conflicts)

        # Destino: el ala solo se incluye si otra pieza (distinta orígen Y distinto destino)
        # iría a un escaque con el mismo nombre corto y mismo rango descriptivo.
        # (Si van al mismo destino exacto, la ambigüedad está en el origen, no el destino.)
        to_col_idx = ord(to_sq[0]) - ord("a")
        to_file_short = last_letter(FILES_DESC[to_col_idx])  # última letra: 'R','N','B','Q','K'

        # Ambigüedad de destino: ¿existe otro escaque con el mismo nombre corto y
        # mismo rango descriptivo al que pueda ir cualquier pieza del mismo tipo
        # (incluyendo la propia)? Una torre que va a QB4 y KB4 ambas son "B4".
        dest_file_ambiguous = any(
            m.piece().upper() == piece_type
            and m.xto() != to_sq  # distinto destino algebraico
            and last_letter(FILES_DESC[ord(m.xto()[0]) - ord("a")])
            == to_file_short  # mismo nombre corto
            and (int(m.xto()[1]) if is_white else 9 - int(m.xto()[1]))
            == to_rank_desc  # mismo rango
            for m in legal_moves
            if not m.capture()
        )
        dest_label = to_file_desc if dest_file_ambiguous else to_file_short
        move_str = f"{prefix}-{dest_label}{to_rank_desc}"

    # 6. Sufijos (Jaque, Mate, Promoción)
    if info_actual.mate():
        move_str += "++"
    elif info_actual.check():
        move_str += "+"

    if promotion:
        move_str += f"={promotion.upper()}"

    return move_str


def get_pgn_longalgebraic(from_sq, to_sq, promotion):
    info = None
    legal_moves = get_exmoves()
    move = from_sq + to_sq + promotion
    for m in legal_moves:
        if m.move() == move:
            info = m
            break

    if not info:
        return ""

    ini = f"{info.piece().upper()}{from_sq}"
    sep = "x" if m.capture() else "-"
    end = to_sq
    if promotion:
        end += f"={promotion.upper()}"
    if info.mate():
        end += "#"
    elif info.check():
        end += "+"
    return f"{ini}{sep}{end}"
