import sys

import Code
from Code import Procesador, Util, XRun
from Code.Base.Constantes import ExitProgram
from Code.MainWindow import LucasChessGui
from Code.Sound import Sound


def init():
    if not __debug__:
        sys.stderr = Util.Log("bug.log")

    main_procesador = Procesador.Procesador()
    main_procesador.set_version(Code.VERSION)
    run_sound = Sound.RunSound()
    resp = LucasChessGui.run_gui(main_procesador)
    run_sound.close()

    if resp == ExitProgram.REINIT.value:
        XRun.run_lucas()
