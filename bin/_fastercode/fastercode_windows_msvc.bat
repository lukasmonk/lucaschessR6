@echo off
setlocal enabledelayedexpansion

REM -------------------------------------------------------
REM CONFIGURATION
REM -------------------------------------------------------

:: Change these paths to match your local environment
set "PYTHON_EXE=H:\lucaschessR6\.venv\Scripts\python.exe"
set "VS_PATH=C:\Program Files\Microsoft Visual Studio\2022\Community"

REM -------------------------------------------------------
REM VALIDATION
REM -------------------------------------------------------

:: Check if Python exists at the specified path
if not exist "%PYTHON_EXE%" (
    echo.
    echo [ERROR] Python executable not found at: "%PYTHON_EXE%"
    echo.
    echo Help: Please edit this .bat file and update the 'set PYTHON_EXE=...'
    echo       line with the correct path to your python.exe.
    echo.
    pause
    exit /b 1
)

:: Check if Visual Studio path exists
if not exist "%VS_PATH%" (
    echo.
    echo [ERROR] Visual Studio path not found at: "%VS_PATH%"
    echo.
    echo Help: Please edit this .bat file and update the 'set VS_PATH=...'
    echo       line to point to your MSVC installation folder.
    echo.
    pause
    exit /b 1
)

set "VCVARS=%VS_PATH%\VC\Auxiliary\Build\vcvars64.bat"

REM -------------------------------------------------------
REM INITIALIZE MSVC ENVIRONMENT
REM -------------------------------------------------------

if not exist "%VCVARS%" (
    echo [ERROR] MSVC initialization script not found at: %VCVARS%
    pause
    exit /b 1
)

call "%VCVARS%"
if errorlevel 1 (
    echo [ERROR] Failed to initialize MSVC environment.
    pause
    exit /b 1
)

REM -------------------------------------------------------
REM Compile C library: libirina.lib
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
REM Generate FasterCode.pyx
REM -------------------------------------------------------

echo.
echo === Generating FasterCode.pyx ===
echo.

copy /B Faster_Irina.pyx+Faster_Polyglot.pyx FasterCode.pyx > nul

REM -------------------------------------------------------
REM Compiling Python extension with setup.py
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
