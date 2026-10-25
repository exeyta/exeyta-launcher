# -*- coding: utf-8 -*-
"""Сайдбар лаунчера (280px, на всю высоту) — 1:1 с assets/launcher-ui.svg.

Логотип, навигация, СООБЩЕСТВО (Telegram), карточка аккаунта внизу
со статусом «Premium Offline» и шестерёнкой (управление аккаунтами).
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

from .controls import (FxButton, add_label, apply_glow, draw_base, lerp_color,
                       rounded_path, w)


# ---------------------------------------------------------------------------
# Кнопка Telegram (232x50, #2AABEE + glow)
# ---------------------------------------------------------------------------
class TelegramButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, k=1.0, parent=None, url=theme.TELEGRAM_URL):
        super().__init__(parent)
        self.k = float(k)
        self._url = url
        self.setFixedSize(round(232 * k), round(50 * k))
        self.setCursor(Qt.PointingHandCursor)
        self._hover = HoverFader(self, ms=220)
        apply_glow(self, "#2AABEE", blur=26, alpha=130)

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
        inset = (2.0 if getattr(self, "_pressed", False) else 0.0)
        r = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        bg = lerp_color("#2AABEE", "#4dc0f5", t)
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(r, 16 * k, 16 * k)
        # бумажный самолётик (из макета): 78,447 116,455 78,463 88,455
        pts = [QPointF(26 * k, 17 * k), QPointF(64 * k, 25 * k),
               QPointF(26 * k, 33 * k), QPointF(36 * k, 25 * k)]
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawPolygon(QPolygonF(pts))
        f = theme.font(15 * k, w(700))
        draw_base(p, 80 * k, 30 * k, "Telegram", f, "#ffffff", wide=round(120 * k))
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
        btn_add = FxButton("Добавить", kind="chip", w_=110, h_=38, radius=12,
                           px=13, svg_w=700)
        btn_add.clicked.connect(self.on_add)
        row.addWidget(btn_add)
        root.addLayout(row)

        row2 = QHBoxLayout()
        btn_del = FxButton("Удалить", kind="danger", w_=110, h_=38, radius=12,
                           px=13, svg_w=600)
        btn_del.clicked.connect(self.on_remove)
        btn_sel = FxButton("Выбрать активный", kind="sun", w_=180, h_=38,
                           radius=12, px=13, svg_w=700)
        btn_sel.clicked.connect(self.on_select)
        row2.addWidget(btn_del)
        row2.addStretch(1)
        row2.addWidget(btn_sel)
        root.addLayout(row2)

        self.hint = QLabel("")
        self.hint.setObjectName("dlgHint")
        root.addWidget(self.hint)

        btn_close = FxButton("Закрыть", kind="ghost", w_=412, h_=40, radius=12,
                             px=13, svg_w=600)
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close)

        self.reload()

    def _dlg_qss(self):
        return """
            QDialog { background: #1a0c16; }
            QLabel#dlgTitle { color: #fff8f2; font-size: 20px; font-weight: 700; }
            QLabel#dlgSub { color: #b9a3b4; font-size: 12px; }
            QLabel#dlgHint { color: #ff4d6d; font-size: 12px; min-height: 16px; }
            QLineEdit#dlgEdit {
                background: #1c1024; border: 1px solid rgba(255,255,255,0.13);
                border-radius: 10px; padding: 8px 12px; color: #fff8f2;
                font-size: 14px; selection-background-color: #ffb703;
                selection-color: #1a0a10;
            }
            QLineEdit#dlgEdit:focus { border: 1px solid #ffb703; }
            QListWidget#acctList {
                background: #120910; border: 1px solid rgba(255,255,255,0.09);
                border-radius: 12px; padding: 6px; color: #fff8f2;
                font-size: 14px; outline: none;
            }
            QListWidget#acctList::item { padding: 10px 12px; border-radius: 8px; }
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
        # подсветить активный
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
    ("play", "Играть", theme.ICON_PLAY),
    ("skins", "Скины", theme.ICON_SKIN),
    ("settings", "Настройки", theme.ICON_GEAR_SM),
]


class Sidebar(QWidget):
    nav_clicked = pyqtSignal(str)
    gear_clicked = pyqtSignal()

    def __init__(self, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.setFixedSize(round(280 * k), round(1036 * k))
        self._account = {"name": "Exeyta"}
        self._nav = {}
        self._build()

    def _build(self):
        k = self.k
        from .controls import NavButton
        ys = {"home": 126, "play": 184, "skins": 242, "settings": 300}
        for key, label, icon in NAV_ITEMS:
            btn = NavButton(label, icon, k=k, parent=self)
            btn.move(round(24 * k), round(ys[key] * k))
            btn.clicked.connect(lambda kk=key: self.nav_clicked.emit(kk))
            self._nav[key] = btn

        self.tg = TelegramButton(k=k, parent=self)
        self.tg.move(round(24 * k), round(408 * k))
        self.tg.clicked.connect(self._open_telegram)

        # «Скачать текстурпак» — ссылка на каталог ресурс-паков
        pack_icon = theme.icon_pixmap(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'width="24" height="24"><path d="%s" fill="none" stroke="@COLOR@" '
            'stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"'
            '/></svg>' % theme.ICON_PACK, round(20 * k), "#ffe7b0")
        self.btn_packs = FxButton(
            "Скачать текстурпак", kind="chip",
            w_=round(232 * k), h_=round(50 * k), radius=16,
            px=14, svg_w=700, icon=pack_icon, gap=10,
            tooltip=theme.RESOURCE_PACKS_URL, parent=self)
        self.btn_packs.move(round(24 * k), round(470 * k))
        self.btn_packs.clicked.connect(self._open_resource_packs)

        gear_svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
                    'width="24" height="24"><path d="%s" fill="#ffe7b0"/></svg>'
                    % theme.ICON_GEAR)
        self.gear = FxButton("", kind="chip", w_=round(36 * k),
                             h_=round(36 * k), radius=12,
                             icon=theme.icon_pixmap(gear_svg, round(24 * k)),
                             tooltip="Управление offline-аккаунтами",
                             parent=self)
        self.gear.move(round(208 * k), round(962 * k))
        self.gear.clicked.connect(self.gear_clicked.emit)

    def _open_telegram(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        url = self.tg._url or theme.TELEGRAM_URL
        QDesktopServices.openUrl(QUrl(url))

    def _open_resource_packs(self):
        """Открывает каталог текстурпаков в браузере пользователя."""
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

        # контур сайдбара: скруглены ЛЕВЫЕ углы (28), правый край прямой
        r28 = 28 * k
        contour = QPainterPath()
        contour.moveTo(w_, 0)
        contour.lineTo(r28, 0)
        contour.arcTo(0, 0, 2 * r28, 2 * r28, 270, -90)
        contour.lineTo(0, h_ - r28)
        contour.arcTo(0, h_ - 2 * r28, 2 * r28, 2 * r28, 180, -90)
        contour.lineTo(w_, h_)
        contour.closeSubpath()
        p.setClipPath(contour)

        # фон: side-градиент
        g = QLinearGradient(0, 0, w_, h_)
        g.setColorAt(0.0, QColor("#24122c"))
        g.setColorAt(1.0, QColor("#100810"))
        p.fillRect(self.rect(), g)

        # верхняя полоска 3px sunH (продолжение полоски окна)
        strip = QRectF(0, 0, w_, 3 * k)
        sg = QLinearGradient(strip.left(), strip.top(),
                             strip.right(), strip.top())
        sg.setColorAt(0.0, QColor("#ffb703"))
        sg.setColorAt(1.0, QColor("#ff4d6d"))
        p.fillRect(strip, sg)

        # разделитель справа (#ffffff 6%)
        p.setPen(QPen(QColor(255, 255, 255, 16)))
        p.drawLine(w_ - 1, 0, w_ - 1, h_)

        # логотип 42x42 r13 (солнечный градиент) + E
        lr = QRectF(30 * k, 36 * k, 42 * k, 42 * k)
        sg = QLinearGradient(lr.topLeft(), lr.bottomRight())
        sg.setColorAt(0.0, QColor("#ffe08a"))
        sg.setColorAt(0.42, QColor("#ff8a3d"))
        sg.setColorAt(1.0, QColor("#ff4d88"))
        p.setPen(Qt.NoPen)
        p.setBrush(sg)
        p.drawRoundedRect(lr, 13 * k, 13 * k)
        ef = theme.font(22 * k, w(800))
        p.setFont(ef)
        p.setPen(QColor("#1a0a10"))
        p.drawText(lr, Qt.AlignCenter, "E")

        # EXEYTA — градиентный текст через путь (addText -> fill градиентом)
        xf = theme.font(26 * k, w(800))
        x = 86 * k
        base_y = 56 * k
        tpath = QPainterPath()
        tpath.addText(x, base_y, xf, "EXEYTA")
        br = tpath.boundingRect()
        tg = QLinearGradient(br.topLeft(), br.bottomRight())
        tg.setColorAt(0.0, QColor("#ffe08a"))
        tg.setColorAt(0.5, QColor("#ff8a3d"))
        tg.setColorAt(1.0, QColor("#ff4d88"))
        p.setPen(Qt.NoPen)
        p.setBrush(tg)
        p.drawPath(tpath)

        lf = theme.font(10 * k, w(500))
        lf.setLetterSpacing(QFont.AbsoluteSpacing, 3.2 * k)
        draw_base(p, x, 76 * k, "LAUNCHER", lf, "#c9a8b8", wide=round(170 * k))

        # СООБЩЕСТВО
        cf = theme.font(11 * k, w(500))
        cf.setLetterSpacing(QFont.AbsoluteSpacing, 1.8 * k)
        draw_base(p, 32 * k, 390 * k, "СООБЩЕСТВО", cf, "#8d7084",
                  wide=round(200 * k))

        # карточка аккаунта 232x70 r16
        ar = QRectF(24 * k, 946 * k, 232 * k, 70 * k)
        p.setBrush(QColor("#1c1024"))
        p.setPen(QPen(QColor("#14ffffff")))
        p.drawRoundedRect(ar, 16 * k, 16 * k)

        # аватар: кольцо sun + лицо + волосы
        cx, cy = 58 * k, 981 * k
        ring = QLinearGradient(cx - 20 * k, cy - 20 * k, cx + 20 * k, cy + 20 * k)
        ring.setColorAt(0.0, QColor("#ffe08a"))
        ring.setColorAt(0.42, QColor("#ff8a3d"))
        ring.setColorAt(1.0, QColor("#ff4d88"))
        p.setBrush(QColor("#e8c49a"))
        p.setPen(QPen(ring, 2 * k))
        p.drawEllipse(QPointF(cx, cy), 20 * k, 20 * k)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#4a3728"))
        p.drawRoundedRect(QRectF(cx - 10 * k, cy - 9 * k, 20 * k, 7 * k),
                          2 * k, 2 * k)

        # ник + статус Premium Offline
        name = (self._account or {}).get("name") or "Exeyta"
        draw_base(p, 86 * k, 976 * k, name, theme.font(14 * k, w(700)),
                  "#fff8f2", wide=round(120 * k))
        draw_base(p, 86 * k, 996 * k, "Premium Offline",
                  theme.font(11 * k, w(500)), "#ffb703", wide=round(130 * k))
        p.end()
