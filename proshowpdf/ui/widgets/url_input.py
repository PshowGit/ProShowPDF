"""Multiline URL input with drag-and-drop and file import."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
    QWidget,
)

from proshowpdf.core.url_utils import parse_urls, normalize_url


def _cell_to_str(value: object) -> str:
    """Stringify an Excel cell, dropping the trailing '.0' that openpyxl/xlrd
    add to whole numbers (a numeric filename like 98888 reads back as 98888.0)."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class DragDropPlainText(QPlainTextEdit):
    """PlainTextEdit with drag-and-drop for txt/csv/xlsx files."""

    urls_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self._custom_names: dict[str, str] = {}

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
                text, custom_names = self._read_excel(path)
                self._custom_names.update(custom_names)
            elif path.suffix.lower() == ".csv":
                text, custom_names = self._read_csv(path)
                self._custom_names.update(custom_names)
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")

            existing = self.toPlainText().rstrip()
            joined = (existing + "\n" + text) if existing else text
            self.setPlainText(joined)
            self._update_counter()
        except Exception:
            pass


    def _read_excel(self, path: Path) -> tuple[str, dict[str, str]]:
        """Extract URLs from Excel. Returns (text, custom_names_dict)."""
        if path.suffix.lower() == ".xls":
            return self._read_excel_xls(path)
        else:
            return self._read_excel_xlsx(path)

    def _read_excel_xlsx(self, path: Path) -> tuple[str, dict[str, str]]:
        """Read .xlsx file using openpyxl. Returns (text, custom_names_dict)."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(path), data_only=True)
            ws = wb.active
            lines = []
            custom_names = {}
            for row_idx, row in enumerate(ws.iter_rows(min_col=1, max_col=2, values_only=True)):
                url = row[0]
                custom_name = row[1] if len(row) > 1 else None
                if url is not None and str(url).strip():
                    url_str = _cell_to_str(url).strip()
                    if url_str.lower() != "url":
                        normalized_url = normalize_url(url_str)
                        lines.append(url_str)
                        if custom_name is not None and str(custom_name).strip():
                            custom_name_str = _cell_to_str(custom_name).strip()
                            if custom_name_str.lower() not in ("name", "filename"):
                                custom_names[normalized_url] = custom_name_str
            return "\n".join(lines), custom_names
        except ImportError:
            text = path.read_text(encoding="utf-8", errors="ignore")
            return text, {}

    def _read_excel_xls(self, path: Path) -> tuple[str, dict[str, str]]:
        """Read .xls file using xlrd. Returns (text, custom_names_dict)."""
        try:
            import xlrd
            book = xlrd.open_workbook(str(path))
            sheet = book.sheet_by_index(0)
            lines = []
            custom_names = {}
            for row_num in range(sheet.nrows):
                url = sheet.cell_value(row_num, 0)
                custom_name = sheet.cell_value(row_num, 1) if sheet.ncols > 1 else None
                if url is not None and str(url).strip():
                    url_str = _cell_to_str(url).strip()
                    if url_str.lower() != "url":
                        normalized_url = normalize_url(url_str)
                        lines.append(url_str)
                        if custom_name is not None and str(custom_name).strip():
                            custom_name_str = _cell_to_str(custom_name).strip()
                            if custom_name_str.lower() not in ("name", "filename"):
                                custom_names[normalized_url] = custom_name_str
            return "\n".join(lines), custom_names
        except ImportError:
            text = path.read_text(encoding="utf-8", errors="ignore")
            return text, {}

    def _read_csv(self, path: Path) -> tuple[str, dict[str, str]]:
        """Read .csv file. Auto-detects delimiter (comma or semicolon). Returns (text, custom_names_dict)."""
        import csv
        lines = []
        custom_names = {}
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    delimiter = csv.Sniffer().sniff(sample, delimiters=",;").delimiter
                except csv.Error:
                    delimiter = ","
                reader = csv.reader(f, delimiter=delimiter)
                for row in reader:
                    if not row or not row[0]:
                        continue
                    url = row[0].strip()
                    if url.lower() != "url":
                        normalized_url = normalize_url(url)
                        lines.append(url)
                        if len(row) > 1:
                            custom_name = row[1].strip()
                            if custom_name.lower() not in ("name", "filename"):
                                custom_names[normalized_url] = custom_name
            return "\n".join(lines), custom_names
        except Exception:
            text = path.read_text(encoding="utf-8", errors="ignore")
            return text, {}


class UrlInput(QWidget):
    """Textarea for URLs with drag-and-drop and file import (txt, csv, xlsx)."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("URL (uno per riga, drag-and-drop file txt/csv/xlsx)"))

        self._editor = DragDropPlainText()
        self._editor.setPlaceholderText("https://example.com\nexample.org/page\n\no trascina file txt/csv/xlsx")
        self._editor.textChanged.connect(self._update_counter)
        layout.addWidget(self._editor)

        row = QHBoxLayout()
        self._url_counter = QLabel("URL caricate: 0")
        self._url_counter.setStyleSheet("color: #333; font-size: 14px; font-weight: bold;")
        row.addWidget(self._url_counter)
        row.addStretch()
        import_btn = QPushButton("Importa da file…")
        import_btn.setObjectName("secondary")
        import_btn.clicked.connect(self._import_file)
        row.addWidget(import_btn)
        layout.addLayout(row)

    def _import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importa URL", "", "Testo/CSV/Excel (*.txt *.csv *.xlsx *.xls)"
        )
        if path:
            self._editor._load_file(Path(path))

    def _update_counter(self) -> None:
        """Update URL counter display."""
        text = self._editor.toPlainText()
        url_count = len([l for l in text.split("\n") if l.strip()])
        self._url_counter.setText(f"URL caricate: {url_count}")

    def urls(self) -> list[str]:
        """Return normalized, validated, de-duplicated URLs."""
        return parse_urls(self._editor.toPlainText())

    def custom_filenames(self) -> list[str | None]:
        """Return custom filenames for URLs (or None if not provided)."""
        urls = self.urls()
        return [self._editor._custom_names.get(url) for url in urls]
