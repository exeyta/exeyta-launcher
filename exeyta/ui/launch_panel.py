# -*- coding: utf-8 -*-
"""Панель «Запуск» (430x648, r22) — 1:1 с assets/launcher-ui.svg.

Заголовок + статус сессии, плашка версии (Minecraft / версия / чип «Моды»),
блок Память+слайдер / Java / Папка / Моды / «Готово к запуску»,
кнопка ИГРАТЬ 382x70 (sun-градиент, капс, letter-spacing 3, без блика).
"""
import re

from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QVBoxLayout,
                             QWidget)

from exeyta_shared import theme

from .controls import (CardPanel, FxButton, GradientSlider, PanelBox,
                       add_label, apply_glow, draw_base, w)

# keep-alive для фоновых VersionsWorker (нельзя удалять работающий QThread)
_VERSION_WORKERS = []


def elide_path(path, px, width, k):
    """Серединное сокращение длинного пути под ширину (в пикселях макета)."""
    path = str(path)
    max_len = int(width / (px * 0.55)) if px else 40
    if len(path) <= max_len:
        return path
    head = max(6, (max_len * 2) // 3)
    tail = max(4, max_len - head - 1)
    return path[:head] + "…" + path[-tail:]


class _InfoBlock(QWidget):
    """Центральный блок 382x360 (r18) с разделителями (белый 10%)."""

    def __init__(self, w_, h_, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.setFixedSize(round(w_ * k), round(h_ * k))

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#120910"))
        p.drawRoundedRect(r, 18 * k, 18 * k)
        pen = QPen(QColor("#10ffffff"))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.drawRoundedRect(r, 18 * k, 18 * k)
        # разделители y: 64 / 132 / 200 (в координатах блока)
        p.drawLine(QPointF_(20 * k, 64 * k), QPointF_(362 * k, 64 * k))
        p.drawLine(QPointF_(20 * k, 132 * k), QPointF_(362 * k, 132 * k))
        p.drawLine(QPointF_(20 * k, 200 * k), QPointF_(362 * k, 200 * k))
        p.end()


def QPointF_(x, y):
    from PyQt5.QtCore import QPointF
    return QPointF(x, y)


class _ClickZone(QWidget):
    """Прозрачная зона клика (виртуальные методы PyQt не патчатся на实例).

    Реальный подкласс: клик гарантированно доходит до Python-кода.
    """

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        event.accept()


class VersionDialog(QDialog):
    """Выбор версии Minecraft: онлайн-список релизов Mojang + установка.

    * список грузится в QThread (VersionsWorker), есть кэш и «Обновить»;
    * фильтр по номеру;
    * отметка «установлено» (клиент + нужная Java уже скачаны);
    * кнопки: «Скачать» (единый мастер MC+Java) и «Выбрать».
    """

    chosen = pyqtSignal(str)              # выбрать как текущую
    download_requested = pyqtSignal(str)  # скачать/допроверить

    def __init__(self, current, ids, types=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Версии Minecraft — Exeyta")
        self.setModal(True)
        self.setFixedSize(540, 600)
        self.current = current
        self.ids = list(ids or [])
        self.types = dict(types or {})
        self._worker = None
        self.setStyleSheet(self._qss())

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)

        title = QLabel("Версии Minecraft")
        title.setObjectName("dlgTitle")
        root.addWidget(title)
        sub = QLabel("Релизы, снапшоты и старые версии · список онлайн")
        sub.setObjectName("dlgSub")
        root.addWidget(sub)

        row = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setObjectName("dlgEdit")
        self.filter.setPlaceholderText("Фильтр, напр. 1.20 или 1.16")
        self.filter.textChanged.connect(self._populate)
        row.addWidget(self.filter, 1)
        self.btn_refresh = FxButton("Обновить", kind="chip", w_=112, h_=40,
                                    radius=12, px=13, svg_w=600)
        self.btn_refresh.clicked.connect(self._start_load)
        row.addWidget(self.btn_refresh)
        root.addLayout(row)

        self.listw = QListWidget()
        self.listw.setObjectName("acctList")
        self.listw.itemDoubleClicked.connect(lambda _it: self._pick())
        root.addWidget(self.listw, 1)

        self.status = QLabel("")
        self.status.setObjectName("dlgHint")
        root.addWidget(self.status)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        btn_close = FxButton("Закрыть", kind="ghost", w_=116, h_=42,
                             radius=12, px=13, svg_w=600)
        btn_close.clicked.connect(self.reject)
        self.btn_download = FxButton("Скачать", kind="chip", w_=160, h_=42,
                                     radius=12, px=13, svg_w=700)
        self.btn_download.clicked.connect(self._download)
        self.btn_pick = FxButton("Выбрать", kind="sun", w_=160, h_=42,
                                 radius=12, px=13, svg_w=700)
        self.btn_pick.clicked.connect(self._pick)
        btns.addWidget(btn_close)
        btns.addStretch(1)
        btns.addWidget(self.btn_download)
        btns.addWidget(self.btn_pick)
        root.addLayout(btns)

        self.listw.currentItemChanged.connect(self._selection_changed)
        self._populate()
        if not self.ids:
            self._start_load()
        else:
            self.status.setText("%d версий в списке" % len(self.ids))

    # --- данные ------------------------------------------------------------
    def _start_load(self):
        if self._worker is not None and self._worker.isRunning():
            return
        from ..workers.download_worker import VersionsWorker
        self.btn_refresh.set_disabled(True)
        self.status.setStyleSheet("color: #b9a3b4;")
        self.status.setText("Загрузка списка версий…")
        worker = VersionsWorker()
        worker.loaded.connect(self._on_ids)
        worker.failed.connect(self._on_fail)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(
            lambda: self.btn_refresh.set_disabled(False))

        def _release(w=worker):
            if w in _VERSION_WORKERS:
                _VERSION_WORKERS.remove(w)

        worker.finished.connect(_release)
        _VERSION_WORKERS.append(worker)   # живёт до завершения потока
        self._worker = worker
        worker.start()

    def _on_ids(self, ids):
        if ids:
            # список приходит как [{"id","type"}] или как [id, ...]
            self.ids, self.types = [], {}
            for it in ids:
                if isinstance(it, dict):
                    vid, typ = str(it.get("id", "")), it.get("type", "release")
                else:
                    vid, typ = str(it), None
                if not vid:
                    continue
                self.ids.append(vid)
                if typ:
                    self.types[vid] = typ
            self.status.setStyleSheet("color: #86efac;")
            self.status.setText("%d версий загружено" % len(self.ids))
            self._populate()
        else:
            self._on_fail("Пустой список версий")

    def _on_fail(self, message):
        self.status.setStyleSheet("color: #ff4d6d;")
        if self.ids:
            self.status.setText("%s (показан кэш: %d версий)"
                                % (message, len(self.ids)))
        else:
            self.status.setText("%s — нет списка и кэша" % message)

    def _installed(self, vid):
        from ..core.java_resolver import major_for
        from ..core.minecraft_installer import is_client_installed
        from ..core.portable_java import is_installed
        try:
            return (is_client_installed(vid)
                    and is_installed(major_for(vid)))
        except Exception:
            return False

    def _populate(self, *_a):
        text = (self.filter.text() if hasattr(self, "filter") else "")
        text = (text or "").strip().lower()
        self.listw.clear()
        current_row = -1
        for vid in self.ids:
            if text and text not in vid.lower():
                continue
            inst = self._installed(vid)
            typ = self.types.get(vid, "release")
            suffix = {"snapshot": "· снапшот",
                      "old_beta": "· old beta",
                      "old_alpha": "· old alpha"}.get(typ, "")
            mark = "✓ установлено" if inst else suffix
            label = ("%s    %s" % (vid, mark)).rstrip()
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, vid)
            if inst:
                it.setForeground(QBrush(QColor("#86efac")))
            elif suffix:
                it.setForeground(QBrush(QColor("#c9a8b8")))
            self.listw.addItem(it)
            if vid == self.current:
                current_row = self.listw.count() - 1
        if current_row >= 0:
            self.listw.setCurrentRow(current_row)
        elif self.listw.count():
            self.listw.setCurrentRow(0)
        self._selection_changed()

    def _selected(self):
        it = self.listw.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _selection_changed(self, *_a):
        has = self._selected() is not None
        self.btn_pick.set_disabled(not has)
        self.btn_download.set_disabled(not has)

    # --- действия ----------------------------------------------------------
    def _pick(self):
        vid = self._selected()
        if not vid:
            return
        self.current = vid
        self.close()
        self.chosen.emit(vid)

    def _download(self):
        vid = self._selected()
        if not vid:
            return
        self.close()
        self.download_requested.emit(vid)

    # --- окно --------------------------------------------------------------
    def _qss(self):
        return """
            QDialog { background: #1a0c16; }
            QLabel#dlgTitle { color: #fff8f2; font-size: 20px; font-weight: 700; }
            QLabel#dlgSub { color: #b9a3b4; font-size: 12px; }
            QLabel#dlgHint { font-size: 12px; min-height: 16px; color: #86efac; }
            QLineEdit#dlgEdit {
                background: #1c1024; border: 1px solid rgba(255,255,255,0.13);
                border-radius: 10px; padding: 9px 12px; color: #fff8f2;
                font-size: 14px; selection-background-color: #ffb703;
                selection-color: #1a0a10;
            }
            QLineEdit#dlgEdit:focus { border: 1px solid #ffb703; }
            QListWidget#acctList {
                background: #120910; border: 1px solid rgba(255,255,255,0.09);
                border-radius: 12px; padding: 6px; color: #fff8f2;
                font-size: 14px; outline: none;
            }
            QListWidget#acctList::item { padding: 9px 12px; border-radius: 8px; }
            QListWidget#acctList::item:hover { background: rgba(255,255,255,0.06); }
            QListWidget#acctList::item:selected {
                background: rgba(255,183,3,0.09); color: #ffe7b0;
                border: 1px solid #ffb703;
            }
            QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
            QScrollBar::handle:vertical {
                background: #3a2148; border-radius: 4px; min-height: 24px;
            }
            QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
        """


class LaunchPanel(CardPanel):
    """Карточка «Запуск»."""

    play_clicked = pyqtSignal()
    version_chosen = pyqtSignal(str)
    download_version = pyqtSignal(str)   # запросить установку выбранной версии

    MEM_MIN, MEM_MAX, MEM_STEP = 4096, 8192, 512

    def __init__(self, cfg, k=1.0, parent=None):
        super().__init__(round(430 * k), round(648 * k), radius=22,
                         border="#18ffffff", parent=parent)
        self.k = float(k)
        self.cfg = cfg
        self._build()

    def _build(self):
        k = self.k

        # --- заголовок ----------------------------------------------------
        self.lbl_title = add_label(self, k, 24, 38, 22, 700, 300, "Запуск")
        self.lbl_status = add_label(self, k, 24, 60, 12, 500, 300,
                                    "сессия готова", color="#86efac")

        # --- плашка версии 382x78 (24,80) ---------------------------------
        self.plate = PanelBox(round(382 * k), round(78 * k), radius=16,
                              fill="#120910", border="#14ffffff", parent=self)
        self.plate.move(round(24 * k), round(80 * k))
        add_label(self.plate, k, 20, 28, 12, 500, 200, "Minecraft",
                  color="#b9a3b4")
        self.lbl_version = add_label(self.plate, k, 20, 56, 22, 700, 210,
                                     self.cfg.last_version)
        # зона клика по версии
        self._ver_hit = _ClickZone(self.plate)
        self._ver_hit.setGeometry(round(14 * k), round(30 * k),
                                  round(230 * k), round(44 * k))
        self._ver_hit.clicked.connect(self._open_versions)
        self._ver_hit.setToolTip("Выбрать или скачать версию Minecraft")

        # вместо чипа «Моды» — выбор версии (110x30, 248,28)
        self.btn_version = FxButton("Версия ▾", kind="chip",
                                    w_=round(110 * k), h_=round(30 * k),
                                    radius=10, px=13, svg_w=700,
                                    tooltip="Выбрать или скачать версию",
                                    parent=self.plate)
        self.btn_version.move(round(248 * k), round(28 * k))
        self.btn_version.clicked.connect(self._open_versions)

        # --- блок 382x360 (24,174) ----------------------------------------
        self.block = _InfoBlock(382, 360, k=k, parent=self)
        self.block.move(round(24 * k), round(174 * k))

        add_label(self.block, k, 20, 28, 12, 500, 200, "Память",
                  color="#b9a3b4")
        self.lbl_mem = add_label(self.block, k, 162, 28, 14, 600, 200, "6 GB",
                                 align=Qt.AlignRight | Qt.AlignVCenter)
        self.slider = GradientSlider(self.MEM_MIN, self.MEM_MAX, self.MEM_STEP,
                                     self.cfg.memory_mb, 342, k=k,
                                     parent=self.block)
        self.slider.move(round(20 * k), round(36 * k))
        self.slider.valueChanged.connect(self._on_memory)

        add_label(self.block, k, 20, 96, 12, 500, 200, "Java", color="#b9a3b4")
        self.lbl_java = add_label(self.block, k, 162, 96, 14, 600, 200,
                                  "21 Temurin",
                                  align=Qt.AlignRight | Qt.AlignVCenter)

        add_label(self.block, k, 20, 164, 12, 500, 200, "Папка",
                  color="#b9a3b4")
        self.lbl_folder = add_label(self.block, k, 120, 164, 14, 600, 242,
                                    "", align=Qt.AlignRight | Qt.AlignVCenter)

        add_label(self.block, k, 20, 232, 12, 500, 200, "Моды",
                  color="#b9a3b4")
        self.lbl_mods = add_label(self.block, k, 162, 232, 14, 600, 200,
                                  "Из коробки",
                                  align=Qt.AlignRight | Qt.AlignVCenter)

        self.lbl_ready = add_label(self.block, k, 20, 318, 13, 500, 300,
                                   "Готово к запуску", color="#86efac")

        # --- ИГРАТЬ 382x70 (24,554) ---------------------------------------
        self.btn_play = FxButton("ИГРАТЬ", kind="sun",
                                 w_=round(382 * k), h_=round(70 * k),
                                 radius=18, px=22, svg_w=800, letter=3.0 * k,
                                 glow="#ff7a4d", parent=self)
        self.btn_play.move(round(24 * k), round(554 * k))
        self.btn_play.clicked.connect(self.play_clicked.emit)

    # --- версии ------------------------------------------------------------
    def _open_versions(self):
        """Диалог выбора/скачивания версии (все версии + снапшоты, онлайн)."""
        ids = list(getattr(self, "_version_ids", None) or [])
        types = dict(getattr(self, "_version_types", None) or {})
        dlg = VersionDialog(self.cfg.last_version, ids, types=types,
                            parent=self.window())
        dlg.chosen.connect(self.version_chosen.emit)
        dlg.download_requested.connect(self.download_version.emit)
        dlg.exec_()

    def set_version_ids(self, ids):
        """Принимает список id или [{"id","type"}] (включая снапшоты)."""
        out, types = [], {}
        for it in ids or []:
            if isinstance(it, dict):
                vid = str(it.get("id", ""))
                typ = it.get("type", "release")
            else:
                vid = str(it)
                typ = ("release" if re.match(r"^\d+\.\d+", vid)
                       else "snapshot")
            if not vid:
                continue
            out.append(vid)
            types[vid] = typ
        self._version_ids = out
        self._version_types = types

    # --- обновления --------------------------------------------------------
    def set_version(self, vid):
        self.lbl_version.setText(str(vid))

    def set_status(self, text, color="#86efac"):
        self.lbl_status.setText(text)
        pal = self.lbl_status.palette()
        pal.setColor(self.lbl_status.foregroundRole(), QColor(color))
        self.lbl_status.setPalette(pal)

    def set_ready(self, flag, text=None):
        self.lbl_ready.setText(text if text is not None else
                               ("Готово к запуску" if flag
                                else "Требуется установка"))
        pal = self.lbl_ready.palette()
        pal.setColor(self.lbl_ready.foregroundRole(),
                     QColor("#86efac" if flag else "#ffb703"))
        self.lbl_ready.setPalette(pal)

    def set_busy(self, flag):
        self.btn_play.set_disabled(bool(flag))
        self.btn_play.set_text("ЗАПУСК..." if flag else "ИГРАТЬ")

    def set_java(self, text):
        self.lbl_java.setText(text)

    def set_folder(self, path):
        self.lbl_folder.setText(elide_path(path, 14, 242, self.k))
        self.lbl_folder.setToolTip(str(path))

    def set_mods(self, text):
        self.lbl_mods.setText(text)

    def set_memory_mb(self, mb):
        if mb != self.slider.value():
            self.slider.set_value(mb, emit=False)
        self._mem_label(mb)

    def _mem_label(self, mb):
        if mb % 1024 == 0:
            txt = "%d GB" % (mb // 1024)
        else:
            txt = "%d MB" % mb
        self.lbl_mem.setText(txt)

    def _on_memory(self, mb):
        self._mem_label(mb)
        self.cfg.memory_mb = mb
        self.memory_changed.emit(mb)

    memory_changed = pyqtSignal(int)
