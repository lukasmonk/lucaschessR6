from typing import Any, Optional, Tuple

import Code
from Code.Base.Constantes import (
    COL_BLACK,
    COL_NUMBER,
    COL_WHITE,
    GT_AGAINST_GM,
    GT_AGAINST_PGN,
    GT_ALONE,
    GT_BOOK,
    GT_ELO,
    GT_FICS,
    GT_FIDE,
    GT_GAME,
    GT_LEARN_PLAY,
    GT_MICELO,
    GT_NOTE_DOWN,
    GT_RESISTANCE,
    GT_ROUTES,
    GT_TURN_ON_LIGHTS,
    GT_VARIATIONS,
    GT_WICKER,
    RS_DRAW,
    RS_WIN_OPPONENT,
    RS_WIN_PLAYER,
    ST_ENDGAME,
    ST_PLAYING,
)
from Code.Z import Util


class ControlPGN:
    def __init__(self, manager: Any) -> None:
        self.manager = manager
        self.with_figurines = Code.configuration.x_pgn_withfigurines
        self.must_show = True

        self.pos_variation = None

    @property
    def variations_mode(self) -> bool:
        state = self.manager.state
        game_type = self.manager.game_type
        return game_type in (GT_ALONE, GT_GAME, GT_VARIATIONS) or state == ST_ENDGAME

    def num_rows(self) -> int:
        if self.manager.game:
            n = len(self.manager.game)
            if self.manager.game.starts_with_black:
                n += 1
            if n % 2 == 1:
                n += 1
            return n // 2
        else:
            return 0

    def only_move(self, row: int, key: str) -> Optional[Any]:
        li_moves = self.manager.game.li_moves

        pos = row * 2
        size_limoves = len(li_moves)

        if key == COL_WHITE:
            if self.manager.game.starts_with_black:
                pos -= 1
        else:
            if not self.manager.game.starts_with_black:
                pos += 1

        if 0 <= pos <= (size_limoves - 1):
            return li_moves[pos]
        else:
            return None

    def dato(self, row: int, key: str) -> str:
        if key == COL_NUMBER:
            return str(self.manager.game.first_num_move() + row)

        move = self.only_move(row, key)
        if move:
            if self.must_show:
                return move.pgn_figurines() if self.with_figurines else move.pgn_translated()
            else:
                return "-"
        else:
            return " "

    def analysis(self, row: int, key: str) -> Optional[Any]:
        if key == COL_NUMBER:
            return None
        return self.only_move(row, key)

    def goto_row_iswhite(self, row: int, is_white: bool) -> None:
        starts_with_black = self.manager.game.starts_with_black

        if row == 0 and is_white and starts_with_black:
            return

        lj = self.manager.game.li_moves
        pos = row * 2
        if not is_white:
            pos += 1
        if starts_with_black:
            pos -= 1

        tam_lj = len(lj)
        if tam_lj:

            is_last = (pos + 1) >= tam_lj
            if is_last:
                pos = tam_lj - 1

            move = self.manager.game.move(pos)

            if is_last:
                self.manager.set_position(move.position, variation_history=str(pos))
                if self.manager.human_is_playing and self.manager.state == ST_PLAYING:
                    if self.manager.game_type in (
                            GT_ALONE,
                            GT_GAME,
                            GT_VARIATIONS,
                            GT_LEARN_PLAY,
                    ):
                        side = move.position.is_white
                    else:
                        side = self.manager.is_human_side_white
                    self.manager.activate_side(side)
            else:
                if self.variations_mode:
                    self.manager.set_position(move.position, variation_history=str(pos))
                else:
                    self.manager.set_position(move.position)
                    self.manager.disable_all()

            self.manager.put_arrow_sc(move.from_sq, move.to_sq)
            self.manager.refresh()

    def get_pos_move(self, row: int, key: str) -> Tuple[Optional[int], Optional[Any]]:
        tam_lj = len(self.manager.game)
        if tam_lj == 0:
            return None, None
        starts_with_black = self.manager.game.starts_with_black
        if row == 0:
            if key == COL_NUMBER or (key == COL_WHITE and starts_with_black):
                return 0, self.manager.game.move(0)

        is_white = key != COL_BLACK

        pos = row * 2
        if not is_white:
            pos += 1
        if starts_with_black:
            pos -= 1

        if pos >= len(self.manager.game):
            pos = len(self.manager.game) - 1

        return pos, self.manager.game.move(pos)

    def actual(self) -> str:
        game_type = self.manager.game_type

        if game_type in (
                GT_AGAINST_PGN,
                GT_ALONE,
                GT_GAME,
                GT_VARIATIONS,
                GT_ROUTES,
                GT_TURN_ON_LIGHTS,
                GT_NOTE_DOWN,
                GT_AGAINST_GM,
        ):
            return self.manager.current_pgn()

        if game_type == GT_BOOK:
            rival = self.manager.book.name
        elif game_type in (GT_FICS, GT_FIDE):
            rival = self.manager.name_obj
        elif self.manager.xrival:  # foncap change
            rival = self.manager.xrival.name  # foncap change
        else:  # foncap change
            rival = ""  # foncap change

        player = self.manager.configuration.nom_player()
        resultado = self.manager.resultado
        human_side = self.manager.is_human_side_white

        if resultado == RS_WIN_PLAYER:
            r = "1-0" if human_side else "0-1"
        elif resultado == RS_WIN_OPPONENT:
            r = "0-1" if human_side else "1-0"
        elif resultado == RS_DRAW:
            r = "1/2-1/2"
        else:
            r = "*"
        if human_side:
            blancas = player
            negras = rival
        else:
            blancas = rival
            negras = player
        hoy = Util.today()
        resp = f'[Site "{Code.lucas_chess}"]\n'
        # Site (lugar): el lugar donde el evento se llevo a cabo.
        # Esto debe ser en formato "Ciudad, Region PAIS", donde PAIS es el codigo del mismo
        # en tres letras de acuerdo al codigo del Comite Olimpico Internacional. Como ejemplo: "Mexico, D.F. MEX".
        resp += f'[Date "{hoy.year}.{hoy.month:02d}.{hoy.day:02d}"]\n'
        # Round (ronda): La ronda original de la game.
        resp += f'[White "{blancas}"]\n'
        resp += f'[Black "{negras}"]\n'
        resp += f'[Result "{r}"]\n'

        if self.manager.fen:
            resp += f'[FEN "{self.manager.fen}"]\n'

        xrival = getattr(self.manager, "xrival", None)
        if xrival and game_type not in [GT_BOOK]:
            if xrival.depth_engine:
                resp += f'[Depth "{xrival.depth_engine}"]\n'

            if xrival.mstime_engine:
                resp += f'[TimeEngineMS "{xrival.mstime_engine}"]\n'

            if self.manager.categoria:
                resp += f'[Category "{self.manager.categoria.name()}"]\n'

        if game_type not in [GT_BOOK, GT_RESISTANCE]:
            if self.manager.hints:
                resp += f'[Hints "{self.manager.hints}"]\n'

        if game_type in (GT_ELO, GT_MICELO, GT_WICKER):
            resp += f'[WhiteElo "{self.manager.white_elo}"]\n'
            resp += f'[BlackElo "{self.manager.black_elo}"]\n'

        ap = self.manager.game.opening
        if ap:
            resp += f'[ECO "{ap.eco}"]\n'
            resp += f'[Opening "{ap.tr_name}"]\n'

        dmore = getattr(self.manager, "pgnLabelsAdded", None)
        if dmore:
            for k, v in dmore().items():
                resp += f'[{k} "{v}"]\n'

        resp += f"\n{self.manager.game.pgn_base()}"
        if not resp.endswith(r):
            resp += f" {r}"

        return resp
