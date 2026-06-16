"""Typed exception hierarchy for conversion failures."""
from __future__ import annotations


class ConversionError(Exception):
    """Base class for all conversion errors."""
    error_type = "conversion_error"


class NavigationError(ConversionError):
    """Page failed to navigate (DNS, connection, HTTP error)."""
    error_type = "navigation"


class ConversionTimeoutError(ConversionError):
    """Navigation or rendering exceeded the configured timeout."""
    error_type = "timeout"


class RenderError(ConversionError):
    """Page loaded but PDF rendering/measurement failed."""
    error_type = "render"


class OutputError(ConversionError):
    """Failed to write the PDF to disk."""
    error_type = "output"
