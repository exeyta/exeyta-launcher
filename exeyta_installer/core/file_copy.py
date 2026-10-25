# -*- coding: utf-8 -*-
"""Копирование файлов лаунчера при установке (в QThread, с прогрессом).

Источник (порядок приоритета):
  1. переменная окружения EXEYTA_PAYLOAD;
  2. onefile-сборка: sys._MEIPASS/payload (ExeytaSetup.exe, PyInstaller);
  3. репозиторий: dist/ExeytaLauncher (после build_launcher.bat);
  4. репозиторий: исходники (dev-режим, python installer.py).

Установщик НЕ скачивает Minecraft/Java — это делает лаунчер в мастере.
Повторная установка перезаписывает файлы пакета и не создаёт дублей
ярлыков; config.json пользователя сохраняется.
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from .install_paths import (DIRS, LAUNCHER_EXE, CREATE_NO_WINDOW,
                            ensure_config_json, repo_root,
                            write_install_json)


class CopyError(Exception):
    pass


# ---------------------------------------------------------------------------
# Источник файлов
# ---------------------------------------------------------------------------
def collect_payload() -> dict:
    """Возвращает {'root': Path, 'source': str, 'files': [..]} пакета лаунчера."""
    # 1) явный путь
    env = os.environ.get("EXEYTA_PAYLOAD")
    if env and Path(env).exists():
        root = Path(env)
        return {"root": root, "source": "env:EXEYTA_PAYLOAD",
                "files": [p for p in root.rglob("*") if p.is_file()]}

    # 2) bundled payload (PyInstaller onefile)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cand = Path(meipass) / "payload"
        if cand.exists():
            return {"root": cand, "source": "bundled",
                    "files": [p for p in cand.rglob("*") if p.is_file()]}

    # 3/4) репозиторий
    root = repo_root()
    built = root / "dist" / "ExeytaLauncher"
    if (built / LAUNCHER_EXE).exists():
        return {"root": built, "source": "dist",
                "files": [p for p in built.rglob("*") if p.is_file()]}

    # dev: исходники + assets
    files = []
    for rel in ("launcher.py", "requirements.txt", "start.bat",
                "exeyta", "exeyta_shared", "assets"):
        p = root / rel
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend([f for f in p.rglob("*") if f.is_file()])
    if not files:
        raise CopyError("Не найдены файлы лаунчера (нет dist/ExeytaLauncher)")
    return {"root": root, "source": "repo", "files": files}


def _payload_rel(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return Path(path.name)


def _copy_replace(src: Path, out: Path, rel):
    """Копия с заменой: повторная установка перезаписывает файлы пакета.

    При «файле занят» (запущенный лаунчер) — короткие ретраи и понятная
    ошибка вместо обрыва без объяснений.
    """
    last = None
    for attempt in range(4):
        try:
            shutil.copy2(str(src), str(out))
            return
        except PermissionError as e:
            last = e
            time.sleep(0.35)
        except Exception as e:
            raise CopyError("Не удалось скопировать %s: %s" % (rel, e))
    raise CopyError("Файл занят (закройте Exeyta): %s (%s)" % (rel, last))


# ---------------------------------------------------------------------------
# Установка
# ---------------------------------------------------------------------------
def launcher_running() -> bool:
    """Запущен ли ExeytaLauncher.exe (для повторной установки)."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ExeytaLauncher.exe"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW)
        return b"ExeytaLauncher.exe" in out.stdout
    except Exception:
        return False


def perform_install(dest: Path, progress=None, cancel=None, desktop=True,
                    startmenu=True):
    """Копирует лаунчер в dest (с ОТСТРАНЕНИЕМ файлов), структуру, ярлыки.

    Повторная установка: файлы из пакета перезаписываются, config.json
    пользователя НЕ трогается, старые ярлыки удаляются и создаются
    заново (без копий).

    progress(done:int, total:int, name:str)
    cancel() -> bool
    """
    progress = progress or (lambda *a: None)
    cancel = cancel or (lambda: False)

    dest = Path(dest)
    # если лаунчер запущен — файлы заняты, просим закрыть и повторить
    if launcher_running() and (dest / LAUNCHER_EXE).exists():
        raise CopyError("Лаунчер запущен — закройте Exeyta и повторите установку")

    payload = collect_payload()
    files = payload["files"]
    total = len(files) + 4  # + структура каталогов + конфиги

    dest.mkdir(parents=True, exist_ok=True)

    done = 0
    for src in files:
        if cancel():
            raise CopyError("Отменено")
        rel = _payload_rel(src, payload["root"])
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        _copy_replace(src, out, rel)
        done += 1
        if done % 2 == 0 or done == total:
            progress(done, total, str(rel))

    # структура каталогов
    for d in DIRS:
        if cancel():
            raise CopyError("Отменено")
        (dest / d).mkdir(parents=True, exist_ok=True)
        done += 1
        progress(done, total, d + "/")

    ensure_config_json(dest)
    write_install_json(dest, files_count=len(files), source=payload["source"])
    done += 2
    progress(done, total, "install.json")

    # ярлыки: Рабочий стол и меню «Пуск» (только эти места)
    from .install_paths import create_launcher_shortcut, desktop_dir, start_menu_dir
    info = {"exe": str(dest / LAUNCHER_EXE), "source": payload["source"],
            "files": len(files)}
    if not (dest / LAUNCHER_EXE).exists():
        info["exe"] = str(dest / "launcher.py")
    if desktop:
        link = create_launcher_shortcut(dest, desktop_dir())
        info["shortcut_desktop"] = str(link) if link else ""
    if startmenu:
        link = create_launcher_shortcut(dest, start_menu_dir())
        info["shortcut_start"] = str(link) if link else ""
    return info


def launch_installed(dest: Path):
    """Запускает установленный лаунчер (exe, иначе python launcher.py)."""
    dest = Path(dest)
    exe = dest / LAUNCHER_EXE
    try:
        if exe.exists():
            subprocess.Popen([str(exe)], cwd=str(dest),
                             creationflags=CREATE_NO_WINDOW)
            return True
        dev = dest / "launcher.py"
        if dev.exists():
            subprocess.Popen([sys.executable, str(dev)], cwd=str(dest))
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# QThread-обёртка
# ---------------------------------------------------------------------------
class CopyWorker(QThread):
    progressed = pyqtSignal(int, int, str)     # done, total, name
    succeeded = pyqtSignal(dict)               # info
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, dest, desktop=True, startmenu=True, parent=None):
        super().__init__(parent)
        self.dest = Path(dest)
        self.desktop = desktop
        self.startmenu = startmenu
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            info = perform_install(
                self.dest,
                progress=lambda d, t, n: self.progressed.emit(d, t, n),
                cancel=lambda: self._cancel,
                desktop=self.desktop,
                startmenu=self.startmenu,
            )
            if self._cancel:
                self.cancelled.emit()
            else:
                self.succeeded.emit(info)
        except CopyError as e:
            if str(e) == "Отменено":
                self.cancelled.emit()
            else:
                self.failed.emit(str(e))
        except Exception as e:
            self.failed.emit(str(e))
