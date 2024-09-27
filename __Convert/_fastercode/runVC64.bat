@echo off

set PATH_BASE=f:

cd source\irina
set PATH_MINGW=%PATH_BASE%\Mingw64\bin
set PATH_PYTHON=%PATH_BASE%\WPy64-31241\python-3.12.4.amd64
set PATH=%PATH_MINGW%;%PATH_PYTHON%;%PATH_PYTHON%\DLLs;%PATH_PYTHON%\lib;%PATH%

gcc -DNDEBUG -DWIN32 -c lc.c board.c data.c eval.c hash.c loop.c makemove.c movegen.c movegen_piece_to.c search.c util.c pgn.c parser.c polyglot.c
ar rcs ..\libirina.a lc.o board.o data.o eval.o hash.o loop.o makemove.o movegen.o movegen_piece_to.o search.o util.o pgn.o parser.o polyglot.o
del *.o

cd ..

copy /B Faster_Irina.pyx+Faster_Polyglot.pyx FasterCode.pyx

python setup.py build_ext --inplace -i clean

del FasterCode.c
del libirina.a
rmdir /s /q build



