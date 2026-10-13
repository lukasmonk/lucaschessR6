import sys

import Code
from Code import Procesador
from Code.Base.Constantes import ExitProgram
from Code.Main import LucasChessGui
from Code.QT import QTUtils
from Code.Z import Util, XRun


def init():
    if __debug__:
        from Code.Z import Debug

        sys.stderr = Debug.LogDebug("bug.log")
    else:
        sys.stderr = Util.Log("bug.log")

    main_procesador = Procesador.Procesador()
    main_procesador.set_version(Code.VERSION)
    resp = LucasChessGui.run_gui(main_procesador)
    if Code.runSound:
        Code.runSound.reset()

    if resp == ExitProgram.REINIT.value:
        XRun.run_lucas()

    QTUtils.close_app()
