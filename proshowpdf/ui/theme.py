"""Theme loading and dark/light switching."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

_QSS_DIR = Path(__file__).parent.parent / "resources" / "qss"


def available_themes() -> list[str]:
    return ["dark", "light"]


def apply_theme(app: QApplication, theme: str) -> None:
    """Load and apply the named QSS stylesheet to the application."""
    qss_file = _QSS_DIR / f"{theme}.qss"
    if qss_file.exists():
        app.setStyleSheet(qss_file.read_text(encoding="utf-8"))
