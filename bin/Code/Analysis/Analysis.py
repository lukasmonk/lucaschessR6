from typing import List, Tuple

import Code
from Code.Analysis import AnalysisIndexes, WindowAnalysis
from Code.Base import Game, Move
from Code.Base.Constantes import TOP_RIGHT
from Code.Engines import EngineResponse, EngineManagerAnalysis
from Code.QT import QTMessages


class ControlAnalysis:
    wmu: None
    rm: EngineResponse.EngineResponse
    game: Game.Game
    mrm: EngineResponse.MultiEngineResponse
    list_rm_name: List[Tuple[EngineResponse.EngineResponse, str, int]]

    def __init__(self, tb_analysis, mrm, pos_selected, number, xengine):

        self.tb_analysis = tb_analysis
        self.number = number
        self.xengine = xengine
        self.with_figurines = tb_analysis.configuration.x_pgn_withfigurines

        self.mrm = mrm
        self.pos_selected = pos_selected

        self.pos_rm_active = pos_selected
        self.pos_mov_active = 0

        self.move = tb_analysis.move

        self.is_active = False

        self.list_rm_name = self.do_lirm()  # rm, name, centpawns

    def time_engine(self):
        return self.mrm.name.strip()

    def time_label(self):
        if self.mrm.max_time:
            t = f"{float(self.mrm.max_time) / 1000.0:0.2f}"
            t = t.rstrip("0")
            if t[-1] == ".":
                t = t[:-1]
            return f"{_('Second(s)')}: {t}"
        elif self.mrm.max_depth:
            return "%s: %d" % (_("Depth"), self.mrm.max_depth)
        else:
            return ""

    def do_lirm(self) -> List[Tuple[EngineResponse.EngineResponse, str, int]]:
        li = []
        pb = self.move.position_before
        for rm in self.mrm.li_rm:
            pv1 = rm.pv.split(" ")[0]
            from_sq = pv1[:2]
            to_sq = pv1[2:4]
            promotion = pv1[4].lower() if len(pv1) == 5 else ""

            name = (
                pb.pgn(from_sq, to_sq, promotion)
                if self.with_figurines
                else pb.pgn_translated(from_sq, to_sq, promotion)
            )
            if name:
                if txt := rm.abbrev_text_base():
                    name += f"({txt})"
                li.append((rm, name, rm.centipawns_abs()))

        return li

    def set_wmu(self, wmu):
        self.wmu = wmu
        self.is_active = True

    def desactiva(self):
        self.wmu.hide()
        self.is_active = False

    def is_selected(self, pos_rm):
        return pos_rm == self.pos_selected

    def set_pos_rm_active(self, pos_rm):
        self.pos_rm_active = min(pos_rm, len(self.list_rm_name) - 1)
        self.rm = self.list_rm_name[self.pos_rm_active][0]
        self.game = Game.Game(self.move.position_before)
        self.game.read_pv(self.rm.pv)
        self.game.is_finished()
        self.pos_mov_active = 0

    def pgn_active(self):
        num_mov = self.game.first_num_move()
        style_number = f"color:{Code.dic_colors['PGN_NUMBER']}; font-weight: bold;"
        style_select = f"color:{Code.dic_colors['PGN_SELECT']};font-weight: bold;"
        style_moves = f"color:{Code.dic_colors['PGN_MOVES']};"
        li_pgn = []
        if self.game.starts_with_black:
            li_pgn.append('<span style="%s">%d...</span>' % (style_number, num_mov))
            num_mov += 1
            salta = 1
        else:
            salta = 0
        for n, move in enumerate(self.game.li_moves):
            if n % 2 == salta:
                li_pgn.append('<span style="%s">%d.</span>' % (style_number, num_mov))
                num_mov += 1

            xp = move.pgn_html(self.with_figurines)
            if n == self.pos_mov_active:
                xp = f'<span style="{style_select}">{xp}</span>'
            else:
                xp = f'<span style="{style_moves}">{xp}</span>'

            li_pgn.append(f'<a href="{n:d}" style="text-decoration:none;">{xp}</a> ')

        return " ".join(li_pgn)

    def score_active(self):
        rm = self.list_rm_name[self.pos_rm_active][0]
        return rm.texto()

    def score_active_depth(self):
        rm = self.list_rm_name[self.pos_rm_active][0]
        return f"{rm.texto()}   -   {_('Depth')}: {rm.depth:d}"

    def complexity(self):
        return AnalysisIndexes.get_complexity(self.move.position_before, self.mrm)

    def winprobability(self):
        return AnalysisIndexes.get_winprobability(self.move.position_before, self.mrm)

    def narrowness(self):
        return AnalysisIndexes.get_narrowness(self.move.position_before, self.mrm)

    def efficientmobility(self):
        return AnalysisIndexes.get_efficientmobility(self.move.position_before, self.mrm)

    def piecesactivity(self):
        return AnalysisIndexes.get_piecesactivity(self.move.position_before, self.mrm)

    def activate_position(self):
        n_movs = len(self.game)
        if self.pos_mov_active >= n_movs:
            self.pos_mov_active = n_movs - 1
        if self.pos_mov_active < 0:
            self.pos_mov_active = -1
            return self.game.move(0).position_before, None, None
        else:
            move_active = self.game.move(self.pos_mov_active)
            return move_active.position, move_active.from_sq, move_active.to_sq

    def get_game(self):
        game_original: Game.Game = self.move.game
        if self.move.movimiento():
            game_send = game_original.copy_until_move(self.move)
            # if len(game_send) == 0:
            #     game_send = game_original.copia()
        else:
            game_send = game_original.copia()
        if self.pos_mov_active > -1:
            for nmove in range(self.pos_mov_active + 1):
                move = self.game.move(nmove)
                move_send = move.clone(game_send)
                game_send.add_move(move_send)

        return game_send

    def change_mov_active(self, accion):
        if accion == "forward":
            self.pos_mov_active += 1
        elif accion == "back":
            self.pos_mov_active -= 1
        elif accion == "to_beginning":
            self.pos_mov_active = -1
        elif accion == "to_end":
            self.pos_mov_active = len(self.game) - 1

    def set_pos_mov_active(self, pos):
        if 0 <= pos < len(self.game):
            self.pos_mov_active = pos

    def is_final_position(self):
        return self.pos_mov_active >= len(self.game) - 1

    def fen_active(self):
        move = self.game.move(max(self.pos_mov_active, 0))
        return move.position.fen()

    # def external_analysis(self, wowner, is_white):
    #     move = self.game.move(max(self.pos_mov_active, 0))
    #     pts = self.score_active()
    #     AnalisisVariations(wowner, self.xengine, move, is_white, pts)

    def save_base(self, game, rm, is_complete):
        name = self.time_engine()
        vtime = self.time_label()
        variation = game.copia() if is_complete else game.copia(0)

        if len(variation) > 0:
            comment = f"{rm.abbrev_text()} {name} {vtime}"
            variation.move(0).set_comment(comment.strip())
        self.move.add_variation(variation)

    def put_view_manager(self):
        if self.tb_analysis.procesador.manager:
            self.tb_analysis.procesador.manager.put_view()


class CreateAnalysis:
    def __init__(self, procesador, move, pos_move):

        self.procesador = procesador
        self.configuration = Code.configuration
        self.move = move
        self.pos_move = pos_move  # Para mostrar el pgn con los numeros correctos
        self.li_tabs_analysis = []

    def create_initial_show(self, main_window, xengine: EngineManagerAnalysis.EngineManagerAnalysis):
        move: Move.Move = self.move
        if move.analysis is None:
            with QTMessages.WaitingMessage(
                main_window, _("Analyzing the move...."), physical_pos=TOP_RIGHT, with_cancel=True
            ) as me:
                game = move.game
                mrm, pos = xengine.analyze_move(game, game.move_pos(move), me.dispatcher_analysis)
                if pos >= 0:
                    move.analysis = mrm, pos
                if pos < 0:
                    return None
        else:
            mrm, pos = move.analysis

        tab_analysis = ControlAnalysis(self, mrm, pos, 0, xengine)
        self.li_tabs_analysis.append(tab_analysis)
        return tab_analysis

    def create_show(self, main_window, alm):
        if alm.engine == "default":
            xengine = Code.procesador.analyzer_clone(alm.vtime, alm.depth, alm.nodes, alm.multiPV)

        else:
            xengine = None
            busca = alm.engine[1:] if alm.engine.startswith("*") else alm.engine
            for tab_analysis in self.li_tabs_analysis:
                if tab_analysis.xengine.key == busca:
                    xengine = tab_analysis.xengine
                    xengine.set_multipv_var(alm.multiPV)
                    break
            if xengine is None:
                conf_engine = self.configuration.engines.search(alm.engine)
                conf_engine.set_multipv_var(alm.multiPV)
                xengine = self.procesador.create_manager_engine(conf_engine, alm.vtime, alm.depth, has_multipv=True)

        with QTMessages.WaitingMessage(main_window, _("Analyzing the move...."), physical_pos=TOP_RIGHT):
            mrm, pos = xengine.analysis_move(self.move, alm.vtime, alm.depth)
            xengine.finalize()

        tab_analysis = ControlAnalysis(self, mrm, pos, self.li_tabs_analysis[-1].number + 1, xengine)
        self.li_tabs_analysis.append(tab_analysis)
        return tab_analysis


def show_analysis(
    manager_analyzer: EngineManagerAnalysis.EngineManagerAnalysis,
    move: Move.Move,
    is_white: bool,
    pos_move: int,
    main_window=None,
    must_save: bool = True,
    subanalysis: bool = False,
):
    main_window = Code.procesador.main_window if main_window is None else main_window

    ma = CreateAnalysis(Code.procesador, move, pos_move)
    if manager_analyzer is None:
        manager_analyzer = Code.procesador.get_manager_analyzer()
    tab_analysis0 = ma.create_initial_show(main_window, manager_analyzer)
    move = ma.move
    if not tab_analysis0:
        return
    wa = WindowAnalysis.WAnalisis(ma, main_window, is_white, must_save, tab_analysis0, subanalysis=subanalysis)
    if subanalysis:
        wa.show()
    else:
        wa.exec()
        busca = True
        for uno in ma.li_tabs_analysis:
            if busca and uno.is_active:
                move.analysis = uno.mrm, uno.pos_selected

                busca = False
            xengine = uno.xengine
            if not manager_analyzer or xengine.engine.key != manager_analyzer.engine.key:
                xengine.finalize()
