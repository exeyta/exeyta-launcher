# -*- coding: utf-8 -*-
"""Окно установщика ExeytaSetup: те же токены темы, что у лаунчера.

Шаги: приветствие → согласие → путь → ярлыки → прогресс копирования
(QThread) → «Запустить Exeyta».
"""
from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from exeyta_shared import theme
from exeyta_shared.animations import HoverFader, fade_in

from ..core.file_copy import CopyWorker, launch_installed
from ..core.install_paths import default_install_dir
from exeyta.ui.controls import FxButton
from .pages import (DonePage, LicensePage, PathPage, ProgressPage,
                    ShortcutsPage, WelcomePage)
from .pages.base import LogoBadge

W = 760
H = 540


class _CloseBtn(QWidget):
    """Крестик окна (в полосе над контентом)."""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 18)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = HoverFader(self, ms=200)

    def enterEvent(self, event):
        self._hover.target(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover.target(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = self._hover.hoverT
        color = QColor("#8d7084") if t < 0.4 else QColor("#ff4d6d")
        pen = QPen(color)
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        s = 5.0
        p.drawLine(QPointF_(cx - s, cy - s), QPointF_(cx + s, cy + s))
        p.drawLine(QPointF_(cx + s, cy - s), QPointF_(cx - s, cy + s))
        p.end()


def QPointF_(x, y):
    from PyQt5.QtCore import QPointF
    return QPointF(x, y)


class WizardWindow(QWidget):
    """Мастер установки (6 шагов)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(W, H)
        self.setWindowTitle("ExeytaSetup")

        self._drag_pos = None
        self._worker = None
        self._install_dir = str(default_install_dir())
        self._desktop = True
        self._startmenu = True
        self._error = False

        self._build_header()
        self._build_pages()
        self._build_footer()
        self._show_page(0)

    # ------------------------------------------------------------------ UI
    def _build_header(self):
        self.logo = LogoBadge(42, self)
        self.logo.move(32, 26)

        t = QLabel("Exeyta", self)
        t.setStyleSheet("color: #fff8f2; font-size: 22px; font-weight: 800; "
                        "background: transparent;")
        t.setGeometry(86, 24, 220, 30)

        s = QLabel("УСТАНОВЩИК", self)
        s.setStyleSheet("color: #c9a8b8; font-size: 10px; "
                        "background: transparent;")
        s.setGeometry(87, 52, 220, 16)

        self.step_lbl = QLabel("", self)
        self.step_lbl.setStyleSheet("color: #b9a3b4; font-size: 13px; "
                                    "background: transparent;")
        self.step_lbl.setGeometry(W - 32 - 220, 34, 220, 22)
        self.step_lbl.setAlignment(Qt.AlignRight)

        self.close_btn = _CloseBtn(self)
        self.close_btn.move(W - 32 - 24, 70)
        self.close_btn.clicked.connect(self._on_close)

    def _build_pages(self):
        self.stack = QStackedWidget(self)
        self.stack.setGeometry(32, 104, 696, 320)

        self.page_welcome = WelcomePage()
        self.page_license = LicensePage()
        self.page_path = PathPage()
        self.page_shortcuts = ShortcutsPage()
        self.page_progress = ProgressPage()
        self.page_done = DonePage()

        for p in (self.page_welcome, self.page_license, self.page_path,
                  self.page_shortcuts, self.page_progress, self.page_done):
            self.stack.addWidget(p)

        self.page_license.agreed_changed.connect(lambda _:
                                                 self._update_footer())
        self.page_path.path_changed.connect(self._path_changed)

    def _build_footer(self):
        self.btn_cancel = FxButton("Отмена", kind="ghost", w_=120, h_=44,
                                   radius=12, px=14, svg_w=600, parent=self)
        self.btn_cancel.move(32, 468)
        self.btn_cancel.clicked.connect(self._on_close)

        self.btn_back = FxButton("Назад", kind="ghost", w_=140, h_=44,
                                 radius=12, px=14, svg_w=600, parent=self)
        self.btn_back.move(W - 32 - 160 - 10 - 140, 468)
        self.btn_back.clicked.connect(self._back)

        self.btn_next = FxButton("Далее", kind="sun", w_=160, h_=44,
                                 radius=12, px=14, svg_w=700,
                                 glow="#ff7a4d", parent=self)
        self.btn_next.move(W - 32 - 160, 468)
        self.btn_next.clicked.connect(self._next)

    # ------------------------------------------------------------- переходы
    def _path_changed(self, path):
        self._install_dir = path

    def _steps(self):
        return [self.page_welcome, self.page_license, self.page_path,
                self.page_shortcuts, self.page_progress, self.page_done]

    def _show_page(self, idx):
        pages = self._steps()
        idx = max(0, min(idx, len(pages) - 1))
        self._index = idx
        self.stack.setCurrentIndex(idx)
        page = pages[idx]
        page.on_enter()
        fade_in(page, ms=300)
        if idx <= 4:
            self.step_lbl.setText("Шаг %d из 5 · %s" % (idx + 1, page.title()))
        else:
            self.step_lbl.setText("Готово")
        if page is self.page_progress:
            self.page_progress.set_dest(self._install_dir)
            self.page_progress.set_error("")
            self.page_progress.status.setText("")
            self.page_progress.file_lbl.setText("Подготовка…")
            self._start_copy()
        if page is self.page_done:
            self.page_done.set_dest(self._install_dir)
        self._update_footer()

    def _update_footer(self):
        idx = self._index
        can_next = self.stack.currentWidget().can_next()
        if idx == 0:
            self.btn_next.set_text("Далее")
            self.btn_next.set_disabled(False)
            self.btn_back.set_disabled(True)
            self.btn_cancel.set_text("Отмена")
        elif idx in (1, 2, 3):
            self.btn_next.set_text("Далее" if idx < 3 else "Установить")
            self.btn_next.set_disabled(not can_next)
            self.btn_back.set_disabled(False)
        elif idx == 4:
            # прогресс: «Назад» скрыт; при ошибке — «Повторить»
            self.btn_back.set_disabled(True)
            if self._error:
                self.btn_next.set_text("Повторить")
                self.btn_next.set_disabled(False)
                self.btn_next.show()
            else:
                self.btn_next.hide()
            self.btn_cancel.set_text("Отмена")
        else:
            self.btn_next.set_text("Готово")
            self.btn_next.set_disabled(False)
            self.btn_back.set_disabled(True)
            self.btn_next.show()
        if idx != 4:
            self.btn_next.show()

    def _next(self):
        idx = self._index
        if idx == 4 and self._error:
            self._error = False
            self._update_footer()
            self.page_progress.set_error("")
            self.page_progress.status.setText("")
            self._start_copy()
            return
        self._show_page(idx + 1)

    def _back(self):
        if self._index > 0 and self._index != 4:
            self._show_page(self._index - 1)

    # ------------------------------------------------------------ копирование
    def _start_copy(self):
        if self._worker is not None and self._worker.isRunning():
            return
        self._desktop = self.page_shortcuts.desktop()
        self._startmenu = self.page_shortcuts.startmenu()
        ok, msg = _validate(self._install_dir)
        if not ok:
            self._error = True
            self.page_progress.set_error(msg)
            self._update_footer()
            return
        self._error = False
        self._worker = CopyWorker(self._install_dir, desktop=self._desktop,
                                  startmenu=self._startmenu)
        self._worker.progressed.connect(self.page_progress.set_progress)
        self._worker.succeeded.connect(self._copy_done)
        self._worker.failed.connect(self._copy_failed)
        self._worker.cancelled.connect(self.close)
        self._worker.start()

    def _copy_done(self, info):
        self._update_footer()  # убрать состояние ошибки
        self._show_page(5)

    def _copy_failed(self, message):
        self._error = True
        self.page_progress.set_error(message)
        self._update_footer()

    # ----------------------------------------------------------------- окно
    def _on_close(self):
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
        if self._index == 5 and self.page_done.run_after():
            launch_installed(_Path(self._install_dir))
        self.close()

    def closeEvent(self, event):
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
        super().closeEvent(event)

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = theme.rounded_path(r, 28)
        p.setClipPath(path)
        p.fillRect(r, theme.bg_gradient(r.width(), r.height()))
        strip = QRectF(r.left(), r.top(), r.width(), 3)
        p.fillRect(strip, theme.sunh_gradient(strip))
        # тонкая разделительная линия под шапкой (как у сайдбара лаунчера)
        pen = QPen(QColor(255, 255, 255, 16))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.drawLine(QPointF_(32, 88), QPointF_(W - 32, 88))
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


def _Path(text):
    from pathlib import Path
    return Path(text)


def _validate(text):
    from ..core.install_paths import validate_install_dir
    return validate_install_dir(text)
