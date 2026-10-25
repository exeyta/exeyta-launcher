# -*- coding: utf-8 -*-
"""Подмена стандартного скина в клиентском jar (offline-фолбэк ванили).

Как это работает:
  ванильный клиент при отсутствии онлайн-профиля (offline-аккаунт, токен 0)
  берёт стандартный скин ИЗ клиентского jar:
    * до ~1.21.x  — assets/minecraft/textures/entity/steve.png (и alex.png);
    * 26.x        — пул assets/minecraft/textures/entity/player/wide/*.png
                    и .../slim/*.png (выбор по UUID).
  Лаунчер подменяет ВСЕ эти текстуры на композит скина из редактора, поэтому
  скин виден в одиночной игре и на offline-серверах без модов.

Подмена идемпотентна: рядом с jar лежит маркер с md5 скина, оригиналы
сохраняются в <jar>.skinbak — «В игру»/запуск меняют только при изменении
скина, отсутствие скина у аккаунта -> восстановление оригинала.
"""
import hashlib
import re
import zipfile
from pathlib import Path

from .minecraft_installer import paths_for

# подменяемые текстуры стандартного скина
SKIN_ENTRY_RE = re.compile(
    r"^assets/minecraft/textures/entity/player/(wide|slim)/[A-Za-z0-9_]+\.png$"
    r"|^assets/minecraft/textures/entity/(steve|alex)\.png$"
)


class SkinPatchError(RuntimeError):
    pass


def _marker(jar: Path) -> Path:
    return Path(str(jar) + ".exeyta_skin")


def _backup(jar: Path) -> Path:
    return Path(str(jar) + ".skinbak")


def find_entries(jar: Path):
    try:
        with zipfile.ZipFile(jar) as z:
            return [n for n in z.namelist() if SKIN_ENTRY_RE.match(n)]
    except Exception:
        return []


def _rewrite(jar: Path, replacer):
    """Переписывает jar, подменяя некоторые записи (replacer(name)->bytes|None).

    Структура/метаданные остальных записей сохраняются.
    """
    tmp = Path(str(jar) + ".part")
    with zipfile.ZipFile(jar) as src, zipfile.ZipFile(tmp, "w") as dst:
        for info in src.infolist():
            new = replacer(info.filename)
            if new is None:
                new = src.read(info.filename)
            dst.writestr(info, new)
    tmp.replace(jar)


def skin_digest(skin_png: Path) -> str:
    return hashlib.md5(Path(skin_png).read_bytes()).hexdigest()


def apply_skin(version_id: str, skin_png, game_dir=None, cancel=None,
               progress=None) -> str:
    """Ставит скин в клиентский jar. Возвращает 'applied:N' | 'skip' | 'none'.

    SkinPatchError при отсутствии jar/скина — вызывающая сторона решает,
    блокировать ли запуск (нет: косметика).
    """
    p = paths_for(version_id, game_dir)
    jar = p["jar"]
    if not jar.exists():
        raise SkinPatchError("Клиент не установлен: %s" % version_id)
    skin_png = Path(skin_png) if skin_png else None
    if skin_png is None or not skin_png.exists():
        return restore_skin(version_id, game_dir)  # скина нет -> оригинал

    digest = skin_digest(skin_png)
    marker = _marker(jar)
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == digest:
        return "skip"

    entries = find_entries(jar)
    if not entries:
        return "none"

    if progress:
        progress("Поиск текстур скина в клиенте…")
    if cancel and cancel():
        return "cancelled"

    # оригиналы — в бэкап только при первой подмене
    bak = _backup(jar)
    if not bak.exists():
        wanted = set(entries)
        with zipfile.ZipFile(jar) as src, zipfile.ZipFile(bak, "w") as dst:
            for info in src.infolist():
                if info.filename in wanted:
                    dst.writestr(info.filename, src.read(info.filename))
        if cancel and cancel():
            bak.unlink(missing_ok=True)
            return "cancelled"

    data = skin_png.read_bytes()
    if cancel and cancel():
        return "cancelled"
    if progress:
        progress("Запись скина в клиент (%d текстур)…" % len(entries))

    def replacer(name):
        return data if name in set(entries) else None

    _rewrite(jar, replacer)

    if cancel and cancel():
        return "cancelled"
    marker.write_text(digest, encoding="utf-8")
    if progress:
        progress("Скин применён")
    return "applied:%d" % len(entries)


def restore_skin(version_id: str, game_dir=None, progress=None) -> str:
    """Возвращает оригинальные стандартные скины (аккаунт без скина)."""
    p = paths_for(version_id, game_dir)
    jar = p["jar"]
    if not jar.exists():
        raise SkinPatchError("Клиент не установлен: %s" % version_id)
    marker = _marker(jar)
    bak = _backup(jar)
    if not bak.exists():
        marker.unlink(missing_ok=True)
        return "nothing"
    if progress:
        progress("Возврат стандартного скина…")
    with zipfile.ZipFile(bak) as b:
        originals = {n: b.read(n) for n in b.namelist()}

    def replacer(name):
        return originals.get(name)

    _rewrite(jar, replacer)
    marker.unlink(missing_ok=True)
    return "restored:%d" % len(originals)


def status_of(version_id: str, game_dir=None) -> str:
    """'none' | 'patched' | 'vanilla' — состояние клиента относительно скина."""
    p = paths_for(version_id, game_dir)
    jar = p["jar"]
    if not jar.exists() or not find_entries(jar):
        return "none"
    return "patched" if _marker(jar).exists() else "vanilla"
