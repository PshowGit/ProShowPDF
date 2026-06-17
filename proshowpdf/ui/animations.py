"""Lightweight QPropertyAnimation helpers for micro-interactions."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget


def fade_in(widget: QWidget, duration_ms: int = 250) -> QPropertyAnimation:
    """Fade a widget from transparent to opaque; returns the running anim."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim


def slide_fade_in(
    widget: QWidget, duration_ms: int = 320, offset: int = 14
) -> QParallelAnimationGroup:
    """Fade in while rising slightly into place — a softer reveal than a plain
    fade. Returns the running group (kept alive via widget parenting)."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    fade = QPropertyAnimation(effect, b"opacity", widget)
    fade.setDuration(duration_ms)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    start_pos = widget.pos()
    slide = QPropertyAnimation(widget, b"pos", widget)
    slide.setDuration(duration_ms)
    slide.setStartValue(QPoint(start_pos.x(), start_pos.y() + offset))
    slide.setEndValue(start_pos)
    slide.setEasingCurve(QEasingCurve.Type.OutCubic)

    group = QParallelAnimationGroup(widget)
    group.addAnimation(fade)
    group.addAnimation(slide)
    group.start(QParallelAnimationGroup.DeletionPolicy.DeleteWhenStopped)
    return group


def cross_fade_swap(
    widget: QWidget, swap: Callable[[], None], duration_ms: int = 300
) -> QPropertyAnimation:
    """Cross-fade a widget through a visual change (e.g. a theme switch).

    Snapshots the widget's current pixels into an overlay, runs ``swap`` to
    apply the change underneath, then fades the snapshot out to reveal the new
    look — so the transition dissolves smoothly instead of flashing.
    """
    snapshot = widget.grab()
    overlay = QLabel(widget)
    overlay.setPixmap(snapshot)
    overlay.setGeometry(widget.rect())
    overlay.show()
    overlay.raise_()

    swap()

    effect = QGraphicsOpacityEffect(overlay)
    overlay.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", overlay)
    anim.setDuration(duration_ms)
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
    anim.finished.connect(overlay.deleteLater)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim
