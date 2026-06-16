"""Multiline URL input with import-from-file support."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
    QWidget,
)

from proshowpdf.core.url_utils import parse_urls


class UrlInput(QWidget):
    """Textarea for URLs plus a button to import .txt/.csv files."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("URL (uno per riga)"))

        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText("https://example.com\nexample.org/page")
        layout.addWidget(self._editor)

        row = QHBoxLayout()
        import_btn = QPushButton("Importa da file…")
        import_btn.setObjectName("secondary")
        import_btn.clicked.connect(self._import_file)
        row.addStretch()
        row.addWidget(import_btn)
        layout.addLayout(row)

    def _import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importa URL", "", "Testo/CSV (*.txt *.csv)"
        )
        if path:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
            existing = self._editor.toPlainText().rstrip()
            joined = (existing + "\n" + text) if existing else text
            self._editor.setPlainText(joined)

    def urls(self) -> list[str]:
        """Return normalized, validated, de-duplicated URLs."""
        return parse_urls(self._editor.toPlainText())
