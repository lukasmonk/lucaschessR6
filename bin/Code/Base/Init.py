import sys

import Code
from Code import Procesador
from Code.Base.Constantes import ExitProgram
from Code.MainWindow import LucasChessGui
from Code.Sound import Sound
from Code.Z import Util, XRun


def init():
    if __debug__:
        from Code.Z import Debug
        sys.stderr = Debug.LogDebug("bug.log")
    else:
        sys.stderr = Util.Log("bug.log")

    main_procesador = Procesador.Procesador()
    main_procesador.set_version(Code.VERSION)
    run_sound = Sound.RunSound()
    resp = LucasChessGui.run_gui(main_procesador)
    run_sound.close()

    if resp == ExitProgram.REINIT.value:
        XRun.run_lucas()

    Util.close_app()
