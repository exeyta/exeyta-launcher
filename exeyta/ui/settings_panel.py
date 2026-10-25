# -*- coding: utf-8 -*-
"""Панель «Настройки» (1536x320, r22) — 1:1 с assets/launcher-ui.svg.

4 карточки: Память (+ автозапуск), Java (+ JVM), Папка игры (+ Обзор),
Язык. Каждая карточка 332x228 (r16) с левой полосой sunH.
"""
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QFileDialog, QLineEdit, QWidget

from exeyta_shared import theme

from .controls import (CardPanel, FxButton, GradientSlider, PanelBox,
                       ToggleSwitch, add_label, rounded_path, w)


class _LangRow(QWidget):
    """Строка выбора языка: выбрана — без рамки и белым, иначе — рамка."""

    def __init__(self, text, selected, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self._text = text
        self._selected = selected
        self.setFixedSize(round(288 * k), round(42 * k))
        self.setCursor(Qt.PointingHandCursor)

    def set_selected(self, flag):
        flag = bool(flag)
        if flag != self._selected:
            self._selected = flag
            self.update()

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        r = QRectF_of(self)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1c1024"))
        p.drawRoundedRect(r, 12 * k, 12 * k)
        if not self._selected:
            pen = QPen(QColor("#18ffffff"))
            pen.setWidthF(1.0)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 12 * k, 12 * k)
        f = theme.font(14 * k, w(600 if self._selected else 500))
        p.setFont(f)
        p.setPen(QColor("#fff8f2" if self._selected else "#e7d5df"))
        from PyQt5.QtGui import QFontMetricsF
        fm = QFontMetricsF(f)
        y = 24 * k - fm.ascent()
        p.drawText(QRectF(14 * k, y, 260 * k, fm.height() + 2),
                   Qt.AlignLeft | Qt.AlignTop, self._text)
        p.end()


def QRectF_of(widget):
    from PyQt5.QtCore import QRectF
    return QRectF(widget.rect()).adjusted(0.5, 0.5, -0.5, -0.5)


class SettingsPanel(CardPanel):
    """Карточка «Настройки»."""

    memory_changed = pyqtSignal(int)
    autostart_changed = pyqtSignal(bool)
    jvm_edited = pyqtSignal(str)
    folder_chosen = pyqtSignal(str)

    MEM_MIN, MEM_MAX, MEM_STEP = 4096, 8192, 512

    def __init__(self, cfg, k=1.0, parent=None):
        super().__init__(round(1536 * k), round(320 * k), radius=22,
                         border="#18ffffff", parent=parent)
        self.k = float(k)
        self.cfg = cfg
        self._build()

    def _build(self):
        k = self.k
        add_label(self, k, 24, 38, 22, 700, 400, "Настройки")

        # --- карточка 1: Память (24,64) -----------------------------------
        c1 = PanelBox(round(332 * k), round(228 * k), radius=16,
                      fill="#100810", border="#10ffffff", strip=True,
                      parent=self)
        c1.move(round(24 * k), round(64 * k))
        add_label(c1, k, 22, 36, 14, 700, 280, "Память", color="#ffd0e0")
        add_label(c1, k, 22, 60, 12, 500, 288,
                  "%d MB  -  %d MB" % (self.MEM_MIN, self.MEM_MAX),
                  color="#b9a3b4")
        fld1 = PanelBox(round(288 * k), round(42 * k), radius=12,
                        fill="#1c1024", border="", parent=c1)
        fld1.move(round(22 * k), round(80 * k))
        self.lbl_mem = add_label(fld1, k, 14, 26, 14, 600, 260, "6 GB")
        self.slider = GradientSlider(self.MEM_MIN, self.MEM_MAX, self.MEM_STEP,
                                     self.cfg.memory_mb, 288, k=k, parent=c1)
        self.slider.move(round(22 * k), round(136 * k))
        self.slider.valueChanged.connect(self._on_memory)
        add_label(c1, k, 22, 184, 13, 500, 200, "Автозапуск", color="#e7d5df")
        self.tg_auto = ToggleSwitch(bool(self.cfg.get("autostart")), k=k,
                                    parent=c1)
        self.tg_auto.move(round(250 * k), round(168 * k))
        self.tg_auto.toggled.connect(self._on_autostart)

        # --- карточка 2: Java (384,64) ------------------------------------
        c2 = PanelBox(round(332 * k), round(228 * k), radius=16,
                      fill="#100810", border="#10ffffff", strip=True,
                      parent=self)
        c2.move(round(384 * k), round(64 * k))
        add_label(c2, k, 22, 36, 14, 700, 280, "Java", color="#ffd0e0")
        self.lbl_java_name = add_label(c2, k, 22, 60, 12, 500, 288,
                                       "Java 21 Temurin", color="#b9a3b4")
        fld2 = PanelBox(round(288 * k), round(42 * k), radius=12,
                        fill="#1c1024", border="", parent=c2)
        fld2.move(round(22 * k), round(80 * k))
        self.lbl_java_path = add_label(fld2, k, 14, 26, 14, 600, 260, "")
        self.lbl_java_path.setToolTip("")
        add_label(c2, k, 22, 146, 12, 500, 288, "JVM", color="#b9a3b4")
        self.edit_jvm = QLineEdit(str(self.cfg.get("jvm_args") or ""), c2)
        self.edit_jvm.setGeometry(round(22 * k), round(158 * k),
                                  round(288 * k), round(40 * k))
        self.edit_jvm.setStyleSheet(
            "QLineEdit { background: #1c1024; border: none; border-radius: 10px;"
            " padding: 0 14px; color: #ffe7b0; font-family: Consolas, "
            "'Courier New', monospace; font-size: %dpx; }"
            " QLineEdit:focus { background: #22142c; }" % max(10, round(13 * k)))
        self.edit_jvm.textChanged.connect(
            lambda t: self.cfg.set("jvm_args", t))
        self.edit_jvm.setToolTip("Дополнительные JVM-аргументы")

        # --- карточка 3: Папка игры (744,64) ------------------------------
        c3 = PanelBox(round(332 * k), round(228 * k), radius=16,
                      fill="#100810", border="#10ffffff", strip=True,
                      parent=self)
        c3.move(round(744 * k), round(64 * k))
        add_label(c3, k, 22, 36, 14, 700, 280, "Папка игры", color="#ffd0e0")
        add_label(c3, k, 22, 60, 12, 500, 288, "Каталог клиента",
                  color="#b9a3b4")
        fld3 = PanelBox(round(288 * k), round(42 * k), radius=12,
                        fill="#1c1024", border="", parent=c3)
        fld3.move(round(22 * k), round(80 * k))
        self.lbl_dir = add_label(fld3, k, 14, 26, 14, 600, 260, "")
        self.btn_browse = FxButton("Обзор", kind="chip",
                                   w_=round(288 * k), h_=round(42 * k),
                                   radius=12, px=14, svg_w=700, parent=c3)
        self.btn_browse.move(round(22 * k), round(142 * k))
        self.btn_browse.clicked.connect(self._browse)

        # --- карточка 4: Язык (1104,64) -----------------------------------
        c4 = PanelBox(round(332 * k), round(228 * k), radius=16,
                      fill="#100810", border="#10ffffff", strip=True,
                      parent=self)
        c4.move(round(1104 * k), round(64 * k))
        add_label(c4, k, 22, 36, 14, 700, 280, "Язык", color="#ffd0e0")
        add_label(c4, k, 22, 60, 12, 500, 288, "Интерфейс", color="#b9a3b4")
        self.row_ru = _LangRow("Русский", True, k=k, parent=c4)
        self.row_ru.move(round(22 * k), round(80 * k))
        self.row_en = _LangRow("English", False, k=k, parent=c4)
        self.row_en.move(round(22 * k), round(142 * k))
        self.row_ru.mousePressEvent = lambda e: self._lang("Русский")
        self.row_en.mousePressEvent = lambda e: self._lang("English")

        # стартовые значения
        self.set_memory_mb(self.cfg.memory_mb)
        self.set_folder(str(self.cfg.game_dir))

    # --- слоты -------------------------------------------------------------
    def _on_memory(self, mb):
        if mb % 1024 == 0:
            txt = "%d GB" % (mb // 1024)
        else:
            txt = "%d MB" % mb
        self.lbl_mem.setText(txt)
        self.cfg.memory_mb = mb
        self.memory_changed.emit(mb)

    def _on_autostart(self, on):
        self.cfg.set("autostart", bool(on))
        self.autostart_changed.emit(bool(on))

    def _browse(self):
        start = str(self.cfg.game_dir)
        d = QFileDialog.getExistingDirectory(self, "Папка игры", start)
        if d:
            self.cfg.game_dir = d
            self.set_folder(d)
            self.folder_chosen.emit(d)

    def _lang(self, lang):
        self.cfg.set("language", lang)
        self.row_ru.set_selected(lang == "Русский")
        self.row_en.set_selected(lang == "English")

    # --- обновления --------------------------------------------------------
    def set_memory_mb(self, mb):
        if mb != self.slider.value():
            self.slider.set_value(mb, emit=False)
        if mb % 1024 == 0:
            txt = "%d GB" % (mb // 1024)
        else:
            txt = "%d MB" % mb
        self.lbl_mem.setText(txt)

    def set_folder(self, path):
        from .launch_panel import elide_path
        txt = elide_path(path, 14, 250, self.k)
        self.lbl_dir.setText(txt)
        self.lbl_dir.setToolTip(str(path))

    def set_java(self, name, path):
        self.lbl_java_name.setText(name)
        from .launch_panel import elide_path
        self.lbl_java_path.setText(elide_path(path, 14, 250, self.k))
        self.lbl_java_path.setToolTip(str(path))
