# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ProShow PDF — Web-to-PDF Converter (Windows x64)

**Purpose:** Desktop application (PySide6 GUI + Playwright/Chromium headless) that converts web pages to single-page continuous PDFs with high visual fidelity.

**Stack:** Python 3.13, PySide6 6.8.1, Playwright 1.49 (Chromium headless), asyncio, pytest, PyInstaller (onedir), openpyxl 3.1.2, xlrd 2.0.1, PyMuPDF 1.27.2.3.

---

## Quick Start

```bash
# Setup (one-time)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# Run
python -m proshowpdf

# Tests
pytest -q

# Build (onedir distributable)
rebuild.bat
# Or manually: pyinstaller packaging/proshowpdf.spec --noconfirm
# Output: dist\ProShowPDF\ProShowPDF.exe + zip (312 MB) with bundled Chromium
```

---

## Architecture

### Three-Layer Design

1. **Core (`proshowpdf/core/`)** — Pure Python, no Qt/Playwright imports in the UI layer
   - `models.py` — Data classes (ConversionSettings, JobResult, JobStatus, JobItem with optional custom_filename)
   - `errors.py` — Typed exception hierarchy
   - `url_utils.py` — URL validation, normalization, parsing (txt/csv/xlsx/xls)
   - `naming.py` — Windows-safe filenames, collision resolution, custom filename sanitization
   - `cookie_banner.py` — Heuristic banner dismissal (euristiques for common consent platforms)
   - `page_converter.py` — Per-page conversion: navigate → dismiss cookies → scroll lazy-load → measure height → render PDF → trim trailing whitespace; supports optional custom_filename for per-URL naming
   - `pdf_postprocess.py` — Post-render PDF cleanup: rasterize the page, find the bottom of the main content block (stopping at the first large whitespace gap) and crop the page to it, removing the blank band Chromium's printToPDF leaves after the footer along with any `position: fixed` widgets baked into it (PyMuPDF)
   - `browser_pool.py` — Single Chromium instance + isolated BrowserContext per URL + viewport sizing
   - `converter_engine.py` — Batch orchestration: asyncio.Semaphore for concurrency cap, retry/backoff, progress callbacks, cancellation, supports optional custom_filenames for per-URL PDF naming

2. **Bridge (`proshowpdf/bridge/`)** — Qt ↔ Async boundary
   - `controller.py` — ConversionController(QObject): QThread hosting asyncio event loop, emits Qt signals (progress, finished, failed, cancelled), accepts commands (start, cancel, shutdown)

3. **UI (`proshowpdf/ui/`)** — Pure PySide6
   - `main_window.py` — Assembles widgets, wires controller signals/slots
   - `widgets/` — UrlInput (drag-drop txt/csv/xlsx/xls with optional custom filenames in column 2, real-time URL counter), OptionsPanel (settings form), ProgressView (realtime bar + status list), ResultsPanel (summary + CSV export + open-folder)
   - `theme.py` — Apply dark/light QSS stylesheets from `resources/qss/`
   - `animations.py` — fade_in helper (micro-interactions)

**Persistence:** `proshowpdf/persistence/settings_store.py` (QSettings wrapper)
**Logging:** `proshowpdf/logging_setup.py` (RotatingFileHandler to `%LOCALAPPDATA%/ProShowPDF/logs/`)

---

## Key Design Decisions

### Concurrency Model
- **One async event loop in a QThread worker** (not Qt thread pool). Single Chromium instance reused across all URLs.
- **Semaphore governs concurrency** (default 3 simultaneous conversions).
- **Cancellation is cooperative:** `task.cancel()` → `finally` blocks close pages/contexts/browser (no orphan processes).

### Fidelity (Rendering)
- `emulate_media("screen")` — on-screen appearance, not print styles.
- `print_background=True` — preserve CSS colors/gradients.
- Margin=0 — edge-to-edge PDF.
- Dynamic height: measure `scrollHeight` after `networkidle` + scroll lazy-load + `document.fonts.ready`.
- Trailing-whitespace trim: Chromium's `printToPDF` can lay a page out shorter than the measured `scrollHeight` (large image/gallery sections re-flow shorter in the PDF pass), leaving a blank band after the footer with `position: fixed` widgets baked into it. `pdf_postprocess.trim_trailing_whitespace` crops the rendered PDF to its real content bottom (best-effort; never fails the conversion).

### Windows x64 Only
- `proshowpdf/__main__.py` checks architecture at startup; exits with error dialog on 32-bit systems (Playwright Chromium is x64-only).

---

## Code Conventions

- **Type hints everywhere** (PEP 484).
- **No comments except WHY** (not WHAT — well-named code explains itself).
- **Error handling:** Typed exceptions (ConversionError subclasses) with `.error_type` attribute for classification (navigation, timeout, render, output).
- **Testing:** pytest + pytest-asyncio; unit tests for core modules (url_utils, naming, page_converter); integration tested via E2E conversion.
- **Logging:** Structured log messages with context (URL, attempt number, timestamp).

---

## Common Tasks

### Add a New Conversion Setting
1. Add field to `ConversionSettings` (proshowpdf/core/models.py).
2. Expose in `OptionsPanel.load()`/`to_settings()` (proshowpdf/ui/widgets/options_panel.py).
3. Persist via `SettingsStore.load_settings()`/`save_settings()` (proshowpdf/persistence/settings_store.py).
4. Use in `convert_page()` or `ConverterEngine` (proshowpdf/core/page_converter.py or converter_engine.py).

### Add Support for a New File Format (URL Lists)
- Extend `DragDropPlainText._load_file()` and add a `_read_<format>()` method to extract URLs and optional custom filenames.
- Return `(text, custom_names_dict)` where custom_names_dict maps URL → custom_pdf_name.
- UrlInput.custom_filenames() returns a parallel list to urls() with None for URLs without custom names.
- Update dialog filter in `_import_file()` QFileDialog.

**Custom Filename Format (all file types):**
- Column 1: URL
- Column 2 (optional): Custom PDF filename (without .pdf extension)
- Header row is auto-detected and skipped if it contains "url", "name", "filename"

### Improve Cookie Banner Heuristics
- Edit `_KNOWN_SELECTORS` and `_ACCEPT_TEXTS` (proshowpdf/core/cookie_banner.py).
- Test by rendering a known consent-banner site and checking logs for "Dismissed banner via ...".

### Style UI Components
- Dark theme: `proshowpdf/resources/qss/dark.qss`
- Light theme: `proshowpdf/resources/qss/light.qss`
- Note: `-margin-left`, `-margin-right` etc. work; don't use shorthand `margin:`.

---

## Testing

```bash
# Run all tests
pytest -v

# Run specific test
pytest tests/test_url_utils.py::test_normalize_adds_scheme_and_trims -v

# Run with coverage
pytest --cov=proshowpdf tests/
```

**Test Structure:**
- `tests/test_url_utils.py` — URL validation/parsing
- `tests/test_naming.py` — Filename sanitization, collision resolution
- `tests/test_page_converter.py` — Height measurement logic (with AsyncMock page)

---

## Known Limits & Future Work

**Known Issues:**
- Pages with aggressive anti-bot detection or login requirements may fail.
- Cookie banner heuristics don't cover 100% of consent platforms (disableable from UI).
- Very tall single-page PDFs (entire page in one image) can be I/O intensive.

**Future Enhancements:**
- Persistent browser profiles for login-requiring sites.
- Standard page-size formats (A4) as optional mode.
- Persistent job queue (resume crashed batches).
- Multi-language UI.

---

## Debugging

**Enable verbose logging:**
```python
# In app.py, change setup_logging() to:
setup_logging(level=logging.DEBUG)
```

**Browser logs:**
Playwright logs are emitted to stderr. Redirect or filter in console scripts if noisy.

**Headless Testing (offscreen rendering):**
```python
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# ... then run your UI code
```

---

## Packaging & Distribution

**Build (automated):**
```bash
rebuild.bat
```
Automatically recompiles exe and creates ProShowPDF-v1.0.0-windows-x64.zip (312 MB).

**Build (manual):**
```bash
.venv\Scripts\pyinstaller packaging\proshowpdf.spec --noconfirm
cd dist
Compress-Archive -Path "ProShowPDF" -DestinationPath "..\ProShowPDF-v1.0.0-windows-x64.zip" -Force
```

**Bundling:** The spec resolves pinned Chromium revision from `playwright/driver/package/browsers.json` and bundles only the active browser + headless shell + ffmpeg, then uses `packaging/rthook_playwright.py` to redirect `PLAYWRIGHT_BROWSERS_PATH` at runtime.

**Distribution:** Deliver ProShowPDF-v1.0.0-windows-x64.zip (312 MB); users extract and run ProShowPDF.exe with no installation needed. See DOWNLOAD_GUIDE.html for user instructions.

---

## References

- **Design Spec:** `docs/superpowers/specs/2026-06-16-proshowpdf-design.md`
- **Implementation Plan:** `docs/superpowers/plans/2026-06-16-proshowpdf.md`
- **README:** `README.md` (user-facing setup & features)
