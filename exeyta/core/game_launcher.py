# -*- coding: utf-8 -*-
"""Запуск игры: .bat + Python-оркестратор (UI не блокируется).

Логи: %APPDATA%/Exeyta/logs/launch_<timestamp>.log
Запуск через subprocess.Popen в отдельном QThread.
"""
import os
import subprocess
import time
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from . import config as cfg

CREATE_NO_WINDOW = 0x08000000


class GameWorker(QThread):
    """Исполняет сгенерированный .bat, стримит логи, не трогая UI."""

    log_line = pyqtSignal(str)
    game_started = pyqtSignal()
    game_finished = pyqtSignal(int)
    game_failed = pyqtSignal(str)

    def __init__(self, bat: Path, cwd: Path = None, parent=None):
        super().__init__(parent)
        self.bat = Path(bat)
        self.cwd = Path(cwd) if cwd else cfg.root_dir()
        self._proc = None
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        try:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
        except Exception:
            pass

    def _log_file(self) -> Path:
        ts = time.strftime("%Y%m%d_%H%M%S")
        return cfg.logs_dir() / ("launch_%s.log" % ts)

    def run(self):
        if not self.bat.exists():
            self.game_failed.emit("Не найден bat: %s" % self.bat)
            return
        log_path = self._log_file()
        env = dict(os.environ)
        env.setdefault("LANG", "ru_RU.UTF-8")
        # не даём внешнему JAVA_TOOL_OPTIONS конфликтовать с нашими -Xmx
        env.pop("JAVA_TOOL_OPTIONS", None)
        try:
            with open(log_path, "ab") as logf:
                header = ("=== Exeyta launch: %s ===\r\n" % self.bat.name).encode("utf-8")
                logf.write(header)
                self.log_line.emit("Запуск: %s" % self.bat.name)
                creationflags = 0
                if os.name == "nt":
                    creationflags = CREATE_NO_WINDOW
                self._proc = subprocess.Popen(
                    ["cmd", "/d", "/c", str(self.bat)],
                    cwd=str(self.cwd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    env=env,
                    creationflags=creationflags,
                )
                self.game_started.emit()
                for raw in iter(self._proc.stdout.readline, b""):
                    if not raw:
                        break
                    line = raw.decode("utf-8", "replace").rstrip("\r\n")
                    try:
                        logf.write(raw.rstrip(b"\r\n") + b"\r\n")
                        logf.flush()
                    except Exception:
                        pass
                    if line.strip():
                        self.log_line.emit(line[-400:])
                rc = self._proc.wait()
                self.log_line.emit("Процесс завершён с кодом %d" % rc)
                logf.write(("=== rc=%d ===\r\n" % rc).encode("utf-8"))
            if self._cancelled:
                self.game_finished.emit(-1)
            elif rc != 0:
                self.game_failed.emit("Игра завершилась с кодом %d (см. лог %s)"
                                      % (rc, log_path.name))
                self.game_finished.emit(rc)
            else:
                self.game_finished.emit(0)
        except Exception as e:
            self.game_failed.emit("Ошибка запуска: %s" % e)
