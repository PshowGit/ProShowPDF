"""Conversion options: width, concurrency, timeout, retries, cookies, output."""
from __future__ import annotations

from PySide6.QtCore import Qt
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
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self._width = QSpinBox()
        self._width.setRange(320, 5000)
        self._width.setSingleStep(20)
        self._width.setSuffix(" px")
        self._width.setToolTip("Larghezza del PDF; l'altezza è dinamica e continua")
        form.addRow("Larghezza PDF", self._width)

        self._concurrency = QSpinBox()
        self._concurrency.setRange(1, 10)
        self._concurrency.setToolTip("Quante pagine convertire contemporaneamente")
        form.addRow("Conversioni parallele", self._concurrency)

        self._timeout = QSpinBox()
        self._timeout.setRange(5, 300)
        self._timeout.setSuffix(" s")
        self._timeout.setToolTip("Tempo massimo di attesa per ogni pagina")
        form.addRow("Timeout per pagina", self._timeout)

        self._retries = QSpinBox()
        self._retries.setRange(0, 5)
        self._retries.setToolTip("Tentativi aggiuntivi in caso di errore")
        form.addRow("Tentativi (retry)", self._retries)

        self._conflict = QComboBox()
        self._conflict.addItems(["rename", "overwrite"])
        self._conflict.setToolTip("Cosa fare se un file con lo stesso nome esiste già")
        form.addRow("Conflitti file", self._conflict)

        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        self._output = QLineEdit()
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("Nessuna cartella selezionata")
        browse = QPushButton("Sfoglia…")
        browse.setObjectName("secondary")
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.clicked.connect(self._pick_output)
        out_row.addWidget(self._output)
        out_row.addWidget(browse)
        form.addRow("Cartella output", out_row)

        self._cookies = QCheckBox("Chiudi automaticamente i banner cookie")
        form.addRow("", self._cookies)

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
