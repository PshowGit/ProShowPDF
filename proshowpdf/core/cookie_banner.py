"""Best-effort dismissal of common cookie/consent banners.

Heuristics only — no external dependency. Never raises: failures are swallowed
so a stubborn banner never aborts a conversion.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Text labels (case-insensitive) commonly used by accept/close buttons.
_ACCEPT_TEXTS = [
    "Accept all", "Accept All", "Accetta tutto", "Accetta tutti",
    "Accetta", "Accept", "Acconsento", "I agree", "Agree",
    "OK", "Got it", "Consenti tutti", "Allow all",
]

# CSS selectors for well-known consent platforms.
_KNOWN_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "button#didomi-notice-agree-button",
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    ".cc-allow",
    "[aria-label='Accept cookies']",
]


async def dismiss_cookie_banner(page, timeout_ms: int = 800) -> bool:
    """Try to close/accept a consent banner. Returns True if something clicked.

    Each probe first checks whether the selector matches anything (a cheap,
    non-blocking `count()`) before attempting a timed click, so banner-free
    pages return almost immediately instead of paying a click timeout per probe.
    """
    for selector in _KNOWN_SELECTORS:
        if await _try_click(page, selector, timeout_ms):
            return True
    for text in _ACCEPT_TEXTS:
        if await _try_click(page, f"button:has-text('{text}')", timeout_ms):
            return True
    # Some consent UIs live in an iframe (e.g. Didomi/Sourcepoint).
    for frame in page.frames:
        for selector in _KNOWN_SELECTORS:
            if await _try_click(frame, selector, timeout_ms):
                return True
    return False


async def _try_click(target, selector: str, timeout_ms: int) -> bool:
    """Click the first matching visible element; swallow any error.

    Skips the timed click entirely when the selector matches no element, which
    keeps the common (no-banner) path fast.
    """
    try:
        locator = target.locator(selector)
        if await locator.count() == 0:
            return False
        await locator.first.click(timeout=timeout_ms)
        log.debug("Dismissed banner via %s", selector)
        return True
    except Exception:
        return False
