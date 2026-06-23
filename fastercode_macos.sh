#!/bin/bash
# Build FasterCode Cython extension for macOS (Apple Silicon arm64)
# Usage: bash fastercode_macos.sh

set -e

echo ""
echo ":: Building FasterCode for macOS (arm64)"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/bin/_fastercode/src"
IRINA_DIR="$SRC_DIR/irina"
OUT_DIR="$SCRIPT_DIR/bin/OS/darwin"

cd "$IRINA_DIR"

echo "  [1/4] Compiling irina C sources..."
gcc -Wall -O2 -fPIC -fno-strict-aliasing -arch arm64 \
    -c lc.c board.c data.c eval.c hash.c loop.c makemove.c movegen.c \
       movegen_piece_to.c search.c util.c pgn.c parser.c polyglot.c -DNDEBUG
ar rcs libirina.a lc.o board.o data.o eval.o hash.o loop.o makemove.o \
    movegen.o movegen_piece_to.o search.o util.o pgn.o parser.o polyglot.o
mv libirina.a "$SRC_DIR/"
rm *.o

echo "  [2/4] Building FasterCode Cython extension..."
cd "$SRC_DIR"
cat Faster_Irina.pyx Faster_Polyglot.pyx > FasterCode.pyx
ARCHFLAGS="-arch arm64" python3 setup_linux.py build_ext --inplace
cp FasterCode.cpython-*.so "$OUT_DIR/"

echo "  [3/4] Compiling irina UCI engine for macOS..."
cd "$IRINA_DIR"
# Create a minimal stub for test-only symbols not needed in production
cat > _test_stub_mac.c << 'CEOF'
#include "defs.h"
#include "protos.h"
#include "globals.h"
#include <stdio.h>
void test(void) {}
void perft(int depth) { (void)depth; }
void perft_file(char *file) { (void)file; }
Bitmap calc_perft(char *fen, int depth) { (void)fen; (void)depth; return 0; }
CEOF

gcc -Wall -O2 -arch arm64 \
    -o "$OUT_DIR/Engines/irina/irina" \
    main.c board.c data.c eval.c hash.c loop.c lc.c makemove.c movegen.c \
    movegen_piece.c movegen_piece_to.c search.c util.c pgn.c parser.c \
    polyglot.c _test_stub_mac.c -DNDEBUG
chmod +x "$OUT_DIR/Engines/irina/irina"
rm _test_stub_mac.c

echo "  [4/4] Cleanup..."
rm -f "$SRC_DIR/FasterCode.pyx" "$SRC_DIR/FasterCode.c" "$SRC_DIR/libirina.a"
rm -rf "$SRC_DIR/build"

echo ""
echo ":: Build complete! Artifacts in bin/OS/darwin/"
echo ""
