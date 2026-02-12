@echo off
setlocal enabledelayedexpansion

REM -------------------------------------------------------
REM CONFIGURACIÓN
REM -------------------------------------------------------

set PYTHON_EXE=H:\lucaschessR6\.venv\Scripts\python.exe
set VS_PATH=C:\Program Files\Microsoft Visual Studio\2022\Community
set VCVARS=%VS_PATH%\VC\Auxiliary\Build\vcvars64.bat

REM -------------------------------------------------------
REM Inicializar entorno MSVC
REM -------------------------------------------------------

set USE_FALLBACK=0

echo.
echo === Checking default configuration ===
echo.

REM Check Python
if not exist "%PYTHON_EXE%" (
    echo [WARN] Default Python not found: %PYTHON_EXE%
    set USE_FALLBACK=1
) else (
    echo [OK] Python: %PYTHON_EXE%
)

REM Check MSVC
if not exist "%VCVARS%" (
    echo [WARN] Default vcvars64.bat not found: %VCVARS%
    set USE_FALLBACK=1
) else (
    echo [OK] MSVC: %VCVARS%
)

if "!USE_FALLBACK!" == "0" (
    call "%VCVARS%"
    if errorlevel 1 (
        echo [WARN] vcvars64.bat failed to initialize
        set USE_FALLBACK=1
    )
)

if "!USE_FALLBACK!" == "0" (
    where cl >nul 2>&1
    if errorlevel 1 (
        echo [WARN] cl.exe not available after vcvars
        set USE_FALLBACK=1
    )
)

if "!USE_FALLBACK!" == "0" goto :env_ready

REM -------------------------------------------------------
REM Fallback - auto-detect environment
REM -------------------------------------------------------

echo.
echo ============================================
echo  Default configuration failed.
echo  Attempting auto-detect fallback...
echo ============================================
echo.

REM --- Auto-detect Python ---
set PYTHON_EXE=
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
)

if not defined PYTHON_EXE (
    echo ERROR: Python not found in PATH
    exit /b 1
)
echo [FALLBACK] Python: !PYTHON_EXE!

REM --- Auto-detect MSVC via vswhere ---
set VCVARS=
set "VSWHERE=C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if exist "!VSWHERE!" (
    for /f "delims=" %%I in ('"!VSWHERE!" -latest -property installationPath 2^>nul') do (
        set "VCVARS=%%I\VC\Auxiliary\Build\vcvars64.bat"
    )
)
if defined VCVARS (
    if not exist "!VCVARS!" set VCVARS=
)

REM --- If vswhere failed, search known directories ---
if not defined VCVARS (
    echo [FALLBACK] vswhere not found or returned no result, searching...
    for /f "delims=" %%F in ('where /r "C:\Program Files" vcvars64.bat 2^>nul') do (
        if not defined VCVARS set "VCVARS=%%F"
    )
)
if not defined VCVARS (
    for /f "delims=" %%F in ('where /r "C:\Program Files (x86)" vcvars64.bat 2^>nul') do (
        if not defined VCVARS set "VCVARS=%%F"
    )
)

if not defined VCVARS (
    echo ERROR: No MSVC installation found on this system
    exit /b 1
)

echo [FALLBACK] MSVC: !VCVARS!

call "!VCVARS!"
if errorlevel 1 (
    echo ERROR: MSVC environment failed to initialize
    exit /b 1
)

where cl >nul 2>&1
if errorlevel 1 (
    echo ERROR: cl.exe still not available after vcvars
    exit /b 1
)
echo [FALLBACK] cl.exe OK

echo.
echo [FALLBACK] Environment ready.
echo.

:env_ready

REM -------------------------------------------------------
REM Change to script directory (so relative paths work)
REM -------------------------------------------------------

cd /d "%~dp0"

REM -------------------------------------------------------
REM Compilar librería C: irina.lib
REM -------------------------------------------------------

echo.
echo === Building irina.lib ===
echo.

cd src\irina

cl /nologo /O2 /DNDEBUG /DWIN32 /MD /c ^
    lc.c board.c data.c eval.c hash.c loop.c makemove.c ^
    movegen.c movegen_piece_to.c search.c util.c ^
    pgn.c parser.c polyglot.c

if errorlevel 1 (
    echo ERROR: C compilation failed
    cd ..\..
    exit /b 1
)

lib /nologo /OUT:..\irina.lib ^
    lc.obj board.obj data.obj eval.obj hash.obj loop.obj makemove.obj ^
    movegen.obj movegen_piece_to.obj search.obj util.obj ^
    pgn.obj parser.obj polyglot.obj

if errorlevel 1 (
    echo ERROR: lib creation failed
    del *.obj 2>nul
    cd ..\..
    exit /b 1
)

del *.obj
cd ..

REM -------------------------------------------------------
REM Generar FasterCode.pyx (si procede)
REM -------------------------------------------------------

echo.
echo === Generating FasterCode.pyx ===
echo.

copy /B Faster_Irina.pyx+Faster_Polyglot.pyx FasterCode.pyx > nul

REM -------------------------------------------------------
REM Compilar extensión Python con setup.py
REM -------------------------------------------------------

echo.
echo === Building FasterCode extension ===
echo.

"!PYTHON_EXE!" setup_windows.py build_ext --inplace
if errorlevel 1 (
    echo ERROR: Python extension build failed
    del FasterCode.pyx 2>nul
    exit /b 1
)

REM -------------------------------------------------------
REM Limpieza opcional
REM -------------------------------------------------------

REM Copy .pyd to bin/ directory
for %%F in (FasterCode*.pyd) do (
    copy /Y "%%F" ..\..\
    echo Copied %%F to bin\
)

del FasterCode.pyx 2>nul

echo.
echo ============================================
echo  Build completed successfully
echo ============================================
pause
