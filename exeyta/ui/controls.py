# -*- coding: utf-8 -*-
"""Переиспользуемые контролы лаунчера (рисуются вручную).

Все размеры/координаты задаются в логических пикселях и умножаются
на масштаб окна k.
"""
from PyQt5.QtCore import (QRectF, Qt, QPropertyAnimation, pyqtSignal,
                          pyqtProperty)
from PyQt5.QtGui import (QColor, QFont, QFontMetricsF, QLinearGradient,
                         QPainter, QPainterPath, QPen, QPixmap)
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QWidget

from exeyta_shared import theme
from exeyta_shared.animations import (HoverFader, ease_out_cubic,
                                       finish_fade, safe_stop)


# ---------------------------------------------------------------------------
# Цвета / текст / масштаб
# ---------------------------------------------------------------------------
def lerp_color(a, b, t):
    ca, cb = QColor(a), QColor(b)
    t = max(0.0, min(1.0, float(t)))
    return QColor(
        round(ca.red() + (cb.red() - ca.red()) * t),
        round(ca.green() + (cb.green() - ca.green()) * t),
        round(ca.blue() + (cb.blue() - ca.blue()) * t),
        round(ca.alpha() + (cb.alpha() - ca.alpha()) * t),
    )


def w(svg_weight):
    """SVG font-weight -> Qt weight (Qt5: 0..99)."""
    if svg_weight >= 800:
        return 87
    if svg_weight >= 700:
        return 75
    if svg_weight >= 600:
        return 63
    return 50


def draw_base(p, x, baseline, text, font_, color, wide=800):
    """Рисует строку с базовой линией baseline (как text в SVG)."""
    p.setFont(font_)
    p.setPen(QColor(color))
    fm = QFontMetricsF(font_)
    y = baseline - fm.ascent()
    p.drawText(QRectF(x, y, wide, fm.height() + 2),
               Qt.AlignLeft | Qt.AlignTop, text)


def add_label(parent, k, x, baseline, px, svg_w, width, text="", color=None,
              align=None, family=None):
    """QLabel по координатам макета с масштабом k (weight — из SVG)."""
    return theme.text_label(
        parent, round(x * k), round(baseline * k), round(px * k),
        round(width * k), text=text, color=color, weight=w(svg_w),
        align=align, family=family)


def apply_glow(widget, color="#c9a45c", blur=24, alpha=90):
    """Мягкое свечение вокруг виджета."""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    c = QColor(color)
    c.setAlpha(alpha)
    eff.setColor(c)
    eff.setOffset(0, 0)
    widget.setGraphicsEffect(eff)


def rounded_path(r, rad):
    path = QPainterPath()
    path.addRoundedRect(QRectF(r), rad, rad)
    return path


# ---------------------------------------------------------------------------
# Панели
# ---------------------------------------------------------------------------
class PanelBox(QWidget):
    """Плоская тёмная плашка + тонкая рамка + опциональная полоса."""

    def __init__(self, w_, h_, radius=12, fill="#15161a", border="#16ffffff",
                 strip=False, parent=None):
        super().__init__(parent)
        self._fill = fill
        self._border = border
        self._radius = radius
        self._strip = strip
        self.setFixedSize(int(w_), int(h_))

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        rad = self._radius
        path = rounded_path(r, rad)
        p.fillPath(path, QColor(self._fill))
        if self._strip:
            p.save()
            p.setClipPath(path)
            strip = QRectF(r.left(), r.top(), 3, r.height())
            g = QLinearGradient(strip.topLeft(), strip.bottomLeft())
            g.setColorAt(0.0, QColor(theme.TOKENS["sunH"][0]))
            g.setColorAt(1.0, QColor(theme.TOKENS["sunH"][1]))
            p.fillRect(strip, g)
            p.restore()
        if self._border:
            pen = QPen(QColor(self._border))
            pen.setWidthF(1.0)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, rad, rad)
        p.end()


class CardPanel(QWidget):
    """Карточка: градиент card + лёгкий блик сверху + рамка."""

    def __init__(self, w_, h_, radius=14, border="#16ffffff", sheen=True,
                 parent=None):
        super().__init__(parent)
        self._radius = radius
        self._border = border
        self._sheen = sheen
        self.setFixedSize(int(w_), int(h_))

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        theme.paint_card(p, self.rect(), radius=self._radius,
                         border=self._border, sheen=self._sheen)
        p.end()


class ClickZone(QWidget):
    """Прозрачная зона клика внутри карточек."""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent;")

    def mousePressEvent(self, event):
        finish_fade(self)
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        event.accept()


# ---------------------------------------------------------------------------
# Кнопка с плавным hover (QPropertyAnimation, OutCubic)
# ---------------------------------------------------------------------------
class FxButton(QWidget):
    """Универсальная кнопка.

    kind:
      sun      — золотой градиент, тёмный текст (главное действие)
      ghost    — тёмная плашка + рамка, светлый текст
      chip     — плашка + золотая рамка, золотистый текст
      danger   — тёмно-красная плашка + красная рамка
      telegram — #2AABEE, белый текст
      plain    — прозрачный фон
    """

    clicked = pyqtSignal()

    def __init__(self, text="", kind="ghost", w_=100, h_=40, radius=10,
                 px=13, svg_w=600, letter=0.0, icon=None, glow=None,
                 layout="center", pad=0, gap=10, parent=None, tooltip=None):
        super().__init__(parent)
        self._text = text
        self._kind = kind
        self._radius = radius
        self._letter = float(letter)
        self._icon = icon              # QPixmap | None
        self._layout = layout          # 'center' | 'left'
        self._pad = pad
        self._gap = gap
        self._disabled = False
        self.setFixedSize(int(w_), int(h_))
        self._font = theme.font(px, w(svg_w))
        if self._letter:
            self._font.setLetterSpacing(QFont.AbsoluteSpacing, self._letter)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = HoverFader(self, ms=180)
        self._press = 0.0
        self._press_anim = None
        if tooltip:
            self.setToolTip(tooltip)
        if glow:
            apply_glow(self, glow, blur=22, alpha=90)

    @pyqtProperty(float)
    def pressT(self):
        return self._press

    @pressT.setter
    def pressT(self, v):
        self._press = float(v)
        self.update()

    def set_text(self, text):
        self._text = text
        self.update()

    def set_icon(self, icon):
        self._icon = icon
        self.update()

    def set_disabled(self, flag):
        self._disabled = bool(flag)
        self.setEnabled(not flag)
        self.update()

    # --- анимации ---------------------------------------------------------
    def _animate_press(self, value, ms=110):
        safe_stop(self._press_anim)
        anim = QPropertyAnimation(self, b"pressT")
        anim.setDuration(ms)
        anim.setStartValue(self._press)
        anim.setEndValue(float(value))
        ease_out_cubic(anim)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._press_anim = anim

    def enterEvent(self, event):
        self._hover.target(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover.target(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        finish_fade(self)
        if event.button() == Qt.LeftButton:
            self._animate_press(1.0, 90)
        super().mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        inside = self.rect().contains(event.pos())
        self._animate_press(0.0, 160)
        if event.button() == Qt.LeftButton and inside and not self._disabled:
            self.clicked.emit()
        super().mouseReleaseEvent(event)
        event.accept()

    # --- отрисовка --------------------------------------------------------
    def _colors(self, t):
        kind = self._kind
        if kind == "sun":
            return None, None
        if kind == "ghost":
            bg = lerp_color("#1c1d22", "#25262c", t)
            bd = lerp_color("#2a2b31", "#3a3b43", t)
            return bg, bd
        if kind == "chip":
            bg = lerp_color("#26272e", "#2f3037", t)
            return bg, QColor("#c9a45c")
        if kind == "telegram":
            return lerp_color("#2AABEE", "#4dc0f5", t), None
        if kind == "danger":
            bg = lerp_color("#26272e", "#3a2225", t)
            return bg, QColor("#d97a7a")
        return None, None

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = self._hover.hoverT
        pr = self._press
        inset = pr * 1.5
        r = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        rad = max(4.0, self._radius - inset * 0.5)

        if self._disabled:
            p.setOpacity(0.45)

        bg, bd = self._colors(t)
        if self._kind == "sun":
            grad = QLinearGradient(r.left(), r.top(), r.right(), r.bottom())
            s = theme.TOKENS["sun"]
            grad.setColorAt(0.0, QColor(s[0]))
            grad.setColorAt(0.42, QColor(s[1]))
            grad.setColorAt(1.0, QColor(s[2]))
            p.fillPath(rounded_path(r, rad), grad)
            if t > 0:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 255, 255, round(26 * t)))
                p.drawRoundedRect(r, rad, rad)
        elif bg is not None:
            p.fillPath(rounded_path(r, rad), bg)

        if bd is not None:
            pen = QPen(bd)
            pen.setWidthF(1.0)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, rad, rad)

        text_color = {"sun": "#1c1609", "ghost": "#eceef2",
                      "chip": "#e8cf9a", "telegram": "#ffffff",
                      "danger": "#e8b0b0"}.get(self._kind, "#eceef2")
        p.setFont(self._font)
        p.setPen(QColor(text_color))
        fm = QFontMetricsF(self._font)
        tw = fm.horizontalAdvance(self._text) if self._text else 0
        ih = 0
        icon_w = 0
        if self._icon is not None and not self._icon.isNull():
            icon_w = self._icon.width()
            ih = self._icon.height()
        if self._text and self._icon is not None:
            content_w = icon_w + (self._gap if self._layout == "center" else 8) + tw
        else:
            content_w = max(tw, icon_w)

        if self._layout == "left":
            x = r.left() + self._pad
        else:
            x = r.center().x() - content_w / 2.0

        if self._icon is not None and not self._icon.isNull():
            iy = r.center().y() - ih / 2.0
            p.drawPixmap(QRectF(x, iy, icon_w, ih).toRect(), self._icon)
            x += icon_w + (self._gap if self._layout == "center" else 8)

        if self._text:
            p.setPen(QColor(text_color))
            y = r.center().y() - (fm.ascent() + fm.descent()) / 2.0
            p.drawText(QRectF(x, y, tw + 4, fm.height()),
                       Qt.AlignLeft | Qt.AlignTop, self._text)
        p.end()


class NavButton(QWidget):
    """Пункт навигации сайдбара: 200x44, r9.

    Активный пункт: мягкая золотая подложка, золотая иконка и текст.
    """

    clicked = pyqtSignal()

    def __init__(self, text, icon_svg, k=1.0, parent=None):
        super().__init__(parent)
        self._text = text
        self._icon_svg = icon_svg
        self.k = float(k)
        self._checked = False
        self.setFixedSize(round(200 * k), round(44 * k))
        self.setCursor(Qt.PointingHandCursor)
        self._hover = HoverFader(self, ms=180)
        self._icon_cache = None
        self._icon_key = None

    def set_checked(self, flag):
        flag = bool(flag)
        if flag != self._checked:
            self._checked = flag
            self.update()

    def checked(self):
        return self._checked

    def _icon(self):
        k = self.k
        color = "#d8b56e" if self._checked else "#8b8f98"
        if not self._checked and self._hover.hoverT > 0.02:
            color = lerp_color("#8b8f98", "#dfe2e8", self._hover.hoverT).name()
        key = (color, round(k, 2))
        if self._icon_key != key:
            self._icon_cache = theme.icon_pixmap(
                self._icon_svg, round(18 * k), color, stroke=1.7)
            self._icon_key = key
        return self._icon_cache

    def enterEvent(self, event):
        self._hover.target(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover.target(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        finish_fade(self)
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        was = getattr(self, "_pressed", False)
        self._pressed = False
        self.update()
        if was and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)
        event.accept()

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        t = self._hover.hoverT
        pressed = getattr(self, "_pressed", False)

        if self._checked:
            p.fillPath(rounded_path(r, 9 * k), QColor(201, 164, 92, 28))
            pen = QPen(QColor(201, 164, 92, 110))
            pen.setWidthF(1.0)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 9 * k, 9 * k)
        else:
            alpha = round((5 if pressed else 0) + 7 * t)
            if alpha > 0:
                p.fillPath(rounded_path(r, 9 * k), QColor(255, 255, 255, alpha))

        icon = self._icon()
        if icon is not None:
            p.drawPixmap(round(13 * k), round((44 * k - icon.height()) / 2.0),
                         icon)

        f = theme.font(14 * k, 63 if self._checked else 50)
        color = "#e8cf9a" if self._checked else "#b6bac2"
        draw_base(p, 42 * k, 27 * k, self._text, f, color,
                  wide=round(150 * k))
        p.end()


class GradientSlider(QWidget):
    """Слайдер-полоса: тёмный трек + золотая заливка (r3, h5)."""

    valueChanged = pyqtSignal(int)

    def __init__(self, min_v, max_v, step, value, w_, k=1.0, h=6, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.min_v = int(min_v)
        self.max_v = int(max_v)
        self.step = max(1, int(step))
        self._value = int(value)
        self.setFixedSize(round(w_ * k), round(18 * k))
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._hover = HoverFader(self, ms=160)

    def value(self):
        return self._value

    def set_value(self, v, emit=True):
        v = int(v)
        v = self.min_v + round((v - self.min_v) / self.step) * self.step
        v = max(self.min_v, min(self.max_v, v))
        if v != self._value:
            self._value = v
            self.update()
            if emit:
                self.valueChanged.emit(v)

    def _frac(self):
        span = float(self.max_v - self.min_v) or 1.0
        return (self._value - self.min_v) / span

    def _set_from_pos(self, x):
        left, right = 0.0, float(self.width())
        frac = 0.0 if right <= left else (x - left) / (right - left)
        frac = max(0.0, min(1.0, frac))
        self.set_value(self.min_v + frac * (self.max_v - self.min_v))

    def enterEvent(self, event):
        self._hover.target(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover.target(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        finish_fade(self)
        if event.button() == Qt.LeftButton:
            self._set_from_pos(event.x())
        super().mousePressEvent(event)
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._set_from_pos(event.x())
        super().mouseMoveEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        event.accept()

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        th = max(3.0, 5 * k)
        r = QRectF(0, (self.height() - th) / 2.0, self.width(), th)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2a2b31"))
        p.drawRoundedRect(r, th / 2, th / 2)
        fw = r.width() * self._frac()
        if fw > 0.5:
            fr = QRectF(r.left(), r.top(), fw, r.height())
            g = QLinearGradient(fr.left(), 0, fr.right(), 0)
            g.setColorAt(0.0, QColor("#a8843c"))
            g.setColorAt(1.0, QColor("#d3b06a"))
            p.setBrush(g)
            p.drawRoundedRect(fr, th / 2, th / 2)
            t = self._hover.hoverT
            if t > 0:
                p.setBrush(QColor(255, 255, 255, round(30 * t)))
                p.drawRoundedRect(fr, th / 2, th / 2)
        # ручка
        cx = r.left() + fw
        p.setBrush(QColor("#e8cf9a"))
        p.setPen(QPen(QColor("#141519"), 2))
        p.drawEllipse(QRectF(cx - 5 * k, r.center().y() - 5 * k,
                             10 * k, 10 * k))
        p.end()


class ToggleSwitch(QWidget):
    """Переключатель 40x22 (r11): золотой вкл / тёмный выкл."""

    toggled = pyqtSignal(bool)

    def __init__(self, on=False, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self.setFixedSize(round(40 * k), round(22 * k))
        self.setCursor(Qt.PointingHandCursor)
        self._on = bool(on)
        self._t = 1.0 if on else 0.0
        self._anim = None

    @pyqtProperty(float)
    def t(self):
        return self._t

    @t.setter
    def t(self, v):
        self._t = float(v)
        self.update()

    def is_on(self):
        return self._on

    def set_on(self, on, emit=True):
        on = bool(on)
        if on == self._on:
            return
        self._on = on
        safe_stop(self._anim)
        anim = QPropertyAnimation(self, b"t")
        anim.setDuration(180)
        anim.setStartValue(self._t)
        anim.setEndValue(1.0 if on else 0.0)
        ease_out_cubic(anim)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._anim = anim
        if emit:
            self.toggled.emit(on)

    def mousePressEvent(self, event):
        finish_fade(self)
        if event.button() == Qt.LeftButton:
            self.set_on(not self._on)
        super().mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        event.accept()

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        r = QRectF(self.rect())
        rad = r.height() / 2.0
        t = self._t
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2a2b31"))
        p.drawRoundedRect(r, rad, rad)
        if t > 0.02:
            g = QLinearGradient(r.left(), r.top(), r.right(), r.top())
            g.setColorAt(0.0, QColor("#a8843c"))
            g.setColorAt(1.0, QColor("#d3b06a"))
            p.setBrush(g)
            p.setOpacity(t)
            p.drawRoundedRect(r, rad, rad)
            p.setOpacity(1.0)
        knob_r = 8 * k
        pad = (r.height() - knob_r * 2) / 2.0
        cx = r.left() + pad + t * (r.width() - knob_r * 2 - pad * 2) + knob_r
        p.setBrush(QColor("#f2efe6" if t > 0.5 else "#c7cad1"))
        p.drawEllipse(QRectF(cx - knob_r, r.center().y() - knob_r,
                             knob_r * 2, knob_r * 2))
        p.end()


class ToolButton(QWidget):
    """Инструмент редактора скина: 52x46, r10."""

    clicked = pyqtSignal()

    def __init__(self, icon_svg, k=1.0, viewBox="0 0 30 30", parent=None):
        super().__init__(parent)
        self.k = float(k)
        self._icon_svg = icon_svg
        self._viewBox = viewBox
        self._checked = False
        self.setFixedSize(round(52 * k), round(46 * k))
        self.setCursor(Qt.PointingHandCursor)
        self._hover = HoverFader(self, ms=160)
        self._pm = None
        self._key = None

    def set_checked(self, flag):
        flag = bool(flag)
        if flag != self._checked:
            self._checked = flag
            self.update()

    def checked(self):
        return self._checked

    def _icon(self):
        color = "#e8cf9a" if self._checked else "#c7cad1"
        if not self._checked and self._hover.hoverT > 0.02:
            color = lerp_color("#c7cad1", "#eceef2", self._hover.hoverT).name()
        key = (color, self._viewBox, self._icon_svg)
        if self._key != key:
            size = round(28 * self.k)
            svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s" '
                   'width="%d" height="%d"><path d="%s" fill="none" '
                   'stroke="%s" stroke-width="1.7" stroke-linecap="round" '
                   'stroke-linejoin="round"/></svg>'
                   % (self._viewBox, size, size, self._icon_svg, color))
            self._pm = theme.icon_pixmap(svg, size)
            self._key = key
        return self._pm

    def enterEvent(self, event):
        self._hover.target(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover.target(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        super().mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        was = getattr(self, "_pressed", False)
        self._pressed = False
        if was and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)
        event.accept()

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        t = self._hover.hoverT
        if self._checked:
            p.fillPath(rounded_path(r, 10 * k), QColor(201, 164, 92, 30))
            pen = QPen(QColor(201, 164, 92, 120))
            pen.setWidthF(1.0)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 10 * k, 10 * k)
        else:
            bg = lerp_color("#1c1d22", "#25262c", t)
            p.setPen(Qt.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(r, 10 * k, 10 * k)
        icon = self._icon()
        if icon is not None:
            x = (self.width() - icon.width()) / 2.0
            y = (self.height() - icon.height()) / 2.0
            p.drawPixmap(round(x), round(y), icon)
        p.end()


class PaletteSwatch(QWidget):
    """Кружок палитры r10 (выбран — светлая обводка)."""

    clicked = pyqtSignal(str)

    def __init__(self, color_hex, k=1.0, parent=None):
        super().__init__(parent)
        self.k = float(k)
        self._color = color_hex
        self._selected = False
        size = round(26 * k)
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)

    def set_selected(self, flag):
        flag = bool(flag)
        if flag != self._selected:
            self._selected = flag
            self.update()

    def color_hex(self):
        return self._color

    def mousePressEvent(self, event):
        finish_fade(self)
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._color)
        super().mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        event.accept()

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        cx, cy = self.width() / 2.0, self.height() / 2.0
        if self._selected:
            p.setPen(QPen(QColor("#eceef2"), max(1.5, 2 * k)))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(cx - 13 * k, cy - 13 * k, 26 * k, 26 * k))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self._color))
        p.drawEllipse(QRectF(cx - 10 * k, cy - 10 * k, 20 * k, 20 * k))
        p.end()


class Badge(QWidget):
    """Небольшой статусный бейдж (например, «готова»)."""

    def __init__(self, text="", k=1.0, color="#c9a45c", parent=None):
        super().__init__(parent)
        self.k = float(k)
        self._text = text
        self._color = QColor(color)
        fm = QFontMetricsF(theme.font(11 * k, 63))
        self.setFixedSize(round(fm.horizontalAdvance(text) + 22 * k),
                          round(22 * k))

    def set_text(self, text):
        self._text = text
        fm = QFontMetricsF(theme.font(11 * self.k, 63))
        self.setFixedWidth(round(fm.horizontalAdvance(text) + 22 * self.k))
        self.update()

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        c = QColor(self._color)
        fill = QColor(c)
        fill.setAlpha(38)
        p.setBrush(fill)
        border = QColor(c)
        border.setAlpha(150)
        p.setPen(QPen(border, 1.0))
        p.drawRoundedRect(r, 6 * k, 6 * k)
        f = theme.font(11 * k, 63)
        p.setFont(f)
        p.setPen(c)
        p.drawText(r, Qt.AlignCenter, self._text)
        p.end()
