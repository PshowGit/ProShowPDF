# PyInstaller onedir spec for Windows x64.
# Bundles Playwright's Chromium by collecting the ms-playwright browser cache
# into the dist folder and pointing PLAYWRIGHT_BROWSERS_PATH at it at runtime.
import os
from pathlib import Path

block_cipher = None

# Locate the per-user Playwright browser cache produced by `playwright install`.
_pw_cache = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"
browser_datas = [(str(_pw_cache), "ms-playwright")] if _pw_cache.exists() else []

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
