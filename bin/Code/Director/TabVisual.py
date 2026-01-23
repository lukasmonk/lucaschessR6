import copy
import time
from typing import Callable, Any

import Code
from Code.Z import Util
from Code.Base import Position
from Code.Board import BoardTypes
from Code.SQL import UtilSQL
from Code.Translations import TrListas


class PFlecha(BoardTypes.Flecha):
    def __init__(self):
        BoardTypes.Flecha.__init__(self)
        self.name = ""
        self.id = None


class PMarco(BoardTypes.Marco):
    def __init__(self):
        BoardTypes.Marco.__init__(self)
        self.name = ""
        self.id = None


class PCircle(BoardTypes.Circle):
    def __init__(self):
        BoardTypes.Circle.__init__(self)
        self.name = ""
        self.id = None


class PSVG(BoardTypes.SVG):
    def __init__(self):
        BoardTypes.SVG.__init__(self)
        self.name = ""
        self.id = None


class PMarker(BoardTypes.Marker):
    def __init__(self):
        BoardTypes.Marker.__init__(self)
        self.name = ""
        self.id = None


(
    TP_FLECHA,
    TP_MARCO,
    TP_TEXTO,
    TP_SVG,
    TP_MARKER,
    TP_PIEZACREA,
    TP_PIEZAMUEVE,
    TP_PIEZABORRA,
    TP_ACTION,
    TP_CONFIGURATION,
    TP_CIRCLE,
) = ("F", "M", "T", "S", "X", "PC", "PM", "PB", "A", "C", "D")


class GTarea:
    def __init__(self, guion, tp):
        self.guion = guion
        self._id = Util.huella()
        self._tp = tp
        self._marcado = False
        self._orden = 0
        self._name = None
        self._registro = None
        self.xmarcadoOwner = False

    def id(self):
        return self._id

    def tp(self):
        return self._tp

    def marcado(self, si=None):
        if si is not None:
            self._marcado = bool(si)
        return self._marcado

    def marked_owner(self, si=None):
        if si is not None:
            self.xmarcadoOwner = bool(si)
        return self.xmarcadoOwner

    def name(self, name=None):
        if name is not None:
            self._name = name
        return self._name if self._name else ""

    def registro(self, valores=None):
        if valores:
            self._registro = valores
        return self._registro

    def guarda(self):
        reg = {}
        for atr in dir(self):
            if atr.startswith("_") and not atr.startswith("__"):
                if atr == "_item_sc" and self._item_sc:
                    reg["_bloqueDatos"] = self._item_sc.block_data
                else:
                    valor = getattr(self, atr)
                    reg[atr] = valor
        return reg

    def recupera(self, reg):
        for atr in reg:
            if atr.startswith("_") and not atr.startswith("__") and atr != "_id":
                valor = reg[atr]
                setattr(self, atr, valor)


class GTItem(GTarea):
    def __init__(self, guion, tp):
        GTarea.__init__(self, guion, tp)
        self._item_sc = None
        self._bloqueDatos = None
        self.xitemSCOwner = None

    def item_sc(self, sc=None):
        if sc is not None:
            self._item_sc = sc
            if self._bloqueDatos is None:
                self._bloqueDatos = self.block_data()
        return self._item_sc

    def remove_item_sc_owner(self):
        self.xitemSCOwner = None
        self.marked_owner(False)

    def item_sc_owner(self, sc=None):
        if sc is not None:
            self.xitemSCOwner = sc
        return self.xitemSCOwner

    def a1h8(self):
        bd = self._item_sc.block_data
        return bd.a1h8

    def block_data(self):
        return self._item_sc.block_data

    def name(self, name=None):
        if name is not None:
            self._name = name
        if self._name:
            return self._name
        if self._name:
            return self._name
        if self._item_sc and self._item_sc.block_data and getattr(self._item_sc.block_data, "name"):
            if self._item_sc.block_data.name:
                return self._item_sc.block_data.name
        return self._bloqueDatos.name

    def coordina(self):
        if self.xitemSCOwner:
            if self.tp() == TP_SVG:
                self.xitemSCOwner.coordinate_position_with_other(self._item_sc)
                self.xitemSCOwner.update()
            else:
                bf = copy.deepcopy(self._item_sc.block_data)
                bf.width_square = self.xitemSCOwner.block_data.width_square
                self.xitemSCOwner.block_data = bf
                self.xitemSCOwner.reset()
            self.xitemSCOwner.escena.update()


class GTTexto(GTarea):
    def __init__(self, guion):
        GTarea.__init__(self, guion, TP_TEXTO)
        self._texto = None
        self._continuar = None

    def texto(self, txt=None):
        if txt is not None:
            self._texto = txt
        return self._texto

    def continuar(self, ok=None):
        if ok is not None:
            self._continuar = ok
        return self._continuar

    def info(self):
        mas_texto = "? " if self._continuar else ""
        if not self._texto:
            return mas_texto
        if "</head>" in self._texto:
            li = self._texto.split("</head>")[1].split("<")
            for n in range(len(li)):
                li1 = li[n].split(">")
                if len(li1) == 2:
                    li[n] = li1[1]
            return mas_texto + "".join(li)
        else:
            return mas_texto + self._texto

    @staticmethod
    def txt_tipo():
        return _("Text")

    def run(self):
        self.guion.write_pizarra(self)

    def __str__(self):
        return f"TEXT {self._texto}"


class GTArrow(GTItem):
    def __init__(self, guion):
        GTItem.__init__(self, guion, TP_FLECHA)

    @staticmethod
    def txt_tipo():
        return _("Arrow")

    def info(self):
        if self._item_sc:
            bd = self._item_sc.block_data
        else:
            bd = self._bloqueDatos
        return bd.a1h8

    def run(self):
        if self._bloqueDatos:
            sc = self.guion.board.create_arrow(self._bloqueDatos)
            sc.set_routine_if_pressed(None, self.id())
            self.item_sc(sc)
            self.marcado(True)
            if self._item_sc:
                self._item_sc.show()


class GTMarco(GTItem):
    def __init__(self, guion):
        GTItem.__init__(self, guion, TP_MARCO)

    @staticmethod
    def txt_tipo():
        return _("Box")

    def info(self):
        if self._item_sc:
            bd = self._item_sc.block_data
            return bd.a1h8
        return ""

    def run(self):
        if self._item_sc:
            self._item_sc.show()

        sc = self.guion.board.create_marco(self._bloqueDatos)
        sc.set_routine_if_pressed(None, self.id())
        self.item_sc(sc)
        self.marcado(True)


class GTCircle(GTItem):
    def __init__(self, guion):
        GTItem.__init__(self, guion, TP_CIRCLE)

    @staticmethod
    def txt_tipo():
        return _("Circle")

    def info(self):
        if self._item_sc:
            bd = self._item_sc.block_data
            return bd.a1h8
        return self._bloqueDatos.a1h8

    def run(self):
        if self._item_sc:
            self._item_sc.show()

        sc = self.guion.board.create_circle(self._bloqueDatos)
        sc.set_routine_if_pressed(None, self.id())
        self.item_sc(sc)
        self.marcado(True)


class GTSvg(GTItem):
    def __init__(self, guion):
        GTItem.__init__(self, guion, TP_SVG)

    @staticmethod
    def txt_tipo():
        return _("Image")

    def info(self):
        x, y, w, h = self.get_datos()
        a1h8 = self.guion.board.fc_a1h8(int(y) + 1, int(x) + 1, int(y + h) + 1, int(x + w) + 1)
        return "%s+[%.02f,%.02f]    ➝ %.02f   ↓ %.02f" % (
            a1h8[:2],
            x - int(x),
            y - int(y),
            w,
            h,
        )

    def get_datos(self):
        bd = self._item_sc.block_data
        p = bd.physical_pos

        def f(n):
            return float(n * 1.0 / bd.width_square)

        return f(p.x), f(p.y), f(p.ancho), f(p.alto)

    def set_datos(self, col, fil, ancho, alto):
        bd = self._item_sc.block_data
        p = bd.physical_pos

        def f(n):
            return float(n * bd.width_square)

        p.x = f(col)
        p.y = f(fil)
        p.ancho = f(ancho)
        p.alto = f(alto)

    def run(self):
        if self._item_sc:
            self._item_sc.show()

        is_editing = self.guion.is_editing()

        sc = self.guion.board.create_svg(self._bloqueDatos, is_editing=is_editing)
        sc.set_routine_if_pressed(None, self.id())
        sc.block_data = self._bloqueDatos  # necesario para svg con physical_pos no ajustado a squares
        sc.update()
        self.item_sc(sc)
        self.marcado(True)


class GTMarker(GTItem):
    def __init__(self, guion):
        GTItem.__init__(self, guion, TP_MARKER)

    @staticmethod
    def txt_tipo():
        return _("Marker")

    def info(self):
        bd = self._item_sc.block_data
        return bd.a1h8

    def run(self):
        if self._item_sc:
            self._item_sc.show()

        is_editing = self.guion.is_editing()
        sc = self.guion.board.create_marker(self._bloqueDatos, is_editing=is_editing)
        self.item_sc(sc)
        self.marcado(True)


class GTAction(GTarea):
    def __init__(self, guion):
        (
            self.GTA_INICIO,
            self.GTA_MAINARROW_REMOVE,
            self.GTA_PIECES_REMOVEALL,
            self.GTA_GRAPHICS_REMOVEALL,
            self.GTA_PIZARRA_REMOVE,
        ) = ("I", "MAR", "PRA", "GRA", "PR")
        self.dicTxt = {
            self.GTA_INICIO: _("Initial physical pos"),
            self.GTA_MAINARROW_REMOVE: _("Remove main arrow"),
            self.GTA_PIECES_REMOVEALL: _("Remove all pieces"),
            self.GTA_GRAPHICS_REMOVEALL: _("Remove all graphics"),
            self.GTA_PIZARRA_REMOVE: _("Remove text"),
        }

        GTarea.__init__(self, guion, TP_ACTION)
        self._action = None

    def action(self, action=None):
        if action:
            self._action = action
        return self._action

    @staticmethod
    def txt_tipo():
        return _("Action")

    def info(self):
        return self.dicTxt[self._action] if self._action else "?"

    def run(self):
        guion = self.guion
        board = guion.board
        if self._action == self.GTA_INICIO:
            guion.restore_board()
        elif self._action == self.GTA_MAINARROW_REMOVE:
            if board.arrow_sc:
                board.arrow_sc.hide()
        elif self._action == self.GTA_PIECES_REMOVEALL:
            board.remove_pieces()
        elif self._action == self.GTA_GRAPHICS_REMOVEALL:
            board.remove_movables()
        elif self._action == self.GTA_PIZARRA_REMOVE:
            guion.close_pizarra()


class GTConfiguration(GTarea):
    GTC_TRANSITION, GTC_NEXT_TRANSITION = "T", "NT"
    dicTxt = {
        GTC_TRANSITION: "General transition time",
        GTC_NEXT_TRANSITION: "Next transition time",
    }

    def __init__(self, guion):
        GTarea.__init__(self, guion, TP_CONFIGURATION)
        self._configuration = None
        self._value = 0

    def configuration(self, configuration=None):
        if configuration:
            self._configuration = configuration
        return self._configuration

    def value(self, value=None):
        if isinstance(value, int):
            self._value = value
        return self._value

    @staticmethod
    def txt_tipo():
        return _("Configuration")

    def info(self):
        return "%d=%s" % (
            self._value,
            self.dicTxt[self._configuration] if self._configuration else "?",
        )

    def run(self):
        guion = self.guion
        if self._configuration == self.GTC_TRANSITION:
            guion.transition = self._value
        elif self._configuration == self.GTC_NEXT_TRANSITION:
            guion.nextTransition = self._value


class GTPieceMove(GTarea):
    def __init__(self, guion):
        GTarea.__init__(self, guion, TP_PIEZAMUEVE)
        self._desde = None
        self._hasta = None
        self._borra = None
        self._position = None

    def set_position(self, physical_pos):
        self._position = physical_pos

    def physical_pos(self):
        return self._position

    def remove_from_to(self, from_sq=None, to_sq=None, pieza_borra=None):
        if from_sq is not None:
            self._desde = from_sq
            self._hasta = to_sq
            self._borra = pieza_borra
        return self._desde, self._hasta, self._borra

    @staticmethod
    def txt_tipo():
        return _("Move piece")

    def info(self):
        return f"{self._desde} -> {self._hasta}"

    def run(self):
        self.guion.mueve_pieza(self._desde, self._hasta)


class GTPieceCreate(GTarea):
    def __init__(self, guion):
        GTarea.__init__(self, guion, TP_PIEZACREA)
        self._pieza = None
        self._desde = None
        self._borra = None

    def from_sq(self, from_sq=None, borra=None):
        if from_sq is not None:
            self._desde = from_sq
            self._borra = borra
        return self._desde, self._borra

    def pieza(self, pz=None):
        if pz is not None:
            self._pieza = pz
        return self._pieza

    @staticmethod
    def txt_tipo():
        return _("Create piece")

    def info(self):
        pz = TrListas.letter_piece(self._pieza)
        return f"{pz if pz.isupper() else pz.lower()} -> {self._desde}"

    def run(self):
        self.guion.crea_pieza(self._pieza, self._desde)


class GTPieceRemove(GTarea):
    def __init__(self, guion):
        GTarea.__init__(self, guion, TP_PIEZABORRA)
        self._pieza = None
        self._desde = None

    def from_sq(self, from_sq=None):
        if from_sq is not None:
            self._desde = from_sq
        return self._desde

    def pieza(self, pz=None):
        if pz is not None:
            self._pieza = pz
        return self._pieza

    @staticmethod
    def txt_tipo():
        return _("Delete piece")

    def info(self):
        pz = TrListas.letter_piece(self._pieza)
        return f"{pz if pz.isupper() else pz.lower()} -> {self._desde}"

    def run(self):
        self.guion.borra_pieza(self._desde)


class Guion:
    board_last_position: Position.Position
    board_activasPiezas: tuple[bool, bool]
    board_mensajero: Callable
    board_is_white_bottom: bool
    board_arrow_sc: Any

    def __init__(self, board, win_director=None):
        self.liGTareas = []
        self.pizarra = None
        self.anchoPizarra = 250
        self.posPizarra = "R"
        self.board = board
        self.win_director = win_director
        self.save_board()
        self.cerrado = False

    def is_editing(self):
        return self.win_director is not None

    def save_board(self):
        self.board_last_position = self.board.last_position
        self.board_is_white_bottom = self.board.is_white_bottom
        if self.board.arrow_sc and self.board.arrow_sc.isVisible():
            a1h8 = self.board.arrow_sc.block_data.a1h8
            self.board_arrow_sc = a1h8[:2], a1h8[2:]
        else:
            self.board_arrow_sc = None

        if self.win_director:
            if getattr(self, "board_mensajero", None) != self.win_director.move_piece:
                self.board_mensajero = self.board.mensajero
                self.board.mensajero = self.win_director.move_piece

        self.board_activasPiezas = (
            self.board.pieces_are_active,
            self.board.side_pieces_active,
        )

    def restore_board(self, remove_movables_now=False):
        self.board.dirvisual = None
        self.board.set_position(self.board_last_position, remove_movables_now=remove_movables_now)
        if self.board_arrow_sc:
            from_sq, to_sq = self.board_arrow_sc
            self.board.put_arrow_sc(from_sq, to_sq)
        if self.win_director:
            self.board.mensajero = self.board_mensajero
        if self.board_activasPiezas[0]:
            self.board.activate_side(self.board_activasPiezas[1])
        self.board.with_director = True
        self.close_pizarra()

    def new_task(self, tarea, row=-1):
        if row == -1:
            self.liGTareas.append(tarea)
            row = len(self.liGTareas) - 1
        else:
            self.liGTareas.insert(row, tarea)
        return row

    def saved_pizarra(self):
        self.win_director.refresh_guion()

    def write_pizarra(self, tarea):
        if self.pizarra is None:
            self.pizarra = BoardTypes.Pizarra(
                self,
                self.board,
                self.anchoPizarra,
                edit_mode=self.win_director is not None,
                with_continue=tarea.continuar(),
            )
            self.pizarra.mensaje.setFocus()
        self.pizarra.write(tarea)
        self.pizarra.show()

    def close_pizarra(self):
        if self.pizarra:
            self.pizarra.close()
            self.pizarra = None

    def remove_pizarra_active(self):
        if self.win_director:
            self.win_director.remove_pizarra_active()
        else:
            self.close_pizarra()

    # def nuevaCopia(self, ntarea):
    #     tarea = copy.copy(self.tarea(ntarea))
    #     tarea._id = Util.huella()
    #     return self.new_task(tarea, ntarea + 1)

    def borra(self, ntask):
        if ntask < len(self.liGTareas):
            del self.liGTareas[ntask]

    def change_mark_task(self, ntask, valor):
        tarea = self.liGTareas[ntask]
        tarea.marcado(valor)
        return tarea

    # def cambiaMarcaTareaOwner(self, nTarea, valor):
    #     tarea = self.liGTareas[nTarea]
    #     tarea.marked_owner(valor)
    #     return tarea

    def tasks_item(self, item):
        for n, tarea in enumerate(self.liGTareas):
            if isinstance(tarea, GTItem) and tarea.item_sc() == item:
                return tarea, n
        return None, -1

    def tasks_in_position(self, pos):
        li = []
        for n, tarea in enumerate(self.liGTareas):
            if isinstance(tarea, GTItem) and tarea.item_sc() and tarea.item_sc().contain(pos):
                li.append((n, tarea))
        return li

    def item_of_task(self, ntask):
        if ntask < len(self.liGTareas):
            tarea = self.liGTareas[ntask]
            return tarea.item_sc() if isinstance(tarea, GTItem) else None
        return None

    # def itemTareaOwner(self, nTarea):
    #     tarea = self.liGTareas[nTarea]
    #     return tarea.item_sc_owner() if isinstance(tarea, GTItem) else None

    # def borraItemTareaOwner(self, nTarea):
    #     tarea = self.liGTareas[nTarea]
    #     if isinstance(tarea, GTItem):
    #         tarea.remove_item_sc_owner()

    def marcado(self, ntask):
        return self.liGTareas[ntask].marcado()

    def marked_owner(self, ntask):
        return self.liGTareas[ntask].marked_owner()

    def unmark_item(self, item):
        for tarea in self.liGTareas:
            if isinstance(tarea, GTItem) and tarea.item_sc() == item:
                tarea.marcado(False)
                return

    def id(self, ntask):
        return self.liGTareas[ntask].id()

    def tarea(self, ntask):
        nlig_tareas = len(self.liGTareas)
        if nlig_tareas == 0:
            return None
        if ntask < 0:
            return self.liGTareas[ntask] if nlig_tareas >= abs(ntask) else None
        else:
            return self.liGTareas[ntask] if ntask < nlig_tareas else None

    def remove_last_repetition(self):
        len_li = len(self.liGTareas)
        if len_li > 1:
            ult_tarea = self.liGTareas[-1]
            if hasattr(ult_tarea, "_item_sc"):
                ult_bd = ult_tarea.block_data()
                ult_tp, ult_xid = ult_bd.tpid
                ult_a1h8 = ult_bd.a1h8
                for pos in range(len_li - 1):
                    tarea = self.liGTareas[pos]
                    if hasattr(tarea, "_item_sc"):
                        bd = tarea.item_sc().block_data
                        t_tp, t_xid = bd.tpid
                        t_a1h8 = bd.a1h8
                        t_h8a1 = t_a1h8[2:] + t_a1h8[:2]
                        if ult_tp == t_tp and ult_xid == t_xid and ult_a1h8 in (t_a1h8, t_h8a1):
                            return [pos, len_li - 1]
        return False

    def arriba(self, task):
        if task > 0:
            self.liGTareas[task], self.liGTareas[task - 1] = (
                self.liGTareas[task - 1],
                self.liGTareas[task],
            )
            return True
        else:
            return False

    def abajo(self, task):
        if task < (len(self.liGTareas) - 1):
            self.liGTareas[task], self.liGTareas[task + 1] = (
                self.liGTareas[task + 1],
                self.liGTareas[task],
            )
            return True
        else:
            return False

    def __len__(self):
        return len(self.liGTareas)

    def txt_tipo(self, row):
        tarea = self.liGTareas[row]
        return tarea.txt_tipo()

    def name(self, row):
        tarea = self.liGTareas[row]
        return tarea.name()

    def info(self, row):
        tarea = self.liGTareas[row]
        return tarea.info()

    def guarda(self):
        lista = []
        for tarea in self.liGTareas:
            lista.append(tarea.guarda())
        return lista

    def restore_reg(self, reg):
        dic = {
            TP_FLECHA: GTArrow,
            TP_MARCO: GTMarco,
            TP_CIRCLE: GTCircle,
            TP_SVG: GTSvg,
            TP_MARKER: GTMarker,
            TP_TEXTO: GTTexto,
            TP_PIEZACREA: GTPieceCreate,
            TP_PIEZAMUEVE: GTPieceMove,
            TP_PIEZABORRA: GTPieceRemove,
            TP_ACTION: GTAction,
            TP_CONFIGURATION: GTConfiguration,
        }
        tarea = dic[reg["_tp"]](self)
        tarea.recupera(reg)
        self.new_task(tarea, -1)
        return tarea

    def restore_movables_board(self):
        st_previos = set()
        if self.board.dic_movables:
            task = None
            for k, item in self.board.dic_movables.items():
                bd = item.block_data
                if hasattr(bd, "tpid"):
                    tp, xid = bd.tpid
                    if tp == TP_FLECHA:
                        task = GTArrow(self)

                    elif tp == TP_MARCO:
                        task = GTMarco(self)

                    elif tp == TP_CIRCLE:
                        task = GTCircle(self)

                    elif tp == TP_SVG:
                        task = GTSvg(self)

                    elif tp == TP_MARKER:
                        task = GTMarker(self)
                    task.item_sc(item)
                    self.new_task(task)
                    st_previos.add((tp, xid, bd.a1h8))
        return st_previos

    def recupera(self):
        fenm2 = self.board.last_position.fenm2()
        lista = self.board.dbvisual_list(fenm2)
        self.liGTareas = []
        if lista is not None:
            for reg in lista:
                self.restore_reg(reg)
        else:
            lista = []

        li_previos = self.board.list_movables()
        self.board.remove_movables()
        for tp, bloquedatos in li_previos:
            esta = False
            for reg in lista:
                if tp == reg["_tp"]:
                    bloquedatos_reg = reg["_bloqueDatos"]
                    ok = True
                    li_campos = [
                        x
                        for x in dir(bloquedatos_reg)
                        if not x.startswith("_")
                        and x not in ('copia', 'physical_pos', 'restore_dic', 'save_dic', 'tipoqt')
                    ]
                    for x in li_campos:
                        if x[0] != "_" and getattr(bloquedatos, x, None) != getattr(bloquedatos_reg, x):
                            ok = False
                            break
                    if ok:
                        esta = True
                        break
            if not esta:
                reg = {
                    '_bloqueDatos': bloquedatos,
                    '_marcado': True,
                    '_name': None,
                    '_orden': 0,
                    '_registro': None,
                    '_tp': tp,
                }
                self.restore_reg(reg)

        if self.win_director:
            for tarea in self.liGTareas:
                if tarea.tp() not in (TP_ACTION, TP_CONFIGURATION, TP_TEXTO):
                    # if not hasattr("tarea", "_item_sc") or not tarea._item_sc():
                    #      tarea.run()
                    tarea.marcado(True)
                else:
                    tarea.marcado(False)

    def play(self, editing=False):
        self.cerrado = False
        for tarea in self.liGTareas:
            if editing and not tarea.marcado():
                continue
            if not hasattr("tarea", "item_sc") or not tarea.item_sc():
                tarea.run()
            if tarea.tp() == TP_TEXTO and tarea.continuar():
                while self.pizarra is not None and self.pizarra.is_blocked():
                    time.sleep(0.05)
                if self.pizarra:
                    self.pizarra.close()
                    self.pizarra = None
            if self.cerrado:
                return

    def mueve_pieza(self, xfrom, xto):
        self.board.move_piece(xfrom, xto)
        self.board.put_arrow_sc(xfrom, xto)

    def borra_pieza(self, xfrom):
        self.board.remove_piece(xfrom)

    def crea_pieza(self, pieza, xfrom):
        self.board.create_piece(pieza, xfrom)


class DBManagerVisual:
    _filepath: str

    def __init__(self, file, show_always=False, save_always=False):
        self._db_fen = self._db_config = None
        self._db_arrows = self._db_marcos = self._db_svgs = self._db_markers = self._db_circles = None
        self._show_always = show_always
        self._save_always = save_always
        self.set_file(file)

    def save_movables_board(self, board):
        fenm2 = board.lastFenM2
        if not fenm2:
            return
        dic_movables = board.dic_movables
        n = 0
        for k, v in dic_movables.items():
            if hasattr(v, "block_data") and hasattr(v.block_data, "tpid"):
                n += 1
        if n == 0:
            if fenm2 in self.db_fen:
                del self.db_fen[fenm2]
            return
        guion = Guion(board)
        guion.restore_movables_board()
        self.db_fen[fenm2] = guion.guarda()

    def save_always(self, yesno=None):
        if yesno is not None:
            self._save_always = yesno
        return self._save_always

    def show_always(self, yesno=None):
        if yesno is not None:
            self._show_always = yesno
        return self._show_always

    def set_file(self, file):
        self.close()
        self._filepath = file if file is not None else Code.configuration.paths.file_resources()
        if not Util.exist_file(self._filepath):
            Util.file_copy(Code.path_resource("IntFiles", "recursos.dbl"), self._filepath)

    def reset(self):
        self.close()

        def reset_table(name, zap):
            path_resources = Code.path_resource("IntFiles", "recursos.dbl")
            with (
                UtilSQL.DictRawSQL(self._filepath, tabla=name) as dba,
                UtilSQL.DictRawSQL(path_resources, tabla=name) as dbr,
            ):
                if zap:
                    dba.zap()
                for k, v in dbr.as_dictionary().items():
                    dba[k] = v

        for table_name in (
            "Config",
            "Flechas",
            "Marcos",
            "Circles",
            "SVGs",
            "Markers",
        ):  # Todos menos FEN
            reset_table(table_name, table_name != "Config")

    def remove_fens(self):
        self.close()
        with UtilSQL.DictRawSQL(self._filepath, tabla="FEN") as dbf:
            dbf.zap()

    @property
    def file(self):
        return self._filepath

    @property
    def db_fen(self):
        if self._db_fen is None:
            self._db_fen = UtilSQL.DictSQL(self._filepath, tabla="FEN")
            self._db_fen.wrong_pickle(b"Physicalphysical_pos", b"PhysicalPos")
        return self._db_fen

    @property
    def db_config(self):
        if self._db_config is None:
            self._db_config = UtilSQL.DictSQL(self._filepath, tabla="Config")
        return self._db_config

    @property
    def db_arrows(self):
        if self._db_arrows is None:
            self._db_arrows = UtilSQL.DictSQL(self._filepath, tabla="Flechas")
        return self._db_arrows

    @property
    def db_marcos(self):
        if self._db_marcos is None:
            self._db_marcos = UtilSQL.DictSQL(self._filepath, tabla="Marcos")
        return self._db_marcos

    @property
    def db_circles(self):
        if self._db_circles is None:
            self._db_circles = UtilSQL.DictSQL(self._filepath, tabla="Circles")
        return self._db_circles

    @property
    def db_svgs(self):
        if self._db_svgs is None:
            self._db_svgs = UtilSQL.DictSQL(self._filepath, tabla="SVGs")
        return self._db_svgs

    @property
    def db_markers(self):
        if self._db_markers is None:
            self._db_markers = UtilSQL.DictSQL(self._filepath, tabla="Markers")
        return self._db_markers

    def close(self):
        for db in (
            self._db_fen,
            self._db_config,
            self._db_arrows,
            self._db_marcos,
            self._db_circles,
            self._db_svgs,
            self._db_markers,
        ):
            if db is not None:
                db.close()
        self._db_fen = self._db_config = self._db_arrows = self._db_marcos = self._db_circles = self._db_svgs = (
            self._db_markers
        ) = None


# def readGraphLive(configuration):
#     db = DBManagerVisual(configuration.paths.file_resources(), False)
#     rel = {0: "MR", 1: "ALTMR", 2: "SHIFTMR", 6: "MR1", 7: "ALTMR1", 8: "SHIFTMR1" }
#     dic = {}
#     li = db.db_config["SELECTBANDA"]
#     for xid, pos in li:
#         if xid.startswith("_F"):
#             xdb = db.db_arrows
#             tp = TP_FLECHA
#         elif xid.startswith("_M"):
#             xdb = db.db_marcos
#             tp = TP_MARCO
#         elif xid.startswith("_S"):
#             xdb = db.db_svgs
#             tp = TP_SVG
#         elif xid.startswith("_X"):
#             xdb = db.db_markers
#             tp = TP_MARKER
#         else:
#             continue
#         if pos in rel:
#             valor = xdb[xid[3:]]
#             valor.TP = tp
#             dic[rel[pos]] = valor

#     db.close()
#     return dic

# def leeGraficos(configuration):
#     dicResp = {}

#     fdb = configuration.paths.file_resources()
#     db_config = UtilSQL.DictSQL(fdb, tabla="Config")
#     li = db_config["SELECTBANDA"]
#     db_config.close()
#     db_arrows = db_marcos = db_svgs = db_markers = None
#     for xid, pos in li:
#         if xid.startswith("_F"):
#             if not db_arrows:
#                 db_arrows = UtilSQL.DictSQL(fdb, tabla="Flechas")
#             dicResp[pos] = db_arrows[xid[3:]]
#             dicResp[pos].xtipo = TP_FLECHA
#         elif xid.startswith("_M"):
#             if not db_marcos:
#                 db_marcos = UtilSQL.DictSQL(fdb, tabla="Marcos")
#             dicResp[pos] = db_marcos[xid[3:]]
#             dicResp[pos].xtipo = TP_MARCO
#         elif xid.startswith("_S"):
#             if not db_svgs:
#                 db_svgs = UtilSQL.DictSQL(fdb, tabla="SVGs")
#             dicResp[pos] = db_svgs[xid[3:]]
#             dicResp[pos].xtipo = TP_SVG
#         elif xid.startswith("_X"):
#             if not db_markers:
#                 db_markers = UtilSQL.DictSQL(fdb, tabla="Markers")
#             dicResp[pos] = db_markers[xid[3:]]
#             dicResp[pos].xtipo = TP_MARKER
#     for db in (db_arrows, db_marcos, db_svgs, db_markers):
#         if db:
#             db.close()

#     return dicResp
