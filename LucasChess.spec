# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

block_cipher = None

base_dir = os.path.abspath("bin")
resources_dir = os.path.abspath("Resources")

a = Analysis(
    ['bin/LucasR.py'],
    pathex=[base_dir, os.path.join(base_dir, 'OS', 'darwin')],
    binaries=[
        ('bin/OS/darwin/FasterCode.cpython-312-darwin.so', 'OS/darwin'),
        ('bin/OS/darwin/Engines/irina/irina', 'OS/darwin/Engines/irina'),
        ('bin/OS/darwin/Engines/stockfish/stockfish-18-arm64', 'OS/darwin/Engines/stockfish'),
    ],
    datas=[
        ('bin/Code', 'Code'),
        ('bin/OS/darwin/OSEngines.py', 'OS/darwin'),
        ('bin/OS/darwin/uci_options.sqlite', 'OS/darwin'),
        ('Resources', 'Resources'),
    ],
    hiddenimports=[
        'FasterCode',
        'Code',
        'Code.Main',
        'Code.Main.Init',
        'Code.Z.Util',
        'Code.Z.XRun',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'PySide6.QtMultimedia',
        'psutil',
        'chess',
        'PIL',
        'polib',
        'deep_translator',
        'charset_normalizer',
        'sortedcontainers',
        'bs4',
        'cpuinfo',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='LucasChess',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LucasChess',
)

app = BUNDLE(
    coll,
    name='LucasChess.app',
    icon=None,
    bundle_identifier='com.lucaschess.lucaschessR6',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '6.0.1',
        'CFBundleVersion': '6.0.1',
        'NSRequiresAquaSystemAppearance': False,
    },
)
