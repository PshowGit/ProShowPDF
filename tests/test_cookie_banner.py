from unittest.mock import AsyncMock, MagicMock

import pytest

from proshowpdf.core.cookie_banner import dismiss_cookie_banner


def _page_with_counts(counts: list[int]):
    """A fake page whose every locator().count() yields the given sequence."""
    page = MagicMock()
    page.frames = []
    seq = iter(counts + [0] * 2000)
    locator = MagicMock()
    locator.count = AsyncMock(side_effect=lambda: next(seq))
    locator.first = MagicMock()
    locator.first.click = AsyncMock()
    page.locator = MagicMock(return_value=locator)
    page._locator = locator
    return page


@pytest.mark.asyncio
async def test_no_banner_returns_zero():
    page = _page_with_counts([0])
    assert await dismiss_cookie_banner(page) == 0
    page._locator.first.click.assert_not_awaited()


@pytest.mark.asyncio
async def test_dismisses_one_banner_then_stops():
    # First probe matches (count 1) and clicks; every later probe finds nothing.
    page = _page_with_counts([1])
    assert await dismiss_cookie_banner(page) == 1
    page._locator.first.click.assert_awaited()
