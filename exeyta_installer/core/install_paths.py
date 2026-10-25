# -*- coding: utf-8 -*-
"""Пути установки ExeytaSetup.

По умолчанию: %LOCALAPPDATA%\\Exeyta (можно выбрать другой каталог).
Структура каталогов у пользователя — см. README.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

APP_NAME = "Exeyta"
LAUNCHER_EXE = "ExeytaLauncher.exe"
VERSION = "1.0.0-alpha.2"   # альфа-версия
CREATE_NO_WINDOW = 0x08000000


def repo_root() -> Path:
    """Корень репозитория/источника (рядом с installer.py)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def default_install_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(
        Path.home() / "AppData" / "Local")
    return Path(base) / APP_NAME


def desktop_dir() -> Path:
    base = os.environ.get("USERPROFILE") or str(Path.home())
    return Path(base) / "Desktop"


def start_menu_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(
        Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME


DIRS = ["runtime", "game", "mods", "scripts", "logs"]


def validate_install_dir(text: str):
    """(ok, message): каталог можно создать и в него писать."""
    text = (text or "").strip()
    if not text:
        return False, "Укажите путь установки"
    if len(text) < 3:
        return False, "Слишком короткий путь"
    try:
        p = Path(text)
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".exeyta_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as e:
        return False, "Нет доступа на запись: %s" % e
    return True, ""


def write_install_json(install_dir: Path, files_count=0, source=""):
    data = {
        "app": APP_NAME,
        "install_dir": str(install_dir),
        "launcher_exe": str(install_dir / LAUNCHER_EXE),
        "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "files": int(files_count),
        "source": source,
        "version": VERSION,
    }
    try:
        (install_dir / "install.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return data


def ensure_config_json(install_dir: Path):
    """Создаёт config.json рядом с exe, если его ещё нет (значения по умолчанию)."""
    cfg = install_dir / "config.json"
    if cfg.exists():
        return
    defaults = {
        "config_version": 1,
        "memory_mb": 6144,
        "autostart": False,
        "jvm_args": "-XX:+UseG1GC -XX:MaxGCPauseMillis=40",
        "game_dir": str(install_dir / "game"),
        "language": "Русский",
        "last_version": "1.21.4",
        "mods_mode": "Из коробки",
        "telegram": "https://t.me/exeyta",
    }
    try:
        cfg.write_text(json.dumps(defaults, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Ярлыки
# ---------------------------------------------------------------------------
def _shortcut_via_powershell(target: Path, lnk: Path, workdir: Path,
                              icon=None, arguments=None):
    target = str(target)
    lnk = str(lnk)
    workdir = str(workdir)
    icon_loc = "%s,0" % (str(icon) if icon else target)
    arg_line = ("$s.Arguments = '%s'; " % arguments.replace("'", "''")
                if arguments else "")
    ps = (
        "$w = New-Object -ComObject WScript.Shell; "
        "$s = $w.CreateShortcut('%s'); "
        "$s.TargetPath = '%s'; "
        "%s"
        "$s.WorkingDirectory = '%s'; "
        "$s.IconLocation = '%s'; "
        "$s.Save()"
    ) % (lnk.replace("'", "''"), target.replace("'", "''"), arg_line,
         workdir.replace("'", "''"), icon_loc.replace("'", "''"))
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                        "-Command", ps],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       creationflags=CREATE_NO_WINDOW)
    return r.returncode == 0 and Path(lnk).exists()


def _shortcut_via_bat(target: Path, lnk_dir: Path, name="Exeyta"):
    """Фолбэк: обычный .bat-ярлык, если .lnk недоступен."""
    try:
        lnk_dir.mkdir(parents=True, exist_ok=True)
        bat = lnk_dir / ("%s.bat" % name)
        bat.write_text('@echo off\r\ncd /d "%s"\r\nstart "" "%s"\r\n'
                       % (target.parent, target.name), encoding="utf-8")
        return bat
    except Exception:
        return None


def create_launcher_shortcut(dest: Path, shortcuts_dir: Path,
                             display="Exeyta Launcher"):
    """Ярлык запуска лаунчера в каталоге (Рабочий стол / меню «Пуск»).

    * собранная версия: .lnk на ExeytaLauncher.exe с ИКОНКОЙ exe;
    * dev-режим (нет exe): .lnk на python launcher.py с ИКОНКОЙ icon.ico
      (фолбэк — .bat без иконки);
    * перед созданием удаляются старые варианты того же ярлыка
      (.lnk/.bat с теми же именами), чтобы повторная установка
      НЕ оставляла копии-дубли.
    """
    dest = Path(dest)
    shortcuts_dir = Path(shortcuts_dir)
    exe = dest / LAUNCHER_EXE
    try:
        shortcuts_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # убираем прежние дубли: текущее имя + легаси-имена, lnk и bat
    for name in (display, "Exeyta", "Exeyta Launcher", "ExeytaSetup Launcher"):
        for ext in (".lnk", ".bat"):
            old = shortcuts_dir / (name + ext)
            try:
                if old.exists():
                    old.unlink()
            except Exception:
                pass

    if exe.exists():
        lnk = shortcuts_dir / ("%s.lnk" % display)
        try:
            if _shortcut_via_powershell(exe, lnk, dest, icon=exe):
                return lnk
        except Exception:
            pass

    # dev: .lnk на python с иконкой assets/icon.ico
    py = dest / "launcher.py"
    if py.exists():
        ico = dest / "assets" / "icon.ico"
        try:
            lnk = shortcuts_dir / ("%s.lnk" % display)
            if _shortcut_via_powershell(sys.executable, lnk, dest,
                                        icon=ico if ico.exists() else None,
                                        arguments='"%s"' % py.name):
                return lnk
        except Exception:
            pass
        # фолбэк: bat без иконки
        bat = shortcuts_dir / ("%s.bat" % display)
        try:
            bat.write_text(
                '@echo off\r\ncd /d "%s"\r\nstart "" python "%s"\r\n'
                % (dest, py.name), encoding="utf-8")
            return bat
        except Exception:
            return None
    # последний фолбэк — универсальный bat
    return _shortcut_via_bat(exe if exe.exists() else dest,
                             shortcuts_dir)


def create_shortcut(target: Path, lnk_path: Path, workdir: Path, icon=None):
    """Создаёт .lnk (PowerShell WScript.Shell); фолбэк — .bat."""
    try:
        lnk_path.parent.mkdir(parents=True, exist_ok=True)
        if _shortcut_via_powershell(target, lnk_path, workdir, icon):
            return lnk_path
    except Exception:
        pass
    return _shortcut_via_bat(target, lnk_path.parent)
