"""Multiline URL input with drag-and-drop and file import."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
    QWidget,
)

from proshowpdf.core.url_utils import parse_urls


class DragDropPlainText(QPlainTextEdit):
    """PlainTextEdit with drag-and-drop for txt/csv/xlsx files."""

    urls_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in (".txt", ".csv", ".xlsx", ".xls"):
                self._load_file(path)
                event.acceptProposedAction()

    def _load_file(self, path: Path) -> None:
        try:
            if path.suffix.lower() in (".xlsx", ".xls"):
                text = self._read_excel(path)
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")
            existing = self.toPlainText().rstrip()
            joined = (existing + "\n" + text) if existing else text
            self.setPlainText(joined)
        except Exception:
            pass

    def _read_excel(self, path: Path) -> str:
        """Extract URLs from Excel (first column, ignore header)."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(path), data_only=True)
            ws = wb.active
            lines = []
            for row_num, row in enumerate(ws.iter_rows(min_col=1, max_col=1, values_only=True), 1):
                if row[0]:
                    cell = str(row[0]).strip()
                    if row_num > 1 and cell.lower() != "url":
                        lines.append(cell)
            return "\n".join(lines)
        except ImportError:
            # openpyxl not installed; try generic CSV-like fallback
            return path.read_text(encoding="utf-8", errors="ignore")


class UrlInput(QWidget):
    """Textarea for URLs with drag-and-drop and file import (txt, csv, xlsx)."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("URL (uno per riga, drag-and-drop file txt/csv/xlsx)"))

        self._editor = DragDropPlainText()
        self._editor.setPlaceholderText("https://example.com\nexample.org/page\n\no trascina file txt/csv/xlsx")
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
            self, "Importa URL", "", "Testo/CSV/Excel (*.txt *.csv *.xlsx *.xls)"
        )
        if path:
            self._editor._load_file(Path(path))

    def urls(self) -> list[str]:
        """Return normalized, validated, de-duplicated URLs."""
        return parse_urls(self._editor.toPlainText())
