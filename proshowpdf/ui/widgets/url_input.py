"""Multiline URL input with drag-and-drop and file import."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor, QDragEnterEvent, QDropEvent, QSyntaxHighlighter, QTextCharFormat,
)
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
    QWidget,
)

from proshowpdf.core.url_utils import is_valid_url, normalize_url, parse_urls


def _cell_to_str(value: object) -> str:
    """Stringify an Excel cell, dropping the trailing '.0' that openpyxl/xlrd
    add to whole numbers (a numeric filename like 98888 reads back as 98888.0)."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _line_is_invalid(line: str) -> bool:
    """A line counts as invalid only when it carries content that cannot become
    a URL. Blank lines and '#' comments are skipped (not flagged)."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    cell = stripped.split(",", 1)[0].split(";", 1)[0].strip()
    if cell.lower() == "url":
        return False
    return not is_valid_url(normalize_url(cell))


class UrlHighlighter(QSyntaxHighlighter):
    """Underlines invalid URL lines in red as the user types."""

    def __init__(self, document) -> None:
        super().__init__(document)
        self._fmt = QTextCharFormat()
        self._fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        self._fmt.setUnderlineColor(QColor("#ff6b6b"))
        self._fmt.setForeground(QColor("#ff8585"))

    def highlightBlock(self, text: str) -> None:
        if _line_is_invalid(text):
            self.setFormat(0, len(text), self._fmt)


class DragDropPlainText(QPlainTextEdit):
    """PlainTextEdit with drag-and-drop for txt/csv/xlsx files."""

    urls_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self._custom_names: dict[str, str] = {}
        self.setProperty("dragActive", False)

    def _set_drag_active(self, active: bool) -> None:
        """Toggle the dragActive property and repolish so QSS reacts live."""
        if self.property("dragActive") == active:
            return
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            self._set_drag_active(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_drag_active(False)
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._editor = DragDropPlainText()
        self._editor.setObjectName("dropZone")
        self._editor.setPlaceholderText(
            "https://example.com\nexample.org/page\n\n…oppure trascina qui un file txt / csv / xlsx"
        )
        self._editor.setMinimumHeight(150)
        self._highlighter = UrlHighlighter(self._editor.document())
        self._editor.textChanged.connect(self._update_counter)
        layout.addWidget(self._editor)

        row = QHBoxLayout()
        self._url_counter = QLabel("0 URL caricate")
        self._url_counter.setObjectName("counter")
        row.addWidget(self._url_counter)
        row.addStretch()
        import_btn = QPushButton("Importa da file…")
        import_btn.setObjectName("secondary")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        """Update URL counter: how many lines are valid vs. need fixing."""
        valid = len(self.urls())
        invalid = sum(
            1 for line in self._editor.toPlainText().splitlines()
            if _line_is_invalid(line)
        )
        suffix = "URL valida" if valid == 1 else "URL valide"
        text = f"{valid} {suffix}"
        if invalid:
            plural = "riga" if invalid == 1 else "righe"
            text += (
                f"<span style='color:#ff6b6b'>"
                f"&nbsp;&nbsp;·&nbsp;&nbsp;{invalid} {plural} da correggere</span>"
            )
        self._url_counter.setText(text)

    def urls(self) -> list[str]:
        """Return normalized, validated, de-duplicated URLs."""
        return parse_urls(self._editor.toPlainText())

    def custom_filenames(self) -> list[str | None]:
        """Return custom filenames for URLs (or None if not provided)."""
        urls = self.urls()
        return [self._editor._custom_names.get(url) for url in urls]
