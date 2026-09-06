#!/bin/bash

echo ""
echo ":: Building FasterCode"
echo ""
PATH=/home/lucas/miniconda312/bin:$PATH

cd ./src/irina
gcc -Wall -O2 -fPIC -fno-strict-aliasing \
    -march=x86-64 -mtune=generic \
    -c lc.c board.c data.c hash.c makemove.c movegen.c movegen_piece_to.c util.c pgn.c parser.c polyglot.c cpu_flags.c -DNDEBUG
ar rcs libirina.a lc.o board.o data.o hash.o makemove.o movegen.o movegen_piece_to.o util.o pgn.o parser.o polyglot.o cpu_flags.o
mv libirina.a ..

rm *.o
cd ..

cat Faster_Irina.pyx Faster_Polyglot.pyx > FasterCode.pyx

python3 setup_linux.py build_ext --inplace --verbose

echo ""
echo ":: Building Complete"
echo ""
