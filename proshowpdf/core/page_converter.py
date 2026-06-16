"""Per-page conversion: load, dismiss banners, scroll, measure, render PDF.

`compute_pdf_height` is pure and unit-tested. `convert_page` drives a Playwright
`Page` and is exercised with a mock in tests.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeout

from .cookie_banner import dismiss_cookie_banner
from .errors import (
    ConversionTimeoutError,
    NavigationError,
    OutputError,
    RenderError,
)
from .models import ConversionSettings
from .naming import build_pdf_name, resolve_collision

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


def compute_pdf_height(measured: int, min_height: int) -> int:
    """Clamp a measured scrollHeight to at least `min_height`."""
    return max(int(measured), min_height)


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
        await page.goto(url, wait_until="networkidle", timeout=settings.timeout_ms)
        if settings.handle_cookie_banners:
            await dismiss_cookie_banner(page)
        await _scroll_to_bottom(page)
        try:
            await page.wait_for_function("document.fonts.ready", timeout=5000)
        except PlaywrightTimeout:
            log.debug("fonts.ready timed out for %s", url)

        measured = await page.evaluate(_HEIGHT_JS)
        height = compute_pdf_height(measured, settings.min_height_px)

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
            width=f"{settings.width_px}px",
            height=f"{height}px",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            scale=1.0,
        )
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
