"""Entrypoint with a hard 64-bit guard (Playwright Chromium is x64-only)."""
from __future__ import annotations

import ctypes
import struct
import sys


def _is_64bit() -> bool:
    return struct.calcsize("P") * 8 == 64


def _show_error_and_exit(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(0, message, "ProShow PDF", 0x10)
    except Exception:
        print(message, file=sys.stderr)
    sys.exit(1)


def main() -> int:
    if not _is_64bit():
        _show_error_and_exit(
            "ProShow PDF richiede Windows a 64 bit (x64).\n"
            "Il Chromium di Playwright è disponibile solo per x64."
        )
    from proshowpdf.app import run
    return run()


if __name__ == "__main__":
    sys.exit(main())
