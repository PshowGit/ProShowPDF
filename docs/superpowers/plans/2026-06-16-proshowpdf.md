# ProShow PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows x64 desktop app (PySide6 + Playwright) that converts web pages to single-page continuous PDFs preserving on-screen fidelity, with batch concurrency, cancellation, error reporting and a modern themed GUI.

**Architecture:** Three layers with strict boundaries. `core/` is pure (no Qt) and holds the conversion logic driven by Playwright's async API. `bridge/` is a `ConversionController(QObject)` running an asyncio event loop inside a dedicated QThread, translating UI commands to coroutines and async events to Qt signals. `ui/` is pure PySide6. A single Chromium instance is reused for the whole batch; an `asyncio.Semaphore` caps concurrency; cancellation closes pages/contexts/browser cleanly.

**Tech Stack:** Python 3.13, PySide6, Playwright (Chromium, async API), pytest + pytest-asyncio, PyInstaller (onedir).

---

## File Structure & Responsibilities

| File | Responsibility |
|------|----------------|
| `proshowpdf/core/models.py` | Dataclasses & enums: `ConversionSettings`, `JobItem`, `JobResult`, `JobStatus`, `ConflictPolicy` |
| `proshowpdf/core/errors.py` | Typed exception hierarchy |
| `proshowpdf/core/url_utils.py` | URL validation/normalization, parse text/.txt/.csv |
| `proshowpdf/core/naming.py` | Windows-safe filenames, collision resolution |
| `proshowpdf/core/cookie_banner.py` | Heuristic consent-banner dismissal (toggleable) |
| `proshowpdf/core/page_converter.py` | Per-page flow + pure dimension helper |
| `proshowpdf/core/browser_pool.py` | Playwright lifecycle, single browser, semaphore, contexts |
| `proshowpdf/core/converter_engine.py` | Batch orchestration, retry/backoff, progress, cancellation |
| `proshowpdf/bridge/controller.py` | QThread + asyncio loop, Qt signals |
| `proshowpdf/persistence/settings_store.py` | QSettings wrapper |
| `proshowpdf/logging_setup.py` | Rotating file logging |
| `proshowpdf/ui/theme.py` | QSS loading, dark/light switch |
| `proshowpdf/ui/animations.py` | QPropertyAnimation helpers |
| `proshowpdf/ui/widgets/*.py` | Input, options, progress, results widgets |
| `proshowpdf/ui/main_window.py` | Assembles widgets, wires controller signals |
| `proshowpdf/app.py` | QApplication bootstrap, High-DPI, theme |
| `proshowpdf/__main__.py` | x64 guard, entrypoint |
| `packaging/proshowpdf.spec` + `build.md` | PyInstaller onedir build |

Defaults (confirmed): parallelism 3, width 1280px, timeout 30s, retries 2; PDF name = page title, fallback domain+timestamp.

---

## Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`, `pyproject.toml`
- Create: `proshowpdf/__init__.py`, `proshowpdf/core/__init__.py`, `proshowpdf/bridge/__init__.py`, `proshowpdf/ui/__init__.py`, `proshowpdf/ui/widgets/__init__.py`, `proshowpdf/persistence/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `requirements.txt`**

```
PySide6==6.8.1
playwright==1.49.0
```

(dev extras in `pyproject.toml`)

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "proshowpdf"
version = "1.0.0"
description = "Web-to-PDF converter (Windows x64) — PySide6 + Playwright"
requires-python = ">=3.13"

[project.optional-dependencies]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "pyinstaller>=6.11"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.setuptools.packages.find]
include = ["proshowpdf*"]
```

- [ ] **Step 3: Create all `__init__.py` files**

`proshowpdf/__init__.py`:
```python
"""ProShow PDF — Web-to-PDF converter for Windows x64."""

__version__ = "1.0.0"
```

All other `__init__.py` files: empty.

- [ ] **Step 4: Set up venv and install**

Run:
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -U pip
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/playwright install chromium
```
Expected: all installs succeed.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt pyproject.toml proshowpdf tests
git commit -m "chore: project scaffolding"
```

---

## Task 2: Core models

**Files:**
- Create: `proshowpdf/core/models.py`

- [ ] **Step 1: Write `models.py`**

```python
"""Pure data models shared across the core layer. No Qt, no Playwright."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class ConflictPolicy(str, Enum):
    OVERWRITE = "overwrite"
    RENAME = "rename"


@dataclass(frozen=True)
class ConversionSettings:
    """User-tunable conversion parameters."""
    output_dir: str
    width_px: int = 1280
    max_concurrency: int = 3
    timeout_ms: int = 30_000
    retries: int = 2
    handle_cookie_banners: bool = True
    conflict_policy: ConflictPolicy = ConflictPolicy.RENAME
    device_scale_factor: float = 1.0
    min_height_px: int = 100


@dataclass
class JobItem:
    """A single URL to convert."""
    url: str
    index: int
    status: JobStatus = JobStatus.QUEUED


@dataclass
class JobResult:
    """Outcome of one conversion."""
    url: str
    index: int
    status: JobStatus
    output_path: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
```

- [ ] **Step 2: Smoke-import**

Run: `.venv/Scripts/python -c "from proshowpdf.core.models import ConversionSettings; print(ConversionSettings(output_dir='.').width_px)"`
Expected: prints `1280`.

- [ ] **Step 3: Commit**

```bash
git add proshowpdf/core/models.py
git commit -m "feat(core): conversion data models"
```

---

## Task 3: Typed errors

**Files:**
- Create: `proshowpdf/core/errors.py`

- [ ] **Step 1: Write `errors.py`**

```python
"""Typed exception hierarchy for conversion failures."""
from __future__ import annotations


class ConversionError(Exception):
    """Base class for all conversion errors."""
    error_type = "conversion_error"


class NavigationError(ConversionError):
    """Page failed to navigate (DNS, connection, HTTP error)."""
    error_type = "navigation"


class ConversionTimeoutError(ConversionError):
    """Navigation or rendering exceeded the configured timeout."""
    error_type = "timeout"


class RenderError(ConversionError):
    """Page loaded but PDF rendering/measurement failed."""
    error_type = "render"


class OutputError(ConversionError):
    """Failed to write the PDF to disk."""
    error_type = "output"
```

- [ ] **Step 2: Smoke-import**

Run: `.venv/Scripts/python -c "from proshowpdf.core.errors import NavigationError; print(NavigationError.error_type)"`
Expected: prints `navigation`.

- [ ] **Step 3: Commit**

```bash
git add proshowpdf/core/errors.py
git commit -m "feat(core): typed error hierarchy"
```

---

## Task 4: URL utilities (TDD)

**Files:**
- Create: `proshowpdf/core/url_utils.py`
- Test: `tests/test_url_utils.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_url_utils.py
import pytest
from proshowpdf.core.url_utils import normalize_url, is_valid_url, parse_urls


@pytest.mark.parametrize("raw,expected", [
    ("example.com", "https://example.com"),
    ("  https://a.com/path  ", "https://a.com/path"),
    ("http://x.com", "http://x.com"),
])
def test_normalize_adds_scheme_and_trims(raw, expected):
    assert normalize_url(raw) == expected


def test_is_valid_url():
    assert is_valid_url("https://example.com")
    assert not is_valid_url("not a url")
    assert not is_valid_url("")
    assert not is_valid_url("ftp://example.com")


def test_parse_urls_dedups_and_skips_blanks_and_comments():
    text = "example.com\n\n# comment\nexample.com\nhttps://b.com\n"
    assert parse_urls(text) == ["https://example.com", "https://b.com"]


def test_parse_urls_handles_csv_first_column():
    text = "url,note\nexample.com,hi\nb.com,bye"
    assert parse_urls(text) == ["https://example.com", "https://b.com"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/pytest tests/test_url_utils.py -v`
Expected: FAIL — `ModuleNotFoundError: proshowpdf.core.url_utils`.

- [ ] **Step 3: Write `url_utils.py`**

```python
"""URL validation, normalization and list parsing (text/.txt/.csv)."""
from __future__ import annotations

from urllib.parse import urlparse

_ALLOWED_SCHEMES = {"http", "https"}


def normalize_url(raw: str) -> str:
    """Trim whitespace and prepend https:// when no scheme is present."""
    url = raw.strip()
    if not url:
        return url
    if "://" not in url:
        url = "https://" + url
    return url


def is_valid_url(raw: str) -> bool:
    """True for syntactically valid http(s) URLs with a network location."""
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    return parsed.scheme in _ALLOWED_SCHEMES and bool(parsed.netloc)


def parse_urls(text: str) -> list[str]:
    """Parse a blob of text (plain list or CSV) into normalized, unique URLs.

    Rules: skip blank lines and lines starting with '#'; for CSV-like lines
    (commas) take the first column; skip a header row whose first cell is 'url';
    normalize, validate and de-duplicate preserving order.
    """
    seen: set[str] = set()
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cell = stripped.split(",", 1)[0].strip()
        if cell.lower() == "url":
            continue
        url = normalize_url(cell)
        if is_valid_url(url) and url not in seen:
            seen.add(url)
            out.append(url)
    return out
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/pytest tests/test_url_utils.py -v`
Expected: PASS (all cases).

- [ ] **Step 5: Commit**

```bash
git add proshowpdf/core/url_utils.py tests/test_url_utils.py
git commit -m "feat(core): URL normalization and parsing"
```

---

## Task 5: Safe filenames (TDD)

**Files:**
- Create: `proshowpdf/core/naming.py`
- Test: `tests/test_naming.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_naming.py
from proshowpdf.core.naming import sanitize_filename, build_pdf_name, resolve_collision
from proshowpdf.core.models import ConflictPolicy


def test_sanitize_removes_illegal_windows_chars():
    assert sanitize_filename('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"


def test_sanitize_trims_dots_spaces_and_reserved_names():
    assert sanitize_filename("  hello.  ") == "hello"
    assert sanitize_filename("CON") == "_CON"
    assert sanitize_filename("") == "page"


def test_sanitize_truncates_long_names():
    assert len(sanitize_filename("x" * 300)) <= 150


def test_build_pdf_name_prefers_title():
    assert build_pdf_name("My Page", "https://x.com").endswith(".pdf")
    assert build_pdf_name("My Page", "https://x.com").startswith("My Page")


def test_build_pdf_name_falls_back_to_domain_and_timestamp():
    name = build_pdf_name("", "https://www.example.com/path")
    assert name.startswith("example.com_")
    assert name.endswith(".pdf")


def test_resolve_collision_rename(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"x")
    result = resolve_collision(tmp_path / "a.pdf", ConflictPolicy.RENAME)
    assert result.name == "a (1).pdf"


def test_resolve_collision_overwrite(tmp_path):
    target = tmp_path / "a.pdf"
    target.write_bytes(b"x")
    assert resolve_collision(target, ConflictPolicy.OVERWRITE) == target
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/pytest tests/test_naming.py -v`
Expected: FAIL — `ModuleNotFoundError: proshowpdf.core.naming`.

- [ ] **Step 3: Write `naming.py`**

```python
"""Windows-safe filename generation and collision handling."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from .models import ConflictPolicy

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_MAX_LEN = 150


def sanitize_filename(name: str) -> str:
    """Make a string safe as a Windows filename stem."""
    cleaned = _ILLEGAL.sub("_", name).strip().strip(".").strip()
    if not cleaned:
        return "page"
    if cleaned.upper() in _RESERVED:
        cleaned = "_" + cleaned
    if len(cleaned) > _MAX_LEN:
        cleaned = cleaned[:_MAX_LEN].strip()
    return cleaned


def build_pdf_name(title: str, url: str) -> str:
    """Prefer the page title; fall back to domain + timestamp."""
    title = (title or "").strip()
    if title:
        return f"{sanitize_filename(title)}.pdf"
    domain = urlparse(url).netloc.removeprefix("www.") or "page"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{sanitize_filename(domain)}_{stamp}.pdf"


def resolve_collision(target: Path, policy: ConflictPolicy) -> Path:
    """Return a final path honoring the conflict policy."""
    if policy is ConflictPolicy.OVERWRITE or not target.exists():
        return target
    stem, suffix, parent = target.stem, target.suffix, target.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/pytest tests/test_naming.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add proshowpdf/core/naming.py tests/test_naming.py
git commit -m "feat(core): safe filenames and collision policy"
```

---

## Task 6: Cookie banner heuristics

**Files:**
- Create: `proshowpdf/core/cookie_banner.py`

- [ ] **Step 1: Write `cookie_banner.py`**

```python
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


async def dismiss_cookie_banner(page, timeout_ms: int = 2500) -> bool:
    """Try to close/accept a consent banner. Returns True if something clicked."""
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
    """Click the first matching visible element; swallow any error."""
    try:
        locator = target.locator(selector).first
        await locator.click(timeout=timeout_ms)
        log.debug("Dismissed banner via %s", selector)
        return True
    except Exception:
        return False
```

- [ ] **Step 2: Smoke-import**

Run: `.venv/Scripts/python -c "from proshowpdf.core.cookie_banner import dismiss_cookie_banner; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add proshowpdf/core/cookie_banner.py
git commit -m "feat(core): cookie banner heuristics"
```

---

## Task 7: Page converter — pure helper first (TDD)

**Files:**
- Create: `proshowpdf/core/page_converter.py`
- Test: `tests/test_page_converter.py`

- [ ] **Step 1: Write the failing test (pure dimension logic + async flow with mock)**

```python
# tests/test_page_converter.py
from unittest.mock import AsyncMock

import pytest

from proshowpdf.core.models import ConversionSettings
from proshowpdf.core.page_converter import compute_pdf_height, convert_page


def test_compute_pdf_height_uses_measured_value():
    assert compute_pdf_height(2400, min_height=100) == 2400


def test_compute_pdf_height_enforces_minimum():
    assert compute_pdf_height(0, min_height=100) == 100
    assert compute_pdf_height(-5, min_height=100) == 100


@pytest.mark.asyncio
async def test_convert_page_measures_height_and_calls_pdf(tmp_path):
    page = AsyncMock()
    page.title = AsyncMock(return_value="Hello")

    # The mock distinguishes height-measuring evaluate() calls (the JS contains
    # "scrollHeight") from scroll calls (scrollBy/scrollTo), which return None.
    # Heights: 800 then stable 1500 -> the scroll loop stops when height stops
    # growing; the last value is the final measurement used for the PDF.
    heights = iter([800, 1500, 1500, 1500])

    async def fake_evaluate(script, *args, **kwargs):
        if "scrollHeight" in script:
            return next(heights)
        return None

    page.evaluate = AsyncMock(side_effect=fake_evaluate)
    settings = ConversionSettings(output_dir=str(tmp_path), width_px=1280)

    out_path = await convert_page(page, "https://x.com", settings)

    page.goto.assert_awaited()
    page.pdf.assert_awaited()
    kwargs = page.pdf.await_args.kwargs
    assert kwargs["print_background"] is True
    assert kwargs["width"] == "1280px"
    assert kwargs["height"] == "1500px"
    assert kwargs["margin"] == {"top": 0, "right": 0, "bottom": 0, "left": 0}
    assert out_path.endswith(".pdf")
```

> Note: `_scroll_to_bottom` calls `evaluate` twice per iteration (height read +
> `scrollBy`) plus a final `scrollTo(0,0)`; `convert_page` then does one final
> height read. The mock keys off `"scrollHeight"` in the JS so only the four
> genuine height reads (`800, 1500, 1500, 1500`) consume the `heights` iterator —
> robust to the exact number of scroll calls.

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/pytest tests/test_page_converter.py -v`
Expected: FAIL — module/function not defined.

- [ ] **Step 3: Write `page_converter.py`**

```python
"""Per-page conversion: load, dismiss banners, scroll, measure, render PDF.

`compute_pdf_height` is pure and unit-tested. `convert_page` drives a Playwright
`Page` and is exercised with a mock in tests.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeout

from .cookie_banner import dismiss_cookie_banner
from .errors import ConversionTimeoutError, NavigationError, RenderError
from .models import ConversionSettings
from .naming import build_pdf_name, resolve_collision

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


async def convert_page(page, url: str, settings: ConversionSettings) -> str:
    """Convert one page to a single-page PDF; return the written file path."""
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
            margin={"top": 0, "right": 0, "bottom": 0, "left": 0},
            scale=1.0,
        )
        return str(target)
    except PlaywrightTimeout as exc:
        raise ConversionTimeoutError(str(exc)) from exc
    except PlaywrightError as exc:
        message = str(exc)
        if "net::" in message or "navigat" in message.lower():
            raise NavigationError(message) from exc
        raise RenderError(message) from exc
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/pytest tests/test_page_converter.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add proshowpdf/core/page_converter.py tests/test_page_converter.py
git commit -m "feat(core): per-page converter with dynamic height"
```

---

## Task 8: Browser pool

**Files:**
- Create: `proshowpdf/core/browser_pool.py`

- [ ] **Step 1: Write `browser_pool.py`**

```python
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
```

- [ ] **Step 2: Smoke-import**

Run: `.venv/Scripts/python -c "from proshowpdf.core.browser_pool import BrowserPool; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add proshowpdf/core/browser_pool.py
git commit -m "feat(core): single-browser pool with isolated contexts"
```

---

## Task 9: Converter engine (batch orchestration)

**Files:**
- Create: `proshowpdf/core/converter_engine.py`

- [ ] **Step 1: Write `converter_engine.py`**

```python
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
        self, urls: list[str], on_progress: ProgressCallback
    ) -> list[JobResult]:
        items = [JobItem(url=u, index=i) for i, u in enumerate(urls)]
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
                    path = await convert_page(page, item.url, self._settings)
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
```

- [ ] **Step 2: Smoke-import**

Run: `.venv/Scripts/python -c "from proshowpdf.core.converter_engine import ConverterEngine; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add proshowpdf/core/converter_engine.py
git commit -m "feat(core): batch engine with retry, backoff, cancellation"
```

---

## Task 10: Logging setup

**Files:**
- Create: `proshowpdf/logging_setup.py`

- [ ] **Step 1: Write `logging_setup.py`**

```python
"""Structured rotating-file logging configured once at startup."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def log_dir() -> Path:
    """Per-user writable log directory (works when frozen by PyInstaller)."""
    base = os.environ.get("LOCALAPPDATA", str(Path.home()))
    path = Path(base) / "ProShowPDF" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logging(level: int = logging.INFO) -> Path:
    """Configure root logging to a rotating file + console. Returns log path."""
    log_file = log_dir() / "proshowpdf.log"
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    )
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console)
    return log_file
```

- [ ] **Step 2: Smoke-test**

Run: `.venv/Scripts/python -c "from proshowpdf.logging_setup import setup_logging; print(setup_logging())"`
Expected: prints a path ending in `proshowpdf.log`.

- [ ] **Step 3: Commit**

```bash
git add proshowpdf/logging_setup.py
git commit -m "feat: rotating file logging"
```

---

## Task 11: Settings persistence

**Files:**
- Create: `proshowpdf/persistence/settings_store.py`

- [ ] **Step 1: Write `settings_store.py`**

```python
"""QSettings wrapper persisting user preferences across sessions."""
from __future__ import annotations

from PySide6.QtCore import QSettings

from proshowpdf.core.models import ConflictPolicy, ConversionSettings

_ORG = "ProfessionalShow"
_APP = "ProShowPDF"


class SettingsStore:
    """Loads/saves ConversionSettings (+ theme) via QSettings."""

    def __init__(self) -> None:
        self._qs = QSettings(_ORG, _APP)

    def load_settings(self, default_output_dir: str) -> ConversionSettings:
        qs = self._qs
        return ConversionSettings(
            output_dir=qs.value("output_dir", default_output_dir, str),
            width_px=int(qs.value("width_px", 1280)),
            max_concurrency=int(qs.value("max_concurrency", 3)),
            timeout_ms=int(qs.value("timeout_ms", 30_000)),
            retries=int(qs.value("retries", 2)),
            handle_cookie_banners=qs.value("cookies", True, bool),
            conflict_policy=ConflictPolicy(qs.value("conflict", "rename", str)),
        )

    def save_settings(self, s: ConversionSettings) -> None:
        qs = self._qs
        qs.setValue("output_dir", s.output_dir)
        qs.setValue("width_px", s.width_px)
        qs.setValue("max_concurrency", s.max_concurrency)
        qs.setValue("timeout_ms", s.timeout_ms)
        qs.setValue("retries", s.retries)
        qs.setValue("cookies", s.handle_cookie_banners)
        qs.setValue("conflict", s.conflict_policy.value)

    def load_theme(self) -> str:
        return self._qs.value("theme", "dark", str)

    def save_theme(self, theme: str) -> None:
        self._qs.setValue("theme", theme)
```

- [ ] **Step 2: Commit**

```bash
git add proshowpdf/persistence/settings_store.py
git commit -m "feat: persist settings via QSettings"
```

---

## Task 12: Bridge controller (QThread + asyncio)

**Files:**
- Create: `proshowpdf/bridge/controller.py`

- [ ] **Step 1: Write `controller.py`**

```python
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

    def start(self, urls: list[str], settings: ConversionSettings) -> None:
        """Schedule a batch on the worker loop (returns immediately)."""
        assert self._loop is not None, "engine not started"
        self._run_task = asyncio.run_coroutine_threadsafe(
            self._run(urls, settings), self._loop
        )

    async def _run(self, urls: list[str], settings: ConversionSettings) -> None:
        engine = ConverterEngine(settings)

        def on_progress(result: JobResult, completed: int, total: int) -> None:
            self.progress.emit(result, completed, total)

        try:
            results = await engine.run(urls, on_progress)
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
```

> Note: the engine receives the asyncio `CancelledError` because
> `run_coroutine_threadsafe(...).cancel()` cancels the running coroutine; the
> engine's `finally` blocks close pages/contexts/browser — no orphan Chromium.

- [ ] **Step 2: Smoke-import**

Run: `.venv/Scripts/python -c "from proshowpdf.bridge.controller import ConversionController; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add proshowpdf/bridge/controller.py
git commit -m "feat(bridge): async engine in QThread with Qt signals"
```

---

## Task 13: Theme + QSS resources

**Files:**
- Create: `proshowpdf/resources/qss/dark.qss`, `proshowpdf/resources/qss/light.qss`
- Create: `proshowpdf/ui/theme.py`

- [ ] **Step 1: Write `dark.qss`**

```css
* { font-family: "Segoe UI", sans-serif; font-size: 14px; color: #e6e6e6; }
QWidget { background-color: #1e1f26; }
QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background: #2a2c36; border: 1px solid #3a3d4a; border-radius: 8px;
    padding: 6px; selection-background-color: #5a6cff;
}
QPushButton {
    background: #5a6cff; border: none; border-radius: 10px; padding: 10px 18px;
    color: white; font-weight: 600;
}
QPushButton:hover { background: #6f7fff; }
QPushButton:disabled { background: #3a3d4a; color: #888; }
QPushButton#secondary { background: #2a2c36; border: 1px solid #3a3d4a; }
QProgressBar {
    border: none; border-radius: 8px; background: #2a2c36; height: 18px;
    text-align: center;
}
QProgressBar::chunk { background: #5a6cff; border-radius: 8px; }
QListWidget { background: #2a2c36; border: 1px solid #3a3d4a; border-radius: 8px; }
```

- [ ] **Step 2: Write `light.qss`**

```css
* { font-family: "Segoe UI", sans-serif; font-size: 14px; color: #1e1f26; }
QWidget { background-color: #f4f5f9; }
QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background: #ffffff; border: 1px solid #d4d7e0; border-radius: 8px;
    padding: 6px; selection-background-color: #5a6cff;
}
QPushButton {
    background: #5a6cff; border: none; border-radius: 10px; padding: 10px 18px;
    color: white; font-weight: 600;
}
QPushButton:hover { background: #4a5cef; }
QPushButton:disabled { background: #d4d7e0; color: #999; }
QPushButton#secondary { background: #ffffff; border: 1px solid #d4d7e0; color: #1e1f26; }
QProgressBar {
    border: none; border-radius: 8px; background: #e4e6ef; height: 18px;
    text-align: center; color: #1e1f26;
}
QProgressBar::chunk { background: #5a6cff; border-radius: 8px; }
QListWidget { background: #ffffff; border: 1px solid #d4d7e0; border-radius: 8px; }
```

- [ ] **Step 3: Write `theme.py`**

```python
"""Theme loading and dark/light switching."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

_QSS_DIR = Path(__file__).parent.parent / "resources" / "qss"


def available_themes() -> list[str]:
    return ["dark", "light"]


def apply_theme(app: QApplication, theme: str) -> None:
    """Load and apply the named QSS stylesheet to the application."""
    qss_file = _QSS_DIR / f"{theme}.qss"
    if qss_file.exists():
        app.setStyleSheet(qss_file.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Commit**

```bash
git add proshowpdf/resources proshowpdf/ui/theme.py
git commit -m "feat(ui): dark/light QSS themes"
```

---

## Task 14: Animation helpers

**Files:**
- Create: `proshowpdf/ui/animations.py`

- [ ] **Step 1: Write `animations.py`**

```python
"""Lightweight QPropertyAnimation helpers for micro-interactions."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QObject
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


def fade_in(widget: QWidget, duration_ms: int = 250) -> QPropertyAnimation:
    """Fade a widget from transparent to opaque; returns the running anim."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim
```

- [ ] **Step 2: Commit**

```bash
git add proshowpdf/ui/animations.py
git commit -m "feat(ui): animation helpers"
```

---

## Task 15: URL input widget

**Files:**
- Create: `proshowpdf/ui/widgets/url_input.py`

- [ ] **Step 1: Write `url_input.py`**

```python
"""Multiline URL input with import-from-file support."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
    QWidget,
)

from proshowpdf.core.url_utils import parse_urls


class UrlInput(QWidget):
    """Textarea for URLs plus a button to import .txt/.csv files."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("URL (uno per riga)"))

        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText("https://example.com\nexample.org/page")
        layout.addWidget(self._editor)

        row = QHBoxLayout()
        import_btn = QPushButton("Importa da file…")
        import_btn.setObjectName("secondary")
        import_btn.clicked.connect(self._import_file)
        row.addStretch()
        row.addWidget(import_btn)
        layout.addLayout(row)

    def _import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importa URL", "", "Testo/CSV (*.txt *.csv)"
        )
        if path:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
            existing = self._editor.toPlainText().rstrip()
            joined = (existing + "\n" + text) if existing else text
            self._editor.setPlainText(joined)

    def urls(self) -> list[str]:
        """Return normalized, validated, de-duplicated URLs."""
        return parse_urls(self._editor.toPlainText())
```

- [ ] **Step 2: Commit**

```bash
git add proshowpdf/ui/widgets/url_input.py
git commit -m "feat(ui): URL input widget"
```

---

## Task 16: Options panel widget

**Files:**
- Create: `proshowpdf/ui/widgets/options_panel.py`

- [ ] **Step 1: Write `options_panel.py`**

```python
"""Conversion options: width, concurrency, timeout, retries, cookies, output."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit,
    QPushButton, QSpinBox, QWidget,
)

from proshowpdf.core.models import ConflictPolicy, ConversionSettings


class OptionsPanel(QWidget):
    """Form exposing all ConversionSettings to the user."""

    def __init__(self) -> None:
        super().__init__()
        form = QFormLayout(self)

        self._width = QSpinBox()
        self._width.setRange(320, 5000)
        self._width.setSuffix(" px")
        form.addRow("Larghezza PDF", self._width)

        self._concurrency = QSpinBox()
        self._concurrency.setRange(1, 10)
        form.addRow("Conversioni parallele", self._concurrency)

        self._timeout = QSpinBox()
        self._timeout.setRange(5, 300)
        self._timeout.setSuffix(" s")
        form.addRow("Timeout", self._timeout)

        self._retries = QSpinBox()
        self._retries.setRange(0, 5)
        form.addRow("Tentativi (retry)", self._retries)

        self._cookies = QCheckBox("Chiudi banner cookie automaticamente")
        form.addRow(self._cookies)

        self._conflict = QComboBox()
        self._conflict.addItems(["rename", "overwrite"])
        form.addRow("Conflitti file", self._conflict)

        out_row = QHBoxLayout()
        self._output = QLineEdit()
        self._output.setReadOnly(True)
        browse = QPushButton("Sfoglia…")
        browse.setObjectName("secondary")
        browse.clicked.connect(self._pick_output)
        out_row.addWidget(self._output)
        out_row.addWidget(browse)
        form.addRow("Cartella output", out_row)

    def _pick_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Cartella di destinazione")
        if path:
            self._output.setText(path)

    def load(self, s: ConversionSettings) -> None:
        self._width.setValue(s.width_px)
        self._concurrency.setValue(s.max_concurrency)
        self._timeout.setValue(s.timeout_ms // 1000)
        self._retries.setValue(s.retries)
        self._cookies.setChecked(s.handle_cookie_banners)
        self._conflict.setCurrentText(s.conflict_policy.value)
        self._output.setText(s.output_dir)

    def to_settings(self) -> ConversionSettings:
        return ConversionSettings(
            output_dir=self._output.text(),
            width_px=self._width.value(),
            max_concurrency=self._concurrency.value(),
            timeout_ms=self._timeout.value() * 1000,
            retries=self._retries.value(),
            handle_cookie_banners=self._cookies.isChecked(),
            conflict_policy=ConflictPolicy(self._conflict.currentText()),
        )
```

- [ ] **Step 2: Commit**

```bash
git add proshowpdf/ui/widgets/options_panel.py
git commit -m "feat(ui): options panel"
```

---

## Task 17: Progress view widget

**Files:**
- Create: `proshowpdf/ui/widgets/progress_view.py`

- [ ] **Step 1: Write `progress_view.py`**

```python
"""Real-time progress: bar, counter, current URL, per-item status list."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel, QListWidget, QListWidgetItem, QProgressBar, QVBoxLayout, QWidget,
)

from proshowpdf.core.models import JobResult, JobStatus

_ICONS = {
    JobStatus.QUEUED: "⏳",
    JobStatus.RUNNING: "🔄",
    JobStatus.DONE: "✅",
    JobStatus.ERROR: "❌",
    JobStatus.CANCELLED: "⏹️",
}


class ProgressView(QWidget):
    """Shows batch progress and a live list of per-URL statuses."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        self._counter = QLabel("0 / 0")
        layout.addWidget(self._counter)

        self._bar = QProgressBar()
        self._bar.setValue(0)
        layout.addWidget(self._bar)

        self._current = QLabel("")
        self._current.setWordWrap(True)
        layout.addWidget(self._current)

        self._list = QListWidget()
        layout.addWidget(self._list)

        self._rows: dict[int, QListWidgetItem] = {}

    def reset(self, total: int) -> None:
        self._list.clear()
        self._rows.clear()
        self._bar.setRange(0, max(total, 1))
        self._bar.setValue(0)
        self._counter.setText(f"0 / {total}")
        self._current.setText("")

    def update(self, result: JobResult, completed: int, total: int) -> None:
        label = f"{_ICONS[result.status]}  {result.url}"
        if result.status is JobStatus.ERROR:
            label += f"  —  {result.error_type}: {result.error_message}"
        if result.index in self._rows:
            self._rows[result.index].setText(label)
        else:
            item = QListWidgetItem(label)
            self._rows[result.index] = item
            self._list.addItem(item)
        if result.status is JobStatus.RUNNING:
            self._current.setText(f"In corso: {result.url}")
        self._bar.setValue(completed)
        self._counter.setText(f"{completed} / {total}")
```

- [ ] **Step 2: Commit**

```bash
git add proshowpdf/ui/widgets/progress_view.py
git commit -m "feat(ui): progress view"
```

---

## Task 18: Results panel widget

**Files:**
- Create: `proshowpdf/ui/widgets/results_panel.py`

- [ ] **Step 1: Write `results_panel.py`**

```python
"""End-of-batch summary: error table, CSV export, open output folder."""
from __future__ import annotations

import csv
import os
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from proshowpdf.core.models import JobResult, JobStatus


class ResultsPanel(QWidget):
    """Summarizes a finished batch and offers CSV export / open folder."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        self._summary = QLabel("")
        layout.addWidget(self._summary)

        row = QHBoxLayout()
        self._export_btn = QPushButton("Esporta errori CSV")
        self._export_btn.setObjectName("secondary")
        self._export_btn.clicked.connect(self._export_csv)
        self._open_btn = QPushButton("Apri cartella output")
        self._open_btn.setObjectName("secondary")
        self._open_btn.clicked.connect(self._open_folder)
        row.addWidget(self._export_btn)
        row.addWidget(self._open_btn)
        row.addStretch()
        layout.addLayout(row)

        self._results: list[JobResult] = []
        self._output_dir = ""
        self.set_enabled(False)

    def set_enabled(self, enabled: bool) -> None:
        self._export_btn.setEnabled(enabled)
        self._open_btn.setEnabled(enabled)

    def show_results(self, results: list[JobResult], output_dir: str) -> None:
        self._results = results
        self._output_dir = output_dir
        done = sum(1 for r in results if r.status is JobStatus.DONE)
        errors = sum(1 for r in results if r.status is JobStatus.ERROR)
        self._summary.setText(
            f"Completate: {done} — Errori: {errors} — Totale: {len(results)}"
        )
        self.set_enabled(True)

    def _errors(self) -> list[JobResult]:
        return [r for r in self._results if r.status is JobStatus.ERROR]

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Esporta errori", "errori.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["url", "error_type", "message", "timestamp"])
            for r in self._errors():
                ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([r.url, r.error_type, r.error_message, ts])

    def _open_folder(self) -> None:
        if self._output_dir and Path(self._output_dir).exists():
            os.startfile(self._output_dir)  # noqa: S606 — Windows only
```

> Note: `os.startfile` is Windows-only, which matches the x64 target. `subprocess`
> import kept for parity is unnecessary — remove it if your linter flags it.

- [ ] **Step 2: Remove the unused `subprocess`/`datetime` imports if unused**

Edit the import block to only keep what's used: `csv`, `os`, `Path`, the Qt
widgets, and the models. (`datetime`/`subprocess` are not referenced.)

```python
import csv
import os
from pathlib import Path
```

- [ ] **Step 3: Commit**

```bash
git add proshowpdf/ui/widgets/results_panel.py
git commit -m "feat(ui): results panel with CSV export"
```

---

## Task 19: Main window

**Files:**
- Create: `proshowpdf/ui/main_window.py`

- [ ] **Step 1: Write `main_window.py`**

```python
"""Main window: assembles widgets and wires controller signals."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from proshowpdf.bridge.controller import ConversionController
from proshowpdf.core.models import ConversionSettings, JobResult
from proshowpdf.persistence.settings_store import SettingsStore
from proshowpdf.ui.theme import apply_theme
from proshowpdf.ui.widgets.options_panel import OptionsPanel
from proshowpdf.ui.widgets.progress_view import ProgressView
from proshowpdf.ui.widgets.results_panel import ResultsPanel
from proshowpdf.ui.widgets.url_input import UrlInput

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, controller: ConversionController, store: SettingsStore) -> None:
        super().__init__()
        self._controller = controller
        self._store = store
        self._theme = store.load_theme()
        self.setWindowTitle("ProShow PDF")
        self.resize(900, 760)

        self._url_input = UrlInput()
        self._options = OptionsPanel()
        self._progress = ProgressView()
        self._results = ResultsPanel()

        default_out = str(Path.home() / "Documents")
        self._options.load(store.load_settings(default_out))

        central = QWidget()
        root = QVBoxLayout(central)
        root.addWidget(self._url_input)
        root.addWidget(self._options)

        buttons = QHBoxLayout()
        self._start_btn = QPushButton("Converti")
        self._cancel_btn = QPushButton("Annulla")
        self._cancel_btn.setObjectName("secondary")
        self._cancel_btn.setEnabled(False)
        self._theme_btn = QPushButton("Tema chiaro/scuro")
        self._theme_btn.setObjectName("secondary")
        buttons.addWidget(self._start_btn)
        buttons.addWidget(self._cancel_btn)
        buttons.addStretch()
        buttons.addWidget(self._theme_btn)
        root.addLayout(buttons)

        root.addWidget(self._progress)
        root.addWidget(self._results)
        self.setCentralWidget(central)

        self._start_btn.clicked.connect(self._on_start)
        self._cancel_btn.clicked.connect(self._controller.cancel)
        self._theme_btn.clicked.connect(self._toggle_theme)
        controller.progress.connect(self._progress.update)
        controller.finished.connect(self._on_finished)
        controller.failed.connect(self._on_failed)
        controller.cancelled.connect(self._on_cancelled)

    def _on_start(self) -> None:
        urls = self._url_input.urls()
        if not urls:
            QMessageBox.warning(self, "Nessun URL", "Inserisci almeno un URL valido.")
            return
        settings = self._options.to_settings()
        if not settings.output_dir or not Path(settings.output_dir).is_dir():
            QMessageBox.warning(self, "Output", "Seleziona una cartella di output valida.")
            return
        self._store.save_settings(settings)
        self._results.set_enabled(False)
        self._progress.reset(len(urls))
        self._set_running(True)
        self._controller.start(urls, settings)

    def _set_running(self, running: bool) -> None:
        self._start_btn.setEnabled(not running)
        self._cancel_btn.setEnabled(running)

    def _on_finished(self, results: list[JobResult]) -> None:
        self._set_running(False)
        self._results.show_results(results, self._options.to_settings().output_dir)

    def _on_failed(self, message: str) -> None:
        self._set_running(False)
        QMessageBox.critical(self, "Errore", message)

    def _on_cancelled(self) -> None:
        self._set_running(False)
        QMessageBox.information(self, "Annullato", "Batch annullato.")

    def _toggle_theme(self) -> None:
        self._theme = "light" if self._theme == "dark" else "dark"
        apply_theme(self.window().windowHandle().screen() and __import__(
            "PySide6.QtWidgets", fromlist=["QApplication"]
        ).QApplication.instance(), self._theme)
        self._store.save_theme(self._theme)

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt override
        self._controller.shutdown()
        super().closeEvent(event)
```

- [ ] **Step 2: Simplify `_toggle_theme` (replace the convoluted line)**

Replace the body of `_toggle_theme` with a clean version that imports
`QApplication` at the top of the file:

Add to imports: `from PySide6.QtWidgets import QApplication`
Then:
```python
    def _toggle_theme(self) -> None:
        self._theme = "light" if self._theme == "dark" else "dark"
        apply_theme(QApplication.instance(), self._theme)
        self._store.save_theme(self._theme)
```

- [ ] **Step 3: Commit**

```bash
git add proshowpdf/ui/main_window.py
git commit -m "feat(ui): main window wiring controller signals"
```

---

## Task 20: App bootstrap + x64 entrypoint

**Files:**
- Create: `proshowpdf/app.py`, `proshowpdf/__main__.py`

- [ ] **Step 1: Write `app.py`**

```python
"""QApplication bootstrap: High-DPI, theme, controller, main window."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from proshowpdf.bridge.controller import ConversionController
from proshowpdf.logging_setup import setup_logging
from proshowpdf.persistence.settings_store import SettingsStore
from proshowpdf.ui.main_window import MainWindow
from proshowpdf.ui.theme import apply_theme


def run() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("ProShow PDF")
    app.setOrganizationName("ProfessionalShow")

    store = SettingsStore()
    apply_theme(app, store.load_theme())

    controller = ConversionController()
    controller.start_engine()

    window = MainWindow(controller, store)
    window.show()
    return app.exec()
```

> High-DPI note: PySide6 ≥ 6.0 enables High-DPI scaling by default
> (`Qt::AA_EnableHighDpiScaling` is the default), so no extra flag is required.

- [ ] **Step 2: Write `__main__.py` with the x64 guard**

```python
"""Entrypoint with a hard 64-bit guard (Playwright Chromium is x64-only)."""
from __future__ import annotations

import ctypes
import struct
import sys


def _is_64bit() -> bool:
    return struct.calcsize("P") * 8 == 64


def _show_error_and_exit(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(0, message, "ProShow PDF", 0x10)
    except Exception:
        print(message, file=sys.stderr)
    sys.exit(1)


def main() -> int:
    if not _is_64bit():
        _show_error_and_exit(
            "ProShow PDF richiede Windows a 64 bit (x64).\n"
            "Il Chromium di Playwright è disponibile solo per x64."
        )
    from proshowpdf.app import run
    return run()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Manual run check**

Run: `.venv/Scripts/python -m proshowpdf`
Expected: the window opens; converting a real URL (e.g. `https://example.com`)
to a chosen folder produces a PDF. Cancel works mid-batch.

- [ ] **Step 4: Commit**

```bash
git add proshowpdf/app.py proshowpdf/__main__.py
git commit -m "feat: app bootstrap and x64-guarded entrypoint"
```

---

## Task 21: Packaging (PyInstaller onedir)

**Files:**
- Create: `packaging/proshowpdf.spec`, `packaging/build.md`

- [ ] **Step 1: Write `packaging/proshowpdf.spec`**

```python
# PyInstaller onedir spec for Windows x64.
# Bundles Playwright's Chromium by collecting the ms-playwright browser cache
# into the dist folder and pointing PLAYWRIGHT_BROWSERS_PATH at it at runtime.
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Locate the per-user Playwright browser cache produced by `playwright install`.
_pw_cache = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"
browser_datas = [(str(_pw_cache), "ms-playwright")] if _pw_cache.exists() else []

a = Analysis(
    ["..\\proshowpdf\\__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("..\\proshowpdf\\resources", "proshowpdf/resources"),
        *browser_datas,
    ],
    hiddenimports=["playwright"],
    hookspath=[],
    runtime_hooks=["packaging\\rthook_playwright.py"],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="ProShowPDF",
    console=False, target_arch="x86_64",
)
coll = COLLECT(exe, a.binaries, a.datas, name="ProShowPDF")
```

- [ ] **Step 2: Write the runtime hook `packaging/rthook_playwright.py`**

```python
# Runtime hook: point Playwright at the bundled browser cache when frozen.
import os
import sys

if getattr(sys, "frozen", False):
    bundled = os.path.join(sys._MEIPASS, "ms-playwright")
    if os.path.isdir(bundled):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = bundled
```

- [ ] **Step 3: Write `packaging/build.md`**

````markdown
# Build (Windows x64, dal venv)

```bat
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
playwright install chromium
pyinstaller packaging\proshowpdf.spec --noconfirm
```

Output: `dist\ProShowPDF\ProShowPDF.exe` (cartella onedir, con Chromium bundlato).
Distribuisci l'intera cartella `dist\ProShowPDF`.
````

- [ ] **Step 4: Build check**

Run: `.venv/Scripts/pyinstaller packaging/proshowpdf.spec --noconfirm`
Expected: `dist/ProShowPDF/ProShowPDF.exe` exists and launches; conversion works
without a system Playwright install.

- [ ] **Step 5: Commit**

```bash
git add packaging
git commit -m "build: PyInstaller onedir spec with bundled Chromium"
```

---

## Task 22: README + final test sweep

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`** (setup, run, build, known limits — mirror the spec sections 12–14).

- [ ] **Step 2: Run the full test suite**

Run: `.venv/Scripts/pytest -v`
Expected: all tests in `tests/` PASS.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README with setup, build and known limits"
```

---

## Self-Review (completed)

**Spec coverage:** RF1 (url_input+url_utils, T4/T15), RF2 (models/page_converter, T2/T7), RF3 dynamic height (T7), RF4 fidelity flags (T7), RF5 cookies (T6/T16), RF6 progress (T17), RF7 cancel (T9/T12), RF8 concurrency (T8/T9), RF9 output/naming (T5/T18), RF10 errors+CSV (T3/T9/T18), RF11 persistence (T11), RF12 timeout/retry (T9/T16). NFRs: perf (single browser T8), robustness (errors/finally T7-T9-T12), packaging (T21). Tests: url_utils, naming, page_converter (T4/T5/T7). All covered.

**Placeholder scan:** README body in T22 is described section-by-section by reference to spec §12–14 (concrete content), no TBDs elsewhere.

**Type consistency:** `ConversionSettings`, `JobResult`, `JobStatus`, `ConflictPolicy` used consistently; `convert_page`, `compute_pdf_height`, `dismiss_cookie_banner`, `BrowserPool.new_page`, `ConverterEngine.run`, controller signals all match across tasks.
