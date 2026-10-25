# -*- coding: utf-8 -*-
"""Общая тема Exeyta (лаунчер + установщик).

Единственный источник цветовых токенов и помощников рисования.
Соответствует визуальному источнику правды: assets/launcher-ui.svg
(viewBox 28 22 1864 1036, rx окна 28).
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
    # bg: #100710 -> #1a0c16 -> #2a1220
    "bg": ["#100710", "#1a0c16", "#2a1220"],
    # side: #24122c -> #100810
    "side": ["#24122c", "#100810"],
    # card: #3a2148 -> #24142e -> #140c1a
    "card": ["#3a2148", "#24142e", "#140c1a"],
    # sun: #ffe08a -> #ff8a3d -> #ff4d88
    "sun": ["#ffe08a", "#ff8a3d", "#ff4d88"],
    # sunH: #ffb703 -> #ff4d6d
    "sunH": ["#ffb703", "#ff4d6d"],
    "text": "#fff8f2",
    "muted": ["#b9a3b4", "#c9a8b8", "#8d7084"],
    "gold": ["#ffb703", "#ffe7b0"],
    "pink": ["#ffd0e0", "#ff4d88"],
    "success": "#86efac",
    "telegram": "#2AABEE",
    "stroke": ["#14ffffff", "#18ffffff", "#10ffffff"],
    "ink": "#1a0a10",          # тёмный текст на солнечных кнопках
    "panel_dark": "#120910",   # плашки внутри карточек
    "panel_deep": "#100810",   # плашки настроек / инструментов
    "chip": "#2a1834",
    "well": "#1c1024",
    "stage": ["#5a2a48", "#0c0610"],
    "white": "#ffffff",
}

RADIUS_WINDOW = 28
RADIUS_CARD = 22
RADIUS_NAV = 14
SIDEBAR_W = 280
TOP_STRIP = 3
BASE_W = 1864
BASE_H = 1036
SHEEN_H = 56

FONT_FAMILY = "Segoe UI"
FONT_FALLBACK = "Arial"

TELEGRAM_URL = "https://t.me/exeyta"
# кнопка «Скачать текстурпак» в сайдбаре
RESOURCE_PACKS_URL = "https://minecraft-inside.ru/resource-packs/"


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
    """QFont с размером в пикселях (точное соответствие SVG)."""
    fam = family or _resolve_family()
    f = QFont(fam)
    f.setPixelSize(max(1, int(round(px))))
    # Qt5: 0..99 (Normal=50, DemiBold=63, Bold=75, Black=87)
    f.setWeight(int(weight))
    f.setItalic(italic)
    return f


def text_label(parent, x, baseline, px, w, text="", color=None, weight=500,
               align=None, family=None, h=None):
    """QLabel, позиционированный по baseline как текст в SVG.

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


def paint_card(painter, rect, radius=RADIUS_CARD, border="#18ffffff",
               sheen=True, sheen_h=SHEEN_H):
    """Карточка макета: градиент card + блик сверху + тонкая рамка."""
    painter.save()
    path = rounded_path(rect, radius)
    painter.setClipPath(path)
    painter.fillPath(path, card_gradient(rect))
    if sheen:
        sh = QRectF(rect.left(), rect.top(), rect.width(), sheen_h)
        grad = QLinearGradient(QPointF(sh.left(), sh.top()),
                               QPointF(sh.left(), sh.bottom()))
        grad.setColorAt(0.0, QColor(255, 255, 255, 36))
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


# Иконки из макета (24x24 сетка)
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
ICON_TELEGRAM = "M0 0 L38 8 L0 16 L10 8 Z"
# коробка/пакет ресурсов (для кнопки «Скачать текстурпак»)
ICON_PACK = ("M12 2 L21 6.5 V17.5 L12 22 L3 17.5 V6.5 Z "
             "M3 6.5 L12 11 M12 11 L21 6.5 M12 11 V22")
