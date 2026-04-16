from types import SimpleNamespace

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
from Code.Engines import Engines, Priorities
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
        blunders_keep_settings=dic.get("blunders_keep_settings", False),
        tacticblunders=dic.get("tacticblunders", ""),
        pgnblunders=dic.get("pgnblunders", ""),
        oriblunders=dic.get("oriblunders", False),
        bmtblunders=dic.get("bmtblunders", ""),
        brilliancies_keep_settings=dic.get("brilliancies_keep_settings", False),
        fnsbrilliancies=dic.get("fnsbrilliancies", ""),
        pgnbrilliancies=dic.get("pgnbrilliancies", ""),
        oribrilliancies=dic.get("oribrilliancies", False),
        bmtbrilliancies=dic.get("bmtbrilliancies", ""),
        mates_saved_name=dic.get("mates_saved_name", ""),
        mates_keep_settings=dic.get("mates_keep_settings", False),
    )


def _save_analysis_params(analysis_params):
    dic = {x: getattr(analysis_params, x) for x in dir(analysis_params) if not x.startswith("__")}
    configuration = Code.configuration
    file = configuration.paths.file_param_analysis()
    dic1 = Util.restore_pickle(file, {})
    dic1.update(dic)
    Util.save_pickle(file, dic1)


def _get_color_selection(analysis_params):
    if analysis_params.white and analysis_params.black:
        return "BOTH"
    elif analysis_params.black:
        return "BLACK"
    elif analysis_params.white:
        return "WHITE"
    return "BOTH"


def _set_color_selection(analysis_params, color):
    analysis_params.white = color != "BLACK"
    analysis_params.black = color != "WHITE"


def _form_blunders_brilliancies(analysis_params, configuration):
    # Blunders
    blunders_keep_settings = analysis_params.blunders_keep_settings
    if blunders_keep_settings:
        tacticblunders = analysis_params.tacticblunders
        pgnblunders = analysis_params.pgnblunders
        oriblunders = analysis_params.oriblunders
        bmtblunders = analysis_params.bmtblunders
    else:
        tacticblunders = pgnblunders = bmtblunders = ""
        oriblunders = False

    li_blunders = [SEPARADOR]

    li_types = [
        (f"{_('Dubious move')} (⁈)  + {_('Mistake')} (?) + {_('Blunder')} (⁇)", INACCURACY_MISTAKE_BLUNDER),
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

    li_blunders.append((None, _("Generate a training file with these moves")))

    config = FormLayout.Editbox(_("Tactics name"), rx="[^\\:/|?*^%><()]*")
    li_blunders.append((config, tacticblunders))

    path_pgn = file_next("Blunders", "pgn")
    config = FormLayout.Fichero(
        _("PGN Format"),
        f"{_('PGN Format')} (*.pgn)",
        True,
        minimum_width=280,
        file_default=path_pgn,
    )
    li_blunders.append((config, pgnblunders))

    li_blunders.append((f"{_('Also add complete game to PGN')}:", oriblunders))
    li_blunders.append(SEPARADOR)

    eti = f'"{_("Find best move")}"'
    li_blunders.append((f"{_X(_('Add to the training %1 with the name'), eti)}:", bmtblunders))
    li_blunders.append(SEPARADOR)
    li_blunders.append((f"{_('Keep settings')}:", blunders_keep_settings))

    # Brilliancies
    brilliancies_keep_settings = analysis_params.brilliancies_keep_settings
    if brilliancies_keep_settings:
        fnsbrilliancies = analysis_params.fnsbrilliancies
        pgnbrilliancies = analysis_params.pgnbrilliancies
        oribrilliancies = analysis_params.oribrilliancies
        bmtbrilliancies = analysis_params.bmtbrilliancies
    else:
        fnsbrilliancies = pgnbrilliancies = bmtbrilliancies = ""
        oribrilliancies = False

    li_brilliancies = [SEPARADOR]

    path_fns = file_next("Brilliancies", "fns")
    path_pgn = file_next("Brilliancies", "pgn")

    li_brilliancies.append((None, _("Generate a training file with these moves")))

    config = FormLayout.Fichero(
        _("List of FENs"),
        f"{_('List of FENs')} (*.fns)",
        True,
        minimum_width=280,
        file_default=path_fns,
    )
    li_brilliancies.append((config, fnsbrilliancies))

    config = FormLayout.Fichero(
        _("PGN Format"),
        f"{_('PGN Format')} (*.pgn)",
        True,
        minimum_width=280,
        file_default=path_pgn,
    )
    li_brilliancies.append((config, pgnbrilliancies))

    li_brilliancies.append((f"{_('Also add complete game to PGN')}:", oribrilliancies))
    li_brilliancies.append(SEPARADOR)

    eti = f'"{_("Find best move")}"'
    li_brilliancies.append((f"{_X(_('Add to the training %1 with the name'), eti)}:", bmtbrilliancies))
    li_brilliancies.append(SEPARADOR)
    li_brilliancies.append((f"{_('Keep settings')}:", brilliancies_keep_settings))

    return li_blunders, li_brilliancies


def _form_variations(analysis_params):
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
        (FormLayout.Spinbox(_("Maximum centipawns lost"), 0, 1000, 60), analysis_params.limit_include_variations)
    )
    li_var.append((f"{_('Include info about engine')}:", analysis_params.info_variation))
    li_var.append((f"{_('Format')} {_('Score')}/{_('Depth')}/{_('Time')}:", analysis_params.si_pdt))
    li_var.append((f"{_('Only one move of each variation')}:", analysis_params.one_move_variation))
    return li_var


def _form_themes(alm):
    return [
        SEPARADOR,
        (f"{_('Automatic assignment')}:", alm.themes_assign),
        SEPARADOR,
        SEPARADOR,
        (None, f"{_('In case automatic assignment is activated')}:"),
        SEPARADOR,
        (f"{_('Add themes tag to the game')} (TacticThemes):", alm.themes_tags),
        SEPARADOR,
        (f"{_('Pre-delete the following themes?')}:", alm.themes_reset),
        (None, f"@|{AssignThemes.AssignThemes().txt_all_themes()}"),
        SEPARADOR,
    ]


def _form_mates(analysis_params):
    mates_saved_name = analysis_params.mates_saved_name if analysis_params.mates_keep_settings else ""

    return [
        SEPARADOR,
        (f"{_('Save all mates detected with the name')}:", mates_saved_name),
        (None, f"📚️ {_('Train')}/{_('Tactics')}/{_('Training positions')}/{_('Personal Training')}"),
        SEPARADOR,
        (f"{_('Keep settings')}:", analysis_params.mates_keep_settings)
    ]


def _form_engine(analysis_params, all_engines):
    li_engine = [SEPARADOR]

    if all_engines:
        li = Code.configuration.engines.formlayout_combo_analyzer(False)
    else:
        li = Code.configuration.engines.formlayout_combo_analyzer(True)
        li[0] = analysis_params.engine
    li_engine.append((f"{_('Engine')}:", li))
    li_engine.append(SEPARADOR)

    config = FormLayout.Editbox(_("Duration of engine analysis (secs)"), 40, tipo=float)
    li_engine.append((config, analysis_params.vtime / 1000.0))

    tooltip = _("If time and depth are given, the depth is attempted and the time becomes a maximum.")
    config = FormLayout.Editbox(f"{_('Depth')} (0={_('Disable')})", 40, tipo=int, tooltip=tooltip)
    li_engine.append((config, analysis_params.depth))

    tooltip = _("If time and nodes are given, the nodes is attempted and the time becomes a maximum.")
    config = FormLayout.Editbox(f"{_('Fixed nodes')} (0={_('Disable')})", 80, tipo=int, tooltip=tooltip)
    li_engine.append((config, analysis_params.nodes))

    li_engine.append(SEPARADOR)
    li = Engines.list_depths_to_cb()
    config = FormLayout.Combobox(_("Number of variations evaluated by the engine (MultiPV)"), li)
    li_engine.append((config, analysis_params.multiPV))

    config = FormLayout.Combobox(_("Process priority"), Priorities.priorities.combo())
    li_engine.append((config, analysis_params.priority))
    li_engine.append(SEPARADOR)

    return li_engine


def _form_general_options(analysis_params, multiple_selected, is_massive):
    li_gen = [SEPARADOR]

    li_j = [(_("White"), "WHITE"), (_("Black"), "BLACK"), (_("White & Black"), "BOTH")]
    config = FormLayout.Combobox(_("Analyze color"), li_j)
    li_gen.append((config, _get_color_selection(analysis_params)))

    cjug = ";".join(analysis_params.li_players) if analysis_params.li_players else ""
    li_gen.append(
        (
            f'<div align="right">{_("Only the following players")}:<br>'
            f'{_("(You can add multiple aliases separated by ; and wildcards with *)")}</div>',
            cjug,
        )
    )

    config = FormLayout.Editbox(
        f'<div align="right">{_("Moves")}<br>{_("By example:")} -5,8-12,14,19-',
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

    li_gen.append((f"{_('Do not scan standard opening moves')}:", analysis_params.standard_openings))
    li_gen.append(SEPARADOR)
    li_gen.append((f"{_('Add accuracy tags to the game')}:", analysis_params.accuracy_tags))
    li_gen.append((f"{_('Redo any existing prior analysis (if they exist)')}:", analysis_params.delete_previous))
    li_gen.append((f"{_('Start from the end of the game')}:", analysis_params.from_last_move))
    li_gen.append((f"{_('Show graphics')}:", analysis_params.show_graphs))

    if multiple_selected:
        li_gen.append(SEPARADOR)
        li_gen.append((f"{_('Only selected games')}:", multiple_selected))

    if is_massive:
        cores = 999
        li_gen.append(
            (FormLayout.Spinbox(_("Number of parallel processes"), 1, cores, 40),
             min(analysis_params.workers, cores))
        )
        li_gen.append(SEPARADOR)

    return li_gen


def _create_dispatch():
    reg = Util.Record()
    reg.form = None
    reg.cb_variations = None
    reg.cb_add_variations = None
    reg.cb_variations_checked = False
    reg.cb_add_variations_checked = False

    def dispatch(valor):
        if reg.form is None:
            if isinstance(valor, FormLayout.FormTabWidget):
                reg.form = valor
                reg.cb_variations = valor.get_widget(2, 0)
                reg.cb_add_variations = valor.get_widget(2, 1)
                reg.cb_variations_checked = reg.cb_variations.isChecked()
                reg.cb_add_variations_checked = reg.cb_add_variations.isChecked()
                if reg.cb_variations_checked and reg.cb_add_variations_checked:
                    reg.cb_add_variations.setChecked(False)
        else:
            if (
                    reg.cb_variations
                    and reg.cb_add_variations
                    and reg.cb_variations.isChecked()
                    and reg.cb_add_variations.isChecked()
            ):
                if reg.cb_variations_checked:
                    reg.cb_variations.setChecked(False)
                else:
                    reg.cb_add_variations.setChecked(False)
                reg.cb_variations_checked = reg.cb_variations.isChecked()
                reg.cb_add_variations_checked = reg.cb_add_variations.isChecked()
            QTUtils.refresh_gui()

    return dispatch


def _create_analysis_config_option():
    def analysis_config():
        from PySide6 import QtWidgets

        last_active_window = QtWidgets.QApplication.activeWindow()
        w = WindowAnalysisConfig.WConfAnalysis(last_active_window, None)
        w.show()

    return analysis_config


def _apply_engine_params(analysis_params, li_engine):
    analysis_params.engine = li_engine[0]
    analysis_params.vtime = int(li_engine[1] * 1000)
    analysis_params.depth = li_engine[2]
    analysis_params.nodes = li_engine[3]
    if analysis_params.vtime == 0 and analysis_params.depth == 0 and analysis_params.nodes == 0:
        analysis_params.vtime = 1000
    analysis_params.multiPV = li_engine[4]
    analysis_params.priority = li_engine[5]


def _apply_general_params(analysis_params, li_gen, multiple_selected=None):
    color = li_gen[0]
    _set_color_selection(analysis_params, color)
    cjug = li_gen[1].strip()
    analysis_params.li_players = cjug.split(";") if cjug else None
    analysis_params.num_moves = li_gen[2]
    analysis_params.book = li_gen[3]
    analysis_params.book_name = analysis_params.book.name if analysis_params.book else None
    analysis_params.standard_openings = li_gen[4]
    analysis_params.accuracy_tags = li_gen[5]
    analysis_params.delete_previous = li_gen[6]
    analysis_params.from_last_move = li_gen[7]
    analysis_params.show_graphs = li_gen[8]
    if multiple_selected is not None:
        if multiple_selected:
            analysis_params.multiple_selected = li_gen[9]
            pos_workers = 10
        else:
            analysis_params.multiple_selected = False
            pos_workers = 9
        analysis_params.workers = li_gen[pos_workers]


def _apply_variation_params(analysis_params, li_var):
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


def _apply_blunders_params(analysis_params, li_blunders):
    (
        analysis_params.kblunders_condition,
        analysis_params.tacticblunders,
        analysis_params.pgnblunders,
        analysis_params.oriblunders,
        analysis_params.bmtblunders,
        analysis_params.blunders_keep_settings,
    ) = li_blunders


def _apply_brilliancies_params(analysis_params, li_brilliancies):
    (
        analysis_params.fnsbrilliancies,
        analysis_params.pgnbrilliancies,
        analysis_params.oribrilliancies,
        analysis_params.bmtbrilliancies,
        analysis_params.brilliancies_keep_settings,
    ) = li_brilliancies


def _apply_themes_params(analysis_params, li_themes):
    analysis_params.themes_assign, analysis_params.themes_tags, analysis_params.themes_reset = li_themes


def _apply_mates_params(analysis_params, li_mates):
    analysis_params.mates_saved_name, analysis_params.mates_keep_settings = li_mates


def analysis_parameters(parent, extended_mode, all_engines, multiple_selected, is_massive):
    analysis_params = read_dic_params()
    configuration = Code.configuration

    li_engine = _form_engine(analysis_params, all_engines)

    if extended_mode:
        li_gen = _form_general_options(analysis_params, multiple_selected, is_massive)
        li_var = _form_variations(analysis_params)
        li_blunders, li_brilliancies = _form_blunders_brilliancies(analysis_params, configuration)
        li_themes = _form_themes(analysis_params)
        li_mates = _form_mates(analysis_params)

        lista = [
            (li_gen, _("General options"), ""),
            (li_engine, _("Engine"), ""),
            (li_var, _("Variations"), ""),
            (li_blunders, _("Wrong moves"), ""),
            (li_brilliancies, _("Brilliancies"), ""),
            (li_mates, _X(_("Mate in %1"), "?"), ""),
            (li_themes, _("Tactical themes"), ""),
        ]
    else:
        lista = li_engine

    func_dispatch = _create_dispatch() if extended_mode else None
    li_extra_options = (
        [(_("Configuration"), Iconos.ConfAnalysis(), _create_analysis_config_option())] if extended_mode else None
    )

    resultado = FormLayout.fedit(
        lista,
        title=_("Analysis Configuration"),
        parent=parent,
        minimum_width=460,
        icon=Iconos.Opciones(),
        dispatch=func_dispatch,
        li_extra_options=li_extra_options,
    )

    if resultado:
        accion, li_resp = resultado

        if extended_mode:
            li_gen, li_engine, li_var, li_blunders, li_brilliancies, li_mates, li_themes = li_resp
            _apply_general_params(analysis_params, li_gen)
            _apply_variation_params(analysis_params, li_var)
            _apply_blunders_params(analysis_params, li_blunders)
            _apply_brilliancies_params(analysis_params, li_brilliancies)
            _apply_themes_params(analysis_params, li_themes)
            _apply_mates_params(analysis_params, li_mates)
        else:
            li_engine = li_resp

        _apply_engine_params(analysis_params, li_engine)
        _save_analysis_params(analysis_params)
        return analysis_params
    return None


def massive_analysis_parameters(parent, configuration, multiple_selected, is_database=False):
    analysis_params = read_dic_params()

    li_gen = _form_general_options(analysis_params, multiple_selected, True)
    li_engine = _form_engine(analysis_params, False)
    li_var = _form_variations(analysis_params)
    li_blunders, li_brilliancies = _form_blunders_brilliancies(analysis_params, configuration)
    li_themes = _form_themes(analysis_params)
    li_mates = _form_mates(analysis_params)

    lista = [
        (li_gen, _("General options"), ""),
        (li_engine, _("Engine"), ""),
        (li_var, _("Variations"), ""),
        (li_blunders, _("Wrong moves"), ""),
        (li_brilliancies, _("Brilliancies"), ""),
        (li_mates, _X(_("Mate in %1"), "?"), ""),
        (li_themes, _("Tactical themes"), ""),
    ]

    li_extra_options = [(_("Configuration"), Iconos.ConfAnalysis(), _create_analysis_config_option())]

    resultado = FormLayout.fedit(
        lista,
        title=_("Mass analysis"),
        parent=parent,
        minimum_width=460,
        icon=Iconos.Opciones(),
        li_extra_options=li_extra_options,
        dispatch=_create_dispatch(),
    )

    if resultado:
        accion, li_resp = resultado

        li_gen, li_engine, li_var, li_blunders, li_brilliancies, li_mates, li_themes = li_resp

        _apply_general_params(analysis_params, li_gen, multiple_selected)
        _apply_engine_params(analysis_params, li_engine)
        _apply_variation_params(analysis_params, li_var)
        _apply_blunders_params(analysis_params, li_blunders)
        _apply_brilliancies_params(analysis_params, li_brilliancies)
        _apply_mates_params(analysis_params, li_mates)
        _apply_themes_params(analysis_params, li_themes)

        _save_analysis_params(analysis_params)

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
    return None
