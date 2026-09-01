"""CIRUS — Time utilities."""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(tz=timezone.utc)


def utcnow_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return utcnow().isoformat()


def duration_ms(start: datetime, end: datetime | None = None) -> int:
    """Compute duration between two datetimes in milliseconds."""
    end = end or utcnow()
    return int((end - start).total_seconds() * 1000)
