import fitz
import pytest

from proshowpdf.core.pdf_postprocess import _bottom_row, trim_trailing_whitespace


def test_bottom_row_stops_at_large_gap():
    # Content rows 0..4, then a 10-row blank gap, then a stray widget at 15.
    rows = [True] * 5 + [False] * 10 + [True]
    # A gap > 6 rows ends the main block, so the stray widget is excluded.
    assert _bottom_row(rows, max_gap_rows=6) == 4


def test_bottom_row_keeps_small_gaps():
    # Small section gaps (<= max) do not end the block.
    rows = [True, True, False, False, True, False, True]
    assert _bottom_row(rows, max_gap_rows=3) == 6


def test_bottom_row_all_blank_returns_negative():
    assert _bottom_row([False, False, False], max_gap_rows=2) == -1


def _make_pdf(path, page_h_pt, content_h_pt):
    """A page with a black bar at the top and blank space below it."""
    doc = fitz.open()
    page = doc.new_page(width=600, height=page_h_pt)
    page.draw_rect(fitz.Rect(0, 0, 600, content_h_pt), color=(0, 0, 0), fill=(0, 0, 0))
    doc.save(str(path))
    doc.close()


def test_trim_removes_trailing_whitespace(tmp_path):
    pdf = tmp_path / "tall.pdf"
    _make_pdf(pdf, page_h_pt=4000, content_h_pt=800)

    trim_trailing_whitespace(str(pdf))

    doc = fitz.open(str(pdf))
    # Cropped close to the content bottom (800pt) plus a little padding/raster slack.
    assert 800 <= doc[0].rect.height <= 900
    doc.close()


def test_trim_leaves_full_pages_untouched(tmp_path):
    pdf = tmp_path / "full.pdf"
    _make_pdf(pdf, page_h_pt=1000, content_h_pt=990)

    trim_trailing_whitespace(str(pdf))

    doc = fitz.open(str(pdf))
    assert doc[0].rect.height == pytest.approx(1000, abs=1)
    doc.close()


def test_trim_missing_file_is_silent():
    # Best-effort: a bad path must never raise.
    trim_trailing_whitespace("does-not-exist.pdf")
