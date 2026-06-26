import ctypes
import os
import time

import Code
from Code.QT import Iconos, QTMessages
from Code.Z import Util


# Install: Wbase #90
# Assign toolbar: Wbase #132


class Eboard:
    def __init__(self):
        self.name = Code.configuration.x_digital_board
        self.driver = None
        self.setup = False
        self.fen_eboard = None
        self.dispatch = None
        self.allowHumanTB = False
        self.working_time = None
        self.side_takeback = None
        self._callbacks = []

    def is_working(self):
        return self.working_time is not None and 1.0 > (time.time() - self.working_time)

    def set_working(self):
        self.working_time = time.time()

    def envia(self, quien, dato):
        # assert prln(quien, dato, self.dispatch)
        return self.dispatch(quien, dato)

    def set_position(self, position):
        # assert prln("set position", position.fen())
        if self.driver:
            if (self.name == "DGT") or (self.name == "Novag UCB" and Code.configuration.x_digital_board_version == 0):
                self.write_position(position.fen_dgt())
            else:
                self.write_position(position.fen())

    @staticmethod
    def log(cad):
        import traceback

        with open("dgt.log", "at", encoding="utf-8", errors="ignore") as q:
            q.write(f"\n[{Util.today()}] {cad}\n")
            for line in traceback.format_stack():
                q.write(f"    {line.strip()}\n")

    def registerStatusFunc(self, dato):
        # assert prln("registerStatusFunc", dato)
        self.envia("status", dato)
        return 1

    def registerScanFunc(self, dato):
        # assert prln("registerScanFunc", dato)
        self.envia("scan", self.dgt2fen(dato))
        return 1

    def registerStartSetupFunc(self):
        # assert prln("registerStartSetupFunc")
        self.setup = True
        return 1

    def registerStableBoardFunc(self, dato):
        # assert prln("registerStableBoardFunc", dato, self.setup)
        self.fen_eboard = self.dgt2fen(dato)
        if self.setup:
            self.envia("stableBoard", self.fen_eboard)
        return 1

    def registerStopSetupWTMFunc(self, dato):
        # assert prln("registerStopSetupWTMFunc", dato)
        if self.setup:
            self.envia("stopSetupWTM", self.dgt2fen(dato))
            self.setup = False
        return 1

    def registerStopSetupBTMFunc(self, dato):
        # assert prln("registerStopSetupBTMFunc", dato)
        if self.setup:
            self.envia("stopSetupBTM", self.dgt2fen(dato))
            self.setup = False
        return 1

    def registerWhiteMoveInputFunc(self, dato):
        # assert prln("registerWhiteMoveInputFunc", dato)
        return self.envia("whiteMove", self.dgt2pv(dato))

    def registerBlackMoveInputFunc(self, dato):
        # assert prln("registerBlackMoveInputFunc", dato)
        return self.envia("blackMove", self.dgt2pv(dato))

    def registerWhiteTakeBackFunc(self):
        # assert prln("registerWhiteTakeBackFunc")
        return self.envia("whiteTakeBack", True)

    def registerBlackTakeBackFunc(self):
        # assert prln("registerBlackTakeBackFunc")
        return self.envia("blackTakeBack", True)

    @staticmethod
    def message_install_libs_linux():
        title = "Driver Installation Failed"
        text = "An error occurred while configuring the board."
        detailed_text = (
            "It is not possible to install the driver for the board. "
            "One way to solve the problem is to install the libraries "
            "following the instructions on the website:<br><br>"
            "<a href='https://goneill.co.nz/chess#linux'>https://goneill.co.nz/chess#linux</a>"
        )
        type_icon = "Critical"
        QTMessages.message_with_links(title, text, detailed_text, type_icon)

    def activate(self, dispatch):
        # assert prln("activate")
        self.fen_eboard = None
        self.driver = driver = None
        self.side_takeback = None
        self.dispatch = dispatch

        path_eboards = Util.opj(Code.folder_os, "DigitalBoards")
        os.chdir(path_eboards)

        if Util.is_linux():
            functype = ctypes.CFUNCTYPE

            board_so_prefixes = {
                "DGT-gon": "dgt",
                "Certabo": "cer",
                "Chessnut": "nut",
                "Pegasus": "peg",
                "Millennium": "mcl",
                "Citrine": "cit",
                "Saitek": "osa",
                "Square Off": "sop",
                "Tabutronic": "tab",
                "iChessOne": "ico",
                "Chessnut Evo": "evo",
                "HOS Sensory": "hos",
                "Chessnut Move": "mov",
            }
            prefijo = board_so_prefixes.get(self.name, "ucb")
            path_so = Util.opj(path_eboards, f"lib{prefijo}.so")

            if os.path.isfile(path_so):
                try:
                    ctypes.CDLL(Util.opj(path_eboards, "libQt6PrintSupport.so.6.2"), mode=ctypes.RTLD_GLOBAL)
                    ctypes.CDLL(Util.opj(path_eboards, "libQt6Pas.so.6.2"), mode=ctypes.RTLD_GLOBAL)
                    driver = ctypes.CDLL(path_so)
                except:
                    driver = None
                    self.message_install_libs_linux()

        else:
            functype = ctypes.WINFUNCTYPE
            path_eboards = Util.opj(Code.folder_os, "DigitalBoards")

            if self.name == "DGT":
                for folder_dll_dgt in (
                        "C:/Program Files (x86)/DGT/DGT e-Board drivers",
                        "C:/Program Files (x86)/DGT/DGT e-Board drivers/Applications/RabbitPlugin/32bit/Common Files",
                        "C:/Program Files (x86)/DGT Projects/",
                        "C:/Program Files (x86)/Common Files/DGT Projects/",
                        "C:/Program Files/DGT Projects/",
                        "C:/Program Files/Common Files/DGT Projects/",
                        "",
                        path_eboards,
                ):
                    path_dll = Util.opj(folder_dll_dgt, "DGTEBDLL.dll")
                    if os.path.isfile(path_dll):
                        try:
                            os.chdir(os.path.dirname(folder_dll_dgt))
                            driver = ctypes.WinDLL(path_dll)
                            break
                        except:
                            pass
            else:
                board_dll_suffixes = {
                    "Certabo": "CER64",
                    "Chessnut": "NUT64",
                    "DGT-gon": "DGT64",
                    "Pegasus": "PEG64",
                    "Millennium": "MCL64",
                    "Citrine": "CIT64",
                    "Saitek": "OSA64",
                    "Square Off": "SOP64",
                    "Tabutronic": "TAB64",
                    "iChessOne": "ICO64",
                    "Cynus": "CYN64",
                    "Chessnut Evo": "EVO64",
                    "HOS Sensory": "HOS64",
                    "Chessnut Move": "MOV64",
                }
                sufijo = board_dll_suffixes.get(self.name, "UCB64")
                path_dll = Util.opj(path_eboards, f"gon-{sufijo}.dll")
                if os.path.isfile(path_dll):
                    try:
                        driver = ctypes.WinDLL(path_dll)
                    except:
                        pass

        if driver is None:
            os.chdir(Code.current_dir)
            return False

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerStatusFunc)
        self._callbacks.append(st)
        driver._DGTDLL_RegisterStatusFunc.argtypes = [cmpfunc]
        driver._DGTDLL_RegisterStatusFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterStatusFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerScanFunc)
        self._callbacks.append(st)
        driver._DGTDLL_RegisterScanFunc.argtypes = [cmpfunc]
        driver._DGTDLL_RegisterScanFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterScanFunc(st)

        cmpfunc = functype(ctypes.c_int)
        st = cmpfunc(self.registerStartSetupFunc)
        self._callbacks.append(st)
        driver._DGTDLL_RegisterStartSetupFunc.argtypes = [cmpfunc]
        driver._DGTDLL_RegisterStartSetupFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterStartSetupFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerStableBoardFunc)
        self._callbacks.append(st)
        driver._DGTDLL_RegisterStableBoardFunc.argtypes = [cmpfunc]
        driver._DGTDLL_RegisterStableBoardFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterStableBoardFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerStopSetupWTMFunc)
        self._callbacks.append(st)
        driver._DGTDLL_RegisterStopSetupWTMFunc.argtypes = [cmpfunc]
        driver._DGTDLL_RegisterStopSetupWTMFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterStopSetupWTMFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerStopSetupBTMFunc)
        self._callbacks.append(st)
        driver._DGTDLL_RegisterStopSetupBTMFunc.argtypes = [cmpfunc]
        driver._DGTDLL_RegisterStopSetupBTMFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterStopSetupBTMFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerWhiteMoveInputFunc)
        self._callbacks.append(st)
        driver._DGTDLL_RegisterWhiteMoveInputFunc.argtypes = [cmpfunc]
        driver._DGTDLL_RegisterWhiteMoveInputFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterWhiteMoveInputFunc(st)

        cmpfunc = functype(ctypes.c_int, ctypes.c_char_p)
        st = cmpfunc(self.registerBlackMoveInputFunc)
        self._callbacks.append(st)
        driver._DGTDLL_RegisterBlackMoveInputFunc.argtypes = [cmpfunc]
        driver._DGTDLL_RegisterBlackMoveInputFunc.restype = ctypes.c_int
        driver._DGTDLL_RegisterBlackMoveInputFunc(st)

        driver._DGTDLL_WritePosition.argtypes = [ctypes.c_char_p]
        driver._DGTDLL_WritePosition.restype = ctypes.c_int

        driver._DGTDLL_ShowDialog.argtypes = [ctypes.c_int]
        driver._DGTDLL_ShowDialog.restype = ctypes.c_int

        driver._DGTDLL_HideDialog.argtypes = [ctypes.c_int]
        driver._DGTDLL_HideDialog.restype = ctypes.c_int

        driver._DGTDLL_WriteDebug.argtypes = [ctypes.c_bool]
        driver._DGTDLL_WriteDebug.restype = ctypes.c_int

        driver._DGTDLL_SetNRun.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        driver._DGTDLL_SetNRun.restype = ctypes.c_int

        if self.name != "DGT":
            driver._DGTDLL_GetVersion.argtypes = []
            driver._DGTDLL_GetVersion.restype = ctypes.c_int
            Code.configuration.x_digital_board_version = driver._DGTDLL_GetVersion()
            try:
                driver._DGTDLL_AllowTakebacks.argtypes = [ctypes.c_bool]
                driver._DGTDLL_AllowTakebacks.restype = ctypes.c_int
                driver._DGTDLL_AllowTakebacks(ctypes.c_bool(True))
                cmpfunc = functype(ctypes.c_int)
                st = cmpfunc(self.registerWhiteTakeBackFunc)
                self._callbacks.append(st)
                driver._DGTDLL_RegisterWhiteTakebackFunc.argtypes = [cmpfunc]
                driver._DGTDLL_RegisterWhiteTakebackFunc.restype = ctypes.c_int
                driver._DGTDLL_RegisterWhiteTakebackFunc(st)
                cmpfunc = functype(ctypes.c_int)
                st = cmpfunc(self.registerBlackTakeBackFunc)
                self._callbacks.append(st)
                driver._DGTDLL_RegisterBlackTakebackFunc.argtypes = [cmpfunc]
                driver._DGTDLL_RegisterBlackTakebackFunc.restype = ctypes.c_int
                driver._DGTDLL_RegisterBlackTakebackFunc(st)
            except:
                pass

        driver._DGTDLL_ShowDialog(ctypes.c_int(1))

        os.chdir(Code.current_dir)
        self.driver = driver
        return True

    def deactivate(self):
        # assert prln("deactivate", self.driver)
        if self.driver:
            self.driver._DGTDLL_HideDialog(ctypes.c_int(1))
            self.setup = False
            if Util.is_windows():
                from ctypes import wintypes

                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.FreeLibrary.argtypes = [wintypes.HMODULE]
                kernel32.FreeLibrary.restype = wintypes.BOOL
                kernel32.FreeLibrary(self.driver._handle)

            self.driver = None
            self._callbacks = []
            return True
        return False

    def show_dialog(self):
        # assert prln("showdialog")
        if self.driver:
            self.driver._DGTDLL_ShowDialog(ctypes.c_int(1))

    def write_debug(self, activar):
        # assert prln("writeDebug")
        if self.driver:
            self.driver._DGTDLL_WriteDebug(activar)

    def write_position(self, cposicion):
        # assert prln("write_position", cposicion, self.fen_eboard)
        if self.driver and cposicion != self.fen_eboard:
            # log( "Enviado a la DGT" + cposicion )
            self.driver._DGTDLL_WritePosition(cposicion.encode())
            self.fen_eboard = cposicion
            self.envia("stableBoard", cposicion.encode())
            Code.eboard.allowHumanTB = False

    def writeClocks(self, wclock, bclock):
        # assert prln("writeclocks")
        if self.driver:
            if self.name in ("DGT", "DGT-gon"):
                # log( "WriteClocks: W-%s B-%s"%(str(wclock), str(bclock)) )
                self.driver._DGTDLL_SetNRun(wclock.encode(), bclock.encode(), 0)

    @staticmethod
    def dgt2fen(datobyte):
        n = 0
        dato = datobyte.decode()
        ndato = len(dato)
        caja = [""] * 8
        ncaja = 0
        ntam = 0
        while True:
            if dato[n].isdigit():
                num = int(dato[n])
                if (n + 1 < ndato) and dato[n + 1].isdigit():
                    num = num * 10 + int(dato[n + 1])
                    n += 1
                while num:
                    pte = 8 - ntam
                    if num >= pte:
                        caja[ncaja] += str(pte)
                        ncaja += 1
                        ntam = 0
                        num -= pte
                    else:
                        caja[ncaja] += str(num)
                        ntam += num
                        break

            else:
                caja[ncaja] += dato[n]
                ntam += 1
            if ntam == 8:
                ncaja += 1
                ntam = 0
            n += 1
            if n == ndato:
                break
        if ncaja != 8:
            caja[7] += str(8 - ntam)
        return "/".join(caja)

    @staticmethod
    def dgt2pv(datobyte):
        dato = datobyte.decode()
        # Coronacion
        if dato[0] in "Pp" and dato[3].lower() != "p":
            return dato[1:3] + dato[4:6] + dato[3].lower()

        return dato[1:3] + dato[4:6]

    def icon_eboard(self):
        mapping = {
            "DGT": Iconos.DGT,
            "DGT-gon": Iconos.DGTB,
            "Pegasus": Iconos.DGTB,
            "Certabo": Iconos.Certabo,
            "Chessnut": Iconos.Chessnut,
            "Chessnut Evo": Iconos.Chessnut,
            "Chessnut Move": Iconos.Chessnut,
            "HOS Sensory": Iconos.HOS,
            "Cynus": Iconos.Manya,
            "iChessOne": Iconos.IChessOne,
            "Millennium": Iconos.Millenium,
            "Saitek": Iconos.Saitek,
            "Square Off": Iconos.SquareOff,
            "Tabutronic": Iconos.Tabutronic
        }
        return mapping.get(self.name, Iconos.Novag)()


def version():
    path_version = Util.opj(Code.folder_os, "DigitalBoards", "version")
    xversion = "0"
    if os.path.isfile(path_version):
        with open(path_version, "rt") as f:
            xversion = f.read().strip()
    return xversion
