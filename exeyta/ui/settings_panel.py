# -*- coding: utf-8 -*-
"""Раздел «Настройки»: память, Java, папка игры и язык.

Спокойные карточки 2×2; все изменения сразу пишутся в config.json.
"""
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen
from PyQt5.QtWidgets import QFileDialog, QLineEdit, QWidget

from exeyta_shared import theme

from .controls import (CardPanel, FxButton, GradientSlider, PanelBox,
                       ToggleSwitch, add_label, rounded_path, w)


class _LangRow(QWidget):
    """Строка выбора языка."""

    def __init__(self, text, selected, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self._text = text
        self._selected = selected
        self.setFixedSize(round(506 * k), round(42 * k))
        self.setCursor(Qt.PointingHandCursor)

    def set_selected(self, flag):
        flag = bool(flag)
        if flag != self._selected:
            self._selected = flag
            self.update()

    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()   # обработчик назначается в SettingsPanel

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1c1d22"))
        p.drawRoundedRect(r, 9 * k, 9 * k)
        if self._selected:
            pen = QPen(QColor("#c9a45c"))
            pen.setWidthF(1.0)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 9 * k, 9 * k)
        else:
            pen = QPen(QColor("#2a2b31"))
            pen.setWidthF(1.0)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 9 * k, 9 * k)
        f = theme.font(13 * k, w(700 if self._selected else 500))
        p.setFont(f)
        p.setPen(QColor("#e8cf9a" if self._selected else "#c7cad1"))
        fm = QFontMetricsF(f)
        y = 24 * k - fm.ascent()
        p.drawText(QRectF(14 * k, y, 460 * k, fm.height() + 2),
                   Qt.AlignLeft | Qt.AlignTop, self._text)
        if self._selected:
            p.setPen(QColor("#c9a45c"))
            p.drawText(r.adjusted(0, 0, -14 * k, 0), Qt.AlignRight |
                       Qt.AlignVCenter, "✓")
        p.end()


class SettingsPanel(QWidget):
    """Страница «Настройки» (1144x640)."""

    memory_changed = pyqtSignal(int)
    autostart_changed = pyqtSignal(bool)
    jvm_edited = pyqtSignal(str)
    folder_chosen = pyqtSignal(str)

    MEM_MIN, MEM_MAX, MEM_STEP = 4096, 8192, 512

    def __init__(self, cfg, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.cfg = cfg
        self.setFixedSize(round(1144 * k), round(640 * k))
        self._build()

    def _card(self, x, y):
        c = CardPanel(round(558 * self.k), round(300 * self.k),
                      radius=14, border="#26272d", parent=self)
        c.move(round(x * self.k), round(y * self.k))
        return c

    def _build(self):
        k = self.k

        # ---------------------------------------------------------- память
        c1 = self._card(0, 0)
        add_label(c1, k, 26, 36, 14, 700, 400, "Память")
        add_label(c1, k, 26, 58, 11.5, 500, 500,
                  "Сколько оперативной памяти выделять игре", color="#8b8f98")
        self.lbl_mem = add_label(c1, k, 26, 96, 22, 700, 300, "6 ГБ")
        self.slider = GradientSlider(self.MEM_MIN, self.MEM_MAX, self.MEM_STEP,
                                     self.cfg.memory_mb, 506, k=k, parent=c1)
        self.slider.move(round(26 * k), round(116 * k))
        self.slider.valueChanged.connect(self._on_memory)
        add_label(c1, k, 26, 152, 10.5, 500, 500,
                  "4 ГБ — минимум · 8 ГБ — максимум", color="#62666e")

        sep = QWidget(c1)
        sep.setGeometry(round(26 * k), round(184 * k), round(506 * k), 1)
        sep.setStyleSheet("background: #232429;")
        add_label(c1, k, 26, 216, 12.5, 600, 300, "Запускать игру при старте")
        add_label(c1, k, 26, 235, 11, 500, 400,
                  "Автозапуск при открытии лаунчера", color="#62666e")
        self.tg_auto = ToggleSwitch(bool(self.cfg.get("autostart")), k=k,
                                    parent=c1)
        self.tg_auto.move(round(492 * k), round(208 * k))
        self.tg_auto.toggled.connect(self._on_autostart)

        # ------------------------------------------------------------ Java
        c2 = self._card(586, 0)
        add_label(c2, k, 26, 36, 14, 700, 400, "Java")
        self.lbl_java_name = add_label(c2, k, 26, 58, 11.5, 500, 500,
                                       "Java 21 Temurin", color="#8b8f98")
        fld2 = PanelBox(round(506 * k), round(40 * k), radius=9,
                        fill="#1c1d22", border="#2a2b31", parent=c2)
        fld2.move(round(26 * k), round(76 * k))
        self.lbl_java_path = add_label(fld2, k, 12, 25, 11.5, 500, 480, "")
        self.lbl_java_path.setToolTip("")
        add_label(c2, k, 26, 140, 11.5, 500, 200, "JVM-аргументы",
                  color="#8b8f98")
        self.edit_jvm = QLineEdit(str(self.cfg.get("jvm_args") or ""), c2)
        self.edit_jvm.setGeometry(round(26 * k), round(152 * k),
                                  round(506 * k), round(40 * k))
        self.edit_jvm.setStyleSheet(
            "QLineEdit { background: #1c1d22; border: 1px solid #2a2b31;"
            " border-radius: 9px; padding: 0 12px; color: #e8cf9a;"
            " font-family: Consolas, 'Courier New', monospace;"
            " font-size: %dpx; }"
            " QLineEdit:focus { border: 1px solid #c9a45c; }"
            % max(10, round(12 * k)))
        self.edit_jvm.textChanged.connect(
            lambda t: self.cfg.set("jvm_args", t))
        self.edit_jvm.setToolTip("Дополнительные JVM-аргументы")
        add_label(c2, k, 26, 214, 11, 500, 506,
                  "Java подбирается автоматически под версию Minecraft",
                  color="#62666e")
        add_label(c2, k, 26, 236, 11, 500, 506,
                  "Портативная сборка Temurin, системная Java не нужна",
                  color="#62666e")

        # ----------------------------------------------------- папка игры
        c3 = self._card(0, 320)
        add_label(c3, k, 26, 36, 14, 700, 400, "Папка игры")
        add_label(c3, k, 26, 58, 11.5, 500, 500,
                  "Каталог клиента, библиотек и миров", color="#8b8f98")
        fld3 = PanelBox(round(506 * k), round(40 * k), radius=9,
                        fill="#1c1d22", border="#2a2b31", parent=c3)
        fld3.move(round(26 * k), round(76 * k))
        self.lbl_dir = add_label(fld3, k, 12, 25, 11.5, 500, 480, "")
        self.btn_browse = FxButton("Обзор папки", kind="ghost",
                                   w_=round(506 * k), h_=round(42 * k),
                                   radius=9, px=13, svg_w=600, parent=c3)
        self.btn_browse.move(round(26 * k), round(132 * k))
        self.btn_browse.clicked.connect(self._browse)
        add_label(c3, k, 26, 204, 11, 500, 506,
                  "В папке хранятся versions, libraries, assets и mods",
                  color="#62666e")
        add_label(c3, k, 26, 226, 11, 500, 506,
                  "Настройки и профиль лежат рядом с лаунчером",
                  color="#62666e")

        # ------------------------------------------------------------ язык
        c4 = self._card(586, 320)
        add_label(c4, k, 26, 36, 14, 700, 400, "Язык")
        add_label(c4, k, 26, 58, 11.5, 500, 500,
                  "Язык интерфейса лаунчера", color="#8b8f98")
        self.row_ru = _LangRow("Русский", True, k=k, parent=c4)
        self.row_ru.move(round(26 * k), round(76 * k))
        self.row_en = _LangRow("English", False, k=k, parent=c4)
        self.row_en.move(round(26 * k), round(126 * k))
        self.row_ru.mousePressEvent = lambda e: self._lang("Русский")
        self.row_en.mousePressEvent = lambda e: self._lang("English")
        add_label(c4, k, 26, 194, 11, 500, 506,
                  "Интерфейс переведён не полностью: часть подсказок — "
                  "на русском", color="#62666e")

        self.set_memory_mb(self.cfg.memory_mb)
        self.set_folder(str(self.cfg.game_dir))
        self._lang(str(self.cfg.get("language") or "Русский"))

    # --- слоты -----------------------------------------------------------
    def _on_memory(self, mb):
        if mb % 1024 == 0:
            txt = "%d ГБ" % (mb // 1024)
        else:
            txt = "%d МБ" % mb
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

    # --- обновления ------------------------------------------------------
    def set_memory_mb(self, mb):
        if mb != self.slider.value():
            self.slider.set_value(mb, emit=False)
        if mb % 1024 == 0:
            txt = "%d ГБ" % (mb // 1024)
        else:
            txt = "%d МБ" % mb
        self.lbl_mem.setText(txt)

    def set_folder(self, path):
        from .launch_panel import elide_path
        txt = elide_path(path, 11.5, 470, self.k)
        self.lbl_dir.setText(txt)
        self.lbl_dir.setToolTip(str(path))

    def set_java(self, name, path):
        self.lbl_java_name.setText(name)
        from .launch_panel import elide_path
        self.lbl_java_path.setText(elide_path(path, 11.5, 470, self.k))
        self.lbl_java_path.setToolTip(str(path))
