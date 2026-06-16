# PyInstaller onedir spec for Windows x64.
# Bundles ONLY the Chromium build that the installed Playwright pins (plus its
# headless shell and ffmpeg), not the whole ms-playwright cache, then points
# PLAYWRIGHT_BROWSERS_PATH at it at runtime (see rthook_playwright.py).
import json
import os
from pathlib import Path

import playwright

block_cipher = None

# Per-user Playwright browser cache produced by `playwright install chromium`.
_pw_cache = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"

# Resolve the browser revisions this Playwright version pins, so we bundle the
# exact folders the app uses and skip firefox/webkit/older builds.
_browsers_json = Path(playwright.__file__).parent / "driver" / "package" / "browsers.json"
_revisions: dict[str, str] = {}
if _browsers_json.exists():
    _data = json.loads(_browsers_json.read_text(encoding="utf-8"))
    _revisions = {b["name"]: str(b.get("revision")) for b in _data.get("browsers", [])}

# Folder name prefixes we want from the cache (underscore in the shell folder).
_wanted = [p for p in (
    f"chromium-{_revisions.get('chromium', '')}",
    f"chromium_headless_shell-{_revisions.get('chromium-headless-shell', '')}",
    f"ffmpeg-{_revisions.get('ffmpeg', '')}",
) if not p.endswith("-")]

browser_datas = []
if _pw_cache.exists():
    for child in _pw_cache.iterdir():
        # Use resolved prefixes when available; otherwise fall back to all
        # chromium/ffmpeg folders (still excludes firefox/webkit/mcp-chrome).
        keep = (
            any(child.name == p or child.name.startswith(p) for p in _wanted)
            if _wanted
            else (child.name.startswith("chromium") or child.name.startswith("ffmpeg"))
        )
        if keep:
            browser_datas.append((str(child), f"ms-playwright/{child.name}"))

a = Analysis(
    ["..\\proshowpdf\\__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("..\\proshowpdf\\resources", "proshowpdf/resources"),
        *browser_datas,
    ],
    hiddenimports=["playwright"],
    hookspath=[],
    runtime_hooks=["packaging\\rthook_playwright.py"],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="ProShowPDF",
    console=False, target_arch="x86_64",
)
coll = COLLECT(exe, a.binaries, a.datas, name="ProShowPDF")
