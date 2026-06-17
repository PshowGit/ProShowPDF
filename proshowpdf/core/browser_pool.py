"""Manages a single Chromium instance and per-URL isolated contexts."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from playwright.async_api import Browser, Playwright, async_playwright

from .models import ConversionSettings

log = logging.getLogger(__name__)

# A realistic desktop-Chrome User-Agent: the bundled Chromium's default UA
# contains "HeadlessChrome", which anti-bot services (e.g. Cloudflare) flag.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Injected before any page script runs to mask the most obvious automation
# tells, so bot challenges resolve instead of looping forever.
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['it-IT','it','en-US','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = window.chrome || {runtime: {}};
"""

# Hides the AutomationControlled blink feature (another navigator.webdriver tell).
_LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]


class BrowserPool:
    """Owns the Playwright driver and one reusable Chromium browser."""

    def __init__(self, settings: ConversionSettings) -> None:
        self._settings = settings
        self._pw: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=True, args=_LAUNCH_ARGS
        )
        log.info("Chromium launched")

    @asynccontextmanager
    async def new_page(self):
        """Yield a fresh page in an isolated context; always tears down."""
        assert self._browser is not None, "BrowserPool not started"
        context = await self._browser.new_context(
            viewport={"width": self._settings.width_px, "height": 1024},
            device_scale_factor=self._settings.device_scale_factor,
            user_agent=_USER_AGENT,
            locale="it-IT",
        )
        await context.add_init_script(_STEALTH_JS)
        page = await context.new_page()
        try:
            yield page
        finally:
            await context.close()

    async def close(self) -> None:
        """Close browser and driver; safe to call multiple times."""
        try:
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
        finally:
            if self._pw is not None:
                await self._pw.stop()
                self._pw = None
        log.info("Chromium closed")
