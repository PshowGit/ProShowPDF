"""Pure data models shared across the core layer. No Qt, no Playwright."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class ConflictPolicy(str, Enum):
    OVERWRITE = "overwrite"
    RENAME = "rename"


@dataclass(frozen=True)
class ConversionSettings:
    """User-tunable conversion parameters."""
    output_dir: str
    width_px: int = 1280
    max_concurrency: int = 3
    timeout_ms: int = 30_000
    retries: int = 2
    handle_cookie_banners: bool = True
    conflict_policy: ConflictPolicy = ConflictPolicy.RENAME
    device_scale_factor: float = 1.0
    min_height_px: int = 100


@dataclass
class JobItem:
    """A single URL to convert."""
    url: str
    index: int
    status: JobStatus = JobStatus.QUEUED
    custom_filename: str | None = None


@dataclass
class JobResult:
    """Outcome of one conversion."""
    url: str
    index: int
    status: JobStatus
    output_path: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
