# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PrintTrackingAgent.
#
# Build:
#   cd print-agent
#   .\.venv\Scripts\Activate.ps1
#   pyinstaller build\agent.spec --clean

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

PROJECT_DIR = Path(os.getcwd()).resolve()
ENTRY = str(PROJECT_DIR / "src" / "agent.py")

hiddenimports = []
hiddenimports += collect_submodules("win32print")
hiddenimports += collect_submodules("win32com")
hiddenimports += ["wmi", "pythoncom", "pywintypes"]

a = Analysis(
    [ENTRY],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PrintTrackingAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,            # set to False once stable
    disable_windowed_traceback=False,
    icon=None,
    onefile=True,
)
