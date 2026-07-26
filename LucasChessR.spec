# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

block_cipher = None

bin_dir = os.path.abspath("bin")

a = Analysis(
    [os.path.join(bin_dir, 'LucasR.py')],
    pathex=[bin_dir],
    binaries=[
        (os.path.join(bin_dir, 'OS/darwin/FasterCode.cpython-312-darwin.so'), 'OS/darwin'),
        (os.path.join(bin_dir, 'OS/darwin/Engines/stockfish/stockfish-18-arm64'), 'OS/darwin/Engines/stockfish'),
        (os.path.join(bin_dir, 'OS/darwin/Engines/irina/irina'), 'OS/darwin/Engines/irina'),
    ],
    datas=[
        # Resources (tudo)
        (os.path.join(bin_dir, 'Resources'), 'Resources'),
        # OS/darwin dados (não binários)
        (os.path.join(bin_dir, 'OS/darwin/OSEngines.py'), 'OS/darwin'),
        (os.path.join(bin_dir, 'OS/darwin/uci_options.sqlite'), 'OS/darwin'),
        (os.path.join(bin_dir, 'OS/darwin/Engines/stockfish/AUTHORS'), 'OS/darwin/Engines/stockfish'),
        (os.path.join(bin_dir, 'OS/darwin/Engines/stockfish/Copying.txt'), 'OS/darwin/Engines/stockfish'),
        (os.path.join(bin_dir, 'OS/darwin/Engines/stockfish/README.md'), 'OS/darwin/Engines/stockfish'),
        (os.path.join(bin_dir, 'OS/darwin/Engines/stockfish/versions.txt'), 'OS/darwin/Engines/stockfish'),
        # Code (pacotes Python)
        (os.path.join(bin_dir, 'Code'), 'Code'),
        # OS linux/win32 não são necessários no macOS
    ],
    hiddenimports=[
        'FasterCode',
        'psutil',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'PySide6.QtMultimedia',
        'PySide6.QtPrintSupport',
        'sortedcontainers',
        'chess',
        'chess.pgn',
        'chess.polyglot',
        'polib',
        'deep_translator',
        'requests',
        'bs4',
        'cpuinfo',
        'sqlite3',
        'ssl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'jupyter',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LucasChessR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
    icon="/Users/carloseduardo/Downloads/lucaschessR6-src/bin/_genicons/lucas/LucasChessR.icns",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LucasChessR',
)

app = BUNDLE(
    coll,
    name='LucasChessR.app',
    icon="/Users/carloseduardo/Downloads/lucaschessR6-src/bin/_genicons/lucas/LucasChessR.icns",
    bundle_identifier='com.lucaschess.lucaschessR',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDocumentTypes': [],
        'LSMinimumSystemVersion': '11.0',
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '6.0.1',
        'CFBundleVersion': '6.0.1',
        'CFBundleName': 'LucasChessR',
        'CFBundleDisplayName': 'LucasChessR',
    },
)
