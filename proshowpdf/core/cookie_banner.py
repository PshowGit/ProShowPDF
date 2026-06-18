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
import re

log = logging.getLogger(__name__)

# Text labels matched as a WHOLE, case-insensitively, against a button's
# accessible name. Whole-string (not substring): substring matching makes "OK"
# hit "Informativa sui cOOKie" and "Accetta" hit "Non accettare". Matched only
# against role=button elements (button / [role=button] / <a role=button> /
# input) — never plain links, which usually navigate to policy pages.
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
    "#sp-cc-accept",  # Amazon consent
    "input#sp-cc-accept",
    "#wt-cli-accept-all-btn",  # WebToffee / WP Cookie Law Info
    "#cookie_action_close_header",
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


# Containers of well-known floating chat/support widgets. Vendor-specific and
# unambiguous, so hiding them can't drop real content — used as a precise pass
# on top of the generic geometric detection below (which catches the rest).
_WIDGET_SELECTORS = [
    "#hubspot-messages-iframe-container",                  # HubSpot
    "#intercom-container", ".intercom-lightweight-app",    # Intercom
    "#drift-frame-controller", "#drift-widget-container",  # Drift
    "#chat-widget-container", "#livechat-compact-container",  # LiveChat
    ".zEWidget-launcher", "iframe#webWidget",              # Zendesk
    "#tawkchat-container", "#tawkchat-minified-wrapper",   # Tawk.to
    "#crisp-chatbox", ".crisp-client",                     # Crisp
    "#tidio-chat", "#tidio-chat-iframe",                   # Tidio
    ".fb_dialog", ".fb-customerchat",                      # FB Messenger
    "#olark-wrapper",                                      # Olark
    "#fc_frame", "#freshworks-container",                  # Freshchat
    "#smartsupp-widget-container",                         # Smartsupp
    "#gorgias-chat-container",                             # Gorgias
    "#beacon-container",                                   # Help Scout Beacon
]

# Generic floating-widget removal. Two passes: (1) the known vendor containers
# above; (2) geometric detection of any `position:fixed` element docked to a
# viewport edge that is neither a full-width bar (header / announcement / cookie
# bar — left to the consent logic) nor a full-height side panel (could be real
# nav). That signature — edge-docked, not spanning a whole side — is what chat
# bubbles, social rails, "contact us" tabs, back-to-top and floating CTAs share,
# and they otherwise bake into the PDF as stray objects. Centre-covering modals
# are handled separately by `remove_blocking_overlays`.
_REMOVE_WIDGETS_JS = """
(selectors) => {
  const vw = window.innerWidth, vh = window.innerHeight;
  let n = 0;
  const hide = (el) => { el.style.setProperty('display', 'none', 'important'); n++; };
  for (const sel of selectors) {
    let els;
    try { els = document.querySelectorAll(sel); } catch (e) { continue; }
    for (const el of els) hide(el);
  }
  if (!vw || !vh) return n;
  const EDGE = 40;
  const cand = [];
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed') continue;
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 16 || r.height < 16) continue;
    if (r.width >= vw * 0.6) continue;     // full-width bar / header
    if (r.height >= vh * 0.8) continue;    // full-height side panel
    const docked = r.left <= EDGE || (vw - r.right) <= EDGE
                || r.top <= EDGE || (vh - r.bottom) <= EDGE;
    if (!docked) continue;
    cand.push(el);
  }
  for (const el of cand) {
    if (cand.some(o => o !== el && o.contains(el))) continue;  // keep outermost
    hide(el);
  }
  return n;
}
"""


async def remove_floating_widgets(page) -> int:
    """Hide floating widgets — known chat/support vendors plus generic
    edge-docked fixed widgets — so they don't bake into the PDF. Best effort."""
    try:
        n = await page.evaluate(_REMOVE_WIDGETS_JS, _WIDGET_SELECTORS)
    except Exception:
        return 0
    if n:
        log.debug("Hid %d floating widget(s)", n)
    return n


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
        # Whole-name, case-insensitive match on any role=button (covers
        # <button>, [role=button], <a role=button>, <input>). Playwright's
        # :text-is is case-sensitive, so a regex-named role lookup is used.
        name = re.compile(r"^\s*" + re.escape(text) + r"\s*$", re.IGNORECASE)
        if await _click_first_visible(
            page.get_by_role("button", name=name), timeout_ms
        ):
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
    """Click the first visible element matching a CSS selector; swallow errors."""
    try:
        locator = target.locator(selector)
    except Exception:
        return False
    return await _click_first_visible(locator, timeout_ms)


async def _click_first_visible(locator, timeout_ms: int) -> bool:
    """Click the first *visible* element the locator matches; swallow any error.

    Skips entirely when nothing matches (keeps the common, no-banner path fast).
    Iterates over matches because broad locators (e.g. a popup close button or a
    repeated accept label) can match several hidden duplicates before the live
    one; the bound caps how long a single stubborn locator can take.
    """
    try:
        count = await locator.count()
    except Exception:
        return False
    for i in range(min(count, 6)):
        candidate = locator.nth(i)
        try:
            if not await candidate.is_visible():
                continue
            await candidate.click(timeout=timeout_ms)
            log.debug("Dismissed banner/overlay")
            return True
        except Exception:
            continue
    return False
