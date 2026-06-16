"""Windows-safe filename generation and collision handling."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from .models import ConflictPolicy

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_MAX_LEN = 150


def sanitize_filename(name: str) -> str:
    """Make a string safe as a Windows filename stem."""
    cleaned = _ILLEGAL.sub("_", name).strip().strip(".").strip()
    if not cleaned:
        return "page"
    if cleaned.upper() in _RESERVED:
        cleaned = "_" + cleaned
    if len(cleaned) > _MAX_LEN:
        cleaned = cleaned[:_MAX_LEN].strip()
    return cleaned


def build_pdf_name(title: str, url: str) -> str:
    """Prefer the page title; fall back to domain + timestamp."""
    title = (title or "").strip()
    if title:
        return f"{sanitize_filename(title)}.pdf"
    domain = urlparse(url).netloc.removeprefix("www.") or "page"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{sanitize_filename(domain)}_{stamp}.pdf"


def resolve_collision(target: Path, policy: ConflictPolicy) -> Path:
    """Return a final path honoring the conflict policy."""
    if policy is ConflictPolicy.OVERWRITE or not target.exists():
        return target
    stem, suffix, parent = target.stem, target.suffix, target.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
