# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: ExeytaLauncher.exe (onedir).

runtime/, game/, mods/, scripts/ — НЕ запаковываются: создаются рядом с exe
и пополняются самим лаунчером (скачивание MC/Java в мастере).
"""
from pathlib import Path

ROOT = Path(SPECPATH).parent          # build/ -> корень репозитория
icon = ROOT / "assets" / "icon.ico"

datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "exeyta" / "ui" / "styles.qss"), "exeyta/ui"),
]

a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["PyQt5.QtSvg"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ExeytaLauncher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon) if icon.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ExeytaLauncher",
)
