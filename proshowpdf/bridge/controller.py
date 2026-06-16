"""Bridge: runs the async engine in a dedicated thread, emits Qt signals.

The GUI talks ONLY to this object. It never touches Playwright or asyncio
directly. All cross-thread communication uses Qt signals (thread-safe).
"""
from __future__ import annotations

import asyncio
import logging
import threading

from PySide6.QtCore import QObject, Signal

from proshowpdf.core.converter_engine import ConverterEngine
from proshowpdf.core.models import ConversionSettings, JobResult

log = logging.getLogger(__name__)


class ConversionController(QObject):
    """Owns the worker thread + asyncio loop; exposes start()/cancel()."""

    progress = Signal(object, int, int)   # (JobResult, completed, total)
    finished = Signal(list)               # list[JobResult]
    failed = Signal(str)                  # fatal error message
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._run_task: asyncio.Future | None = None
        self._ready = threading.Event()

    def start_engine(self) -> None:
        """Spin up the background thread hosting the asyncio loop."""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ready.wait()

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    def start(self, urls: list[str], settings: ConversionSettings,
              custom_filenames: list[str | None] | None = None) -> None:
        """Schedule a batch on the worker loop (returns immediately)."""
        assert self._loop is not None, "engine not started"
        self._run_task = asyncio.run_coroutine_threadsafe(
            self._run(urls, settings, custom_filenames), self._loop
        )

    async def _run(self, urls: list[str], settings: ConversionSettings,
                   custom_filenames: list[str | None] | None = None) -> None:
        engine = ConverterEngine(settings)

        def on_progress(result: JobResult, completed: int, total: int) -> None:
            self.progress.emit(result, completed, total)

        try:
            results = await engine.run(urls, on_progress, custom_filenames)
            self.finished.emit(results)
        except asyncio.CancelledError:
            self.cancelled.emit()
        except Exception as exc:  # noqa: BLE001 — surface any fatal error to UI
            log.exception("Fatal batch error")
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        """Request cooperative cancellation of the running batch."""
        if self._run_task is not None and self._loop is not None:
            self._loop.call_soon_threadsafe(self._run_task.cancel)

    def shutdown(self) -> None:
        """Stop the loop and join the thread on app exit."""
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5)
