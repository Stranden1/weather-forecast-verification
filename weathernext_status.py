from __future__ import annotations

import re
import sqlite3
from collections import deque
from pathlib import Path


PROVIDER = "WeatherNext3-mean"
_TIMESTAMP = r"(?P<timestamp>\S+)\s{2}"
_SUCCESS = re.compile(
    _TIMESTAMP + r".*\bWeatherNext=(?P<added>\d+) new values; run=(?P<run>\S+)"
)
_ERROR = re.compile(_TIMESTAMP + r".*\bWeatherNext ERROR (?P<detail>.+)$")
_DISABLED = re.compile(_TIMESTAMP + r".*\bWeatherNext disabled\b")


def _weather_next_log_entries(log_path: Path, limit: int = 15) -> list[dict]:
    """Return finalized WeatherNext outcomes, oldest-to-newest in the file."""
    entries: deque[dict] = deque(maxlen=limit)
    if not log_path.exists():
        return []

    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            success = _SUCCESS.search(line)
            error = _ERROR.search(line)
            disabled = _DISABLED.search(line)
            if success:
                added = int(success.group("added"))
                entries.append(
                    {
                        "timestamp": success.group("timestamp"),
                        "status": "up to date" if added else "waiting for new run",
                        "new_values": added,
                        "model_run": success.group("run"),
                        "detail": f"Saved {added:,} new statistic values",
                    }
                )
            elif error:
                entries.append(
                    {
                        "timestamp": error.group("timestamp"),
                        "status": "error",
                        "new_values": None,
                        "model_run": None,
                        "detail": error.group("detail"),
                    }
                )
            elif disabled:
                entries.append(
                    {
                        "timestamp": disabled.group("timestamp"),
                        "status": "disabled",
                        "new_values": None,
                        "model_run": None,
                        "detail": "Collector was disabled for this background run",
                    }
                )
    return list(entries)


def load_weathernext_status(
    con: sqlite3.Connection, log_path: Path, log_limit: int = 15
) -> tuple[dict, list[dict]]:
    tables = {
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    has_samples = "weathernext_samples" in tables

    active_stations = con.execute(
        "SELECT COUNT(*) FROM locations WHERE active=1"
    ).fetchone()[0]
    latest_run = con.execute(
        "SELECT MAX(issued_at) FROM forecast_runs WHERE provider=?", (PROVIDER,)
    ).fetchone()[0]
    forecast_points = con.execute(
        """
        SELECT COUNT(*)
        FROM forecasts f
        JOIN forecast_runs r ON r.id=f.run_id
        WHERE r.provider=?
        """,
        (PROVIDER,),
    ).fetchone()[0]

    statistic_values = 0
    stored_at = None
    if has_samples:
        statistic_values, stored_at = con.execute(
            """
            SELECT COUNT(*), MAX(s.retrieved_at)
            FROM weathernext_samples s
            JOIN forecast_runs r ON r.id=s.run_id
            WHERE r.provider=?
            """,
            (PROVIDER,),
        ).fetchone()

    entries = _weather_next_log_entries(log_path, log_limit)
    attempts = [entry for entry in entries if "disabled" not in entry["detail"].lower()]
    successes = [entry for entry in attempts if entry["status"] != "error"]
    latest_attempt = attempts[-1] if attempts else None
    latest_success = successes[-1] if successes else None

    if latest_attempt and latest_attempt["status"] == "error":
        collector_status = "error"
    elif latest_success:
        collector_status = latest_success["status"]
    elif latest_run:
        collector_status = "up to date"
    else:
        collector_status = "waiting for new run"

    summary = {
        "latest_run": latest_run,
        "last_attempt": latest_attempt["timestamp"] if latest_attempt else stored_at,
        "last_success": latest_success["timestamp"] if latest_success else stored_at,
        "active_stations": active_stations,
        "forecast_points": forecast_points,
        "statistic_values": statistic_values,
        "new_values": latest_attempt["new_values"] if latest_attempt else None,
        "collector_status": collector_status,
    }
    return summary, list(reversed(entries))
