"""Background check for a newer release on GitHub; notify without blocking UI.

`is_newer`/`_parse_version` are pure and unit-tested. `fetch_latest_release`
does the network call (stdlib only). `UpdateChecker` runs the check on a worker
thread and emits a Qt signal when a newer release exists; all failures are
swallowed so a flaky network never disrupts startup.
"""
from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal

from proshowpdf import __version__

log = logging.getLogger(__name__)

# Repo that publishes releases; the zip is attached to each GitHub Release.
_RELEASES_API = "https://api.github.com/repos/PshowGit/ProShowPDF/releases/latest"
_TIMEOUT_S = 6


def _parse_version(tag: str) -> tuple[int, ...]:
    """Parse 'v1.2.3' / '1.2.3' into a comparable int tuple; junk parts -> 0."""
    cleaned = tag.strip().lstrip("vV")
    parts = []
    for chunk in cleaned.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


def is_newer(latest: str, current: str) -> bool:
    """True if `latest` is a strictly newer version than `current`."""
    lt, ct = _parse_version(latest), _parse_version(current)
    width = max(len(lt), len(ct))
    lt += (0,) * (width - len(lt))
    ct += (0,) * (width - len(ct))
    return lt > ct


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    url: str  # the release page to open in a browser


def fetch_latest_release() -> ReleaseInfo | None:
    """Return the latest GitHub release, or None on any failure."""
    request = urllib.request.Request(
        _RELEASES_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "ProShowPDF"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
            data = json.load(response)
    except Exception as exc:  # network, JSON, HTTP — all non-fatal
        log.debug("Update check failed: %s", exc)
        return None
    tag, url = data.get("tag_name"), data.get("html_url")
    if not tag or not url:
        return None
    return ReleaseInfo(version=str(tag), url=str(url))


class UpdateChecker(QThread):
    """Worker thread that emits `update_available(version, url)` when a newer
    release than the running version is published. Silent otherwise."""

    update_available = Signal(str, str)

    def __init__(self, current_version: str = __version__, parent=None) -> None:
        super().__init__(parent)
        self._current = current_version

    def run(self) -> None:  # noqa: D401 — QThread entry point
        info = fetch_latest_release()
        if info and is_newer(info.version, self._current):
            log.info("Update available: %s (current %s)", info.version, self._current)
            self.update_available.emit(info.version, info.url)
