"""Structured rotating-file logging configured once at startup."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def log_dir() -> Path:
    """Per-user writable log directory (works when frozen by PyInstaller)."""
    base = os.environ.get("LOCALAPPDATA", str(Path.home()))
    path = Path(base) / "ProShowPDF" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logging(level: int = logging.INFO) -> Path:
    """Configure root logging to a rotating file + console. Returns log path."""
    log_file = log_dir() / "proshowpdf.log"
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    )
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console)
    return log_file
