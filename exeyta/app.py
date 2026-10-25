# -*- coding: utf-8 -*-
"""Точка входа лаунчера Exeyta (вызывается из корневого launcher.py)."""
import sys
import time
import traceback
from pathlib import Path


def _install_excepthook():
    """Логирует необработанные исключения и НЕ роняет приложение.

    Исключение внутри paintEvent/слота иначе приводит к аварийному
    завершению процесса (нативный abort); хук пишет трейс в
    %APPDATA%/Exeyta/logs/error.log и даёт UI продолжить работу.
    """
    try:
        from .core.config import logs_dir
        log_path = logs_dir() / "error.log"
    except Exception:
        log_path = Path(tempfile_fallback()) / "exeyta_error.log"

    def hook(tp, val, tb):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n=== %s ===\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
                traceback.print_exception(tp, val, tb, file=f)
        except Exception:
            pass
        try:
            sys.__excepthook__(tp, val, tb)   # дубль в консоль (dev)
        except Exception:
            pass

    sys.excepthook = hook


def tempfile_fallback():
    import tempfile
    return tempfile.gettempdir()


def _load_qss(app):
    qss = Path(__file__).resolve().parent / "ui" / "styles.qss"
    try:
        if qss.exists():
            app.setStyleSheet(qss.read_text(encoding="utf-8"))
    except Exception:
        pass


def run() -> int:
    _install_excepthook()

    # PyQt5 импортируем здесь, чтобы выдать понятную инструкцию при отсутствии
    try:
        from PyQt5.QtCore import Qt, QTimer
        from PyQt5.QtGui import QFont, QIcon
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        print("Не найден PyQt5.")
        print("Установите зависимости: install_deps.bat"
              "  (pip install -r requirements.txt)")
        return 1

    # High-DPI до создания QApplication (масштаб с сохранением пропорций)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Exeyta Launcher")
    app.setOrganizationName("Exeyta")
    app.setFont(QFont("Segoe UI", 10))
    _load_qss(app)

    # иконка
    try:
        from .core import config as cfgmod
        ico = cfgmod.assets_dir() / "icon.ico"
        if ico.exists():
            app.setWindowIcon(QIcon(str(ico)))
    except Exception:
        pass

    # масштаб окна с сохранением пропорций 1864x1036
    from .core import config as cfgmod2
    screen = app.primaryScreen()
    k = 1.0
    if screen is not None:
        geo = screen.availableGeometry()
        k = min(1.0,
                geo.width() / float(cfgmod2.BASE_W),
                geo.height() / float(cfgmod2.BASE_H))
        k = max(0.55, k)

    from .ui.main_window import MainWindow
    win = MainWindow(k=k)
    # центрирование
    if screen is not None:
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - win.width()) // 2
        y = geo.y() + (geo.height() - win.height()) // 2
        win.move(max(geo.x(), x), max(geo.y(), y))
    win.show()

    return app.exec_()
