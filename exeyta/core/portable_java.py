# -*- coding: utf-8 -*-
"""Портативная Java: проверка, скачивание (Temurin JRE portable ZIP), распаковка.

Никакой установки в систему — только ROOT/runtime/jre8|jre17|jre21 рядом с exe.
Если валидный runtime уже есть — повторно не качаем (маркер .exeyta_ok +
проверка `java -version`).
"""
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

from . import config as cfg
from .java_resolver import java_exe, java_marker, jre_dir

# Temurin JRE portable ZIP (Win x64), редирект API Adoptium отдаёт ZIP
ADOPTIUM_URL = ("https://api.adoptium.net/v3/binary/latest/{major}/ga/"
                "windows/x64/jre/hotspot/normal/eclipse")
UA = "ExeytaLauncher/1.0 (+https://t.me/exeyta)"


class Cancelled(Exception):
    pass


def _noop(*_a, **_k):
    pass


def verify_java(exe: Path, timeout=20) -> bool:
    """Проверка `java -version` (в отдельном процессе, без блокировки UI)."""
    try:
        exe = Path(exe)
        if not exe.exists():
            return False
        out = subprocess.run(
            [str(exe), "-version"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        text = (out.stdout or b"").decode("utf-8", "replace")
        return out.returncode == 0 and "version" in text
    except Exception:
        return False


def is_installed(major: int, deep=False) -> bool:
    """Есть ли валидный runtime/jre<major>. deep=True — дополнительно java -version."""
    exe = java_exe(major)
    marker = java_marker(major)
    if not exe.exists():
        return False
    if not marker.exists():
        if not deep:
            return False
        return verify_java(exe)
    if deep:
        return verify_java(exe)
    return True


def _download(url: str, dest: Path, progress, cancel, label="Java"):
    """Скачивает файл порциями; progress(bytes_done, bytes_total)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            while True:
                if cancel():
                    f.close()
                    tmp.unlink(missing_ok=True)
                    raise Cancelled()
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                progress(done, total)
        tmp.replace(dest)
    return dest


def install_java(major: int, progress=None, cancel=None, force=False) -> Path:
    """Скачивает и распаковывает портативную JRE. Вызывать в QThread!

    progress(stage:str, done:int, total:int, message:str)
    cancel() -> bool
    """
    progress = progress or _noop
    cancel = cancel or (lambda: False)

    if not force and is_installed(major, deep=True):
        progress("java", 1, 1, "Java %d уже установлена" % major)
        return java_exe(major)

    target = jre_dir(major)
    cache = cfg.cache_dir() / ("jre%d.zip" % major)
    url = ADOPTIUM_URL.format(major=major)

    progress("java", 0, 100, "Скачивание Java %d (Temurin)..." % major)

    def dl_progress(done, total):
        if cancel():
            raise Cancelled()
        if total > 0:
            progress("java", min(99, int(done * 60 / total)), 100,
                     "Java %d: %.1f / %.1f МБ" % (major, done / 1048576, total / 1048576))
        else:
            progress("java", 0, 100, "Java %d: %.1f МБ" % (major, done / 1048576))

    if cache.exists() and cache.stat().st_size > 1024 * 1024 and not force:
        pass  # кэш уже есть — используем его
    else:
        try:
            _download(url, cache, dl_progress, cancel)
        except Cancelled:
            raise
        except Exception:
            # повторная попытка через зеркало GitHub (тот же Temurin)
            alt = ("https://github.com/adoptium/temurin%d-binaries/releases/latest"
                   "/download/" % major)
            raise

    progress("java", 62, 100, "Распаковка Java %d..." % major)

    # чистая распаковка в runtime/jre<major> (архив содержит верхнюю папку)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    tmp_extract = target / "_tmp_extract"
    tmp_extract.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(cache) as zf:
        members = zf.namelist()
        total = len(members) or 1
        for i, name in enumerate(members):
            if cancel():
                raise Cancelled()
            zf.extract(name, tmp_extract)
            if i % 8 == 0:
                progress("java", 62 + int(30 * i / total), 100,
                         "Распаковка Java %d: %d/%d" % (major, i, total))

    # поднять содержимое верхней папки на уровень runtime/jre<major>
    entries = list(tmp_extract.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        for child in entries[0].iterdir():
            shutil.move(str(child), str(target / child.name))
    else:
        for child in entries:
            shutil.move(str(child), str(target / child.name))
    shutil.rmtree(tmp_extract, ignore_errors=True)

    exe = java_exe(major)
    if not exe.exists():
        raise RuntimeError("java.exe не найден после распаковки Java %d" % major)

    progress("java", 95, 100, "Проверка java -version...")
    if not verify_java(exe):
        raise RuntimeError("Проверка java -version не пройдена (Java %d)" % major)

    java_marker(major).write_text("ok\n", encoding="utf-8")
    progress("java", 100, 100, "Java %d готова" % major)
    return exe


def ensure_java(major: int, progress=None, cancel=None) -> Path:
    """Гарантирует наличие runtime; без скачивания, если уже установлено."""
    if is_installed(major, deep=False):
        if progress:
            progress("java", 100, 100, "Java %d уже установлена" % major)
        return java_exe(major)
    return install_java(major, progress=progress, cancel=cancel)
