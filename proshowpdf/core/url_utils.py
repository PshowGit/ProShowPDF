"""URL validation, normalization and list parsing (text/.txt/.csv)."""
from __future__ import annotations

from urllib.parse import urlparse

_ALLOWED_SCHEMES = {"http", "https"}


def normalize_url(raw: str) -> str:
    """Trim whitespace and prepend https:// when no scheme is present."""
    url = raw.strip()
    if not url:
        return url
    if "://" not in url:
        url = "https://" + url
    return url


def is_valid_url(raw: str) -> bool:
    """True for syntactically valid http(s) URLs with a network location.

    The host must be non-empty and whitespace-free, so a typo like "not a url"
    (which would otherwise normalize to "https://not a url") is rejected rather
    than silently treated as a host.
    """
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.netloc:
        return False
    return not any(ch.isspace() for ch in parsed.netloc)


def parse_urls(text: str) -> list[str]:
    """Parse a blob of text (plain list or CSV) into normalized, unique URLs.

    Rules: skip blank lines and lines starting with '#'; for CSV-like lines
    (commas) take the first column; skip a header row whose first cell is 'url';
    normalize, validate and de-duplicate preserving order.
    """
    seen: set[str] = set()
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cell = stripped.split(",", 1)[0].strip()
        if cell.lower() == "url":
            continue
        url = normalize_url(cell)
        if is_valid_url(url) and url not in seen:
            seen.add(url)
            out.append(url)
    return out
