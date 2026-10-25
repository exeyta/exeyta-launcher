# -*- coding: utf-8 -*-
"""Базовые элементы шагов установщика (единый стиль с лаунчером)."""
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QLabel, QWidget

from exeyta_shared import theme

PAGE_W = 696
PAGE_H = 320


class LogoBadge(QWidget):
    """Квадрат 42x42, r13, sun-градиент, буква E (как в лаунчере)."""

    def __init__(self, size=42, parent=None):
        super().__init__(parent)
        self.size = int(size)
        self.setFixedSize(self.size, self.size)

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        g = theme.sun_gradient(r)
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, self.size * 13 / 42.0, self.size * 13 / 42.0)
        f = theme.font(self.size * 22 / 42.0, 87)
        p.setFont(f)
        p.setPen(QColor("#1a0a10"))
        p.drawText(r, Qt.AlignCenter, "E")
        p.end()


def make_heading(text, parent, y=0, px=24):
    lbl = QLabel(text, parent)
    lbl.setStyleSheet(
        "color: #fff8f2; font-size: %dpx; font-weight: 700;"
        " background: transparent;" % px)
    lbl.move(0, y)
    lbl.resize(PAGE_W, px + 14)
    return lbl


def make_body(text, parent, y, px=14, height=180):
    lbl = QLabel(text, parent)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        "color: #b9a3b4; font-size: %dpx; background: transparent;" % px)
    lbl.setGeometry(0, y, PAGE_W, height)
    return lbl


class PageWidget(QWidget):
    """Базовый шаг мастера фиксированного размера."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(PAGE_W, PAGE_H)

    def can_next(self):
        return True

    def on_enter(self):
        pass

    def title(self):
        return ""
