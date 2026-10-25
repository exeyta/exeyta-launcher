# -*- coding: utf-8 -*-
"""Шаг 4 — ярлыки."""
from PyQt5.QtWidgets import QCheckBox, QLabel

from .base import PageWidget, make_heading


class ShortcutsPage(PageWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        make_heading("Ярлыки", self, y=0, px=24)
        tip = QLabel("Где создать ярлык запуска Exeyta?", self)
        tip.setStyleSheet("color: #b9a3b4; font-size: 13px; "
                          "background: transparent;")
        tip.move(0, 38)

        self.cb_desktop = QCheckBox("Создать ярлык на рабочем столе", self)
        self.cb_desktop.move(0, 78)
        self.cb_desktop.setChecked(True)

        self.cb_start = QCheckBox("Добавить в меню «Пуск»", self)
        self.cb_start.move(0, 118)
        self.cb_start.setChecked(True)

        note = QLabel(
            "Ярлыки указывают на ExeytaLauncher.exe в выбранном каталоге. "
            "Игровые данные (%APPDATA%\\Exeyta: аккаунты, логи, кэш) "
            "хранятся отдельно и не удаляются вместе с программой.", self)
        note.setWordWrap(True)
        note.setStyleSheet("color: #8d7084; font-size: 12px; "
                           "background: transparent;")
        note.setGeometry(0, 170, 696, 60)

    def desktop(self):
        return self.cb_desktop.isChecked()

    def startmenu(self):
        return self.cb_start.isChecked()

    def title(self):
        return "Ярлыки"
