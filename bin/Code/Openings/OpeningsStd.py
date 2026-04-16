import collections

import FasterCode

import Code
from Code.Base import Position
from Code.Base.Constantes import FENM2_INITIAL
from Code.Translations import TrListas
from Code.Z import Util

# ---------------------------------------------------------------------------
# Piece-letter set used by tr_pgn (pre-computed at module level)
# ---------------------------------------------------------------------------
_PIECE_LETTERS = frozenset("KQRBNPkqrbnp")
fen_fenm2 = FasterCode.fen_fenm2


class Opening:
    __slots__ = ("name", "parent_fm2", "children_fm2", "a1h8", "pgn", "eco", "is_basic", "fm2")

    def __init__(self, key: str):
        self.name: str = key
        self.parent_fm2: str = ""
        self.children_fm2: list = []
        self.a1h8: str = ""
        self.pgn: str = ""
        self.eco: str = ""
        self.is_basic: bool = False
        self.fm2: str | None = None

    @property
    def tr_name(self) -> str:
        return _FO(self.name)

    def tr_pgn(self) -> str:
        """Return the PGN notation with piece letters translated to the UI language."""
        parts = []
        pgn = self.pgn
        last = len(pgn) - 1
        for n, c in enumerate(pgn):
            if c in _PIECE_LETTERS and (n == last or not pgn[n + 1].isdigit()):
                c = TrListas.letter_piece(c)
            parts.append(c)
        return "".join(parts)

    def __str__(self) -> str:
        return f"{self.name} {self.pgn}"

    def __repr__(self) -> str:
        return f"Opening({self.name!r}, eco={self.eco!r})"


class ListaOpeningsStd:
    def __init__(self):
        self.st_fenm2_test: set = set()
        self.dic_fenm2_op: dict = {}
        self.dic_fenm2_op_all: dict = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_lkop_lines():
        """Yield parsed field-tuples from openings.lkop."""
        path = Code.path_resource("Openings", "openings.lkop")
        with open(path, "rt", encoding="utf-8") as fh:
            for linea in fh:
                yield linea.rstrip("\n").split("|")

    # ------------------------------------------------------------------
    # Static readers
    # ------------------------------------------------------------------

    @staticmethod
    def read_fenm2_test() -> set:
        path = Code.path_resource("Openings", "openings.lkfen")
        with open(path, "rt") as fh:
            return set(fh.read().split("|"))

    @staticmethod
    def read_fenm2_op():
        """Read the main openings file and return the three data structures."""
        path = Code.path_resource("Openings", "openings.lkop")
        dic_fenm2_op: dict = {}
        dic_fenm2_op_all: collections.defaultdict = collections.defaultdict(set)
        st_fenm2_test: set = set()

        with open(path, "rt", encoding="utf-8") as fh:
            for linea in fh:
                fields = linea.rstrip("\n").split("|")
                name, a1h8, pgn, eco, basic, fenm2, _hijos, parent, lfenm2 = fields

                op = Opening(name)
                op.a1h8 = a1h8
                op.eco = eco
                op.pgn = pgn
                op.parent_fm2 = parent
                op.is_basic = basic == "Y"
                op.fm2 = fenm2

                dic_fenm2_op[fenm2] = op
                dic_fenm2_op_all[fenm2].add(op)
                st_fenm2_test.add(fenm2)
                if parent:
                    st_fenm2_test.add(parent)

                li_pv = a1h8.split(" ")
                li_fenm2 = lfenm2.split(",")
                for x, _ in enumerate(li_pv):
                    fm2_x = FENM2_INITIAL if x == 0 else li_fenm2[x - 1]
                    dic_fenm2_op_all[fm2_x].add(op)
                    st_fenm2_test.add(fm2_x)

        return dic_fenm2_op, dic_fenm2_op_all, st_fenm2_test

    @staticmethod
    def dic_fen64() -> dict:
        """Return {fen64: [pv, ...]} for every intermediate position in openings.lkop."""
        path = Code.path_resource("Openings", "openings.lkop")
        dd: collections.defaultdict = collections.defaultdict(list)

        with open(path, "rt", encoding="utf-8") as fh:
            for linea in fh:
                fields = linea.strip().split("|")
                _name, a1h8, _pgn, _eco, _basic, _fenm2, _hijos, _parent, lfenm2 = fields

                li_fen = [FENM2_INITIAL]
                li_fen.extend(lfenm2.split(","))

                li_moves = a1h8.split(" ")
                for pos, move in enumerate(li_moves):
                    pv = " ".join(li_moves[: pos])
                    fen64 = Util.fen_fen64(li_fen[pos])
                    if pv not in dd[fen64]:
                        dd[fen64].append(pv)

        return dd

    # ------------------------------------------------------------------
    # Initialisation / reload
    # ------------------------------------------------------------------

    def reset(self):
        """(Re)load all opening data from disk."""
        self.dic_fenm2_op, self.dic_fenm2_op_all, self.st_fenm2_test = self.read_fenm2_op()
        self.read_personal()

    def read_personal(self):
        """Merge user-defined personal openings into the loaded data."""
        fichero_pers = Code.configuration.paths.file_pers_openings()
        lista = Util.restore_pickle(fichero_pers, [])
        for reg in lista:
            op = Opening(reg["NOMBRE"])
            op.eco = reg["ECO"]
            op.a1h8 = reg["A1H8"]
            op.pgn = reg["PGN"]
            op.is_basic = reg["ESTANDAR"]
            li_uci = op.a1h8.split(" ")
            num = len(li_uci)
            for x in range(num):
                pv = " ".join(li_uci[: x + 1])
                fen = FasterCode.make_pv(pv)
                fm2 = Position.legal_fenm2(fen)
                self.st_fenm2_test.add(fm2)
                if x == num - 1:
                    self.dic_fenm2_op[fm2] = op
                    op.fm2 = fm2

    # ------------------------------------------------------------------
    # Opening assignment
    # ------------------------------------------------------------------

    def assign_opening(self, game) -> None:
        """Assign the deepest matching opening to *game*.

        Sets ``game.opening`` (an :class:`Opening` or ``None``) and marks
        moves up to the last recognised position with ``in_the_opening = True``.

        The search stops early after 10 consecutive unrecognised positions to
        avoid scanning the rest of a long game needlessly.
        """
        game.opening = None
        game.pending_opening = True

        without = 0
        last_move_opening = -1
        st = self.st_fenm2_test
        dic = self.dic_fenm2_op

        for nj, move in enumerate(game.li_moves):
            fm2 = move.position.fenm2()
            if fm2 in st:
                if fm2 in dic:
                    game.opening = dic[fm2]
                    game.pending_opening = False
                last_move_opening = nj
                without = 0  # reset streak on any recognised fen
            else:
                without += 1
                if without == 10:
                    game.pending_opening = False
                    break

        if last_move_opening >= 0:
            for np in range(last_move_opening + 1):
                game.move(np).in_the_opening = True

    # ------------------------------------------------------------------
    # Possible-openings query
    # ------------------------------------------------------------------
    def list_possible_openings(self, game) -> list:
        """Return openings reachable from *game*'s current position, sorted."""
        fm2 = game.last_position.fenm2()

        if not (all_openings := self.dic_fenm2_op_all.get(fm2)):
            return []

        selected = self.dic_fenm2_op.get(fm2)
        candidates = sorted(
            (op for op in all_openings if op != selected),
            key=lambda op: op.a1h8,
        )

        # Drop openings whose a1h8 is a prefix of a subsequent one (keep the longer)
        deduped = []
        last_a1h8 = None
        for op in candidates:
            if last_a1h8 is None or not op.a1h8.startswith(last_a1h8):
                last_a1h8 = op.a1h8
                deduped.append(op)

        deduped.sort(key=lambda op: ("A" if op.is_basic else "B") + op.tr_name.upper())
        return deduped

    # ------------------------------------------------------------------
    # xpv / pv helpers (shared implementation)
    # ------------------------------------------------------------------

    def _lookup_last_opening(self, pv_str: str):
        """Walk *pv_str* move by move and return the deepest matching Opening."""
        last_ap = None
        FasterCode.set_init_fen()
        for pv in pv_str.split(" "):
            FasterCode.make_move(pv)
            fenm2 = Position.legal_fenm2(FasterCode.get_fen())
            if fenm2 in self.dic_fenm2_op:
                last_ap = self.dic_fenm2_op[fenm2]
        return last_ap

    def base_xpv(self, xpv):
        return self._lookup_last_opening(FasterCode.xpv_pv(xpv))

    def xpv(self, xpv) -> str:
        last_ap = self.base_xpv(xpv)
        return last_ap.tr_name if last_ap else ""

    def xpv_eco(self, xpv) -> str:
        last_ap = self.base_xpv(xpv)
        return last_ap.eco if last_ap else ""

    def assign_pv(self, pv: str):
        """Return the deepest Opening matching the UCI pv string, or None."""
        return self._lookup_last_opening(pv)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def is_book_fenm2(self, fenm2: str) -> bool:
        """Return True if *fenm2* is part of any known opening."""
        return fenm2 in self.st_fenm2_test


# ---------------------------------------------------------------------------
# Module-level singleton – lazy initialisation so import is free
# ---------------------------------------------------------------------------
class _LazySingleton:
    """Proxy that initialises ListaOpeningsStd on first attribute access."""

    _instance: ListaOpeningsStd | None = None

    def _get(self) -> ListaOpeningsStd:
        if self._instance is None:
            inst = ListaOpeningsStd.__new__(ListaOpeningsStd)
            ListaOpeningsStd.__init__(inst)
            self._instance = inst
        return self._instance

    def __getattr__(self, name):
        return getattr(self._get(), name)

    def reset(self):
        self._get().reset()


ap: ListaOpeningsStd = _LazySingleton()  # type: ignore[assignment]
