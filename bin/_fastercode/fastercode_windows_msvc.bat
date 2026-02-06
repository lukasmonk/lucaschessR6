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

call "%VCVARS%"
if errorlevel 1 (
    echo ERROR: MSVC environment not initialized
    exit /b 1
)

REM -------------------------------------------------------
REM Compilar librería C: libirina.lib
REM -------------------------------------------------------

echo.
echo === Building libirina.lib ===
echo.

cd src\irina

cl /nologo /O2 /DNDEBUG /DWIN32 /MD /c ^
    lc.c board.c data.c eval.c hash.c loop.c makemove.c ^
    movegen.c movegen_piece_to.c search.c util.c ^
    pgn.c parser.c polyglot.c

lib /nologo /OUT:..\irina.lib ^
    lc.obj board.obj data.obj eval.obj hash.obj loop.obj makemove.obj ^
    movegen.obj movegen_piece_to.obj search.obj util.obj ^
    pgn.obj parser.obj polyglot.obj

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


%PYTHON_EXE% setup_windows.py build_ext --inplace
if errorlevel 1 (
    echo ERROR: build failed
    exit /b 1
)

REM -------------------------------------------------------
REM Limpieza opcional
REM -------------------------------------------------------

del FasterCode.pyx

echo.
echo ============================================
echo Build completed successfully
echo ============================================
pause
