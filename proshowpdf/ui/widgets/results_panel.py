"""End-of-batch summary: error table, CSV export, open output folder."""
from __future__ import annotations

import csv
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from proshowpdf.core.models import JobResult, JobStatus


class ResultsPanel(QWidget):
    """Summarizes a finished batch and offers CSV export / open folder."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        self._summary = QLabel("")
        layout.addWidget(self._summary)

        row = QHBoxLayout()
        self._export_btn = QPushButton("Esporta errori CSV")
        self._export_btn.setObjectName("secondary")
        self._export_btn.clicked.connect(self._export_csv)
        self._open_btn = QPushButton("Apri cartella output")
        self._open_btn.setObjectName("secondary")
        self._open_btn.clicked.connect(self._open_folder)
        row.addWidget(self._export_btn)
        row.addWidget(self._open_btn)
        row.addStretch()
        layout.addLayout(row)

        self._results: list[JobResult] = []
        self._output_dir = ""
        self.set_enabled(False)

    def set_enabled(self, enabled: bool) -> None:
        self._export_btn.setEnabled(enabled)
        self._open_btn.setEnabled(enabled)

    def show_results(self, results: list[JobResult], output_dir: str) -> None:
        self._results = results
        self._output_dir = output_dir
        done = sum(1 for r in results if r.status is JobStatus.DONE)
        errors = sum(1 for r in results if r.status is JobStatus.ERROR)
        self._summary.setText(
            f"Completate: {done} — Errori: {errors} — Totale: {len(results)}"
        )
        self.set_enabled(True)

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
