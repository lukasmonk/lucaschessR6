from PySide6 import QtCore, QtWidgets

import Code
import Code.Board.WBoardColors as WBoardColors
from Code.Z import Util
from Code.QT import (
    Colocacion,
    Controles,
    Iconos,
    QTDialogs,
)


class BoardVisualMenu:
    """
    Board menu controller.

    Responsibility:
    - Visual menus
    - Board appearance actions
    """

    def __init__(self, board):
        self._board = board

    def launch_visual_menu(self):
        board = self._board
        if not board.with_menu_visual:
            return

        menu = QTDialogs.LCMenu(board)

        menu.opcion("colors", _("Colors"), Iconos.Colores())
        menu.separador()
        menu.opcion("pieces", _("Pieces"), board.pieces.icono("K"))
        menu.separador()
        c = str(board.main_window)
        ok = True
        if "MainWindow" in c:
            ok = not board.main_window.isMaximized()

        if ok:
            menu.opcion("size", _("Change board size"), Iconos.ResizeBoard())
            menu.separador()

        submenu = menu.submenu(_("By default"), Iconos.Defecto())
        submenu.opcion("def_todo1", "1", Iconos.m1())
        submenu.opcion("def_todo2", "2", Iconos.m2())
        submenu.opcion("def_todo3", "3", Iconos.m3())

        menu.separador()
        if board.with_director:
            menu.opcion("director", f"{_('Director')} [{_('F1-F10')}] ", Iconos.Director())
            menu.separador()

        if board.can_be_rotated:
            menu.opcion(
                "girar",
                f"{_('Flip the board')} [{_('ALT')}-F]",
                Iconos.JS_Rotacion(),
            )
            menu.separador()

        menu.opcion("keys", f"{_('Active keys')} [{_('ALT')}-K]", Iconos.Rename())
        menu.separador()

        resp = menu.lanza()
        if resp is None:
            return
        elif resp == "colors":
            menucol = QTDialogs.LCMenu(board)
            menucol.opcion("edit", _("Edit"), Iconos.EditarColores())
            menucol.separador()
            li_temas = Util.restore_pickle(Code.configuration.paths.file_themes())
            if li_temas:
                WBoardColors.add_menu_themes(menucol, li_temas, "tt_")
                menucol.separador()
            for entry in Util.listdir(Code.path_resource("Themes")):
                fich = entry.name
                if fich.lower().endswith(".lktheme3"):
                    board.fich_ = fich[:-9]
                    name = board.fich_
                    menucol.opcion(f"ot_{fich}", name, Iconos.Division())
            resp = menucol.lanza()
            if resp:
                if resp == "edit":
                    w = WBoardColors.WBoardColors(board)
                    w.exec()
                else:
                    self._set_colors(li_temas, resp)

        elif resp == "pieces":
            menup = QTDialogs.LCMenu(board)
            li = []
            for x in Util.listdir(Code.path_resource("Pieces")):
                try:
                    if x.is_dir():
                        ico = Code.all_pieces.icono("K", x.name)
                        li.append((x.name, ico))
                except:
                    pass
            li.sort(key=lambda rx: rx[0])
            for x, ico in li:
                menup.opcion(x, x, ico)
            if resp := menup.lanza():
                board.change_the_pieces(resp)

        elif resp == "size":
            self._change_size()

        elif resp == "girar":
            board.rotate_board()

        elif resp == "director":
            board.launch_director()

        elif resp == "keys":
            board.keyboard.show_keys()

        elif resp.startswith("def_todo"):
            board.configuration.change_theme_num(int(resp[-1]))
            board.config_board = board.configuration.reset_conf_board(
                board.config_board.id(), board.config_board.width_piece()
            )
            if board.config_board.is_base:
                nom_pieces_ori = board.config_board.nomPiezas()
                board.change_the_pieces(nom_pieces_ori)
            board.reset(board.config_board)
            if hasattr(board.main_window.parent, "adjust_size"):
                board.main_window.parent.adjust_size()

    def _change_size(self):
        imp = WTamBoard(self._board)
        imp.colocate()
        imp.exec()

    def _set_colors(self, li_temas, resp):
        board = self._board
        if resp.startswith("tt_"):
            tema = li_temas[int(resp[3:])]

        else:
            fich = Code.path_resource(f"Themes/{resp[3:]}")
            tema = WBoardColors.elige_tema(board, fich)

        if tema:
            board.config_board.leeTema(tema["o_tema"])
            if "o_base" in tema:
                board.config_board.leeBase(tema["o_base"])

            board.config_board.guardaEnDisco()
            pac = board.pieces_are_active
            pac_sie = board.side_pieces_active
            board.draw_window()
            if pac and pac_sie is not None:
                board.activate_side(pac_sie)


class WTamBoard(QtWidgets.QDialog):
    def __init__(self, board):

        QtWidgets.QDialog.__init__(self, board.parent())

        self.setWindowTitle(_("Change board size"))
        self.setWindowIcon(Iconos.ResizeBoard())
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
        )

        self.dispatch_size = board.dispatch_size
        self.board = board
        self.config_board = board.config_board

        ap = self.config_board.width_piece()

        self.antes = ap

        li_tams = [
            (_("Very large"), 80),
            (_("Large"), 64),
            (_("Medium"), 48),
            (_("Medium-small"), 32),
            (_("Small"), 24),
            (_("Very small"), 16),
            (_("Custom size"), 0),
            (_("Initial size"), -1),
            (_("By default"), -2),
        ]

        self.cb = Controles.CB(self, li_tams, self.width_for_cb(ap)).capture_changes(self.changed_width_cb)

        minimo = self.board.minimum_size
        maximo = board.calc_width_mx_piece() + 30

        self.sb = Controles.SB(self, ap, minimo, maximo).capture_changes(self.cambiado_tam_sb)

        self.sl = Controles.SL(self, minimo, maximo, ap, self.cambiado_tam_sl, tick=0).set_width(180)

        bt_aceptar = Controles.PB(self, "", rutina=self.aceptar, plano=False).set_icono(Iconos.Aceptar())

        layout = Colocacion.G()
        layout.control(bt_aceptar, 0, 0).control(self.cb, 0, 1).control(self.sb, 0, 2)
        layout.controlc(self.sl, 1, 0, 1, 3).margen(5)
        self.setLayout(layout)

        self.siOcupado = False
        self.siCambio = False
        self.board.allowed_extern_resize(False)

    @staticmethod
    def width_for_cb(ap):
        return ap if ap in (80, 64, 48, 32, 24, 16) else 0

    def colocate(self):
        self.show()  # Necesario para que calcule bien el tama_o antes de colocar
        pos = self.board.parent().mapToGlobal(self.board.pos())

        y = pos.y() - self.frameGeometry().height()
        y = max(y, 0)
        pos.setY(y)
        self.move(pos)

    def aceptar(self):
        self.close()

    def change_width(self):
        is_white_bottom = self.board.is_white_bottom
        self.board.width_changed()
        if not is_white_bottom:
            self.board.try_to_rotate_the_board(None)

    def dispatch(self):
        t = self.board
        if t.dispatch_size:
            t.dispatch_size()
        self.siCambio = True

    def changed_width_cb(self):
        if self.siOcupado:
            return
        self.siOcupado = True
        ct = self.config_board
        tam = self.cb.valor()

        if tam == 0:
            ct.width_piece(self.board.width_piece)
        elif tam == -1:
            tpz = self.antes
            ct.width_piece(tpz)
            self.cb.set_value(self.width_for_cb(tpz))
            self.change_width()
        elif tam == -2:
            self.cb.set_value(self.width_for_cb(ct.ponDefAnchoPieza()))
            self.change_width()
        else:
            ct.width_piece(tam)
            self.change_width()

        self.sb.set_value(self.board.width_piece)
        self.sl.set_value(self.board.width_piece)
        self.siOcupado = False
        self.dispatch()

    def cambiado_tam_sb(self):
        if self.siOcupado:
            return
        self.siOcupado = True
        tam = self.sb.valor()
        self.config_board.width_piece(tam)
        self.cb.set_value(self.width_for_cb(tam))
        self.change_width()
        self.sl.set_value(tam)
        self.siOcupado = False
        self.dispatch()

    def cambiado_tam_sl(self):
        if self.siOcupado:
            return
        self.siOcupado = True
        tam = self.sl.valor()
        self.config_board.width_piece(tam)
        self.cb.set_value(self.width_for_cb(tam))
        self.sb.set_value(tam)
        self.change_width()
        self.siOcupado = False
        self.dispatch()

    def closeEvent(self, event):
        self.config_board.guardaEnDisco()
        self.close()
        if self.siCambio:
            self.dispatch()
        if self.config_board.is_base:
            self.board.allowed_extern_resize(self.config_board.is_base)
