# -*- coding: utf-8 -*-
"""Шаг 5 — прогресс копирования (QThread)."""
from PyQt5.QtWidgets import QLabel, QProgressBar

from .base import PageWidget, make_heading


class ProgressPage(PageWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        make_heading("Копирование файлов…", self, y=0, px=24)
        self.dest_lbl = QLabel("", self)
        self.dest_lbl.setStyleSheet("color: #86efac; font-size: 13px; "
                                    "background: transparent;")
        self.dest_lbl.move(0, 40)

        self.bar = QProgressBar(self)
        self.bar.setObjectName("progressWiz")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setGeometry(0, 76, 696, 16)

        self.pct = QLabel("0%", self)
        self.pct.setStyleSheet("color: #ffe7b0; font-size: 13px; "
                               "font-weight: 700; background: transparent;")
        self.pct.setGeometry(0, 100, 696, 20)

        self.file_lbl = QLabel("Подготовка…", self)
        self.file_lbl.setStyleSheet("color: #b9a3b4; font-size: 13px; "
                                    "background: transparent;")
        self.file_lbl.setGeometry(0, 126, 696, 20)

        self.status = QLabel("", self)
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #ff4d6d; font-size: 13px; "
                                  "background: transparent;")
        self.status.setGeometry(0, 156, 696, 60)

        self.summary = QLabel(
            "Сейчас: копирование лаунчера и создание структуры каталогов. "
            "Minecraft и Java установит сам лаунчер при первом запуске.",
            self)
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("color: #8d7084; font-size: 12px; "
                                   "background: transparent;")
        self.summary.setGeometry(0, 224, 696, 50)

    def set_dest(self, path):
        self.dest_lbl.setText(str(path))

    def set_progress(self, done, total, name):
        pct = 0 if total <= 0 else int(done * 100 / total)
        pct = max(0, min(100, pct))          # защита от «102%»
        self.bar.setValue(pct)
        self.pct.setText("%d%%" % pct)
        text = str(name)
        if len(text) > 76:
            text = "…" + text[-75:]
        self.file_lbl.setText(text)

    def set_error(self, message):
        self.status.setText(str(message))
        self.file_lbl.setText("Ошибка")
        self.bar.setValue(0)
        self.pct.setText("0%")

    def set_done(self):
        self.bar.setValue(100)
        self.pct.setText("100%")
        self.file_lbl.setText("Готово")
        self.status.setStyleSheet("color: #86efac; font-size: 13px; "
                                  "background: transparent;")
        self.status.setText("Лаунчер установлен.")

    def title(self):
        return "Установка"
