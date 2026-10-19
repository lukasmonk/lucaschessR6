import ctypes

from PySide6 import QtCore

# Constantes de Win32 API
PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400

# Estructura para Power Throttling
PROCESS_POWER_THROTTLING_CURRENT_VERSION = 1
PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1


class ProcessPowerThrottlingState(ctypes.Structure):
    _fields_ = [
        ("Version", ctypes.c_uint32),
        ("ControlMask", ctypes.c_uint32),
        ("StateMask", ctypes.c_uint32),
    ]


def apply_power_throttling_fix(process: QtCore.QProcess):
    # 1. Obtener el PID del proceso
    pid = process.processId()
    if pid <= 0:
        return  # El proceso no está en ejecución

    # 2. Obtener el process_handle de Windows usando OpenProcess
    # Se requieren permisos para consultar y modificar información del proceso
    kernel32 = ctypes.windll.kernel32
    process_handle = kernel32.OpenProcess(
        PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION, False, pid
    )

    if not process_handle:
        return  # No se pudo abrir el handle

    try:
        # 3. Desactivar EcoQoS / Power Throttling en el handle
        throttling = ProcessPowerThrottlingState()
        throttling.Version = PROCESS_POWER_THROTTLING_CURRENT_VERSION
        throttling.ControlMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED
        throttling.StateMask = 0  # Desactiva la limitación de velocidad

        kernel32.SetProcessInformation(
            process_handle,
            0,  # ProcessPowerThrottling
            ctypes.byref(throttling),
            ctypes.sizeof(throttling),
        )
    finally:
        # 4. Es fundamental cerrar el handle nativo para no dejar fugas de recursos
        kernel32.CloseHandle(process_handle)
