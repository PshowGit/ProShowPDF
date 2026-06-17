from unittest.mock import AsyncMock

import pytest

from proshowpdf.core.models import ConversionSettings
from proshowpdf.core.page_converter import (
    compute_pdf_dimensions,
    compute_pdf_height,
    convert_page,
)


def test_compute_pdf_height_uses_measured_value():
    assert compute_pdf_height(2400, min_height=100) == 2400


def test_compute_pdf_height_enforces_minimum():
    assert compute_pdf_height(0, min_height=100) == 100
    assert compute_pdf_height(-5, min_height=100) == 100


def test_compute_pdf_dimensions_passes_through_short_pages():
    # A page well under 200in keeps native px dimensions.
    assert compute_pdf_dimensions(1500, width_px=1280, min_height=100) == (
        "1280px",
        "1500px",
    )


def test_compute_pdf_dimensions_clamps_tall_pages_within_limit():
    # 31105px == 324in, over the 200in PDF page limit -> scaled to 199in.
    width, height = compute_pdf_dimensions(31105, width_px=1280, min_height=100)
    assert height == "199.0in"
    # Width scales by the same factor so the whole page stays on one page.
    assert width.endswith("in")
    assert float(width[:-2]) < 1280 / 96


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
    # Disable the cookie path here: it is covered separately and a blanket
    # AsyncMock page would otherwise leave unawaited locator coroutines.
    settings = ConversionSettings(
        output_dir=str(tmp_path), width_px=1280, handle_cookie_banners=False
    )

    out_path = await convert_page(page, "https://x.com", settings)

    page.goto.assert_awaited()
    page.pdf.assert_awaited()
    kwargs = page.pdf.await_args.kwargs
    assert kwargs["print_background"] is True
    assert kwargs["width"] == "1280px"
    assert kwargs["height"] == "1500px"
    assert kwargs["margin"] == {"top": "0", "right": "0", "bottom": "0", "left": "0"}
    assert out_path.endswith(".pdf")
