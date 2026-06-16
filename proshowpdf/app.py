"""QApplication bootstrap: High-DPI, theme, controller, main window."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from proshowpdf.bridge.controller import ConversionController
from proshowpdf.logging_setup import setup_logging
from proshowpdf.persistence.settings_store import SettingsStore
from proshowpdf.ui.main_window import MainWindow
from proshowpdf.ui.theme import apply_theme


def run() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("ProShow PDF")
    app.setOrganizationName("ProfessionalShow")

    store = SettingsStore()
    apply_theme(app, store.load_theme())

    controller = ConversionController()
    controller.start_engine()

    window = MainWindow(controller, store)
    window.show()
    return app.exec()
