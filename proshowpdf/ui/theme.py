"""Theme loading and dark/light switching."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

_QSS_DIR = Path(__file__).parent.parent / "resources" / "qss"


def available_themes() -> list[str]:
    return ["dark", "light"]


def apply_theme(app: QApplication, theme: str) -> None:
    """Load and apply the named QSS stylesheet to the application.

    QSS loaded from a string resolves ``url()`` paths against the working
    directory, so the ``__ICONS__`` token is replaced with an absolute,
    forward-slash path to the bundled icons before the sheet is applied.
    """
    qss_file = _QSS_DIR / f"{theme}.qss"
    if qss_file.exists():
        css = qss_file.read_text(encoding="utf-8")
        icons_dir = (_QSS_DIR.parent / "icons").as_posix()
        css = css.replace("__ICONS__", icons_dir)
        app.setStyleSheet(css)
