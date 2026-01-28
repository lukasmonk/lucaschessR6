from PySide6 import QtCore, QtGui, QtWidgets

import Code
from Code.CompetitionWithTutor import CompetitionWithTutor
from Code.QT import Colocacion, Controles, Iconos, QTDialogs, QTMessages, ScreenUtils
from Code.Translations import TrListas


def datos(w_parent):
    if resp := dame_categoria(w_parent):
        rival, categorias, categoria = resp
    else:
        return None

    w = WDatos(w_parent, rival, categorias, categoria)
    if w.exec():
        return categorias, categoria, w.nivel, w.is_white, w.puntos
    else:
        return None


def dame_categoria(w_parent):
    dbm = CompetitionWithTutor.DBManagerCWT()
    rival_key = dbm.get_current_rival_key()
    li_grupos = dbm.grupos.liGrupos

    categorias = dbm.get_categorias_rival(rival_key)

    rival = Code.configuration.engines.search(rival_key)

    font_normal = Controles.FontType(more_puntos=2)
    font_bold = Controles.FontType(more_puntos=4, peso=300)

    menu = Controles.Menu(w_parent)
    menu.set_font(font_bold)

    menu.separador()
    submenu_rival = menu.submenu(
        f'{_("Opponent")}: {rival.name} [{categorias.puntuacion()} {_("pts")}]',
        Iconos.NuevaPartida(),
    )
    submenu_rival.setFont(font_normal)
    menu.separador()

    # ----------- RIVAL
    submenu_rival.separador()
    submenu_rival.opcion(None, _("Change opponent"), is_disabled=True, font_type=font_bold)
    menu.separador()
    submenu_rival.separador()

    ico_no = Iconos.Motor_No()
    ico_si = Iconos.Motor_Si()
    ico_actual = Iconos.Motor_Actual()
    grp_no = Iconos.Grupo_No()
    grp_si = Iconos.Grupo_Si()

    for grupo in li_grupos:
        name = _X(_("%1 group"), grupo.name)
        if grupo.minPuntos > 0:
            name += " (+%d %s)" % (grupo.minPuntos, _("pts"))

        si_des = grupo.minPuntos > dbm.puntuacion()
        if si_des:
            ico_g = grp_no
            ico_m = ico_no
        else:
            ico_g = grp_si
            ico_m = ico_si
        submenu = submenu_rival.submenu(name, ico_g)

        for rv in grupo.li_rivales:
            si_actual = rv.key == rival.key
            ico = ico_actual if si_actual else ico_m
            name = rv.nombre_ext() if rv.is_type_external() else rv.name
            submenu.opcion(
                f"MT_{rv.key}",
                "%s: [%d %s]" % (name, dbm.get_puntos_rival(rv.key), _("pts")),
                ico,
                si_des or si_actual,
            )
        submenu_rival.separador()

    # ---------- CATEGORIAS
    ant = 1
    for x in range(6):
        cat = categorias.number(x)
        txt = cat.name()
        nm = cat.level_done

        nh = cat.hecho

        if nm > 0:
            txt += f" {TrListas.level(nm)}"
        if nh:
            if "B" in nh:
                txt += " +%s:%d" % (_("White"), nm + 1)
            if "N" in nh:
                txt += " +%s:%d" % (_("Black"), nm + 1)

        siset_disabled = ant == 0
        ant = nm
        menu.opcion(str(x), txt, cat.icono(), is_disabled=siset_disabled, font_type=font_normal)

    menu.separador()
    menu.opcion(
        None,
        f'{_("Total score")}: {dbm.puntuacion()} {_("pts")}',
        Iconos.MoverMas(),
        font_type=font_bold,
    )
    menu.separador()
    menu.opcion("get_help", _("Help"), Iconos.Ayuda(), font_type=font_normal)

    cursor = QtGui.QCursor.pos()
    resp = menu.lanza()
    if resp is None:
        return None
    elif resp == "get_help":
        titulo = _("Competition")
        ancho, alto = ScreenUtils.desktop_size()
        ancho = min(ancho, 700)
        txt = _(
            "<br><b>The aim is to obtain the highest possible score</b> :<ul><li>The current point score is displayed in the title bar.</li><li>To obtain points it is necessary to win on different levels in different categories.</li><li>To overcome a level it is necessary to win against the engine with white and with black.</li><li>The categories are ranked in the order of the following table:</li><ul><li><b>Beginner</b> : 5</li><li><b>Amateur</b> : 10</li><li><b>Candidate Master</b> : 20</li><li><b>Master</b> : 40</li><li><b>International Master</b> : 80</li><li><b>Grandmaster</b> : 160</li></ul><li>The score for each game is calculated by multiplying the playing level with the score of the category.</li><li>The engines are divided into groups.</li><li>To be able to play with an opponent of a particular group a minimum point score is required. The required score is shown next to the group label.</li></ul>"
        )
        QTDialogs.info(w_parent, Code.lucas_chess, titulo, txt, ancho, Iconos.pmAyudaGR())
        return None

    elif resp.startswith("MT_"):
        dbm.set_current_rival_key(resp[3:])
        QtGui.QCursor.setPos(cursor)
        return dame_categoria(w_parent)
    else:
        categoria = categorias.number(int(resp))
        return rival, categorias, categoria


class WDatos(QtWidgets.QDialog):
    def __init__(self, w_parent, rival, categorias, categoria):
        super(WDatos, self).__init__(w_parent)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.setWindowTitle(_("New game"))
        self.setWindowIcon(Iconos.Datos())
        self.setWindowFlags(QtCore.Qt.WindowType.Dialog | QtCore.Qt.WindowType.WindowTitleHint)

        tb = QTDialogs.tb_accept_cancel(self)

        f = Controles.FontType(puntos=12, peso=75)
        flb = Controles.FontType(puntos=10)

        self.max_level, self.maxNivelHecho, self.max_puntos = categorias.max_level_by_category(categoria)
        self.nivel = None
        self.is_white = None
        self.puntos = 0

        self.ed = Controles.SB(self, self.max_level, 1, self.max_level).relative_width(40)
        lb = Controles.LB(self, f"{categoria.name()} {_('Level')}")

        lb.set_font(f)
        self.lbPuntos = Controles.LB(self).align_right()
        self.ed.valueChanged.connect(self.level_changed)

        is_white = not categoria.done_with_white()
        self.rb_white = QtWidgets.QRadioButton(_("White"))
        self.rb_white.setChecked(is_white)
        self.rb_black = QtWidgets.QRadioButton(_("Black"))
        self.rb_black.setChecked(not is_white)

        self.rb_white.clicked.connect(self.set_max_score)
        self.rb_black.clicked.connect(self.set_max_score)

        # Rival
        lb_r_motor = (
            Controles.LB(self, f'<b>{_("Engine")}</b> : {rival.name}').set_font(flb).set_wrap().relative_width(400)
        )
        lb_r_autor = (
            Controles.LB(self, f'<b>{_("Author")}</b> : {rival.autor}').set_font(flb).set_wrap().relative_width(400)
        )
        lb_r_web = (
            Controles.LB(self, f'<b>{_("Web")}</b> : <a href="{rival.url}">{rival.url}</a>')
            .set_wrap()
            .relative_width(400)
            .set_font(flb)
        )

        ly = Colocacion.V().control(lb_r_motor).control(lb_r_autor).control(lb_r_web).margen(10)
        gb_r = Controles.GB(self, _("Opponent"), ly).set_font(f)

        # Tutor
        tutor = Code.configuration.engines.engine_tutor()
        lb_t_motor = (
            Controles.LB(self, f'<b>{_("Engine")}</b> : {tutor.name}').set_font(flb).set_wrap().relative_width(400)
        )
        lb_t_autor = (
            Controles.LB(self, f'<b>{_("Author")}</b> : {tutor.autor}').set_font(flb).set_wrap().relative_width(400)
        )
        ly = Colocacion.V().control(lb_t_motor).control(lb_t_autor)

        if hasattr(tutor, "url"):
            lb_t_web = (
                Controles.LB(self, f'<b>Web</b> : <a href="{tutor.url}">{tutor.url}</a>')
                .set_wrap()
                .relative_width(400)
                .set_font(flb)
            )
            ly.control(lb_t_web)

        ly.margen(10)
        gb_t = Controles.GB(self, _("Tutor"), ly).set_font(f)

        hbox = Colocacion.H().relleno().control(self.rb_white).espacio(10).control(self.rb_black).relleno()
        gb_color = Controles.GB(self, _("Side you play with"), hbox).set_font(f)

        ly_nivel = Colocacion.H().control(lb).control(self.ed).espacio(10).control(self.lbPuntos).relleno()

        vlayout = (
            Colocacion.V()
            .otro(ly_nivel)
            .espacio(10)
            .control(gb_color)
            .espacio(10)
            .control(gb_r)
            .espacio(10)
            .control(gb_t)
            .margen(30)
        )

        layout = Colocacion.V().control(tb).otro(vlayout).margen(3)

        self.setLayout(layout)

        self.set_max_score()

    def aceptar(self):
        self.nivel = self.ed.value()
        self.is_white = self.rb_white.isChecked()
        self.accept()

    def level_changed(self, _nuevo):
        self.set_max_score()

    def set_max_score(self):
        p = 0
        if self.ed.value() >= self.max_level:
            color = "B" if self.rb_white.isChecked() else "N"
            if color not in self.maxNivelHecho:
                p = self.max_puntos
        self.lbPuntos.setText(f'{p} {_("points")}')
        self.puntos = p


def edit_training_position(w_parent, titulo, to_sq, etiqueta=None, pos=None, additional_message=None):
    w = WNumEntrenamiento(w_parent, titulo, to_sq, etiqueta, pos, additional_message)
    return w.number if w.exec() else None


class WNumEntrenamiento(QtWidgets.QDialog):
    number: int

    def __init__(self, w_parent, titulo, to_sq, etiqueta=None, pos=None, additional_message=None):
        super(WNumEntrenamiento, self).__init__(w_parent)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.setFont(Controles.FontType(puntos=Code.configuration.x_sizefont_infolabels))

        self.setWindowTitle(titulo)
        self.setWindowIcon(Iconos.Datos())

        tb = QTDialogs.tb_accept_cancel(self)

        if pos is None:
            pos = 1  # random.randint( 1, to_sq )

        if etiqueta is None:
            etiqueta = _("Training unit")

        self.ed, lb = QTMessages.spinbox_lb(self, pos, 1, to_sq, etiqueta=etiqueta, max_width=60)
        lb1 = Controles.LB(self, "/ %d" % to_sq)

        ly_h = Colocacion.H().relleno().control(lb).control(self.ed).control(lb1).relleno().margen(15)

        ly_v = Colocacion.V().control(tb).otro(ly_h)
        if additional_message:
            lb2 = Controles.LB(self, additional_message)
            lb2.set_wrap().minimum_width(250)
            lyb2 = Colocacion.H().control(lb2).margen(15)
            ly_v.otro(lyb2)
        ly_v.margen(3)

        self.setLayout(ly_v)

        self.resultado = None

    def aceptar(self):
        self.number = self.ed.value()
        self.accept()
