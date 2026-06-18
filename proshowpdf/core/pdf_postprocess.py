"""Trim trailing whitespace from rendered single-page PDFs.

Chromium's ``printToPDF`` sometimes lays a page out shorter than the live
``scrollHeight`` we sized the paper to (large image/gallery sections re-flow
shorter in the PDF layout pass). The result is a tall blank band after the real
content — and ``position: fixed`` widgets (chat buttons, social bars, late
cookie banners) get baked into that band at the bottom of the page.

We rasterize the finished page, find the bottom of the main content block
(stopping at the first whitespace gap large enough to separate the content from
any trailing junk), and rewrite the page cropped to that height. ``_bottom_row``
is pure and unit-tested; ``trim_trailing_whitespace`` drives PyMuPDF and is
defensive — any failure leaves the original PDF untouched.
"""
from __future__ import annotations

import logging
import os

import fitz  # PyMuPDF

log = logging.getLogger(__name__)

# Downscale factor for the whitespace scan: small enough to be cheap, large
# enough that a row of real content keeps at least one ink pixel.
_RASTER_SCALE = 0.125
# Gray value (0=black, 255=white) below which a pixel counts as content ink.
_INK_THRESHOLD = 248
# A vertical run of blank space taller than this (in PDF points, 72pt = 1in)
# is treated as the end of the main content; anything past it is trailing
# whitespace plus stray baked-in widgets. Real section gaps stay well below it.
_MAX_GAP_PT = 450.0
# Padding kept below the detected content bottom so descenders/borders survive.
_PAD_PT = 18.0
# Only rewrite the file if trimming removes at least this much (avoid churning
# pages that have no meaningful trailing whitespace).
_MIN_TRIM_PT = 72.0


def _bottom_row(row_has_ink: list[bool], max_gap_rows: float) -> int:
    """Return the index of the last content row before an oversized blank gap.

    Walks rows top-to-bottom, tracking the lowest inked row. Once a run of blank
    rows exceeds ``max_gap_rows`` (after some content has been seen), the main
    block is considered finished and the scan stops. Returns -1 if no ink.
    """
    content_bottom_row = -1
    gap = 0
    for y, ink in enumerate(row_has_ink):
        if ink:
            content_bottom_row = y
            gap = 0
        else:
            gap += 1
            if content_bottom_row >= 0 and gap > max_gap_rows:
                break
    return content_bottom_row


def _content_bottom_pt(page) -> float | None:
    """Find the bottom of the main content block in PDF points, or None."""
    pix = page.get_pixmap(
        matrix=fitz.Matrix(_RASTER_SCALE, _RASTER_SCALE), colorspace=fitz.csGRAY
    )
    width, height, stride = pix.width, pix.height, pix.stride
    samples = pix.samples
    row_has_ink = [
        min(samples[y * stride : y * stride + width]) < _INK_THRESHOLD
        for y in range(height)
    ]
    pt_per_row = page.rect.height / height
    bottom_row = _bottom_row(row_has_ink, _MAX_GAP_PT / pt_per_row)
    if bottom_row < 0:
        return None
    return (bottom_row + 1) * pt_per_row


def trim_trailing_whitespace(pdf_path: str) -> None:
    """Crop trailing whitespace from a single-page PDF in place (best effort)."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        log.debug("PDF trim skipped (open failed) for %s: %s", pdf_path, exc)
        return
    out = None
    try:
        if doc.page_count != 1:
            return
        page = doc[0]
        page_w, page_h = page.rect.width, page.rect.height
        content_bottom = _content_bottom_pt(page)
        if content_bottom is None:
            return
        new_h = min(page_h, content_bottom + _PAD_PT)
        if page_h - new_h < _MIN_TRIM_PT:
            return

        clip = fitz.Rect(0, 0, page_w, new_h)
        out = fitz.open()
        new_page = out.new_page(width=page_w, height=new_h)
        new_page.show_pdf_page(clip, doc, 0, clip=clip)
        tmp_path = pdf_path + ".trim"
        out.save(tmp_path, garbage=3, deflate=True)
    except Exception as exc:
        log.warning("PDF trim failed for %s: %s", pdf_path, exc)
        return
    finally:
        doc.close()
        if out is not None:
            out.close()

    try:
        os.replace(tmp_path, pdf_path)
        log.info("Trimmed %.0fpt of trailing whitespace from %s", page_h - new_h, pdf_path)
    except OSError as exc:
        log.warning("PDF trim could not replace %s: %s", pdf_path, exc)
