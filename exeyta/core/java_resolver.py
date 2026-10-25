# -*- coding: utf-8 -*-
"""Определение major-версии Java по версии Minecraft (автовыбор).

Таблица (жёсткое требование):

    Minecraft              runtime/
    1.7.x  - 1.16.5        jre8
    1.17.x - 1.20.4        jre17
    1.20.5 - 1.21.x        jre21
    26.x+ (и снапшоты)     jre25   # Java 25 LTS обязательна для 26.x+
"""
import re
from pathlib import Path

from .config import runtime_root

# порядок: версия >= порога -> major.
# 2026: Minecraft 26.x+ обязателен на Java 25 (LTS).
_THRESHOLDS = [
    ((26, 0, 0), 25),
    ((1, 20, 5), 21),
    ((1, 17, 0), 17),
    ((0, 0, 0), 8),   # всё старше -> 8
]


def parse_version(version: str):
    """'1.21.4' -> (1, 21, 4); снапшоты типа '24w14a' -> None."""
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?$", (version or "").strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def latest_release_cached():
    """Последняя обычная (релизная) версия из кэша манифеста (без сети)."""
    try:
        from .config import cache_dir
        p = cache_dir() / "latest_release.txt"
        if p.exists():
            v = p.read_text(encoding="utf-8").strip()
            if v:
                return v
    except Exception:
        pass
    return None


def major_for(version: str, reference: str = None) -> int:
    """Major Java для версии Minecraft.

    Снапшоты/старые версии (без x.y.z) определяются по ПОСЛЕДНЕЙ
    обычной (релизной) версии — reference или кэш latest_release.txt.
    """
    v = parse_version(version)
    if v is None:
        ref = reference or latest_release_cached()
        if ref and parse_version(ref):
            return major_for(ref)
        return 21
    for threshold, major in _THRESHOLDS:
        if v >= threshold:
            return major
    return 8


def jre_dir(major: int) -> Path:
    """ROOT/runtime/jre<major> (портативная Java, без установки в систему)."""
    return runtime_root() / ("jre%d" % int(major))


def java_exe(major: int) -> Path:
    return jre_dir(major) / "bin" / "java.exe"


def java_marker(major: int) -> Path:
    """Маркер успешной распаковки .exeyta_ok."""
    return jre_dir(major) / ".exeyta_ok"


def describe(major: int) -> str:
    """'21 Temurin' — как на макете."""
    return "%d Temurin" % int(major)


def label_for(version: str) -> str:
    return describe(major_for(version))
