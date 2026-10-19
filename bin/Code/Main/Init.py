import Code
from Code import Procesador
from Code.Base.Constantes import ExitProgram
from Code.Main import LucasChessGui
from Code.QT import QTUtils
from Code.Z import XRun


def init():
    main_procesador = Procesador.Procesador()
    main_procesador.set_version(Code.VERSION)
    resp = LucasChessGui.run_gui(main_procesador)
    if Code.runSound:
        Code.runSound.reset()

    Code.configuration.set_stderr("bug.log")

    if resp == ExitProgram.REINIT.value:
        QTUtils.close_app(exit0=False)
        XRun.run_lucas()
    else:
        QTUtils.close_app(exit0=True)
