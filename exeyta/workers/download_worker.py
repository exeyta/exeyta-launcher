# -*- coding: utf-8 -*-
"""Воркеры загрузки (QThread): установка MC+Java в едином мастере, список версий.

Правила производительности: всё скачивание только в QThread,
UI получает сигналы прогресса и не зависает.
"""
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from ..core import config as cfg
from ..core.java_resolver import major_for
from ..core.minecraft_installer import (Cancelled, cached_version_ids,
                                        install_version, is_client_installed)
from ..core.portable_java import install_java, is_installed


class InstallWorker(QThread):
    """Единый мастер: Клиент (Minecraft) -> Java (portable JRE)."""

    progressed = pyqtSignal(str, int, int, str)   # stage, done, total, message
    stage_changed = pyqtSignal(str)               # 'client' | 'java'
    succeeded = pyqtSignal()
    failed = pyqtSignal(str, str)                 # stage, текст ошибки
    cancelled = pyqtSignal()

    def __init__(self, version_id: str, game_dir=None, force=False, parent=None):
        super().__init__(parent)
        self.version_id = version_id
        self.game_dir = game_dir
        self.force = force
        self.major = major_for(version_id)
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _is_cancelled(self):
        return self._cancel

    def _progress(self, stage, done, total, message):
        self.progressed.emit(stage, int(done), int(total), str(message))

    def run(self):
        stage = "client"
        try:
            # ---- 1) Minecraft (клиент, библиотеки, ресурсы) --------------
            self.stage_changed.emit("client")
            if self.force or not is_client_installed(self.version_id, self.game_dir):
                install_version(self.version_id,
                                progress=self._progress,
                                cancel=self._is_cancelled,
                                game_dir=self.game_dir)
            else:
                self._progress("client", 100, 100, "Клиент %s уже установлен"
                               % self.version_id)
            if self._cancel:
                self.cancelled.emit()
                return

            # ---- 2) Portable Java ----------------------------------------
            stage = "java"
            self.stage_changed.emit("java")
            if self.force or not is_installed(self.major):
                install_java(self.major,
                             progress=self._progress,
                             cancel=self._is_cancelled,
                             force=self.force)
            else:
                self._progress("java", 100, 100, "Java %d уже установлена" % self.major)

            if self._cancel:
                self.cancelled.emit()
                return
            self.succeeded.emit()
        except Cancelled:
            self.cancelled.emit()
        except Exception as e:
            self.failed.emit(stage, str(e))


class VersionsWorker(QThread):
    """Список всех версий (релизы + снапшоты + старые) — не блокирует UI."""

    loaded = pyqtSignal(list)          # [{"id": str, "type": str}, ...]
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            from ..core.minecraft_installer import list_all_versions
            versions = list_all_versions()
            self.loaded.emit([{"id": v["id"],
                               "type": v.get("type", "release")}
                              for v in versions])
        except Exception:
            cached = cached_version_ids()
            if cached:
                from ..core.java_resolver import parse_version
                self.loaded.emit([{"id": i,
                                   "type": "release" if parse_version(i)
                                   else "snapshot"}
                                  for i in cached])
            else:
                self.failed.emit("Не удалось получить список версий")


class SkinLoadWorker(QThread):
    """Ленивая загрузка скина (PNG) — не блокирует UI при старте."""

    loaded = pyqtSignal(object)   # QImage
    failed = pyqtSignal(str)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            from PyQt5.QtGui import QImage, QImageReader
            if not self.path:
                self.failed.emit("")
                return
            reader = QImageReader(self.path)
            img = reader.read()
            if img.isNull():
                self.failed.emit("Не удалось прочитать скин")
                return
            if img.width() != img.height():
                img = img.scaled(64, 64, 1, 1)  # 64x64 (ratio handled upstream)
            self.loaded.emit(img)
        except Exception as e:
            self.failed.emit(str(e))


class SkinPatchWorker(QThread):
    """Подмена стандартного скина в клиентском jar (QThread, не блокирует UI).

    skin_path пуст/не существует -> возврат оригинальных скинов клиента.
    """

    done = pyqtSignal(str)      # 'applied:N' | 'skip' | 'restored:N' | ...
    progressed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, version_id, skin_path, game_dir=None, parent=None):
        super().__init__(parent)
        self.version_id = version_id
        self.skin_path = skin_path
        self.game_dir = game_dir
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            from ..core.skin_patcher import apply_skin
            path = self.skin_path
            if path and not Path(path).exists():
                path = None
            res = apply_skin(self.version_id, path, game_dir=self.game_dir,
                             cancel=lambda: self._cancel,
                             progress=self.progressed.emit)
            self.done.emit(res)
        except Exception as e:
            self.failed.emit(str(e))
