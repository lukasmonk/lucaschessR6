"""Epaulette Mate Theme implementation.

This module defines the :class:`EpauletteMate` theme, which identifies checkmates
where the king is blocked on both sides ("epaulettes") by its own pieces, preventing
escape from a frontal attack.
"""

from Code.Base import Move, Position
from Code.Engines import EngineResponse
from Code.Themes import CheckTheme


class EpauletteMate(CheckTheme.CheckTheme):
    """Theme that recognises *Epaulette Mate*.

    An Epaulette Mate occurs when:
    1. The king is in checkmate.
    2. The king is attacked from the front (same file or rank).
    3. The two squares adjacent to the king on his rank (or file) are occupied
       by his own pieces, blocking escape.
    """

    def __init__(self) -> None:
        """Initialise the theme identifier."""
        self.theme = "epauletteMate"
        self.is_mate = True

    def is_theme(self, move: Move.Move) -> bool:
        """Return ``True`` if *move* results in an Epaulette Mate.

        Parameters
        ----------
        move: :class:`Code.Base.Move.Move`
            The move to evaluate. It must contain a valid ``analysis`` attribute.
        """
        # -------------------------------------------------------------------
        # Input validation
        # -------------------------------------------------------------------
        if not hasattr(move, "analysis"):
            return False

        mrm, pos_rm = move.analysis
        rm: EngineResponse.EngineResponse = mrm.li_rm[pos_rm]

        # -------------------------------------------------------------------
        # 1. Must be Checkmate
        # -------------------------------------------------------------------
        # rm.mate is usually positive for white winning, negative for black winning.
        # If it's 0, it's not mate. If it's close to 0 (e.g. 1 or -1), it's mate in 1.
        if rm.mate == 0:
            return False

        # -------------------------------------------------------------------
        # Setup positions
        # -------------------------------------------------------------------
        # We need the position AFTER the move to check the mate configuration
        position: Position.Position = move.position_before.copia()
        position.play_pv(rm.pv.split(" ")[0])  # Play the mating move

        # Identify sides
        # If move.is_white() is True, White just moved and gave mate to Black.
        attacker_is_white = move.is_white()
        victim_is_white = not attacker_is_white

        # Get King position
        pos_king = position.get_pos_king(victim_is_white)  # e.g. "e8"
        col_k, row_k = pos_king[0], int(pos_king[1])

        # Get Attacker position (the piece that moved to give mate)
        # The last move in PV is the mating move.
        # rm.to_sq is the destination of the move.
        pos_attacker = rm.to_sq
        piece_attacker = position.get_pz(pos_attacker)

        # -------------------------------------------------------------------
        # 2. Attacker must be Queen or Rook (typically)
        # -------------------------------------------------------------------
        if piece_attacker.upper() not in ("Q", "R"):
            return False

        # -------------------------------------------------------------------
        # 3. Geometric Check: "Epaulettes" (Shoulders)
        # -------------------------------------------------------------------
        # We check if the squares to the left and right (or up/down) are blocked by own pieces.
        # Standard Epaulette: King on edge, attacked vertically, blocked horizontally.

        # Check if attack is vertical (same file)
        if pos_attacker[0] == col_k:
            # Attack is vertical (e.g. Re1 attacking Ke8)
            # Epaulettes should be on the left and right of the King (same rank)

            # Left square
            if col_k > "a":
                sq_left = chr(ord(col_k) - 1) + str(row_k)
                pz_left = position.get_pz(sq_left)
                # Must be occupied by own piece
                if not pz_left or Position.is_white(pz_left) != victim_is_white:
                    return False

            # Right square
            if col_k < "h":
                sq_right = chr(ord(col_k) + 1) + str(row_k)
                pz_right = position.get_pz(sq_right)
                # Must be occupied by own piece
                if not pz_right or Position.is_white(pz_right) != victim_is_white:
                    return False

            # If King is not on edge, check if he can move backwards (away from attacker)
            # Usually Epaulette is on the edge, but if not, the square behind must also be blocked/controlled.
            # For simplicity in this "theme" detection, we often assume edge or blocked behind.
            # Let's check if the King has valid escape squares.
            # If it's mate, he has none. The theme is about WHY he has none (the epaulettes).
            # So if we found the epaulettes, and it is mate, it's likely an Epaulette mate.
            return True

        # Check if attack is horizontal (same rank)
        elif int(pos_attacker[1]) == row_k:
            # Attack is horizontal (e.g. Ra5 attacking Rh5)
            # Epaulettes should be above and below the King (same file)

            # Square below
            if row_k > 1:
                sq_down = col_k + str(row_k - 1)
                pz_down = position.get_pz(sq_down)
                if not pz_down or Position.is_white(pz_down) != victim_is_white:
                    return False

            # Square above
            if row_k < 8:
                sq_up = col_k + str(row_k + 1)
                pz_up = position.get_pz(sq_up)
                if not pz_up or Position.is_white(pz_up) != victim_is_white:
                    return False

            return True

        return False
