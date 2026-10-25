# -*- coding: utf-8 -*-
"""Конфигурация и пути лаунчера Exeyta.

Контракт путей:
  * ROOT            — каталог рядом с exe (frozen) или корень репозитория;
  * %APPDATA%/Exeyta — accounts.json, logs, cache;
  * ROOT/runtime/jre8|jre17|jre21 — портативная Java;
  * ROOT/game       — клиент (versions/, assets/) — «Папка игры»;
  * ROOT/scripts    — генерируемые .bat;
  * ROOT/mods       — моды («Из коробки»).
"""
import json
import os
import sys
import threading
from pathlib import Path

APP_NAME = "Exeyta"
LAUNCHER_NAME = "ExeytaLauncher"
TELEGRAM_URL = "https://t.me/exeyta"
CONFIG_VERSION = 1

# базовый размер окна (viewBox SVG: 28 22 1864 1036)
BASE_W = 1864
BASE_H = 1036

_ROOT_OVERRIDE = None   # см. set_root() — объявлено до root_dir()


def root_dir() -> Path:
    """Каталог лаунчера: рядом с exe в frozen-режиме, иначе корень репо."""
    if _ROOT_OVERRIDE is not None:
        return _ROOT_OVERRIDE
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


ROOT = root_dir()


def set_root(path):
    """Переопределение ROOT (тесты, переносимые режимы).

    Меняет и глобальный ROOT, и root_dir() — иначе пути «рядом с exe»
    (runtime/, scripts/) разойдутся с путями из конфига.
    """
    global ROOT, _ROOT_OVERRIDE
    _ROOT_OVERRIDE = Path(path)
    ROOT = _ROOT_OVERRIDE
    return ROOT


def appdata_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = appdata_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    p = appdata_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def accounts_path() -> Path:
    return appdata_dir() / "accounts.json"


def config_path() -> Path:
    return ROOT / "config.json"


def runtime_root() -> Path:
    return ROOT / "runtime"


def scripts_dir() -> Path:
    p = ROOT / "scripts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def mods_dir() -> Path:
    p = ROOT / "mods"
    p.mkdir(parents=True, exist_ok=True)
    return p


def assets_dir() -> Path:
    """Каталог assets лаунчера (иконки, svg-макет).

    В onedir-сборке PyInstaller 6 ресурсы лежат в _internal/assets —
    учитываем оба расположения.
    """
    p = ROOT / "assets"
    if p.exists():
        return p
    alt = ROOT / "_internal" / "assets"
    if alt.exists():
        return alt
    return p


DEFAULTS = {
    "config_version": CONFIG_VERSION,
    "memory_mb": 6144,
    "autostart": False,
    "jvm_args": "-XX:+UseG1GC -XX:MaxGCPauseMillis=40",
    "game_dir": str(ROOT / "game"),
    "language": "Русский",
    "last_version": "1.21.4",
    "mods_mode": "Из коробки",
    "telegram": TELEGRAM_URL,
}


class Config:
    """config.json рядом с exe; потокобезопасная запись, значения по умолчанию."""

    def __init__(self, path: Path = None):
        self.path = Path(path) if path else config_path()
        self._lock = threading.RLock()
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        with self._lock:
            try:
                if self.path.exists():
                    raw = json.loads(self.path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        self.data.update(raw)
            except Exception:
                # повреждённый конфиг -> значения по умолчанию, файл перезапишется
                self.data = dict(DEFAULTS)
        return self

    def save(self):
        with self._lock:
            try:
                tmp = self.path.with_suffix(".json.tmp")
                tmp.write_text(
                    json.dumps(self.data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                tmp.replace(self.path)
            except Exception:
                pass
        return self

    def get(self, key, default=None):
        with self._lock:
            return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value, save=True):
        with self._lock:
            self.data[key] = value
            if save:
                self.save()
        return value

    # --- удобные доступы --------------------------------------------------
    @property
    def memory_mb(self) -> int:
        try:
            return int(self.get("memory_mb"))
        except Exception:
            return 6144

    @memory_mb.setter
    def memory_mb(self, v: int):
        self.set("memory_mb", int(v))

    @property
    def game_dir(self) -> Path:
        try:
            p = Path(str(self.get("game_dir")))
        except Exception:
            p = ROOT / "game"
        return p if str(p) else (ROOT / "game")

    @game_dir.setter
    def game_dir(self, v):
        self.set("game_dir", str(v))

    @property
    def last_version(self) -> str:
        return str(self.get("last_version") or "1.21.4")

    @last_version.setter
    def last_version(self, v):
        self.set("last_version", str(v))


# Глобальный экземпляр (лениво, чтобы frozen-пути успели определиться)
_config = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
