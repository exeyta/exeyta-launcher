# -*- coding: utf-8 -*-
"""Общая тема Exeyta (лаунчер + установщик).

Единственный источник цветовых токенов и помощников рисования.

Тема 2026: спокойный тёмно-графитовый интерфейс с приглушённым
золотисто-жёлтым акцентом (не неоновым). Акцент используется только
для главного действия, выбранного пункта меню и небольших деталей.
"""
from PyQt5.QtCore import QPointF, QRectF, QSize, Qt
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt5.QtSvg import QSvgRenderer

# ---------------------------------------------------------------------------
# Токены
# ---------------------------------------------------------------------------
TOKENS = {
    # bg: #141519 -> #17181d -> #1a1b20
    "bg": ["#141519", "#17181d", "#1a1b20"],
    # side: #121317 -> #0e0f12
    "side": ["#121317", "#0e0f12"],
    # card: #202127 -> #1b1c21 -> #18191d
    "card": ["#202127", "#1b1c21", "#18191d"],
    # sun: приглушённый золотой градиент
    "sun": ["#ddc27e", "#c9a45c", "#a8843c"],
    # sunH: основной акцент (мягкое золото)
    "sunH": ["#d3b06a", "#b08c44"],
    "text": "#eceef2",
    "muted": ["#9a9ea7", "#8b8f98", "#6f737c"],
    "gold": ["#c9a45c", "#e8cf9a"],
    "pink": ["#e8cf9a", "#c9a45c"],       # прежний «розовый» акцент
    "success": "#7fbf8f",
    "danger": "#d97a7a",
    "telegram": "#2AABEE",
    "stroke": ["#16ffffff", "#1affffff", "#12ffffff"],
    "ink": "#1c1609",                      # тёмный текст на золотых кнопках
    "panel_dark": "#15161a",               # плашки внутри карточек
    "panel_deep": "#121317",               # плашки настроек / инструментов
    "chip": "#26272e",
    "well": "#1c1d22",
    "stage": ["#3a3020", "#0f1013"],
    "white": "#ffffff",
    # семантические алиасы для нового интерфейса
    "accent": "#c9a45c",
    "accent_hover": "#d8b56e",
    "accent_soft": "#1fc9a45c",
    "border": "#2a2b31",
    "border_soft": "#232429",
}

RADIUS_WINDOW = 12
RADIUS_CARD = 14
RADIUS_NAV = 9
SIDEBAR_W = 232
TOP_STRIP = 0
BASE_W = 1440
BASE_H = 900
SHEEN_H = 40

FONT_FAMILY = "Segoe UI"
FONT_FALLBACK = "Arial"

TELEGRAM_URL = "https://t.me/exeyta"
# кнопка «Скачать текстурпак» в сайдбаре
RESOURCE_PACKS_URL = "https://minecraft-inside.ru/resource-packs/"
LAUNCHER_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# Шрифты
# ---------------------------------------------------------------------------
_FAMILY = None


def _resolve_family():
    """Segoe UI, fallback Arial; кэшируется, устойчиво к пустой font DB."""
    global _FAMILY
    if _FAMILY is None:
        try:
            from PyQt5.QtGui import QFontDatabase
            fams = QFontDatabase().families()
            if FONT_FAMILY in fams:
                _FAMILY = FONT_FAMILY
            elif FONT_FALLBACK in fams:
                _FAMILY = FONT_FALLBACK
            elif fams:
                _FAMILY = fams[0]
            else:
                _FAMILY = FONT_FAMILY
        except Exception:
            _FAMILY = FONT_FAMILY
    return _FAMILY


def font(px, weight=500, family=None, italic=False):
    """QFont с размером в пикселях (точное соответствие макету)."""
    fam = family or _resolve_family()
    f = QFont(fam)
    f.setPixelSize(max(1, int(round(px))))
    # Qt5: 0..99 (Normal=50, DemiBold=63, Bold=75, Black=87)
    f.setWeight(int(weight))
    f.setItalic(italic)
    return f


def text_label(parent, x, baseline, px, w, text="", color=None, weight=500,
               align=None, family=None, h=None):
    """QLabel, позиционированный по baseline как текст в макете.

    Геометрия подбирается через QFontMetrics, поэтому базовая линия
    совпадает с макетом независимо от метрик шрифта.
    """
    from PyQt5.QtWidgets import QLabel

    f = font(px, weight, family)
    fm = QFontMetricsF(f)
    if h is None:
        h = int(round(fm.height())) + 2
    y = int(round(baseline - fm.ascent())) - 1
    lbl = QLabel(text, parent)
    lbl.setGeometry(int(x), y, int(w), int(h))
    lbl.setFont(f)
    palette = lbl.palette()
    palette.setColor(lbl.foregroundRole(), QColor(color or TOKENS["text"]))
    lbl.setPalette(palette)
    lbl.setAttribute(Qt.WA_TranslucentBackground, True)
    if align is None:
        align = Qt.AlignLeft | Qt.AlignVCenter
    lbl.setAlignment(align)
    lbl.setWordWrap(False)
    return lbl


# ---------------------------------------------------------------------------
# Градиенты
# ---------------------------------------------------------------------------
def bg_gradient(w, h):
    g = QLinearGradient(0, 0, w, h)
    stops = TOKENS["bg"]
    g.setColorAt(0.0, QColor(stops[0]))
    g.setColorAt(0.45, QColor(stops[1]))
    g.setColorAt(1.0, QColor(stops[2]))
    return g


def side_gradient(w, h):
    g = QLinearGradient(0, 0, w, h)
    s = TOKENS["side"]
    g.setColorAt(0.0, QColor(s[0]))
    g.setColorAt(1.0, QColor(s[1]))
    return g


def card_gradient(rect):
    g = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
    c = TOKENS["card"]
    g.setColorAt(0.0, QColor(c[0]))
    g.setColorAt(0.22, QColor(c[1]))
    g.setColorAt(1.0, QColor(c[2]))
    return g


def sun_gradient(rect):
    g = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
    s = TOKENS["sun"]
    g.setColorAt(0.0, QColor(s[0]))
    g.setColorAt(0.42, QColor(s[1]))
    g.setColorAt(1.0, QColor(s[2]))
    return g


def sunh_gradient(rect):
    g = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
    s = TOKENS["sunH"]
    g.setColorAt(0.0, QColor(s[0]))
    g.setColorAt(1.0, QColor(s[1]))
    return g


def stage_gradient(rect):
    g = QLinearGradient(rect.center().x(), rect.top() + rect.height() * 0.4,
                        rect.center().x(), rect.bottom())
    s = TOKENS["stage"]
    g.setColorAt(0.0, QColor(s[0]))
    g.setColorAt(1.0, QColor(s[1]))
    return g


# ---------------------------------------------------------------------------
# Рисование
# ---------------------------------------------------------------------------
def rounded_path(rect, radius):
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect), radius, radius)
    return path


def paint_card(painter, rect, radius=RADIUS_CARD, border="#16ffffff",
               sheen=True, sheen_h=SHEEN_H):
    """Карточка: мягкий градиент + едва заметный блик + тонкая рамка."""
    painter.save()
    path = rounded_path(rect, radius)
    painter.setClipPath(path)
    painter.fillPath(path, card_gradient(rect))
    if sheen:
        sh = QRectF(rect.left(), rect.top(), rect.width(), sheen_h)
        grad = QLinearGradient(QPointF(sh.left(), sh.top()),
                               QPointF(sh.left(), sh.bottom()))
        grad.setColorAt(0.0, QColor(255, 255, 255, 14))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(sh, grad)
    painter.restore()
    pen = QPen(QColor(border))
    pen.setWidthF(1.0)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(QRectF(rect), radius, radius)


def icon_pixmap(svg, size, color="#ffffff", stroke=1.6, fill="none"):
    """Рендерит SVG-фрагмент (path d=...) в QPixmap нужного размера."""
    w = int(size) if isinstance(size, (int, float)) else int(size.width())
    h = int(size) if isinstance(size, (int, float)) else int(size.height())
    if isinstance(size, (int, float)):
        w = h = int(size)
    body = svg.strip()
    if not body.lstrip().startswith("<"):
        body = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
                'width="24" height="24">'
                '<path d="%s" fill="%s" stroke="%s" stroke-width="%s" '
                'stroke-linejoin="round" stroke-linecap="round"/></svg>'
                % (body, fill, color, stroke))
    else:
        body = body.replace("@COLOR@", color).replace("@STROKE@", str(stroke))
    renderer = QSvgRenderer()
    renderer.load(body.encode("utf-8"))
    pm = QPixmap(w, h)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    renderer.render(p)
    p.end()
    return pm


# Иконки (24x24 сетка)
ICON_HOME = "M4 11 L12 4 L20 11 V20 H14 V14 H10 V20 H4 Z"
ICON_PLAY = "M8 5 L20 12 L8 19 Z"
ICON_SKIN = "M12 4 a4 4 0 1 1 0 8 a4 4 0 0 1 0-8 M5 20 c1-4 4-6 7-6 s6 2 7 6"
ICON_GEAR_SM = ("M12 8 a4 4 0 1 1 0 8 a4 4 0 0 1 0-8 M12 3 v2 M12 19 v2 "
                "M3 12 h2 M19 12 h2")
ICON_GEAR = ("M19.14 12.94c.04-.31.06-.63.06-.94s-.02-.63-.06-.94l2.03-1.58a.49.49 "
             "0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96a7.1 7.1 0 0 "
             "0-1.62-.94l-.36-2.54a.48.48 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 "
             "2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.49.49 0 0 0-.59.22L2.74 8.87c-.12.21-.08.47.12 "
             ".61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 "
             "3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 "
             "0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.03-1.58zM12 "
             "15.6A3.6 3.6 0 1 1 12 8.4a3.6 3.6 0 0 1 0 7.2z")
ICON_PENCIL = "M8 26 L14 6 L22 14 Z"
ICON_BUCKET = "M7 20 L16 8 L22 14 L12 24 Z"
ICON_RECT = "M7 16 H21 V24 H7 Z"
ICON_ERASE = "M16 8 A8 8 0 1 0 18 20"
ICON_PLUS = "M14 8 V20 M8 14 H20"
ICON_MINUS = "M8 14 H20"
ICON_TELEGRAM = "M3 11 L21 3 L14 21 L10 13 Z M10 13 L21 3"
# коробка/пакет ресурсов (для кнопки «Скачать текстурпак»)
ICON_PACK = ("M12 2 L21 6.5 V17.5 L12 22 L3 17.5 V6.5 Z "
             "M3 6.5 L12 11 M12 11 L21 6.5 M12 11 V22")
# новые пункты навигации
ICON_VERSIONS = ("M12 3 L21 7.5 L12 12 L3 7.5 Z "
                 "M3 12 L12 16.5 L21 12 M3 16.5 L12 21 L21 16.5")
ICON_SLIDERS = ("M4 7 h10 M18 7 h2 M16 5 v4 "
                "M4 17 h2 M10 17 h10 M8 15 v4")
ICON_TERMINAL = "M5 7 l5 5 -5 5 M13 17 h6"
ICON_FOLDER = "M3 7 h7 l2 2 h9 v10 H3 Z"
ICON_STOP = "M7 7 h10 v10 H7 Z"
ICON_REFRESH = "M20 12 a8 8 0 1 0-2.4 5.7 M20 6 v5 h-5"
ICON_CHEVRON = "M8 10 l4 4 4-4"
ICON_USER = "M12 4 a4 4 0 1 1 0 8 a4 4 0 0 1 0-8 M5 20 c1-4 4-6 7-6 s6 2 7 6"
ICON_TRASH = "M5 7 h14 M9 7 V5 h6 v2 M7 7 l1 13 h8 l1-13"
