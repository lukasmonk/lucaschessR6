import copy
import os

from PySide6 import QtCore, QtWidgets

import Code
from Code.Z import Util
from Code.Board import Board, BoardTypes
from Code.Director import TabVisual
from Code.QT import (
    Colocacion,
    Columnas,
    Controles,
    FormLayout,
    Grid,
    Iconos,
    LCDialog,
    QTDialogs,
    QTMessages,
    QTUtils,
    SelectFiles,
)

estrellaSVG = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!-- Created with Inkscape (https://www.inkscape.org/) -->

<svg
   xmlns:dc="https://purl.org/dc/elements/1.1/"
   xmlns:cc="https://creativecommons.org/ns#"
   xmlns:rdf="https://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="https://www.w3.org/2000/svg"
   xmlns="https://www.w3.org/2000/svg"
   version="1.1"
   width="64"
   height="64"
   id="svg2996">
  <defs
     id="defs2998" />
  <metadata
     id="metadata3001">
    <rdf:RDF>
      <cc:Work
         rdf:about="">
        <dc:format>image/svg+xml</dc:format>
        <dc:type
           rdf:resource="https://purl.org/dc/dcmitype/StillImage" />
        <dc:title></dc:title>
      </cc:Work>
    </rdf:RDF>
  </metadata>
  <g
     id="layer1">
    <path
       d="M 27.169733,29.728386 C 25.013244,32.2821 14.66025,23.129153 11.578235,24.408078 8.4962206,25.687003 6.6393909,39.1341 3.3071401,38.993129 -0.02511049,38.852157 0.91445325,26.949682 -1.9446847,25.158604 c -2.8591381,-1.791078 -15.0810253,3.34372 -17.0117283,0.569017 -1.930702,-2.774702 8.403637,-10.308248 8.19374,-13.566752 -0.209897,-3.2585049 -10.936253,-10.0036344 -9.712288,-13.06583173 1.223964,-3.06219717 12.0590479,-0.21386597 14.474209,-2.52953107 2.4151612,-2.3156652 0.7741756,-15.3362732 3.9137487,-16.2517622 3.139573,-0.915489 6.1950436,10.0329229 9.4593203,10.280471 3.264277,0.2475482 11.944248,-8.425366 14.803863,-6.774742 2.859615,1.650623 -1.726822,13.0796387 0.03239,15.84516339 1.759209,2.76552481 12.739744,3.15253011 13.354311,6.42891241 0.614567,3.2763822 -10.178057,6.5799722 -11.316244,9.7437452 -1.138187,3.163774 5.079588,11.337377 2.923098,13.891092 z"
       transform="matrix(1.0793664,0,0,1.021226,24.134217,21.975315)"
       id="path3024"
       style="fill:none;stroke:#136ad6;stroke-width:2.29143548;stroke-linecap:butt;stroke-linejoin:round;stroke-miterlimit:4;stroke-opacity:1;stroke-dasharray:none;stroke-dashoffset:0" />
  </g>
</svg>"""


class WTVSvg(QtWidgets.QDialog):
    def __init__(self, owner, reg_svg, xml=None, name=None):

        QtWidgets.QDialog.__init__(self, owner)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.setWindowTitle(_("Image"))
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
        )

        self.configuration = Code.configuration

        if not reg_svg:
            reg_svg = TabVisual.PSVG()
            reg_svg.xml = xml
            if name:
                reg_svg.name = name

        tb = Controles.TBrutina(self)
        tb.new(_("Save"), Iconos.Aceptar(), self.grabar)
        tb.new(_("Cancel"), Iconos.Cancelar(), self.reject)

        # Board
        config_board = owner.board.config_board
        self.board = Board.Board(self, config_board, with_director=False)
        self.board.draw_window()
        self.board.copia_posicion_de(owner.board)

        # Datos generales
        li_gen = []

        # name del svg que se usara en los menus del tutorial
        config = FormLayout.Editbox(_("Name"), ancho=120)
        li_gen.append((config, reg_svg.name))

        # ( "opacity", "n", 1.0 ),
        config = FormLayout.Dial(_("Degree of transparency"), 0, 99)
        li_gen.append((config, 100 - int(reg_svg.opacity * 100)))

        # ( "psize", "n", 100 ),
        config = FormLayout.Spinbox(f"{_('Size')} %", 1, 1600, 50)
        li_gen.append((config, reg_svg.psize))

        # orden
        config = FormLayout.Combobox(_("Order concerning other items"), QTMessages.list_zvalues())
        li_gen.append((config, reg_svg.physical_pos.orden))

        self.form = FormLayout.FormWidget(li_gen, dispatch=self.cambios)

        # Layout
        layout = Colocacion.H().control(self.form).relleno().control(self.board)
        layout1 = Colocacion.V().control(tb).otro(layout)
        self.setLayout(layout1)

        # Ejemplos
        li_movs = ["b4c4", "e2e2", "e4g7"]
        self.liEjemplos = []
        for a1h8 in li_movs:
            reg_svg.a1h8 = a1h8
            reg_svg.siMovible = True
            svg = self.board.create_svg(reg_svg, is_editing=True)
            self.liEjemplos.append(svg)

    def cambios(self):
        if hasattr(self, "form"):
            li = self.form.get()
            for n, svg in enumerate(self.liEjemplos):
                reg_svg = svg.block_data
                reg_svg.name = li[0]
                reg_svg.opacity = (100.0 - float(li[1])) / 100.0
                reg_svg.psize = li[2]
                reg_svg.physical_pos.orden = li[3]
                svg.setOpacity(reg_svg.opacity)
                svg.setZValue(reg_svg.physical_pos.orden)
                svg.update()
            self.board.escena.update()
            QTUtils.refresh_gui()

    def grabar(self):
        reg_svg = self.liEjemplos[0].block_data
        name = reg_svg.name.strip()
        if name == "":
            QTMessages.message_error(self, _("Name missing"))
            return

        self.reg_svg = reg_svg

        pm = self.liEjemplos[0].get_pixmap()
        bf = QtCore.QBuffer()
        pm.save(bf, "PNG")
        self.reg_svg.png = bytes(bf.data().data())

        self.accept()


class WTVSvgs(LCDialog.LCDialog):
    def __init__(self, owner, list_svgs, db_svgs):

        titulo = _("Images")
        icono = Iconos.SVGs()
        extparam = "svgs"
        LCDialog.LCDialog.__init__(self, owner, titulo, icono, extparam)

        self.owner = owner

        flb = Controles.FontType(puntos=8)

        self.configuration = Code.configuration
        self.liPSVGs = list_svgs
        self.db_svgs = db_svgs

        # Lista
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NUMBER", _("N."), 60, align_center=True)
        o_columns.nueva("NOMBRE", _("Name"), 256)

        self.grid = Grid.Grid(self, o_columns, xid="M", complete_row_select=True)

        tb = QTDialogs.LCTB(self)
        tb.new(_("Close"), Iconos.MainMenu(), self.finalize)
        tb.new(_("New"), Iconos.Nuevo(), self.mas)
        tb.new(_("Remove"), Iconos.Borrar(), self.borrar)
        tb.new(_("Modify"), Iconos.Modificar(), self.modificar)
        tb.new(_("Copy"), Iconos.Copiar(), self.copiar)
        tb.new(_("Up"), Iconos.Arriba(), self.arriba)
        tb.new(_("Down"), Iconos.Abajo(), self.abajo)
        tb.setFont(flb)

        ly = Colocacion.V().control(tb).control(self.grid)

        # Board
        config_board = Code.configuration.config_board("EDIT_GRAPHICS", 48)
        self.board = Board.Board(self, config_board, with_director=False)
        self.board.draw_window()
        self.board.copia_posicion_de(owner.board)

        # Layout
        layout = Colocacion.H().otro(ly).control(self.board)
        self.setLayout(layout)

        # Ejemplos
        li_movs = ["g4h3", "e2e2", "d6f4"]
        self.liEjemplos = []
        reg_svg = BoardTypes.SVG()
        for a1h8 in li_movs:
            reg_svg.a1h8 = a1h8
            reg_svg.xml = estrellaSVG
            reg_svg.siMovible = True
            svg = self.board.create_svg(reg_svg, is_editing=True)
            self.liEjemplos.append(svg)

        self.grid.gotop()
        self.grid.setFocus()

    def closeEvent(self, event):
        self.save_video()

    def finalize(self):
        self.save_video()
        self.close()

    def grid_num_datos(self, _grid):
        return len(self.liPSVGs)

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        if key == "NUMBER":
            return str(row + 1)
        elif key == "NOMBRE":
            return self.liPSVGs[row].name
        return None

    def grid_doble_click(self, _grid, _row, _obj_column):
        self.modificar()

    def grid_cambiado_registro(self, _grid, row, _obj_column):
        if row >= 0:
            reg_svg = self.liPSVGs[row]
            for ejemplo in self.liEjemplos:
                a1h8 = ejemplo.block_data.a1h8
                bd = copy.deepcopy(reg_svg)
                bd.a1h8 = a1h8
                bd.width_square = self.board.width_square
                ejemplo.block_data = bd
                ejemplo.reset()
            self.board.escena.update()

    def mas(self):

        menu = QTDialogs.LCMenu(self)

        def look_folder(submenu, base, dr):
            if base:
                path_folder = f"{base}{dr}/"
                smenu = submenu.submenu(dr, Iconos.Carpeta())
            else:
                path_folder = f"{dr}/"
                smenu = submenu
            li = []
            for fich in os.listdir(path_folder):
                path_file = path_folder + fich
                if os.path.isdir(path_file):
                    look_folder(smenu, path_folder, fich)
                elif path_file.lower().endswith(".svg"):
                    li.append((path_file, fich))

            for path_file, fich in li:
                ico = QTDialogs.fsvg2ico(path_file, 32)
                if ico:
                    smenu.opcion(path_file, fich[:-4], ico)

        look_folder(menu, f"{Code.folder_resources}/", "imgs")

        menu.separador()

        menu.opcion("@", _X(_("To seek %1 file"), "SVG"), Iconos.Fichero())

        resp = menu.lanza()

        if resp is None:
            return

        if resp == "@":
            key = "SVG_GRAPHICS"
            dic = self.configuration.read_variables(key)
            folder = dic.get("FOLDER", self.configuration.paths.folder_userdata())
            file = SelectFiles.leeFichero(self, folder, "svg", titulo=_("Image"))
            if not file or not os.path.isfile(file):
                return
            dic["FOLDER"] = os.path.dirname(file)
            self.configuration.write_variables(key, dic)
        else:
            file = resp
        with open(file, "rt", encoding="utf-8", errors="ignore") as f:
            contenido = f.read()
        name = os.path.basename(file)[:-4]
        w = WTVSvg(self, None, xml=contenido, name=name)
        if w.exec():
            reg_svg = w.reg_svg
            reg_svg.id = Util.huella()
            reg_svg.ordenVista = (self.liPSVGs[-1].ordenVista + 1) if self.liPSVGs else 1
            self.db_svgs[reg_svg.id] = reg_svg.save_dic()
            self.liPSVGs.append(reg_svg)
            self.grid.refresh()
            self.grid.gobottom()
            self.grid.setFocus()

    def borrar(self):
        row = self.grid.recno()
        if row >= 0:
            if QTMessages.pregunta(self, _X(_("Delete %1?"), self.liPSVGs[row].name)):
                reg_svg = self.liPSVGs[row]
                str_id = reg_svg.id
                del self.liPSVGs[row]
                del self.db_svgs[str_id]
                self.grid.refresh()
                self.grid.setFocus()

    def modificar(self):
        row = self.grid.recno()
        if row >= 0:
            w = WTVSvg(self, self.liPSVGs[row])
            if w.exec():
                reg_svg = w.reg_svg
                str_id = reg_svg.id
                self.liPSVGs[row] = reg_svg
                self.db_svgs[str_id] = reg_svg.save_dic()
                self.grid.refresh()
                self.grid.setFocus()
                self.grid_cambiado_registro(self.grid, row, None)

    def copiar(self):
        row = self.grid.recno()
        if row >= 0:
            reg_svg = copy.deepcopy(self.liPSVGs[row])
            n = 1

            def exist_name(xname):
                for rf in self.liPSVGs:
                    if rf.name == xname:
                        return True
                return False

            name = "%s-%d" % (reg_svg.name, n)
            while exist_name(name):
                n += 1
                name = "%s-%d" % (reg_svg.name, n)
            reg_svg.name = name
            reg_svg.id = Util.huella()
            reg_svg.ordenVista = self.liPSVGs[-1].ordenVista + 1
            self.db_svgs[reg_svg.id] = reg_svg
            self.liPSVGs.append(reg_svg)
            self.grid.refresh()
            self.grid.setFocus()

    def interchange(self, fila1, fila2):
        reg_svg1, reg_svg2 = self.liPSVGs[fila1], self.liPSVGs[fila2]
        reg_svg1.ordenVista, reg_svg2.ordenVista = (
            reg_svg2.ordenVista,
            reg_svg1.ordenVista,
        )
        self.db_svgs[reg_svg1.id] = reg_svg1.save_dic()
        self.db_svgs[reg_svg2.id] = reg_svg2.save_dic()
        self.liPSVGs[fila1], self.liPSVGs[fila2] = (
            self.liPSVGs[fila2],
            self.liPSVGs[fila1],
        )
        self.grid.goto(fila2, 0)
        self.grid.refresh()
        self.grid.setFocus()

    def arriba(self):
        row = self.grid.recno()
        if row > 0:
            self.interchange(row, row - 1)

    def abajo(self):
        row = self.grid.recno()
        if 0 <= row < (len(self.liPSVGs) - 1):
            self.interchange(row, row + 1)
