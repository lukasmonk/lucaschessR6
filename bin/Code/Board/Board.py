import collections
import copy
import os
import webbrowser
from io import BytesIO
from typing import Any, List, Optional, Callable

import FasterCode
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

import Code
import Code.Board.WBoardColors as WBoardColors
from Code.Z import Util, XRun
from Code.Base import Game, Position
from Code.Base.Constantes import (
    BLUNDER,
    GOOD_MOVE,
    INACCURACY,
    INFINITE,
    INTERESTING_MOVE,
    MISTAKE,
    NO_RATING,
    TB_TAKEBACK,
    VERY_GOOD_MOVE,
    ZVALUE_PIECE,
)
from Code.Board import (
    BoardArrows,
    BoardBoxes,
    BoardCircles,
    BoardDoubleBoxes,
    BoardElements,
    BoardMarkers,
    BoardSVGs,
    BoardTypes,
    LichessCommentParser,
)
from Code.Board.BoardSections import BoardVisualMenu, BoardEboardController, BoardBlindfold
from Code.Databases import DBgames
from Code.Director import TabVisual, WindowDirector
from Code.Nags import Nags
from Code.QT import (
    Delegados,
    Iconos,
    Piezas,
    QTDialogs,
    QTMessages,
    QTUtils,
    ScreenUtils,
    SelectFiles,
)
from Code.Translations import TrListas


class RegKB:
    def __init__(self, key: int, flags: int):
        self.key = key
        self.flags = flags


class SaveVisualState:
    with_menu_visual: bool
    with_director: bool
    show_graphic_icon: bool
    dirvisual: Optional[WindowDirector.Director]
    guion: Optional[TabVisual.Guion]
    lastFenM2: str
    nomdbVisual: str
    dbVisual_show_always: bool


class Board(QtWidgets.QGraphicsView):
    """
    Main class for representing and managing the graphical chessboard.
    It inherits from QGraphicsView and handles the display of pieces, board, arrows,
    and user interaction (mouse, keyboard).
    """

    pieces_are_active: bool
    li_pieces: list
    can_be_rotated: bool
    dic_movables: collections.OrderedDict
    ancho: int
    arrow_sc: Optional[BoardArrows.ArrowSC]
    atajos_raton: Optional[Callable[[Any, Optional[str]], None]]
    baseCasillasFSC: Optional[BoardElements.CajaSC]
    baseCasillasSC: BoardElements.CajaSC | BoardElements.PixmapSC
    cajonSC: BoardElements.CajaSC | BoardElements.PixmapSC
    can_be_rotated: bool
    colorBlancas: int
    colorExterior: int
    colorFondo: int
    colorFrontera: int
    colorNegras: int
    colorTexto: int
    config_board: Any
    configuration: Any
    current_graphlive: Any
    dbVisual: Any
    dicXML: dict[str, str]
    dic_graphlive: dict[str, Any] | None
    dic_movables: dict[Any, Any]
    dirvisual: Any
    escenea: QtWidgets.QGraphicsScene
    extended_fondo: bool
    fich_: str
    guion: Any
    init_white_bottom: bool
    is_white_bottom: bool
    lastFenM2: str | None
    last_position: Any
    liCoordenadasHorizontales: list[Any]
    liCoordenadasVerticales: list[Any]
    margin_center: int
    mensajero: Any
    minimum_size: int
    nCoordenadas: int
    pendingRelease: list[Any] | None
    pieces: Any
    pieces_are_active: bool
    pressed_letter: Any
    pressed_number: Any
    png64Blancas: bytes
    png64Fondo: bytes
    png64Negras: bytes
    rutaSVG: str
    rutinaDropsPGN: Optional[Callable[[str], None]]
    scriptSC_menu: Optional[BoardElements.PixmapSC]
    show_graphic_icon: bool
    side_indicator_sc: Optional[BoardElements.CirculoSC]
    side_pieces_active: bool | None
    tamFrontera: int
    transBlancas: int
    transNegras: int
    transSideIndicator: int
    width_square: int
    with_director: bool
    with_menu_visual: bool
    reg_save_visual_state: SaveVisualState
    indicadorSC_menu: Optional[BoardElements.PixmapSC]
    width_piece: int
    margin_pieces: int
    png64Exterior: str
    do_pressed_number: Optional[Callable]
    do_pressed_letter: Optional[Callable]
    puntos: int
    li_arrows: list
    id_last_movable: int

    def __init__(
        self,
        parent,
        config_board: Any,
        with_menu_visual: bool = True,
        with_director: bool = True,
        allow_eboard: bool = False,
    ):
        super().__init__()

        self.setRenderHints(
            QtGui.QPainter.RenderHint.Antialiasing
            or QtGui.QPainter.RenderHint.TextAntialiasing
            or QtGui.QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheModeFlag.CacheBackground)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
        self.setInteractive(True)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.NoAnchor)
        self.escena = QtWidgets.QGraphicsScene(self)
        self.escena.setItemIndexMethod(QtWidgets.QGraphicsScene.ItemIndexMethod.NoIndex)
        self.setScene(self.escena)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)

        self.main_window = parent
        self.configuration = Code.configuration

        self.visual_menu = BoardVisualMenu.BoardVisualMenu(self)
        self.eboard = BoardEboardController.BoardEboardController(self)
        self.blindfold_controller = BoardBlindfold.BoardBlindfold(self)

        self.variation_history = None

        self.with_menu_visual = with_menu_visual
        self.with_director = with_director and with_menu_visual
        self.show_graphic_icon = self.with_director and self.configuration.x_director_icon
        self.dirvisual = None
        self.guion = None
        self.lastFenM2 = ""
        self.dbVisual = TabVisual.DBManagerVisual(
            self.configuration.paths.file_resources(),
            show_always=self.configuration.x_director_icon is False,
        )
        self.current_graphlive = None
        self.dic_graphlive = None

        self.rutinaDropsPGN = None

        self.config_board = config_board

        self.siInicializado = False

        self.last_position: Optional[Position.Position] = None

        self.siF11 = False

        self.dispatch_size = None  # configuration en vivo, dirige a la rutina de la main_window afectada

        self.pendingRelease = None

        self.siPermitidoResizeExterno = True
        self.mensajero: Optional[Callable] = None

        self.si_borraMovibles = True

        self.kb_buffer: List[RegKB] = []
        self.cad_buffer = ""
        self.dic_tr_keymoves = TrListas.dic_conv()

        self.hard_focus = True  # Controla que cada vez que se indique una posición active el foco al board

        self.allow_eboard = allow_eboard

        self.minimum_size = 2

        self.active_premove = False

        self.analysis_bar = None

        self.arrow_sc = None

    def set_analysis_bar(self, analysis_bar: Any):
        self.analysis_bar = analysis_bar

    def disable_hard_focus(self):
        self.hard_focus = False

    def init_kb_buffer(self):
        self.kb_buffer = []
        self.cad_buffer = ""

    def exec_kb_buffer(self, key: int, flags: int):
        """
        Procesa la entrada del teclado y ejecuta acciones asociadas.
        Maneja atajos de teclado y comandos de movimiento.
        """
        if key == Qt.Key.Key_Escape:
            self.init_kb_buffer()
            return

        if key in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            if self.kb_buffer:
                last = self.kb_buffer[-1]
                key = last.key
                flags = last.flags or QtCore.Qt.KeyboardModifier.AltModifier
            else:
                return

        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete) and self.allow_takeback():
            self.main_window.manager.run_action(TB_TAKEBACK)
            return

        is_alt = (flags & QtCore.Qt.KeyboardModifier.AltModifier.value) > 0
        is_shift = (flags & QtCore.Qt.KeyboardModifier.ShiftModifier.value) > 0
        is_ctrl = (flags & QtCore.Qt.KeyboardModifier.ControlModifier.value) > 0

        okseguir = False

        if is_alt or is_ctrl:

            # CTRL-C/ : copy fen al clipboard
            if key == Qt.Key.Key_C:
                if (self.configuration.x_copy_ctrl and is_ctrl) or (not self.configuration.x_copy_ctrl and is_alt):
                    if is_shift:
                        if hasattr(self.main_window, "manager") and hasattr(
                            self.main_window.manager, "save_pgn_clipboard"
                        ):
                            self.main_window.manager.save_pgn_clipboard()
                    else:
                        if self.last_position:
                            QTUtils.set_clipboard(self.last_position.fen())
                        QTDialogs.fen_is_in_clipboard(self)

            elif is_alt and key == Qt.Key.Key_B:
                self.launch_visual_menu()

            elif is_alt and key == Qt.Key.Key_Y:
                self.blindfold_change()

            elif is_ctrl and key == Qt.Key.Key_Y:
                self.blindfold_config()

            elif is_ctrl and (key in (Qt.Key.Key_Plus, Qt.Key.Key_Minus)):
                ap = self.config_board.width_piece()
                ap += 2 * (1 if key == Qt.Key.Key_Plus else -1)
                if ap >= 10:
                    self.config_board.width_piece(ap)
                    self.config_board.guardaEnDisco()
                    self.width_changed()
                    return

            elif is_ctrl and key == Qt.Key.Key_T:
                resp = DBgames.save_selected_position(self.last_position)
                if not resp.ok:
                    QTMessages.message_error(self, resp.mens_error)
                else:
                    QTMessages.temporary_message(
                        self,
                        f'{_("Saved")}\n{_("Databases")}: __Selected Positions__',
                        1.8,
                    )

            elif is_alt and key == Qt.Key.Key_F:
                self.try_to_rotate_the_board(None)

            elif key == Qt.Key.Key_I:
                self.save_as_img(is_ctrl=is_ctrl, is_alt=is_alt)
                QTMessages.temporary_message(self.main_window, _("Board image is in clipboard"), 1.2)

            elif key == Qt.Key.Key_J:
                if path := SelectFiles.salvaFichero(
                    self,
                    _("File to save"),
                    self.configuration.save_folder(),
                    "png",
                    False,
                ):
                    self.save_as_img(path, "png", is_ctrl=is_ctrl, is_alt=is_alt)
                    self.configuration.set_save_folder(os.path.dirname(path))

            elif is_alt and key == Qt.Key.Key_K:
                self.show_keys()

            elif is_alt and key == Qt.Key.Key_L:
                if self.last_position:
                    webbrowser.open(f"https://lichess.org/analysis/standard/{self.last_position.fen()}")

            elif is_alt and key == Qt.Key.Key_T:
                if self.last_position:
                    webbrowser.open(f"https://old.chesstempo.com/gamedb/fen/{self.last_position.fen()}")

            elif is_alt and key == Qt.Key.Key_X:
                self.play_current_position()

            elif (
                hasattr(self.main_window, "manager")
                and self.main_window.manager
                and key in (Qt.Key.Key_P, Qt.Key.Key_N, Qt.Key.Key_C)
            ):
                # P -> show information
                if key == Qt.Key.Key_P and hasattr(self.main_window.manager, "information_pgn"):
                    self.main_window.manager.information_pgn()
                elif key == Qt.Key.Key_N and hasattr(self.main_window.manager, "non_distract_mode"):
                    self.main_window.manager.non_distract_mode()
                else:
                    okseguir = True
        else:
            okseguir = True

        if not okseguir:
            if self.kb_buffer:
                self.kb_buffer = self.kb_buffer[:-1]
                self.cad_buffer = ""
            return

        if self.mensajero and self.pieces_are_active and not is_alt:
            # Entrada directa
            if 128 > key > 32:
                self.cad_buffer += chr(key)
            if len(self.cad_buffer) >= 2:
                FasterCode.set_fen(self.last_position.fen())
                li = FasterCode.get_exmoves()
                busca = self.cad_buffer.lower()

                exmove_ok = None

                for exmove in li:
                    a1h8 = exmove.move()
                    if busca.endswith(a1h8):
                        exmove_ok = exmove
                        break
                if exmove_ok is None:
                    for exmove in li:
                        san = exmove.san().replace("+", "").replace("#", "")
                        if len(san) > 2:
                            if san[-1].upper() in self.dic_tr_keymoves:
                                san = san[:-1] + self.dic_tr_keymoves[san[-1].upper()]
                            elif san[0].upper() in self.dic_tr_keymoves:
                                san = self.dic_tr_keymoves[san[0].upper()] + san[1:]
                        if (
                            busca.endswith(san.lower())
                            or busca.endswith(san.lower().replace("=", ""))
                            or (san == "O-O-O" and busca.endswith("o3"))
                            or (san == "O-O" and busca.endswith("o2"))
                        ):
                            if exmove_ok:
                                if len(san) > len(exmove_ok.san()):
                                    exmove_ok = exmove
                            else:
                                exmove_ok = exmove

                if exmove_ok:
                    self.init_kb_buffer()
                    self.mensajero(exmove_ok.xfrom(), exmove_ok.xto(), exmove_ok.promotion())

    def sizeHint(self):
        return QtCore.QSize(self.ancho + 6, self.ancho + 6)

    @staticmethod
    def xremove_item(item):
        if scene := item.scene():
            scene.removeItem(item)

    def keyPressEvent(self, event):
        k = event.key()
        m = event.modifiers().value

        if Qt.Key.Key_F1 <= k <= Qt.Key.Key_F10:
            if self.dirvisual and self.dirvisual.keyPressEvent(event):
                return
            if (m & QtCore.Qt.KeyboardModifier.ControlModifier.value) > 0:
                if k == Qt.Key.Key_F1:
                    self.remove_last_movable()
                elif k == Qt.Key.Key_F2:
                    self.remove_movables()
            elif self.launch_director():
                self.dirvisual.keyPressEvent(event)
            return

        event.ignore()

        if k in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace) and len(self.dic_movables) > 0:
            if self.dirvisual:
                self.dirvisual.keyPressEvent(event)
            elif k == QtCore.Qt.Key.Key_Backspace:
                self.remove_last_movable()
            elif k == QtCore.Qt.Key.Key_Delete:
                self.remove_movables()
            return

        self.exec_kb_buffer(k, m)

    def activa_menu_visual(self, si_activar):
        self.with_menu_visual = si_activar

    def allowed_extern_resize(self, sino=None):
        if sino is not None:
            self.siPermitidoResizeExterno = sino
        return self.siPermitidoResizeExterno

    def maximize_size(self, activado_f11):
        self.siF11 = activado_f11
        self.config_board.width_piece(1000)
        self.config_board.guardaEnDisco()
        self.width_changed()

    def normal_size(self, xancho_pieza):
        self.siF11 = False
        self.config_board.width_piece(xancho_pieza)
        self.config_board.guardaEnDisco()
        self.width_changed()

    def width_changed(self):
        is_white_bottom = self.is_white_bottom
        self.set_width()
        if not is_white_bottom:
            self.try_to_rotate_the_board(None)
        if self.dispatch_size:
            self.dispatch_size()

    def is_maximized(self):
        return self.config_board.width_piece() == 1000

    def draw_window(self):
        nom_pieces_ori = self.config_board.nomPiezas()
        if self.blindfold_controller.blind_sides():
            self.pieces = Piezas.Blindfold(nom_pieces_ori, self.blindfold_controller.blind_sides())
        else:
            self.pieces = Code.all_pieces.selecciona(nom_pieces_ori)
        self.width_piece = self.config_board.width_piece()
        self.margin_pieces = (
            Code.configuration.x_margin_pieces - 10
        )  # -10 a +10 como valor real, de 0 a 20 en configuración parámetros

        self.colorBlancas = self.config_board.colorBlancas()
        self.colorNegras = self.config_board.colorNegras()
        self.colorFondo = self.config_board.colorFondo()
        self.png64Blancas = self.config_board.png64Blancas()
        self.png64Negras = self.config_board.png64Negras()
        self.png64Fondo = self.config_board.png64Fondo()
        self.png64Exterior = self.config_board.png64Exterior()
        self.transBlancas = self.config_board.transBlancas()
        self.transNegras = self.config_board.transNegras()
        self.transSideIndicator = self.config_board.transSideIndicator()

        self.extended_fondo = self.config_board.extended_color()
        if self.extended_fondo:
            self.colorExterior = self.colorFondo
            self.png64Exterior = self.png64Fondo
        else:
            self.colorExterior = self.config_board.colorExterior()
            self.png64Exterior = self.png64Exterior

        self.colorTexto = self.config_board.colorTexto()

        self.colorFrontera = self.config_board.colorFrontera()

        self.do_pressed_number = None
        self.do_pressed_letter = None
        self.atajos_raton = None
        self.pieces_are_active = False  # Control adicional, para responder a eventos del raton
        self.side_pieces_active = None

        self.can_be_rotated = True

        self.is_white_bottom = True

        self.nCoordenadas = self.config_board.nCoordenadas()

        self.set_width()

    def calc_width_mx_piece(self):
        if self.siF11:
            sz_width, sz_height = ScreenUtils.desktop_size()
            limit = min(sz_width, sz_height)
        else:
            sz_width, sz_height = ScreenUtils.desktop_size()
            limit = min(sz_width, sz_height)
            if Code.configuration.x_tb_orientation_horizontal:
                limit -= 80

            limit -= 42

        tr = 1.0 * self.config_board.tamRecuadro() / 100.0

        return int((1.0 * limit - 16.0 * self.margin_pieces) / (8.0 + tr * 92.0 / 80))

    def set_width(self):
        d_tam = {
            16: (9, 23),
            24: (10, 29),
            32: (12, 33),
            48: (14, 38),
            64: (16, 42),
            80: (18, 46),
        }

        ap = self.config_board.width_piece()
        if ap == 1000:
            ap = self.calc_width_mx_piece()
        if ap in d_tam:
            self.puntos, self.margin_center = d_tam[ap]
        else:
            mx = INFINITE
            kt = 0
            for k in d_tam:
                mt = abs(k - ap)
                if mt < mx:
                    mx = mt
                    kt = k
            pt, mc = d_tam[kt]
            self.puntos = pt * ap // kt
            self.margin_center = mc * ap // kt

        self.width_piece = ap

        self.width_square = ap + self.margin_pieces * 2
        self.tamFrontera = int(self.margin_center * 3.0 // 46.0)

        self.margin_center = self.margin_center * self.config_board.tamRecuadro() // 100

        fx = self.config_board.tamFrontera()
        self.tamFrontera = int(self.tamFrontera * fx // 100)
        if fx > 0 and self.tamFrontera == 0:
            self.tamFrontera = 2
        if self.tamFrontera % 2 == 1:
            self.tamFrontera += 1

        self.puntos = self.puntos * self.config_board.tamLetra() * 12 // 1000

        # Guardamos las pieces

        if self.siInicializado:
            li_pz = []
            for cpieza, pieza_sc, is_active in self.li_pieces:
                if is_active:
                    physical_pos = pieza_sc.bloquePieza
                    f = physical_pos.row
                    c = physical_pos.column
                    pos_a1_h8 = chr(c + 96) + str(f)
                    li_pz.append((cpieza, pos_a1_h8))

            ap, apc = self.pieces_are_active, self.side_pieces_active
            si_flecha = self.arrow_sc is not None

            self.redraw()

            if li_pz:
                for cpieza, a1h8 in li_pz:
                    self.create_piece(cpieza, a1h8)
            if ap:
                self.activate_side(apc)
                self.set_side_indicator(apc)

            if si_flecha:
                self.reset_arrow_sc()

        else:
            self.redraw()

        self.siInicializado = True
        self.init_kb_buffer()

    def redraw(self):
        self.escena.clear()
        self.li_pieces = []
        self.li_arrows = []
        self.arrow_sc = None
        self.dic_movables = collections.OrderedDict()  # Flechas, Marcos, SVG
        self.id_last_movable = 0
        self.side_indicator_sc = None

        self.is_white_bottom = True

        # Completo
        is_png = False
        if self.extended_fondo:
            if self.png64Fondo:
                cajon = BoardTypes.Imagen()
                cajon.pixmap = self.png64Fondo
                is_png = True
            else:
                cajon = BoardTypes.Caja()
                cajon.colorRelleno = self.colorFondo
        else:
            if self.png64Exterior:
                cajon = BoardTypes.Imagen()
                cajon.pixmap = self.png64Exterior
                is_png = True
            else:
                cajon = BoardTypes.Caja()
                cajon.colorRelleno = self.colorExterior
        self.ancho = ancho = cajon.physical_pos.alto = cajon.physical_pos.ancho = (
            self.width_square * 8 + self.margin_center * 2 + self.tamFrontera * 2
        )
        cajon.physical_pos.orden = 1
        cajon.tipo = 0
        self.setFixedSize(ancho, ancho)
        if is_png:
            self.cajonSC = BoardElements.PixmapSC(self.escena, cajon)
        else:
            self.cajonSC = BoardElements.CajaSC(self.escena, cajon)

        # Fondo squares
        if self.png64Fondo:
            base_casillas = BoardTypes.Imagen()
            base_casillas.pixmap = self.png64Fondo
        else:
            base_casillas = BoardTypes.Caja()
            base_casillas.colorRelleno = self.colorFondo
        base_casillas.physical_pos.x = base_casillas.physical_pos.y = self.margin_center + self.tamFrontera / 2
        base_casillas.physical_pos.alto = base_casillas.physical_pos.ancho = self.width_square * 8
        base_casillas.physical_pos.orden = 2
        base_casillas.tipo = 0
        if self.png64Fondo:
            self.baseCasillasSC = BoardElements.PixmapSC(self.escena, base_casillas)
        else:
            self.baseCasillasSC = BoardElements.CajaSC(self.escena, base_casillas)
        if self.extended_fondo:
            self.baseCasillasSC.hide()

        # Frontera
        base_casillas_f = BoardTypes.Caja()
        base_casillas_f.grosor = self.tamFrontera
        base_casillas_f.physical_pos.x = base_casillas_f.physical_pos.y = self.margin_center
        base_casillas_f.physical_pos.alto = base_casillas_f.physical_pos.ancho = (
            self.width_square * 8 + self.tamFrontera
        )
        base_casillas_f.physical_pos.orden = 3
        base_casillas_f.colorRelleno = -1
        base_casillas_f.color = self.colorFrontera
        base_casillas_f.redEsquina = 0  # self.tamFrontera
        base_casillas_f.tipo = 1

        if base_casillas_f.grosor > 0:
            self.baseCasillasFSC = BoardElements.CajaSC(self.escena, base_casillas_f)

        # squares
        def haz_casillas(tipo, png64, color, transparencia):
            with_pixmap = len(png64) > 0
            pixmap = None
            if with_pixmap:
                square = BoardTypes.Imagen()
                square.pixmap = png64
            else:
                square = BoardTypes.Caja()
                square.tipo = 0
                square.colorRelleno = color
            square.physical_pos.orden = 4
            square.physical_pos.alto = square.physical_pos.ancho = self.width_square
            opacity = 100.0 - transparencia * 1.0
            for z in range(4):
                for y in range(8):
                    una = square.copia()

                    k1 = k = self.margin_center + self.tamFrontera // 2
                    if y % 2 == tipo:
                        k += self.width_square
                    una.physical_pos.x = k + z * 2 * self.width_square
                    una.physical_pos.y = k1 + y * self.width_square
                    if with_pixmap:
                        casilla_sc = BoardElements.PixmapSC(self.escena, una, pixmap=pixmap)
                        pixmap = casilla_sc.pixmap
                    else:
                        casilla_sc = BoardElements.CajaSC(self.escena, una)
                    if opacity != 100.0:
                        casilla_sc.setOpacity(opacity / 100.0)

        haz_casillas(1, self.png64Blancas, self.colorBlancas, self.transBlancas)
        haz_casillas(0, self.png64Negras, self.colorNegras, self.transNegras)

        # Coordenadas
        self.liCoordenadasVerticales = []
        self.liCoordenadasHorizontales = []

        ancho_texto = self.puntos + 4
        if self.margin_center >= self.puntos or self.config_board.sepLetras() < 0:
            coord = BoardTypes.Texto()
            tipo_letra = self.config_board.font_type()
            peso = 75 if self.config_board.bold() else 50
            coord.font_type = BoardTypes.FontType(tipo_letra, self.puntos, peso=peso)
            coord.physical_pos.ancho = ancho_texto
            coord.physical_pos.alto = ancho_texto
            coord.physical_pos.orden = 7
            coord.colorTexto = self.colorTexto

            p_casillas = base_casillas.physical_pos
            p_frontera = base_casillas_f.physical_pos
            gap_casilla = (self.width_square - ancho_texto) / 2
            sep = (
                self.margin_center * self.config_board.sepLetras() * 38 / 50000
            )  # ancho = 38 -> sep = 5 -> sepLetras = 100

            def norm(z):
                if z < 0:
                    return 0
                return ancho - ancho_texto if z > (ancho - ancho_texto) else z

            hx = norm(p_casillas.x + gap_casilla)
            hy_s = norm(p_frontera.y + p_frontera.alto + sep)
            hy_n = norm(p_frontera.y - ancho_texto - sep)

            vy = norm(p_casillas.y + gap_casilla)
            vx_e = norm(p_frontera.x + p_frontera.ancho + sep)
            vx_o = norm(p_frontera.x - ancho_texto - sep)

            for x in range(8):

                if self.nCoordenadas > 0:  # 2 o 3 o 4 o 5 o 6
                    d = {  # hS,     vO,     hN,     vE
                        2: (True, True, False, False),
                        3: (False, True, True, False),
                        4: (True, True, True, True),
                        5: (False, False, True, True),
                        6: (True, False, False, True),
                    }
                    li_co = d[self.nCoordenadas]
                    hor = coord.copia()
                    hor.valor = chr(97 + x)
                    hor.alineacion = "c"
                    hor.physical_pos.x = hx + x * self.width_square

                    if li_co[0]:
                        hor.physical_pos.y = hy_s
                        hor_sc = BoardElements.TextoSC(self.escena, hor, self.pressed_letter)
                        self.liCoordenadasHorizontales.append(hor_sc)

                    if li_co[2]:
                        hor = hor.copia()
                        hor.physical_pos.y = hy_n
                        hor_sc = BoardElements.TextoSC(self.escena, hor, self.pressed_letter)
                        self.liCoordenadasHorizontales.append(hor_sc)

                    ver = coord.copia()
                    ver.valor = chr(56 - x)
                    ver.alineacion = "c"
                    ver.physical_pos.y = vy + x * self.width_square

                    if li_co[1]:
                        ver.physical_pos.x = vx_o
                        ver_sc = BoardElements.TextoSC(self.escena, ver, self.pressed_number)
                        self.liCoordenadasVerticales.append(ver_sc)

                    if li_co[3]:
                        ver = ver.copia()
                        ver.physical_pos.x = vx_e
                        ver_sc = BoardElements.TextoSC(self.escena, ver, self.pressed_number)
                        self.liCoordenadasVerticales.append(ver_sc)

        # Indicador de color activo
        p_frontera = base_casillas_f.physical_pos
        p_cajon = cajon.physical_pos
        ancho = p_cajon.ancho - (p_frontera.x + p_frontera.ancho)
        gap = int(ancho / 8) * 2

        indicador = BoardTypes.Circulo()
        indicador.physical_pos.x = (p_frontera.x + p_frontera.ancho) + gap / 2
        indicador.physical_pos.y = (p_frontera.y + p_frontera.alto) + gap / 2
        indicador.physical_pos.ancho = indicador.physical_pos.alto = ancho - gap
        indicador.physical_pos.orden = 2
        indicador.color = self.colorFrontera
        indicador.grosor = 1
        indicador.tipo = 1
        indicador.sur = indicador.physical_pos.y
        indicador.norte = gap / 2
        self.side_indicator_sc = BoardElements.CirculoSC(self.escena, indicador, rutina=self.try_to_rotate_the_board)

        self.side_indicator_sc.setOpacity((100.0 - self.transSideIndicator * 1.0) / 100.0)

        # Lanzador de menu visual
        self.indicadorSC_menu = None
        self.scriptSC_menu = None
        if self.with_menu_visual:
            indicador_menu = BoardTypes.Imagen()
            indicador_menu.physical_pos.x = 2
            if self.configuration.x_position_tool_board == "B":
                indicador_menu.physical_pos.y = self.ancho - 24
            else:
                indicador_menu.physical_pos.y = 2

            indicador_menu.physical_pos.ancho = indicador_menu.physical_pos.alto = ancho - 2 * gap
            indicador_menu.physical_pos.orden = 2
            indicador_menu.color = self.colorFrontera
            indicador_menu.grosor = 1
            indicador_menu.tipo = 1
            indicador_menu.sur = indicador.physical_pos.y
            indicador_menu.norte = gap / 2
            self.indicadorSC_menu = BoardElements.PixmapSC(
                self.escena,
                indicador_menu,
                pixmap=Iconos.pmSettings(),
                rutina=self.launch_visual_menu,
            )
            self.indicadorSC_menu.setOpacity(0.50 if self.configuration.x_opacity_tool_board == 10 else 0.01)

            if self.show_graphic_icon:
                script = BoardTypes.Imagen()
                script.physical_pos.x = p_frontera.x - ancho + ancho
                if self.configuration.x_position_tool_board == "B":
                    script.physical_pos.y = p_frontera.y + p_frontera.alto + 2 * gap
                else:
                    script.physical_pos.y = 0

                script.physical_pos.ancho = script.physical_pos.alto = ancho - 2 * gap
                script.physical_pos.orden = 2
                script.color = self.colorFrontera
                script.grosor = 1
                script.tipo = 1
                script.sur = indicador.physical_pos.y
                script.norte = gap / 2
                self.scriptSC_menu = BoardElements.PixmapSC(
                    self.escena,
                    script,
                    pixmap=Iconos.pmLampara(),
                    rutina=self.launch_guion_auto,
                )
                self.scriptSC_menu.hide()
                self.scriptSC_menu.setOpacity(0.70)

        self.init_kb_buffer()

        self.setSceneRect(0, 0, self.ancho, self.ancho)

    def set_accept_drop_pgns(self, rutina_drops_pgn):
        self.baseCasillasSC.setAcceptDrops(rutina_drops_pgn is not None)
        self.rutinaDropsPGN = rutina_drops_pgn

    def dropEvent(self, event):
        if self.rutinaDropsPGN is not None:
            mime_data = event.mimeData()
            if mime_data.hasUrls():
                li = mime_data.urls()
                if len(li) > 0:
                    self.rutinaDropsPGN(li[0].path().strip("/"))
        event.setDropAction(QtCore.Qt.DropAction.IgnoreAction)
        event.ignore()

    def show_keys(self):

        class RegSK:
            def __init__(self, key, txt, is_alt=False, is_ctrl=False, is_shift=False):
                self.is_alt = is_alt
                self.is_ctrl = is_ctrl
                self.is_shift = is_shift
                self.text = txt
                self.key = key

            def get_shortcut(self):
                li_alt = []
                if self.is_ctrl:
                    li_alt.append("Ctrl")
                if self.is_alt:
                    li_alt.append("Alt")
                if self.is_shift:
                    li_alt.append("Shift")
                li_alt.append(self.key)
                text_keys = "+".join(li_alt)
                return text_keys

            def get_text(self):
                return self.text

            def icon(self):
                return Iconos.Mover() if len(self.key) == 1 else None

            def run(self, exec_kb_buffer):
                if len(self.key) == 1:
                    flags = 0
                    if self.is_ctrl:
                        flags |= QtCore.Qt.KeyboardModifier.ControlModifier
                    if self.is_alt:
                        flags |= QtCore.Qt.KeyboardModifier.AltModifier
                    if self.is_shift:
                        flags |= QtCore.Qt.KeyboardModifier.ShiftModifier
                    exec_kb_buffer(ord(self.key), flags)

        li_regs = []

        def add_key(xkey, txt, is_alt=False, is_ctrl=False, is_shift=False):
            regkey = RegSK(xkey, txt, is_alt=is_alt, is_ctrl=is_ctrl, is_shift=is_shift)
            li_regs.append(regkey)

        def alt(xkey, txt):
            add_key(xkey, txt, is_alt=True)

        def ctrl(xkey, txt):
            add_key(xkey, txt, is_ctrl=True)

        def close_group():
            li_regs.append(None)

        alt("B", _("Board menu"))
        close_group()

        alt("F", _("Flip the board"))
        close_group()

        if Code.configuration.x_copy_ctrl:
            ctrl("C", _("Copy FEN to clipboard"))
        else:
            alt("C", _("Copy FEN to clipboard"))

        if hasattr(self.main_window, "manager") and hasattr(self.main_window.manager, "save_pgn_clipboard"):
            xis_ctrl = Code.configuration.x_copy_ctrl
            xis_alt = not xis_ctrl
            add_key(
                "C",
                _("Copy PGN to clipboard"),
                is_alt=xis_alt,
                is_ctrl=xis_ctrl,
                is_shift=True,
            )
        close_group()

        alt("I", _("Copy board as image to clipboard"))
        ctrl("I", f"{_('Copy board as image to clipboard')} ({_('without border')})")
        add_key(
            "I",
            f"{_('Copy board as image to clipboard')} ({_('without coordinates')})",
            is_ctrl=True,
            is_alt=True,
        )
        alt("J", _("Copy board as image to a file"))
        ctrl("J", f"{_('Copy board as image to a file')} ({_('without border')})")
        add_key(
            "J",
            f"{_('Copy board as image to a file')} ({_('without coordinates')})",
            is_ctrl=True,
            is_alt=True,
        )
        close_group()

        alt("Y", f'{_("Blindfold chess")}: {_("Enable")}/{_("Disable")}')
        ctrl("Y", f'{_("Blindfold chess")}: {_("Configuration")}')
        close_group()

        alt("L", _("Open position in LiChess"))
        alt("T", _("Open position in ChessTempo"))
        alt("X", _("Play current position"))
        close_group()

        if self.pieces_are_active:
            add_key(
                "a1 ... h8",
                f"{_('To indicate origin and destination of a move')}= a1 ... h8",
            )
            close_group()

        if hasattr(self.main_window, "manager") and self.main_window.manager:
            if hasattr(self.main_window.manager, "grid_right_mouse"):
                alt("P", _("Show/Hide PGN information"))
                close_group()

            ctrl("T", _("Save position in 'Selected positions' file"))
            close_group()

            if hasattr(self.main_window.manager, "can_be_analysed") and self.main_window.manager.can_be_analysed():
                alt("A", _("Analyze"))
                close_group()

            if hasattr(self.main_window.manager, "list_help_keyboard"):
                self.main_window.manager.list_help_keyboard(add_key)
                close_group()

            alt("N", _("Activate/Deactivate non distract mode"))

        alt("O", _("Move the window to the top left corner"))
        add_key("F11", _("Full screen On/Off"))
        add_key("F12", _("Minimize to the tray icon"))
        close_group()

        menu = QTDialogs.LCMenu(self)
        # rondo = QTDialogs.rondo_puntos(shuffle=False)
        # menu.set_font(Code.font_mono)
        menu.opcion(None, _("Active keys"), Iconos.Rename())
        menu.separador()
        # icon = rondo.otro()
        for reg in li_regs:
            if reg is None:
                menu.separador()
                # icon = rondo.otro()
            else:
                menu.opcion(reg, reg.get_text(), shortcut=reg.get_shortcut())
        reg = menu.lanza()
        if reg:
            reg.run(self.exec_kb_buffer)

    def launch_director(self):
        if not self.with_director:
            return False
        if self.dirvisual:
            self.dirvisual.finalize()
            self.dirvisual = None
            return False
        else:
            self.dirvisual = WindowDirector.Director(self)
            self.dirvisual.guion.play(editing=True)
        return True

    def close_visual_script(self):
        if self.guion is not None:
            self.guion.close_pizarra()
            self.guion.cerrado = True
            self.guion = None

    def launch_guion_auto(self):
        if self.guion is not None:
            self.guion.restore_board(remove_movables_now=True)
        else:
            self.launch_guion()

    def launch_guion(self):
        if self.guion is not None:
            self.close_visual_script()
        else:
            self.guion = TabVisual.Guion(self)
            self.guion.recupera()
            self.guion.play()

    def change_the_pieces(self, cual):
        self.config_board.change_the_pieces(cual)
        self.config_board.guardaEnDisco()
        ap, apc = self.pieces_are_active, self.side_pieces_active
        si_flecha = self.arrow_sc is not None
        atajos_raton = self.atajos_raton

        self.draw_window()
        if ap:
            self.activate_side(apc)
            self.set_side_indicator(apc)

        self.atajos_raton = atajos_raton

        if si_flecha:
            self.reset_arrow_sc()

        self.init_kb_buffer()

        if self.config_board.is_base:
            nom_pieces_ori = self.config_board.nomPiezas()
            Code.all_pieces.save_all_png(nom_pieces_ori, 30)
            Delegados.genera_pm(self.pieces)
            self.main_window.pgn_refresh()
            if hasattr(self.main_window.manager, "put_view"):
                self.main_window.manager.put_view()

    def set_colors(self, li_temas, resp):
        if resp.startswith("tt_"):
            tema = li_temas[int(resp[3:])]

        else:
            fich = Code.path_resource(f"Themes/{resp[3:]}")
            tema = WBoardColors.elige_tema(self, fich)

        if tema:
            self.config_board.leeTema(tema["o_tema"])
            if "o_base" in tema:
                self.config_board.leeBase(tema["o_base"])

            self.config_board.guardaEnDisco()
            pac = self.pieces_are_active
            pac_sie = self.side_pieces_active
            self.draw_window()
            if pac and pac_sie is not None:
                self.activate_side(pac_sie)

    def reset(self, config_board):
        self.config_board = config_board
        for item in self.escena.items():
            self.xremove_item(item)
            del item
        pac = self.pieces_are_active
        pac_sie = self.side_pieces_active
        self.draw_window()
        if pac and pac_sie is not None:
            self.activate_side(pac_sie)

    @staticmethod
    def key_current_graphlive(event):
        m = event.modifiers().value
        key = ""
        if (m & QtCore.Qt.KeyboardModifier.ControlModifier.value) > 0:
            key = "CTRL"
        if (m & QtCore.Qt.KeyboardModifier.AltModifier.value) > 0:
            key += "ALT"
        if (m & QtCore.Qt.KeyboardModifier.ShiftModifier.value) > 0:
            key += "SHIFT"
        return key

    def mouse_press_graph_live(self, event, a1h8):
        if not self.configuration.x_direct_graphics:
            return
        key = self.key_current_graphlive(event)
        key += "MR"
        if self.dic_graphlive is None:
            self.dic_graphlive = self.read_graph_live()
        if key in self.dic_graphlive:
            elem = self.dic_graphlive.get(key)
            elem.a1h8 = a1h8 + a1h8
            if TabVisual.TP_FLECHA == elem.TP:
                self.current_graphlive = self.create_arrow(elem)
                self.current_graphlive.mouse_press_ext(event)
            elif TabVisual.TP_MARCO == elem.TP:
                self.current_graphlive = self.create_marco(elem)
                self.current_graphlive.mouse_press_ext(event)
            elif TabVisual.TP_CIRCLE == elem.TP:
                self.current_graphlive = self.create_circle(elem)
                self.current_graphlive.mouse_press_ext(event)
            elif TabVisual.TP_MARKER == elem.TP:
                self.current_graphlive = self.create_marker(elem)
                self.current_graphlive.mouse_press_ext(event)
            elif TabVisual.TP_SVG == elem.TP:
                self.current_graphlive = self.create_svg(elem, False)
                self.current_graphlive.mouse_press_ext(event)

            self.current_graphlive.TP = elem.TP

    def mouse_move_graph_live(self, event):
        if not self.configuration.x_direct_graphics:
            return
        if self.current_graphlive.TP in (TabVisual.TP_FLECHA, TabVisual.TP_MARCO):
            self.current_graphlive.mouse_move_ext(event)
        self.current_graphlive.update()

    def read_graph_live(self):
        dic = {}
        li = self.dbVisual.db_config["SELECTBANDA"]
        if li:
            rel = {
                0: "MR",
                1: "ALTMR",
                2: "SHIFTMR",
                3: "CTRLMR",
                4: "CTRLALTMR",
                5: "CTRLSHIFTMR",
                6: "MR1",
                7: "ALTMR1",
                8: "SHIFTMR1",
            }
            db = self.dbVisual
            for xid, pos in li:
                if xid.startswith("_F"):
                    xdb = db.db_arrows
                    tp = TabVisual.TP_FLECHA
                    obj = BoardTypes.Flecha()
                elif xid.startswith("_M"):
                    xdb = db.db_marcos
                    tp = TabVisual.TP_MARCO
                    obj = BoardTypes.Marco()
                elif xid.startswith("_D"):
                    xdb = db.db_circles
                    tp = TabVisual.TP_CIRCLE
                    obj = BoardTypes.Circle()
                elif xid.startswith("_S"):
                    xdb = db.db_svgs
                    tp = TabVisual.TP_SVG
                    obj = BoardTypes.SVG()
                elif xid.startswith("_X"):
                    xdb = db.db_markers
                    tp = TabVisual.TP_MARKER
                    obj = BoardTypes.Marker()
                else:
                    continue
                if pos in rel:
                    cnum_id = xid[3:]
                    if dic_current := xdb[cnum_id]:
                        obj.restore_dic(dic_current)
                    obj.TP = tp
                    obj.id = int(cnum_id) if cnum_id.isdigit() else cnum_id
                    obj.tpid = (tp, obj.id)
                    dic[rel[pos]] = obj
        return dic

    def remove_current_graphlive(self):
        if self.current_graphlive:
            self.current_graphlive.hide()
            del self.current_graphlive
            self.current_graphlive = None
            self.remove_last_movable()

    def mouse_release_graph_live(self, event):
        if not self.configuration.x_direct_graphics:
            return
        h8 = self.event2a1h8(event)
        if h8 is not None:
            a1 = self.current_graphlive.block_data.a1h8[:2]
            key = self.key_current_graphlive(event)
            if a1 == h8 and not key.startswith("CTRL"):
                self.remove_current_graphlive()
                key += "MR1"
                if key not in self.dic_graphlive:
                    return

                elem = self.dic_graphlive[key]
                elem.a1h8 = a1 + a1
                tp = elem.TP
                if tp == TabVisual.TP_SVG:
                    self.current_graphlive = self.create_svg(elem)
                    self.current_graphlive.TP = tp
                elif tp == TabVisual.TP_MARCO:
                    self.current_graphlive = self.create_marco(elem)
                    self.current_graphlive.TP = tp
                elif tp == TabVisual.TP_CIRCLE:
                    self.current_graphlive = self.create_circle(elem)
                    self.current_graphlive.TP = tp
                elif tp == TabVisual.TP_MARKER:
                    self.current_graphlive = self.create_marker(elem)
                    self.current_graphlive.TP = tp

            else:
                self.current_graphlive.set_a1h8(a1 + h8)
            keys = list(self.dic_movables.keys())
            if len(keys) > 1:
                last = len(keys) - 1
                bd_last = self.current_graphlive.block_data
                st = set()
                for n, (pos, item) in enumerate(self.dic_movables.items()):
                    if n != last:
                        bd = item.block_data
                        if (
                            hasattr(bd_last, "tpid")
                            and hasattr(bd, "tpid")
                            and bd_last.tpid == bd.tpid
                            and bd_last.a1h8 in (bd.a1h8, bd.a1h8[2:] + bd.a1h8[:2])
                        ):
                            st.add(self.current_graphlive)
                            st.add(item)
                for item in st:
                    self.remove_movable(item)

            self.refresh()
        self.current_graphlive = None

    def mouseMoveEvent(self, event):
        if self.dirvisual and self.dirvisual.mouseMoveEvent(event):
            return None
        pos = event.pos()
        x = pos.x()
        y = pos.y()
        minimo = self.margin_center
        maximo = self.margin_center + (self.width_square * 8)
        si_dentro = (minimo < x < maximo) and (minimo < y < maximo)
        if si_dentro and self.current_graphlive:
            return self.mouse_move_graph_live(event)

        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)
        return None

    def mouseReleaseEvent(self, event):
        if self.dirvisual and self.dirvisual.mouseReleaseEvent(event):
            return
        if self.pendingRelease:
            for objeto in self.pendingRelease:
                objeto.hide()
                del objeto
            self.escena.update()
            self.update()
            self.pendingRelease = None
        QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)
        if self.current_graphlive:
            self.mouse_release_graph_live(event)

    def event2a1h8(self, event):
        pos = event.pos()
        x = pos.x()
        y = pos.y()
        minimo = self.margin_center
        maximo = self.margin_center + (self.width_square * 8)
        if (minimo < x < maximo) and (minimo < y < maximo):
            xc = 1 + int(float(x - self.margin_center) / self.width_square)
            yc = 1 + int(float(y - self.margin_center) / self.width_square)

            if self.is_white_bottom:
                yc = 9 - yc
            else:
                xc = 9 - xc

            f = chr(48 + yc)
            c = chr(96 + xc)
            return c + f
        else:
            return None

    def mousePressEvent(self, event):
        if self.dirvisual:
            self.dirvisual.mousePressEvent(event)
            return

        a1h8 = self.event2a1h8(event)

        si_right = event.button() == QtCore.Qt.MouseButton.RightButton
        if si_right:
            if a1h8:
                self.mouse_press_graph_live(event, a1h8)
                return
            self.launch_visual_menu()
            return

        si_izq = event.button() == QtCore.Qt.MouseButton.LeftButton
        if si_izq and a1h8 is not None:
            self.remove_movables()

            if self.active_premove:
                self.main_window.manager.remove_premove()
                self.active_premove = False

        if a1h8 is None:
            if self.atajos_raton:
                self.atajos_raton(self.last_position, None)
            QtWidgets.QGraphicsView.mousePressEvent(self, event)
            return

        if self.atajos_raton:
            self.atajos_raton(self.last_position, a1h8)
            # Atajos raton lanza show_candidates si hace falta

        elif hasattr(self.main_window, "manager"):
            if hasattr(self.main_window.manager, "colect_candidates"):
                if li_c := self.main_window.manager.colect_candidates(a1h8):
                    self.show_candidates(li_c)

        QtWidgets.QGraphicsView.mousePressEvent(self, event)

    def check_leds(self):
        if not hasattr(self, "dicXML"):

            def lee(fich):
                with open(
                    Code.path_resource("IntFiles/Svg", f"{fich}.svg"), "rt", encoding="utf-8", errors="ignore"
                ) as f:
                    resp = f.read()
                return resp

            self.dicXML = {
                "C": lee("candidate"),
                "P+": lee("player_check"),
                "Px": lee("player_capt"),
                "P#": lee("player_mate"),
                "R+": lee("rival_check"),
                "Rx": lee("rival_capt"),
                "R#": lee("rival_mate"),
                "R": lee("rival"),
            }

    def mark_position_ext(self, a1, h8, tipo, ms=None):
        self.check_leds()
        lista = []
        for pos_cuadro in range(4):
            reg_svg = BoardTypes.SVG()
            reg_svg.a1h8 = a1 + h8
            reg_svg.xml = self.dicXML[tipo]
            reg_svg.siMovible = False
            reg_svg.posCuadro = pos_cuadro
            reg_svg.width_square = self.width_square
            if a1 != h8:
                reg_svg.width_square *= 7.64
            svg = BoardSVGs.SVGCandidate(self.escena, reg_svg, False)
            lista.append(svg)
        self.escena.update()

        def quita():
            for objeto in lista:
                objeto.hide()
                del objeto
            self.update()

        if ms is None:
            ms = 2500 if tipo == "C" else 1500
        QtCore.QTimer.singleShot(ms, quita)

    def mark_position(self, a1, ms=None):
        self.mark_position_ext(a1, a1, "R", ms=ms)

    # def markError(self, a1):
    #     if a1:
    #         self.mark_position_ext(a1, a1, "R")

    def show_candidates(self, li_c):
        if not li_c or not self.configuration.x_show_candidates:
            return
        self.check_leds()

        dic_pos_cuadro = {"C": 0, "P+": 1, "Px": 1, "P#": 1, "R+": 2, "R#": 2, "Rx": 3}
        self.pendingRelease = []
        for a1, tp in li_c:
            reg_svg = BoardTypes.SVG()
            reg_svg.a1h8 = a1 + a1
            reg_svg.xml = self.dicXML[tp]
            reg_svg.siMovible = False
            reg_svg.posCuadro = dic_pos_cuadro[tp]
            reg_svg.width_square = self.width_square
            svg = BoardSVGs.SVGCandidate(self.escena, reg_svg, False)
            self.pendingRelease.append(svg)
        self.escena.update()

    def mouseDoubleClickEvent(self, event):
        if item := self.itemAt(event.pos()):
            if item == self.arrow_sc:
                self.arrow_sc.hide()

    def wheelEvent(self, event):
        if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            if self.allowed_extern_resize():
                salto = event.angleDelta().y() < 0
                ap = self.config_board.width_piece()
                if ap > 500:
                    ap = 64
                ap += 2 * (+1 if salto else -1)
                if ap >= self.minimum_size:
                    self.config_board.width_piece(ap)
                    self.config_board.guardaEnDisco()
                    self.width_changed()
                    return

        elif hasattr(self.main_window, "board_wheel_event"):
            self.main_window.board_wheel_event(self, event.angleDelta().y() < 0)

    def set_dispatcher(self, mensajero, atajos_raton=None):
        if self.dirvisual:
            self.dirvisual.mensajero_changed()
        self.mensajero = mensajero
        if atajos_raton:
            self.atajos_raton = atajos_raton
        self.init_kb_buffer()

    def dbvisual_set_file(self, file):
        self.dbVisual.set_file(file)

    def dbvisual_set_show_always(self, ok):
        self.dbVisual.show_always(ok)

    def dbvisual_set_save_always(self, ok):
        self.dbVisual.save_always(ok)

    def dbvisual_close(self):
        self.dbVisual.close()

    def dbvisual_contains(self, fenm2):
        try:
            return fenm2 in self.dbVisual.db_fen and len(self.dbVisual.db_fen[fenm2]) > 0
        except AttributeError:
            return False

    def dbvisual_list(self, fenm2):
        return self.dbVisual.db_fen[fenm2]

    def dbvisual_save(self, fenm2, lista):
        if not lista:
            del self.dbVisual.db_fen[fenm2]
        else:
            self.dbVisual.db_fen[fenm2] = lista

    def save_visual_state(self):
        alm = self.reg_save_visual_state = SaveVisualState()
        alm.with_menu_visual = self.with_menu_visual
        alm.with_director = self.with_director
        alm.show_graphic_icon = self.show_graphic_icon
        alm.dirvisual = self.dirvisual
        alm.guion = self.guion
        alm.lastFenM2 = self.lastFenM2
        alm.nomdbVisual = self.dbVisual.file
        alm.dbVisual_show_always = self.dbVisual.show_always()

    def restore_visual_state(self):
        alm = self.reg_save_visual_state
        self.with_menu_visual = alm.with_menu_visual
        self.with_director = alm.with_director
        self.show_graphic_icon = alm.show_graphic_icon
        self.dirvisual = alm.dirvisual
        self.guion = alm.guion
        self.lastFenM2 = alm.lastFenM2
        self.dbVisual.set_file(alm.nomdbVisual)
        self.dbVisual.show_always(alm.dbVisual_show_always)

    def set_last_position(self, position):
        self.init_kb_buffer()
        self.close_visual_script()
        self.last_position = position
        if Code.eboard and Code.eboard.driver and self.allow_eboard:
            Code.eboard.set_position(position)
        if self.show_graphic_icon or self.dbVisual.show_always():
            fenm2 = position.fenm2()
            if self.lastFenM2 != fenm2:
                self.lastFenM2 = fenm2
                if self.dbvisual_contains(fenm2):
                    if self.show_graphic_icon:
                        self.scriptSC_menu.show()
                    if self.dbVisual.show_always():
                        self.launch_guion()
                elif self.show_graphic_icon:
                    self.scriptSC_menu.hide()

    def set_raw_last_position(self, position):
        if position != self.last_position:
            self.set_last_position(position)

    def set_position(self, position, remove_movables_now=True, variation_history=None):
        self.active_premove = False
        if self.dirvisual:
            self.dirvisual.changed_position_before()
        elif self.dbVisual.save_always():
            self.dbVisual.save_movables_board(self)

        if self.si_borraMovibles and remove_movables_now:
            self.remove_movables()

        self.set_base_position(position, variation_history=variation_history)

        if self.dirvisual:
            if self.guion:
                self.guion.close_pizarra()
            self.dirvisual.changed_position_after()

        if variation_history:
            self.activate_side(position.is_white)

    def remove_pieces(self):
        for x in self.li_pieces:
            if x[2]:
                self.xremove_item(x[1])
        self.li_pieces = []

    def move_piece_temp(self, from_a1h8, to_a1h8):
        npieza = self.get_num_piece_at(from_a1h8)
        if npieza >= 0:
            pieza_sc = self.li_pieces[npieza][1]
            row = int(to_a1h8[1])
            column = ord(to_a1h8[0]) - 96
            x = self.columna2punto(column)
            y = self.fila2punto(row)
            pieza_sc.setPos(x, y)

    def set_base_position(self, position, variation_history=None):
        self.variation_history = variation_history

        self.pieces_are_active = False
        self.remove_pieces()

        squares = position.squares

        for k in squares.keys():
            if squares[k]:
                self.ensure_piece_at(squares[k], k)

        self.escena.update()
        if self.hard_focus:
            self.setFocus()
        self.set_side_indicator(position.is_white)
        if self.arrow_sc:
            self.xremove_item(self.arrow_sc)
            del self.arrow_sc
            self.arrow_sc = None
            self.remove_arrows()
        self.init_kb_buffer()
        self.set_last_position(position)
        if self.variation_history:
            self.activate_side(position.is_white)
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def fila2punto(self, row):
        factor = (8 - row) if self.is_white_bottom else (row - 1)
        # return factor * (self.width_piece + self.margin_pieces * 2) + self.margin_center + self.tamFrontera
        return factor * self.width_square + self.margin_center + self.tamFrontera / 2 + self.margin_pieces

    def columna2punto(self, column):
        factor = (column - 1) if self.is_white_bottom else (8 - column)
        # return factor * (self.width_piece + self.margin_pieces * 2) + self.margin_center + self.tamFrontera
        return factor * self.width_square + self.margin_center + self.tamFrontera / 2 + self.margin_pieces

    def punto2fila(self, pos):
        pos -= self.margin_center + self.tamFrontera / 2 + self.margin_pieces
        pos //= self.width_square
        return int(8 - pos) if self.is_white_bottom else int(pos + 1)

    def punto2columna(self, pos):
        pos -= self.margin_center + self.tamFrontera / 2 + self.margin_pieces
        pos //= self.width_square
        return int(pos + 1) if self.is_white_bottom else int(8 - pos)

    def place_the_piece(self, bloque_pieza, pos_a1_h8):
        bloque_pieza.row = int(pos_a1_h8[1])
        bloque_pieza.column = ord(pos_a1_h8[0]) - 96
        self.replace_the_piece(bloque_pieza)

    def replace_the_piece(self, bloque_pieza):
        physical_pos = bloque_pieza.physical_pos
        physical_pos.x = self.columna2punto(bloque_pieza.column)
        physical_pos.y = self.fila2punto(bloque_pieza.row)

    def create_piece(self, cpieza, pos_a1_h8):
        bloque_pieza = BoardTypes.Pieza()
        p = bloque_pieza.physical_pos
        p.ancho = self.width_piece
        p.alto = self.width_piece
        p.orden = ZVALUE_PIECE
        bloque_pieza.pieza = cpieza
        self.place_the_piece(bloque_pieza, pos_a1_h8)
        pieza_sc = BoardElements.PiezaSC(self.escena, bloque_pieza, self)

        # pieza_sc.setOpacity(self.opacity[0 if cpieza.isupper() else 1])

        self.li_pieces.append([cpieza, pieza_sc, True])
        return pieza_sc

    def ensure_piece_at(self, piece, pos_a1_h8):
        for x in self.li_pieces:
            if not x[2] and x[0] == piece:
                piece_sc = x[1]
                self.place_the_piece(piece_sc.bloquePieza, pos_a1_h8)
                self.escena.addItem(piece_sc)
                piece_sc.update()
                x[2] = True
                return piece_sc

        return self.create_piece(piece, pos_a1_h8)

    def get_num_piece_at(self, pos_a1):
        if pos_a1 is None or len(pos_a1) < 2:
            return -1
        row = int(pos_a1[1])
        column = ord(pos_a1[0]) - 96
        for num, x in enumerate(self.li_pieces):
            if x[2]:
                pieza = x[1].bloquePieza
                if pieza.row == row and pieza.column == column:
                    return num
        return -1

    def get_piece_at(self, pos_a1):
        npieza = self.get_num_piece_at(pos_a1)
        if npieza >= 0:
            return self.li_pieces[npieza][1]
        return None

    # def dameNomPiezaEn(self, pos_a1):
    #     npieza = self.get_num_piece_at(pos_a1)
    #     if npieza >= 0:
    #         return self.li_pieces[npieza][0]
    #     return None

    # def move_pieceTemporal(self, from_a1h8, to_a1h8):
    #     npieza = self.get_num_piece_at(from_a1h8)
    #     if npieza >= 0:
    #         pieza_sc = self.li_pieces[npieza][1]
    #         row = int(to_a1h8[1])
    #         column = ord(to_a1h8[0]) - 96
    #         x = self.columna2punto(column)
    #         y = self.fila2punto(row)
    #         pieza_sc.setPos(x, y)

    def move_piece(self, from_a1h8, to_a1h8):
        npieza = self.get_num_piece_at(from_a1h8)
        if npieza >= 0:
            self.remove_piece(to_a1h8)
            pieza_sc = self.li_pieces[npieza][1]
            self.place_the_piece(pieza_sc.bloquePieza, to_a1h8)
            pieza_sc.redo_position()
            pieza_sc.update()
            self.escena.update()

    def set_piece_again(self, pos_a1):
        npieza = self.get_num_piece_at(pos_a1)
        if npieza >= 0:
            pieza_sc = self.li_pieces[npieza][1]
            pieza_sc.redo_position()
            pieza_sc.update()
            self.escena.update()

    def remove_piece(self, pos_a1):
        npieza = self.get_num_piece_at(pos_a1)
        if npieza >= 0:
            pieza_sc = self.li_pieces[npieza][1]
            self.xremove_item(pieza_sc)
            self.li_pieces[npieza][2] = False
            self.escena.update()

    # def borraPiezaTipo(self, pos_a1, tipo):
    #     row = int(pos_a1[1])
    #
    #     column = ord(pos_a1[0]) - 96
    #     for num, x in enumerate(self.li_pieces):
    #         if x[2]:
    #             pieza = x[1].bloquePieza
    #             if pieza.row == row and pieza.column == column and pieza.pieza == tipo:
    #                 pieza_sc = self.li_pieces[num][1]
    #                 self.xremove_item(pieza_sc)
    #                 self.li_pieces[num][2] = False
    #                 self.escena.update()
    #                 return

    def change_piece(self, pos_a1, nueva):
        self.remove_piece(pos_a1)
        return self.create_piece(nueva, pos_a1)

    def activate_side(self, is_white):
        self.pieces_are_active = True
        self.side_pieces_active = is_white
        for pieza, pieza_sc, is_active in self.li_pieces:
            if is_active:
                if is_white is None:
                    resp = True
                else:
                    resp = is_white if pieza.isupper() else not is_white
                pieza_sc.activate(resp)
        self.init_kb_buffer()

    # def setDispatchMove(self, rutina):
    #     for pieza, pieza_sc, is_active in self.li_pieces:
    #         if is_active:
    #             pieza_sc.setDispatchMove(rutina)

    def enable_all(self):
        self.pieces_are_active = True
        for una in self.li_pieces:
            pieza, pieza_sc, is_active = una
            if is_active:
                pieza_sc.activate(True)
        self.init_kb_buffer()

    def disable_all(self):
        self.pieces_are_active = False
        self.side_pieces_active = None
        for una in self.li_pieces:
            pieza, pieza_sc, is_active = una
            if is_active:
                pieza_sc.activate(False)
        self.init_kb_buffer()

    @staticmethod
    def num2alg(row, column):
        return chr(96 + column) + str(row)

    def alg2num(self, a1):
        x = self.columna2punto(ord(a1[0]) - 96)
        y = self.fila2punto(ord(a1[1]) - 48)
        return x, y

    def try_to_move(self, pieza_sc, pos_cursor):
        pieza = pieza_sc.bloquePieza
        from_sq = self.num2alg(pieza.row, pieza.column)

        x = int(pos_cursor.x())
        y = int(pos_cursor.y())
        cx = self.punto2columna(x)
        cy = self.punto2fila(y)

        if cx in range(1, 9) and cy in range(1, 9):
            to_sq = self.num2alg(cy, cx)

            x = self.columna2punto(cx)
            y = self.fila2punto(cy)
            pieza_sc.setPos(x, y)
            if to_sq == from_sq:
                return

            resp = self.mensajero(from_sq, to_sq)
            if resp is None:
                x, y = self.alg2num(to_sq)
                pieza_sc.setPos(x, y)
                pieza_sc.update()
                self.escena.update()
                self.init_kb_buffer()
                return

            if not resp:
                x, y = self.alg2num(from_sq)
                pieza_sc.setPos(x, y)

            # -CONTROL-
            self.init_kb_buffer()

        pieza_sc.redo_position()
        pieza_sc.update()
        self.escena.update()
        QTUtils.refresh_gui()

    def xy_a1h8(self, x, y):
        cy = self.punto2fila(y)
        cx = self.punto2columna(x)
        return self.num2alg(cy, cx)

    def a1h8_xy(self, a1h8):
        cx, cy = self.alg2num(a1h8)
        return self.columna2punto(cx), self.fila2punto(cy)

    def piece_out_position(self, position):
        si_changed = False
        for una in self.li_pieces:
            pieza, pieza_sc, is_active = una
            if position.is_white == pieza.isupper():
                x = pieza_sc.x()
                y = pieza_sc.y()
                if int(x) != pieza_sc.bloquePieza.physical_pos.x or int(y) != pieza_sc.bloquePieza.physical_pos.y:
                    si_changed = True
                    cy = self.punto2fila(y)
                    cx = self.punto2columna(x)
                    to_sq = self.num2alg(cy, cx)
                    cy = self.punto2fila(pieza_sc.bloquePieza.physical_pos.y)
                    cx = self.punto2columna(pieza_sc.bloquePieza.physical_pos.x)
                    from_sq = self.num2alg(cy, cx)
                    if to_sq != from_sq:
                        return si_changed, from_sq, to_sq
        return si_changed, None, None

    def set_side_indicator(self, is_white):
        bd = self.side_indicator_sc.block_data
        if is_white:
            bd.colorRelleno = self.config_board.sideindicator_white()
            si_abajo = self.is_white_bottom
        else:
            bd.colorRelleno = self.config_board.sideindicator_black()
            si_abajo = not self.is_white_bottom
        bd.physical_pos.y = bd.sur if si_abajo else bd.norte
        self.side_indicator_sc.mostrar()

    def reset_arrow_sc(self):
        if self.arrow_sc:
            a1h8 = self.arrow_sc.block_data.a1h8
            self.put_arrow_sc(a1h8[:2], a1h8[2:])

    def show_arrow_sc(self):
        if self.arrow_sc:
            self.arrow_sc.show()

    def put_arrow_sc(self, from_a1h8, to_a1h8):
        a1h8 = from_a1h8 + to_a1h8
        if self.arrow_sc is None:
            self.arrow_sc = self.create_arrow_sc(a1h8)
        self.arrow_sc.show()
        self.arrow_sc.set_a1h8(a1h8)
        self.arrow_sc.update()

    def put_arrow_scvar(self, li_arrows, destino=None, opacity=None):
        if destino is None:
            destino = "m"
        if opacity is None:
            opacity = 0.4
        for from_sq, to_sq in li_arrows:
            if from_sq and to_sq:
                self.create_arrow_multi(from_sq + to_sq, False, destino=destino, opacity=opacity)

    def pressed_arrow_sc(self):
        self.arrow_sc.hide()

    def create_arrow_multi(self, a1h8, is_main, destino="c", opacity=0.9):
        bf = copy.deepcopy(self.config_board.fTransicion() if is_main else self.config_board.fAlternativa())
        bf.a1h8 = a1h8
        bf.destino = destino
        bf.opacity = opacity

        arrow = self.create_arrow(bf)
        self.li_arrows.append(arrow)
        arrow.show()

    def create_arrow_sc(self, a1h8):
        bf = copy.deepcopy(self.config_board.fTransicion())
        bf.a1h8 = a1h8
        bf.width_square = self.width_square
        bf.siMovible = False

        bf.tamFrontera = self.tamFrontera

        if self.configuration.x_movement_doublebox_board:
            return BoardDoubleBoxes.DoubleBoxesSC(self.escena, bf, self.pressed_arrow_sc)
        else:
            return BoardArrows.ArrowSC(self.escena, bf, self.pressed_arrow_sc)

    def show_one_arrow_temp(self, from_a1h8, to_a1h8, is_main):
        bf = copy.deepcopy(self.config_board.fTransicion() if is_main else self.config_board.fAlternativa())
        bf.a1h8 = from_a1h8 + to_a1h8
        arrow = self.create_arrow(bf)
        self.li_arrows.append(arrow)
        arrow.show()

    def crea_doubleboxes(self, from_a1h8, to_a1h8):
        bf = copy.deepcopy(self.config_board.fTransicion())
        bf.a1h8 = from_a1h8 + to_a1h8
        bf.width_square = self.width_square
        bf.siMovible = False

        bf.tamFrontera = self.tamFrontera
        double = BoardDoubleBoxes.DoubleBoxesSC(self.escena, bf, None)
        double.show()
        self.register_movable(double)

    def show_arrow_premove(self, xfrom, xto):
        self.active_premove = True
        bf = copy.deepcopy(self.config_board.fActivo())
        bf.a1h8 = xfrom + xto
        arrow = self.create_arrow(bf)
        self.li_arrows.append(arrow)
        arrow.show()
        self.update()

    def show_arrow_tutor(self, from_a1h8, to_a1h8, factor):
        bf = copy.deepcopy(self.config_board.fTransicion())
        bf.a1h8 = from_a1h8 + to_a1h8
        bf.opacity = max(factor, 0.20)
        bf.ancho = max(bf.ancho * 2 * (factor**2.2), bf.ancho / 3)
        bf.altocabeza = max(bf.altocabeza * (factor**2.2), bf.altocabeza / 3)
        bf.vuelo = bf.altocabeza / 3
        bf.grosor = 1
        bf.redondeos = True
        bf.forma = "1"
        bf.physical_pos.orden = ZVALUE_PIECE + 1

        arrow = self.create_arrow(bf)
        self.li_arrows.append(arrow)
        arrow.show()

    def show_arrows_temp(self, lista, ms=None):
        self.show_arrows(lista)

        def quita_flechas_tmp():
            self.remove_arrows()
            if self.arrow_sc:
                self.arrow_sc.show()

        if ms is None:
            ms = 2000 if len(lista) > 1 else 1400
        QtCore.QTimer.singleShot(ms, quita_flechas_tmp)

    def show_arrows(self, lista):
        if self.arrow_sc:
            self.arrow_sc.hide()
        for from_sq, to_sq, is_main in lista:
            self.show_one_arrow_temp(from_sq, to_sq, is_main)
        QTUtils.refresh_gui()

    def show_arrow_mov(self, desde_a1h8, hasta_a1h8, modo, opacity=None):
        bf = BoardTypes.Flecha()
        bf.physical_pos.orden = ZVALUE_PIECE + 1
        bf.color = self.config_board.fTransicion().color
        bf.redondeos = False
        bf.forma = "a"

        si_pieza = self.get_num_piece_at(hasta_a1h8) > -1
        if modo == "m":  # movimientos
            bf.tipo = 2
            bf.grosor = 2
            bf.altocabeza = 6
            bf.destino = "m" if si_pieza else "c"

        elif modo == "c":  # captura
            bf.tipo = 1
            bf.grosor = 2
            bf.altocabeza = 8
            bf.destino = "m" if si_pieza else "c"

        elif modo == "tr":  # transición entre flechas
            bf.tipo = 3
            bf.grosor = 2
            bf.forma = "c"
            bf.altocabeza = 14
            bf.destino = "c"
            bf.ancho = 4
            bf.physical_pos.orden = ZVALUE_PIECE - 1

        elif modo == "2":  # m2
            bf = self.config_board.fTransicion().copia()
            bf.destino = "c"

        elif modo == "p":
            bf = self.config_board.fActivo().copia()
            bf.destino = "c"

        elif modo == "r":
            bf = self.config_board.fRival().copia()
            bf.destino = "c"

        elif modo == "pt":
            bf = self.config_board.fTransicion().copia()
            bf.destino = "c"

        elif modo == "rt":
            bf = self.config_board.fAlternativa().copia()
            bf.tipo = 1
            bf.destino = "c"

        elif modo == "ms":
            bf = self.config_board.fActivo().copia()

        elif modo == "mt":
            bf = self.config_board.fRival().copia()

        elif modo == "tb":  # takeback eboard
            bf = self.config_board.fTransicion().copia()
            bf.destino = "m"
            bf.physical_pos.orden = ZVALUE_PIECE + 1

        if self.width_piece > 24:
            bf.grosor = int(bf.grosor * 15 / 10)
            bf.altocabeza = int(bf.altocabeza * 15 / 10)

        bf.a1h8 = desde_a1h8 + hasta_a1h8
        bf.width_square = self.width_square

        if opacity:
            bf.opacity = opacity

        arrow = self.create_arrow(bf)
        self.li_arrows.append(arrow)
        arrow.show()

    def remove_arrows(self):
        for arrow in self.li_arrows:
            self.xremove_item(arrow)
            arrow.hide()
            del arrow

        self.update()

    def set_side_bottom(self, is_white_bottom):
        if self.is_white_bottom == is_white_bottom:
            return
        self.is_white_bottom = is_white_bottom
        if self.analysis_bar:
            self.analysis_bar.set_board_position()

        for ver in self.liCoordenadasVerticales:
            ver.block_data.valor = str(9 - int(ver.block_data.valor))
            ver.update()

        for hor in self.liCoordenadasHorizontales:
            hor.block_data.valor = chr(97 + 104 - ord(hor.block_data.valor))
            hor.update()

        for pieza, pieza_sc, siVisible in self.li_pieces:
            if siVisible:
                self.replace_the_piece(pieza_sc.bloquePieza)
                pieza_sc.redo_position()
                pieza_sc.update()

        self.escena.update()

    def show_coordinates(self, ok):
        for coord in self.liCoordenadasHorizontales:
            coord.setVisible(ok)
        for coord in self.liCoordenadasVerticales:
            coord.setVisible(ok)

    def pawn_promoting(self, is_white):
        if self.configuration.x_autopromotion_q:
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers != QtCore.Qt.KeyboardModifier.AltModifier:
                return "Q" if is_white else "q"
        menu = QTDialogs.LCMenu(self)
        for txt, pieza in (
            (_("Queen"), "Q"),
            (_("Rook"), "R"),
            (_("Bishop"), "B"),
            (_("Knight"), "N"),
        ):
            if not is_white:
                pieza = pieza.lower()
            menu.opcion(pieza, txt, self.pieces.icono(pieza))

        resp = menu.lanza()
        return resp or "q"

    def refresh(self):
        self.escena.update()
        QTUtils.refresh_gui()

    def pressed_number(self, is_left, activate, number):
        if not is_left:
            # si es derecho lo dejamos para el menu visual, y el izquierdo solo muestra capturas,
            # si se quieren ver movimientos, que active show candidates
            return
        if self.do_pressed_number:
            self.do_pressed_number(activate, int(number))

    def pressed_letter(self, is_left, activate, letter):
        if not is_left:
            # si es derecho lo dejamos para el menu visual, y el izquierdo solo muestra capturas,
            # si se quieren ver movimientos, que active show candidates
            return
        if self.do_pressed_letter:
            self.do_pressed_letter(activate, letter)

    def save_as_img(self, file=None, tipo=None, is_ctrl=False, is_alt=False):
        act_ind = act_scr = False
        if self.indicadorSC_menu and self.indicadorSC_menu.isVisible():
            act_ind = True
            self.indicadorSC_menu.hide()
        if self.show_graphic_icon and self.scriptSC_menu and self.scriptSC_menu.isVisible():
            act_scr = True
            self.scriptSC_menu.hide()

        if is_alt and not is_ctrl:
            pm = QtWidgets.QWidget.grab(self)
        else:
            x = 0
            y = 0
            w = self.width()
            h = self.height()
            if is_ctrl and not is_alt:
                x = self.tamFrontera
                y = self.tamFrontera
                w -= self.tamFrontera * 2
                h -= self.tamFrontera * 2
            elif is_alt and is_ctrl:
                x += self.margin_center + self.tamFrontera
                y += self.margin_center + self.tamFrontera
                w -= self.margin_center * 2 + self.tamFrontera * 2
                h -= self.margin_center * 2 + self.tamFrontera * 2
            r = QtCore.QRect(x, y, w, h)
            pm = QtWidgets.QWidget.grab(self, r)
        if file is None:
            QTUtils.set_clipboard(pm, tipo="p")
        else:
            pm.save(file, tipo)

        if act_ind:
            self.indicadorSC_menu.show()
        if act_scr:
            self.scriptSC_menu.show()

    def thumbnail(self, ancho):
        # escondemos pieces+flechas
        for pieza, pieza_sc, si_visible in self.li_pieces:
            if si_visible:
                pieza_sc.hide()
        for arrow in self.li_arrows:
            arrow.hide()
        if self.arrow_sc:
            self.arrow_sc.hide()

        pm = QtWidgets.QWidget.grab(self)
        thumb = pm.scaled(
            ancho,
            ancho,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )

        # mostramos pieces+flechas
        for pieza, pieza_sc, si_visible in self.li_pieces:
            if si_visible:
                pieza_sc.show()
        for arrow in self.li_arrows:
            arrow.show()
        if self.arrow_sc:
            self.arrow_sc.show()

        byte_array = QtCore.QByteArray()
        xbuffer = QtCore.QBuffer(byte_array)
        xbuffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        thumb.save(xbuffer, "PNG")

        bytes_io = BytesIO(byte_array)
        contents = bytes_io.getvalue()
        bytes_io.close()

        return contents

    def a1h8_fc(self, a1h8):
        if len(a1h8) < 4:
            return 0, 0, 0, 0
        df = int(a1h8[1])
        dc = ord(a1h8[0]) - 96
        hf = int(a1h8[3])
        hc = ord(a1h8[2]) - 96
        if self.is_white_bottom:
            df = 9 - df
            hf = 9 - hf
        else:
            dc = 9 - dc
            hc = 9 - hc

        return df, dc, hf, hc

    def fc_a1h8(self, df, dc, hf, hc):
        if self.is_white_bottom:
            df = 9 - df
            hf = 9 - hf
        else:
            dc = 9 - dc
            hc = 9 - hc

        return chr(dc + 96) + str(df) + chr(hc + 96) + str(hf)

    def create_marco(self, bloque_marco):
        bloque_marco_n = copy.deepcopy(bloque_marco)
        bloque_marco_n.width_square = self.width_square

        return BoardBoxes.MarcoSC(self.escena, bloque_marco_n)

    def create_circle(self, bloque_circle):
        bloque_circle = copy.deepcopy(bloque_circle)
        bloque_circle.width_square = self.width_square

        return BoardCircles.CircleSC(self.escena, bloque_circle)

    def create_svg(self, bloque_svg, is_editing=False):
        bloque_svgn = copy.deepcopy(bloque_svg)
        bloque_svgn.width_square = self.width_square

        return BoardSVGs.SVGSC(self.escena, bloque_svgn, is_editing=is_editing)

    def put_colorbox(self, a1h8, color):
        if color == NO_RATING:
            return
        if 100 not in Code.dic_markers:
            with open(Code.path_resource("IntFiles", "Svg", "eval_color.svg"), "rt") as f:
                Code.dic_markers[100] = f.read()
        xcolor = Nags.nag_color(color)
        dic = {
            'xml': Code.dic_markers[100].replace("#222222", xcolor),
            'name': 'eval_color',
            'ordenVista': 4,
        }
        reg_svg = BoardTypes.SVG(dic=dic)
        reg_svg.a1h8 = a1h8 + a1h8
        reg_svg.siMovible = False
        svg = self.create_svg(reg_svg)
        svg.block_data.psize = 110
        self.register_movable(svg)

    def put_rating(self, _from_sq, to_sq, color, poscelda):
        if color not in Code.dic_markers:
            dicm = {
                GOOD_MOVE: "good_move",
                MISTAKE: "mistake",
                VERY_GOOD_MOVE: "very_good_move",
                BLUNDER: "blunder",
                INTERESTING_MOVE: "interesting_move",
                INACCURACY: "inaccuracy",
                NO_RATING: "none",
                999: "good_move_raw",
                1000: "book",
                1001: "book_bin",
            }
            with open(Code.path_resource("IntFiles", "Svg", f"eval_{dicm[color]}.svg"), "rt") as f:
                Code.dic_markers[color] = f.read()
        dic = {
            'xml': Code.dic_markers[color],
            'name': f'eval_{color}',
            'ordenVista': 24,
        }
        reg_svg = BoardTypes.Marker(dic=dic)
        reg_svg.physical_pos.orden = 25
        reg_svg.a1h8 = to_sq + to_sq
        reg_svg.siMovible = False
        reg_svg.poscelda = poscelda
        marker = self.create_marker(reg_svg)
        self.register_movable(marker)
        self.escena.update()

    def create_marker(self, bloque_marker, is_editing=False):
        bloque_marker_n = copy.deepcopy(bloque_marker)
        bloque_marker_n.width_square = self.width_square

        return BoardMarkers.MarkerSC(self.escena, bloque_marker_n, is_editing=is_editing)

    def create_arrow(self, bloque_flecha, rutina=None):
        bloque_flecha_n = copy.deepcopy(bloque_flecha)
        bloque_flecha_n.width_square = self.width_square
        bloque_flecha_n.tamFrontera = self.tamFrontera

        return BoardArrows.ArrowSC(self.escena, bloque_flecha_n, rutina)

    def try_to_rotate_the_board(self, _is_left):
        if self.can_be_rotated:
            self.rotate_board()

    def rotate_board(self):
        self.set_side_bottom(not self.is_white_bottom)
        if self.arrow_sc:
            # self.put_arrow_sc( self.ultMovFlecha[0], self.ultMovFlecha[1])
            self.reset_arrow_sc()
        bd = self.side_indicator_sc.block_data
        self.set_side_indicator(bd.colorRelleno == self.config_board.sideindicator_white())
        for k, uno in self.dic_movables.items():
            uno.physical_pos2xy()
        for arrow in self.li_arrows:
            arrow.physical_pos2xy()
        self.escena.update()

        if hasattr(self.main_window, "capturas"):
            self.main_window.capturas.ponLayout(self.is_white_bottom)

    def register_movable(self, bloque_sc):
        self.id_last_movable += 1
        bloque_sc.id_movable = self.id_last_movable
        self.dic_movables[self.id_last_movable] = bloque_sc

    def list_movables(self):
        if not self.dic_movables:
            return []
        li = []
        for k, v in self.dic_movables.items():
            xobj = str(v)
            if "Marco" in xobj:
                tp = TabVisual.TP_MARCO
            elif "Flecha" in xobj:
                tp = TabVisual.TP_FLECHA
            elif "SVG" in xobj:
                tp = TabVisual.TP_SVG
            elif "Circle" in xobj:
                tp = TabVisual.TP_CIRCLE
            else:
                continue
            li.append((tp, v.block_data))

        return li

    def remove_movable(self, item_sc):
        for k, uno in self.dic_movables.items():
            if uno == item_sc:
                del self.dic_movables[k]
                self.xremove_item(uno)
                return

    def remove_last_movable(self):
        if keys := list(self.dic_movables.keys()):
            self.xremove_item(self.dic_movables[keys[-1]])
            del self.dic_movables[keys[-1]]

    def remove_movables(self):
        for k, uno in self.dic_movables.items():
            self.xremove_item(uno)
        self.dic_movables = collections.OrderedDict()
        self.lastFenM2 = None

    def lock_rotation(self, si_bloquea):  # se usa en la presentacion para que no rote
        self.can_be_rotated = not si_bloquea

    def set_dispatch_size(self, rutina_control):
        self.dispatch_size = rutina_control

    # def boundingRect(self):
    #     return QtCore.QRect(0, 0, self.ancho, self.ancho)

    def fen_active(self):
        li = []
        li.extend(["", "", "", "", "", "", "", ""] for _ in range(8))
        for x in self.li_pieces:
            if x[2]:
                pieza_sc = x[1]
                bp = pieza_sc.bloquePieza
                li[8 - bp.row][bp.column - 1] = x[0]

        lineas = []
        for x in range(8):
            uno = ""
            num = 0
            for y in range(8):
                if li[x][y]:
                    if num:
                        uno += str(num)
                        num = 0
                    uno += li[x][y]
                else:
                    num += 1
            if num:
                uno += str(num)
            lineas.append(uno)

        bd = self.side_indicator_sc.block_data
        is_white = bd.colorRelleno == self.config_board.sideindicator_white()

        resto = f"{'w' if is_white else 'b'} KQkq - 0 1"
        return f"{'/'.join(lineas)} {resto}"

    def copia_posicion_de(self, otro_board):
        for x in self.li_pieces:
            if x[2]:
                self.xremove_item(x[1])
        self.li_pieces = []
        for cpieza, pieza_sc, is_active in otro_board.li_pieces:
            if is_active:
                physical_pos = pieza_sc.bloquePieza
                f = physical_pos.row
                c = physical_pos.column
                pos_a1_h8 = chr(c + 96) + str(f)
                self.create_piece(cpieza, pos_a1_h8)

        if not otro_board.is_white_bottom:
            self.rotate_board()

        if otro_board.side_indicator_sc.isVisible():
            bd_ot = otro_board.side_indicator_sc.block_data
            is_white = bd_ot.colorRelleno == otro_board.colorBlancas
            si_indicador_abajo = bd_ot.physical_pos.y == bd_ot.sur

            bd = self.side_indicator_sc.block_data
            bd.physical_pos.y = bd.sur if si_indicador_abajo else bd.norte
            bd.colorRelleno = (
                self.config_board.sideindicator_white() if is_white else self.config_board.sideindicator_black()
            )
            self.side_indicator_sc.mostrar()

        if otro_board.arrow_sc and otro_board.arrow_sc.isVisible():
            a1h8 = otro_board.arrow_sc.block_data.a1h8
            desde_a1h8, hasta_a1h8 = a1h8[:2], a1h8[2:]
            self.put_arrow_sc(desde_a1h8, hasta_a1h8)

        self.escena.update()
        self.setFocus()

    def finalize(self):
        if self.dirvisual:
            self.dirvisual.finalize()

    def allow_takeback(self):
        return (
            hasattr(self.main_window, "manager")
            and hasattr(self.main_window.manager, "run_action")
            and hasattr(self.main_window.manager, "takeback")
        )

    def set_tmp_position(self, position):
        self.pieces_are_active = False
        self.remove_pieces()

        squares = position.squares
        for k in squares.keys():
            if squares[k]:
                self.ensure_piece_at(squares[k], k)

        self.escena.update()
        if self.hard_focus:
            self.setFocus()
        self.set_side_indicator(position.is_white)
        if self.arrow_sc:
            self.xremove_item(self.arrow_sc)
            del self.arrow_sc
            self.arrow_sc = None
            self.remove_arrows()
        self.init_kb_buffer()
        self.pieces_are_active = True
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def play_current_position(self):
        if hasattr(self.main_window, "manager") and hasattr(self.main_window.manager, "play_current_position"):
            self.main_window.manager.play_current_position()
        else:
            gm = Game.Game(first_position=self.last_position)
            dic = {"GAME": gm.save(), "ISWHITE": gm.last_position.is_white}
            fich = Util.relative_path(self.configuration.temporary_file("pkd"))
            Util.save_pickle(fich, dic)

            XRun.run_lucas("-play", fich)

    def show_lichess_graphics(self, comment: str):
        squares, arrows = LichessCommentParser.parse_lichess_graphics(comment)
        square: LichessCommentParser.ColoredSquare
        arrow: LichessCommentParser.Arrow

        xdic_colors = {
            "G": 0x15781B,
            "R": 0x882020,
            "Y": 0xE68F00,
            "B": 0x003088,
        }
        for square in squares:
            elem = BoardTypes.Circle()
            elem.a1h8 = square.square + square.square
            elem.color = xdic_colors.get(square.color, xdic_colors["G"])
            elem.grosor = 4
            elem.ordenVista = 4
            elem.opacity = 0.8
            elem.tamFrontera = self.tamFrontera

            self.register_movable(self.create_circle(elem))

        for arrow in arrows:
            elem = BoardTypes.Flecha()
            elem.a1h8 = arrow.origin + arrow.target
            elem.grosor = 1
            elem.altocabeza = 20
            elem.tipo = 1
            elem.destino = "c"
            elem.color = xdic_colors.get(arrow.color, xdic_colors["R"])
            elem.colorinterior = elem.color
            elem.width_square = self.width_square
            elem.opacity = 0.5
            elem.redondeos = True
            elem.forma = "1"
            elem.ancho = 4
            elem.vuelo = 8
            elem.descuelgue = 0
            elem.width_square = self.width_square
            elem.siMovible = False
            elem.ordenVista = 5
            elem.tamFrontera = self.tamFrontera

            self.register_movable(self.create_arrow(elem))

    # -----------------------------------------------------------------------------------------------------  VISUALMENU

    def launch_visual_menu(self):
        return self.visual_menu.launch_visual_menu() if self.with_menu_visual else None

    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------      EBOARD

    def try_eboard_takeback(self, side):
        return self.eboard.try_eboard_takeback(side)

    def dispatch_eboard(self, quien, a1h8):
        return self.eboard.dispatch_eboard(quien, a1h8)

    def disable_eboard_here(self):
        return self.eboard.disable_eboard_here()

    def enable_eboard_here(self):
        return self.eboard.enable_eboard_here()

    def eboard_arrow(self, a1, h8, prom):
        return self.eboard.eboard_arrow(a1, h8, prom)

    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------   BLINDFOLD

    def show_pieces(self, is_white, is_black):
        return self.blindfold_controller.show_pieces(is_white, is_black)

    def blindfold_change(self):
        return self.blindfold_controller.blindfold_change()

    def blindfold_reset(self):
        return self.blindfold_controller.blindfold_reset()

    def blindfold_remove(self):
        return self.blindfold_controller.blindfold_remove()

    def blindfold_config(self):
        return self.blindfold_controller.blindfold_config()

    def blindfold_something(self):
        return self.blindfold_controller.blind_sides() is not None

    # -----------------------------------------------------------------------------------------------------------------
