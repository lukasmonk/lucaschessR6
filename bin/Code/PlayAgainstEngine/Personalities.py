from Code.Base.Constantes import (
    ADJUST_BETTER,
    ADJUST_HIGH_LEVEL,
    ADJUST_INTERMEDIATE_LEVEL,
    ADJUST_LOW_LEVEL,
    ADJUST_SELECTED_BY_PLAYER,
    ADJUST_SIMILAR,
    ADJUST_SOMEWHAT_BETTER,
    ADJUST_SOMEWHAT_BETTER_MORE,
    ADJUST_SOMEWHAT_BETTER_MORE_MORE,
    ADJUST_SOMEWHAT_WORSE_LESS,
    ADJUST_SOMEWHAT_WORSE_LESS_LESS,
    ADJUST_WORSE,
    ADJUST_WORST_MOVE,
    BOOK_BEST_MOVE,
    BOOK_RANDOM_PROPORTIONAL,
    BOOK_RANDOM_UNIFORM,
    SELECTED_BY_PLAYER,
)
from Code.QT import Controles, FormLayout, Iconos, QTDialogs, QTMessages


class Personalities:
    def __init__(self, owner, configuration):
        self.owner = owner
        self.configuration = configuration

    def list_personalities(self, si_todos):
        li_ajustes = [
            (_("Best move"), ADJUST_BETTER),
            (f"{_('Somewhat better')}++", ADJUST_SOMEWHAT_BETTER_MORE_MORE),
            (f"{_('Somewhat better')}+", ADJUST_SOMEWHAT_BETTER_MORE),
            (_("Somewhat better"), ADJUST_SOMEWHAT_BETTER),
            (_("Similar to the player"), ADJUST_SIMILAR),
            (_("Somewhat worse"), ADJUST_WORSE),
            (f"{_('Somewhat worse')}-", ADJUST_SOMEWHAT_WORSE_LESS),
            (f"{_('Somewhat worse')}--", ADJUST_SOMEWHAT_WORSE_LESS_LESS),
            (_("Worst move"), ADJUST_WORST_MOVE),
            ("-" * 30, None),
            (_("High level"), ADJUST_HIGH_LEVEL),
            (_("Intermediate level"), ADJUST_INTERMEDIATE_LEVEL),
            (_("Low level"), ADJUST_LOW_LEVEL),
            ("-" * 30, None),
            (_("Move selected by the player"), ADJUST_SELECTED_BY_PLAYER),
        ]
        if si_todos and self.configuration.li_personalities:
            li_ajustes.append(("-" * 30, None))
            for num, una in enumerate(self.configuration.li_personalities):
                li_ajustes.append((una["NOMBRE"], 1000 + num))
        return li_ajustes

    @staticmethod
    def list_personalities_minimum():
        li_ajustes = [
            (_("Best move"), ADJUST_BETTER),
            (_("Move selected by the player"), ADJUST_SELECTED_BY_PLAYER),
        ]
        return li_ajustes

    def label(self, n_ajuste):
        for lb, n in self.list_personalities(True):
            if n == n_ajuste:
                return lb
        return ""

    def edit(self, una, icono):
        if una is None:
            una = {}

        width_field = Controles.calc_fixed_width(50)

        # Datos basicos
        li_gen: list = [(None, None)]
        li_gen.append((FormLayout.Editbox(_("Name")), una.get("NOMBRE", "")))

        li_gen.append((None, None))

        config = FormLayout.Fichero(_("Debug file"), "txt", True)
        li_gen.append((config, una.get("DEBUG", "")))

        li_gen.append((None, None))

        li_gen.append((None, _("Serious errors, select the best move if:")))
        li_gen.append(
            (
                FormLayout.Editbox(_("Mate is less than or equal to"), tipo=int, ancho=width_field),
                una.get("MAXMATE", 0),
            )
        )
        li_gen.append(
            (
                FormLayout.Editbox(
                    _("The loss of centipawns is greater than"),
                    tipo=int,
                    ancho=width_field,
                ),
                una.get("MINDIFPUNTOS", 0),
            )
        )
        li_gen.append((None, None))
        li_gen.append(
            (
                FormLayout.Editbox(
                    _("Max. loss of centipawns per move by the <br> engine to reach a leveled evaluation"),
                    tipo=int,
                    ancho=width_field,
                ),
                una.get("ATERRIZAJE", width_field),
            )
        )

        # Opening
        li_a: list = [(None, None)]

        config = FormLayout.Fichero(_("Polyglot book"), "bin", False)
        li_a.append((config, una.get("BOOK", "")))

        li_resp_book = [
            (_("Always the highest percentage"), BOOK_BEST_MOVE),
            (_("Proportional random"), BOOK_RANDOM_PROPORTIONAL),
            (_("Uniform random"), BOOK_RANDOM_UNIFORM),
            (_("Selected by the player"), SELECTED_BY_PLAYER),
        ]
        li_a.append(
            (
                FormLayout.Combobox(_("Book selection mode"), li_resp_book),
                una.get("BOOKRR", BOOK_BEST_MOVE),
            )
        )

        # Medio juego
        li_mj: list = [(None, None)]

        # # Ajustar
        li_mj.append(
            (
                FormLayout.Combobox(_("Strength"), self.list_personalities(False)),
                una.get("ADJUST", ADJUST_BETTER),
            )
        )

        # Movimiento siguiente
        li_mj.append((None, _("In the next move")))

        trlista_sg = [
            _("To move a pawn"),
            _("Advance piece"),
            _("Make check"),
            _("Capture"),
        ]
        lista_sg = ["MOVERPEON", "AVANZARPIEZA", "JAQUE", "CAPTURAR"]
        for n, opcion in enumerate(lista_sg):
            li_mj.append(
                (
                    FormLayout.Spinbox(trlista_sg[n], -2000, +2000, width_field),
                    una.get(opcion, 0),
                )
            )

        # Movimientos previstos
        li_mj.append((None, _("In the expected moves")))
        trlista_pr = [
            _("Keep the two bishops"),
            _("Advance"),
            _("Make check"),
            _("Capture"),
        ]
        lista_pr = ["2B", "AVANZAR", "JAQUE", "CAPTURAR"]
        for n, opcion in enumerate(lista_pr):
            li_mj.append(
                (
                    FormLayout.Spinbox(trlista_pr[n], -2000, +2000, width_field),
                    una.get(f"{opcion}PR", 0),
                )
            )

        # Final
        li_f: list = [(None, None)]

        # Ajustar
        li_f.append(
            (
                FormLayout.Combobox(_("Strength"), self.list_personalities(False)),
                una.get("AJUSTARFINAL", ADJUST_BETTER),
            )
        )

        li_f.append(
            (
                FormLayout.Spinbox(_("Maximum pieces at this stage"), 0, 32, width_field),
                una.get("MAXPIEZASFINAL", 0),
            )
        )
        li_f.append((None, None))

        # Movimiento siguiente
        li_f.append((None, _("In the next move")))
        for n, opcion in enumerate(lista_sg):
            li_f.append(
                (
                    FormLayout.Spinbox(trlista_sg[n], -2000, +2000, width_field),
                    una.get(f"{opcion}F", 0),
                )
            )

        # Movimientos previstos
        li_f.append((None, _("In the expected moves")))
        for n, opcion in enumerate(lista_pr):
            li_f.append(
                (
                    FormLayout.Spinbox(trlista_pr[n], -2000, +2000, width_field),
                    una.get(f"{opcion}PRF", 0),
                )
            )

        while True:
            lista = []
            lista.append((li_gen, _("Basic data"), ""))
            lista.append((li_a, _("Opening"), ""))
            lista.append((li_mj, _("Middlegame"), ""))
            lista.append((li_f, _("Endgame"), ""))
            resultado = FormLayout.fedit(
                lista,
                title=_("Personalities"),
                parent=self.owner,
                minimum_width=460,
                icon=icono,
            )
            if resultado:
                accion, li_resp = resultado
                li_gen_r, li_ar, li_mjr, li_fr = li_resp

                name = li_gen_r[0].strip()

                if not name:
                    QTMessages.message_error(self.owner, _("Name missing"))
                    continue

                una = {}
                # Base
                una["NOMBRE"] = name
                una["DEBUG"] = li_gen_r[1]
                una["MAXMATE"] = li_gen_r[2]
                una["MINDIFPUNTOS"] = li_gen_r[3]
                una["ATERRIZAJE"] = li_gen_r[4]

                # Opening
                una["BOOK"] = li_ar[0]
                una["BOOKRR"] = li_ar[1]

                # Medio
                una["ADJUST"] = li_mjr[0]

                for num, opcion in enumerate(lista_sg):
                    una[opcion] = li_mjr[num + 1]

                n_sg = len(lista_sg) + 1
                for num, opcion in enumerate(lista_pr):
                    una[f"{opcion}PR"] = li_mjr[num + n_sg]

                # Final
                una["AJUSTARFINAL"] = li_fr[0]
                una["MAXPIEZASFINAL"] = li_fr[1]

                for num, opcion in enumerate(lista_sg):
                    una[f"{opcion}F"] = li_fr[num + 2]

                n_sg = len(lista_sg) + 2
                for num, opcion in enumerate(lista_pr):
                    una[f"{opcion}PRF"] = li_fr[num + n_sg]

                return una

            return None

    def lanza_menu(self):
        menu = QTDialogs.LCMenu(self.owner)
        # f = Controles.FontType(puntos=8, peso=75)
        # menu.set_font(f)
        ico_crear = Iconos.Mas()
        ico_editar = Iconos.ModificarP()
        ico_borrar = Iconos.Delete()
        ico_verde = Iconos.PuntoVerde()
        ico_rojo = Iconos.PuntoNaranja()

        menu.opcion(("c", None), _("New personality"), ico_crear)

        li_personalities = self.configuration.li_personalities
        if li_personalities:
            menu.separador()
            menu_mod = menu.submenu(_("Edit"), ico_editar)
            for num, una in enumerate(li_personalities):
                menu_mod.opcion(("e", num), una["NOMBRE"], ico_verde)
            menu.separador()
            menu_bor = menu.submenu(_("Remove"), ico_borrar)
            for num, una in enumerate(li_personalities):
                menu_bor.opcion(("b", num), una["NOMBRE"], ico_rojo)
        resp = menu.lanza()
        if resp:
            si_rehacer = False
            accion, num = resp
            if accion == "c":
                una = self.edit(None, ico_crear)
                if una:
                    li_personalities.append(una)
                    si_rehacer = True
            elif accion == "e":
                una = self.edit(li_personalities[num], ico_editar)
                if una:
                    li_personalities[num] = una
                    si_rehacer = True
            elif accion == "b":
                if QTMessages.pregunta(self.owner, _X(_("Delete %1?"), li_personalities[num]["NOMBRE"])):
                    del li_personalities[num]
                    si_rehacer = True

            if si_rehacer:
                self.configuration.graba()
                return True
        return False
