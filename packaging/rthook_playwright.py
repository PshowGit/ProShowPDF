# Runtime hook: point Playwright at the bundled browser cache when frozen.
import os
import sys

if getattr(sys, "frozen", False):
    bundled = os.path.join(sys._MEIPASS, "ms-playwright")
    if os.path.isdir(bundled):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = bundled
