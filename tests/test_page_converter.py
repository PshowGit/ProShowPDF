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
