@echo off
setlocal enabledelayedexpansion

REM -------------------------------------------------------
REM CONFIGURATION
REM -------------------------------------------------------

:: Use python from PATH (venv must be activated before running this script)
set "PYTHON_EXE=python"
set "VS_PATH=C:\Program Files\Microsoft Visual Studio\18\Community"

REM -------------------------------------------------------
REM VALIDATION
REM -------------------------------------------------------

:: Check if Python is available in PATH
where %PYTHON_EXE% >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found in PATH.
    echo.
    echo Help: Please activate your Python virtual environment first.
    echo       Example: .venv\Scripts\activate
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
    lc.c board.c data.c hash.c makemove.c ^
    movegen.c movegen_piece_to.c util.c ^
    pgn.c parser.c polyglot.c cpu_flags.c

lib /nologo /OUT:..\irina.lib ^
    lc.obj board.obj data.obj hash.obj makemove.obj ^
    movegen.obj movegen_piece_to.obj util.obj ^
    pgn.obj parser.obj polyglot.obj cpu_flags.obj

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

echo.
echo === Cleaning temporary files ===
echo.

if exist "build" rd /s /q "build"
if exist "FasterCode.c" del /f /q "FasterCode.c"
if exist "irina.lib"    del /f /q "irina.lib"
if exist "FasterCode.pyx" del /f /q "FasterCode.pyx"


echo.
echo === Copying FasterCode to its destination folder ===
echo.
copy /Y *.pyd ..\..\OS\windows

echo.
echo ============================================
echo Build completed successfully
echo ============================================


pause
