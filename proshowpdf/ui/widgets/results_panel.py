"""End-of-batch summary: error table, CSV export, open output folder."""
from __future__ import annotations

import csv
import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPushButton, QStackedLayout, QVBoxLayout,
    QWidget,
)

from proshowpdf.core.models import JobResult, JobStatus


class ResultsPanel(QWidget):
    """Summarizes a finished batch and offers CSV export / open folder."""

    def __init__(self) -> None:
        super().__init__()
        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)

        self._empty = self._build_empty_state()
        self._content = self._build_content()
        self._stack.addWidget(self._empty)
        self._stack.addWidget(self._content)

        self._results: list[JobResult] = []
        self._output_dir = ""
        self.set_enabled(False)

    # ---- Views ------------------------------------------------------------
    def _build_empty_state(self) -> QWidget:
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 18, 0, 18)
        box.setSpacing(6)
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("📄")
        icon.setObjectName("emptyIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Ancora nessuna conversione")
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("Aggiungi degli URL e premi “Converti” per vedere qui i risultati.")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)

        box.addWidget(icon)
        box.addWidget(title)
        box.addWidget(hint)
        return page

    def _build_content(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._summary = QLabel("")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        row = QHBoxLayout()
        row.setSpacing(10)
        self._open_btn = QPushButton("Apri cartella output")
        self._open_btn.setObjectName("secondary")
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.clicked.connect(self._open_folder)
        self._export_btn = QPushButton("Esporta errori CSV")
        self._export_btn.setObjectName("secondary")
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.clicked.connect(self._export_csv)
        row.addWidget(self._open_btn)
        row.addWidget(self._export_btn)
        row.addStretch()
        layout.addLayout(row)
        return page

    # ---- State ------------------------------------------------------------
    def set_enabled(self, enabled: bool) -> None:
        """Enabled means results exist; otherwise show the empty state."""
        self._export_btn.setEnabled(enabled)
        self._open_btn.setEnabled(enabled)
        self._stack.setCurrentWidget(self._content if enabled else self._empty)

    def show_results(self, results: list[JobResult], output_dir: str) -> None:
        self._results = results
        self._output_dir = output_dir
        done = sum(1 for r in results if r.status is JobStatus.DONE)
        errors = sum(1 for r in results if r.status is JobStatus.ERROR)
        ok_color = "#22d3a8" if errors == 0 else "#9fd9cf"
        err_color = "#ff6b6b" if errors else "#7c9b95"
        done_word = "completata" if done == 1 else "completate"
        err_word = "errore" if errors == 1 else "errori"
        self._summary.setText(
            f"<span style='font-size:15px'>"
            f"<b style='color:{ok_color}'>✓ {done} {done_word}</b>"
            f"&nbsp;&nbsp;·&nbsp;&nbsp;"
            f"<b style='color:{err_color}'>✗ {errors} {err_word}</b>"
            f"&nbsp;&nbsp;·&nbsp;&nbsp;"
            f"<span style='color:#8fb3ac'>{len(results)} totali</span>"
            f"</span>"
        )
        self._stack.setCurrentWidget(self._content)
        self._export_btn.setEnabled(errors > 0)
        self._open_btn.setEnabled(True)

    def _errors(self) -> list[JobResult]:
        return [r for r in self._results if r.status is JobStatus.ERROR]

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Esporta errori", "errori.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["url", "error_type", "message", "timestamp"])
            for r in self._errors():
                ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([r.url, r.error_type, r.error_message, ts])

    def _open_folder(self) -> None:
        if self._output_dir and Path(self._output_dir).exists():
            os.startfile(self._output_dir)  # noqa: S606 - Windows only
