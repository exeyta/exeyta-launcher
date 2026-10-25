# -*- coding: utf-8 -*-
"""Программная сборка лаунчера: python build/build_launcher.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        import PyInstaller.__main__ as pyi
    except ImportError:
        print("PyInstaller не установлен: pip install -r requirements-build.txt")
        return 1
    spec = ROOT / "build" / "exeyta_launcher.spec"
    pyi.run(["--noconfirm", "--clean", str(spec)])
    exe = ROOT / "dist" / "ExeytaLauncher" / "ExeytaLauncher.exe"
    print("Готово:", exe if exe.exists() else "см. dist/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
