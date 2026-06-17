"""Conversion options: width, concurrency, timeout, retries, conflict, cookies.

The output directory lives in a separate OutputPicker, so to_settings() takes it
as an argument.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QLabel, QSpinBox, QWidget,
)

from proshowpdf.core.models import ConflictPolicy, ConversionSettings


class OptionsPanel(QWidget):
    """Compact full-width grid of conversion options (no output dir)."""

    def __init__(self) -> None:
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        # Three label/field pairs per row across the full width.
        for field_col in (1, 3, 5):
            grid.setColumnStretch(field_col, 1)

        self._width = QSpinBox()
        self._width.setRange(320, 5000)
        self._width.setSingleStep(20)
        self._width.setSuffix(" px")
        self._width.setMinimumWidth(96)
        self._width.setToolTip("Larghezza del PDF; l'altezza è dinamica e continua")

        self._concurrency = QSpinBox()
        self._concurrency.setRange(1, 10)
        self._concurrency.setMinimumWidth(96)
        self._concurrency.setToolTip("Quante pagine convertire contemporaneamente")

        self._timeout = QSpinBox()
        self._timeout.setRange(5, 300)
        self._timeout.setSuffix(" s")
        self._timeout.setMinimumWidth(96)
        self._timeout.setToolTip("Tempo massimo di attesa per ogni pagina")

        self._retries = QSpinBox()
        self._retries.setRange(0, 5)
        self._retries.setMinimumWidth(96)
        self._retries.setToolTip("Tentativi aggiuntivi in caso di errore")

        self._conflict = QComboBox()
        self._conflict.addItems(["rename", "overwrite"])
        self._conflict.setMinimumWidth(112)
        self._conflict.setToolTip("Cosa fare se un file con lo stesso nome esiste già")

        self._add_field(grid, 0, 0, "Larghezza PDF", self._width)
        self._add_field(grid, 0, 2, "Conversioni parallele", self._concurrency)
        self._add_field(grid, 0, 4, "Timeout per pagina", self._timeout)
        self._add_field(grid, 1, 0, "Tentativi (retry)", self._retries)
        self._add_field(grid, 1, 2, "Conflitti file", self._conflict)

        self._cookies = QCheckBox("Chiudi banner cookie")
        self._cookies.setToolTip("Prova a chiudere automaticamente i banner di consenso")
        grid.addWidget(self._cookies, 1, 4, 1, 2)

    @staticmethod
    def _add_field(grid: QGridLayout, row: int, col: int, label: str, field: QWidget) -> None:
        grid.addWidget(QLabel(label), row, col)
        grid.addWidget(field, row, col + 1)

    def load(self, s: ConversionSettings) -> None:
        self._width.setValue(s.width_px)
        self._concurrency.setValue(s.max_concurrency)
        self._timeout.setValue(s.timeout_ms // 1000)
        self._retries.setValue(s.retries)
        self._cookies.setChecked(s.handle_cookie_banners)
        self._conflict.setCurrentText(s.conflict_policy.value)

    def to_settings(self, output_dir: str) -> ConversionSettings:
        return ConversionSettings(
            output_dir=output_dir,
            width_px=self._width.value(),
            max_concurrency=self._concurrency.value(),
            timeout_ms=self._timeout.value() * 1000,
            retries=self._retries.value(),
            handle_cookie_banners=self._cookies.isChecked(),
            conflict_policy=ConflictPolicy(self._conflict.currentText()),
        )
