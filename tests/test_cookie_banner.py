from unittest.mock import AsyncMock, MagicMock

import pytest

from proshowpdf.core.cookie_banner import dismiss_cookie_banner


def _page_with_counts(counts: list[int]):
    """A fake page whose every locator().count() yields the given sequence.

    The matched element reports visible and clickable, mirroring how
    ``_try_click`` walks ``nth(i)`` candidates and clicks the first visible one.
    """
    page = MagicMock()
    page.frames = []
    seq = iter(counts + [0] * 2000)
    candidate = MagicMock()
    candidate.is_visible = AsyncMock(return_value=True)
    candidate.click = AsyncMock()
    locator = MagicMock()
    locator.count = AsyncMock(side_effect=lambda: next(seq))
    locator.nth = MagicMock(return_value=candidate)
    page.locator = MagicMock(return_value=locator)
    page._candidate = candidate
    return page


@pytest.mark.asyncio
async def test_no_banner_returns_zero():
    page = _page_with_counts([0])
    assert await dismiss_cookie_banner(page) == 0
    page._candidate.click.assert_not_awaited()


@pytest.mark.asyncio
async def test_dismisses_one_banner_then_stops():
    # First probe matches (count 1) and clicks; every later probe finds nothing.
    page = _page_with_counts([1])
    assert await dismiss_cookie_banner(page) == 1
    page._candidate.click.assert_awaited()
