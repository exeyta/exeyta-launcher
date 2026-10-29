# -*- coding: utf-8 -*-
"""«Редактор скина» (1090x648, r22) — 1:1 с assets/launcher-ui.svg.

Слои автоматические (без селектора в редакторе):
  * импорт PNG авто-разбирается на базовый слой и слой-накладку
    (стандарт MC: шляпа/жилет/рукава/штанины);
  * правки маршрутизируются по атлас-региону: пиксель накладки пишется
    на слой накладки, остальное — на базу;
  * 3D показывает накладку отдельной геометрией (с припуском поверх
    базы), сохранение/экспорт — композит.
  * инструменты 76x448: P (карандаш), F (заливка), E (ластик), U (отмена),
    +/− (зум), «1 px»;
  * палитра 12 цветов (70x448);
  * UV-холст 512x448 (чекер-фон, текстура 64x64, сетка);
  * 3D 336x448 — вращение мышью, рендер ≤ 30 fps, без фонового таймера;
  * Сохранить / Импорт PNG / Экспорт / В игру.

Производительность: QPixmap-кэш масштабированной текстуры, repaint только
изменённого виджета, 3D перерисовывается только при вращении/правке скина.
"""
import time
from PyQt5.QtCore import (QPoint, QPointF, QRectF, Qt, QTimer, pyqtSignal)
from PyQt5.QtGui import (QColor, QFont, QFontMetricsF, QImage, QMouseEvent,
                         QPainter, QPainterPath, QPen, QPixmap, QPolygonF,
                         QTransform)
from PyQt5.QtWidgets import QWidget

from exeyta_shared import theme

from .controls import (CardPanel, FxButton, PaletteSwatch, PanelBox,
                       ToolButton, add_label, draw_base, rounded_path, w)

# Палитра из макета (12 цветов)
PALETTE = [
    "#ff4d4d", "#ff8a3d", "#ffd166", "#3ddc84",
    "#4cc9f0", "#7c6bff", "#ff4d88", "#f1c7a4",
    "#5c4033", "#1f2430", "#f7f4f2", "#3d6fbf",
]

ZOOMS = [4, 5, 6, 8, 10, 12]


# ---------------------------------------------------------------------------
# Скин 64x64
# ---------------------------------------------------------------------------
def make_default_skin() -> QImage:
    """Стартовый скин в цветах макета (кожа/волосы/рубашка/штаны)."""
    img = QImage(64, 64, QImage.Format_ARGB32)
    img.fill(Qt.transparent)

    def rect(x, y, ww, hh, color):
        c = QColor(color)
        for yy in range(y, y + hh):
            for xx in range(x, x + ww):
                img.setPixelColor(xx, yy, c)

    SKIN = "#f1c7a4"
    SKIN2 = "#e2b48f"
    HAIR = "#4a3728"
    SHIRT = "#3d7ee8"
    PANTS = "#2c3348"
    PANTS2 = "#3a4258"
    SHOE = "#1f2430"

    # Голова (uv 0,0): лицо/бока/затылок/макушка
    rect(8, 8, 8, 8, SKIN)     # лицо
    rect(0, 8, 8, 8, SKIN2)    # левый бок
    rect(16, 8, 8, 8, SKIN2)   # правый бок
    rect(24, 8, 8, 8, HAIR)    # затылок (волосы)
    rect(8, 0, 8, 8, HAIR)     # макушка
    rect(16, 0, 8, 8, SKIN)    # низ головы
    # чёлка + волосы по бокам
    rect(8, 8, 8, 3, HAIR)
    rect(0, 8, 8, 3, HAIR)
    rect(16, 8, 8, 3, HAIR)
    # глаза / рот
    rect(10, 11, 2, 1, "#ffffff")
    rect(13, 11, 2, 1, "#ffffff")
    rect(11, 11, 1, 1, "#3d6fbf")
    rect(14, 11, 1, 1, "#3d6fbf")
    rect(11, 13, 2, 1, "#d4897a")

    # Тело (uv 16,16)
    rect(20, 20, 8, 12, SHIRT)
    rect(16, 20, 4, 12, SHIRT)
    rect(28, 20, 4, 12, SHIRT)
    rect(32, 20, 8, 12, SHIRT)
    rect(20, 16, 8, 4, SHIRT)
    rect(28, 16, 8, 4, SHIRT)

    # Правая рука (uv 40,16) — кожа + рукав
    for x, y, ww, hh in [(44, 20, 4, 12), (40, 20, 4, 12), (48, 20, 4, 12),
                         (52, 20, 4, 12)]:
        rect(x, y, ww, hh, SKIN)
        rect(x, y, ww, 3, SHIRT)
    rect(44, 16, 4, 4, SHIRT)
    rect(48, 16, 4, 4, SHIRT)

    # Левая рука (uv 32,48) — темнее
    for x, y, ww, hh in [(36, 52, 4, 12), (32, 52, 4, 12), (40, 52, 4, 12),
                         (44, 52, 4, 12)]:
        rect(x, y, ww, hh, SKIN2)
        rect(x, y, ww, 3, SHIRT)
    rect(36, 48, 4, 4, SHIRT)
    rect(40, 48, 4, 4, SHIRT)

    # Правая нога (uv 0,16) — штаны + ботинки
    for x, y, ww, hh in [(4, 20, 4, 12), (0, 20, 4, 12), (8, 20, 4, 12),
                         (12, 20, 4, 12)]:
        rect(x, y, ww, hh, PANTS)
        rect(x, y + hh - 2, ww, 2, SHOE)
    rect(4, 16, 4, 4, PANTS)
    rect(8, 16, 4, 4, PANTS)

    # Левая нога (uv 16,48)
    for x, y, ww, hh in [(20, 52, 4, 12), (16, 52, 4, 12), (24, 52, 4, 12),
                         (28, 52, 4, 12)]:
        rect(x, y, ww, hh, PANTS2)
        rect(x, y + hh - 2, ww, 2, SHOE)
    rect(20, 48, 4, 4, PANTS2)
    rect(24, 48, 4, 4, PANTS2)
    return img


def normalize_skin(img: QImage) -> QImage:
    """Приводит PNG к 64x64 (легаси 64x32 -> расширение левых конечностей)."""
    if img.isNull():
        return make_default_skin()
    if img.width() == 64 and img.height() == 64:
        return img.convertToFormat(QImage.Format_ARGB32)
    if img.width() == 64 and img.height() == 32:
        out = QImage(64, 64, QImage.Format_ARGB32)
        out.fill(Qt.transparent)
        for y in range(32):
            for x in range(64):
                out.setPixelColor(x, y, img.pixelColor(x, y))
        # зеркалим правые конечности в левые
        def mirror(sx, sy, dx, dy, ww, hh):
            for yy in range(hh):
                for xx in range(ww):
                    out.setPixelColor(dx + xx, dy + yy,
                                      img.pixelColor(sx + xx, sy + yy))
        mirror(40, 16, 32, 48, 16, 16)   # рука
        mirror(0, 16, 16, 48, 16, 16)    # нога
        return out
    return img.scaled(64, 64, Qt.IgnoreAspectRatio,
                      Qt.FastTransformation).convertToFormat(QImage.Format_ARGB32)


# ---------------------------------------------------------------------------
# Слои скина (базовый + накладки, сколько угодно, максимум 6)
# ---------------------------------------------------------------------------
OVERLAY_RECTS = [
    (32, 0, 32, 16),    # шляпа (hat)
    (0, 32, 16, 16),    # правая нога — накладка
    (16, 32, 24, 16),   # тело/жилет — накладка
    (40, 32, 16, 16),   # правая рука — накладка
    (0, 48, 16, 16),    # левая нога — накладка
    (48, 48, 16, 16),   # левая рука — накладка
]


def blank_layer() -> QImage:
    img = QImage(64, 64, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    return img


def split_layers(img: QImage):
    """Делит стандартный 64x64 PNG на базовый слой и слой-накладку."""
    img = normalize_skin(img)
    base, ov = blank_layer(), blank_layer()
    rects = OVERLAY_RECTS
    for y in range(64):
        for x in range(64):
            c = img.pixelColor(x, y)
            if c.alpha() == 0:
                continue
            if any(rx <= x < rx + rw and ry <= y < ry + rh
                   for (rx, ry, rw, rh) in rects):
                ov.setPixelColor(x, y, c)
            else:
                base.setPixelColor(x, y, c)
    return base, ov


def compose_layers(layers) -> QImage:
    """Свёртка слоёв (снизу вверх) в итоговую текстуру 64x64."""
    out = blank_layer()
    p = QPainter(out)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    for layer in layers or []:
        if layer is not None and not layer.isNull():
            p.drawImage(0, 0, layer)
    p.end()
    return out


def make_default_layers():
    """Стартовый скин сразу в два слоя: база + видимая накладка (волосы)."""
    base, ov = split_layers(make_default_skin())

    def rect(x, y, ww, hh, color):
        col = QColor(color)
        for yy in range(y, y + hh):
            for xx in range(x, x + ww):
                if 0 <= xx < 64 and 0 <= yy < 64:
                    ov.setPixelColor(xx, yy, col)

    hair = "#4a3728"
    rect(40, 0, 8, 8, hair)     # макушка шляпы
    rect(40, 8, 8, 3, hair)     # чёлка
    rect(32, 8, 8, 3, hair)     # левый бок
    rect(48, 8, 8, 3, hair)     # правый бок
    rect(56, 8, 8, 8, hair)     # затылок
    return [base, ov]


# ---------------------------------------------------------------------------
# UV-холст
# ---------------------------------------------------------------------------
class CanvasWidget(QWidget):
    """UV-холст 512x448: чекер-фон + текстура 64x64 + сетка + надписи."""

    skin_changed = pyqtSignal()

    def __init__(self, editor, k=1.0, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.k = float(k)
        self.setFixedSize(round(512 * k), round(448 * k))
        self._zoom_idx = ZOOMS.index(6) if 6 in ZOOMS else 2
        self._checker = None
        self._tex_pm = None
        self._tex_dirty = True
        self._hover_texel = None
        self._drawing = False
        self._undo_stack = []

    # --- координаты текстуры ---------------------------------------------
    def _geom(self):
        """(left, top, cell) — позиция и размер текстуры на холсте."""
        k = self.k
        z = ZOOMS[self._zoom_idx] * k
        size = 64 * z
        inner_x, inner_y = 12 * k, 12 * k
        inner_w, inner_h = 488 * k, 424 * k
        x = inner_x + (inner_w - size) / 2.0
        y = inner_y + (inner_h - size) / 2.0
        return x, y, z, size

    def texel_at(self, pos):
        x, y, z, size = self._geom()
        if not (x <= pos.x() < x + size and y <= pos.y() < y + size):
            return None
        tx = int((pos.x() - x) // z)
        ty = int((pos.y() - y) // z)
        if 0 <= tx < 64 and 0 <= ty < 64:
            return tx, ty
        return None

    def zoom(self, delta):
        self._zoom_idx = max(0, min(len(ZOOMS) - 1, self._zoom_idx + delta))
        self._tex_dirty = True
        self.update()

    def zoom_label(self):
        return "%d px" % ZOOMS[self._zoom_idx]

    def invalidate(self):
        self._tex_dirty = True
        self.update()

    def push_undo(self):
        self._undo_stack.append(self.editor.snapshot())
        if len(self._undo_stack) > 40:
            del self._undo_stack[0]

    def undo(self):
        if self._undo_stack:
            self.editor.restore(self._undo_stack.pop())
            return True
        return False

    # --- текстура ----------------------------------------------------------
    def _tex_pixmap(self):
        if self._tex_dirty or self._tex_pm is None:
            k = self.k
            z = ZOOMS[self._zoom_idx] * k
            size = max(1, round(64 * z))
            pm = QPixmap(size, size)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.SmoothPixmapTransform, False)
            img = self.editor.skin()
            p.drawImage(pm.rect(), img, img.rect())
            p.end()
            self._tex_pm = pm
            self._tex_dirty = False
        return self._tex_pm

    def _checker_pixmap(self):
        if self._checker is None:
            k = self.k
            w_, h_ = round(488 * k), round(424 * k)
            pm = QPixmap(w_, h_)
            pm.fill(QColor("#1c1d22"))
            p = QPainter(pm)
            cell = round(8 * k)
            p.fillRect(0, 0, w_, h_, QColor("#1c1d22"))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#2a2b31"))
            rows = h_ // cell + 1
            cols = w_ // cell + 1
            for ry in range(rows):
                for cx in range(cols):
                    if (cx + ry) % 2 == 0:
                        p.drawRect(cx * cell, ry * cell, cell, cell)
            p.end()
            self._checker = pm
        return self._checker

    # --- мышь --------------------------------------------------------------
    def mousePressEvent(self, event):
        pos = event.pos()
        t = self.texel_at(pos)
        if t is None:
            event.accept()
            return
        tool = self.editor.tool()
        if tool in ("P", "E", "F"):
            self.push_undo()
        if tool == "F":
            self.editor.flood_fill(t[0], t[1])
            self.skin_changed.emit()
        elif tool in ("P", "E"):
            self._drawing = True
            self.editor.paint_texel(t[0], t[1])
            self.skin_changed.emit()
        self.update()
        event.accept()

    def mouseMoveEvent(self, event):
        t = self.texel_at(event.pos())
        if t != self._hover_texel:
            self._hover_texel = t
            self.update()
        if self._drawing and t is not None and self.editor.tool() in ("P", "E"):
            self.editor.paint_texel(t[0], t[1])
            self.skin_changed.emit()
            self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drawing = False
        event.accept()

    def leaveEvent(self, event):
        if self._hover_texel is not None:
            self._hover_texel = None
            self.update()
        super().leaveEvent(event)

    # --- отрисовка ---------------------------------------------------------
    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#101115"))
        p.drawRoundedRect(r, 16 * k, 16 * k)
        pen = QPen(QColor("#16ffffff"))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 16 * k, 16 * k)

        # чекер-фон (кэш)
        inner = QRectF(12 * k, 12 * k, 488 * k, 424 * k)
        p.save()
        p.setClipPath(rounded_path(inner, 12 * k))
        p.drawPixmap(inner.topLeft().toPoint(), self._checker_pixmap())

        # текстура (nearest)
        x, y, z, size = self._geom()
        pm = self._tex_pixmap()
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)
        p.drawPixmap(QRectF(x, y, size, size), pm, QRectF(pm.rect()))

        # сетка
        grid = QPen(QColor(255, 255, 255, 14))
        grid.setWidthF(1.0)
        p.setPen(grid)
        for i in range(65):
            gx = x + i * z
            p.drawLine(QPointF(gx, y), QPointF(gx, y + size))
            gy = y + i * z
            p.drawLine(QPointF(x, gy), QPointF(x + size, gy))
        grid.setColor(QColor(255, 255, 255, 30))
        p.setPen(grid)
        for i in range(0, 65, 8):
            gx = x + i * z
            p.drawLine(QPointF(gx, y), QPointF(gx, y + size))
            gy = y + i * z
            p.drawLine(QPointF(x, gy), QPointF(x + size, gy))

        # подсветка текселя
        if self._hover_texel is not None:
            tx, ty = self._hover_texel
            hl = QPen(QColor("#e8cf9a"))
            hl.setWidthF(max(1.5, 2 * k))
            p.setPen(hl)
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(x + tx * z, y + ty * z, z, z))
        p.restore()

        # надписи из макета (поверх, полупрозрачно)
        pink = QColor("#e8cf9a")
        pink.setAlpha(210)
        f = theme.font(12 * k, w(600))
        draw_base(p, 40 * k, 34 * k, "Голова", f, pink, wide=round(200 * k))
        draw_base(p, 40 * k, 296 * k, "Тело, руки, ноги", f, pink,
                  wide=round(260 * k))
        p.end()


# ---------------------------------------------------------------------------
# 3D-превью
# ---------------------------------------------------------------------------
# (name, u, v, w, h, d, x0, x1, y0, y1, z0, z1) — мировые координаты, y вверх.
# Персонаж смотрит в +z (на зрителя): char-left = +x, char-right = -x.
PARTS = [
    ("head", 0, 0, 8, 8, 8, -4, 4, 24, 32, -4, 4),
    ("body", 16, 16, 8, 12, 4, -4, 4, 12, 24, -2, 2),
    ("arm_r", 40, 16, 4, 12, 4, -8, -4, 12, 24, -2, 2),
    ("arm_l", 32, 48, 4, 12, 4, 4, 8, 12, 24, -2, 2),
    ("leg_r", 0, 16, 4, 12, 4, -4, 0, 0, 12, -2, 2),
    ("leg_l", 16, 48, 4, 12, 4, 0, 4, 0, 12, -2, 2),
]


# Накладки (слой поверх базы): те же коробки с припуском, свой UV из
# прямоугольников OVERLAY_RECTS — в 3D рисуются ПОВЕРХ базы, поэтому
# слои видны (шляпа, жилет, рукава, штанины).
OVERLAY_PARTS = [
    (32, 0, 8, 8, 8, -4, 4, 24, 32, -4, 4, 0.7),    # шляпа
    (16, 32, 8, 12, 4, -4, 4, 12, 24, -2, 2, 0.5),  # жилет
    (40, 32, 4, 12, 4, -8, -4, 12, 24, -2, 2, 0.5), # рукав правый
    (48, 48, 4, 12, 4, 4, 8, 12, 24, -2, 2, 0.5),   # рукав левый
    (0, 32, 4, 12, 4, -4, 0, 0, 12, -2, 2, 0.5),    # штанина правая
    (0, 48, 4, 12, 4, 0, 4, 0, 12, -2, 2, 0.5),     # штанина левая
]


def _uv_has_pixels(img, ux, uy, uw, uh) -> bool:
    """Есть ли непрозрачные пиксели в UV-прямоугольнике текстуры."""
    x0, y0 = int(ux), int(uy)
    x1, y1 = x0 + int(uw), y0 + int(uh)
    for yy in range(y0, y1):
        for xx in range(x0, x1):
            if 0 <= xx < 64 and 0 <= yy < 64:
                if img.pixelColor(xx, yy).alpha() > 0:
                    return True
    return False


class Preview3D(QWidget):
    """3D-модель скина: вращение мышью, рендер по требованию ≤30 fps."""

    def __init__(self, editor, k=1.0, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.k = float(k)
        self.setFixedSize(round(336 * k), round(448 * k))
        self.setCursor(Qt.OpenHandCursor)
        self._yaw = -0.35
        self._pitch = 0.10
        self._last_drag = None
        self._last_render = 0.0
        self._pending = False

    def set_skin(self, img):
        self.update()

    # --- вращение мышью (троттлинг 33ms -> ≤30 fps) -----------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._last_drag = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        if self._last_drag is not None and event.buttons() & Qt.LeftButton:
            dx = event.x() - self._last_drag.x()
            dy = event.y() - self._last_drag.y()
            self._last_drag = event.pos()
            self._yaw += dx * 0.012
            self._pitch = max(-0.55, min(0.55, self._pitch + dy * 0.008))
            self._throttled_update()
        event.accept()

    def mouseReleaseEvent(self, event):
        self._last_drag = None
        self.setCursor(Qt.OpenHandCursor)
        event.accept()

    def _throttled_update(self):
        now = time.monotonic()
        min_dt = 1.0 / 30.0
        dt = now - self._last_render
        if dt >= min_dt:
            self._last_render = now
            self.update()
        elif not self._pending:
            self._pending = True
            QTimer.singleShot(int(min_dt * 1000), self._late_update)

    def _late_update(self):
        self._pending = False
        self._last_render = time.monotonic()
        self.update()

    # --- рендер ------------------------------------------------------------
    def _rot(self, x, y, z):
        """Поворот вокруг Y (yaw), затем X (pitch)."""
        cy, sy = math_cos(self._yaw), math_sin(self._yaw)
        x1 = x * cy + z * sy
        z1 = -x * sy + z * cy
        cp, sp = math_cos(self._pitch), math_sin(self._pitch)
        y1 = y * cp - z1 * sp
        z2 = y * sp + z1 * cp
        return x1, y1, z2

    def paintEvent(self, event=None):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        # сцена (radial stage-градиент)
        from PyQt5.QtGui import QRadialGradient
        p.save()
        p.setClipPath(rounded_path(r, 16 * k))
        g = QRadialGradient(r.center().x(), r.top() + r.height() * 0.4,
                            r.height() * 0.65)
        g.setColorAt(0.0, QColor("#3a3020"))
        g.setColorAt(1.0, QColor("#101115"))
        p.fillRect(r, g)

        # свечение + тень под фигурой (из макета)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 138, 61, 46))
        p.drawEllipse(QPointF(168 * k, 376 * k), 78 * k, 16 * k)
        p.setBrush(QColor(0, 0, 0, 115))
        p.drawEllipse(QPointF(168 * k, 384 * k), 46 * k, 8 * k)

        self._draw_model(p)
        p.restore()

        # рамка
        pen = QPen(QColor("#16ffffff"))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 16 * k, 16 * k)

        # «3D»
        f = theme.font(12 * k, w(700))
        f.setLetterSpacing(QFont.AbsoluteSpacing, 2 * k)
        p.setFont(f)
        p.setPen(QColor("#e2e4e9"))
        p.drawText(QRectF(0, 16 * k, r.width(), 24 * k),
                   Qt.AlignHCenter | Qt.AlignTop, "3D")

        # плашка «вращение мышью»
        pill = QRectF(60 * k, 400 * k, 216 * k, 30 * k)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 68))
        p.drawRoundedRect(pill, 10 * k, 10 * k)
        p.setPen(QColor("#8b8f98"))
        p.setFont(theme.font(12 * k, w(500)))
        p.drawText(pill, Qt.AlignCenter, "вращение мышью")
        p.end()

    def _draw_model(self, p):
        img = self.editor.skin()
        scale = 8.0 * self.k
        anchor_x = 168 * self.k
        anchor_y = 322 * self.k   # ноги (как в макете: 446 svg -> 322 rel)

        # план: базовые коробки + геометрия накладок (слои видны в 3D)
        plan = [(u, v, bw, bh, bd, x0, x1, y0, y1, z0, z1, 0.0)
                for (_n, u, v, bw, bh, bd, x0, x1, y0, y1, z0, z1) in PARTS]
        plan += list(OVERLAY_PARTS)

        faces = []
        for u, v, bw, bh, bd, x0, x1, y0, y1, z0, z1, inf in plan:
            cx, cy, cz = (x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0
            hx = (x1 - x0) / 2.0 + inf
            hy = (y1 - y0) / 2.0 + inf
            hz = (z1 - z0) / 2.0 + inf
            corners = []
            for sx in (-1, 1):
                for sy in (-1, 1):
                    for sz in (-1, 1):
                        wx = cx + sx * hx - 0  # мировая
                        wy = cy + sy * hy
                        wz = cz + sz * hz
                        rx, ry, rz = self._rot(wx, wy - 0, wz)
                        sxp = anchor_x + rx * scale
                        syp = anchor_y - ry * scale
                        corners.append(((sx, sy, sz), (rx, ry, rz),
                                        QPointF(sxp, syp)))

            def pt(sx, sy, sz):
                for key, _r, q in corners:
                    if key == (sx, sy, sz):
                        return q
                return QPointF(0, 0)

            def depth(sx, sy, sz):
                for key, r3, _q in corners:
                    if key == (sx, sy, sz):
                        return r3[2]
                return 0.0

            # вершины каждой грани: [TL, TR, BR, BL] — как видно снаружи
            d, wd, hd = bd, bw, bh  # для uv-раскладки
            uv = {
                "top": (u + d, v, wd, d),
                "bottom": (u + d + wd, v, wd, d),
                "left": (u, v + d, d, hd),
                "front": (u + d, v + d, wd, hd),
                "right": (u + d + wd, v + d, d, hd),
                "back": (u + 2 * d + wd, v + d, wd, hd),
            }
            quads = [
                ("front", [(-1, 1, 1), (1, 1, 1), (1, -1, 1), (-1, -1, 1)],
                 (0, 0, 1)),
                ("back", [(1, 1, -1), (-1, 1, -1), (-1, -1, -1), (1, -1, -1)],
                 (0, 0, -1)),
                ("right", [(1, 1, 1), (1, 1, -1), (1, -1, -1), (1, -1, 1)],
                 (1, 0, 0)),
                ("left", [(-1, 1, -1), (-1, 1, 1), (-1, -1, 1), (-1, -1, -1)],
                 (-1, 0, 0)),
                ("top", [(-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1)],
                 (0, 1, 0)),
                ("bottom", [(1, -1, -1), (-1, -1, -1), (-1, -1, 1), (1, -1, 1)],
                 (0, -1, 0)),
            ]
            for face_name, verts, normal in quads:
                # отсечение: нормаль должна смотреть к зрителю (+Z)
                if self._rot_view_dot(normal) <= 0.0001:
                    continue
                rect_uv = uv[face_name]
                # и отсечение полностью прозрачных граней (накладка/пустота)
                if not _uv_has_pixels(img, *rect_uv):
                    continue
                pts = [pt(*vv) for vv in verts]
                dep = sum(depth(*vv) for vv in verts) / 4.0
                rnx, rny, rnz = self._rot(*normal)
                lx, ly, lz = self._norm(-0.35, -0.55, 0.75)
                lam = max(0.0, rnx * lx + rny * ly + rnz * lz)
                shade = 0.55 + 0.45 * lam
                faces.append((dep, pts, rect_uv, shade))

        faces.sort(key=lambda f: f[0])
        img_rect = QRectF(0, 0, 64, 64)
        for dep, pts, (ux, uy, uw, uh), shade in faces:
            if uw <= 0 or uh <= 0:
                continue
            self._draw_textured_face(p, img, img_rect, pts,
                                     QRectF(ux, uy, uw, uh))
            if shade < 0.999:
                poly = QPolygonF(pts)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0, 0, 0, round(255 * (1.0 - shade))))
                p.drawPolygon(poly)

    def _rot_view_dot(self, normal):
        """Скалярное произведение повёрнутой нормали на взгляд камеры (+Z)."""
        _x, _y, z = self._rot(*normal)
        return z

    @staticmethod
    def _norm(x, y, z):
        ln = (x * x + y * y + z * z) ** 0.5 or 1.0
        return x / ln, y / ln, z / ln

    @staticmethod
    def _draw_textured_face(p, img, img_rect, pts, src_rect):
        """Аффинное отображение подпрямоугольника текстуры на грань.

        Клип по контуру грани ставится ДО трансформации (устройственные
        координаты), затем текстура рисуется в системе координат текстуры.
        """
        s0 = QPointF(src_rect.left(), src_rect.top())
        s1 = QPointF(src_rect.right(), src_rect.top())
        s2 = QPointF(src_rect.left(), src_rect.bottom())
        t0, t1, t2 = pts[0], pts[1], pts[3]
        m11 = (t1.x() - t0.x()) / (s1.x() - s0.x())
        m12 = (t1.y() - t0.y()) / (s1.x() - s0.x())
        m21 = (t2.x() - t0.x()) / (s2.y() - s0.y())
        m22 = (t2.y() - t0.y()) / (s2.y() - s0.y())
        dx = t0.x() - m11 * s0.x() - m21 * s0.y()
        dy = t0.y() - m12 * s0.x() - m22 * s0.y()
        p.save()
        clip = QPainterPath()
        clip.addPolygon(QPolygonF(pts))
        p.setClipPath(clip)
        p.setTransform(QTransform(m11, m12, m21, m22, dx, dy), True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)
        p.setPen(Qt.NoPen)
        p.drawImage(img_rect, img, img_rect)
        p.setPen(QPen(QColor(0, 0, 0, 40)))
        p.setBrush(Qt.NoBrush)
        p.drawRect(img_rect)
        p.restore()


def math_cos(x):
    import math
    return math.cos(x)


def math_sin(x):
    import math
    return math.sin(x)


# ---------------------------------------------------------------------------
# Панель редактора
# ---------------------------------------------------------------------------
class SkinEditorPanel(CardPanel):
    """Карточка «Редактор скина» (1090x648, r22)."""

    skin_saved = pyqtSignal(str)     # путь к файлу
    skin_applied = pyqtSignal(str)   # «В игру»
    skin_edited = pyqtSignal()       # слои/пиксели изменились

    def __init__(self, cfg, accounts, k=1.0, parent=None):
        super().__init__(round(1090 * k), round(648 * k), radius=22,
                         border="#26c9a45c", parent=parent)
        self.k = float(k)
        self.cfg = cfg
        self.accounts = accounts
        self.layers = make_default_layers()   # слои (база + накладки)
        self.active = 0
        self._composite = None
        self._tool = "P"
        self._color = PALETTE[7]
        self._built = False
        self._patcher = None
        self._build()

    # --- слои и текстура ---------------------------------------------------
    def skin(self) -> QImage:
        """Композит всех слоёв: что видно в 3D и что сохраняется в PNG."""
        if self._composite is None:
            self._composite = compose_layers(self.layers)
        return self._composite

    def composite(self) -> QImage:
        return self.skin()

    def active_layer(self) -> QImage:
        return self.layers[self.active]

    def layer_count(self):
        return len(self.layers)

    @staticmethod
    def _layer_index_for(x, y):
        """Маршрутизация пикселя: регионы накладки -> слой 1, остальное -> 0."""
        for (rx, ry, rw, rh) in OVERLAY_RECTS:
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return 1
        return 0

    def _dirty(self):
        """Слои изменились: сбросить композит и перерисовать холст/3D."""
        self._composite = None
        if self._built:
            self.canvas.invalidate()
            self.preview.update()
        self.skin_edited.emit()

    def snapshot(self):
        """Снимок всех слоёв (для отмены)."""
        return ([l.copy() for l in self.layers], self.active)

    def restore(self, snap):
        layers, active = snap
        self.layers = [l.copy() for l in layers]
        self.active = max(0, min(int(active), len(self.layers) - 1))
        self._dirty()

    def set_skin(self, img, record=False):
        """Заменить содержимое PNG: авто-разбор на базовый слой и накладку."""
        base, ov = split_layers(img)
        self.layers = [base, ov]
        self.active = 0
        self._dirty()

    def tool(self):
        return self._tool

    def color(self):
        return self._color

    # --- рисование (маршрутизация по атлас-региону: база/накладка) --------
    def paint_texel(self, x, y):
        from PyQt5.QtGui import QColor as QC
        c = QC(self._color)
        if self._tool == "E":
            c.setAlpha(0)
        self.layers[self._layer_index_for(x, y)].setPixelColor(x, y, c)
        self._dirty()

    def flood_fill(self, x, y):
        seed_idx = self._layer_index_for(x, y)
        layer = self.layers[seed_idx]
        target = layer.pixelColor(x, y)
        repl = QColor(self._color)
        if target == repl:
            return
        stack = [(x, y)]
        seen = set()
        while stack:
            cx, cy = stack.pop()
            if not (0 <= cx < 64 and 0 <= cy < 64):
                continue
            if (cx, cy) in seen:
                continue
            if self._layer_index_for(cx, cy) != seed_idx:
                continue   # заливка не выходит за пределы своего слоя
            if layer.pixelColor(cx, cy) != target:
                continue
            seen.add((cx, cy))
            layer.setPixelColor(cx, cy, repl)
            stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
        self._dirty()

    # --- сборка ------------------------------------------------------------
    def _build(self):
        k = self.k
        # слои автоматические (база + накладка), выбора слоёв в редакторе нет
        add_label(self, k, 32, 38, 22, 700, 500, "Редактор скина")

        # слои автоматические (база + накладка) — селектор слоёв убран по
        # требованию: правки маршрутизируются по атлас-региону (накладка
        # рисуется на своём слое, база — на своём), 3D показывает накладку
        # отдельной геометрией.
        add_label(self, k, 32, 38, 22, 700, 500, "Редактор скина")

        # --- инструменты 76x448 (28,76) -----------------------------------
        tools = PanelBox(round(76 * k), round(448 * k), radius=16,
                         fill="#15161a", border="#16ffffff", parent=self)
        tools.move(round(28 * k), round(76 * k))
        specs = [
            ("P", theme.ICON_PENCIL, "Карандаш (P)"),
            ("F", theme.ICON_BUCKET, "Заливка (F)"),
            ("E", theme.ICON_RECT, "Ластик (E)"),
            ("U", theme.ICON_ERASE, "Отмена (U)"),
            ("+", theme.ICON_PLUS, "Приблизить (+)"),
            ("-", theme.ICON_MINUS, "Отдалить (−)"),
        ]
        self.tool_btns = {}
        for i, (key, icon, tip) in enumerate(specs):
            btn = ToolButton(icon, k=k, parent=tools)
            btn.move(round(12 * k), round((24 + i * 64) * k))
            btn.setToolTip(tip)
            btn.clicked.connect(lambda kk=key: self._on_tool(kk))
            self.tool_btns[key] = btn
        self.lbl_px = add_label(tools, k, 0, 424, 11, 500, 76, "1 px",
                                color="#8b8f98", align=Qt.AlignCenter)
        self.tool_btns["P"].set_checked(True)

        # --- палитра 70x448 (118,76) --------------------------------------
        pal = PanelBox(round(70 * k), round(448 * k), radius=16,
                       fill="#15161a", border="#16ffffff", parent=self)
        pal.move(round(118 * k), round(76 * k))
        self.swatches = []
        for i, color in enumerate(PALETTE):
            sw = PaletteSwatch(color, k=k, parent=pal)
            cy = 28 + i * 34
            sw.move(round(35 * k - sw.width() / 2.0),
                    round(cy * k - sw.height() / 2.0))
            sw.clicked.connect(self._on_color)
            sw.set_selected(i == 7)
            self.swatches.append(sw)

        # --- UV-холст 512x448 (202,76) ------------------------------------
        self.canvas = CanvasWidget(self, k=k, parent=self)
        self.canvas.move(round(202 * k), round(76 * k))

        # --- 3D 336x448 (730,76) ------------------------------------------
        self.preview = Preview3D(self, k=k, parent=self)
        self.preview.move(round(730 * k), round(76 * k))

        # --- кнопки (y=544) ------------------------------------------------
        self.btn_save = FxButton("Сохранить", kind="sun",
                                 w_=round(156 * k), h_=round(44 * k),
                                 radius=14, px=14, svg_w=800, parent=self)
        self.btn_save.move(round(28 * k), round(544 * k))
        self.btn_save.clicked.connect(self.save_skin)

        self.btn_import = FxButton("Импорт PNG", kind="ghost",
                                   w_=round(144 * k), h_=round(44 * k),
                                   radius=14, px=13, svg_w=600, parent=self)
        self.btn_import.move(round(198 * k), round(544 * k))
        self.btn_import.clicked.connect(self.import_png)

        self.btn_export = FxButton("Экспорт", kind="ghost",
                                   w_=round(144 * k), h_=round(44 * k),
                                   radius=14, px=13, svg_w=600, parent=self)
        self.btn_export.move(round(374 * k), round(544 * k))
        self.btn_export.clicked.connect(self.export_png)

        self.btn_ingame = FxButton("В игру", kind="ghost",
                                   w_=round(144 * k), h_=round(44 * k),
                                   radius=14, px=13, svg_w=600, parent=self)
        self.btn_ingame.move(round(530 * k), round(544 * k))
        self.btn_ingame.clicked.connect(self.apply_ingame)

        # статусная строка (пусто, пока нет сообщений)
        self.lbl_hint = add_label(self, k, 28, 614, 12, 500, 700, "",
                                  color="#7fbf8f")
        self._built = True

    # --- инструменты/цвета -------------------------------------------------
    def _on_tool(self, key):
        if key == "U":
            if self.canvas.undo():
                self._hint("Изменение отменено", "#7fbf8f")
            return
        if key in ("+", "-"):
            self.canvas.zoom(1 if key == "+" else -1)
            self.lbl_px.setText(self.canvas.zoom_label())
            return
        self._tool = key
        for kk, btn in self.tool_btns.items():
            btn.set_checked(kk == key)
        names = {"P": "Карандаш", "F": "Заливка", "E": "Ластик"}
        self._hint(names.get(key, ""), "#8b8f98")

    def _on_color(self, color):
        self._color = color
        for sw in self.swatches:
            sw.set_selected(sw.color_hex() == color)

    # --- файлы -------------------------------------------------------------
    def _skin_path(self):
        from ..core.config import appdata_dir
        nick = (self.accounts.current() or {}).get("name") or "Exeyta"
        d = appdata_dir() / "skins"
        d.mkdir(parents=True, exist_ok=True)
        return d / ("%s.png" % nick)

    def save_skin(self):
        path = self._skin_path()
        try:
            self.composite().save(str(path), "PNG")
            self.accounts.set_skin(str(path))
            self._hint("Скин сохранён: %s" % path.name, "#7fbf8f")
            self.skin_saved.emit(str(path))
        except Exception as e:
            self._hint("Ошибка сохранения: %s" % e, "#d97a7a")

    def import_png(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт скина", "", "PNG (*.png)")
        if not path:
            return
        img = QImage(path)
        if img.isNull():
            self._hint("Не удалось прочитать PNG", "#d97a7a")
            return
        self.set_skin(img)
        import os
        self._hint("Импортировано: %s (слои: база + накладка)"
                   % os.path.basename(path), "#7fbf8f")

    def export_png(self):
        from PyQt5.QtWidgets import QFileDialog
        default = str(self._skin_path())
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт скина", default, "PNG (*.png)")
        if not path:
            return
        if self.composite().save(path, "PNG"):
            self._hint("Экспортировано", "#7fbf8f")
        else:
            self._hint("Ошибка экспорта", "#d97a7a")

    def apply_ingame(self):
        """Сохраняет скин, назначает аккаунту и ставит его в клиентский jar."""
        path = self._skin_path()
        try:
            self.composite().save(str(path), "PNG")
            self.accounts.set_skin(str(path))
            nick = (self.accounts.current() or {}).get("name") or "Exeyta"
            self.skin_applied.emit(str(path))
            self._start_patch(str(path), nick)
        except Exception as e:
            self._hint("Ошибка: %s" % e, "#d97a7a")

    def _start_patch(self, path, nick):
        """Подмена стандартного скина в клиенте текущей версии (QThread)."""
        if self._patcher is not None and self._patcher.isRunning():
            return   # уже применяется
        from ..workers.download_worker import SkinPatchWorker
        ver = str(self.cfg.get("last_version"))
        self._hint("Применяю скин к клиенту %s…" % nick, "#e8cf9a")
        w = SkinPatchWorker(ver, path, game_dir=self.cfg.game_dir,
                            parent=self)
        self._patcher = w

        def _ok(res):
            self._patcher = None
            if res == "skip":
                self._hint("Скин уже в клиенте %s — запускайте" % ver,
                           "#7fbf8f")
            elif res.startswith("applied"):
                self._hint("Скин применён к клиенту %s — запускайте игру"
                           % ver, "#7fbf8f")
            elif res == "none":
                self._hint("Текстуры скина не найдены — установите версию %s"
                           % ver, "#c9a45c")
            else:
                self._hint("Готово: %s" % res, "#7fbf8f")

        def _bad(msg):
            self._patcher = None
            self._hint("Скин не применён: %s" % str(msg)[:70], "#d97a7a")

        w.done.connect(_ok)
        w.failed.connect(_bad)
        w.start()

    def _hint(self, text, color="#7fbf8f"):
        self.lbl_hint.setText(text)
        pal = self.lbl_hint.palette()
        pal.setColor(self.lbl_hint.foregroundRole(), QColor(color))
        self.lbl_hint.setPalette(pal)

    def load_account_skin(self):
        """Ленивая загрузка скина активного аккаунта (в QThread)."""
        path = self.accounts.current_skin()
        if not path:
            return
        from ..workers.download_worker import SkinLoadWorker
        worker = SkinLoadWorker(path, self)
        worker.loaded.connect(lambda img: self.set_skin(img))
        worker.start()
