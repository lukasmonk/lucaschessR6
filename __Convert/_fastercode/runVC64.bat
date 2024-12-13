@echo off

set PATH_BASE=C:

cd source\irina
set PATH_MINGW=%PATH_BASE%\msys64\ucrt64\bin
set PATH_PYTHON=%PATH_BASE%\Python312
set PATH=%PATH_MINGW%;%PATH_PYTHON%;%PATH_PYTHON%\DLLs;%PATH_PYTHON%\lib;%PATH_PYTHON%\libs,%PATH_PYTHON%\include,%PATH_PYTHON%\Scripts,%PATH%

echo "Compiling irina lib with GCC"

gcc -Wall -fPIC -O3 -c lc.c board.c data.c eval.c hash.c loop.c makemove.c movegen.c movegen_piece_to.c search.c util.c pgn.c parser.c polyglot.c -DNDEBUG
ar crs ../libirina.a lc.o board.o data.o eval.o hash.o loop.o makemove.o movegen.o movegen_piece_to.o search.o util.o pgn.o parser.o polyglot.o
del *.o

echo "Compiling irina lib with GCC done"

cd ..

echo "Get FasterCode.pyx from the two files Faster_Irina.pyx and Faster_Polyglot.pyx"
copy /B Faster_Irina.pyx+Faster_Polyglot.pyx FasterCode.pyx

echo "Compiling the Cython code"
%PATH_PYTHON%\Scripts\cython FasterCode.pyx -o FasterCode.c
echo "Compiling the Cython code done"
pause
echo "Compiling the C code using this commands"
echo "gcc -c -I%PATH_PYTHON%\include -o FasterCode.o FasterCode.c -O3"
echo "gcc -shared -L%PATH_PYTHON%\libs -o FasterCode.pyd -s FasterCode.obj .\libirina.a  -lpython312 -O3"

gcc -c -I%PATH_PYTHON%\include -o FasterCode.o FasterCode.c -O3
gcc -shared -L%PATH_PYTHON%\libs -o FasterCode.pyd -s FasterCode.o .\libirina.a  -lpython312 -O3 
echo "Compiling the C code done"

echo "Clean the compilation files"

del FasterCode.o*
del libirina.a
del FasterCode.c
del FasterCode.pyx

echo "Done"



