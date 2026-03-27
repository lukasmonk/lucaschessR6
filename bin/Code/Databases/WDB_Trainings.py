import os
import time

import Code
from Code.Base.Constantes import FEN_INITIAL
from Code.QT import FormLayout, Iconos, QTMessages
from Code.Z import Util


def message_creating_trainings(owner, li_creados, li_no_creados):
    txt = ""
    if li_creados:
        txt += f"{_('Created the following trainings')}:"
        txt += "<ul>"
        for x in li_creados:
            txt += f"<li>{os.path.basename(x)}</li>"
        txt += "</ul>"
    if li_no_creados:
        txt += _("No trainings created due to lack of data")
        if li_creados:
            txt += ":<ul>"
            for x in li_no_creados:
                txt += f"<li>{os.path.basename(x)}</li>"
            txt += "</ul>"
    QTMessages.message_bold(owner, txt)


def create_tactics(wowner, li_registros_selected, li_registros_total, rutina_datos, name):
    nregs = len(li_registros_selected)

    form = FormLayout.FormLayout(wowner, _("Create tactics training"), Iconos.Tacticas())

    form.separador()
    form.edit(_("Name"), name)

    form.separador()
    li_j = [(_("By default"), 0), (_("White"), 1), (_("Black"), 2)]
    form.combobox(_("Point of view"), li_j, 0)

    form.separador()
    form.checkbox(_("Skip the first move"), False)

    form.separador()
    selected = nregs > 1
    form.checkbox("%s (%d)" % (_("Only selected games"), nregs), selected)
    form.separador()

    resultado = form.run()

    if not resultado:
        return

    accion, li_gen = resultado

    menuname = li_gen[0].strip()
    if not menuname:
        return
    pointview = str(li_gen[1])
    skip_first = li_gen[2]
    only_selected = li_gen[3]

    li_registros = li_registros_selected if only_selected else li_registros_total
    nregs = len(li_registros)

    rest_dir = Util.valid_filename(menuname)
    nom_dir = Util.opj(Code.configuration.paths.folder_tactics(), rest_dir)
    nom_ini = Util.opj(nom_dir, "Config.ini")
    if os.path.isfile(nom_ini):
        dic_ini = Util.ini2dic(nom_ini)
        n = 1
        while True:
            if "TACTIC%d" % n in dic_ini:
                if "MENU" in dic_ini["TACTIC%d" % n]:
                    if dic_ini["TACTIC%d" % n]["MENU"].upper() == menuname.upper():
                        break
                else:
                    break
                n += 1
            else:
                break
        nom_tactic = "TACTIC%d" % n
    else:
        Util.create_folder(nom_dir)
        nom_tactic = "TACTIC1"
        dic_ini = {}
    nom_fns = Util.opj(nom_dir, "Puzzles.fns")
    if os.path.isfile(nom_fns):
        n = 1
        nom_fns = Util.opj(nom_dir, "Puzzles-%d.fns")
        while os.path.isfile(nom_fns % n):
            n += 1
        nom_fns = nom_fns % n

    # Se crea el file con los puzzles
    f = open(nom_fns, "wt", encoding="utf-8", errors="ignore")

    tmp_bp = QTMessages.ProgressBarSimple(wowner, menuname, "%s: %d" % (_("Games"), nregs), nregs)
    tmp_bp.mostrar()

    fen0 = FEN_INITIAL

    t = time.time()

    for n in range(nregs):

        if tmp_bp.is_canceled():
            break

        tmp_bp.pon(n + 1)
        if time.time() - t > 1.0 or (nregs - n) < 10:
            tmp_bp.mensaje("%d/%d" % (n + 1, nregs))
            t = time.time()

        recno = li_registros[n]

        dic_valores = rutina_datos(recno, skip_first)
        if dic_valores is None:
            continue
        plies = dic_valores["PLIES"]
        if plies == 0:
            continue

        pgn = dic_valores["PGN"]
        li = pgn.split("\n")
        if len(li) == 1:
            li = pgn.split("\r")
        li = [linea for linea in li if not linea.strip().startswith("[")]
        num_moves = " ".join(li).replace("\r", "").replace("\n", "")
        if not num_moves.strip("*"):
            continue

        def xdic(k):
            x = dic_valores.get(k, "")
            if x is None:
                x = ""
            elif "?" in x:
                x = x.replace(".?", "").replace("?", "")
            return x.strip()

        fen = dic_valores.get("FEN")
        if not fen:
            fen = fen0

        event = xdic("EVENT")
        site = xdic("SITE")
        date = xdic("DATE")
        gameurl = xdic("GAMEURL")
        themes = xdic("THEMES")
        if site == event:
            es = event
        else:
            es = f"{event} {site}"
        es = es.strip()
        if date:
            if es:
                es += f" ({date})"
            else:
                es = date
        white = xdic("WHITE")
        black = xdic("BLACK")
        wb = f"{white}-{black}".strip("-")

        li_titulo = []

        def add_titulo(xtxt):
            if xtxt:
                li_titulo.append(xtxt)

        add_titulo(es)
        add_titulo(wb)
        add_titulo(themes)
        if gameurl:
            add_titulo(f'<a href="{gameurl}">{gameurl}</a>')
        for other in ("TASK", "SOURCE"):
            v = xdic(other)
            add_titulo(v)
        titulo = "<br>".join(li_titulo)

        if skip_first:
            pgn_real = dic_valores["PGN_REAL"].replace("\n", " ").replace("\r", " ")
            txt = f"{fen}|{titulo}|{num_moves}|{pgn_real}\n"
        else:
            txt = f"{fen}|{titulo}|{num_moves}\n"

        f.write(txt)

    f.close()
    tmp_bp.cerrar()

    # Se crea el file de control
    dic_ini[nom_tactic] = d = {}
    d["MENU"] = menuname
    d["FILESW"] = f"{os.path.basename(nom_fns)}:100"
    d["POINTVIEW"] = pointview

    Util.dic2ini(nom_ini, dic_ini)

    def sp(num):
        return " " * num

    QTMessages.message_bold(
        wowner,
        (
                "%s<br>%s<br><br>%s<br>%s<br>%s"
                % (
                    _("Tactic training %s created.") % menuname,
                    _("You can access this training from"),
                    "%s/%s" % (_("Train"), _("Tactics")),
                    "%s1) %s / %s / %s <br>%s➔ %s"
                    % (
                        sp(5),
                        _("Training positions"),
                        _("Personal Training"),
                        _("Personal tactics"),
                        sp(12),
                        _("for a standard training"),
                    ),
                    "%s2) %s / %s <br>%s➔ %s"
                    % (
                        sp(5),
                        _("Learn tactics by repetition"),
                        _("Personal tactics"),
                        sp(12),
                        _("for a training by repetition"),
                    ),
                )
        ),
    )


def create_training_positions(wowner, li_registros_selected, li_registros_total, rutina_datos, name):
    nregs = len(li_registros_selected)

    form = FormLayout.FormLayout(wowner, _("Training positions"), Iconos.TrainPositions())

    form.separador()
    form.edit(_("Name"), name)

    form.separador()
    form.checkbox(_("Skip the first move"), False)

    form.separador()
    selected = nregs > 1
    form.checkbox("%s (%d)" % (_("Only selected games"), nregs), selected)
    form.separador()

    resultado = form.run()

    if not resultado:
        return

    accion, li_gen = resultado

    menuname = li_gen[0].strip()
    if not menuname:
        return
    skip_first = li_gen[1]
    only_selected = li_gen[2]

    li_registros = li_registros_selected if only_selected else li_registros_total
    nregs = len(li_registros)

    menuname = Util.valid_filename(menuname)
    Util.create_folder(Code.configuration.paths.folder_personal_trainings())
    nom_fns = Util.opj(Code.configuration.paths.folder_personal_trainings(), f"{menuname}.fns")

    nom_menu = menuname
    if os.path.isfile(nom_fns):
        n = 1
        nom_fns = Util.opj(Code.configuration.paths.folder_personal_trainings(), f"{menuname}-%d.fns")
        while os.path.isfile(nom_fns % n):
            n += 1
        nom_fns = nom_fns % n
        nom_menu = menuname + "-%d" % n

    # Se crea el file con los puzzles
    f = open(nom_fns, "wt", encoding="utf-8", errors="ignore")

    tmp_bp = QTMessages.ProgressBarWithTime(wowner, menuname, show_time=True)
    tmp_bp.mostrar()
    tmp_bp.set_total(nregs)

    ok = True

    for n in range(nregs):

        if tmp_bp.is_canceled():
            ok = False
            break

        tmp_bp.pon(n + 1)

        recno = li_registros[n]

        dic_valores = rutina_datos(recno, skip_first)
        fen = dic_valores.get("FEN")
        if not fen:
            continue

        pgn = dic_valores["PGN"]
        li = pgn.split("\n")
        if len(li) == 1:
            li = pgn.split("\r")
        li = [linea for linea in li if not linea.strip().startswith("[")]
        num_moves = " ".join(li).replace("\r", "").replace("\n", "")

        def xdic(k):
            x = dic_valores.get(k, "")
            if x is None:
                x = ""
            elif "?" in x:
                x = x.replace(".?", "").replace("?", "")
            return x.strip()

        event = xdic("EVENT")
        site = xdic("SITE")
        date = xdic("DATE")
        gameurl = xdic("GAMEURL")
        themes = xdic("THEMES")
        if site == event:
            es = event
        else:
            es = f"{event} {site}"
        es = es.strip()
        if date:
            if es:
                es += f" ({date})"
            else:
                es = date
        white = xdic("WHITE")
        black = xdic("BLACK")
        wb = f"{white}-{black}".strip("-")

        li_titulo = []

        def add_titulo(xtxt):
            if xtxt:
                li_titulo.append(xtxt)

        add_titulo(es)
        add_titulo(wb)
        add_titulo(themes)
        if gameurl:
            add_titulo(f'<a href="{gameurl}">{gameurl}</a>')
        for other in ("TASK", "SOURCE"):
            v = xdic(other)
            add_titulo(v)
        titulo = "<br>".join(li_titulo)

        if skip_first:
            pgn_real = dic_valores["PGN_REAL"].replace("\n", " ").replace("\r", " ")
            txt = f"{fen}|{titulo}|{num_moves}|{pgn_real}\n"
        else:
            txt = f"{fen}|{titulo}|{num_moves}\n"

        f.write(txt)

    f.close()
    tmp_bp.cerrar()

    if ok:
        message = f'{_("Tactics")}\n  {_("Training positions")}\n    {_("Personal Training")}\n      {nom_menu}\n'
        QTMessages.message_bold(wowner, f"{_('Created')}:\n\n{message}")
