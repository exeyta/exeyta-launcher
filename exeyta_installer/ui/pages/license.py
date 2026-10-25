# -*- coding: utf-8 -*-
"""Шаг 2 — согласие (лицензия)."""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QCheckBox, QPlainTextEdit

from .base import PageWidget, make_heading


LICENSE_TEXT = """Exeyta Launcher — лицензионное соглашение (краткая версия)

1. Exeyta Launcher является бесплатным офлайн-лаунчером Minecraft.
   Он не связан с Mojang Studios, Microsoft и не использует их сервисы
   авторизации (Microsoft/Mojang OAuth не применяется).

2. Лаунчер использует только offline-аккаунты: генерация локального
   offline UUID и локальные скины. Никакие учётные данные не передаются.

3. Скачивание клиента Minecraft и портативной Java (Eclipse Temurin)
   выполняется из официальных источников исключительно для запуска игры.

4. Вы подтверждаете, что владеете копией Minecraft либо используете
   лицензионно доступные ресурсы игры, и соблюдаёте условия использования
   Mojang (EULA).

5. Программа распространяена «как есть»; разработчик не несёт
   ответственности за данные и результаты использования.

Продолжая установку, вы принимаете эти условия.
"""


class LicensePage(PageWidget):
    agreed_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        make_heading("Лицензионное соглашение", self, y=0, px=24)
        self.text = QPlainTextEdit(LICENSE_TEXT, self)
        self.text.setReadOnly(True)
        self.text.setGeometry(0, 40, 696, 224)
        from .base import PAGE_W  # noqa: F401  (размер шага мастера)
        self.check = QCheckBox("Я принимаю условия лицензии", self)
        self.check.move(0, 276)
        self.check.toggled.connect(lambda on: self.agreed_changed.emit(on))

    def can_next(self):
        return self.check.isChecked()

    def title(self):
        return "Согласие"
