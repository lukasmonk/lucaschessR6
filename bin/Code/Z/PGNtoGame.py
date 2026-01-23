from typing import Dict, Optional, Union, List

import FasterCode

import Code
from Code import Util
from Code.Base import Position
from Code.Base.Constantes import FEN_INITIAL, RESULT_DRAW, RESULT_UNKNOWN, RESULT_WIN_BLACK, RESULT_WIN_WHITE
from Code.Nags.Nags import NAG_1, NAG_2, NAG_3, NAG_4, NAG_5, NAG_6


class PGNtoGame:
    """
    Represents a chess game and provides PGN import capabilities.
    """

    NAG_SYMBOLS: Dict[str, int] = {
        "!": NAG_1,
        "?": NAG_2,
        "!!": NAG_3,
        "‼": NAG_3,
        "??": NAG_4,
        "⁇": NAG_4,
        "!?": NAG_5,
        "⁉": NAG_5,
        "?!": NAG_6,
        "⁈": NAG_6,
    }
    _last_position: Position.Position
    _active_move: object
    _fen_detected: bool

    def __init__(self, pgn: Union[str, bytes], game: object | None = None):
        """Initialize a PGNtoGame instance with PGN content and an optional game object.
        This sets up the converter to populate or update the provided Game instance.

        The PGN input is stored for later parsing, and a new Game is created if none is supplied.
        This allows the same class to be used for both creating fresh games and enriching existing ones.

        Args:
            pgn: PGN content as a string or bytes to be parsed into game moves and metadata.
            game: Optional existing Game instance to populate; if omitted, a new Game is created.
        """
        self.pgn = pgn
        self.game = Code.Base.Game.Game() if game is None else game

    def read(self):
        normalized_pgn: str = self._normalize_pgn(self.pgn)
        tokens: Optional[List[str]] = FasterCode.xparse_pgn(normalized_pgn)
        if not tokens:
            return False, self.game

        self._last_position: Position.Position = self.game.first_position
        self._active_move = None
        self._fen_detected: bool = False

        FasterCode.set_init_fen()

        handlers = {
            "[": self._handle_tag,
            "M": self._handle_move,
            "$": self._handle_numeric_nag,
            "{": self._handle_comment,
            ";": self._handle_comment,
            "(": self._handle_variation,
            "R": self._handle_result,
        }

        token: str
        for token in tokens:
            key: str = token[0] if token else ""
            if handler := handlers.get(key):
                handler(token)
            elif token in self.NAG_SYMBOLS:
                self._handle_symbolic_nag(token)

        if self._fen_detected:
            self.game.pending_opening = False

        if self._active_move:
            self.game.verify()

        return True, self.game

    @staticmethod
    def _normalize_pgn(pgn: Union[str, bytes]) -> str:
        """
        Normalize PGN input to a UTF-8 string.

        Args:
            pgn: PGN content as string or bytes.

        Returns:
            PGN content as a decoded string.
        """
        if isinstance(pgn, bytes):
            try:
                pgn, _ = Util.bytes_str_codec(pgn)
            except UnicodeDecodeError:
                pgn = pgn.decode("utf-8", errors="ignore")
        return pgn

    def _handle_tag(self, token: str) -> None:
        """
        Handle PGN tag tokens (e.g. [Event "..."], [FEN "..."]).

        Args:
            token: Raw PGN tag token.
        """
        kv: str = token[1:].strip()
        pos: int = kv.find(" ")
        if pos <= 0:
            return

        label: str = kv[:pos]
        value: str = kv[pos + 1:].strip()
        label_upper: str = label.upper()

        if label_upper == "FEN":
            FasterCode.set_fen(value)
            if value != FEN_INITIAL:
                self.game.set_fen(value)
                self._last_position = self.game.first_position
                self._fen_detected = True
            self.game.set_tag(label, value)

        elif label_upper == "RESULT":
            self.result = value
            self.game.set_tag("Result", value)

        else:
            self.game.set_tag(label, value)

    def _handle_move(self, token: str) -> None:
        """
        Handle a move token and update game state.

        Args:
            token: PGN move token.
        """
        move_str: str = token[1:]
        base_position: Position.Position = self._last_position

        FasterCode.make_move(move_str)

        new_position: Position.Position = Position.Position()
        new_position.read_fen(FasterCode.get_fen())

        move: Code.Base.Move.Move = Code.Base.Move.Move(
            self,
            base_position,
            new_position,
            move_str[:2],
            move_str[2:4],
            move_str[4:],
        )

        self.game.li_moves.append(move)
        self._active_move = move
        self._last_position = new_position

    def _handle_numeric_nag(self, token: str) -> None:
        """
        Handle numeric NAG tokens (e.g. $1, $3).

        Args:
            token: Numeric NAG token.
        """
        if not self._active_move:
            return

        nag_str: str = token[1:]
        if nag_str.isdigit():
            nag: int = int(nag_str)
            if 0 < nag < 256:
                self._active_move.add_nag(nag)

    def _handle_symbolic_nag(self, token: str) -> None:
        """
        Handle symbolic NAG tokens (e.g. !, ??, !?).

        Args:
            token: Symbolic NAG token.
        """
        if self._active_move:
            self._active_move.add_nag(self.NAG_SYMBOLS[token])

    def _handle_comment(self, token: str) -> None:
        """
        Handle PGN comments.

        Args:
            token: Comment token.
        """
        comment: str = token[1:-1].strip()
        if not comment:
            return

        if self._active_move:
            if self._active_move.comment:
                self._active_move.comment += "\n"
            self._active_move.comment += comment.replace("}", "]")
        else:
            self.game.set_first_comment(comment, False)

    def _handle_variation(self, token: str) -> None:
        """
        Handle PGN variations.

        Args:
            token: Variation token.
        """
        if not self._active_move:
            return

        variation: str = token[1:-1].strip()
        if not variation:
            return

        fen: str = FasterCode.get_fen()
        self._active_move.variations.add_pgn_variation(variation)
        FasterCode.set_fen(fen)

    def _handle_result(self, token: str) -> None:
        """
        Handle PGN result markers.

        Args:
            token: Result token.
        """
        if not self._active_move:
            return

        code: str = token[1]
        if code == "1":
            self.result = RESULT_WIN_WHITE
        elif code == "2":
            self.result = RESULT_DRAW
        elif code == "3":
            self.result = RESULT_WIN_BLACK
        elif code == "0":
            self.result = RESULT_UNKNOWN


def pgn_to_game(pgn):
    ptg = PGNtoGame(pgn)
    return ptg.read()
