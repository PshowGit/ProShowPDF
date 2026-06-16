"""Batch orchestration: concurrency cap, retry/backoff, progress, cancellation."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from .browser_pool import BrowserPool
from .errors import ConversionError
from .models import ConversionSettings, JobItem, JobResult, JobStatus
from .page_converter import convert_page

log = logging.getLogger(__name__)

# Called from the worker loop on every status change. Signature:
# (result: JobResult, completed: int, total: int)
ProgressCallback = Callable[[JobResult, int, int], None]


class ConverterEngine:
    """Runs a batch of conversions against a shared browser pool."""

    def __init__(self, settings: ConversionSettings) -> None:
        self._settings = settings
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)

    async def run(
        self, urls: list[str], on_progress: ProgressCallback,
        custom_filenames: list[str | None] | None = None,
    ) -> list[JobResult]:
        items = [
            JobItem(url=u, index=i, custom_filename=custom_filenames[i] if custom_filenames else None)
            for i, u in enumerate(urls)
        ]
        total = len(items)
        completed = 0
        results: list[JobResult] = []
        pool = BrowserPool(self._settings)
        await pool.start()
        try:
            async def worker(item: JobItem) -> JobResult:
                nonlocal completed
                async with self._semaphore:
                    on_progress(
                        JobResult(item.url, item.index, JobStatus.RUNNING),
                        completed, total,
                    )
                    result = await self._convert_with_retry(pool, item)
                completed += 1
                on_progress(result, completed, total)
                return result

            tasks = [asyncio.create_task(worker(it)) for it in items]
            try:
                results = await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise
        finally:
            await pool.close()
        return results

    async def _convert_with_retry(
        self, pool: BrowserPool, item: JobItem
    ) -> JobResult:
        last_exc: Exception | None = None
        for attempt in range(self._settings.retries + 1):
            try:
                async with pool.new_page() as page:
                    path = await convert_page(page, item.url, self._settings, item.custom_filename)
                return JobResult(
                    item.url, item.index, JobStatus.DONE, output_path=path
                )
            except asyncio.CancelledError:
                raise
            except ConversionError as exc:
                last_exc = exc
                log.warning(
                    "Attempt %d failed for %s: %s", attempt + 1, item.url, exc
                )
                if attempt < self._settings.retries:
                    await asyncio.sleep(2 ** attempt)  # backoff: 1s, 2s, 4s
        error_type = getattr(last_exc, "error_type", "conversion_error")
        return JobResult(
            item.url, item.index, JobStatus.ERROR,
            error_type=error_type, error_message=str(last_exc),
        )
