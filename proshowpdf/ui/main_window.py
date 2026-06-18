"""Main window: assembles widgets and wires controller signals."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from proshowpdf.bridge.controller import ConversionController
from proshowpdf.core.models import ConversionSettings, JobResult
from proshowpdf.persistence.settings_store import SettingsStore
from proshowpdf.ui.animations import cross_fade_swap, fade_in, slide_fade_in
from proshowpdf.ui.theme import apply_theme
from proshowpdf.ui.widgets.card import Card
from proshowpdf.ui.widgets.options_panel import OptionsPanel
from proshowpdf.ui.widgets.output_picker import OutputPicker
from proshowpdf.ui.widgets.progress_view import ProgressView
from proshowpdf.ui.widgets.results_panel import ResultsPanel
from proshowpdf.ui.widgets.url_input import UrlInput

log = logging.getLogger(__name__)

_RESOURCES = Path(__file__).parent.parent / "resources"


class MainWindow(QMainWindow):
    def __init__(self, controller: ConversionController, store: SettingsStore) -> None:
        super().__init__()
        self._controller = controller
        self._store = store
        self._theme = store.load_theme()
        self.setWindowTitle("ProShow PDF")
        icon_path = _RESOURCES / "ProShowPDF.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1000, 1200)
        self.setMinimumSize(880, 780)

        self._url_input = UrlInput()
        self._output_picker = OutputPicker()
        self._options = OptionsPanel()
        self._progress = ProgressView()
        self._results = ResultsPanel()

        default_out = str(Path.home() / "Documents")
        initial = store.load_settings(default_out)
        self._options.load(initial)
        self._output_picker.set_path(initial.output_dir)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 22)
        root.setSpacing(14)

        root.addLayout(self._build_header())

        # Full-width URL box (the primary input), then the output folder.
        input_card = Card(
            "URL da convertire",
            "Uno per riga · trascina file txt/csv/xlsx · 2ª colonna = nome PDF",
        )
        input_card.add(self._url_input)
        root.addWidget(input_card, 2)

        output_card = Card("Cartella di output")
        output_card.add(self._output_picker)
        root.addWidget(output_card)

        options_card = Card("Opzioni di conversione")
        options_card.add(self._options)
        root.addWidget(options_card)

        root.addLayout(self._build_actions())

        # Progress and results share one card: the per-item list already is the
        # results detail, so a single "activity" area avoids a redundant panel.
        self._activity_card = Card("Avanzamento e risultati")
        self._activity_card.add(self._progress)
        self._activity_card.add(self._results)
        root.addWidget(self._activity_card, 1)

        self.setCentralWidget(central)

        self._wire_signals(controller)

    # ---- Layout builders --------------------------------------------------
    def _build_header(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(14)

        logo_path = _RESOURCES / "ProShowPDF.ico"
        if logo_path.exists():
            logo = QLabel()
            logo.setPixmap(
                QPixmap(str(logo_path)).scaled(
                    44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            bar.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel("ProShow PDF")
        title.setObjectName("appTitle")
        subtitle = QLabel("Converti pagine web in PDF ad alta fedeltà")
        subtitle.setObjectName("appSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        bar.addLayout(titles)

        bar.addStretch()

        self._theme_btn = QPushButton()
        self._theme_btn.setObjectName("ghost")
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.setToolTip("Cambia tema chiaro / scuro")
        self._update_theme_btn_text()
        bar.addWidget(self._theme_btn)
        return bar

    def _build_actions(self) -> QHBoxLayout:
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self._start_btn = QPushButton("Converti")
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.setMinimumWidth(150)
        self._cancel_btn = QPushButton("Annulla")
        self._cancel_btn.setObjectName("secondary")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setEnabled(False)
        self._clear_btn = QPushButton("Pulisci")
        self._clear_btn.setObjectName("secondary")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.addWidget(self._start_btn)
        buttons.addWidget(self._cancel_btn)
        buttons.addWidget(self._clear_btn)
        buttons.addStretch()
        return buttons

    def _wire_signals(self, controller: ConversionController) -> None:
        self._start_btn.clicked.connect(self._on_start)
        self._cancel_btn.clicked.connect(self._controller.cancel)
        self._clear_btn.clicked.connect(self._on_clear)
        self._theme_btn.clicked.connect(self._toggle_theme)
        controller.progress.connect(self._progress.update)
        controller.finished.connect(self._on_finished)
        controller.failed.connect(self._on_failed)
        controller.cancelled.connect(self._on_cancelled)

    # ---- Slots ------------------------------------------------------------
    def _on_start(self) -> None:
        urls = self._url_input.urls()
        if not urls:
            QMessageBox.warning(self, "Nessun URL", "Inserisci almeno un URL valido.")
            return
        settings = self._options.to_settings(self._output_picker.path())
        if not settings.output_dir or not Path(settings.output_dir).is_dir():
            QMessageBox.warning(self, "Output", "Seleziona una cartella di output valida.")
            return
        self._store.save_settings(settings)
        self._results.set_enabled(False)
        self._progress.reset(len(urls))
        slide_fade_in(self._activity_card)
        self._set_running(True)
        custom_filenames = self._url_input.custom_filenames()
        self._controller.start(urls, settings, custom_filenames)

    def _set_running(self, running: bool) -> None:
        self._start_btn.setEnabled(not running)
        self._start_btn.setText("Conversione in corso…" if running else "Converti")
        self._cancel_btn.setEnabled(running)

    def _on_finished(self, results: list[JobResult]) -> None:
        self._set_running(False)
        self._results.show_results(results, self._output_picker.path())
        fade_in(self._results)

    def _on_failed(self, message: str) -> None:
        self._set_running(False)
        QMessageBox.critical(self, "Errore", message)

    def _on_cancelled(self) -> None:
        self._set_running(False)
        QMessageBox.information(self, "Annullato", "Batch annullato.")

    def _on_clear(self) -> None:
        """Reset form to default values."""
        self._url_input._editor.clear()
        self._url_input._editor._custom_names.clear()
        self._url_input._update_counter()
        default_out = str(Path.home() / "Documents")
        default_settings = ConversionSettings(output_dir=default_out)
        self._options.load(default_settings)
        self._output_picker.set_path(default_out)
        self._progress.reset(0)
        self._results.set_enabled(False)

    def _update_theme_btn_text(self) -> None:
        icon = "☀️" if self._theme == "dark" else "🌙"
        label = "Chiaro" if self._theme == "dark" else "Scuro"
        self._theme_btn.setText(f"{icon}  {label}")

    def _toggle_theme(self) -> None:
        def swap() -> None:
            self._theme = "light" if self._theme == "dark" else "dark"
            apply_theme(QApplication.instance(), self._theme)
            self._update_theme_btn_text()
            self._store.save_theme(self._theme)

        cross_fade_swap(self.centralWidget(), swap)

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt override
        self._controller.shutdown()
        super().closeEvent(event)
