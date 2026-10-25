# -*- coding: utf-8 -*-
"""Плавные анимации Exeyta: QPropertyAnimation, OutCubic.

Правила производительности:
  * hover 180-320 мс, переходы 280-420 мс;
  * никаких таймеров на 16 мс с repaint всего окна;
  * анимируются только свойства (opacity / pos / float), не полная перерисовка.
"""
from PyQt5.QtCore import (QEasingCurve, QObject, QPoint, QPropertyAnimation,
                          Qt, pyqtProperty)


HOVER_MS = 220
PAGE_MS = 340
PRESS_MS = 120


def ease_out_cubic(anim):
    anim.setEasingCurve(QEasingCurve.OutCubic)
    return anim


def safe_stop(anim):
    """Останавливает сохранённую анимацию, переживая DeleteWhenStopped.

    QPropertyAnimation, запущенный с DeleteWhenStopped, удаляет свой
    C++-объект сразу после завершения — повторный stop() на «мёртвой»
    обёртке бросал RuntimeError ДО отправки clicked (кнопки «не кликались»).
    """
    if anim is None:
        return
    try:
        anim.stop()
    except RuntimeError:
        pass   # объект уже удалён — просто создадим новую анимацию


def anim_property(target, prop_name, start, end, ms=HOVER_MS, on_done=None):
    """Универсальная анимация свойства target.<prop_name>."""
    name = prop_name if isinstance(prop_name, bytes) else prop_name.encode()
    anim = QPropertyAnimation(target, name)
    anim.setDuration(int(ms))
    anim.setStartValue(start)
    anim.setEndValue(end)
    ease_out_cubic(anim)
    if on_done is not None:
        anim.finished.connect(on_done)
    # владелец = target, чтобы анимацию не собрал GC до завершения
    try:
        anim.setParent(target)
    except Exception:
        pass
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim


def fade_in(widget, ms=PAGE_MS):
    """Плавное появление (opacity 0 -> 1).

    ВАЖНО: QGraphicsOpacityEffect снимается сразу после окончания анимации —
    постоянный эффект у секции ломал рендер дочерних кнопок с
    QGraphicsDropShadowEffect (ИГРАТЬ «исчезал» при зажатии, известный
    конфликт child-effect внутри ancestor-effect в Qt).
    """
    from PyQt5.QtWidgets import QGraphicsOpacityEffect

    # если предыдущая fade-анимация ещё идёт — гасим её, чтобы её
    # завершение не сняло эффект новой анимации
    prev = getattr(widget, "_fade_anim", None)
    if prev is not None:
        try:
            prev.stop()          # finished -> cleanup старой (она уже заменена)
        except RuntimeError:
            pass

    eff = widget.graphicsEffect()
    if not isinstance(eff, QGraphicsOpacityEffect):
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
    eff.setOpacity(0.0)

    anim = QPropertyAnimation(eff, b"opacity")
    anim.setDuration(int(ms))
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    ease_out_cubic(anim)
    anim.setParent(widget)          # не даём GC оборвать анимацию
    widget._fade_anim = anim

    def _done(*_a, anim=anim, eff=eff):
        if getattr(widget, "_fade_anim", None) is not anim:
            return                  # уже запущена новая fade-анимация
        widget._fade_anim = None
        try:
            eff.setOpacity(1.0)
            widget.setGraphicsEffect(None)   # снимаем навсегда
        except RuntimeError:
            pass

    anim.finished.connect(_done)
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim


def finish_fade(widget):
    """Мгновенно завершает fade-анимацию и СНИМАЕТ эффект секции.

    Вызывается из обработчиков нажатия: пока у секции активен
    QGraphicsOpacityEffect, зажатие кнопок с glow (ИГРАТЬ) давало
    конфликт child-effect/ancestor-effect в Qt — кнопка «исчезала».
    Снимаем эффект принудительно (stop() не гарантирует finished()).
    """
    w = widget
    while w is not None:
        anim = getattr(w, "_fade_anim", None)
        if anim is not None:
            w._fade_anim = None        # не дать cleanup'у сделать двойную работу
            try:
                anim.stop()
            except RuntimeError:
                pass
        eff = w.graphicsEffect()
        if eff is not None and type(eff).__name__ == "QGraphicsOpacityEffect":
            try:
                eff.setOpacity(1.0)
                w.setGraphicsEffect(None)
            except RuntimeError:
                pass
        w = w.parentWidget()


def slide_up(widget, dy=18, ms=PAGE_MS):
    """Мягкий сдвиг снизу вверх (появление панели)."""
    end = widget.pos()
    start = QPoint(end.x(), end.y() + int(dy))
    widget.move(start)
    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(int(ms))
    anim.setStartValue(start)
    anim.setEndValue(end)
    ease_out_cubic(anim)
    anim.setParent(widget)
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim


class HoverFader(QObject):
    """Плавный hover для кнопок, рисующихся вручную (0.0..1.0).

    Анимирует собственное свойство hoverT; при изменении вызывает
    update() владельца — repaint затрагивает только маленький виджет.
    """

    def __init__(self, owner, ms=HOVER_MS):
        super().__init__(owner)
        self.owner = owner
        self._value = 0.0
        self._anim = None
        self._ms = int(ms)

    @pyqtProperty(float)
    def hoverT(self):
        return self._value

    @hoverT.setter
    def hoverT(self, v):
        self._value = float(v)
        self.owner.update()

    def target(self, on):
        safe_stop(self._anim)
        self._anim = QPropertyAnimation(self, b"hoverT")
        self._anim.setDuration(self._ms)
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(1.0 if on else 0.0)
        ease_out_cubic(self._anim)
        self._anim.start(QPropertyAnimation.DeleteWhenStopped)


def debounce(ms, fn, parent=None):
    """Возвращает функцию, вызывающую fn не чаще чем раз в ms мс."""
    from PyQt5.QtCore import QTimer
    timer = QTimer(parent)
    timer.setSingleShot(True)
    timer.setInterval(int(ms))
    timer.timeout.connect(fn)

    def _kick():
        timer.start()

    return _kick
