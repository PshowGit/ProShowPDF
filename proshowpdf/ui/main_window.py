"""Main window: assembles widgets and wires controller signals."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QMainWindow, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from proshowpdf.bridge.controller import ConversionController
from proshowpdf.core.models import ConversionSettings, JobResult
from proshowpdf.persistence.settings_store import SettingsStore
from proshowpdf.ui.theme import apply_theme
from proshowpdf.ui.widgets.options_panel import OptionsPanel
from proshowpdf.ui.widgets.progress_view import ProgressView
from proshowpdf.ui.widgets.results_panel import ResultsPanel
from proshowpdf.ui.widgets.url_input import UrlInput

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, controller: ConversionController, store: SettingsStore) -> None:
        super().__init__()
        self._controller = controller
        self._store = store
        self._theme = store.load_theme()
        self.setWindowTitle("ProShow PDF")
        self.resize(900, 760)

        self._url_input = UrlInput()
        self._options = OptionsPanel()
        self._progress = ProgressView()
        self._results = ResultsPanel()

        default_out = str(Path.home() / "Documents")
        self._options.load(store.load_settings(default_out))

        central = QWidget()
        root = QVBoxLayout(central)
        root.addWidget(self._url_input)
        root.addWidget(self._options)

        buttons = QHBoxLayout()
        self._start_btn = QPushButton("Converti")
        self._cancel_btn = QPushButton("Annulla")
        self._cancel_btn.setObjectName("secondary")
        self._cancel_btn.setEnabled(False)
        self._theme_btn = QPushButton("Tema chiaro/scuro")
        self._theme_btn.setObjectName("secondary")
        buttons.addWidget(self._start_btn)
        buttons.addWidget(self._cancel_btn)
        buttons.addStretch()
        buttons.addWidget(self._theme_btn)
        root.addLayout(buttons)

        root.addWidget(self._progress)
        root.addWidget(self._results)
        self.setCentralWidget(central)

        self._start_btn.clicked.connect(self._on_start)
        self._cancel_btn.clicked.connect(self._controller.cancel)
        self._theme_btn.clicked.connect(self._toggle_theme)
        controller.progress.connect(self._progress.update)
        controller.finished.connect(self._on_finished)
        controller.failed.connect(self._on_failed)
        controller.cancelled.connect(self._on_cancelled)

    def _on_start(self) -> None:
        urls = self._url_input.urls()
        if not urls:
            QMessageBox.warning(self, "Nessun URL", "Inserisci almeno un URL valido.")
            return
        settings = self._options.to_settings()
        if not settings.output_dir or not Path(settings.output_dir).is_dir():
            QMessageBox.warning(self, "Output", "Seleziona una cartella di output valida.")
            return
        self._store.save_settings(settings)
        self._results.set_enabled(False)
        self._progress.reset(len(urls))
        self._set_running(True)
        self._controller.start(urls, settings)

    def _set_running(self, running: bool) -> None:
        self._start_btn.setEnabled(not running)
        self._cancel_btn.setEnabled(running)

    def _on_finished(self, results: list[JobResult]) -> None:
        self._set_running(False)
        self._results.show_results(results, self._options.to_settings().output_dir)

    def _on_failed(self, message: str) -> None:
        self._set_running(False)
        QMessageBox.critical(self, "Errore", message)

    def _on_cancelled(self) -> None:
        self._set_running(False)
        QMessageBox.information(self, "Annullato", "Batch annullato.")

    def _toggle_theme(self) -> None:
        self._theme = "light" if self._theme == "dark" else "dark"
        apply_theme(QApplication.instance(), self._theme)
        self._store.save_theme(self._theme)

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt override
        self._controller.shutdown()
        super().closeEvent(event)
