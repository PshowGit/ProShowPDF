"""Real-time progress: bar, counter, current URL, per-item status list."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel, QListWidget, QListWidgetItem, QProgressBar, QVBoxLayout, QWidget,
)

from proshowpdf.core.models import JobResult, JobStatus

_ICONS = {
    JobStatus.QUEUED: "⏳",
    JobStatus.RUNNING: "\U0001f504",
    JobStatus.DONE: "✅",
    JobStatus.ERROR: "❌",
    JobStatus.CANCELLED: "⏹️",
}


class ProgressView(QWidget):
    """Shows batch progress and a live list of per-URL statuses."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        self._counter = QLabel("0 / 0")
        layout.addWidget(self._counter)

        self._bar = QProgressBar()
        self._bar.setValue(0)
        layout.addWidget(self._bar)

        self._current = QLabel("")
        self._current.setWordWrap(True)
        layout.addWidget(self._current)

        self._list = QListWidget()
        layout.addWidget(self._list)

        self._rows: dict[int, QListWidgetItem] = {}

    def reset(self, total: int) -> None:
        self._list.clear()
        self._rows.clear()
        self._bar.setRange(0, max(total, 1))
        self._bar.setValue(0)
        self._counter.setText(f"0 / {total}")
        self._current.setText("")

    def update(self, result: JobResult, completed: int, total: int) -> None:
        label = f"{_ICONS[result.status]}  {result.url}"
        if result.status is JobStatus.ERROR:
            label += f"  —  {result.error_type}: {result.error_message}"
        if result.index in self._rows:
            self._rows[result.index].setText(label)
        else:
            item = QListWidgetItem(label)
            self._rows[result.index] = item
            self._list.addItem(item)
        if result.status is JobStatus.RUNNING:
            self._current.setText(f"In corso: {result.url}")
        self._bar.setValue(completed)
        self._counter.setText(f"{completed} / {total}")
