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


# Generic, language/site-agnostic removal of modal overlays that cover the
# page. Whatever paints on top at the viewport centre is almost always a
# blocking overlay (consent wall, welcome/region dialog) rather than page
# content: sticky headers are too short to reach the centre and the article
# body is not position:fixed. We strip the top-most large fixed ancestor at a
# few centre samples, then clear scroll locks so the revealed page measures
# correctly.
_REMOVE_OVERLAYS_JS = """
() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  if (!vw || !vh) return [];
  const removed = [];
  const samples = [[vw/2, vh/2], [vw/2, vh*0.35], [vw/2, vh*0.65]];
  for (let pass = 0; pass < 6; pass++) {
    let overlay = null;
    for (const [x, y] of samples) {
      let node = document.elementFromPoint(x, y);
      let candidate = null;
      while (node && node !== document.body && node !== document.documentElement) {
        const cs = getComputedStyle(node);
        if (cs.position === 'fixed') {
          const r = node.getBoundingClientRect();
          if (r.width >= vw * 0.5 && r.height >= vh * 0.4) candidate = node;
        }
        node = node.parentElement;
      }
      if (candidate) { overlay = candidate; break; }
    }
    if (!overlay) break;
    const cls = (overlay.className && overlay.className.toString)
      ? overlay.className.toString() : '';
    removed.push((overlay.id || cls || overlay.tagName).slice(0, 60));
    overlay.remove();
  }
  if (removed.length) {
    for (const el of [document.documentElement, document.body]) {
      el.style.setProperty('overflow', 'visible', 'important');
      el.style.setProperty('position', 'static', 'important');
    }
  }
  return removed;
}
"""


async def remove_blocking_overlays(page) -> int:
    """Strip modal overlays covering the page centre; return how many. Best effort."""
    try:
        removed = await page.evaluate(_REMOVE_OVERLAYS_JS)
    except Exception:
        return 0
    if removed:
        log.debug("Removed %d blocking overlay(s): %s", len(removed), removed)
    return len(removed)


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
