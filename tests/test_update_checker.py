import io
import json
from contextlib import contextmanager
from unittest.mock import patch

from proshowpdf.update_checker import (
    ReleaseInfo,
    _parse_version,
    fetch_latest_release,
    is_newer,
)


def test_parse_version_strips_v_and_handles_junk():
    assert _parse_version("v1.2.3") == (1, 2, 3)
    assert _parse_version("1.0.0") == (1, 0, 0)
    assert _parse_version("v2.0") == (2, 0)
    assert _parse_version("garbage") == (0,)


def test_is_newer_compares_semantically():
    assert is_newer("v1.0.1", "1.0.0")
    assert is_newer("v1.1.0", "1.0.9")
    assert is_newer("2.0", "1.9.9")


def test_is_newer_false_when_same_or_older():
    assert not is_newer("1.0.0", "1.0.0")
    assert not is_newer("v1.0.0", "1.0.1")
    # Differing component counts compare correctly (1.0 == 1.0.0).
    assert not is_newer("1.0", "1.0.0")


@contextmanager
def _fake_urlopen(payload: dict):
    yield io.BytesIO(json.dumps(payload).encode())


def test_fetch_latest_release_parses_payload():
    payload = {"tag_name": "v1.2.0", "html_url": "https://example/releases/v1.2.0"}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        info = fetch_latest_release()
    assert info == ReleaseInfo(version="v1.2.0", url="https://example/releases/v1.2.0")


def test_fetch_latest_release_returns_none_on_error():
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        assert fetch_latest_release() is None


def test_fetch_latest_release_returns_none_on_incomplete_payload():
    with patch("urllib.request.urlopen", return_value=_fake_urlopen({"tag_name": "v1"})):
        assert fetch_latest_release() is None
