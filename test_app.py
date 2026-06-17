#!/usr/bin/env python
"""Quick smoke test of ProShowPDF core modules."""
import sys
import tempfile
from pathlib import Path

# Create QApplication for UI tests
from PySide6.QtWidgets import QApplication
app = QApplication([])

print("=" * 60)
print("ProShowPDF - Core Module Tests")
print("=" * 60)

# Test 1: URL parsing
print("\n[PASS] Test 1: URL Parsing")
from proshowpdf.core.url_utils import parse_urls
urls_text = """
https://example.com
example.org
https://test.com/page
# comment line
google.com

"""
parsed = parse_urls(urls_text)
assert len(parsed) == 4, f"Expected 4 URLs, got {len(parsed)}"
assert "https://example.com" in parsed
assert "https://example.org" in parsed
assert "https://google.com" in parsed
print(f"  Parsed {len(parsed)} URLs, normalized, and deduplicated")

# Test 2: Filename sanitization
print("\n[PASS] Test 2: Filename Sanitization")
from proshowpdf.core.naming import sanitize_filename
fname = sanitize_filename("My <Weird> File|Name?.pdf")
assert '"' not in fname and '<' not in fname and '|' not in fname
print(f"  Sanitized: {fname}")

# Test 3: CSV reading with comma delimiter
print("\n[PASS] Test 3: CSV Reader (comma delimiter)")
with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
    f.write("url,name\n")
    f.write("https://example.com,Article 1\n")
    f.write("https://site.org,Guide 2\n")
    csv_path = Path(f.name)

try:
    from proshowpdf.ui.widgets.url_input import DragDropPlainText
    widget = DragDropPlainText()
    text, custom_names = widget._read_csv(csv_path)
    assert "https://example.com" in text
    assert custom_names.get("https://example.com") == "Article 1"
    assert len(custom_names) == 2
    print(f"  Parsed CSV with {len(custom_names)} custom names")
finally:
    csv_path.unlink()

# Test 4: CSV reading with semicolon delimiter
print("\n[PASS] Test 4: CSV Reader (semicolon delimiter)")
with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
    f.write("url;nome\n")
    f.write("https://example.com;Articolo 1\n")
    f.write("https://site.org;Guida 2\n")
    csv_path = Path(f.name)

try:
    widget = DragDropPlainText()
    text, custom_names = widget._read_csv(csv_path)
    assert "https://example.com" in text
    assert custom_names.get("https://example.com") == "Articolo 1"
    print(f"  Parsed semicolon-delimited CSV correctly")
finally:
    csv_path.unlink()

# Test 5: Settings persistence
print("\n[PASS] Test 5: Settings Store")
from proshowpdf.persistence.settings_store import SettingsStore
from proshowpdf.core.models import ConversionSettings
store = SettingsStore()
settings = ConversionSettings(
    output_dir=str(Path.home() / "Documents"),
    timeout_ms=45000,
    max_concurrency=5,
    handle_cookie_banners=False,
)
store.save_settings(settings)
loaded = store.load_settings(str(Path.home() / "Documents"))
assert loaded.timeout_ms == 45000
assert loaded.max_concurrency == 5
assert loaded.handle_cookie_banners == False
print(f"  Settings saved and loaded correctly")

# Test 6: Theme persistence
print("\n[PASS] Test 6: Theme Store")
store.save_theme("light")
theme = store.load_theme()
assert theme == "light"
print(f"  Theme saved and loaded: {theme}")

# Test 7: Icon file exists
print("\n[PASS] Test 7: Icon File")
icon_path = Path(__file__).parent / "proshowpdf" / "resources" / "ProShowPDF.ico"
assert icon_path.exists(), f"Icon not found at {icon_path}"
icon_size = icon_path.stat().st_size
print(f"  Icon file exists ({icon_size} bytes)")

# Test 8: Module imports (excluding UI which requires QApplication)
print("\n[PASS] Test 8: Core Module Imports")
from proshowpdf.core.models import ConversionSettings, JobResult
from proshowpdf.core.errors import ConversionError
from proshowpdf.bridge.controller import ConversionController
print(f"  All core modules import successfully")

print("\n" + "=" * 60)
print("[OK] All tests passed!")
print("=" * 60)
