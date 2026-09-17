"""Collection completion health from the existing background log."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


SOURCES = ("MET", "WeatherNext", "Frost")
SOURCE_LABELS = {"MET": "Yr/MET", "WeatherNext": "WeatherNext", "Frost": "Frost"}
OK_HOURS = 8
STALE_HOURS = 12
GAP_HOURS = 12
GAP_LOOKBACK_DAYS = 7

_LINE = re.compile(r"^(?P<timestamp>\S+)\s{2}(?P<body>.*)$")
_SOURCE = re.compile(
    r"^SOURCE\s{2}(?P<source>MET|WeatherNext|Frost)\s{2}"
    r"(?P<outcome>OK|ERROR|SKIPPED)\b"
)


def _utc(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("Collection timestamps must include a UTC offset")
    return value.astimezone(timezone.utc)


def append_source_event(
    log_path: Path, source: str, outcome: str, detail: str = ""
) -> None:
    """Append a stable source-level outcome without changing collector storage."""
    if source not in SOURCES:
        raise ValueError(f"Unknown collection source: {source}")
    outcome = outcome.upper()
    if outcome not in {"OK", "ERROR", "SKIPPED"}:
        raise ValueError(f"Unknown collection outcome: {outcome}")
    clean_detail = " ".join(str(detail).split())
    suffix = f"  {clean_detail}" if clean_detail else ""
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp}  SOURCE  {source}  {outcome}{suffix}\n")


def _legacy_outcomes(body: str) -> list[tuple[str, str]]:
    """Read finalized pre-health summary lines already present in background.log."""
    if not (body.startswith("OK  ") or body.startswith("PARTIAL ERROR  ")):
        return []
    summary = body.split("  ", 1)[1]
    outcomes = []
    for part in summary.split(" | "):
        if part.startswith("MET="):
            outcomes.append(("MET", "OK" if re.search(r"['\"]errors['\"]:\s*\[\s*\]", part) else "ERROR"))
        elif part.startswith("Frost="):
            outcomes.append(("Frost", "OK" if re.search(r"['\"]errors['\"]:\s*\[\s*\]", part) else "ERROR"))
        elif part.startswith("Frost skipped"):
            outcomes.append(("Frost", "SKIPPED"))
        elif part.startswith("WeatherNext="):
            outcomes.append(("WeatherNext", "OK"))
        elif part.startswith("WeatherNext ERROR"):
            outcomes.append(("WeatherNext", "ERROR"))
        elif part.startswith("WeatherNext disabled"):
            outcomes.append(("WeatherNext", "SKIPPED"))
    return outcomes


def read_collection_events(log_path: Path) -> list[dict]:
    events = []
    if not log_path.exists():
        return events
    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            matched = _LINE.match(raw_line.strip())
            if not matched:
                continue
            try:
                timestamp = _utc(matched.group("timestamp"))
            except ValueError:
                continue
            body = matched.group("body")
            explicit = _SOURCE.match(body)
            outcomes = (
                [(explicit.group("source"), explicit.group("outcome"))]
                if explicit
                else _legacy_outcomes(body)
            )
            for source, outcome in outcomes:
                events.append(
                    {"timestamp": timestamp, "source": source, "outcome": outcome}
                )
    return events


def health_status(age_hours: float | None, latest_outcome: str | None = None) -> str:
    if age_hours is None or age_hours > STALE_HOURS:
        return "Stale / attention needed"
    if age_hours > OK_HOURS or latest_outcome == "ERROR":
        return "Delayed"
    return "OK"


def format_age(age_hours: float | None) -> str:
    if age_hours is None:
        return "—"
    total_minutes = max(0, round(age_hours * 60))
    days, remaining = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remaining, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _collection_times(events: list[dict], source: str) -> list[datetime]:
    """Collapse explicit+legacy entries from the same run into one completion."""
    times = sorted(
        event["timestamp"]
        for event in events
        if event["source"] == source and event["outcome"] == "OK"
    )
    collapsed: list[datetime] = []
    for timestamp in times:
        if collapsed and timestamp - collapsed[-1] <= timedelta(hours=1):
            collapsed[-1] = timestamp
        else:
            collapsed.append(timestamp)
    return collapsed


def load_collection_health(log_path: Path, now: datetime | None = None) -> dict:
    now = _utc(now or datetime.now(timezone.utc))
    events = [event for event in read_collection_events(log_path) if event["timestamp"] <= now]
    sources = {}
    for source in SOURCES:
        attempts = [
            event
            for event in events
            if event["source"] == source and event["outcome"] != "SKIPPED"
        ]
        successes = [event for event in attempts if event["outcome"] == "OK"]
        latest_attempt = max(attempts, key=lambda event: event["timestamp"]) if attempts else None
        latest_success = max(successes, key=lambda event: event["timestamp"]) if successes else None
        success_time = latest_success["timestamp"] if latest_success else None
        age_hours = (now - success_time).total_seconds() / 3600 if success_time else None
        latest_outcome = latest_attempt["outcome"] if latest_attempt else None
        sources[source] = {
            "source": source,
            "label": SOURCE_LABELS[source],
            "last_success": success_time,
            "age_hours": age_hours,
            "age": format_age(age_hours),
            "status": health_status(age_hours, latest_outcome),
            "latest_attempt": latest_attempt["timestamp"] if latest_attempt else None,
            "latest_outcome": latest_outcome,
        }

    cutoff = now - timedelta(days=GAP_LOOKBACK_DAYS)
    yr_times = [time for time in _collection_times(events, "MET") if time >= cutoff]
    gaps = [
        {"start": earlier, "end": later, "hours": (later - earlier).total_seconds() / 3600}
        for earlier, later in zip(yr_times, yr_times[1:])
        if later - earlier > timedelta(hours=GAP_HOURS)
    ]
    return {"sources": sources, "yr_gap": max(gaps, key=lambda gap: gap["hours"], default=None)}


def yr_stale_warning(health: dict) -> str | None:
    if health["sources"]["MET"]["status"] == "Stale / attention needed":
        return (
            "Yr collection may have a gap. Historical long-range forecasts missed "
            "during this period may not be recoverable."
        )
    return None

