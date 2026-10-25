# -*- coding: utf-8 -*-
"""Шаг 3 — путь установки (%LOCALAPPDATA%\\Exeyta по умолчанию)."""
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QLabel, QLineEdit

from exeyta.ui.controls import FxButton

from ...core.install_paths import default_install_dir, validate_install_dir
from .base import PageWidget, make_heading


class PathPage(PageWidget):
    path_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        make_heading("Куда установить Exeyta?", self, y=0, px=24)
        tip = QLabel("Рекомендуется оставить путь по умолчанию.", self)
        tip.setStyleSheet("color: #b9a3b4; font-size: 13px; "
                          "background: transparent;")
        tip.move(0, 38)

        self.edit = QLineEdit(str(default_install_dir()), self)
        self.edit.setGeometry(0, 70, 536, 48)
        self.edit.textChanged.connect(self._changed)

        btn = FxButton("Обзор", kind="chip", w_=150, h_=48, radius=12,
                       px=14, svg_w=700, parent=self)
        btn.move(546, 70)
        btn.clicked.connect(self._browse)

        self.hint = QLabel(
            "Создаются каталоги: runtime (jre8/jre17/jre21 — скачает "
            "лаунчер), game (клиент), mods, scripts, logs.", self)
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: #8d7084; font-size: 12px; "
                                "background: transparent;")
        self.hint.setGeometry(0, 134, 696, 44)

        self.err = QLabel("", self)
        self.err.setStyleSheet("color: #ff4d6d; font-size: 13px; "
                               "background: transparent;")
        self.err.setGeometry(0, 186, 696, 24)

        info = QLabel("Занято примерно 120 МБ (без Minecraft/Java).", self)
        info.setStyleSheet("color: #b9a3b4; font-size: 12px; "
                           "background: transparent;")
        info.move(0, 220)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Каталог установки",
                                             self.edit.text())
        if d:
            self.edit.setText(d)

    def _changed(self, text):
        ok, msg = validate_install_dir(text)
        self.err.setText(msg)
        self.path_changed.emit(text)

    def can_next(self):
        ok, msg = validate_install_dir(self.edit.text())
        self.err.setText(msg)
        return ok

    def path(self):
        return self.edit.text().strip()

    def title(self):
        return "Путь"
