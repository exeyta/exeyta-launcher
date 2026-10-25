# -*- coding: utf-8 -*-
"""Мастер «Установка Minecraft и Java» — единый для клиента и portable Java.

QThread (workers.download_worker.InstallWorker), прогресс «Клиент» / «Java»,
отмена и повтор. UI не блокируется.
"""
from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QProgressBar,
                             QVBoxLayout, QWidget)

from exeyta_shared import theme

from .controls import FxButton, PanelBox, add_label, apply_glow, rounded_path


class _Stage(QWidget):
    """Строка прогресса: подпись + полоса + процент + статус."""

    def __init__(self, title, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.setFixedHeight(round(74 * k))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(round(6 * k))
        top = QHBoxLayout()
        self.title = QLabel(title)
        self.title.setObjectName("wzStageTitle")
        self.pct = QLabel("0%")
        self.pct.setObjectName("wzPct")
        top.addWidget(self.title)
        top.addStretch(1)
        top.addWidget(self.pct)
        lay.addLayout(top)
        self.bar = QProgressBar()
        self.bar.setObjectName("wzBar")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(round(10 * k))
        lay.addWidget(self.bar)
        self.msg = QLabel("Ожидание…")
        self.msg.setObjectName("wzMsg")
        lay.addWidget(self.msg)

    def set_progress(self, done, total, message):
        pct = 0 if total <= 0 else int(done * 100 / total)
        pct = max(0, min(100, pct))          # защита от «102%»
        self.bar.setValue(pct)
        self.pct.setText("%d%%" % pct)
        self.msg.setText(message)

    def set_message(self, message, color=None):
        self.msg.setText(message)
        if color:
            self.msg.setStyleSheet("color: %s;" % color)


class InstallWizard(QDialog):
    """Окно установки: одна волна — клиент Minecraft + portable Java."""

    finished_ok = pyqtSignal()

    def __init__(self, version_id, game_dir=None, parent=None):
        super().__init__(parent)
        self.version_id = version_id
        self.game_dir = game_dir
        self._worker = None
        self._done = False

        self.setWindowTitle("Установка Minecraft и Java — Exeyta")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(round(640), round(430))

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 26, 32, 24)
        root.setSpacing(12)

        title = QLabel("Установка Minecraft и Java")
        title.setObjectName("wzTitle")
        root.addWidget(title)

        row = QHBoxLayout()
        from ..core.java_resolver import major_for
        ver = QLabel("Minecraft %s  ·  Java %d Temurin"
                     % (version_id, major_for(version_id)))
        ver.setObjectName("wzVersion")
        row.addWidget(ver)
        row.addStretch(1)
        root.addLayout(row)

        self.stage_client = _Stage("Клиент", parent=self)
        self.stage_java = _Stage("Java (portable)", parent=self)
        root.addWidget(self.stage_client)
        root.addWidget(self.stage_java)

        self.error = QLabel("")
        self.error.setObjectName("wzError")
        self.error.setWordWrap(True)
        root.addWidget(self.error)
        root.addStretch(1)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.btn_cancel = FxButton("Отмена", kind="ghost", w_=140, h_=42,
                                   radius=12, px=14, svg_w=600)
        self.btn_retry = FxButton("Повторить", kind="chip", w_=160, h_=42,
                                  radius=12, px=14, svg_w=700)
        self.btn_close = FxButton("Готово", kind="sun", w_=160, h_=42,
                                  radius=12, px=14, svg_w=700)
        self.btn_retry.hide()
        self.btn_close.hide()
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_retry.clicked.connect(self._start)
        self.btn_close.clicked.connect(self._close_ok)
        btns.addWidget(self.btn_cancel)
        btns.addStretch(1)
        btns.addWidget(self.btn_retry)
        btns.addWidget(self.btn_close)
        root.addLayout(btns)

        self._start()

    # --- worker ------------------------------------------------------------
    def _start(self):
        self.btn_retry.hide()
        self.error.setText("")
        self.btn_cancel.show()
        self.stage_client.set_message("Подготовка…")
        self.stage_java.set_message("Ожидание…")
        from ..workers.download_worker import InstallWorker
        self._worker = InstallWorker(self.version_id, game_dir=self.game_dir)
        self._worker.progressed.connect(self._on_progress)
        self._worker.stage_changed.connect(self._on_stage)
        self._worker.succeeded.connect(self._on_ok)
        self._worker.failed.connect(self._on_fail)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.start()

    def _cancel(self):
        if self._worker is not None:
            self._worker.cancel()
            self.btn_cancel.setEnabled(False)
            self.stage_client.set_message("Отмена…", "#ffb703")

    def _on_stage(self, stage):
        if stage == "java":
            self.stage_client.set_progress(100, 100, "Клиент готов")
            self.stage_java.set_message("Скачивание Java…")

    def _on_progress(self, stage, done, total, message):
        if stage == "client":
            self.stage_client.set_progress(done, total, message)
        else:
            self.stage_java.set_progress(done, total, message)

    def _on_ok(self):
        self._done = True
        self.stage_client.set_progress(100, 100, "Готово")
        self.stage_java.set_progress(100, 100, "Готово")
        self.btn_cancel.hide()
        self.btn_close.show()
        self.finished_ok.emit()

    def _on_fail(self, stage, message):
        self.btn_cancel.hide()
        self.btn_retry.show()
        name = "Клиент" if stage == "client" else "Java"
        self.error.setText("%s: %s" % (name, message))
        (self.stage_client if stage == "client" else self.stage_java) \
            .set_message("Ошибка — нажмите «Повторить»", "#ff4d6d")

    def _on_cancelled(self):
        self.close()

    def _close_ok(self):
        self.close()

    # --- окно --------------------------------------------------------------
    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = rounded_path(r, 22)
        # фон: та же карточная тема, что у лаунчера
        p.fillPath(path, theme.card_gradient(r))
        # верхняя полоска 3px sunH, обрезанная по скруглению
        p.save()
        p.setClipPath(path)
        strip = QRectF(r.left(), r.top(), r.width(), 3)
        g = QLinearGradient(strip.left(), strip.top(),
                            strip.right(), strip.top())
        g.setColorAt(0.0, QColor("#ffb703"))
        g.setColorAt(1.0, QColor("#ff4d6d"))
        p.fillRect(strip, g)
        p.restore()
        pen = QPen(QColor("#18ffffff"))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 22, 22)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, "_drag") and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag)
            event.accept()
