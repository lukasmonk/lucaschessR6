import FasterCode
from PySide6 import QtWidgets

import Code
from Code.Base import Game, Move
from Code.Base.Constantes import (
    BLUNDER,
    GOOD_MOVE,
    INACCURACY,
    MISTAKE,
    INTERESTING_MOVE,
    VERY_GOOD_MOVE,
)
from Code.Base.Constantes import ENDGAME, MIDDLEGAME, OPENING
from Code.Nags import Nags
from Code.QT import Colocacion, Columnas, Controles, Grid, ScreenUtils, QTDialogs
from Code.QT.QTDialogs import rondo_puntos


class GridSummary:
    (BEST, BRILLIANT, GOOD, OTHER_GOOD, INTERESTING, ACCEPTABLE,
     BAD, DUBIOUS, MISTAKES, BLUNDERS, OTHER, OPENING, NOT_ANALYZED) = range(13)

    def __init__(self, wowner, game: Game.Game):
        self.wowner = wowner

        self._game = game

        self.grid = None
        self._color_background_groups = ScreenUtils.qt_color(Code.alternate_color_tableview)

        self.key_var = "GRIDSUMMARY"
        dic_vars = self.read_vars()

        self.qwidget = QtWidgets.QWidget(self.wowner)
        self.chb_select_opening = Controles.CHB(self.qwidget, _("Opening"), dic_vars.get("select_opening", True))

        self.chb_select_middlegame = Controles.CHB(self.qwidget, _("Middlegame"),
                                                   dic_vars.get("select_middlegame", True))
        self.chb_select_endgame = Controles.CHB(self.qwidget, _("Endgame"), dic_vars.get("select_endgame", True))

        # self.lb_show = Controles.LB(self.qwidget, f'{_("Show")}')
        self.chb_show_empty = Controles.CHB(self.qwidget, _("Is empty"), dic_vars.get("show_empty", False))
        self.chb_show_percentage = Controles.CHB(self.qwidget, "%", dic_vars.get("show_percentage", True))
        self.chb_show_noanalysed = Controles.CHB(self.qwidget, _("Not analysed"), dic_vars.get("show_noanalysed", True))

        for chb in (self.chb_select_opening, self.chb_select_middlegame, self.chb_select_endgame,
                    self.chb_show_empty, self.chb_show_percentage, self.chb_show_noanalysed):
            chb.capture_changes(self.reset)

        self.li_data = self.gen_data(dic_vars)

    def read_vars(self):
        return Code.configuration.read_variables(self.key_var)

    def save_vars(self):
        dic_vars = {
            "select_opening": self.chb_select_opening.isChecked(),
            "select_middlegame": self.chb_select_middlegame.isChecked(),
            "select_endgame": self.chb_select_endgame.isChecked(),
            "show_empty": self.chb_show_empty.isChecked(),
            "show_percentage": self.chb_show_percentage.isChecked(),
            "show_noanalysed": self.chb_show_noanalysed.isChecked(),
        }
        Code.configuration.write_variables(self.key_var, dic_vars)
        return dic_vars

    def get_widget(self):
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("MOVETYPE", _("Move type"), 200)
        o_columns.nueva("WHITE", _("White"), 80, align_center=True)
        o_columns.nueva("BLACK", _("Black"), 80, align_center=True)
        o_columns.nueva("TOTAL", _("Total"), 80, align_center=True)
        o_columns.nueva("NAG", "", 30, align_center=True)
        o_columns.nueva("WHITE%", "% " + _("White"), 80, align_center=True)
        o_columns.nueva("BLACK%", "% " + _("Black"), 80, align_center=True)
        o_columns.nueva("TOTAL%", "% " + _("Total"), 80, align_center=True)
        self.grid = Grid.Grid(self.wowner, o_columns, complete_row_select=False, xid="Summary",
                              is_column_header_movable=False, alternate=False)
        self.wowner.register_grid(self.grid)

        ly = Colocacion.H()
        ly.control(self.chb_select_opening).control(self.chb_select_middlegame).control(self.chb_select_endgame)
        ly.relleno()
        ly.control(self.chb_show_percentage).control(self.chb_show_noanalysed).control(self.chb_show_empty)

        layout = Colocacion.V().control(self.grid).otro(ly)
        self.qwidget.setLayout(layout)
        return self.qwidget

    def ancho_grid(self):
        return self.grid.width_columns_displayables()

    def gen_data(self, dic_vars) -> list:

        st_phases = set()
        if dic_vars.get("select_opening"):
            st_phases.add(OPENING)
        if dic_vars.get("select_middlegame"):
            st_phases.add(MIDDLEGAME)
        if dic_vars.get("select_endgame"):
            st_phases.add(ENDGAME)

        show_empty = dic_vars.get("show_empty")
        show_noanalysed = dic_vars.get("show_noanalysed")

        def reg(only_num_moves=False) -> dict:
            if only_num_moves:
                return {True: 0, False: 0}
            else:
                return {True: {"POS": 0, "MOVES": []}, False: {"POS": 0, "MOVES": []}}

        group_moves_best = reg(True)
        moves_brilliant = reg(False)
        moves_good = reg(False)
        moves_good_no = reg(False)
        moves_interestings = reg(False)

        moves_acceptable = reg(False)

        group_moves_bad = reg(True)
        moves_inaccuracies = reg(False)
        moves_mistakes = reg(False)
        moves_blunders = reg(False)

        group_moves_other = reg(True)
        moves_opening = reg(False)
        moves_noanalyzed = reg(False)

        nmoves_analyzed = reg(True)

        move: Move.Move

        for move in self._game.li_moves:
            is_white = move.is_white()
            if move.analysis:

                move.ta_general = nmoves_analyzed[True] + nmoves_analyzed[False]
                move.ta_white = nmoves_analyzed[True]
                move.ta_black = nmoves_analyzed[False]

                nmoves_analyzed[is_white] += 1

                # Hay que controlarlo aqquí para que se actualice la posicion
                if move.phase not in st_phases:
                    continue

                mrm, pos = move.analysis
                rm = mrm.li_rm[pos]
                if not hasattr(mrm, "dic_depth") or len(mrm.dic_depth) == 0:
                    # Generación de gráficos sin un análisis previo con su depth
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

                # nag_move determina el simbolo mostrado con nag
                # nag_color determina a que grupo pertenece
                # Caso principal nag_move=NO_RATING, nag_color=BLUE

                move.nag_color = nag_move, nag_color

                if nag_move == VERY_GOOD_MOVE:
                    moves_brilliant[is_white]["MOVES"].append(move)

                elif nag_color == GOOD_MOVE:
                    if nag_move == GOOD_MOVE:
                        moves_good[is_white]["MOVES"].append(move)
                    else:
                        moves_good_no[is_white]["MOVES"].append(move)

                elif nag_move == INTERESTING_MOVE:
                    moves_interestings[is_white]["MOVES"].append(move)

                elif nag_color == MISTAKE:
                    moves_mistakes[is_white]["MOVES"].append(move)

                elif nag_color == BLUNDER:
                    moves_blunders[is_white]["MOVES"].append(move)

                elif nag_color == INACCURACY:
                    moves_inaccuracies[is_white]["MOVES"].append(move)

                else:
                    moves_acceptable[is_white]["MOVES"].append(move)

            else:
                if move.is_book_move():
                    moves_opening[is_white]["MOVES"].append(move)
                else:
                    moves_noanalyzed[is_white]["MOVES"].append(move)

        for moves in (moves_brilliant, moves_good, moves_interestings, moves_good_no, moves_acceptable):
            group_moves_best[True] += len(moves[True]["MOVES"])
            group_moves_best[False] += len(moves[False]["MOVES"])

        for moves in (moves_blunders, moves_inaccuracies, moves_mistakes):
            group_moves_bad[True] += len(moves[True]["MOVES"])
            group_moves_bad[False] += len(moves[False]["MOVES"])

        for moves in (moves_opening, moves_noanalyzed):
            group_moves_other[True] += len(moves[True]["MOVES"])
            group_moves_other[False] += len(moves[False]["MOVES"])

        li_data = []

        def add_row(data, movetype, nag="", is_group=False, is_elem=True, show_porc=True, num_nag=None):
            white = len(data[True]["MOVES"]) if is_elem else data[True]
            black = len(data[False]["MOVES"]) if is_elem else data[False]
            total = white + black
            whitep = white / nmoves_analyzed[True] if white else 0
            blackp = black / nmoves_analyzed[False] if black else 0
            totalp = total / (nmoves_analyzed[True] + nmoves_analyzed[False]) if total else 0
            if total == 0 and not show_empty:
                return

            def set_num_col(value, dec):
                return f"{int(value)}" if dec == 0 else f"{value * 100.0:0.01f}%"

            li_data.append({
                "data": data,
                "is_group": is_group,
                "qcolor": Nags.nag_qcolor(num_nag) if num_nag else None,
                "MOVETYPE": movetype,
                "WHITE": set_num_col(white, 0),
                "BLACK": set_num_col(black, 0),
                "TOTAL": set_num_col(total, 0),
                "NAG": nag,
                "WHITE%": set_num_col(whitep, 2) if show_porc else "",
                "BLACK%": set_num_col(blackp, 2) if show_porc else "",
                "TOTAL%": set_num_col(totalp, 2) if show_porc else "",
            })

        add_row(group_moves_best, _("Good moves"), is_group=True, is_elem=False)
        add_row(moves_brilliant, _("Brilliant moves"), nag="!!", num_nag=Nags.NAG_3)
        add_row(moves_good, _("Best moves"), nag="!", num_nag=Nags.NAG_1)
        add_row(moves_good_no, _("Other best moves"), num_nag=Nags.NAG_1)
        add_row(moves_interestings, _("Interesting moves"), nag="!?", num_nag=Nags.NAG_5)
        add_row(moves_acceptable, _("Acceptable moves"))

        add_row(group_moves_bad, _("Bad moves"), is_group=True, is_elem=False)
        add_row(moves_inaccuracies, _("Dubious moves"), nag="?!", num_nag=Nags.NAG_6)
        add_row(moves_mistakes, _("Mistakes"), nag="?", num_nag=Nags.NAG_2)
        add_row(moves_blunders, _("Blunders"), nag="??", num_nag=Nags.NAG_4)

        add_row(nmoves_analyzed, _("Total"), is_group=True, is_elem=False)

        if show_noanalysed:
            add_row(group_moves_other, _("Not analysed"), is_group=True, is_elem=False, show_porc=False)
            add_row(moves_opening, _("Opening"), show_porc=False)
            add_row(moves_noanalyzed, _("Not analysed"), show_porc=False)

        return li_data

    def grid_left_button(self, row, obj_column):
        key_col = obj_column.key
        if key_col not in ("WHITE", "BLACK"):
            return

        dic_row: dict = self.li_data[row]
        data = dic_row["data"][key_col == "WHITE"]
        if isinstance(data, int):
            return
        moves = data["MOVES"]
        nmoves = len(moves)
        if nmoves == 0:
            return
        pos = data["POS"]
        if pos >= nmoves:
            pos = 0
        move: Move.Move = moves[pos]
        data["POS"] = pos + 1
        row = move.ta_general
        self.wowner.grid_all.goto(row, 0)
        if move.is_white():
            row = move.ta_white
            if row:
                self.wowner.grid_b.goto(row-1, 0)
            self.wowner.grid_w.goto(row, 0)
        else:
            row = move.ta_black
            if row:
                self.wowner.grid_w.goto(row-1, 0)
            self.wowner.grid_b.goto(row, 0)

    def grid_right_button(self, row, obj_column, modif):
        key_col = obj_column.key
        if key_col not in ("WHITE", "BLACK"):
            return

        dic_row: dict = self.li_data[row]
        data = dic_row["data"][key_col == "WHITE"]
        if isinstance(data, int):
            return
        moves = data["MOVES"]
        nmoves = len(moves)
        if nmoves == 0:
            return

        menu = QTDialogs.LCMenu(self.wowner)
        rp = QTDialogs.rondo_puntos()
        for pos, move in enumerate(moves):
            menu.opcion((pos, move), move.base_pgn_with_number(), rp.otro())

        resp = menu.lanza()
        if resp is None:
            return
        pos, move = resp
        data["POS"] = pos + 1
        if move.is_white():
            row = move.ta_white
            if row:
                self.wowner.grid_b.goto(row-1, 0)
            self.wowner.grid_w.goto(row, 0)
        else:
            row = move.ta_black
            if row:
                self.wowner.grid_w.goto(row-1, 0)
            self.wowner.grid_b.goto(row, 0)
        row = move.ta_general
        self.wowner.grid_all.goto(row, 0)





    def grid_doble_click(self, row, obj_column):
        pass

    def grid_tecla_control(self, k):
        pass

    def grid_color_texto(self, row, _obj_column):
        dic_row: dict = self.li_data[row]
        return dic_row["qcolor"]

    def grid_color_fondo(self, row, _obj_column):
        dic_row: dict = self.li_data[row]
        return self._color_background_groups if dic_row["is_group"] else None

    @staticmethod
    def grid_bold(_row, _column):
        return True
        # dic_row: dict = self.li_data[row]
        # return dic_row["is_group"]

    def grid_alineacion(self, row, obj_column):
        if obj_column.key == "MOVETYPE":
            dic_row: dict = self.li_data[row]
            if not dic_row["is_group"]:
                return "d"
        return None

    def grid_num_datos(self):
        return len(self.li_data)

    def grid_dato(self, row, obj_column):
        dic_row = self.li_data[row]
        return dic_row[obj_column.key]

    def reset(self):
        dic_vars = self.save_vars()
        self.li_data = self.gen_data(dic_vars)
        o_columns = self.grid.columnas()
        show_percentage = dic_vars["show_percentage"]
        for o_column in o_columns.li_columns:
            if "%" in o_column.key:
                o_column.must_show = show_percentage
        self.grid.reread_columns()
        self.grid.refresh()
