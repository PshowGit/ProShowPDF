"""Reusable section card: a titled, elevated container used app-wide."""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class Card(QFrame):
    """A rounded surface with an optional uppercase section title.

    Children are added to the card body via ``add()`` / ``add_layout()`` so the
    title and consistent padding are applied automatically.
    """

    def __init__(self, title: str | None = None, hint: str | None = None) -> None:
        super().__init__()
        self.setObjectName("card")

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(20, 18, 20, 18)
        self._outer.setSpacing(12)

        if title:
            label = QLabel(title.upper())
            label.setObjectName("sectionTitle")
            self._outer.addWidget(label)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("hint")
            hint_label.setWordWrap(True)
            self._outer.addWidget(hint_label)

    def add(self, widget: QWidget) -> None:
        self._outer.addWidget(widget)

    def add_layout(self, layout) -> None:
        self._outer.addLayout(layout)
