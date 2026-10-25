# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: ExeytaSetup.exe (onefile).

Если собран dist/ExeytaLauncher — его содержимое кладётся в payload/
(onefile распакует его в sys._MEIPASS/payload, установщик скопирует).
Без собранного лаунчера установщик работает в dev-режиме (исходники).
"""
from pathlib import Path

ROOT = Path(SPECPATH).parent
icon = ROOT / "assets" / "icon.ico"
built = ROOT / "dist" / "ExeytaLauncher"

datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "exeyta_installer" / "ui" / "styles.qss"),
     "exeyta_installer/ui"),
]
if built.exists():
    datas.append((str(built), "payload"))

a = Analysis(
    [str(ROOT / "installer.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["PyQt5.QtSvg", "exeyta.ui.controls"],
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
    a.binaries,
    a.datas,
    [],
    name="ExeytaSetup",
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
