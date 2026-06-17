"""Standalone output-folder picker: a read-only path field plus a Browse button."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget,
)


class OutputPicker(QWidget):
    """Holds the chosen output directory; exposes path()/set_path()."""

    def __init__(self) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._output = QLineEdit()
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("Nessuna cartella selezionata")
        browse = QPushButton("Sfoglia…")
        browse.setObjectName("secondary")
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.clicked.connect(self._pick)
        row.addWidget(self._output)
        row.addWidget(browse)

    def _pick(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Cartella di destinazione")
        if path:
            self._output.setText(path)

    def path(self) -> str:
        return self._output.text()

    def set_path(self, path: str) -> None:
        self._output.setText(path)
