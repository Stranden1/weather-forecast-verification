"""Pipeline health for the status line under the page title (health.json).

Built at export from the run log in the working state's meta.json. Only
statuses and counts are published, never raw error messages.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import SITE_DATA_DIR
from .timeutil import iso, parse

SOURCES = {"yr": "Yr ", "wn": "WeatherNext", "frost": "Frost"}  # error-message prefixes
ROW_KEYS = {"yr": "yr_rows", "wn": "wn_rows", "frost": "obs_rows"}
# Lenient expectation for the "runs in 48 h" count on the page. The real cadence is 2.5 h
# (MIN_GAP_MIN); 3 h leaves room for retries and late timer ticks without a false warning.
RUN_EVERY_H = 3
WINDOW_H = 48
# A scheduled run collects only when the last complete run is at least this old. The timer
# ticks every 30 min, and the gate runs a second or two earlier in the job than the moment
# the previous run stamped, so the gap is set just under five ticks (150 min): the cadence is
# a steady 2.5 h instead of 2.5 or 3 h by runner jitter (DECISIONS.md, 13 Nov 2026).
MIN_GAP_MIN = 145
# A run is complete only when every enabled forecast source delivered rows. Frost alone is
# not enough: forecast snapshots missed now can never be collected later.
FORECAST_SOURCES = ("yr", "wn")
FAIL_AFTER_RUNS = 2  # `cloud.run check` fails only when a source errs this many runs in a row
# Earth Engine's answers when the caller may not read WeatherNext yet.
NO_ACCESS = re.compile(r"does not have access|does not have required permission|"
                       r"PERMISSION_DENIED|not authorized", re.I)


def source_summary(name: str, rows: int, errors: list[str], enabled: bool = True) -> dict:
    """What run.collect stores per source (first error kept for the log only)."""
    return {"rows": int(rows), "errors": len(errors), "error": errors[0][:300] if errors else None,
            "enabled": enabled}


def _sources(run: dict) -> dict:
    """Per-source summary; older run records only have row counts and the first 20 errors."""
    if "sources" in run:
        return run["sources"]
    errs = run.get("errors") or []
    out = {}
    for name, prefix in SOURCES.items():
        mine = [e for e in errs if e.startswith(prefix)]
        out[name] = source_summary(name, run.get(ROW_KEYS[name], 0), mine)
    return out


def status(name: str, src: dict) -> str:
    if not src.get("enabled", True):
        return "paused"
    rows, errors = src.get("rows", 0), src.get("errors", 0)
    if name == "wn" and rows == 0 and NO_ACCESS.search(src.get("error") or ""):
        return "no_access"
    if rows and not errors:
        return "ok"
    if rows:
        return "partial"
    return "error" if errors else "no_data"


def failed(run: dict) -> bool:
    """A run failed when no enabled source delivered anything."""
    srcs = _sources(run)
    return not any(s.get("rows", 0) for s in srcs.values() if s.get("enabled", True))


def missing_forecasts(run: dict) -> list[str]:
    """Enabled forecast sources (Yr, WeatherNext) that delivered no rows in this run."""
    srcs = _sources(run)
    return [name for name in FORECAST_SOURCES
            if srcs.get(name, {}).get("enabled", True) and not srcs.get(name, {}).get("rows", 0)]


def complete(run: dict) -> bool:
    return not missing_forecasts(run)


def run_errors(run: dict) -> dict[str, int]:
    """Error count per source in one run, the Yr archive included."""
    out = {name: s.get("errors", 0) for name, s in _sources(run).items()}
    out["yr_archive"] = (run.get("yr_archive") or {}).get("errors", 0)
    return out


def persistent_errors(runs: list[dict], n: int = FAIL_AFTER_RUNS) -> list[str]:
    """Sources with errors in each of the last n runs. A one-off outage that the next run
    gets past (an API timeout) is left out, so it doesn't turn the workflow red."""
    if len(runs) < n:
        return []
    recent = [run_errors(r) for r in runs[-n:]]
    return sorted(name for name in recent[-1] if all(r.get(name, 0) for r in recent))


def expected_runs(first: datetime, now: datetime) -> int:
    """Runs the schedule should have produced in the last WINDOW_H hours.

    Right after the start fewer runs are possible, so only time since the first run counts.
    """
    def count(since: datetime) -> int:
        return math.floor(max(0.0, (now - since).total_seconds() / 3600) / RUN_EVERY_H)

    window_start = now - timedelta(hours=WINDOW_H)
    return min(count(window_start), count(max(first, window_start)) + 1)


def build(meta: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    runs = sorted(meta.get("runs") or [], key=lambda r: r["fetched_at"])
    out = {"generated_at": iso(now), "last_run": None, "last_run_failed": None,
           "last_success": None, "sources": {}, "runs_48h": 0, "expected_48h": 0}
    if not runs:
        return out
    last = runs[-1]
    if "yr_archive" in last:
        out["yr_archive"] = {k: last["yr_archive"].get(k) for k in
                             ("enabled", "status", "captured_stations", "closed_slots", "incomplete_slots", "errors", "published")}
    ok = [r for r in runs if not failed(r)]
    out.update(last_run=last["fetched_at"], last_run_failed=failed(last),
               last_success=ok[-1]["fetched_at"] if ok else None)
    out["sources"] = {name: {"status": status(name, s), "rows": s.get("rows", 0),
                             "errors": s.get("errors", 0)}
                      for name, s in _sources(last).items()}
    hours = lambda r: (now - parse(r["fetched_at"])).total_seconds() / 3600
    out["runs_48h"] = sum(1 for r in runs if 0 <= hours(r) <= WINDOW_H)
    out["expected_48h"] = expected_runs(parse(meta.get("first_fetch") or runs[0]["fetched_at"]), now)
    return out


def due(meta: dict, now: datetime | None = None, manual: bool = False) -> tuple[bool, str]:
    """Whether this run should collect, and why (for the workflow's gate step)."""
    if manual:
        return True, "manual run"
    now = now or datetime.now(timezone.utc)
    runs = sorted(meta.get("runs") or [], key=lambda r: r["fetched_at"])
    if not runs:
        return True, "no run yet"
    last = runs[-1]
    missing = missing_forecasts(last)
    if missing:
        # Retry at the next tick: a 6-hour forecast outage would otherwise leave permanent holes.
        return True, f"last run had no rows from {', '.join(missing)}; retrying"
    age_min = (now - parse(last["fetched_at"])).total_seconds() / 60
    if 0 <= age_min < MIN_GAP_MIN:
        return False, f"last complete run {age_min:.0f} min ago (< {MIN_GAP_MIN})"
    return True, f"last complete run {age_min:.0f} min ago"


def write(meta: dict, out_dir: Path = SITE_DATA_DIR, now: datetime | None = None) -> dict:
    h = build(meta, now)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "health.json").write_text(json.dumps(h, separators=(",", ":")), encoding="utf-8")
    return h
