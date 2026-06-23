# feat: macOS (Apple Silicon) Support

## Summary

This PR adds full macOS support for LucasChessR on Apple Silicon (ARM64 / M-series chips). The application can now run natively on macOS — both directly from source and as a distributable `.app` bundle.

---

## Motivation

LucasChessR was designed primarily for Linux and Windows. This PR brings it to macOS by:
- Compiling the native `FasterCode` extension for ARM64
- Bundling the Stockfish engine (ARM64 native build)
- Generating a proper macOS `.app` with icon via PyInstaller
- Fixing resource path resolution inside PyInstaller bundles

---

## What Changed

### 1. `bin/Code/__init__.py` — PyInstaller Bundle Compatibility

**Problem:** When packaged with PyInstaller, data files (Resources, OS engines) are extracted to `sys._MEIPASS`, not alongside `sys.argv[0]`. The original code always resolved paths relative to the working directory, causing `FileNotFoundError` at startup.

**Fix:**

```python
# Before
folder_os = Util.opj(current_dir, "OS", platform)
folder_resources = Util.opj(folder_root, "Resources")

# After
_data_dir = getattr(sys, "_MEIPASS", current_dir)
folder_os = Util.opj(_data_dir, "OS", platform)
folder_resources = Util.opj(_data_dir, "Resources")
```

This makes the app work both in development mode (running `python3 LucasR.py`) **and** inside a PyInstaller `.app` bundle without any path hacks.

---

### 2. `bin/OS/darwin/` — macOS Engine Support

The `darwin` OS folder was already present in the repo but incomplete. Added:

- **`bin/OS/darwin/Engines/stockfish/versions.txt`**: contains `stockfish-18-arm64`, pointing to the ARM64 native Stockfish 18 binary already present in the folder.
- **`bin/OS/darwin/FasterCode.cpython-312-darwin.so`**: the compiled Python extension (`_fastercode`) for macOS ARM64 — built locally from source using the existing `setup_linux.py` adapted for macOS.

The `OSEngines.py` for darwin already referenced `stockfish-18-arm64` correctly.

---

### 3. `bin/_genicons/lucas/LucasChessR.icns` — macOS App Icon

Generated a proper `.icns` file from the existing `peon64r6.png` (64×64 RGBA PNG) using macOS `iconutil`, covering all required resolutions:

| File | Size |
|------|------|
| icon_16x16.png | 16×16 |
| icon_16x16@2x.png | 32×32 |
| icon_32x32.png | 32×32 |
| icon_32x32@2x.png | 64×64 |
| icon_128x128.png | 128×128 |
| icon_128x128@2x.png | 256×256 |
| icon_256x256.png | 256×256 |
| icon_256x256@2x.png | 512×512 |
| icon_512x512.png | 512×512 |
| icon_512x512@2x.png | 1024×1024 |

**Commands used:**
```bash
mkdir -p /tmp/LucasChessR.iconset
sips -z 16 16   peon64r6.png --out /tmp/LucasChessR.iconset/icon_16x16.png
sips -z 32 32   peon64r6.png --out /tmp/LucasChessR.iconset/icon_16x16@2x.png
sips -z 32 32   peon64r6.png --out /tmp/LucasChessR.iconset/icon_32x32.png
sips -z 64 64   peon64r6.png --out /tmp/LucasChessR.iconset/icon_32x32@2x.png
sips -z 128 128 peon64r6.png --out /tmp/LucasChessR.iconset/icon_128x128.png
sips -z 256 256 peon64r6.png --out /tmp/LucasChessR.iconset/icon_128x128@2x.png
sips -z 256 256 peon64r6.png --out /tmp/LucasChessR.iconset/icon_256x256.png
sips -z 512 512 peon64r6.png --out /tmp/LucasChessR.iconset/icon_256x256@2x.png
sips -z 512 512 peon64r6.png --out /tmp/LucasChessR.iconset/icon_512x512.png
sips -z 1024 1024 peon64r6.png --out /tmp/LucasChessR.iconset/icon_512x512@2x.png
iconutil -c icns /tmp/LucasChessR.iconset -o bin/_genicons/lucas/LucasChessR.icns
```

---

### 4. `LucasChessR.spec` — PyInstaller Build Spec

A complete PyInstaller spec file to produce a self-contained `LucasChessR.app` for macOS ARM64.

**Key points:**
- Entry point: `bin/LucasR.py`
- Bundles `FasterCode.cpython-312-darwin.so` and engines (`stockfish-18-arm64`, `irina`) as binaries
- Includes the entire `Resources/` tree and `Code/` package as data
- Excludes unused heavy packages (`tkinter`, `numpy`, `matplotlib`, etc.)
- Sets `argv_emulation=True` for proper macOS file-association behavior
- Sets `target_arch='arm64'`
- Configures `Info.plist` with bundle ID `com.lucaschess.lucaschessR`, version `6.0.1`, `NSHighResolutionCapable: True`, and `LSMinimumSystemVersion: 11.0`
- Sets the `.icns` icon

---

### 5. `LucasChessR.sh` — Development Launch Script

A simple shell script to launch the app directly from source without building:

```bash
#!/bin/zsh
cd "$(dirname "$0")/bin"
python3 LucasR.py "$@"
```

---

### 6. `.gitignore` — Updated

Added exclusions for:
- `.DS_Store` (macOS metadata)
- `bin/Resources` (symlink used locally during development to point to the Resources folder)
- `build/` and `dist/` (PyInstaller output — already present but made explicit)

---

## How to Run (Development)

### Prerequisites

```bash
pip3 install psutil pillow python-chess PySide6 sortedcontainers polib \
             deep-translator requests beautifulsoup4 py-cpuinfo \
             charset-normalizer urllib3 idna certifi
```

> **Note:** Make sure `pip3` installs ARM64-native wheels. If `python3` is a universal binary (as shipped by python.org), pip will auto-select the correct arch. You can verify with:
> ```bash
> python3 -c "import platform; print(platform.machine())"
> # Expected: arm64
> ```

### Symlink Resources (first time only)

The source tree (`lucaschessR6-src/bin`) does not include the `Resources/` folder (it lives separately in the release package). Create a symlink so the dev run can find it:

```bash
ln -sf /path/to/LucasChessR/Resources /path/to/lucaschessR6-src/bin/Resources
```

Replace `/path/to/LucasChessR` with the location of your extracted LucasChessR release.

### Run

```bash
cd lucaschessR6-src
./LucasChessR.sh
# or
cd lucaschessR6-src/bin && python3 LucasR.py
```

---

## How to Build the .app Bundle

### Prerequisites (additional)

```bash
pip3 install pyinstaller
```

You also need the `Resources/` folder available at `bin/Resources` (symlink or real copy — see above).

### Build

```bash
cd lucaschessR6-src
pyinstaller LucasChessR.spec --distpath ./dist --workpath ./build --noconfirm
```

The output will be at:
```
lucaschessR6-src/dist/LucasChessR.app   (~510 MB)
```

### Run the .app

```bash
open dist/LucasChessR.app
# or double-click in Finder
```

You can also copy it to `/Applications` for permanent installation.

---

## Architecture Notes

### FasterCode Extension

The `FasterCode` C extension is the chess move generation library. It must be compiled for the target architecture. The compiled `FasterCode.cpython-312-darwin.so` (ARM64) is placed at:

```
bin/OS/darwin/FasterCode.cpython-312-darwin.so
```

`bin/Code/__init__.py` inserts `bin/OS/darwin/` into `sys.path` at startup, so `import FasterCode` resolves correctly.

To recompile for a different Python version or architecture:

```bash
cd bin/_fastercode/src
# The existing setup_linux.py can be adapted for macOS
python3 setup.py build_ext --inplace
cp FasterCode.cpython-*.so ../OS/darwin/
```

### Engines

| Engine | Binary | Location |
|--------|--------|----------|
| Stockfish 18 | `stockfish-18-arm64` | `bin/OS/darwin/Engines/stockfish/` |
| Irina | `irina` | `bin/OS/darwin/Engines/irina/` |

Both binaries are ARM64 native Mach-O executables.

### Resource Path Resolution

```
Development mode:
  sys.argv[0] → bin/LucasR.py
  _data_dir   → bin/
  Resources   → bin/Resources   (symlink → LucasChessR/Resources)
  OS/darwin   → bin/OS/darwin

PyInstaller bundle mode:
  sys._MEIPASS → LucasChessR.app/Contents/MacOS/_internal/
  _data_dir    → sys._MEIPASS
  Resources    → .app/Contents/MacOS/_internal/Resources  (bundled)
  OS/darwin    → .app/Contents/MacOS/_internal/OS/darwin  (bundled)
```

---

## Tested On

| Item | Value |
|------|-------|
| Hardware | Apple M-series (ARM64) |
| macOS | 14.x (Sonoma) |
| Python | 3.12.6 (python.org universal binary) |
| PySide6 | 6.11.1 |
| Pillow | 12.2.0 (ARM64 native wheel) |
| Stockfish | 18 (ARM64) |
| PyInstaller | 6.21.0 |

---

## Files Changed

| File | Type | Description |
|------|------|-------------|
| `bin/Code/__init__.py` | Modified | PyInstaller `sys._MEIPASS` support for resource paths |
| `LucasChessR.spec` | Added | PyInstaller spec for macOS .app bundle |
| `LucasChessR.sh` | Added | Dev launch script |
| `bin/OS/darwin/Engines/stockfish/versions.txt` | Added | Points to `stockfish-18-arm64` |
| `bin/_genicons/lucas/LucasChessR.icns` | Added | macOS app icon (all resolutions) |
| `.gitignore` | Modified | Added `.DS_Store`, `bin/Resources`, `build/`, `dist/` |

---

## Known Limitations

- **Intel Macs (x86_64):** Not tested. Would require recompiling `FasterCode` and obtaining an x86_64 Stockfish binary. The `spec` file uses `target_arch='arm64'` explicitly.
- **Code signing:** The `.app` is self-signed by PyInstaller. On first launch, macOS Gatekeeper may warn. Right-click → Open to bypass.
- **Bundle size:** ~510 MB uncompressed. This is expected given PySide6 (~440 MB) + Resources (~246 MB) are fully bundled. A DMG with compression would reduce distribution size significantly.
