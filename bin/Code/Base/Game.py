from typing import Any, Dict, Optional, Union, List

import FasterCode

from Code.Base import Move, Position
from Code.Base.Constantes import (
    ALL,
    ALLGAME,
    BEEP_DRAW,
    BEEP_DRAW_50,
    BEEP_DRAW_MATERIAL,
    BEEP_DRAW_REPETITION,
    BEEP_WIN_OPPONENT,
    BEEP_WIN_OPPONENT_TIME,
    BEEP_WIN_PLAYER,
    BEEP_WIN_PLAYER_TIME,
    BLACK,
    FEN_INITIAL,
    INFINITE,
    LI_BASIC_TAGS,
    NONE,
    ONLY_BLACK,
    ONLY_WHITE,
    RESULT_DRAW,
    RESULT_UNKNOWN,
    RESULT_WIN_BLACK,
    RESULT_WIN_WHITE,
    STANDARD_TAGS,
    TACTICTHEMES,
    TERMINATION_ADJUDICATION,
    TERMINATION_DRAW_50,
    TERMINATION_DRAW_AGREEMENT,
    TERMINATION_DRAW_MATERIAL,
    TERMINATION_DRAW_REPETITION,
    TERMINATION_DRAW_STALEMATE,
    TERMINATION_ENGINE_MALFUNCTION,
    TERMINATION_MATE,
    TERMINATION_RESIGN,
    TERMINATION_UNKNOWN,
    TERMINATION_WIN_ON_TIME,
    WHITE,
    OPENING,
    MIDDLEGAME,
    ENDGAME,
    PHASE_NODEFINED,
)
from Code.Nags.Nags import NAG_1, NAG_2, NAG_3, NAG_4, NAG_5, NAG_6
from Code.Openings import Opening, OpeningsStd
from Code.Z import Util


class Game:
    li_moves = None
    opening = None
    rotuloTablasRepeticion = None
    pending_opening = True
    termination = TERMINATION_UNKNOWN
    result = RESULT_UNKNOWN
    first_position = None

    def __init__(self, first_position=None, fen=None, li_tags=None):
        self.first_comment = ""
        self.li_tags = li_tags or []
        if fen:
            self.set_fen(fen)
        else:
            self.set_position(first_position)

    def reset(self):
        self.set_position(self.first_position)

    def set_fen(self, fen):
        if not fen or fen == FEN_INITIAL:
            self.set_position()
            return

        cp = Position.Position()
        cp.read_fen(fen)
        self.set_position(cp)

    def set_position(self, first_position=None):
        if first_position and first_position.is_initial():
            first_position = None

        self.li_moves = []
        self.opening = None
        self.termination = TERMINATION_UNKNOWN
        self.result = RESULT_UNKNOWN
        self.del_tag("Termination")
        self.del_tag("Result")
        self.rotuloTablasRepeticion = None
        self.pending_opening = True

        if first_position:
            self.first_position = first_position.copia()
        else:
            self.del_tag("Opening")
            self.del_tag("ECO")
            self.first_position = Position.Position()
            self.first_position.set_pos_initial()

    def is_mate(self):
        return self.termination == TERMINATION_MATE

    def set_termination_time(self, white_has_lost):
        self.termination = TERMINATION_WIN_ON_TIME
        self.result = RESULT_WIN_BLACK if white_has_lost else RESULT_WIN_WHITE
        self.set_extend_tags()

    def set_termination(self, termination, result):
        self.termination = termination
        self.result = result
        self.set_extend_tags()

    def set_unknown(self):
        self.set_termination(TERMINATION_UNKNOWN, RESULT_UNKNOWN)
        if self.get_tag("Result"):
            self.set_tag("Result", RESULT_UNKNOWN)

    def add_tag_date(self):
        hoy = Util.today()
        self.set_tag("Date", "%d.%02d.%02d" % (hoy.year, hoy.month, hoy.day))

    def add_tag_timestart(self):
        t = Util.today()
        self.set_tag("TimeStart", str(t)[:19].replace("-", "."))

    def tag_timeend(self):
        t = Util.today()
        self.set_tag("TimeEnd", str(t)[:19].replace("-", "."))

    @property
    def last_position(self):
        position = self.li_moves[-1].position if self.li_moves else self.first_position
        return position.copia()

    @property
    def starts_with_black(self):
        return not self.first_position.is_white

    def save(self, with_litags=True):
        dic = {
            "first_position": self.first_position.fen(),
            "first_comment": self.first_comment,
            "li_moves": [move.save() for move in self.li_moves],
            "result": self.result,
            "termination": self.termination,
        }
        if with_litags and self.li_tags:
            dic["li_tags"] = self.li_tags

        if self.first_position.is_initial():
            self.del_tag("FEN")
        return Util.var2zip(dic)

    def restore(self, btxt_save):
        self.reset()
        dic = Util.zip2var(btxt_save)
        if not dic:
            return
        self.first_position = Position.Position()
        self.first_position.read_fen(dic["first_position"])
        self.first_comment = dic["first_comment"]
        self.result = dic["result"]
        self.termination = dic["termination"]
        self.li_moves = []
        cp = self.first_position.copia()
        for save_jg in dic["li_moves"]:
            move = Move.Move(self, position_before=cp)
            move.restore(save_jg)
            cp = move.position.copia()
            self.li_moves.append(move)
        self.assign_opening()
        self.si3repetidas()
        self.set_result()
        self.li_tags = dic.get("li_tags", [])

    def __eq__(self, other):
        return self.save() == other.save()

    def eq_body(self, other):
        return self.save(False) == other.save(False)

    def set_tags(self, litags):
        self.li_tags = litags[:]
        self.check_tags()
        self.set_result()

    def check_tags(self):
        if self.first_position and not self.first_position.is_initial() and not self.get_tag("FEN"):
            self.set_tag("FEN", self.first_position.fen())
            self.order_tags()

    def set_result(self):
        self.result = RESULT_UNKNOWN
        for pos, (tag, value) in enumerate(self.li_tags):
            if tag.upper() == "RESULT":
                if value.strip() not in (
                        RESULT_UNKNOWN,
                        RESULT_WIN_BLACK,
                        RESULT_WIN_WHITE,
                        RESULT_DRAW,
                ):
                    value = RESULT_UNKNOWN
                self.li_tags[pos] = ["Result", value]
                self.result = value
                break

    def get_tag(self, tag):
        tag = tag.upper()
        return next((v for k, v in self.li_tags if k.upper() == tag), "")

    def has_tag(self, tag):
        return len(self.get_tag(tag)) > 0

    def dic_tags(self):
        return dict(self.li_tags)

    def order_tags(self):
        self.set_result()
        li_main = []
        li_resto = []
        dic = {k.upper(): (k, v) for k, v in self.li_tags}
        li_main.extend(dic[k] for k in LI_BASIC_TAGS if k in dic)
        li_resto.extend(v for k, v in dic.items() if k not in LI_BASIC_TAGS)
        self.li_tags = li_main
        self.li_tags.extend(li_resto)

    def set_tag(self, key, value):
        if not value:
            self.del_tag(key)
            return
        found = False
        key_upper = key.upper()
        for n, (xkey, xvalue) in enumerate(self.li_tags):
            if xkey.upper() == key_upper:
                self.li_tags[n] = [key, value]
                found = True
                break
        if not found:
            self.li_tags.append([key, value])
        if key == "Result":
            self.set_result()

    def del_tag(self, key):
        key_upper = key.upper()
        for n, (xkey, xvalue) in enumerate(self.li_tags):
            if xkey.upper() == key_upper:
                del self.li_tags[n]
                self.set_result()
                return
        self.set_result()

    def set_extend_tags(self):
        if self.result:
            self.set_tag("Result", self.result)

        if self.termination:
            tm = self.get_tag("Termination")
            if not tm and self.termination != TERMINATION_UNKNOWN:
                if txt := self.label_termination():
                    self.set_tag("Termination", txt)

        if self.is_fen_initial():
            op = self.get_tag("OPENING")
            eco = self.get_tag("ECO")
            if not op or not eco:
                self.assign_opening()
                if self.opening:
                    if not op:
                        self.li_tags.append(["Opening", self.opening.tr_name])
                    if not eco:
                        self.li_tags.append(["ECO", self.opening.eco])
        else:
            self.set_tag("FEN", self.first_position.fen())

        if self.num_moves():
            self.set_tag("PlyCount", "%d" % self.num_moves())

    def sort_tags(self):
        st_hechos = set()
        li_nuevo = []
        for tag in STANDARD_TAGS:
            for k, v in self.li_tags:
                if k == tag:
                    st_hechos.add(tag)
                    li_nuevo.append((k, v))
                    break
        li_nuevo.extend((k, v) for k, v in self.li_tags if k not in st_hechos)
        self.li_tags = li_nuevo

    def read_pgn(self, pgn):
        ok, game_tmp = pgn_game(pgn)
        self.restore(game_tmp.save())
        return self

    def add_seventags(self):
        for upper_tag in LI_BASIC_TAGS[:7]:
            if not self.has_tag(upper_tag):
                tag = upper_tag[0] + upper_tag[1:].lower()
                value = "????.??.??" if upper_tag == "DATE" else "?"
                self.set_tag(tag, value)
        self.order_tags()

    def pgn(self):
        self.check_tags()
        li = [f'[{k} "{v}"]\n' for k, v in self.li_tags]
        txt = "".join(li)
        txt += f"\n{self.pgn_base()}"
        return txt

    def pgn_tags(self):
        self.check_tags()
        return "\n".join([f'[{k} "{v}"]' for k, v in self.li_tags])

    def pgn_base_raw(self, movenum=None, translated=False):
        resp = ""
        if movenum is None:
            if self.first_comment:
                resp = "{%s} " % self.first_comment
            movenum = self.first_num_move()
        if self.starts_with_black:
            resp += "%d... " % movenum
            movenum += 1
            salta = 1
        else:
            salta = 0
        for n, move in enumerate(self.li_moves):
            if n % 2 == salta:
                resp += " %d." % movenum
                movenum += 1
            resp += f"{move.pgn_translated()} " if translated else f"{move.pgn_english()} "
        resp = resp.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").strip()
        while "  " in resp:
            resp = resp.replace("  ", " ")

        return resp

    def pgn_base(self, movenum=None, translated=False):
        resp = self.pgn_base_raw(movenum, translated=translated)
        li = []
        ln = len(resp)
        pos = 0
        while pos < ln:
            while resp[pos] == " ":
                pos += 1
            final = pos + 80
            txt = resp[pos:final]
            if txt[-1] == " ":
                txt = txt[:-1]
            elif final < ln:
                if resp[final] == " ":
                    final += 1
                else:
                    while final > pos and resp[final - 1] != " ":
                        final -= 1
                    if final > pos:
                        txt = resp[pos:final]
                    else:
                        final = pos + 80
            li.append(txt)
            pos = final
        if li:
            li[-1] = li[-1].strip()
            return "\n".join(li)
        else:
            return ""

    def pgn_translated(self, movenum=None, until_move=INFINITE):
        resp = "{%s} " % self.first_comment if self.first_comment else ""
        if movenum is None:
            movenum = self.first_num_move()
        if self.starts_with_black:
            resp += "%d..." % movenum
            movenum += 1
            salta = 1
        else:
            salta = 0
        for n, move in enumerate(self.li_moves):
            if n > until_move:
                break
            if n % 2 == salta:
                resp += "%d." % movenum
                movenum += 1

            pgn = move.pgn_translated()
            if n == len(self) - 1 and (self.termination == TERMINATION_MATE and not pgn.endswith("#")):
                pgn += "#"

            resp += f"{pgn} "

        return resp.strip()

    def pgn_html(self, movenum=None, until_move=INFINITE, with_figurines=True):
        li_resp = []
        if self.first_comment:
            li_resp.append("{%s}" % self.first_comment)
        if movenum is None:
            movenum = self.first_num_move()
        if self.starts_with_black:
            li_resp.append('<span style="color:navy">%d...</span>' % movenum)
            movenum += 1
            salta = 1
        else:
            salta = 0
        for n, move in enumerate(self.li_moves):
            if n > until_move:
                break
            if n % 2 == salta:
                x = '<span style="color:navy">%d.</span>' % movenum
                movenum += 1
            else:
                x = ""
            li_resp.append(x + (move.pgn_html(with_figurines)))
        return " ".join(li_resp)

    def pgn_base_raw_copy(self, movenum, hasta_jugada):
        resp = ""
        if movenum is None:
            movenum = self.first_num_move()
        if self.starts_with_black:
            resp += "%d... " % movenum
            movenum += 1
            salta = 1
        else:
            salta = 0
        for n, move in enumerate(self.li_moves[: hasta_jugada + 1]):
            if n % 2 == salta:
                resp += " %d." % movenum
                movenum += 1

            resp += f"{move.pgn_english()} "

        resp = resp.replace("\n", " ").replace("\r", " ").replace("  ", " ").strip()

        return resp

    def titulo(self, *litags, sep=" ∣ "):
        li = []
        for key in litags:
            if tag := self.get_tag(key):
                li.append(tag.replace("?", "").replace(".", ""))
        return sep.join(li)

    def window_title(self):
        white = ""
        black = ""
        event = ""
        site = ""
        date = ""
        result = ""
        for key, valor in self.li_tags:
            if key.upper() == "WHITE":
                white = valor
            elif key.upper() == "BLACK":
                black = valor
            elif key.upper() == "EVENT":
                event = valor
            elif key.upper() == "SITE":
                site = valor
            elif key.upper() == "DATE":
                date = valor.replace("?", "").replace(" ", "").strip(".")
            elif key.upper() == "RESULT":
                if valor in ("1-0", "0-1", "1/2-1/2"):
                    result = valor
        li = []
        if event:
            li.append(event)
        if site:
            li.append(site)
        if date:
            li.append(date)
        if result:
            li.append(result)
        titulo = f"{white}-{black}"
        if li:
            titulo += f' ({" - ".join(li)})'
        return titulo

    def first_num_move(self):
        return self.first_position.num_moves

    def move(self, num):
        total_moves = len(self.li_moves)
        if total_moves > 0:
            if num < 0:
                num = total_moves + num
            return self.li_moves[num] if 0 <= num < total_moves else self.li_moves[-1]
        return None

    def move_pos(self, move: Move.Move) -> int:
        """Devuelve la posición del movimiento en la lista, o -1 si no se encuentra."""
        try:
            return self.li_moves.index(move)
        except ValueError:
            return -1

    def verify(self):
        if self.pending_opening:
            self.assign_opening()
        if len(self.li_moves) == 0:
            return
        move: Move.Move = self.move(-1)
        if not move:
            return
        if move.position.is_finished():
            if move.is_check:
                self.set_termination(
                    TERMINATION_MATE,
                    (RESULT_WIN_WHITE if move.position_before.is_white else RESULT_WIN_BLACK),
                )
            else:
                self.set_termination(TERMINATION_DRAW_STALEMATE, RESULT_DRAW)

        elif self.si3repetidas():
            self.set_termination(TERMINATION_DRAW_REPETITION, RESULT_DRAW)

        elif self.last_position.mov_pawn_capt >= 100:
            self.set_termination(TERMINATION_DRAW_50, RESULT_DRAW)

        elif self.last_position.not_enough_material():
            self.set_termination(TERMINATION_DRAW_MATERIAL, RESULT_DRAW)

    def add_move(self, move):
        self.li_moves.append(move)
        self.verify()
        move.game = self

    def add_a1h8(self, a1h8):
        ok, error, move = Move.get_game_move(self, self.last_position, a1h8[:2], a1h8[2:4], a1h8[4:])
        if ok:
            self.add_move(move)

    def is_fen_initial(self):
        return self.first_position.fen() == FEN_INITIAL

    def num_moves(self):
        return len(self.li_moves)

    def __len__(self):
        return len(self.li_moves)

    def last_jg(self):
        return self.li_moves[-1] if self.li_moves else None

    def assign_other_game(self, other):
        txt = other.save()
        self.restore(txt)

    def clone(self, with_variations: bool = True):
        gclone = Game(self.first_position.copia())
        gclone.first_comment = self.first_comment
        gclone.result = self.result
        gclone.termination = self.termination
        gclone.li_tags = [(k, v) for k, v in self.li_tags]
        gclone.li_moves = []
        for move in self.li_moves:
            mclone = move.clone(gclone, with_variations=with_variations)
            gclone.li_moves.append(mclone)
        gclone.assign_opening()
        gclone.si3repetidas()
        gclone.set_result()
        return gclone

    def si3repetidas(self):
        n_jug = len(self.li_moves)
        if n_jug > 3:
            fenm2 = self.li_moves[n_jug - 1].fenm2()
            li_rep = [n_jug - 1]
            li_rep.extend(n for n in range(n_jug - 1) if self.li_moves[n].fenm2() == fenm2)
            if self.first_position.fenm2() == fenm2:
                li_rep.append(-1)

            if len(li_rep) >= 3:
                li_rep.sort()
                label = "".join("%d," % (j / 2 + 1 if j != -1 else 0,) for j in li_rep)
                label = label.strip(",")
                self.rotuloTablasRepeticion = label
                return True
        return False

    def read_pv(self, pv_bloque):
        return self.read_lipv(pv_bloque.split(" "))

    def read_xpv(self, xpv):
        return self.read_pv(FasterCode.xpv_pv(xpv))

    def read_lipv(self, lipv):
        position = self.last_position
        pv = []
        for mov in lipv:
            if (
                    len(mov) >= 4
                    and mov[0] in "abcdefgh"
                    and mov[1] in "12345678"
                    and mov[2] in "abcdefgh"
                    and mov[3] in "12345678"
            ):
                pv.append(mov)
            else:
                break

        is_white = self.is_white

        for mov in pv:
            from_sq = mov[:2]
            to_sq = mov[2:4]
            if len(mov) == 5:
                promotion = mov[4]
                if is_white:
                    promotion = promotion.upper()
            else:
                promotion = ""
            ok, mens, move = Move.get_game_move(self, position, from_sq, to_sq, promotion)
            if ok:
                self.li_moves.append(move)
                position = move.position
            is_white = not is_white
        return self

    def get_position(self, pos):
        n_jugadas = len(self.li_moves)
        return self.li_moves[pos].position if n_jugadas else self.first_position

    def last_fen(self):
        return self.last_position.fen()

    def is_white(self):
        return self.last_position.is_white

    def is_white_top(self):
        return self.first_position.is_white

    def is_draw(self):
        return self.result == RESULT_DRAW

    def set_first_comment(self, txt, replace):
        if replace or not self.first_comment:
            self.first_comment = txt
        elif txt not in self.first_comment:
            self.first_comment = f"{self.first_comment.strip()}\n{txt}"

    def is_finished(self):
        if self.termination != TERMINATION_UNKNOWN or self.result != RESULT_UNKNOWN:
            self.check_tag_result()
            return True
        if self.li_moves:
            move = self.li_moves[-1]
            if move.position.is_finished():
                if move.is_check:
                    self.result = RESULT_WIN_WHITE if move.position_before.is_white else RESULT_WIN_BLACK
                    self.termination = TERMINATION_MATE
                else:
                    self.result = RESULT_DRAW
                    self.termination = TERMINATION_DRAW_STALEMATE
                self.check_tag_result()
                return True
        return False

    def is_possible_add_moves(self):
        if self.li_moves:
            move = self.li_moves[-1]
            if move.position.is_finished():
                return False
        return True

    def check_tag_result(self):
        if not self.get_tag("RESULT"):
            self.set_tag("Result", self.result)

    def resultado(self):
        result_tag = self.get_tag("RESULT")
        if result_tag in (RESULT_WIN_WHITE, RESULT_WIN_BLACK, RESULT_DRAW):
            self.result = result_tag
        elif self.result in (RESULT_WIN_WHITE, RESULT_WIN_BLACK, RESULT_DRAW):
            self.set_tag("Result", self.result)
        return self.result

    def pv(self):
        return " ".join([move.movimiento() for move in self.li_moves])

    def xpv(self):
        resp = FasterCode.pv_xpv(self.pv())
        if not self.first_position.is_initial():
            resp = f"|{self.first_position.fen()}|{resp}"
        return resp

    def xpv_until_move(self, num_move):
        pv = " ".join([move.movimiento() for move in self.li_moves[: num_move + 1]])
        return FasterCode.pv_xpv(pv)

    def all_pv(self, pv_previo, with_variations):
        li_pvc = []
        if pv_previo:
            pv_previo += " "
        for move in self.li_moves:
            if with_variations != NONE and move.variations:
                is_w = move.is_white()
                if (
                        (with_variations == ALL)
                        or (is_w and with_variations == ONLY_WHITE)
                        or (not is_w and with_variations == ONLY_BLACK)
                ):
                    for variation in move.variations.li_variations:
                        li_pvc.extend(variation.all_pv(pv_previo.strip(), with_variations))
            pv_previo += f"{move.movimiento()} "
            li_pvc.append(pv_previo.strip())
        return li_pvc

    def all_comments(self, with_variations):
        dic = {}
        for move in self.li_moves:
            if with_variations != NONE and move.variations:
                is_w = move.is_white()
                if (
                        (with_variations == ALL)
                        or (is_w and with_variations == ONLY_WHITE)
                        or (not is_w and with_variations == ONLY_BLACK)
                ):
                    for variation in move.variations.li_variations:
                        if dicv := variation.all_comments(with_variations):
                            dic |= dicv
            if move.comment or move.li_nags:
                fenm2 = move.position.fenm2()
                d = {}
                if move.comment:
                    d["C"] = move.comment
                if move.li_nags:
                    d["N"] = move.li_nags
                dic[fenm2] = d
        if self.first_comment and self.li_moves:
            self._extracted_from_all_comments_(dic)
        return dic

    # TODO Rename this here and in `all_comments`
    def _extracted_from_all_comments_(self, dic):
        move = self.li_moves[0]
        fenm2 = move.position.fenm2()
        d = dic.get(fenm2, {})
        comment = self.first_comment
        if previo := d.get("C"):
            comment += f" {previo}"
        d["C"] = comment
        dic[fenm2] = d

    def lipv(self):
        return [move.movimiento() for move in self.li_moves]

    def pv_hasta(self, njug):
        return " ".join([move.movimiento() for move in self.li_moves[: njug + 1]])

    def remove_last_move(self, is_white):
        del self.li_moves[-1]
        self.set_unknown()
        ndel = 1
        if self.li_moves and self.li_moves[-1].position.is_white != is_white:
            del self.li_moves[-1]
            ndel += 1
        self.assign_opening()
        self.remove_result()
        return ndel

    def remove_only_last_movement(self):
        if self.li_moves:
            move = self.li_moves[-1]
            del self.li_moves[-1]
            self.set_unknown()
            self.assign_opening()
            self.remove_result()
            return move
        return None

    def remove_result(self):
        self.del_tag("TERMINATION")
        self.del_tag("RESULT")
        self.termination = TERMINATION_UNKNOWN
        self.result = RESULT_UNKNOWN

    def copia(self, until_move=None):
        p = Game()
        p.assign_other_game(self)
        if until_move is not None:
            if until_move == -1:
                p.li_moves = []
            elif until_move < (p.num_moves() - 1):
                p.li_moves = [move.clone(p) for move in p.li_moves[: until_move + 1]]
            if len(p) != len(self):
                p.set_unknown()
        return p

    def copy_until_move(self, seek_move):
        for pos, move in enumerate(self.li_moves):
            if seek_move == move:
                return self.copia(pos - 1)
        return self.copia(-1)

    def copy_from_move(self, from_move):
        if from_move == 0:
            cp = self.first_position
        else:
            cp = self.li_moves[from_move - 1].position
        p = Game(cp)
        p.li_moves = [move.clone(p) for move in self.li_moves[from_move:]]
        return p

    def resign(self, is_white):
        self.set_termination(TERMINATION_RESIGN, RESULT_WIN_BLACK if is_white else RESULT_WIN_WHITE)
        self.set_extend_tags()

    def remove_analysis(self):
        for move in self.li_moves:
            move.analysis = None

    def assign_opening(self):
        OpeningsStd.ap.assign_opening(self)
        if self.is_fen_initial():
            if self.pending_opening:
                self.del_tag("Opening")
                self.del_tag("ECO")
            else:
                self.set_tag("Opening", self.opening.tr_name)
                self.set_tag("ECO", self.opening.eco)

    def label_opening(self):
        return self.opening.tr_name if hasattr(self, "opening") and self.opening is not None else None

    def check_opening(self):
        if not hasattr(self, "opening") or self.pending_opening:
            self.assign_opening()

    def only_has_moves(self) -> bool:
        if self.first_comment:
            return False
        return all(move.only_has_move() for move in self.li_moves)

    def dic_labels(self):
        return dict(self.li_tags)

    def _label_won(self, nom_other):
        if nom_other:
            mensaje = _X(_("Congratulations you have won against %1."), nom_other)
        else:
            mensaje = _("Congratulations you have won.")
        if self.termination == TERMINATION_WIN_ON_TIME:
            beep = BEEP_WIN_PLAYER_TIME
        else:
            beep = BEEP_WIN_PLAYER
        return mensaje, beep

    def _label_lost(self, nom_other):
        if nom_other:
            mensaje = _X(_("Unfortunately you have lost against %1."), nom_other)
        else:
            mensaje = _("Unfortunately you have lost.")
        if self.termination == TERMINATION_WIN_ON_TIME:
            beep = BEEP_WIN_OPPONENT_TIME
        else:
            beep = BEEP_WIN_OPPONENT
        return mensaje, beep

    def label_result_player(self, player_side):
        nom_w = self.get_tag("White")
        nom_b = self.get_tag("Black")

        nom_other = nom_b if player_side == WHITE else nom_w

        mensaje = ""
        beep = None
        player_lost = False
        if (self.result == RESULT_WIN_WHITE and player_side == WHITE) or (
                self.result == RESULT_WIN_BLACK and player_side == BLACK
        ):
            mensaje, beep = self._label_won(nom_other)

        elif (self.result == RESULT_WIN_WHITE and player_side == BLACK) or (
                self.result == RESULT_WIN_BLACK and player_side == WHITE
        ):
            player_lost = True
            mensaje, beep = self._label_lost(nom_other)

        elif self.result == RESULT_DRAW:
            mensaje = _X(_("Draw against %1."), nom_other) if nom_other else _("Draw")
            beep = BEEP_DRAW
            if self.termination == TERMINATION_DRAW_REPETITION:
                beep = BEEP_DRAW_REPETITION
            elif self.termination == TERMINATION_DRAW_50:
                beep = BEEP_DRAW_50
            elif self.termination == TERMINATION_DRAW_MATERIAL:
                beep = BEEP_DRAW_MATERIAL

        if self.termination != TERMINATION_UNKNOWN:
            if self.termination == TERMINATION_WIN_ON_TIME and player_lost:
                label = _("Lost on time")
            else:
                label = self.label_termination()

            mensaje += f"\n\n{_('Result')}: {label}"

        return mensaje, beep, beep in (BEEP_WIN_PLAYER_TIME, BEEP_WIN_PLAYER)

    def label_termination(self):
        return {
            TERMINATION_MATE: _("Mate"),
            TERMINATION_DRAW_STALEMATE: _("Stalemate"),
            TERMINATION_DRAW_REPETITION: _("Draw by threefold repetition"),
            TERMINATION_DRAW_MATERIAL: _("Draw by insufficient material"),
            TERMINATION_DRAW_50: _("Draw by fifty-move rule"),
            TERMINATION_DRAW_AGREEMENT: _("Draw by agreement"),
            TERMINATION_RESIGN: _("Resignation"),
            TERMINATION_ADJUDICATION: _("Adjudication"),
            TERMINATION_WIN_ON_TIME: _("Won on time"),
            TERMINATION_UNKNOWN: _("Unknown"),
            TERMINATION_ENGINE_MALFUNCTION: _("Engine malfunction"),
        }.get(self.termination, "")

    def shrink(self, until_move: int):
        self.li_moves = self.li_moves[: until_move + 1]

    def copy_raw(self, xto):
        g = Game(self.first_position)
        if xto not in (None, -1):
            if pv := self.pv_hasta(xto):
                g.read_pv(pv)
        return g

    def skip_first(self):
        if len(self.li_moves) == 0:
            return
        move0 = self.li_moves[0]
        self.li_moves = self.li_moves[1:]
        self.first_position = move0.position
        fen_inicial = self.first_position.fen()
        self.set_tag("FEN", fen_inicial)

    def average_mstime_user(self, num):
        # solo se pregunta cuando le toca jugar al usuario
        is_white = self.last_position.is_white
        li = [move.time_ms for move in self.li_moves if move.is_white() == is_white and move.time_ms > 0]
        if len(li) > 0:
            li = li[-num:]
            return sum(li) / len(li)
        else:
            return 0

    def convert_variation_into_mainline(self, num_move, num_variation):
        game_last_moves = self.copy_from_move(num_move)  # Desde el movimiento hasta el final es la nueva variante
        move = self.li_moves[num_move]
        game_variation = move.variations.li_variations[num_variation]
        self.li_moves = self.li_moves[:num_move]
        for xmove in game_variation.li_moves:
            nv_move = xmove.clone(self)
            self.li_moves.append(nv_move)

        move0 = self.li_moves[num_move]
        move0.variations = Move.Variations(move0)
        for xnum, variation in enumerate(move.variations.li_variations):
            if xnum == num_variation:
                game_last_moves.li_moves[0].variations.li_variations = []
                move0.add_variation(game_last_moves)
            else:
                move0.add_variation(variation)

    def remove_info_moves(
            self,
            variations=True,
            ratings=True,
            comments=True,
            analysis=True,
            themes=True,
            time_ms=True,
            clock_ms=True,
    ):
        if comments:
            self.first_comment = ""
        for move in self.li_moves:
            if variations:
                move.del_variations()
            if ratings:
                move.del_nags()
            if comments:
                move.del_comment()
            if analysis:
                move.del_analysis()
            if themes:
                move.del_themes()
            if clock_ms:
                move.clock_ms = 0
            if time_ms:
                move.time_ms = 0

    def remove_moves(self, num_move, to_end):
        if to_end:
            self.li_moves = self.li_moves[:num_move]
            self.set_unknown()
        else:
            self.li_moves = self.li_moves[num_move + 1:]
            if self.li_moves:
                move: Move.Move = self.li_moves[0]
                self.first_position = move.position_before.copia()
        self.assign_opening()

    def has_analisis(self):
        return any(move.analysis for move in self.li_moves)

    def get_accuracy(self):
        njg_t = njg_w = njg_b = 0
        porc_t = porc_w = porc_b = 0.0

        for move in self.li_moves:
            if move.analysis:
                mrm, pos = move.analysis
                is_white = move.is_white()
                pts = mrm.li_rm[pos].centipawns_abs()
                pts0 = mrm.li_rm[0].centipawns_abs()
                lostp_abs = pts0 - pts

                porc = 100 - lostp_abs if lostp_abs < 100 else 0
                porc_t += porc

                njg_t += 1
                if is_white:
                    njg_w += 1
                    porc_w += porc
                else:
                    njg_b += 1
                    porc_b += porc

        porc_t = porc_t * 1.0 / njg_t if njg_t else 0
        porc_w = porc_w * 1.0 / njg_w if njg_w else 0
        porc_b = porc_b * 1.0 / njg_b if njg_b else 0

        return porc_t, porc_w, porc_b

    def add_accuracy_tags(self):
        def add(base, porc):
            if porc > 0:
                self.set_tag(f"{base}Accuracy", f"{porc:.02f}")
            else:
                self.del_tag(f"{base}Accuracy")

        porc_t, porc_w, porc_b = self.get_accuracy()
        add("White", porc_w)
        add("Black", porc_b)
        add("Total", porc_t)

    def has_comments(self):
        if self.first_comment:
            return True
        return any(move.comment for move in self.li_moves)

    def remove_bad_variations(self):
        for move in self.li_moves:
            move.remove_bad_variations()

    def refresh_tacticthemes(self, create: bool) -> None:
        if not create and self.get_tag(TACTICTHEMES):
            create = True

        if create:
            li = []
            for move in self.li_moves:
                if move.li_themes:
                    for theme in move.li_themes:
                        if theme not in li:
                            li.append(theme)
            tag = ",".join(li)
            self.set_tag(TACTICTHEMES, tag)

    def has_themes(self):
        return any(move.li_themes for move in self.li_moves)

    def assign_isbook_phases(self) -> None:
        ap = Opening.OpeningPol(999)
        max_misses = 4
        misses = 0

        # 1. Detect opening-book moves
        for move in self.li_moves:
            move.is_book = False
            if ap.check_human(move.position_before.fen(), move.from_sq, move.to_sq):
                move.is_book = True
                misses = 0
            else:
                misses += 1
                if misses >= max_misses:
                    break

        # 2. Assign phases
        last_phase = PHASE_NODEFINED

        for idx, move in enumerate(self.li_moves):
            if move.is_book:
                if last_phase > OPENING:
                    for prev in self.li_moves[:idx]:
                        prev.set_phase(OPENING)

                move.set_phase(OPENING)
                last_phase = OPENING
                continue
            last_phase = max(MIDDLEGAME, last_phase)
            phase = move.position_before.phase()
            last_phase = max(last_phase, phase)
            move.set_phase(last_phase)

    def calc_elo_color(self, is_white):
        nummoves = {OPENING: 0, MIDDLEGAME: 0, ENDGAME: 0}
        sumelos = {OPENING: 0, MIDDLEGAME: 0, ENDGAME: 0}
        factormoves = {OPENING: 0, MIDDLEGAME: 0, ENDGAME: 0}
        for move in self.li_moves:
            if move.analysis and move.has_alternatives():
                if move.is_white() != is_white:
                    continue
                std = move.phase
                move.calc_elo()
                elo_factor = move.factor_elo()
                nummoves[std] += 1
                sumelos[std] += move.elo * elo_factor
                factormoves[std] += elo_factor

                sume = 0
                numf = 0
                for std in (OPENING, MIDDLEGAME, ENDGAME):
                    sume += sumelos[std]
                    numf += factormoves[std]

                move.elo_avg = int(sume * 1.0 / numf) if numf else 0

        elos = {}
        for std in (OPENING, MIDDLEGAME, ENDGAME):
            sume = sumelos[std]
            numf = factormoves[std]
            elos[std] = int(sume * 1.0 / numf) if numf else 0
        sume = 0
        numf = 0
        for std in (OPENING, MIDDLEGAME, ENDGAME):
            sume += sumelos[std]
            numf += factormoves[std]

        elos[ALLGAME] = int(sume * 1.0 / numf) if numf else 0
        return elos

    def calc_elos(self):
        elos: dict[bool | None, dict[Any, Any]] = {
            is_white: self.calc_elo_color(is_white) for is_white in (True, False)
        }
        elos[None] = {}
        for std in (OPENING, MIDDLEGAME, ENDGAME, ALLGAME):
            elos[None][std] = int((elos[True][std] + elos[False][std]) / 2.0)

        return elos

    def import_pgn(self, pgn):
        import_pgn = PGNtoGame(pgn, self)
        return import_pgn.read()


def pv_san(fen, pv):
    p = Game(fen=fen)
    p.read_pv(pv)
    move = p.move(0)
    return move.pgn_translated()


def pv_pgn(fen, pv):
    p = Game(fen=fen)
    p.read_pv(pv)
    return p.pgn_translated()


def pv_game(fen, pv):
    g = Game(fen=fen)
    g.read_pv(pv)
    g.assign_opening()
    return g


def lipv_lipgn(lipv):
    FasterCode.set_init_fen()
    li_pgn = []
    for pv in lipv:
        info = FasterCode.move_expv(pv[:2], pv[2:4], pv[4:])
        li_pgn.append(info.san())
    return li_pgn


def pv_pgn_raw(fen, pv):
    p = Game(fen=fen)
    p.read_pv(pv)
    return p.pgn_base_raw()


def pgn_game(pgn):
    ptg = PGNtoGame(pgn)
    return ptg.read()


def fen_game(fen, variation):
    pgn = f'[FEN "{fen}"]\n\n{variation}'
    ok, p = pgn_game(pgn)
    return p


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

    def __init__(self, pgn: Union[str, bytes], game: Game | None = None):
        """Initialize a PGNtoGame instance with PGN content and an optional game object.
        This sets up the converter to populate or update the provided Game instance.

        The PGN input is stored for later parsing, and a new Game is created if none is supplied.
        This allows the same class to be used for both creating fresh games and enriching existing ones.

        Args:
            pgn: PGN content as a string or bytes to be parsed into game moves and metadata.
            game: Optional existing Game instance to populate; if omitted, a new Game is created.
        """
        self.pgn = pgn
        self.game = Game() if game is None else game

    def read(self):
        normalized_pgn: str = self._normalize_pgn(self.pgn)
        tokens: Optional[List[str]] = FasterCode.xparse_pgn(normalized_pgn)
        if not tokens:
            return False, self.game

        self._last_position: Position.Position = self.game.first_position
        self._active_move: Move.Move | None = None
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

        move: Move.Move = Move.Move(
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


def read_games(pgnfile):
    with Util.OpenCodec(pgnfile) as f:
        si_b_cab = True
        lineas = []
        nbytes = 0
        last_line = ""
        for linea in f:
            nbytes += len(linea)
            if si_b_cab:
                if linea and linea[0] != "[":
                    si_b_cab = False
            elif last_line == "" and linea.startswith("["):
                ln = linea.strip()
                if ln.endswith("]"):
                    ln = ln[:-1]
                    if ln.endswith('"') and ln.count('"') > 1:
                        ok, p = pgn_game("".join(lineas))
                        yield nbytes, p
                        lineas = []
                        si_b_cab = True
            lineas.append(linea)
            last_line = linea.strip()
        if lineas:
            ok, p = pgn_game("".join(lineas))
            yield nbytes, p


def game_without_variations(game: Game):
    return game.clone(with_variations=False)
