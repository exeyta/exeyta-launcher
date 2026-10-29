# -*- coding: utf-8 -*-
"""Раздел «Консоль»: журнал запуска игры и сообщения лаунчера."""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QPlainTextEdit, QWidget

from exeyta_shared import theme

from .controls import CardPanel, FxButton, add_label


class ConsolePanel(QWidget):
    """Страница «Консоль» (1144x640)."""

    open_logs_clicked = pyqtSignal()

    def __init__(self, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.setFixedSize(round(1144 * k), round(640 * k))
        self._build()

    def _build(self):
        k = self.k
        bar = CardPanel(round(1144 * k), round(58 * k), radius=12,
                        border="#26272d", sheen=False, parent=self)
        add_label(bar, k, 22, 34, 12.5, 600, 300, "Журнал запуска")
        self.lbl_state = add_label(bar, k, 150, 34, 11.5, 500, 500,
                                   "ожидание", color="#62666e")
        self.btn_clear = FxButton("Очистить", kind="ghost",
                                  w_=round(110 * k), h_=round(34 * k),
                                  radius=8, px=12, svg_w=600, parent=bar)
        self.btn_clear.move(round(898 * k), round(12 * k))
        self.btn_clear.clicked.connect(self.clear)
        self.btn_logs = FxButton("Открыть логи", kind="ghost",
                                 w_=round(114 * k), h_=round(34 * k),
                                 radius=8, px=12, svg_w=600, parent=bar)
        self.btn_logs.move(round(1008 * k), round(12 * k))
        self.btn_logs.clicked.connect(self.open_logs_clicked.emit)

        self.edit = QPlainTextEdit(self)
        self.edit.setObjectName("consoleView")
        self.edit.setReadOnly(True)
        self.edit.setGeometry(round(0 * k), round(74 * k),
                              round(1144 * k), round(566 * k))
        self.edit.setFont(theme.font(12 * k, 50, family="Consolas"))
        self.edit.setPlaceholderText(
            "Здесь появятся сообщения лаунчера и вывод игры…")

    def append_log(self, line):
        text = str(line).rstrip()
        if not text:
            return
        self.edit.appendPlainText(text)
        bar = self.edit.verticalScrollBar()
        bar.setValue(bar.maximum())

    def set_running(self, running, text=None):
        self.lbl_state.setText(text or ("игра запущена" if running
                                        else "ожидание"))
        pal = self.lbl_state.palette()
        pal.setColor(self.lbl_state.foregroundRole(),
                     QColor("#7fbf8f" if running else "#62666e"))
        self.lbl_state.setPalette(pal)

    def clear(self):
        self.edit.clear()
