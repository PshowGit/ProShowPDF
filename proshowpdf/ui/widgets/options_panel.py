"""Conversion options: width, concurrency, timeout, retries, cookies, output."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit,
    QPushButton, QSpinBox, QWidget,
)

from proshowpdf.core.models import ConflictPolicy, ConversionSettings


class OptionsPanel(QWidget):
    """Form exposing all ConversionSettings to the user."""

    def __init__(self) -> None:
        super().__init__()
        form = QFormLayout(self)

        self._width = QSpinBox()
        self._width.setRange(320, 5000)
        self._width.setSuffix(" px")
        form.addRow("Larghezza PDF", self._width)

        self._concurrency = QSpinBox()
        self._concurrency.setRange(1, 10)
        form.addRow("Conversioni parallele", self._concurrency)

        self._timeout = QSpinBox()
        self._timeout.setRange(5, 300)
        self._timeout.setSuffix(" s")
        form.addRow("Timeout", self._timeout)

        self._retries = QSpinBox()
        self._retries.setRange(0, 5)
        form.addRow("Tentativi (retry)", self._retries)

        self._cookies = QCheckBox("Chiudi banner cookie automaticamente")
        form.addRow(self._cookies)

        self._conflict = QComboBox()
        self._conflict.addItems(["rename", "overwrite"])
        form.addRow("Conflitti file", self._conflict)

        out_row = QHBoxLayout()
        self._output = QLineEdit()
        self._output.setReadOnly(True)
        browse = QPushButton("Sfoglia…")
        browse.setObjectName("secondary")
        browse.clicked.connect(self._pick_output)
        out_row.addWidget(self._output)
        out_row.addWidget(browse)
        form.addRow("Cartella output", out_row)

    def _pick_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Cartella di destinazione")
        if path:
            self._output.setText(path)

    def load(self, s: ConversionSettings) -> None:
        self._width.setValue(s.width_px)
        self._concurrency.setValue(s.max_concurrency)
        self._timeout.setValue(s.timeout_ms // 1000)
        self._retries.setValue(s.retries)
        self._cookies.setChecked(s.handle_cookie_banners)
        self._conflict.setCurrentText(s.conflict_policy.value)
        self._output.setText(s.output_dir)

    def to_settings(self) -> ConversionSettings:
        return ConversionSettings(
            output_dir=self._output.text(),
            width_px=self._width.value(),
            max_concurrency=self._concurrency.value(),
            timeout_ms=self._timeout.value() * 1000,
            retries=self._retries.value(),
            handle_cookie_banners=self._cookies.isChecked(),
            conflict_policy=ConflictPolicy(self._conflict.currentText()),
        )
