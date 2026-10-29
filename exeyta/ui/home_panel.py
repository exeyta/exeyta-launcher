# -*- coding: utf-8 -*-
"""Раздел «Главная»: выбранная версия, состояние и параметры запуска.

Визуальный стиль — спокойные тёмные карточки с золотистым акцентом.
Все значения обновляются из MainWindow._refresh_state.
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QLabel, QWidget

from exeyta_shared import theme

from .controls import (Badge, CardPanel, ClickZone, FxButton, add_label,
                       draw_base, w)


class HomePanel(QWidget):
    """Главный экран (1144x560)."""

    play_clicked = pyqtSignal()
    version_clicked = pyqtSignal()
    open_folder_clicked = pyqtSignal()

    def __init__(self, cfg, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.cfg = cfg
        self.setFixedSize(round(1144 * k), round(560 * k))
        self._build()

    def _build(self):
        k = self.k

        # ---------------------------------------------------------- версия
        self.card_ver = CardPanel(round(730 * k), round(270 * k),
                                  radius=14, border="#26272d", parent=self)
        self.card_ver.move(0, 0)
        self.lbl_ver_cap = add_label(self.card_ver, k, 26, 36, 11, 700, 300,
                                     "ВЫБРАННАЯ ВЕРСИЯ", color="#8b8f98")
        self.lbl_ver_cap.setStyleSheet("letter-spacing: 1px;")
        self.lbl_greeting = add_label(
            self.card_ver, k, 26, 36, 11, 500, 400, "",
            color="#62666e", align=Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_version = add_label(self.card_ver, k, 26, 108, 46, 800, 400,
                                     str(self.cfg.last_version))
        self.badge = Badge("готова", k=k, color="#7fbf8f",
                           parent=self.card_ver)
        self.badge.move(round(26 * k), round(126 * k))
        self.lbl_ready = add_label(
            self.card_ver, k, 112, 142, 12, 500, 560,
            "Установлена и готова к запуску", color="#8b8f98")

        # акцентная линия под версией
        self._line = _AccentLine(self.card_ver, k=k)
        self._line.setGeometry(round(26 * k), round(166 * k),
                               round(678 * k), round(4 * k))

        ico_play = theme.icon_pixmap(theme.ICON_PLAY, round(14 * k),
                                     "#1c1609", stroke=1.8, fill="#1c1609")
        self.btn_play = FxButton("Играть", kind="sun",
                                 w_=round(150 * k), h_=round(46 * k),
                                 radius=9, px=14, svg_w=700,
                                 icon=ico_play, gap=9, parent=self.card_ver)
        self.btn_play.move(round(26 * k), round(196 * k))
        self.btn_play.clicked.connect(self.play_clicked.emit)

        ico_chev = theme.icon_pixmap(theme.ICON_CHEVRON, round(14 * k),
                                     "#c7cad1", stroke=1.8)
        self.btn_version = FxButton("Выбрать версию", kind="ghost",
                                    w_=round(172 * k), h_=round(46 * k),
                                    radius=9, px=13, svg_w=600,
                                    icon=ico_chev, gap=8,
                                    parent=self.card_ver)
        self.btn_version.move(round(188 * k), round(196 * k))
        self.btn_version.clicked.connect(self.version_clicked.emit)

        ico_folder = theme.icon_pixmap(theme.ICON_FOLDER, round(15 * k),
                                       "#c7cad1", stroke=1.7)
        self.btn_folder = FxButton("Открыть папку", kind="ghost",
                                   w_=round(172 * k), h_=round(46 * k),
                                   radius=9, px=13, svg_w=600,
                                   icon=ico_folder, gap=8,
                                   parent=self.card_ver)
        self.btn_folder.move(round(372 * k), round(196 * k))
        self.btn_folder.clicked.connect(self.open_folder_clicked.emit)

        # -------------------------------------------------------- состояние
        self.card_state = CardPanel(round(394 * k), round(270 * k),
                                    radius=14, border="#26272d", parent=self)
        self.card_state.move(round(750 * k), 0)
        add_label(self.card_state, k, 24, 36, 11, 700, 300, "СОСТОЯНИЕ",
                  color="#8b8f98")
        self._state_rows = {}
        rows = [
            ("installed", "Установлено версий", "1"),
            ("catalog", "Доступно в каталоге", "—"),
            ("profile", "Профиль", "Exeyta"),
        ]
        y0 = 64
        for i, (key, cap, val) in enumerate(rows):
            y = y0 + i * 62
            if i:
                self._sep(self.card_state, y - 12, 24, 370)
            add_label(self.card_state, k, 24, y + 22, 12, 500, 220, cap,
                      color="#9a9ea7")
            self._state_rows[key] = add_label(
                self.card_state, k, 24, y + 22, 12, 700, 346, val,
                color="#eceef2", align=Qt.AlignRight | Qt.AlignVCenter)

        # ---------------------------------------------------------- память
        self.card_params = CardPanel(round(730 * k), round(250 * k),
                                     radius=14, border="#26272d", parent=self)
        self.card_params.move(0, round(290 * k))
        add_label(self.card_params, k, 26, 36, 11, 700, 350,
                  "ПАРАМЕТРЫ ЗАПУСКА", color="#8b8f98")
        self.lbl_mem = self._param_row(self.card_params, 64, "Память",
                                       "6144 МБ (авто)")
        self.lbl_java = self._param_row(self.card_params, 126, "Java",
                                        "подбирается автоматически")
        self.lbl_folder = self._param_row(self.card_params, 188, "Папка игры",
                                          "…")

        # ------------------------------------------------------ о лаунчере
        self.card_about = CardPanel(round(394 * k), round(250 * k),
                                    radius=14, border="#26272d", parent=self)
        self.card_about.move(round(750 * k), round(290 * k))
        add_label(self.card_about, k, 24, 36, 11, 700, 350, "О ЛАУНЧЕРЕ",
                  color="#8b8f98")
        add_label(self.card_about, k, 24, 68, 14, 700, 350,
                  "Exeyta Launcher %s" % theme.LAUNCHER_VERSION)
        self.lbl_about_path = QLabel("", self.card_about)
        self.lbl_about_path.setFont(theme.font(11.5 * k, 50))
        self.lbl_about_path.setStyleSheet(
            "color: #8b8f98; background: transparent;")
        self.lbl_about_path.setWordWrap(True)
        self.lbl_about_path.setGeometry(round(24 * k), round(84 * k),
                                        round(346 * k), round(40 * k))
        self.note_about = QLabel(
            "Настройки, версии и профиль хранятся в папке лаунчера. "
            "Удаление папки полностью отключает установку.",
            self.card_about)
        self.note_about.setFont(theme.font(11.5 * k, 50))
        self.note_about.setStyleSheet(
            "color: #8b8f98; background: transparent;")
        self.note_about.setWordWrap(True)
        self.note_about.setGeometry(round(24 * k), round(136 * k),
                                    round(346 * k), round(70 * k))

    def _sep(self, parent, y, x1, x2):
        k = self.k
        s = QWidget(parent)
        s.setGeometry(round(x1 * k), round(y * k),
                      round((x2 - x1) * k), 1)
        s.setStyleSheet("background: #232429;")

    def _param_row(self, parent, y, cap, val):
        k = self.k
        add_label(parent, k, 26, y + 24, 12, 500, 160, cap, color="#9a9ea7")
        lbl = add_label(parent, k, 190, y + 24, 12.5, 600, 514, val,
                        align=Qt.AlignRight | Qt.AlignVCenter)
        if y > 64:
            self._sep(parent, y - 14, 26, 704)
        return lbl

    # --- обновления из MainWindow ----------------------------------------
    def set_status(self, text, color="#7fbf8f"):
        pass  # статус показывается в нижней строке окна

    def set_busy(self, flag):
        self.btn_play.set_disabled(bool(flag))
        self.btn_play.set_text("Запуск…" if flag else "Играть")

    def set_greeting(self, name):
        self.lbl_greeting.setText("Привет, %s" % (name or "Exeyta"))

    def set_version(self, vid):
        text = str(vid)
        self.lbl_version.setText(text)
        px = 46 if len(text) <= 10 else 34
        self.lbl_version.setFont(theme.font(px * self.k, 800))

    def set_ready(self, ready, text=None):
        self.badge.set_text("готова" if ready else "не готова")
        self.badge.set_color("#7fbf8f" if ready else "#c9a45c")
        self.lbl_ready.setText(
            text if text is not None else
            ("Установлена и готова к запуску" if ready
             else "Требуется установка клиента или Java"))

    def set_java(self, text):
        self.lbl_java.setText(text)

    def set_memory(self, text):
        if isinstance(text, (int, float)):
            txt = "%d МБ (авто)" % int(text)
        else:
            txt = str(text)
            if txt.endswith(" GB"):
                mb = int(float(txt[:-3]) * 1024)
                txt = "%d МБ (авто)" % mb
        self.lbl_mem.setText(txt)

    def set_folder(self, path):
        from .launch_panel import elide_path
        txt = elide_path(path, 12.5, 500, self.k)
        self.lbl_folder.setText(txt)
        self.lbl_folder.setToolTip(str(path))
        self.lbl_about_path.setText(elide_path(path, 11.5, 330, self.k))
        self.lbl_about_path.setToolTip(str(path))

    def set_counts(self, installed, available):
        self._state_rows["installed"].setText(str(installed))
        self._state_rows["catalog"].setText(
            str(available) if available else "—")

    def set_profile(self, name):
        self._state_rows["profile"].setText(str(name or "Exeyta"))


class _AccentLine(QWidget):
    """Тонкая золотая линия-индикатор под выбранной версией."""

    def __init__(self, parent=None, k=1.0):
        super().__init__(parent)
        self.k = float(k)

    def paintEvent(self, event=None):
        from PyQt5.QtGui import QPainter, QLinearGradient, QColor
        from PyQt5.QtCore import QRectF, Qt
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        g = QLinearGradient(r.left(), 0, r.right(), 0)
        g.setColorAt(0.0, QColor("#a8843c"))
        g.setColorAt(0.55, QColor("#d3b06a"))
        g.setColorAt(1.0, QColor("#c9a45c"))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, 2, 2)
        p.end()
