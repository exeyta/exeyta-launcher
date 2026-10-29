# -*- coding: utf-8 -*-
"""Шаг 6 — завершение."""
from PyQt5.QtWidgets import QCheckBox, QLabel

from .base import LogoBadge, PageWidget, make_heading


class DonePage(PageWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logo = LogoBadge(64, self)
        self.logo.move(0, 4)
        make_heading("Установка завершена!", self, y=82, px=26)
        self.body = QLabel(
            "Exeyta установлен. При первом запуске лаунчер предложит "
            "скачать Minecraft и подходящую Java одним мастером.", self)
        self.body.setWordWrap(True)
        self.body.setStyleSheet("color: #8b8f98; font-size: 14px; "
                                "background: transparent;")
        self.body.setGeometry(0, 124, 696, 60)

        self.dest_lbl = QLabel("", self)
        self.dest_lbl.setStyleSheet("color: #7fbf8f; font-size: 13px; "
                                    "background: transparent;")
        self.dest_lbl.setGeometry(0, 190, 696, 20)

        self.cb_run = QCheckBox("Запустить Exeyta", self)
        self.cb_run.move(0, 230)
        self.cb_run.setChecked(True)

    def set_dest(self, path):
        self.dest_lbl.setText(str(path))

    def run_after(self):
        return self.cb_run.isChecked()

    def title(self):
        return "Готово"
