"""QSettings wrapper persisting user preferences across sessions."""
from __future__ import annotations

from PySide6.QtCore import QSettings

from proshowpdf.core.models import ConflictPolicy, ConversionSettings

_ORG = "ProfessionalShow"
_APP = "ProShowPDF"


class SettingsStore:
    """Loads/saves ConversionSettings (+ theme) via QSettings."""

    def __init__(self) -> None:
        self._qs = QSettings(_ORG, _APP)

    def load_settings(self, default_output_dir: str) -> ConversionSettings:
        qs = self._qs
        return ConversionSettings(
            output_dir=qs.value("output_dir", default_output_dir, str),
            width_px=int(qs.value("width_px", 1280)),
            max_concurrency=int(qs.value("max_concurrency", 3)),
            timeout_ms=int(qs.value("timeout_ms", 30_000)),
            retries=int(qs.value("retries", 2)),
            handle_cookie_banners=qs.value("cookies", True, bool),
            conflict_policy=ConflictPolicy(qs.value("conflict", "rename", str)),
        )

    def save_settings(self, s: ConversionSettings) -> None:
        qs = self._qs
        qs.setValue("output_dir", s.output_dir)
        qs.setValue("width_px", s.width_px)
        qs.setValue("max_concurrency", s.max_concurrency)
        qs.setValue("timeout_ms", s.timeout_ms)
        qs.setValue("retries", s.retries)
        qs.setValue("cookies", s.handle_cookie_banners)
        qs.setValue("conflict", s.conflict_policy.value)

    def load_theme(self) -> str:
        return self._qs.value("theme", "light", str)

    def save_theme(self, theme: str) -> None:
        self._qs.setValue("theme", theme)
