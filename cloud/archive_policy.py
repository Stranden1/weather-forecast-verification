"""Yr-only archive policy: two UTC receipt windows, independent of scores."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

UTC = timezone.utc
POLICY_VERSION = "yr-twice-daily-v1"


@dataclass(frozen=True)
class Slot:
    day: date
    name: str

    def __post_init__(self):
        if self.name not in ("am", "pm"):
            raise ValueError("Unknown archive slot")

    @property
    def start(self) -> datetime:
        return datetime.combine(self.day, time(8 if self.name == "am" else 20, 30), UTC)

    @property
    def end(self) -> datetime:
        return self.start + timedelta(hours=4, minutes=30)

    @property
    def directory(self) -> str:
        return f"{self.day:%Y/%m/%d}/{self.name}"

    def contains(self, at: datetime) -> bool:
        return self.start <= utc(at) < self.end

    def record(self) -> dict:
        return {"slot_date": self.day.isoformat(), "slot": self.name,
                "window_start": self.start.isoformat(), "window_end": self.end.isoformat()}


def utc(at: datetime) -> datetime:
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("Archive timestamps need a timezone")
    return at.astimezone(UTC)


def active_slot(at: datetime, start_day: date) -> Slot | None:
    at = utc(at)
    for day in (at.date() - timedelta(days=1), at.date()):
        if day < start_day:
            continue
        for name in ("am", "pm"):
            slot = Slot(day, name)
            if slot.contains(at):
                return slot
    return None


def closed_slots(start_day: date, at: datetime):
    """No missing-slot records before the declared activation date."""
    at = utc(at)
    day = start_day
    while day <= at.date():
        for name in ("am", "pm"):
            slot = Slot(day, name)
            if slot.end <= at:
                yield slot
        day += timedelta(days=1)
