import collections
import os
import shutil

from PySide6 import QtCore, QtGui, QtSvg
from PySide6.QtSvgWidgets import QSvgWidget

import Code
import itertools
from Code.Z import Util
from Code.Base.Constantes import BLINDFOLD_BLACK, BLINDFOLD_CONFIG, BLINDFOLD_WHITE
from Code.QT import Colocacion, Controles, FormLayout, Iconos, LCDialog, QTDialogs
from Code.Translations import TrListas

DEFAULT_PIECES = "Cburnett"


def is_only_board(name) -> bool:
    fich = Code.path_resource("Pieces", name, "only_board")
    return os.path.isfile(fich)


class ConjuntoPiezas:
    def __init__(self, name):
        self.name = name
        self.dic_pieces = self.read_pieces(name)

    def is_only_board(self):
        return is_only_board(self.name)

    @staticmethod
    def get_default():
        return ConjuntoPiezas(DEFAULT_PIECES)

    def read_pieces(self, name):
        try:
            dic = {}
            for pieza in "rnbqkpRNBQKP":
                fich = Code.path_resource(
                    "Pieces",
                    name,
                    f"{'w' if pieza.isupper() else 'b'}{pieza.lower()}.svg",
                )
                with open(fich, "rb") as f:
                    qb = QtCore.QByteArray(f.read())
                dic[pieza] = qb
            return dic
        except:
            return self.read_pieces(DEFAULT_PIECES)

    def render(self, pieza):
        return QtSvg.QSvgRenderer(self.dic_pieces[pieza])

    def widget(self, pieza):
        w = QSvgWidget()
        w.load(self.dic_pieces[pieza])
        return w

    def pixmap(self, pieza, tam=24):
        pm = QtGui.QPixmap(tam, tam)
        pm.fill(QtCore.Qt.GlobalColor.transparent)
        render = self.render(pieza)
        painter = QtGui.QPainter()
        painter.begin(pm)
        render.render(painter)
        painter.end()
        return pm

    def label(self, owner, pieza, tam):
        pm = self.pixmap(pieza, tam)
        lb = Controles.LB(owner)
        lb.put_image(pm)
        lb.pieza = pieza
        lb.tam_pieza = tam
        return lb

    def change_label(self, lb, tam):
        if lb.tam_pieza != tam:
            pm = self.pixmap(lb.pieza, tam)
            lb.put_image(pm)

    def icono(self, pieza):
        icon = QtGui.QIcon(self.pixmap(pieza, 32))
        return icon

    def cursor(self, pieza):
        return QtGui.QCursor(self.pixmap(pieza))

    def change_set(self, new):
        self.name = new
        self.dic_pieces = self.read_pieces(new)


class AllPieces:
    def __init__(self):
        self.dicConjuntos = {}

    def selecciona(self, name):
        if name in self.dicConjuntos:
            return self.dicConjuntos[name]
        else:
            return self.nuevo(name)

    def nuevo(self, name):
        self.dicConjuntos[name] = ConjuntoPiezas(name)
        return self.dicConjuntos[name]

    def icono(self, pieza, name, width=32):
        pm = self.pixmap(pieza, name, width)
        return QtGui.QIcon(pm)

    def pixmap(self, pieza, name, width):
        fich = Code.path_resource("Pieces", name, f'{"w" if pieza.isupper() else "b"}{pieza.lower()}.svg')
        pm = QtGui.QPixmap(width, width)
        pm.fill(QtCore.Qt.GlobalColor.transparent)
        render = QtSvg.QSvgRenderer(fich)
        painter = QtGui.QPainter()
        painter.begin(pm)
        render.render(painter)
        painter.end()
        return pm

    def default_icon(self, pieza, width=32):
        return self.icono(pieza, DEFAULT_PIECES, width)

    def default_pixmap(self, pieza, width):
        return self.pixmap(pieza, DEFAULT_PIECES, width)

    def save_all_png(self, name, px):
        if is_only_board(name):
            name = DEFAULT_PIECES
        folder_to_save = Code.configuration.paths.folder_pieces_png()

        for pieza, color in itertools.product("pnbrqk", "wb"):
            path_file = Code.path_resource("Pieces", name, f"{color}{pieza}.svg")
            render = QtSvg.QSvgRenderer(path_file)
            painter = QtGui.QPainter()
            pm = QtGui.QPixmap(px, px)
            pm.fill(QtCore.Qt.GlobalColor.transparent)
            painter.begin(pm)
            render.render(painter)
            painter.end()
            path = Util.opj(folder_to_save, f"{color}{pieza}.png")
            pm.save(path, "PNG")


HIDE, GREY, CHECKER, SHOW = range(4)


class BlindfoldConfig:
    def __init__(self, nom_pieces_ori, dic_pieces=None):
        self.nom_pieces_ori = nom_pieces_ori
        if dic_pieces is None:
            self.restore()
        else:
            self.dic_pieces = dic_pieces

    def base_file(self, pz, is_white):
        pz = pz.lower()
        if is_white:
            pz_t = pz.upper()
        else:
            pz_t = pz
        tipo = self.dic_pieces[pz_t]
        if tipo == SHOW:
            pz = ("w" if is_white else "b") + pz
            return Code.path_resource("Pieces", self.nom_pieces_ori, f"{pz}.svg")
        if tipo == HIDE:
            fich = "h"
        elif tipo == GREY:
            fich = "g"
        elif tipo == CHECKER:
            fich = "w" if is_white else "b"
        else:
            return None
        return Code.path_resource("IntFiles/Svg", f"blind_{fich}.svg")

    def restore(self):
        self.dic_pieces = Code.configuration.read_variables("BLINDFOLD")
        if not self.dic_pieces:
            for pieza in "rnbqkpRNBQKP":
                self.dic_pieces[pieza] = HIDE

    def save(self):
        dic: dict = Code.configuration.read_variables("BLINDFOLD")
        dic.update(self.dic_pieces)
        Code.configuration.write_variables("BLINDFOLD", dic)

    def list_saved(self):
        return [k[1:] for k in self.dic_pieces if k.startswith("_")]

    def remove(self, name):
        del self.dic_pieces[f"_{name}"]
        Code.configuration.write_variables("BLINDFOLD", self.dic_pieces)

    def add_current(self, name):
        kdic = {k: v for k, v in self.dic_pieces.items() if not k.startswith("_")}
        self.dic_pieces[f"_{name}"] = kdic
        Code.configuration.write_variables("BLINDFOLD", self.dic_pieces)

    def saved(self, name):
        return self.dic_pieces[f"_{name}"]


class Blindfold(ConjuntoPiezas):
    config_bf = None

    def __init__(self, nom_pieces_ori, tipo=BLINDFOLD_CONFIG):
        self.name = "BlindFold"
        self.carpetaBF = Util.opj(Code.configuration.paths.folder_userdata(), "BlindFoldPieces")
        self.carpetaPZ = Code.path_resource("IntFiles")
        self.tipo = tipo
        self.reset(nom_pieces_ori)

    def read_pieces(self, name=None):  # name usado por compatibilidad
        dic = {}
        for pieza in "rnbqkpRNBQKP":
            fich = Util.opj(
                self.carpetaBF,
                f"{'w' if pieza.isupper() else 'b'}{pieza.lower()}.svg",
            )
            with open(fich, "rb") as f:
                qb = QtCore.QByteArray(f.read())
            dic[pieza] = qb
        return dic

    def reset(self, nom_pieces_ori):
        if self.tipo == BLINDFOLD_CONFIG:
            dic_t_piezas = None
        else:
            w = b = HIDE
            if self.tipo == BLINDFOLD_WHITE:
                b = SHOW
            elif self.tipo == BLINDFOLD_BLACK:
                w = SHOW
            dic_t_piezas = {}
            for pieza in "rnbqkp":
                dic_t_piezas[pieza] = b
                dic_t_piezas[pieza.upper()] = w
        self.config_bf = BlindfoldConfig(nom_pieces_ori, dic_pieces=dic_t_piezas)
        if not os.path.isdir(self.carpetaBF):
            Util.create_folder(self.carpetaBF)

        for siWhite in (True, False):
            for pieza in "rnbqkp":
                ori = self.config_bf.base_file(pieza, siWhite)
                bs = "w" if siWhite else "b"
                dest = Util.opj(self.carpetaBF, f"{bs}{pieza}.svg")
                shutil.copy(ori, dest)

        self.dic_pieces = self.read_pieces()


class WBlindfold(LCDialog.LCDialog):
    def __init__(self, owner, nom_pieces_ori):

        titulo = f"{_('Blindfold chess')} - {_('Configuration')}"
        icono = Iconos.Ojo()
        extparam = "wblindfold"
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, extparam)

        self.config = BlindfoldConfig(nom_pieces_ori)
        self.nom_pieces_ori = nom_pieces_ori

        lb_white = Controles.LB(self, _("White")).set_font_type(peso=75, puntos=10)
        lb_black = Controles.LB(self, _("Black")).set_font_type(peso=75, puntos=10)

        self.dicWidgets = collections.OrderedDict()
        self.dicImgs = {}

        li_options = (
            (_("Hide"), HIDE),
            (_("Green"), GREY),
            (_("Checker"), CHECKER),
            (_("Show"), SHOW),
        )
        dic_nom_piezas = TrListas.dic_nom_pieces()

        def haz(xpz):
            tp_w = self.config.dic_pieces[xpz.upper()]
            tp_b = self.config.dic_pieces[xpz]
            xlb_pz_w = Controles.LB(self)
            xcb_pz_w = Controles.CB(self, li_options, tp_w).capture_changes(self.reset)
            xlb_pz = Controles.LB(self, dic_nom_piezas[xpz.upper()]).set_font_type(peso=75, puntos=10)
            xlb_pz_b = Controles.LB(self)
            xcb_pz_b = Controles.CB(self, li_options, tp_b).capture_changes(self.reset)
            self.dicWidgets[xpz] = [
                xlb_pz_w,
                xcb_pz_w,
                xlb_pz,
                xlb_pz_b,
                xcb_pz_b,
                None,
                None,
            ]

        for pz in "kqrbnp":
            haz(pz)

        bt_all_w = Controles.PB(self, _("All White"), self.all_white, plano=False)
        self.cbAll = Controles.CB(self, li_options, HIDE)
        bt_all_b = Controles.PB(self, _("All Black"), self.all_black, plano=False)

        bt_swap = Controles.PB(self, _("Swap"), self.swap, plano=False)

        tb = QTDialogs.LCTB(self)
        tb.new(_("Save"), Iconos.Grabar(), self.grabar)
        tb.new(_("Cancel"), Iconos.Cancelar(), self.cancelar)
        tb.new(_("Configurations"), Iconos.Opciones(), self.configurations)

        ly = Colocacion.G()
        ly.controlc(lb_white, 0, 1).controlc(lb_black, 0, 3)
        row = 1
        for pz in "kqrbnp":
            lb_pz_w, cb_pz_w, lb_pz, lb_pz_b, cb_pz_b, tipo_w, tipo_b = self.dicWidgets[pz]
            ly.control(cb_pz_w, row, 0)
            ly.controlc(lb_pz_w, row, 1)
            ly.controlc(lb_pz, row, 2)
            ly.controlc(lb_pz_b, row, 3)
            ly.control(cb_pz_b, row, 4)
            row += 1

        ly.empty_row(row, 20)
        row += 1

        ly.controld(bt_all_w, row, 0, 1, 2)
        ly.control(self.cbAll, row, 2)
        ly.control(bt_all_b, row, 3, 1, 2)
        ly.controlc(bt_swap, row + 1, 0, 1, 5)
        ly.margen(20)

        layout = Colocacion.V().control(tb).otro(ly)

        self.setLayout(layout)

        self.reset()

    def closeEvent(self, event):
        self.save_video()

    def grabar(self):
        self.save_video()
        self.config.save()
        self.accept()

    def cancelar(self):
        self.save_video()
        self.reject()

    def configurations(self):
        menu = QTDialogs.LCMenu(self)
        li_saved = self.config.list_saved()
        for name in li_saved:
            menu.opcion((True, name), name, Iconos.PuntoAzul())
        menu.separador()
        menu.opcion((True, None), _("Save current configuration"), Iconos.PuntoVerde())
        if li_saved:
            menu.separador()
            menudel = menu.submenu(_("Remove"), Iconos.Delete())
            for name in li_saved:
                menudel.opcion((False, name), name, Iconos.PuntoNegro())

        resp = menu.lanza()
        if resp is None:
            return

        si, cual = resp

        if si:
            if cual:
                dpz = self.config.saved(cual)
                for pz in "kqrbnp":
                    lb_pz_w, cb_pz_w, lb_pz, lb_pz_b, cb_pz_b, tipo_w, tipo_b = self.dicWidgets[pz]
                    cb_pz_w.set_value(dpz[pz.upper()])
                    cb_pz_b.set_value(dpz[pz])
                self.reset()
            else:
                li_gen = [(None, None), (f"{_('Name')}:", "")]

                resultado = FormLayout.fedit(
                    li_gen,
                    title=_("Save current configuration"),
                    parent=self,
                    minimum_width=460,
                    icon=Iconos.TutorialesCrear(),
                )
                if resultado is None:
                    return

                accion, li_resp = resultado
                name = li_resp[0].strip()
                if not name:
                    return
                self.config.add_current(name)
        else:
            self.config.remove(cual)

    # def configurations1(self):
    #     dic = Code.configuration.read_variables("BLINDFOLD")
    #     dicConf = collections.OrderedDict()
    #     for k in dic:
    #         if k.startswith("_"):
    #             cl = k[1:]
    #             dicConf[cl] = dic[k]
    #
    #     menu = QTDialogs.LCMenu(self)
    #     for k in dicConf:
    #         menu.opcion((True, k), k, Iconos.PuntoAzul())
    #     menu.separador()
    #     menu.opcion((True, None), _("Save current configuration"), Iconos.PuntoVerde())
    #     if dicConf:
    #         menu.separador()
    #         menudel = menu.submenu(_("Remove"), Iconos.Delete())
    #         for k in dicConf:
    #             menudel.opcion((False, k), k, Iconos.PuntoNegro())
    #
    #     resp = menu.lanza()
    #     if resp is None:
    #         return
    #
    #     si, cual = resp
    #
    #     if si:
    #         if cual:
    #             dpz = dic["_" + cual]
    #             for pz in "kqrbnp":
    #                 lb_pz_w, cb_pz_w, lb_pz, lb_pz_b, cb_pz_b, tipo_w, tipo_b = self.dicWidgets[pz]
    #                 cb_pz_w.set_value(dpz[pz.upper()])
    #                 cb_pz_b.set_value(dpz[pz])
    #             self.reset()
    #         else:
    #             li_gen = [(None, None)]
    #             li_gen.append((_("Name") + ":", ""))
    #
    #             resultado = FormLayout.fedit(
    #                 li_gen,
    #                 title=_("Save current configuration"),
    #                 parent=self,
    #                 minimum_width=460,
    #                 icon=Iconos.TutorialesCrear(),
    #             )
    #             if resultado is None:
    #                 return None
    #
    #             accion, li_resp = resultado
    #             name = li_resp[0].strip()
    #             if not name:
    #                 return None
    #             dic["_%s" % name] = self.config.dic_pieces
    #             Code.configuration.write_variables("BLINDFOLD", dic)
    #     else:
    #         del dic["_%s" % cual]
    #         Code.configuration.write_variables("BLINDFOLD", dic)

    def all_white(self):
        tp = self.cbAll.valor()
        for pzB in "rnbqkp":
            lb_pz_w, cb_pz_w, lb_pz, lb_pz_b, cb_pz_b, tipo_w, tipo_b = self.dicWidgets[pzB]
            cb_pz_w.set_value(tp)
        self.reset()

    def all_black(self):
        tp = self.cbAll.valor()
        for pzB in "rnbqkp":
            lb_pz_w, cb_pz_w, lb_pz, lb_pz_b, cb_pz_b, tipo_w, tipo_b = self.dicWidgets[pzB]
            cb_pz_b.set_value(tp)
        self.reset()

    def swap(self):
        for pzB in "rnbqkp":
            lb_pz_w, cb_pz_w, lb_pz, lb_pz_b, cb_pz_b, tipo_w, tipo_b = self.dicWidgets[pzB]
            tp_b = cb_pz_b.valor()
            tp_w = cb_pz_w.valor()
            cb_pz_b.set_value(tp_w)
            cb_pz_w.set_value(tp_b)
        self.reset()

    def reset(self):
        for pzB in "kqrbnp":
            lb_pz_w, cb_pz_w, lb_pz, lb_pz_b, cb_pz_b, tipo_w, tipo_b = self.dicWidgets[pzB]
            tipo_nv = cb_pz_w.valor()
            if tipo_w != tipo_nv:
                pz_w = pzB.upper()
                self.config.dic_pieces[pz_w] = tipo_nv
                self.dicWidgets[pzB][5] = tipo_nv  # tiene que ser pzB que esta en misnusculas
                fich = self.config.base_file(pzB, True)
                if fich in self.dicImgs:
                    pm = self.dicImgs[fich]
                else:
                    pm = QTDialogs.fsvg2pm(fich, 32)
                    self.dicImgs[fich] = pm
                lb_pz_w.put_image(pm)
            tipo_nv = cb_pz_b.valor()
            if tipo_b != tipo_nv:
                self.config.dic_pieces[pzB] = tipo_nv
                self.dicWidgets[pzB][6] = tipo_nv
                fich = self.config.base_file(pzB, False)
                if fich in self.dicImgs:
                    pm = self.dicImgs[fich]
                else:
                    pm = QTDialogs.fsvg2pm(fich, 32)
                    self.dicImgs[fich] = pm
                lb_pz_b.put_image(pm)
