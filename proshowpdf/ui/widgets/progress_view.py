"""Real-time progress: bar, counter, current URL, per-item status list."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QProgressBar,
    QVBoxLayout, QWidget,
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        head = QHBoxLayout()
        self._current = QLabel("In attesa di avvio…")
        self._current.setObjectName("hint")
        self._current.setWordWrap(True)
        self._counter = QLabel("0 / 0")
        self._counter.setObjectName("counter")
        head.addWidget(self._current, 1)
        head.addWidget(self._counter, 0)
        layout.addLayout(head)

        self._bar = QProgressBar()
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        layout.addWidget(self._bar)

        self._list = QListWidget()
        self._list.setMinimumHeight(120)
        layout.addWidget(self._list)

        self._rows: dict[int, QListWidgetItem] = {}

    def reset(self, total: int) -> None:
        self._list.clear()
        self._rows.clear()
        self._bar.setRange(0, max(total, 1))
        self._bar.setValue(0)
        self._counter.setText(f"0 / {total}")
        self._current.setText("In attesa di avvio…" if total == 0 else "Preparazione…")

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
            self._list.scrollToItem(item)
        if result.status is JobStatus.RUNNING:
            self._current.setText(f"In corso · {result.url}")
        elif completed == total:
            self._current.setText("Completato")
        self._bar.setValue(completed)
        pct = int(completed / total * 100) if total else 0
        self._counter.setText(f"{completed} / {total}  ·  {pct}%")
