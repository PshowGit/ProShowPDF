"""Lightweight QPropertyAnimation helpers for micro-interactions."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QObject
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
