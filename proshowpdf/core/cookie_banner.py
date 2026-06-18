"""Best-effort dismissal of cookie/consent banners and blocking overlay popups.

Heuristics only — no external dependency. Never raises: failures are swallowed
so a stubborn banner never aborts a conversion. Dismissal loops a few rounds so
stacked or re-appearing banners all get clicked. Beyond consent banners this
also closes intrusive overlay windows (region/location selectors, welcome
dialogs) that sit over the page via their explicit close affordance.
"""
from __future__ import annotations

import asyncio
import logging

log = logging.getLogger(__name__)

# Text labels (case-insensitive substring, matched via Playwright :has-text)
# commonly used by accept/close buttons.
_ACCEPT_TEXTS = [
    "Accetta tutti i cookie", "Accetta tutto", "Accetta tutti",
    "Accetto", "Accetta", "Acconsento", "Consenti tutti",
    "Accept all cookies", "Accept all", "Accept", "Allow all", "I agree",
    "Agree", "Got it", "Ho capito", "OK",
]

# CSS selectors for well-known consent platforms. Partial-class matches keep
# these resilient to extra utility classes around the accept button.
_KNOWN_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "button#didomi-notice-agree-button",
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    "#CybotCookiebotDialogBodyButtonAccept",
    'button[class*="x13eucookies__btn--accept"]',
    'button[class*="accept-all"]',
    'button[class*="acceptAll"]',
    ".cc-allow",
    ".cc-dismiss",
    "[aria-label='Accept cookies']",
    "[aria-label='Accept all']",
]

# Close affordances for blocking overlay popups/modals that sit over the page
# (region/location selectors, welcome dialogs, newsletter boxes). Scoped to
# popup/modal/dialog containers so we click an explicit close control rather
# than page content; case-insensitive so PopupBox/popupbox both match.
_CLOSE_SELECTORS = [
    '[class*="popup" i] a.close',
    '[class*="popup" i] .close',
    '[class*="modal" i] [class*="close" i]',
    '[role="dialog"] [class*="close" i]',
    "[role='dialog'] [aria-label='Close' i]",
    "[aria-label='Close' i]",
    "button.close",
]


async def dismiss_cookie_banner(page, timeout_ms: int = 1000, rounds: int = 4) -> int:
    """Click accept/close on consent banners; return how many were dismissed.

    Loops up to ``rounds`` times because some sites stack banners (e.g. a cookie
    notice plus a newsletter/age popup) or re-show one after the first reload.
    """
    total = 0
    for _ in range(rounds):
        if await _dismiss_once(page, timeout_ms):
            total += 1
            await asyncio.sleep(0.5)  # let the banner animate out / DOM settle
        else:
            break
    if total:
        log.debug("Dismissed %d banner(s)", total)
    return total


async def _dismiss_once(page, timeout_ms: int) -> bool:
    """One pass: known selectors, accept-text buttons, overlay-close, iframes."""
    for selector in _KNOWN_SELECTORS:
        if await _try_click(page, selector, timeout_ms):
            return True
    for text in _ACCEPT_TEXTS:
        if await _try_click(page, f"button:has-text('{text}')", timeout_ms):
            return True
        if await _try_click(page, f"a:has-text('{text}')", timeout_ms):
            return True
    for selector in _CLOSE_SELECTORS:
        if await _try_click(page, selector, timeout_ms):
            return True
    # Some consent UIs live in an iframe (e.g. Didomi/Sourcepoint).
    for frame in page.frames:
        for selector in _KNOWN_SELECTORS:
            if await _try_click(frame, selector, timeout_ms):
                return True
    return False


async def _try_click(target, selector: str, timeout_ms: int) -> bool:
    """Click the first *visible* matching element; swallow any error.

    Skips entirely when the selector matches no element (keeps the common,
    no-banner path fast). Iterates over matches because broad selectors (e.g. a
    popup's close button) can match several hidden duplicates before the live
    one; the bound caps how long a single stubborn selector can take.
    """
    try:
        locator = target.locator(selector)
        count = await locator.count()
    except Exception:
        return False
    for i in range(min(count, 6)):
        candidate = locator.nth(i)
        try:
            if not await candidate.is_visible():
                continue
            await candidate.click(timeout=timeout_ms)
            log.debug("Dismissed banner/overlay via %s", selector)
            return True
        except Exception:
            continue
    return False
