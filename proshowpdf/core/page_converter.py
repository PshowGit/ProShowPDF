"""Per-page conversion: load, dismiss banners, scroll, measure, render PDF.

`compute_pdf_height` is pure and unit-tested. `convert_page` drives a Playwright
`Page` and is exercised with a mock in tests.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeout

from .cookie_banner import (
    dismiss_cookie_banner,
    hide_chat_widgets,
    remove_blocking_overlays,
)
from .errors import (
    ConversionTimeoutError,
    NavigationError,
    OutputError,
    RenderError,
)
from .models import ConversionSettings
from .naming import build_pdf_name, resolve_collision
from .pdf_postprocess import trim_trailing_whitespace

# Substrings in a Playwright error that indicate a filesystem write failure
# rather than a rendering problem (so we can classify it as OutputError).
_OUTPUT_ERROR_HINTS = ("enoent", "eacces", "eperm", "enospc", "failed to write")

log = logging.getLogger(__name__)

# JS measuring the full document height across quirks.
_HEIGHT_JS = (
    "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight,"
    " document.body.offsetHeight, document.documentElement.offsetHeight)"
)
_SCROLL_STEP_JS = "window.scrollBy(0, window.innerHeight)"
_SCROLL_TOP_JS = "window.scrollTo(0, 0)"


# PDF pages cannot exceed 200 inches (14400 pt) per side or viewers like Adobe
# Reader treat the file as damaged. Stay just under to absorb rounding.
_MAX_PDF_INCHES = 199.0
_CSS_PX_PER_INCH = 96.0


def _navigated_away(current: str, original: str) -> bool:
    """True if a banner click left the originally requested page.

    Compares host and path (ignoring query/fragment) so a consent click that
    only tweaks query params is not mistaken for navigating off the page.
    """
    a, b = urlsplit(current), urlsplit(original)
    return (a.netloc, a.path) != (b.netloc, b.path)


def compute_pdf_height(measured: int, min_height: int) -> int:
    """Clamp a measured scrollHeight to at least `min_height`."""
    return max(int(measured), min_height)


def compute_pdf_dimensions(
    measured: int, width_px: int, min_height: int
) -> tuple[str, str]:
    """Return (width, height) strings for page.pdf, scaled to stay within the
    PDF 200-inch page limit so tall pages don't produce 'corrupted' files.

    Chrome lays the page out at the browser viewport width and scales that
    rendering to the paper size, so shrinking both paper dimensions by the same
    factor keeps the whole page on one valid page, just at a smaller scale.
    """
    height = compute_pdf_height(measured, min_height)
    height_in = height / _CSS_PX_PER_INCH
    if height_in <= _MAX_PDF_INCHES:
        return f"{width_px}px", f"{height}px"
    scale = _MAX_PDF_INCHES / height_in
    scaled_width_in = (width_px / _CSS_PX_PER_INCH) * scale
    return f"{scaled_width_in}in", f"{_MAX_PDF_INCHES}in"


async def _wait_settled(page, timeout_ms: int) -> None:
    """Wait for the page to go quiet again (e.g. after a consent reload)."""
    try:
        await page.wait_for_load_state(
            "networkidle", timeout=min(timeout_ms, 10_000)
        )
    except PlaywrightTimeout:
        log.debug("networkidle wait timed out after banner dismissal")
    await asyncio.sleep(0.3)


# Markers of an anti-bot interstitial (Cloudflare "Just a moment…" etc.) that
# precedes the real page; we wait for it to clear before measuring/rendering.
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "checking your browser",
    "verifying you are",
    "verifica di sicurezza",
)


async def _await_challenge_cleared(page, timeout_ms: int) -> None:
    """Poll until an anti-bot challenge page transitions to real content.

    Bounded by the page timeout (capped at 25s). Returns quietly if no challenge
    is present or it never clears — rendering then captures whatever is shown.
    """
    deadline = asyncio.get_event_loop().time() + min(timeout_ms / 1000, 25.0)
    while asyncio.get_event_loop().time() < deadline:
        try:
            title = (await page.title()).lower()
            body = (await page.inner_text("body"))[:400].lower()
        except Exception:
            await asyncio.sleep(0.5)
            continue
        if not any(m in title or m in body for m in _CHALLENGE_MARKERS):
            return
        await asyncio.sleep(1.0)
    log.debug("anti-bot challenge did not clear within budget")


async def _scroll_to_bottom(page, max_steps: int = 40) -> None:
    """Scroll the page to trigger lazy-loaded content, then return to top."""
    previous = -1
    for _ in range(max_steps):
        height = await page.evaluate(_HEIGHT_JS)
        if height == previous:
            break
        previous = height
        await page.evaluate(_SCROLL_STEP_JS)
        await asyncio.sleep(0.15)
    await page.evaluate(_SCROLL_TOP_JS)


async def convert_page(page, url: str, settings: ConversionSettings, custom_filename: str | None = None) -> str:
    """Convert one page to a single-page PDF; return the written file path."""
    output_dir = settings.output_dir
    if not os.path.isdir(output_dir) or not os.access(output_dir, os.W_OK):
        raise OutputError(f"Output directory not writable: {output_dir}")
    try:
        await page.emulate_media(media="screen")
        await page.goto(url, wait_until="domcontentloaded", timeout=settings.timeout_ms)
        # Sit through any anti-bot interstitial, then wait for the real page.
        await _await_challenge_cleared(page, settings.timeout_ms)
        await _wait_settled(page, settings.timeout_ms)
        if settings.handle_cookie_banners:
            target_url = page.url
            if await dismiss_cookie_banner(page):
                # Accepting can reload the page or load deferred content; wait
                # for it to settle, then sweep again for banners shown after.
                await _wait_settled(page, settings.timeout_ms)
                await dismiss_cookie_banner(page)
            # Generic catch-all for anything the semantic clicks missed (consent
            # walls in any language, region/welcome dialogs blocking the page).
            if await remove_blocking_overlays(page):
                await _wait_settled(page, settings.timeout_ms)
            # Safety net: if a misfired consent click navigated off the target
            # page (e.g. a policy link), restore it and only strip overlays,
            # which never navigate, so we still render the intended page.
            if _navigated_away(page.url, target_url):
                log.debug("Banner click left %s; restoring %s", page.url, url)
                await page.goto(
                    url, wait_until="domcontentloaded", timeout=settings.timeout_ms
                )
                await _await_challenge_cleared(page, settings.timeout_ms)
                await _wait_settled(page, settings.timeout_ms)
                await remove_blocking_overlays(page)
            # Hide floating chat/support widgets so they don't bake into the PDF.
            await hide_chat_widgets(page)
        await _scroll_to_bottom(page)
        try:
            await page.wait_for_function("document.fonts.ready", timeout=5000)
        except PlaywrightTimeout:
            log.debug("fonts.ready timed out for %s", url)

        measured = await page.evaluate(_HEIGHT_JS)
        pdf_width, pdf_height = compute_pdf_dimensions(
            measured, settings.width_px, settings.min_height_px
        )

        if custom_filename:
            from .naming import sanitize_filename
            filename = sanitize_filename(custom_filename) + ".pdf"
        else:
            title = await page.title()
            filename = build_pdf_name(title, url)
        target = resolve_collision(
            Path(settings.output_dir) / filename, settings.conflict_policy
        )

        await page.pdf(
            path=str(target),
            width=pdf_width,
            height=pdf_height,
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            scale=1.0,
        )
        # Chromium's PDF layout can render the page shorter than the measured
        # scrollHeight, leaving a blank band (with stray fixed widgets baked in)
        # after the footer. Crop it off; best-effort, never fails the conversion.
        await asyncio.to_thread(trim_trailing_whitespace, str(target))
        return str(target)
    except PlaywrightTimeout as exc:
        raise ConversionTimeoutError(str(exc)) from exc
    except PlaywrightError as exc:
        message = str(exc)
        lowered = message.lower()
        if any(hint in lowered for hint in _OUTPUT_ERROR_HINTS):
            raise OutputError(message) from exc
        if "net::" in message or "navigat" in lowered:
            raise NavigationError(message) from exc
        raise RenderError(message) from exc
