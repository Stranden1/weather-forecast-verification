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
RUN_EVERY_H = 3  # keep in step with the cron in .github/workflows/collect.yml
WINDOW_H = 48
# The schedule was every 6 h until this time. Expected runs are counted per period, so the
# 48 h after the change don't read as missed runs. Both can go once the window has passed.
PREVIOUS_RUN_EVERY_H = 6
RUN_EVERY_CHANGED_AT = datetime(2026, 10, 1, 18, tzinfo=timezone.utc)
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


def expected_runs(first: datetime, now: datetime) -> int:
    """Runs the schedule should have produced in the last WINDOW_H hours.

    Right after the start fewer runs are possible, so only time since the first run counts.
    """
    def count(since: datetime) -> int:
        hours = lambda a, b: max(0.0, (b - a).total_seconds() / 3600)
        return (math.floor(hours(since, min(now, RUN_EVERY_CHANGED_AT)) / PREVIOUS_RUN_EVERY_H)
                + math.floor(hours(max(since, RUN_EVERY_CHANGED_AT), now) / RUN_EVERY_H))

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


def write(meta: dict, out_dir: Path = SITE_DATA_DIR, now: datetime | None = None) -> dict:
    h = build(meta, now)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "health.json").write_text(json.dumps(h, separators=(",", ":")), encoding="utf-8")
    return h
