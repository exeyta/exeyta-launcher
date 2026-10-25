#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ExeytaSetup — ЕДИНСТВЕННЫЙ вход установщика."""
import sys
from pathlib import Path

ROOT = Path(sys.executable).parent if getattr(sys, "frozen", False) \
    else Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from exeyta_installer.app import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run())
