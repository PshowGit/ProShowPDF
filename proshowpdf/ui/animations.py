"""Lightweight QPropertyAnimation helpers for micro-interactions."""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


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
