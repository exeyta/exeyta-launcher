# -*- coding: utf-8 -*-
"""Главное окно лаунчера Exeyta.

Сетка 1:1 с assets/launcher-ui.svg (viewBox 28 22 1864 1036):
  окно 1864x1036 (или масштаб с сохранением пропорций), rx=28,
  верхняя полоска 3px sunH, сайдбар 280, «Запуск» 430x648 (300,26),
  «Редактор скина» 1090x648 (746,26), «Настройки» 1536x320 (300,690).

Один раздел за раз (вкладки в сайдбаре): Главная → приветствие/сводка/ИГРАТЬ,
«Играть» → панель «Запуск», «Скины» → редактор, «Настройки» → настройки.
Каждый раздел раскрывается с анимацией (fade + slide, OutCubic); при старте
открыта «Главная». Мастер установки и диалоги — модальные окна.
"""
from PyQt5.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QWidget

from exeyta_shared import theme
from exeyta_shared.animations import HoverFader

from ..core import config as cfgmod
from ..core.accounts import AccountStore
from ..core.java_resolver import describe, java_exe, major_for
from ..core.minecraft_installer import is_client_installed
from ..core.portable_java import is_installed
from .controls import add_label, rounded_path
from .home_panel import HomePanel
from .launch_panel import LaunchPanel
from .settings_panel import SettingsPanel
from .sidebar import AccountsDialog, Sidebar

# keep-alive для потоков, переживающих закрытие окна (игра и т.п.)
_BACKGROUND_THREADS = []


class _GlyphBtn(QWidget):
    """Минимальные кнопки окна (– / ✕) в свободной полосе над карточками."""

    clicked = pyqtSignal()

    def __init__(self, kind, k=1.0, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.k = float(k)
        self.setFixedSize(round(24 * k), round(18 * k))
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
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        event.accept()

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = self._hover.hoverT
        base = "#8d7084"
        if self.kind == "close":
            color = QColor(base)
            if t > 0:
                color = QColor(round(141 + (255 - 141) * 0), 0, 0)
                color = QColor("#ff4d6d") if t > 0.4 else QColor(base)
            pen = QPen(color)
        else:
            pen = QPen(QColor(base) if t < 0.4 else QColor("#fff8f2"))
        pen.setWidthF(max(1.4, 1.6 * self.k))
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        s = 5 * self.k
        if self.kind == "min":
            p.drawLine(QPointF_(cx - s, cy), QPointF_(cx + s, cy))
        else:
            p.drawLine(QPointF_(cx - s, cy - s), QPointF_(cx + s, cy + s))
            p.drawLine(QPointF_(cx + s, cy - s), QPointF_(cx - s, cy + s))
        p.end()


def QPointF_(x, y):
    from PyQt5.QtCore import QPointF
    return QPointF(x, y)


class MainWindow(QWidget):
    """Единственное окно лаунчера: вкладки-разделы с анимацией."""

    def __init__(self, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(round(cfgmod.BASE_W * k), round(cfgmod.BASE_H * k))
        self.setWindowTitle("Exeyta Launcher")

        self.cfg = cfgmod.get_config()
        self.cfg.save()          # config.json рядом с exe создаётся сразу
        self.accounts = AccountStore()
        self.busy = False
        self._game = None
        self._wizard = None
        self._install_ok = False
        self._pending_play = False
        self._drag_pos = None
        self.skin_editor = None

        self._build()
        self.sidebar.set_account(self.accounts.current())
        self.sidebar.set_active("home")   # стартовый раздел — «Главная»

        # ленивая инициализация редактора скина (после первого кадра)
        QTimer.singleShot(0, self._build_skin_editor)
        # состояние готовности + фоновые задачи
        QTimer.singleShot(10, self._refresh_state)
        QTimer.singleShot(60, self._load_versions)
        QTimer.singleShot(900, self._autostart)

    # ------------------------------------------------------------------ UI
    def _center(self, w_, h_):
        """Центрирует раздел в рабочей области (правее сайдбара 280)."""
        k = self.k
        x = round(280 * k + ((1864 - 280) * k - w_) / 2)
        y = round((1036 * k - h_) / 2)
        return x, y

    def _section(self, key):
        return {
            "home": getattr(self, "home", None),
            "play": getattr(self, "launch", None),
            "skins": getattr(self, "skin_editor", None),
            "settings": getattr(self, "settings", None),
        }.get(key)

    def _build(self):
        k = self.k

        self.sidebar = Sidebar(k=k, parent=self)
        self.sidebar.move(0, 0)
        self.sidebar.nav_clicked.connect(self._nav)
        self.sidebar.gear_clicked.connect(self._accounts)

        # «Главная» — стартовый раздел
        self.home = HomePanel(self.cfg, k=k, parent=self)
        self.home.move(*self._center(round(760 * k), round(560 * k)))
        self.home.play_clicked.connect(self._play)
        self.home.version_clicked.connect(self._open_versions)
        self._active_tab = "home"

        self.launch = LaunchPanel(self.cfg, k=k, parent=self)
        self.launch.move(*self._center(round(430 * k), round(648 * k)))
        self.launch.play_clicked.connect(self._play)
        self.launch.version_chosen.connect(self._version_chosen)
        self.launch.download_version.connect(self._open_install)
        self.launch.memory_changed.connect(
            lambda mb: self.settings.set_memory_mb(mb))
        self.launch.hide()   # до выбора вкладки показана «Главная»

        self.settings = SettingsPanel(self.cfg, k=k, parent=self)
        self.settings.move(*self._center(round(1536 * k), round(320 * k)))
        self.settings.memory_changed.connect(
            lambda mb: self.launch.set_memory_mb(mb))
        self.settings.folder_chosen.connect(self._folder_chosen)
        self.settings.hide()

        # кнопки окна (в свободной полосе y=5..23)
        self.btn_min = _GlyphBtn("min", k=k, parent=self)
        self.btn_min.move(round(1784 * k), round(5 * k))
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_close = _GlyphBtn("close", k=k, parent=self)
        self.btn_close.move(round(1812 * k), round(5 * k))
        self.btn_close.clicked.connect(self.close)

    def _build_skin_editor(self):
        """Lazy init: редактор скина строится после первого кадра (скрытым)."""
        if self.skin_editor is not None:
            return
        from .skin_editor import SkinEditorPanel
        self.skin_editor = SkinEditorPanel(self.cfg, self.accounts,
                                           k=self.k, parent=self)
        self.skin_editor.move(*self._center(round(1090 * self.k),
                                            round(648 * self.k)))
        self.skin_editor.hide()   # покажет _nav при выборе вкладки «Скины»
        self.skin_editor.load_account_skin()

    # ------------------------------------------------------------ навигация
    def _nav(self, key):
        """Переключает раздел с анимацией раскрытия (fade + slide, OutCubic)."""
        from exeyta_shared.animations import fade_in, slide_up
        self.sidebar.set_active(key)
        if key == "skins" and self.skin_editor is None:
            self._build_skin_editor()
        if key == self._active_tab:
            return
        prev = self._section(self._active_tab)
        target = self._section(key)
        if target is None:
            return
        if prev is not None and prev is not target:
            prev.hide()
        self._active_tab = key
        target.show()
        target.raise_()
        fade_in(target, ms=320)
        slide_up(target, dy=18, ms=320)

    def _open_versions(self):
        """Диалог выбора версии, открытый со страницы «Главная»."""
        self.launch._open_versions()

    def _set_status(self, text, color="#86efac"):
        """Статус дублируется в активных разделах (Главная + Запуск)."""
        self.launch.set_status(text, color)
        if getattr(self, "home", None) is not None:
            self.home.set_status(text, color)

    def _set_busy(self, flag):
        self.launch.set_busy(flag)
        if getattr(self, "home", None) is not None:
            self.home.set_busy(flag)

    def _accounts(self):
        dlg = AccountsDialog(self.accounts, self)
        dlg.exec_()
        self.sidebar.set_account(self.accounts.current())
        self._refresh_state()
        if self.skin_editor is not None:
            self.skin_editor.load_account_skin()

    # ------------------------------------------------------------ состояние
    def _version_chosen(self, vid):
        self.cfg.last_version = vid
        self._refresh_state()

    def _folder_chosen(self, path):
        self.cfg.game_dir = path
        self.launch.set_folder(path)
        self._refresh_state()

    def _refresh_state(self):
        """Сверяет готовность (клиент + Java) и обновляет метки."""
        version = self.cfg.last_version
        major = major_for(version)
        client_ok = is_client_installed(version, self.cfg.game_dir)
        java_ok = is_installed(major)
        ready = client_ok and java_ok

        self.launch.set_version(version)
        self.launch.set_ready(ready)
        self.launch.set_java(describe(major))
        self.launch.set_folder(str(self.cfg.game_dir))
        self.launch.set_mods(str(self.cfg.get("mods_mode") or "Из коробки"))
        # раздел «Главная» — та же сводка и приветствие
        if getattr(self, "home", None) is not None:
            cur = self.accounts.current() or {}
            self.home.set_greeting(cur.get("name") or "Exeyta")
            self.home.set_version(version)
            self.home.set_java(describe(major))
            self.home.set_memory(self.launch.lbl_mem.text())
            self.home.set_folder(str(self.cfg.game_dir))
        if not self.busy:
            if ready:
                self._set_status("сессия готова", "#86efac")
            elif client_ok or java_ok:
                self._set_status("докачка компонентов…", "#ffb703")
            else:
                self._set_status("требуется установка", "#ffb703")
        self.settings.set_java("Java %d Temurin" % major,
                               str(java_exe(major)))
        return ready

    def _load_versions(self):
        from ..workers.download_worker import VersionsWorker
        self._versions_worker = VersionsWorker(self)
        self._versions_worker.loaded.connect(self.launch.set_version_ids)
        self._versions_worker.start()

    def _autostart(self):
        if self.cfg.get("autostart") and self._refresh_state():
            self._play()

    # -------------------------------------------------------------- установка
    def _open_install(self, version):
        if self._wizard is not None and self._wizard.isVisible():
            return
        from .install_wizard import InstallWizard
        self._install_ok = False
        self._set_busy(True)
        self._set_status("установка Minecraft и Java…", "#ffb703")
        w = InstallWizard(version, game_dir=self.cfg.game_dir, parent=self)
        self._wizard = w
        w.finished_ok.connect(self._install_succeeded)
        w.finished.connect(self._wizard_closed)
        w.exec_()   # модальное окно: ввод блокируется, фон живёт в QThread

    def _install_succeeded(self):
        self._install_ok = True

    def _wizard_closed(self):
        ok = self._install_ok
        self._install_ok = False
        self._wizard = None
        self._set_busy(False)
        self._refresh_state()
        if ok and self._pending_play:
            self._pending_play = False
            QTimer.singleShot(300, self._do_play)

    # ----------------------------------------------------------------- игра
    def _play(self):
        if self.busy:
            return
        if not self._refresh_state():
            self._pending_play = True
            self._open_install(self.cfg.last_version)
            return
        self._do_play()

    def _do_play(self):
        from ..core.launch_builder import ensure_ready

        version = self.cfg.last_version
        account = self.accounts.current()
        try:
            bat = ensure_ready(version, account, self.cfg.memory_mb,
                               self.cfg.game_dir,
                               str(self.cfg.get("jvm_args") or ""))
        except RuntimeError:
            self._pending_play = True
            self._open_install(version)
            return
        except Exception as e:
            self._set_status("ошибка: %s" % str(e)[:60], "#ff4d6d")
            return

        self.busy = True
        self._set_busy(True)

        # 1) автоматически ставим скин активного аккаунта в клиентский jar
        #    (offline-фолбэк ванили) — в QThread, UI не блокируется
        from ..workers.download_worker import SkinPatchWorker
        skin = (account or {}).get("skin") or ""
        self._set_status("применение скина…", "#ffd0e0")
        patcher = SkinPatchWorker(version, skin,
                                  game_dir=self.cfg.game_dir, parent=self)
        self._patcher = patcher

        def _after_patch(*_a):
            self._patcher = None
            self._start_game_worker(bat)

        patcher.done.connect(_after_patch)
        # скин — косметика: при ошибке всё равно запускаем игру
        patcher.failed.connect(_after_patch)
        patcher.start()

    def _start_game_worker(self, bat):
        # 2) запуск .bat оркестратором (QThread, логи в %APPDATA%/Exeyta/logs)
        from ..core.game_launcher import GameWorker
        self._set_status("запуск игры…", "#86efac")
        worker = GameWorker(bat, cwd=cfgmod.root_dir(), parent=self)
        worker.log_line.connect(self._game_log)
        worker.game_finished.connect(self._game_finished)
        worker.game_failed.connect(self._game_failed)
        self._game = worker
        worker.start()

    def _game_log(self, line):
        text = line.strip()
        if len(text) > 58:
            text = text[:57] + "…"
        self._set_status(text, "#c9a8b8")

    def _game_finished(self, rc):
        self.busy = False
        self._set_busy(False)
        if rc == 0:
            self._set_status("сессия готова", "#86efac")
        self._refresh_state()

    def _game_failed(self, message):
        self.busy = False
        self._set_busy(False)
        self._set_status(str(message)[:58], "#ff4d6d")

    # ----------------------------------------------------------------- окно
    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = rounded_path(r, 28 * self.k)
        p.setClipPath(path)
        p.fillRect(r, theme.bg_gradient(r.width(), r.height()))
        # верхняя полоска 3px: sunH #ffb703 -> #ff4d6d
        strip = QRectF(r.left(), r.top(), r.width(), 3)
        g = theme.sunh_gradient(strip)
        p.fillRect(strip, g)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self.windowHandle()
            try:
                if handle is not None and handle.startSystemMove():
                    return
            except Exception:
                pass
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        try:
            self.cfg.save()
        except Exception:
            pass
        w = self._wizard
        if w is not None and w.isVisible():
            w._cancel()
        # работающие потоки (игра/патч/список версий) переживают закрытие
        # окна: снимаем родителя, чтобы не «QThread destroyed while running»
        for th in (getattr(self, "_game", None),
                   getattr(self, "_patcher", None),
                   getattr(self, "_versions_worker", None)):
            if th is not None and getattr(th, "isRunning", lambda: False)():
                th.setParent(None)
                _BACKGROUND_THREADS.append(th)
        super().closeEvent(event)
