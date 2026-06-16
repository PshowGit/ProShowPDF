"""Manages a single Chromium instance and per-URL isolated contexts."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from playwright.async_api import Browser, Playwright, async_playwright

from .models import ConversionSettings

log = logging.getLogger(__name__)


class BrowserPool:
    """Owns the Playwright driver and one reusable Chromium browser."""

    def __init__(self, settings: ConversionSettings) -> None:
        self._settings = settings
        self._pw: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        log.info("Chromium launched")

    @asynccontextmanager
    async def new_page(self):
        """Yield a fresh page in an isolated context; always tears down."""
        assert self._browser is not None, "BrowserPool not started"
        context = await self._browser.new_context(
            viewport={"width": self._settings.width_px, "height": 1024},
            device_scale_factor=self._settings.device_scale_factor,
        )
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
