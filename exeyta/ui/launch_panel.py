# -*- coding: utf-8 -*-
"""Раздел «Версии»: текущая версия, каталог версий и установка.

Список версий приходит из VersionsWorker (QThread) в MainWindow и
передаётся в set_version_ids(). Установка запускается мастером
Minecraft + Java (сигнал download_version).
"""
import re
from pathlib import Path

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QVBoxLayout,
                             QWidget)

from exeyta_shared import theme
from exeyta_shared.animations import finish_fade

from .controls import (Badge, CardPanel, ClickZone, FxButton, add_label,
                       w)

# keep-alive для фоновых VersionsWorker (нельзя удалять работающий QThread)
_VERSION_WORKERS = []


def elide_path(path, px, width, k):
    """Серединное сокращение длинного пути под ширину (в пикселях)."""
    path = str(path)
    max_len = int(width / (px * 0.55)) if px else 40
    if len(path) <= max_len:
        return path
    head = max(6, (max_len * 2) // 3)
    tail = max(4, max_len - head - 1)
    return path[:head] + "…" + path[-tail:]


class _ClickZone(ClickZone):
    """Совместимость со старым именем."""


class VersionDialog(QDialog):
    """Выбор версии Minecraft: онлайн-список релизов Mojang + установка."""

    chosen = pyqtSignal(str)
    download_requested = pyqtSignal(str)

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
                                    radius=9, px=13, svg_w=600)
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
                             radius=9, px=13, svg_w=600)
        btn_close.clicked.connect(self.reject)
        self.btn_download = FxButton("Скачать", kind="chip", w_=160, h_=42,
                                     radius=9, px=13, svg_w=700)
        self.btn_download.clicked.connect(self._download)
        self.btn_pick = FxButton("Выбрать", kind="sun", w_=160, h_=42,
                                 radius=9, px=13, svg_w=700)
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

    # --- данные ----------------------------------------------------------
    def _start_load(self):
        if self._worker is not None and self._worker.isRunning():
            return
        from ..workers.download_worker import VersionsWorker
        self.btn_refresh.set_disabled(True)
        self.status.setStyleSheet("color: #8b8f98;")
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
        _VERSION_WORKERS.append(worker)
        self._worker = worker
        worker.start()

    def _on_ids(self, ids):
        if ids:
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
            self.status.setStyleSheet("color: #7fbf8f;")
            self.status.setText("%d версий загружено" % len(self.ids))
            self._populate()
        else:
            self._on_fail("Пустой список версий")

    def _on_fail(self, message):
        self.status.setStyleSheet("color: #d97a7a;")
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
                it.setForeground(QBrush(QColor("#7fbf8f")))
            elif suffix:
                it.setForeground(QBrush(QColor("#8b8f98")))
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

    # --- действия --------------------------------------------------------
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

    # --- окно ------------------------------------------------------------
    def _qss(self):
        return """
            QDialog { background: #17181d; }
            QLabel#dlgTitle { color: #eceef2; font-size: 20px; font-weight: 700; }
            QLabel#dlgSub { color: #8b8f98; font-size: 12px; }
            QLabel#dlgHint { font-size: 12px; min-height: 16px; color: #7fbf8f; }
            QLineEdit#dlgEdit {
                background: #1c1d22; border: 1px solid #2a2b31;
                border-radius: 9px; padding: 9px 12px; color: #eceef2;
                font-size: 14px; selection-background-color: #c9a45c;
                selection-color: #1c1609;
            }
            QLineEdit#dlgEdit:focus { border: 1px solid #c9a45c; }
            QListWidget#acctList {
                background: #141519; border: 1px solid #2a2b31;
                border-radius: 10px; padding: 6px; color: #eceef2;
                font-size: 14px; outline: none;
            }
            QListWidget#acctList::item { padding: 9px 12px; border-radius: 7px; }
            QListWidget#acctList::item:hover { background: rgba(255,255,255,0.05); }
            QListWidget#acctList::item:selected {
                background: rgba(201,164,92,0.14); color: #e8cf9a;
                border: 1px solid rgba(201,164,92,0.55);
            }
            QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
            QScrollBar::handle:vertical {
                background: #34353c; border-radius: 4px; min-height: 24px;
            }
            QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
        """


class LaunchPanel(QWidget):
    """Страница «Версии» (1144x640)."""

    play_clicked = pyqtSignal()
    version_chosen = pyqtSignal(str)
    download_version = pyqtSignal(str)
    memory_changed = pyqtSignal(int)

    MEM_MIN, MEM_MAX, MEM_STEP = 4096, 8192, 512

    def __init__(self, cfg, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.cfg = cfg
        self._version_ids = []
        self._version_types = {}
        self._installed_cache = set()
        self._current = self.cfg.last_version
        self.setFixedSize(round(1144 * k), round(640 * k))
        self._build()

    def _build(self):
        k = self.k

        # ------------------------------------------------- текущая версия
        self.card_cur = CardPanel(round(1144 * k), round(158 * k),
                                  radius=14, border="#26272d", parent=self)
        add_label(self.card_cur, k, 26, 34, 11, 700, 300,
                  "ТЕКУЩАЯ ВЕРСИЯ", color="#8b8f98")
        self.lbl_version = add_label(self.card_cur, k, 26, 82, 32, 800, 400,
                                     self.cfg.last_version)
        self.badge = Badge("готова", k=k, color="#7fbf8f",
                           parent=self.card_cur)
        self.badge.move(round(26 * k), round(98 * k))
        self.lbl_ready = add_label(self.card_cur, k, 110, 114, 12, 500, 520,
                                   "Установлена и готова к запуску",
                                   color="#8b8f98")
        self.lbl_meta = add_label(self.card_cur, k, 26, 138, 11.5, 500, 700,
                                  "", color="#62666e")

        ico_play = theme.icon_pixmap(theme.ICON_PLAY, round(13 * k),
                                     "#1c1609", stroke=1.8, fill="#1c1609")
        self.btn_play = FxButton("Играть", kind="sun",
                                 w_=round(146 * k), h_=round(42 * k),
                                 radius=9, px=14, svg_w=700,
                                 icon=ico_play, gap=8, parent=self.card_cur)
        self.btn_play.move(round(972 * k), round(50 * k))
        self.btn_play.clicked.connect(self.play_clicked.emit)
        ico_ref = theme.icon_pixmap(theme.ICON_REFRESH, round(14 * k),
                                    "#c7cad1", stroke=1.7)
        self.btn_dl_current = FxButton("Обновить", kind="ghost",
                                       w_=round(146 * k), h_=round(42 * k),
                                       radius=9, px=13, svg_w=600,
                                       icon=ico_ref, gap=8,
                                       parent=self.card_cur)
        self.btn_dl_current.move(round(972 * k), round(100 * k))
        self.btn_dl_current.clicked.connect(self._download_current)

        # ------------------------------------------------------ каталог
        self.card_list = CardPanel(round(1144 * k), round(462 * k),
                                   radius=14, border="#26272d", parent=self)
        self.card_list.move(0, round(178 * k))
        add_label(self.card_list, k, 24, 34, 11, 700, 300,
                  "КАТАЛОГ ВЕРСИЙ", color="#8b8f98")
        self.lbl_count = add_label(
            self.card_list, k, 24, 34, 11, 500, 1096, "",
            color="#62666e", align=Qt.AlignRight | Qt.AlignVCenter)

        self.filter = QLineEdit(self.card_list)
        self.filter.setObjectName("versionFilter")
        self.filter.setPlaceholderText("Поиск версии, например 1.21 или 1.7.10")
        self.filter.setGeometry(round(24 * k), round(50 * k),
                                round(700 * k), round(38 * k))
        self.filter.textChanged.connect(self._populate)
        self.btn_refresh = FxButton("Обновить список", kind="ghost",
                                    w_=round(170 * k), h_=round(38 * k),
                                    radius=9, px=13, svg_w=600,
                                    parent=self.card_list)
        self.btn_refresh.move(round(740 * k), round(50 * k))
        self.btn_refresh.clicked.connect(self._request_versions)

        self.listw = QListWidget(self.card_list)
        self.listw.setObjectName("versionsList")
        self.listw.setGeometry(round(24 * k), round(100 * k),
                               round(1096 * k), round(250 * k))
        self.listw.currentItemChanged.connect(self._selection_changed)
        self.listw.itemDoubleClicked.connect(lambda _it: self._choose())

        self.lbl_status = add_label(self.card_list, k, 24, 378, 11.5, 500,
                                    500, "Список версий загружается…",
                                    color="#62666e")
        ico_chev = theme.icon_pixmap(theme.ICON_CHEVRON, round(13 * k),
                                     "#1c1609", stroke=1.8)
        self.btn_choose = FxButton("Выбрать", kind="sun",
                                   w_=round(140 * k), h_=round(40 * k),
                                   radius=9, px=13, svg_w=700,
                                   parent=self.card_list)
        self.btn_choose.move(round(690 * k), round(364 * k))
        self.btn_choose.clicked.connect(self._choose)
        self.btn_download = FxButton("Скачать", kind="ghost",
                                     w_=round(140 * k), h_=round(40 * k),
                                     radius=9, px=13, svg_w=600,
                                     parent=self.card_list)
        self.btn_download.move(round(846 * k), round(364 * k))
        self.btn_download.clicked.connect(self._download_selected)
        self._selection_changed()

    # --- данные ----------------------------------------------------------
    def _request_versions(self):
        self.lbl_status.setText("Загрузка списка версий…")
        from ..workers.download_worker import VersionsWorker
        worker = VersionsWorker(self)
        worker.loaded.connect(self.set_version_ids)
        worker.failed.connect(
            lambda msg: self.lbl_status.setText(
                "Не удалось загрузить список: %s" % str(msg)[:70]))
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

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
        self._installed_cache = self._scan_installed()
        self._populate()

    def _scan_installed(self):
        try:
            base = Path(self.cfg.game_dir) / "versions"
            if base.is_dir():
                return {p.name for p in base.iterdir() if p.is_dir()}
        except Exception:
            pass
        return set()

    def _populate(self, *_a):
        text = (self.filter.text() or "").strip().lower()
        self.listw.blockSignals(True)
        self.listw.clear()
        current_row = -1
        for vid in self._version_ids:
            if text and text not in vid.lower():
                continue
            typ = self._version_types.get(vid, "release")
            inst = vid in self._installed_cache
            suffix = {"snapshot": "· снапшот",
                      "old_beta": "· old beta",
                      "old_alpha": "· old alpha"}.get(typ, "")
            mark = "✓ установлено" if inst else suffix
            label = ("%s    %s" % (vid, mark)).rstrip()
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, vid)
            if vid == self._current:
                it.setForeground(QBrush(QColor("#e8cf9a")))
            elif inst:
                it.setForeground(QBrush(QColor("#7fbf8f")))
            elif suffix:
                it.setForeground(QBrush(QColor("#8b8f98")))
            self.listw.addItem(it)
            if vid == self._current:
                current_row = self.listw.count() - 1
        if current_row >= 0:
            self.listw.setCurrentRow(current_row)
        elif self.listw.count():
            self.listw.setCurrentRow(0)
        self.listw.blockSignals(False)
        self.lbl_count.setText("%d версий" % len(self._version_ids))
        if not self._version_ids:
            self.lbl_status.setText("Список версий загружается…")
        else:
            self.lbl_status.setText(
                "Установлено: %d · выберите версию и нажмите «Выбрать»"
                % len(self._installed_cache))
        self._selection_changed()

    def _selected(self):
        it = self.listw.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _selection_changed(self, *_a):
        has = self._selected() is not None
        self.btn_choose.set_disabled(not has)
        self.btn_download.set_disabled(not has)

    def _choose(self):
        vid = self._selected()
        if vid:
            self.version_chosen.emit(vid)

    def _download_selected(self):
        vid = self._selected()
        if vid:
            self.download_version.emit(vid)

    def _download_current(self):
        self.download_version.emit(self.cfg.last_version)

    # --- совместимость ----------------------------------------------------
    def _open_versions(self):
        """Старый вызов из MainWindow: открыть диалог выбора версии."""
        ids = list(self._version_ids or [])
        types = dict(self._version_types or {})
        dlg = VersionDialog(self.cfg.last_version, ids, types=types,
                            parent=self.window())
        dlg.chosen.connect(self.version_chosen.emit)
        dlg.download_requested.connect(self.download_version.emit)
        dlg.exec_()

    def set_version(self, vid):
        self._current = str(vid)
        self.lbl_version.setText(str(vid))
        px = 32 if len(str(vid)) <= 10 else 24
        self.lbl_version.setFont(theme.font(px * self.k, 800))
        self._populate()

    def set_status(self, text, color="#7fbf8f"):
        pass

    def set_ready(self, flag, text=None):
        self.badge.set_text("готова" if flag else "не готова")
        self.badge.set_color("#7fbf8f" if flag else "#c9a45c")
        self.lbl_ready.setText(
            text if text is not None else
            ("Установлена и готова к запуску" if flag
             else "Требуется установка клиента или Java"))

    def set_busy(self, flag):
        self.btn_play.set_disabled(bool(flag))
        self.btn_play.set_text("Запуск…" if flag else "Играть")

    def set_java(self, text):
        self.lbl_meta.setText("Java: %s" % text)

    def set_folder(self, path):
        self._installed_cache = self._scan_installed()
        self._populate()

    def set_mods(self, text):
        pass

    def set_memory_mb(self, mb):
        self.cfg.memory_mb = int(mb)

    def _mem_label(self, mb):
        pass

    def _on_memory(self, mb):
        self.memory_changed.emit(mb)
