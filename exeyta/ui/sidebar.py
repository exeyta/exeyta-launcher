# -*- coding: utf-8 -*-
"""Сайдбар лаунчера: 232px, спокойная тёмная панель.

Сверху — название и навигация (Главная / Версии / Настройки / Консоль /
Скины), снизу — сообщество, карточка offline-аккаунта и версия лаунчера.
"""
from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import (QBrush, QColor, QFont, QFontMetricsF,
                         QLinearGradient, QPainter, QPainterPath, QPen,
                         QPolygonF)
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QVBoxLayout,
                             QWidget)

from exeyta_shared import theme
from exeyta_shared.animations import HoverFader

from .controls import (FxButton, add_label, draw_base, lerp_color,
                       rounded_path, w)


# ---------------------------------------------------------------------------
# Ссылка сайдбара (Telegram / текстурпак)
# ---------------------------------------------------------------------------
class _LinkRow(QWidget):
    clicked = pyqtSignal()

    def __init__(self, text, icon_svg=None, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self._text = text
        self._icon_svg = icon_svg
        self._pm = None
        self.setFixedSize(round(192 * k), round(32 * k))
        self.setCursor(Qt.PointingHandCursor)
        self._hover = HoverFader(self, ms=160)

    def _icon(self):
        if self._icon_svg is None:
            return None
        if self._pm is None:
            self._pm = theme.icon_pixmap(
                self._icon_svg, round(16 * self.k), "#8b8f98", stroke=1.7)
        return self._pm

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
        if t > 0.02:
            p.fillPath(rounded_path(QRectF(self.rect()).adjusted(
                0.5, 0.5, -0.5, -0.5), 7 * k),
                QColor(255, 255, 255, round(7 * t)))
        color = lerp_color("#8b8f98", "#e2e4e9", t).name()
        icon = self._icon()
        x = 10 * k
        if icon is not None:
            p.drawPixmap(round(x), round((self.height() - icon.height()) / 2),
                         icon)
            x += 22 * k
        f = theme.font(12.5 * k, 50)
        draw_base(p, x, 21 * k, self._text, f, color,
                  wide=round(150 * k))
        p.end()


# ---------------------------------------------------------------------------
# Диалог управления offline-аккаунтами (шестерёнка)
# ---------------------------------------------------------------------------
class AccountsDialog(QDialog):
    """Добавить / удалить / выбрать активный offline-аккаунт."""

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("Аккаунты — Exeyta")
        self.setModal(True)
        self.setFixedSize(460, 480)
        self.setStyleSheet(self._dlg_qss())

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)

        title = QLabel("Offline-аккаунты")
        title.setObjectName("dlgTitle")
        root.addWidget(title)
        sub = QLabel("Только offline: без Microsoft/Mojang OAuth.\n"
                     "Хранение: %APPDATA%\\Exeyta\\accounts.json")
        sub.setObjectName("dlgSub")
        sub.setWordWrap(True)
        root.addWidget(sub)

        self.listw = QListWidget()
        self.listw.setObjectName("acctList")
        root.addWidget(self.listw, 1)

        row = QHBoxLayout()
        self.edit = QLineEdit()
        self.edit.setObjectName("dlgEdit")
        self.edit.setPlaceholderText("Ник (латиница, цифры, _, до 16)")
        self.edit.setMaxLength(16)
        row.addWidget(self.edit, 1)
        btn_add = FxButton("Добавить", kind="chip", w_=110, h_=38, radius=9,
                           px=13, svg_w=700)
        btn_add.clicked.connect(self.on_add)
        row.addWidget(btn_add)
        root.addLayout(row)

        row2 = QHBoxLayout()
        btn_del = FxButton("Удалить", kind="danger", w_=110, h_=38, radius=9,
                           px=13, svg_w=600)
        btn_del.clicked.connect(self.on_remove)
        btn_sel = FxButton("Выбрать активный", kind="sun", w_=180, h_=38,
                           radius=9, px=13, svg_w=700)
        btn_sel.clicked.connect(self.on_select)
        row2.addWidget(btn_del)
        row2.addStretch(1)
        row2.addWidget(btn_sel)
        root.addLayout(row2)

        self.hint = QLabel("")
        self.hint.setObjectName("dlgHint")
        root.addWidget(self.hint)

        btn_close = FxButton("Закрыть", kind="ghost", w_=412, h_=40, radius=9,
                             px=13, svg_w=600)
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close)

        self.reload()

    def _dlg_qss(self):
        return """
            QDialog { background: #17181d; }
            QLabel#dlgTitle { color: #eceef2; font-size: 20px; font-weight: 700; }
            QLabel#dlgSub { color: #8b8f98; font-size: 12px; }
            QLabel#dlgHint { color: #d97a7a; font-size: 12px; min-height: 16px; }
            QLineEdit#dlgEdit {
                background: #1c1d22; border: 1px solid #2a2b31;
                border-radius: 9px; padding: 8px 12px; color: #eceef2;
                font-size: 14px; selection-background-color: #c9a45c;
                selection-color: #1c1609;
            }
            QLineEdit#dlgEdit:focus { border: 1px solid #c9a45c; }
            QListWidget#acctList {
                background: #141519; border: 1px solid #2a2b31;
                border-radius: 10px; padding: 6px; color: #eceef2;
                font-size: 14px; outline: none;
            }
            QListWidget#acctList::item { padding: 10px 12px; border-radius: 7px; }
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

    def reload(self):
        self.listw.clear()
        cur = self.store.current() or {}
        for i, acc in enumerate(self.store.all()):
            active = acc.get("name") == cur.get("name")
            label = "%s  %s  %s" % ("●" if active else " ",
                                    acc.get("name", "?"), acc.get("uuid", ""))
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, i)
            if active:
                it.setToolTip("Активный offline-аккаунт")
            self.listw.addItem(it)
        for i in range(self.listw.count()):
            if self.listw.item(i).data(Qt.UserRole) == self.store.active:
                self.listw.setCurrentRow(i)
                break

    def on_add(self):
        name = self.edit.text().strip()
        if not name:
            self.hint.setText("Введите ник")
            return
        try:
            self.store.add(name)
            self.edit.clear()
            self.hint.setText("")
            self.reload()
        except ValueError as e:
            self.hint.setText(str(e))

    def on_remove(self):
        row = self.listw.currentRow()
        if row < 0:
            self.hint.setText("Выберите аккаунт")
            return
        idx = self.listw.item(row).data(Qt.UserRole)
        self.store.remove(int(idx))
        self.hint.setText("")
        self.reload()

    def on_select(self):
        row = self.listw.currentRow()
        if row < 0:
            self.hint.setText("Выберите аккаунт")
            return
        idx = self.listw.item(row).data(Qt.UserRole)
        self.store.set_active(int(idx))
        self.hint.setText("")
        self.reload()
        self.accept()


# ---------------------------------------------------------------------------
# Сайдбар
# ---------------------------------------------------------------------------
NAV_ITEMS = [
    ("home", "Главная", theme.ICON_HOME),
    ("versions", "Версии", theme.ICON_VERSIONS),
    ("settings", "Настройки", theme.ICON_SLIDERS),
    ("console", "Консоль", theme.ICON_TERMINAL),
    ("skins", "Скины", theme.ICON_SKIN),
]


class Sidebar(QWidget):
    nav_clicked = pyqtSignal(str)
    gear_clicked = pyqtSignal()

    def __init__(self, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.setFixedSize(round(232 * k), round(900 * k))
        self._account = {"name": "Exeyta"}
        self._nav = {}
        self._build()

    def _build(self):
        k = self.k
        from .controls import NavButton
        ys = {"home": 82, "versions": 132, "settings": 182,
              "console": 232, "skins": 282}
        for key, label, icon in NAV_ITEMS:
            btn = NavButton(label, icon, k=k, parent=self)
            btn.move(round(16 * k), round(ys[key] * k))
            btn.clicked.connect(lambda kk=key: self.nav_clicked.emit(kk))
            self._nav[key] = btn

        self.tg = _LinkRow("Telegram-сообщество", theme.ICON_TELEGRAM,
                           k=k, parent=self)
        self.tg.move(round(20 * k), round(392 * k))
        self.tg.clicked.connect(self._open_telegram)

        self.btn_packs = _LinkRow("Скачать текстурпак", theme.ICON_PACK,
                                  k=k, parent=self)
        self.btn_packs.move(round(20 * k), round(428 * k))
        self.btn_packs.clicked.connect(self._open_resource_packs)

        # карточка аккаунта
        self._acct_rect = QRectF(16 * k, 800 * k, 200 * k, 62 * k)
        self._acct_zone = _LinkRow("", None, k=k, parent=self)
        self._acct_zone.setFixedSize(round(200 * k), round(62 * k))
        self._acct_zone.move(round(16 * k), round(800 * k))
        self._acct_zone.clicked.connect(self.gear_clicked.emit)

        gear_svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
                    'width="24" height="24"><path d="%s" fill="#c9a45c"/></svg>'
                    % theme.ICON_GEAR)
        self.gear = FxButton("", kind="plain", w_=round(28 * k),
                             h_=round(28 * k), radius=8,
                             icon=theme.icon_pixmap(gear_svg, round(16 * k)),
                             tooltip="Управление offline-аккаунтами",
                             parent=self)
        self.gear.move(round(178 * k), round(817 * k))
        self.gear.clicked.connect(self.gear_clicked.emit)

    def _open_telegram(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(theme.TELEGRAM_URL))

    def _open_resource_packs(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(theme.RESOURCE_PACKS_URL))

    # --- состояние --------------------------------------------------------
    def set_active(self, key):
        for k_, btn in self._nav.items():
            btn.set_checked(k_ == key)

    def set_account(self, account):
        self._account = account or {"name": "Exeyta"}
        self.update()

    # --- отрисовка --------------------------------------------------------
    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        w_, h_ = self.width(), self.height()

        p.fillRect(self.rect(), QColor("#101115"))
        # тонкая полоса-градиент сверху (очень сдержанная)
        top = QRectF(0, 0, w_, 2 * k)
        g = QLinearGradient(top.left(), 0, top.right(), 0)
        g.setColorAt(0.0, QColor(201, 164, 92, 170))
        g.setColorAt(1.0, QColor(201, 164, 92, 0))
        p.fillRect(top, g)

        # разделитель справа
        p.setPen(QPen(QColor("#232429")))
        p.drawLine(w_ - 1, 0, w_ - 1, h_)

        # логотип + название
        lr = QRectF(20 * k, 26 * k, 24 * k, 24 * k)
        lg = QLinearGradient(lr.topLeft(), lr.bottomRight())
        lg.setColorAt(0.0, QColor("#ddc27e"))
        lg.setColorAt(1.0, QColor("#a8843c"))
        p.setPen(Qt.NoPen)
        p.setBrush(lg)
        p.drawRoundedRect(lr, 7 * k, 7 * k)
        p.setFont(theme.font(13 * k, w(800)))
        p.setPen(QColor("#1c1609"))
        p.drawText(lr, Qt.AlignCenter, "E")

        f = theme.font(13.5 * k, w(700))
        draw_base(p, 54 * k, 43 * k, "Exeyta Launcher", f, "#e6e8ec",
                  wide=round(160 * k))

        # разделители секций
        p.setPen(QPen(QColor("#1d1e23")))
        p.drawLine(round(16 * k), round(344 * k), round(216 * k),
                   round(344 * k))
        p.drawLine(round(16 * k), round(478 * k), round(216 * k),
                   round(478 * k))

        cf = theme.font(10 * k, w(700))
        cf.setLetterSpacing(QFont.AbsoluteSpacing, 1.4 * k)
        draw_base(p, 22 * k, 370 * k, "СООБЩЕСТВО", cf, "#62666e",
                  wide=round(180 * k))

        # карточка аккаунта
        ar = self._acct_rect
        p.setBrush(QColor("#1a1b20"))
        p.setPen(QPen(QColor("#2a2b31")))
        p.drawRoundedRect(ar, 10 * k, 10 * k)

        # аватар
        cx, cy = 40 * k, 831 * k
        ring = QLinearGradient(cx - 16 * k, cy - 16 * k,
                               cx + 16 * k, cy + 16 * k)
        ring.setColorAt(0.0, QColor("#ddc27e"))
        ring.setColorAt(1.0, QColor("#a8843c"))
        p.setBrush(QColor("#d9c9ae"))
        p.setPen(QPen(ring, 1.6 * k))
        p.drawEllipse(QPointF(cx, cy), 16 * k, 16 * k)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#4a3728"))
        p.drawRoundedRect(QRectF(cx - 8 * k, cy - 7 * k, 16 * k, 5.5 * k),
                          1.6 * k, 1.6 * k)

        name = (self._account or {}).get("name") or "Exeyta"
        draw_base(p, 64 * k, 827 * k, name, theme.font(13 * k, w(700)),
                  "#eceef2", wide=round(110 * k))
        draw_base(p, 64 * k, 845 * k, "Premium Offline",
                  theme.font(10.5 * k, w(500)), "#c9a45c",
                  wide=round(120 * k))

        # версия лаунчера
        draw_base(p, 20 * k, 886 * k, theme.LAUNCHER_VERSION,
                  theme.font(10.5 * k, w(500)), "#5f636b",
                  wide=round(100 * k))
        p.end()
