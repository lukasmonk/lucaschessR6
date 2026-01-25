from types import SimpleNamespace

from PySide6 import QtWidgets

import Code
from Code.Analysis import WindowAnalysisConfig
from Code.Base.Constantes import (
    ALL_VARIATIONS,
    BETTER_VARIATIONS,
    BLUNDER,
    HIGHEST_VARIATIONS,
    INACCURACY,
    INACCURACY_MISTAKE,
    INACCURACY_MISTAKE_BLUNDER,
    MISTAKE,
    MISTAKE_BLUNDER,
)
from Code.Books import Books
from Code.Engines import Engines
from Code.Engines import Priorities
from Code.QT import FormLayout, Iconos, QTMessages, QTUtils
from Code.Themes import AssignThemes
from Code.Z import Util

SEPARADOR = FormLayout.separador


def read_dic_params():
    configuration = Code.configuration
    file = configuration.paths.file_param_analysis()
    dic = Util.restore_pickle(file) or {}
    return SimpleNamespace(
        engine=dic.get("engine", configuration.x_tutor_clave),
        vtime=dic.get("vtime", configuration.x_tutor_mstime),
        depth=dic.get("depth", configuration.x_tutor_depth),
        nodes=dic.get("nodes", 0),
        kblunders_condition=dic.get("kblunders_condition", MISTAKE_BLUNDER),
        from_last_move=dic.get("from_last_move", False),
        multiPV=dic.get("multiPV", "PD"),
        priority=dic.get("priority", Priorities.priorities.normal),
        book_name=dic.get("book_name", None),
        standard_openings=dic.get("standard_openings", False),
        accuracy_tags=dic.get("accuracy_tags", False),
        analyze_variations=dic.get("analyze_variations", False),
        include_variations=dic.get("include_variations", True),
        what_variations=dic.get("what_variations", ALL_VARIATIONS),
        include_played=dic.get("include_played", True),
        limit_include_variations=dic.get("limit_include_variations", 0),
        info_variation=dic.get("info_variation", True),
        one_move_variation=dic.get("one_move_variation", False),
        delete_previous=dic.get("delete_previous", True),
        si_pdt=dic.get("si_pdt", False),
        show_graphs=dic.get("show_graphs", True),
        white=dic.get("white", True),
        black=dic.get("black", True),
        li_players=dic.get("li_players", None),
        workers=dic.get("workers", 1),
        themes_tags=dic.get("themes_tags", False),
        themes_assign=dic.get("themes_assign", False),
        themes_reset=dic.get("themes_reset", False),
    )


def save_dic_params(dic):
    configuration = Code.configuration
    file = configuration.paths.file_param_analysis()
    dic1 = Util.restore_pickle(file, {})
    dic1.update(dic)
    Util.save_pickle(file, dic1)


def form_blunders_brilliancies(analysis_params, configuration):
    li_blunders = [SEPARADOR]

    li_types = [
        (
            f"{_('Dubious move')} (⁈)  + {_('Mistake')} (?) + {_('Blunder')} (⁇)",
            INACCURACY_MISTAKE_BLUNDER,
        ),
        (f"{_('Dubious move')} (⁈) + {_('Mistake')} (?)", INACCURACY_MISTAKE),
        (f"{_('Mistake')} (?) + {_('Blunder')} (⁇)", MISTAKE_BLUNDER),
        (f"{_('Dubious move')} (⁈)", INACCURACY),
        (f"{_('Mistake')} (?)", MISTAKE),
        (f"{_('Blunder')} (⁇)", BLUNDER),
    ]
    condition = FormLayout.Combobox(_("Condition"), li_types)
    li_blunders.append((condition, analysis_params.kblunders_condition))

    li_blunders.append(SEPARADOR)

    def file_next(base, ext):
        return Util.file_next(configuration.paths.folder_personal_trainings(), base, ext)

    path_pgn = file_next("Blunders", "pgn")

    li_blunders.append((None, _("Generate a training file with these moves")))

    config = FormLayout.Editbox(_("Tactics name"), rx="[^\\:/|?*^%><()]*")
    li_blunders.append((config, ""))

    config = FormLayout.Fichero(
        _("PGN Format"),
        f'{_("PGN Format")} (*.pgn)',
        True,
        minimum_width=280,
        file_default=path_pgn,
    )
    li_blunders.append((config, ""))

    li_blunders.append((f"{_('Also add complete game to PGN')}:", False))

    li_blunders.append(SEPARADOR)

    eti = f'"{_("Find best move")}"'
    li_blunders.append((f"{_X(_('Add to the training %1 with the name'), eti)}:", ""))

    li_brilliancies = [SEPARADOR]

    path_fns = file_next("Brilliancies", "fns")
    path_pgn = file_next("Brilliancies", "pgn")

    li_brilliancies.append((None, _("Generate a training file with these moves")))

    config = FormLayout.Fichero(
        _("List of FENs"),
        f'{_("List of FENs")} (*.fns)',
        True,
        minimum_width=280,
        file_default=path_fns,
    )
    li_brilliancies.append((config, ""))

    config = FormLayout.Fichero(
        _("PGN Format"),
        f'{_("PGN Format")} (*.pgn)',
        True,
        minimum_width=280,
        file_default=path_pgn,
    )
    li_brilliancies.append((config, ""))

    li_brilliancies.append((f"{_('Also add complete game to PGN')}:", False))

    li_brilliancies.append(SEPARADOR)

    eti = f'"{_("Find best move")}"'
    li_brilliancies.append((f"{_X(_('Add to the training %1 with the name'), eti)}:", ""))

    return li_blunders, li_brilliancies


def form_variations(analysis_params):
    li_var = [
        SEPARADOR,
        (f"{_('Also analyze variations')}:", analysis_params.analyze_variations),
        SEPARADOR,
        (f"<big><b>{_('Convert analyses into variations')}:", analysis_params.include_variations),
    ]

    li = [
        (_("All variations"), ALL_VARIATIONS),
        (_("The one(s) with the highest score"), HIGHEST_VARIATIONS),
        (_("All the ones with better score than the one played"), BETTER_VARIATIONS),
    ]
    what_variations = FormLayout.Combobox(_("What variations?"), li)
    li_var.append((what_variations, analysis_params.what_variations))
    li_var.append((f"{_('Include move played')}:", analysis_params.include_played))
    li_var.append(SEPARADOR)

    li_var.append(
        (
            FormLayout.Spinbox(_("Maximum centipawns lost"), 0, 1000, 60),
            analysis_params.limit_include_variations,
        )
    )
    li_var.append(SEPARADOR)

    li_var.append((f"{_('Include info about engine')}:", analysis_params.info_variation))
    li_var.append(SEPARADOR)

    li_var.append(
        (
            f'{_("Format")} {_("Score")}/{_("Depth")}/{_("Time")}:',
            analysis_params.si_pdt,
        )
    )
    li_var.append(SEPARADOR)

    li_var.append((f"{_('Only one move of each variation')}:", analysis_params.one_move_variation))
    return li_var


def form_themes(alm):
    return [
        SEPARADOR,
        (f"{_('Automatic assignment')}:", alm.themes_assign),
        SEPARADOR,
        SEPARADOR,
        (None, f"{_('In case automatic assignment is activated')}:"),
        SEPARADOR,
        (
            f"{_('Add themes tag to the game')} (TacticThemes):",
            alm.themes_tags,
        ),
        SEPARADOR,
        (f"{_('Pre-delete the following themes?')}:", alm.themes_reset),
        (None, f"@|{AssignThemes.AssignThemes().txt_all_themes()}"),
        SEPARADOR,
    ]


def form_engine(analysis_params, all_engines):
    li_engine = [SEPARADOR]

    if all_engines:
        li = Code.configuration.engines.formlayout_combo_analyzer(False)
    else:
        li = Code.configuration.engines.formlayout_combo_analyzer(True)
        li[0] = analysis_params.engine
    li_engine.append((f"{_('Engine')}:", li))
    li_engine.append(SEPARADOR)

    # # Time
    config = FormLayout.Editbox(_("Duration of engine analysis (secs)"), 40, tipo=float)
    li_engine.append((config, analysis_params.vtime / 1000.0))

    tooltip = _("If time and depth are given, the depth is attempted and the time becomes a maximum.")
    config = FormLayout.Editbox(f'{_("Depth")} (0={_("Disable")})', 40, tipo=int, tooltip=tooltip)
    li_engine.append((config, analysis_params.depth))

    tooltip = _("If time and nodes are given, the nodes is attempted and the time becomes a maximum.")
    config = FormLayout.Editbox(f'{_("Fixed nodes")} (0={_("Disable")})', 80, tipo=int, tooltip=tooltip)
    li_engine.append((config, analysis_params.nodes))

    # MultiPV
    li_engine.append(SEPARADOR)
    li = Engines.list_depths_to_cb()
    config = FormLayout.Combobox(_("Number of variations evaluated by the engine (MultiPV)"), li)
    li_engine.append((config, analysis_params.multiPV))

    # Priority
    config = FormLayout.Combobox(_("Process priority"), Priorities.priorities.combo())
    li_engine.append((config, analysis_params.priority))
    li_engine.append(SEPARADOR)

    return li_engine


def analysis_parameters(parent, extended_mode, all_engines=False):
    analysis_params = read_dic_params()

    configuration = Code.configuration

    # Datos
    li_engine = form_engine(analysis_params, all_engines)

    # Completo
    if extended_mode:
        li_gen = [SEPARADOR]

        li_j = [
            (_("White"), "WHITE"),
            (_("Black"), "BLACK"),
            (_("White & Black"), "BOTH"),
        ]
        config = FormLayout.Combobox(_("Analyze color"), li_j)
        if analysis_params.white and analysis_params.black:
            color = "BOTH"
        elif analysis_params.black:
            color = "BLACK"
        elif analysis_params.white:
            color = "WHITE"
        else:
            color = "BOTH"
        li_gen.append((config, color))

        config = FormLayout.Editbox(
            f"<div align=\"right\">{_('Moves')}<br>{_('By example:')} -5,8-12,14,19-",
            rx=r"[0-9,\-]*",
        )
        li_gen.append((config, ""))

        list_books = Books.ListBooks()
        li = [("--", None)]
        defecto = list_books.lista[0] if analysis_params.book_name else None
        for book in list_books.lista:
            if analysis_params.book_name == book.name:
                defecto = book
            li.append((book.name, book))
        config = FormLayout.Combobox(_("Do not scan the opening moves based on book"), li)
        li_gen.append((config, defecto))

        li_gen.append(
            (
                f"{_('Do not scan standard opening moves')}:",
                analysis_params.standard_openings,
            )
        )
        li_gen.append(SEPARADOR)
        li_gen.append((f"{_('Add accuracy tags to the game')}:", analysis_params.accuracy_tags))

        li_gen.append(
            (
                f"{_('Redo any existing prior analysis (if they exist)')}:",
                analysis_params.delete_previous,
            )
        )

        li_gen.append((f"{_('Start from the end of the game')}:", analysis_params.from_last_move))

        li_gen.append((f"{_('Show graphics')}:", analysis_params.show_graphs))

        li_var = form_variations(analysis_params)

        li_blunders, li_brilliancies = form_blunders_brilliancies(analysis_params, configuration)

        li_themes = form_themes(analysis_params)

        lista = [
            (li_gen, _("General options"), ""),
            (li_engine, _("Engine"), ""),
            (li_var, _("Variations"), ""),
            (li_blunders, _("Wrong moves"), ""),
            (li_brilliancies, _("Brilliancies"), ""),
            (li_themes, _("Tactical themes"), ""),
        ]

    else:
        lista = li_engine

    reg = Util.Record()
    reg.form = None

    def dispatch(valor):
        # Para manejar la incompatibilidad entre analizar variaciones y añadir analysis como variaciones.
        if reg.form is None:
            if isinstance(valor, FormLayout.FormTabWidget):
                reg.form = valor
                reg.cb_variations = valor.get_widget(2, 0)
                reg.cb_add_variations = valor.get_widget(2, 1)
                reg.cb_variations_checked = reg.cb_variations.isChecked()
                reg.cb_add_variations_checked = reg.cb_add_variations.isChecked()
                if reg.cb_variations_checked is True and reg.cb_add_variations_checked is True:
                    reg.cb_add_variations.setChecked(False)
        else:
            if hasattr(reg, "cb_variations") and (
                    reg.cb_variations.isChecked() is True and reg.cb_add_variations.isChecked() is True
            ):
                if reg.cb_variations_checked:
                    reg.cb_variations.setChecked(False)
                else:
                    reg.cb_add_variations.setChecked(False)
                reg.cb_variations_checked = reg.cb_variations.isChecked()
                reg.cb_add_variations_checked = reg.cb_add_variations.isChecked()

            QTUtils.refresh_gui()

    def analysis_config():
        last_active_window = QtWidgets.QApplication.activeWindow()
        w = WindowAnalysisConfig.WConfAnalysis(last_active_window, None)
        w.show()

    li_extra_options = ((_("Configuration"), Iconos.ConfAnalysis(), analysis_config),) if extended_mode else None

    func_dispatch = dispatch if extended_mode else None
    resultado = FormLayout.fedit(
        lista,
        title=_("Analysis Configuration"),
        parent=parent,
        minimum_width=460,
        icon=Iconos.Opciones(),
        dispatch=func_dispatch,
        li_extra_options=li_extra_options,
    )

    li_gen = li_var = li_blunders = li_brilliancies = li_themes = None

    if resultado:
        accion, li_resp = resultado

        if extended_mode:
            li_gen, li_engine, li_var, li_blunders, li_brilliancies, li_themes = li_resp
        else:
            li_engine = li_resp

        analysis_params.engine = li_engine[0]
        analysis_params.vtime = int(li_engine[1] * 1000)
        analysis_params.depth = li_engine[2]
        analysis_params.nodes = li_engine[3]
        if analysis_params.vtime == 0 and analysis_params.depth == 0 and analysis_params.nodes == 0:
            analysis_params.vtime = 1000
        analysis_params.multiPV = li_engine[4]
        analysis_params.priority = li_engine[5]

        if extended_mode:
            color = li_gen[0]
            analysis_params.white = color != "BLACK"
            analysis_params.black = color != "WHITE"
            analysis_params.num_moves = li_gen[1]
            analysis_params.book = li_gen[2]
            analysis_params.book_name = analysis_params.book.name if analysis_params.book else None
            analysis_params.standard_openings = li_gen[3]
            analysis_params.accuracy_tags = li_gen[4]
            analysis_params.delete_previous = li_gen[5]
            analysis_params.from_last_move = li_gen[6]
            analysis_params.show_graphs = li_gen[7]

            (
                analysis_params.analyze_variations,
                analysis_params.include_variations,
                analysis_params.what_variations,
                analysis_params.include_played,
                analysis_params.limit_include_variations,
                analysis_params.info_variation,
                analysis_params.si_pdt,
                analysis_params.one_move_variation,
            ) = li_var

            (
                analysis_params.kblunders_condition,
                analysis_params.tacticblunders,
                analysis_params.pgnblunders,
                analysis_params.oriblunders,
                analysis_params.bmtblunders,
            ) = li_blunders

            (
                analysis_params.fnsbrilliancies,
                analysis_params.pgnbrilliancies,
                analysis_params.oribrilliancies,
                analysis_params.bmtbrilliancies,
            ) = li_brilliancies

            (
                analysis_params.themes_assign,
                analysis_params.themes_tags,
                analysis_params.themes_reset,
            ) = li_themes

        dic = {}
        for x in dir(analysis_params):
            if not x.startswith("__"):
                dic[x] = getattr(analysis_params, x)
        save_dic_params(dic)

        return analysis_params
    else:
        return None


def massive_analysis_parameters(parent, configuration, multiple_selected, is_database=False):
    analysis_params = read_dic_params()

    # Datos
    li_gen = [SEPARADOR]
    li_j = [(_("White"), "WHITE"), (_("Black"), "BLACK"), (_("White & Black"), "BOTH")]
    config = FormLayout.Combobox(_("Analyze color"), li_j)
    if analysis_params.white and analysis_params.black:
        color = "BOTH"
    elif analysis_params.black:
        color = "BLACK"
    elif analysis_params.white:
        color = "WHITE"
    else:
        color = "BOTH"
    li_gen.append((config, color))

    cjug = ";".join(analysis_params.li_players) if analysis_params.li_players else ""
    li_gen.append(
        (
            (
                    '<div align="right">'
                    + _("Only the following players")
                    + f':<br>{_("(You can add multiple aliases separated by ; and wildcards with *)")}</div>'
            ),
            cjug,
        )
    )

    config = FormLayout.Editbox(
        f"<div align=\"right\">{_('Moves')}<br>{_('By example:')} -5,8-12,14,19-",
        rx=r"[0-9,\-]*",
    )
    li_gen.append((config, ""))

    list_books = Books.ListBooks()
    li = [("--", None)]
    defecto = None if analysis_params.book_name is None else list_books.lista[0]
    for book in list_books.lista:
        if book.name == analysis_params.book_name:
            defecto = book
        li.append((book.name, book))
    config = FormLayout.Combobox(_("Do not scan the opening moves based on book"), li)
    li_gen.append((config, defecto))

    li_gen.append(
        (
            f"{_('Do not scan standard opening moves')}:",
            analysis_params.standard_openings,
        )
    )

    li_gen.append((f"{_('Add accuracy tags to the game')}:", analysis_params.accuracy_tags))

    li_gen.append(SEPARADOR)
    li_gen.append((f"{_('Start from the end of the game')}:", analysis_params.from_last_move))

    li_gen.append(
        (
            f"{_('Redo any existing prior analysis (if they exist)')}:",
            analysis_params.delete_previous,
        )
    )

    li_gen.append((f"{_('Only selected games')}:", multiple_selected))
    li_gen.append(SEPARADOR)
    cores = Util.cpu_count()
    li_gen.append(
        (
            FormLayout.Spinbox(_("Number of parallel processes"), 1, cores, 40),
            min(analysis_params.workers, cores),
        )
    )
    li_gen.append(SEPARADOR)

    li_var = form_variations(analysis_params)

    li_blunders, li_brilliancies = form_blunders_brilliancies(analysis_params, configuration)
    li_themes = form_themes(analysis_params)

    li_engine = form_engine(analysis_params, False)

    lista = [
        (li_gen, _("General options"), ""),
        (li_engine, _("Engine"), ""),
        (li_var, _("Variations"), ""),
        (li_blunders, _("Wrong moves"), ""),
        (li_brilliancies, _("Brilliancies"), ""),
        (li_themes, _("Tactical themes"), ""),
    ]

    reg = Util.Record()
    reg.form = None

    reg = Util.Record()
    reg.form = None

    def dispatch(valor):
        # Para manejar la incompatibilidad entre analizar variaciones y añadir analysis como variaciones.
        if reg.form is None:
            if isinstance(valor, FormLayout.FormTabWidget):
                reg.form = valor
                reg.cb_variations = valor.get_widget(2, 0)
                reg.cb_add_variations = valor.get_widget(2, 1)
                reg.cb_variations_checked = reg.cb_variations.isChecked()
                reg.cb_add_variations_checked = reg.cb_add_variations.isChecked()
                if reg.cb_variations_checked is True and reg.cb_add_variations_checked is True:
                    reg.cb_add_variations.setChecked(False)
        else:
            if hasattr(reg, "cb_variations") and (
                    reg.cb_variations.isChecked() is True and reg.cb_add_variations.isChecked() is True
            ):
                if reg.cb_variations_checked:
                    reg.cb_variations.setChecked(False)
                else:
                    reg.cb_add_variations.setChecked(False)
                reg.cb_variations_checked = reg.cb_variations.isChecked()
                reg.cb_add_variations_checked = reg.cb_add_variations.isChecked()

            QTUtils.refresh_gui()

    def analysis_config():
        last_active_window = QtWidgets.QApplication.activeWindow()
        w = WindowAnalysisConfig.WConfAnalysis(last_active_window, None)
        w.show()

    li_extra_options = ((_("Configuration"), Iconos.ConfAnalysis(), analysis_config),)

    resultado = FormLayout.fedit(
        lista,
        title=_("Mass analysis"),
        parent=parent,
        minimum_width=460,
        icon=Iconos.Opciones(),
        li_extra_options=li_extra_options,
        dispatch=dispatch,
    )

    if resultado:
        accion, li_resp = resultado

        li_gen, li_engine, li_var, li_blunders, li_brilliancies, li_themes = li_resp

        (
            color,
            cjug,
            analysis_params.num_moves,
            analysis_params.book,
            analysis_params.standard_openings,
            analysis_params.accuracy_tags,
            analysis_params.from_last_move,
            analysis_params.delete_previous,
            analysis_params.multiple_selected,
            analysis_params.workers,
        ) = li_gen

        (
            analysis_params.engine,
            vtime,
            analysis_params.depth,
            analysis_params.nodes,
            analysis_params.multiPV,
            analysis_params.priority,
        ) = li_engine

        analysis_params.vtime = int(vtime * 1000)
        if analysis_params.vtime == 0 and analysis_params.depth == 0 and analysis_params.nodes == 0:
            analysis_params.vtime = 1000

        analysis_params.white = color != "BLACK"
        analysis_params.black = color != "WHITE"
        cjug = cjug.strip()
        analysis_params.li_players = cjug.split(";") if cjug else None
        analysis_params.book_name = analysis_params.book.name if analysis_params.book else None

        (
            analysis_params.kblunders_condition,
            analysis_params.tacticblunders,
            analysis_params.pgnblunders,
            analysis_params.oriblunders,
            analysis_params.bmtblunders,
        ) = li_blunders

        (
            analysis_params.analyze_variations,
            analysis_params.include_variations,
            analysis_params.what_variations,
            analysis_params.include_played,
            analysis_params.limit_include_variations,
            analysis_params.info_variation,
            analysis_params.si_pdt,
            analysis_params.one_move_variation,
        ) = li_var

        (
            analysis_params.fnsbrilliancies,
            analysis_params.pgnbrilliancies,
            analysis_params.oribrilliancies,
            analysis_params.bmtbrilliancies,
        ) = li_brilliancies

        (
            analysis_params.themes_assign,
            analysis_params.themes_tags,
            analysis_params.themes_reset,
        ) = li_themes

        dic = {}
        for x in dir(analysis_params):
            if not x.startswith("__"):
                dic[x] = getattr(analysis_params, x)
        save_dic_params(dic)

        if not (
                analysis_params.tacticblunders
                or analysis_params.pgnblunders
                or analysis_params.bmtblunders
                or analysis_params.fnsbrilliancies
                or analysis_params.pgnbrilliancies
                or analysis_params.bmtbrilliancies
                or is_database
        ):
            QTMessages.message_error(parent, _("No file was specified where to save results"))
            return None

        return analysis_params
    else:
        return None
