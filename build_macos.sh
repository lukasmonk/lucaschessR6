#!/bin/bash
# Build LucasChess distributable for macOS (Apple Silicon arm64)
# Prerequisites: Python 3.12+, Xcode Command Line Tools
#
# Usage:
#   python3 -m venv venv && source venv/bin/activate
#   pip install -r requirements.txt Cython pyinstaller setuptools
#   bash build_macos.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "==================================================="
echo "  LucasChess R6 — macOS build (Apple Silicon)"
echo "==================================================="
echo ""

# ── Step 1: Build FasterCode + irina ──────────────────
bash fastercode_macos.sh

# ── Step 2: Bundle with PyInstaller ───────────────────
echo ":: Bundling with PyInstaller..."
cd "$SCRIPT_DIR"
pyinstaller LucasChess.spec --noconfirm

echo ""
echo "==================================================="
echo "  Build complete!"
echo "  App:    dist/LucasChess.app"
echo "  Folder: dist/LucasChess/"
echo "==================================================="
echo ""
