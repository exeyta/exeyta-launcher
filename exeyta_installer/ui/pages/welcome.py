# -*- coding: utf-8 -*-
"""Шаг 1 — приветствие."""
from .base import LogoBadge, PageWidget, make_body, make_heading


class WelcomePage(PageWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logo = LogoBadge(72, self)
        self.logo.move(0, 6)
        make_heading("Добро пожаловать в Exeyta", self, y=96, px=26)
        make_body(
            "Мастер установки офлайн-лаунчера Minecraft.\n\n"
            "• Установщик развернёт лаунчер, создаст ярлыки и структуру "
            "каталогов (runtime, game, mods, scripts, logs).\n"
            "• Minecraft и портативную Java (jre8 / jre17 / jre21) скачает "
            "сам лаунчер — единым мастером, Java определяется по версии "
            "автоматически.\n"
            "• Только offline-аккаунты: без Microsoft/Mojang OAuth.\n\n"
            "Требования: Windows 10/11 x64. Системная Java не нужна.",
            self, y=142, height=170)

    def title(self):
        return "Приветствие"
