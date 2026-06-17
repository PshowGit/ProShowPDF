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
    # A host with whitespace (the typical "two words" typo) is rejected even
    # after a scheme is prepended, so it is not silently accepted as a host.
    assert not is_valid_url("https://not a url")


def test_parse_urls_drops_lines_with_whitespace_hosts():
    text = "example.com\nnot a url\nhttps://b.com"
    assert parse_urls(text) == ["https://example.com", "https://b.com"]


def test_parse_urls_dedups_and_skips_blanks_and_comments():
    text = "example.com\n\n# comment\nexample.com\nhttps://b.com\n"
    assert parse_urls(text) == ["https://example.com", "https://b.com"]


def test_parse_urls_handles_csv_first_column():
    text = "url,note\nexample.com,hi\nb.com,bye"
    assert parse_urls(text) == ["https://example.com", "https://b.com"]
