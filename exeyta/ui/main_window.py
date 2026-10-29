# -*- coding: utf-8 -*-
"""Главное окно лаунчера Exeyta.

Новый интерфейс: спокойный тёмный фон, узкий сайдбар, крупные карточки
и приглушённый золотистый акцент. Разделы: Главная, Версии, Настройки,
Консоль, Скины. Внизу — строка состояния с кнопкой остановки игры.
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
from .console_panel import ConsolePanel
from .controls import add_label, rounded_path
from .home_panel import HomePanel
from .launch_panel import LaunchPanel
from .settings_panel import SettingsPanel
from .sidebar import AccountsDialog, Sidebar

# keep-alive для потоков, переживающих закрытие окна (игра и т.п.)
_BACKGROUND_THREADS = []

PAGE_X = 264
PAGE_Y = 92
PAGE_W = 1144
PAGE_H = 648

PAGE_META = {
    "home": ("Главная", "Выбранная версия и текущие параметры запуска"),
    "versions": ("Версии", "Каталог версий Minecraft и установка компонентов"),
    "settings": ("Настройки", "Память, Java, папка игры и язык интерфейса"),
    "console": ("Консоль", "Журнал запуска и сообщения лаунчера"),
    "skins": ("Скины", "Редактор скина и предпросмотр в 3D"),
}


class _WinBtn(QWidget):
    """Кнопка окна (свернуть / закрыть) в стиле макета."""

    clicked = pyqtSignal()

    def __init__(self, kind, k=1.0, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.k = float(k)
        self.setFixedSize(round(30 * k), round(28 * k))
        self.setCursor(Qt.PointingHandCursor)
        self._hover = HoverFader(self, ms=140)

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
        k = self.k
        t = self._hover.hoverT
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        base = QColor("#17181d")
        hover = QColor("#2a2023") if self.kind == "close" else QColor("#23242a")
        p.setBrush(base if t < 0.02 else hover)
        p.setPen(QPen(QColor("#2e2f36"), 1.0))
        p.drawRoundedRect(r, 7 * k, 7 * k)
        if self.kind == "close" and t > 0.3:
            color = QColor("#e08a8a")
        else:
            color = QColor("#8b8f98") if t < 0.3 else QColor("#e2e4e9")
        pen = QPen(color)
        pen.setWidthF(max(1.3, 1.5 * k))
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        s = 5 * k
        if self.kind == "min":
            p.drawLine(int(cx - s), int(cy), int(cx + s), int(cy))
        else:
            p.drawLine(int(cx - s), int(cy - s), int(cx + s), int(cy + s))
            p.drawLine(int(cx + s), int(cy - s), int(cx - s), int(cy + s))
        p.end()


class _DragBar(QWidget):
    """Прозрачная полоса для перетаскивания окна за верхнюю область."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._drag = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self.window().windowHandle()
            try:
                if handle is not None and handle.startSystemMove():
                    event.accept()
                    return
            except Exception:
                pass
            self._drag = event.globalPos() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPos() - self._drag)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag = None
        super().mouseReleaseEvent(event)


class _StatusBar(QWidget):
    """Нижняя строка состояния: статус слева, «Остановить» справа."""

    stop_clicked = pyqtSignal()

    def __init__(self, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self._color = QColor("#8b8f98")
        self._text = "сессия готова"
        self.setFixedSize(round(1208 * k), round(52 * k))
        self.lbl_text = add_label(self, k, 38, 32, 12.5, 500, 960,
                                  self._text, color="#8b8f98")
        self.btn_stop = _StopButton(k=k, parent=self)
        self.btn_stop.move(round(1034 * k), round(10 * k))
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        self.btn_stop.hide()

    def set_status(self, text, color="#8b8f98"):
        self._text = str(text)
        self._color = QColor(_color_for(color))
        self.lbl_text.setText(self._text)
        pal = self.lbl_text.palette()
        pal.setColor(self.lbl_text.foregroundRole(), self._color)
        self.lbl_text.setPalette(pal)
        self.update()

    def set_stoppable(self, flag):
        self.btn_stop.setVisible(bool(flag))

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        p.fillRect(self.rect(), QColor("#101115"))
        p.setPen(QPen(QColor("#232429")))
        p.drawLine(0, 0, self.width(), 0)
        # индикатор состояния
        p.setPen(Qt.NoPen)
        glow = QColor(self._color)
        glow.setAlpha(45)
        p.setBrush(glow)
        p.drawEllipse(QRectF(22 * k, 23 * k, 10 * k, 10 * k))
        p.setBrush(self._color)
        p.drawEllipse(QRectF(24.5 * k, 25.5 * k, 5 * k, 5 * k))
        p.end()


class _StopButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.setFixedSize(round(140 * k), round(32 * k))
        self.setCursor(Qt.PointingHandCursor)
        self._hover = HoverFader(self, ms=140)

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
        k = self.k
        t = self._hover.hoverT
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setBrush(QColor("#24252b") if t < 0.3 else QColor("#332528"))
        p.setPen(QPen(QColor("#a35c5c") if t < 0.5 else QColor("#d97a7a"), 1.0))
        p.drawRoundedRect(r, 8 * k, 8 * k)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#c98a8a"))
        p.drawRoundedRect(QRectF(18 * k, 12 * k, 8 * k, 8 * k), 1.5 * k, 1.5 * k)
        p.setFont(theme.font(12 * k, 500))
        p.setPen(QColor("#d9b0b0"))
        p.drawText(QRectF(34 * k, 0, 96 * k, 32 * k),
                   Qt.AlignLeft | Qt.AlignVCenter, "Остановить")
        p.end()


def _color_for(color):
    """Приводит старые hex-цвета статусов к новой палитре."""
    mapping = {
        "#86efac": "#7fbf8f",
        "#ffb703": "#c9a45c",
        "#ff4d6d": "#d97a7a",
        "#ffd0e0": "#e8cf9a",
        "#c9a8b8": "#8b8f98",
    }
    return mapping.get(str(color).lower(), color)


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
        self.cfg.save()
        self.accounts = AccountStore()
        self.busy = False
        self._stoppable = False
        self._game = None
        self._wizard = None
        self._install_ok = False
        self._pending_play = False
        self._drag_pos = None
        self.skin_editor = None
        self._active_tab = "home"

        self._build()
        self.sidebar.set_account(self.accounts.current())
        self.sidebar.set_active("home")
        self._apply_page_meta("home")

        QTimer.singleShot(0, self._build_skin_editor)
        QTimer.singleShot(10, self._refresh_state)
        QTimer.singleShot(60, self._load_versions)
        QTimer.singleShot(900, self._autostart)

    # ------------------------------------------------------------------ UI
    def _section(self, key):
        return {
            "home": getattr(self, "home", None),
            "versions": getattr(self, "launch", None),
            "settings": getattr(self, "settings", None),
            "console": getattr(self, "console", None),
            "skins": getattr(self, "skin_editor", None),
        }.get(key)

    def _build(self):
        k = self.k

        self.sidebar = Sidebar(k=k, parent=self)
        self.sidebar.move(0, 0)
        self.sidebar.nav_clicked.connect(self._nav)
        self.sidebar.gear_clicked.connect(self._accounts)

        # полоса перетаскивания и заголовок страницы
        self._dragbar = _DragBar(self)
        self._dragbar.setGeometry(round(232 * k), 0, round(1208 * k),
                                  round(48 * k))

        self.lbl_title = add_label(self, k, PAGE_X, 52, 21, 700, 700,
                                   "Главная")
        self.lbl_sub = add_label(self, k, PAGE_X, 76, 12, 500, 900,
                                 PAGE_META["home"][1], color="#8b8f98")

        self.btn_min = _WinBtn("min", k=k, parent=self)
        self.btn_min.move(round(1356 * k), round(14 * k))
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_close = _WinBtn("close", k=k, parent=self)
        self.btn_close.move(round(1394 * k), round(14 * k))
        self.btn_close.clicked.connect(self.close)

        # страницы
        self.home = HomePanel(self.cfg, k=k, parent=self)
        self.home.move(round(PAGE_X * k), round(PAGE_Y * k))
        self.home.play_clicked.connect(self._play)
        self.home.version_clicked.connect(self._open_versions)
        self.home.open_folder_clicked.connect(self._open_game_folder)

        self.launch = LaunchPanel(self.cfg, k=k, parent=self)
        self.launch.move(round(PAGE_X * k), round(PAGE_Y * k))
        self.launch.play_clicked.connect(self._play)
        self.launch.version_chosen.connect(self._version_chosen)
        self.launch.download_version.connect(self._open_install)
        self.launch.memory_changed.connect(
            lambda mb: self.settings.set_memory_mb(mb))
        self.launch.hide()

        self.settings = SettingsPanel(self.cfg, k=k, parent=self)
        self.settings.move(round(PAGE_X * k), round(PAGE_Y * k))
        self.settings.memory_changed.connect(self._memory_changed)
        self.settings.folder_chosen.connect(self._folder_chosen)
        self.settings.autostart_changed.connect(
            lambda _on: self.cfg.save())
        self.settings.hide()

        self.console = ConsolePanel(k=k, parent=self)
        self.console.move(round(PAGE_X * k), round(PAGE_Y * k))
        self.console.open_logs_clicked.connect(self._open_logs_folder)
        self.console.hide()

        # нижняя строка состояния
        self.statusbar = _StatusBar(k=k, parent=self)
        self.statusbar.move(round(232 * k), round(848 * k))
        self.statusbar.stop_clicked.connect(self._stop_game)
        self.statusbar.set_status("сессия готова", "#7fbf8f")

    def _build_skin_editor(self):
        if self.skin_editor is not None:
            return
        from .skin_editor import SkinEditorPanel
        self.skin_editor = SkinEditorPanel(self.cfg, self.accounts,
                                           k=self.k, parent=self)
        # редактор 1090x648 центрируем в области страницы 1144x648
        self.skin_editor.move(round((PAGE_X + 27) * self.k),
                              round(PAGE_Y * self.k))
        self.skin_editor.hide()
        self.skin_editor.load_account_skin()

    def _apply_page_meta(self, key):
        title, sub = PAGE_META.get(key, ("", ""))
        self.lbl_title.setText(title)
        self.lbl_sub.setText(sub)

    # ------------------------------------------------------------ навигация
    def _nav(self, key):
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
        self._apply_page_meta(key)
        target.show()
        target.raise_()
        fade_in(target, ms=240)
        slide_up(target, dy=14, ms=240)

    def _open_versions(self):
        """Кнопка «Выбрать версию» на главной открывает раздел «Версии»."""
        self._nav("versions")

    def _open_game_folder(self):
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        path = str(self.cfg.game_dir)
        try:
            self.cfg.game_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _open_logs_folder(self):
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(cfgmod.logs_dir())))

    # ------------------------------------------------------------ состояние
    def _set_status(self, text, color="#7fbf8f"):
        self.statusbar.set_status(text, color)
        self.console.set_running(self.busy, text)

    def _set_busy(self, flag, stoppable=True):
        self.busy = bool(flag)
        self._stoppable = bool(flag) and bool(stoppable)
        self.launch.set_busy(flag)
        self.home.set_busy(flag)
        self.statusbar.set_stoppable(self._stoppable)

    def _accounts(self):
        dlg = AccountsDialog(self.accounts, self)
        dlg.exec_()
        self.sidebar.set_account(self.accounts.current())
        self._refresh_state()
        if self.skin_editor is not None:
            self.skin_editor.load_account_skin()

    def _version_chosen(self, vid):
        self.cfg.last_version = vid
        self._set_status("выбрана версия %s" % vid, "#c9a45c")
        self._refresh_state()

    def _memory_changed(self, mb):
        self.launch.set_memory_mb(mb)
        self.home.set_memory(mb)
        self.settings.set_memory_mb(mb)

    def _installed_count(self):
        try:
            base = self.cfg.game_dir / "versions"
            if base.is_dir():
                return sum(1 for p in base.iterdir() if p.is_dir())
        except Exception:
            pass
        return 1 if is_client_installed(self.cfg.last_version,
                                        self.cfg.game_dir) else 0

    def _folder_chosen(self, path):
        self.cfg.game_dir = path
        self._refresh_state()

    def _refresh_state(self):
        """Сверяет готовность (клиент + Java) и обновляет метки."""
        version = self.cfg.last_version
        major = major_for(version)
        client_ok = is_client_installed(version, self.cfg.game_dir)
        java_ok = is_installed(major)
        ready = client_ok and java_ok
        account = self.accounts.current() or {}

        self.launch.set_version(version)
        self.launch.set_ready(ready)
        self.launch.set_java(describe(major))
        self.launch.set_folder(str(self.cfg.game_dir))
        self.launch.set_mods(str(self.cfg.get("mods_mode") or "Из коробки"))

        self.home.set_version(version)
        self.home.set_ready(ready)
        self.home.set_java(describe(major))
        self.home.set_memory(self.cfg.memory_mb)
        self.home.set_folder(str(self.cfg.game_dir))
        self.home.set_greeting(account.get("name") or "Exeyta")
        self.home.set_profile(account.get("name") or "Exeyta")
        self.home.set_counts(self._installed_count(),
                             len(getattr(self.launch, "_version_ids", [])))

        if not self.busy:
            if ready:
                self._set_status("сессия готова", "#7fbf8f")
            elif client_ok or java_ok:
                self._set_status("докачка компонентов…", "#c9a45c")
            else:
                self._set_status("требуется установка", "#c9a45c")

        self.settings.set_java("Java %d Temurin" % major,
                               str(java_exe(major)))
        self.settings.set_memory_mb(self.cfg.memory_mb)
        self.sidebar.set_account(account)
        return ready

    def _load_versions(self):
        from ..workers.download_worker import VersionsWorker
        self._versions_worker = VersionsWorker(self)
        self._versions_worker.loaded.connect(self._versions_loaded)
        self._versions_worker.start()

    def _versions_loaded(self, ids):
        self.launch.set_version_ids(ids)
        self.home.set_counts(
            self._installed_count(),
            len(getattr(self.launch, "_version_ids", [])))

    def _autostart(self):
        if self.cfg.get("autostart") and self._refresh_state():
            self._play()

    # -------------------------------------------------------------- установка
    def _open_install(self, version):
        if self._wizard is not None and self._wizard.isVisible():
            return
        from .install_wizard import InstallWizard
        self._install_ok = False
        self._set_busy(True, stoppable=False)
        self._set_status("установка Minecraft и Java…", "#c9a45c")
        w = InstallWizard(version, game_dir=self.cfg.game_dir, parent=self)
        self._wizard = w
        w.finished_ok.connect(self._install_succeeded)
        w.finished.connect(self._wizard_closed)
        w.exec_()

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
            self._set_status("ошибка: %s" % str(e)[:60], "#d97a7a")
            return

        self._set_busy(True)
        self.console.append_log("=== Запуск Minecraft %s ===" % version)

        from ..workers.download_worker import SkinPatchWorker
        skin = (account or {}).get("skin") or ""
        self._set_status("применение скина…", "#e8cf9a")
        patcher = SkinPatchWorker(version, skin,
                                  game_dir=self.cfg.game_dir, parent=self)
        self._patcher = patcher

        def _after_patch(*_a):
            self._patcher = None
            self._start_game_worker(bat)

        patcher.done.connect(_after_patch)
        patcher.failed.connect(_after_patch)
        patcher.start()

    def _start_game_worker(self, bat):
        from ..core.game_launcher import GameWorker
        self._set_status("запуск игры…", "#7fbf8f")
        worker = GameWorker(bat, cwd=cfgmod.root_dir(), parent=self)
        worker.log_line.connect(self._game_log)
        worker.game_finished.connect(self._game_finished)
        worker.game_failed.connect(self._game_failed)
        self._game = worker
        worker.start()

    def _stop_game(self):
        stopped = False
        patcher = getattr(self, "_patcher", None)
        if patcher is not None and patcher.isRunning():
            try:
                patcher.cancel()
                stopped = True
            except Exception:
                pass
        if self._game is not None and self._game.isRunning():
            try:
                self._game.cancel()
                stopped = True
            except Exception:
                pass
        if stopped:
            self._set_status("остановка игры…", "#c9a45c")
            self.console.append_log("=== Остановка по запросу пользователя ===")

    def _game_log(self, line):
        text = line.strip()
        self.console.append_log(text)
        short = text
        if len(short) > 70:
            short = short[:69] + "…"
        self._set_status(short, "#8b8f98")

    def _game_finished(self, rc):
        self._set_busy(False)
        if rc == 0:
            self._set_status("сессия готова", "#7fbf8f")
        elif rc < 0:
            self._set_status("игра остановлена", "#c9a45c")
        self.console.set_running(False)
        self._refresh_state()

    def _game_failed(self, message):
        self._set_busy(False)
        self._set_status(str(message)[:70], "#d97a7a")
        self.console.append_log("Ошибка: %s" % message)
        self.console.set_running(False)

    # ----------------------------------------------------------------- окно
    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = rounded_path(r, 12 * self.k)
        p.setClipPath(path)
        p.fillRect(r, theme.bg_gradient(r.width(), r.height()))
        pen = QPen(QColor("#2a2b31"))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 12 * self.k, 12 * self.k)
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
        from PyQt5.QtCore import QThread
        seen = set()
        for th in ([getattr(self, "_game", None),
                    getattr(self, "_patcher", None),
                    getattr(self, "_versions_worker", None)]
                   + self.findChildren(QThread)):
            if th is None or id(th) in seen:
                continue
            seen.add(id(th))
            if getattr(th, "isRunning", lambda: False)():
                th.setParent(None)
                _BACKGROUND_THREADS.append(th)
        super().closeEvent(event)
