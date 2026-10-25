# -*- coding: utf-8 -*-
"""Точка входа установщика ExeytaSetup (вызывается из корневого installer.py)."""
import sys
import time
import traceback
from pathlib import Path


def _install_excepthook():
    """Логирует необработанные исключения и НЕ роняет установщик.

    Лог пишется в %TEMP%\\ExeytaSetup_error.log (каталог установки может
    быть недоступен на запись до копирования файлов).
    """
    import tempfile
    log_path = Path(tempfile.gettempdir()) / "ExeytaSetup_error.log"

    def hook(tp, val, tb):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n=== %s ===\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
                traceback.print_exception(tp, val, tb, file=f)
        except Exception:
            pass
        try:
            sys.__excepthook__(tp, val, tb)
        except Exception:
            pass

    sys.excepthook = hook


def _load_qss(app):
    qss = Path(__file__).resolve().parent / "ui" / "styles.qss"
    try:
        if qss.exists():
            app.setStyleSheet(qss.read_text(encoding="utf-8"))
    except Exception:
        pass


def run() -> int:
    _install_excepthook()
    try:
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont, QIcon
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        print("Не найден PyQt5.")
        print("Установите зависимости: install_deps.bat"
              "  (pip install -r requirements.txt)")
        return 1

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("ExeytaSetup")
    app.setOrganizationName("Exeyta")
    app.setFont(QFont("Segoe UI", 10))
    _load_qss(app)

    # иконка (рядом с installer.py / внутри сборки)
    try:
        root = Path(__file__).resolve().parents[2]
        ico = root / "assets" / "icon.ico"
        if ico.exists():
            app.setWindowIcon(QIcon(str(ico)))
    except Exception:
        pass

    from .ui.wizard_window import WizardWindow
    win = WizardWindow()
    screen = app.primaryScreen()
    if screen is not None:
        geo = screen.availableGeometry()
        win.move(geo.x() + (geo.width() - win.width()) // 2,
                 geo.y() + (geo.height() - win.height()) // 2)
    win.show()
    return app.exec_()
