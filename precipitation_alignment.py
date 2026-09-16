"""Canonical one-hour precipitation intervals; no scoring or database writes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


ONE_HOUR = timedelta(hours=1)


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Precipitation timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def frost_interval(reference_time: str) -> tuple[datetime, datetime]:
    """Frost PT1H referenceTime is the end of [T-1h, T)."""
    end = _utc(reference_time)
    return end - ONE_HOUR, end


def met_interval(valid_at: str) -> tuple[datetime, datetime]:
    """MET next_1_hours begins at valid_at and covers [T, T+1h)."""
    start = _utc(valid_at)
    return start, start + ONE_HOUR


def weathernext_interval(end_time: str) -> tuple[datetime, datetime]:
    """WeatherNext total_precipitation_1hr ends at end_time."""
    end = _utc(end_time)
    return end - ONE_HOUR, end
