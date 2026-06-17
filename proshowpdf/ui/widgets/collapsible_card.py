"""A card whose body collapses/expands with a smooth height animation."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout, QWidget

_QT_MAX = 16777215  # Qt's QWIDGETSIZE_MAX, i.e. "no maximum height".


class CollapsibleCard(QFrame):
    """A titled card with a clickable header that toggles its body (accordion)."""

    def __init__(self, title: str, expanded: bool = True) -> None:
        super().__init__()
        self.setObjectName("card")
        self._title = title
        self._expanded = expanded

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 8)
        outer.setSpacing(0)

        self._header = QPushButton()
        self._header.setObjectName("accordionHeader")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.clicked.connect(self._toggle)
        outer.addWidget(self._header)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(12, 10, 12, 8)
        outer.addWidget(self._body)

        self._update_header()
        if not expanded:
            self._body.setMaximumHeight(0)
            self._body.setVisible(False)

    def add(self, widget: QWidget) -> None:
        self._body_layout.addWidget(widget)

    def _update_header(self) -> None:
        chevron = "▾" if self._expanded else "▸"
        self._header.setText(f"{chevron}   {self._title.upper()}")

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._update_header()
        self._body.setVisible(True)
        start = self._body.height()
        end = self._body.sizeHint().height() if self._expanded else 0

        anim = QPropertyAnimation(self._body, b"maximumHeight", self._body)
        anim.setDuration(200)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        if self._expanded:
            # Release the cap once open so the body can grow with the window.
            anim.finished.connect(lambda: self._body.setMaximumHeight(_QT_MAX))
        else:
            anim.finished.connect(lambda: self._body.setVisible(False))
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
