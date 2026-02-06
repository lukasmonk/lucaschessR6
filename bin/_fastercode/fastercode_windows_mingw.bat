@echo off


REM ---------------------------------------------------------------------------------------------------------
REM It is necessary to indicate the python version and path of python and mingw, changing the next 3 lines
set PYTHON_VERSION=312
set PYTHON_PATH=C:\Users\lucas\AppData\Roaming\uv\python\cpython-3.12.12-windows-x86_64-none
set MINGW64_PATH=h:\mingw64\bin
REM ---------------------------------------------------------------------------------------------------------


set PATH=%MINGW64_PATH%;%PYTHON_PATH%;%PYTHON_PATH%\DLLs;%PYTHON_PATH%\Scripts;%PYTHON_PATH%\lib;%PATH%

REM ---------------------------------------------------------------------------------------------------------
REM Library Irina
echo Creating the C irina library
cd src
cd irina
gcc -DNDEBUG -DWIN32 -fPIC -O2 -march=x86-64 -mtune=generic -c lc.c board.c data.c eval.c hash.c loop.c makemove.c movegen.c movegen_piece_to.c search.c util.c pgn.c parser.c polyglot.c
ar cr ../libirina.so lc.o board.o data.o eval.o hash.o loop.o makemove.o movegen.o movegen_piece_to.o search.o util.o pgn.o parser.o polyglot.o
del *.o
cd ..
REM ---------------------------------------------------------------------------------------------------------

REM ---------------------------------------------------------------------------------------------------------
REM cython
echo Generating FasterCode in C with cython
copy /B Faster_Irina.pyx+Faster_Polyglot.pyx FasterCode.pyx > nul
cython --embed -o FasterCode.c FasterCode.pyx
REM ---------------------------------------------------------------------------------------------------------

REM ---------------------------------------------------------------------------------------------------------
REM Compiling
echo Compiling everything
gcc -c -I%PYTHON_PATH%\include -DWIN32 -fPIC -O2 -march=x86-64 -mtune=generic -o FasterCode.o FasterCode.c
gcc -shared -L%PYTHON_PATH%\libs -DWIN32 -fPIC -O2 -march=x86-64 -mtune=generic -o FasterCode.cp%PYTHON_VERSION%-win_amd64.pyd FasterCode.o .\libirina.so  -lpython%PYTHON_VERSION%
strip FasterCode.cp%PYTHON_VERSION%-win_amd64.pyd
REM ---------------------------------------------------------------------------------------------------------

REM ---------------------------------------------------------------------------------------------------------
REM Removing temporary files
del FasterCode.o
del FasterCode.c
del FasterCode.pyx
del libirina.so
REM ---------------------------------------------------------------------------------------------------------

REM ---------------------------------------------------------------------------------------------------------
REM Final message
if exist "FasterCode.cp%PYTHON_VERSION%-win_amd64.pyd" (
    echo.
    echo.
    echo File created: FasterCode.cp%PYTHON_VERSION%-win_amd64.pyd
    echo.
    echo.
) else (
    echo Error,
)
pause
REM ---------------------------------------------------------------------------------------------------------
