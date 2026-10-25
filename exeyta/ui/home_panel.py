# -*- coding: utf-8 -*-
"""Раздел «Главная» — стартовый экран лаунчера (вкладка по умолчанию).

Приветствие + статус сессии, сводка (версия / Java / память / папка)
и большая кнопка ИГРАТЬ. Всё обновляется из MainWindow._refresh_state.
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget

from exeyta_shared import theme

from .controls import (CardPanel, FxButton, PanelBox, add_label, draw_base,
                       rounded_path, w)
from .launch_panel import _ClickZone, elide_path


class HomePanel(CardPanel):
    """Карточка «Главная» (760x560)."""

    play_clicked = pyqtSignal()
    version_clicked = pyqtSignal()

    def __init__(self, cfg, k=1.0, parent=None):
        super().__init__(round(760 * k), round(560 * k), radius=22,
                         border="#18ffffff", parent=parent)
        self.k = float(k)
        self.cfg = cfg
        self._build()

    def _build(self):
        k = self.k

        # заголовок + статус
        add_label(self, k, 32, 38, 22, 700, 400, "Главная")
        self.lbl_status = add_label(self, k, 32, 60, 12, 500, 500,
                                    "сессия готова", color="#86efac")

        # приветствие
        self.lbl_hello = add_label(self, k, 32, 150, 26, 800, 380,
                                   "Привет, Exeyta!")
        self.lbl_prem = add_label(self, k, 32, 186, 13, 600, 300,
                                  "Premium Offline", color="#ffb703")
        note = add_label(self, k, 32, 240, 13, 500, 340,
                         "Скин применяется в игру автоматически\n"
                         "при нажатии «ИГРАТЬ».",
                         color="#b9a3b4")
        note.setWordWrap(True)
        note.setGeometry(round(32 * k), round(232 * k),
                         round(350 * k), round(70 * k))

        # сводка 2x2
        facts = PanelBox(round(328 * k), round(210 * k), radius=16,
                         fill="#120910", border="#10ffffff", parent=self)
        facts.move(round(400 * k), round(110 * k))
        cells = [
            (20, 44, "Версия", "1.21.4"),
            (178, 44, "Java", "21 Temurin"),
            (20, 140, "Память", "6 GB"),
            (178, 140, "Папка", "…"),
        ]
        self.lbls = {}
        for x, y, cap, val in cells:
            add_label(facts, k, x, y, 11, 500, 150, cap, color="#8d7084")
            lbl = add_label(facts, k, x, y + 30, 15, 600, 150, val)
            self.lbls[cap] = lbl

        # клик по версии открывает диалог выбора (как в разделе «Играть»)
        self._ver_hit = _ClickZone(facts)
        self._ver_hit.setGeometry(round(10 * k), round(26 * k),
                                  round(160 * k), round(70 * k))
        self._ver_hit.setToolTip("Выбрать версию Minecraft")
        self._ver_hit.clicked.connect(self.version_clicked.emit)

        # ИГРАТЬ
        self.btn_play = FxButton("ИГРАТЬ", kind="sun",
                                 w_=round(382 * k), h_=round(70 * k),
                                 radius=18, px=22, svg_w=800,
                                 letter=3.0 * k, glow="#ff7a4d", parent=self)
        self.btn_play.move(round(189 * k), round(420 * k))
        self.btn_play.clicked.connect(self.play_clicked.emit)

        hint = add_label(self, k, 100, 522, 12, 500, 560,
                         "Minecraft и Java качаются лаунчером одним мастером",
                         color="#8d7084", align=Qt.AlignCenter)

    # --- обновления из MainWindow -----------------------------------------
    def set_status(self, text, color="#86efac"):
        self.lbl_status.setText(text)
        pal = self.lbl_status.palette()
        pal.setColor(self.lbl_status.foregroundRole(), QColor(color))
        self.lbl_status.setPalette(pal)

    def set_busy(self, flag):
        self.btn_play.set_disabled(bool(flag))
        self.btn_play.set_text("ЗАПУСК..." if flag else "ИГРАТЬ")

    def set_greeting(self, name):
        self.lbl_hello.setText("Привет, %s!" % (name or "Exeyta"))

    def set_version(self, vid):
        self.lbls["Версия"].setText(str(vid))

    def set_java(self, text):
        self.lbls["Java"].setText(text)

    def set_memory(self, text):
        self.lbls["Память"].setText(text)

    def set_folder(self, path):
        txt = elide_path(path, 15, 150, self.k)
        self.lbls["Папка"].setText(txt)
        self.lbls["Папка"].setToolTip(str(path))
