"""Command-line entry point used by GitHub Actions (and locally).

    python -m cloud.run collect    # Yr + WeatherNext + ECMWF snapshot, recent Frost obs
    python -m cloud.run score      # prepare finished days; no pruning before remote confirmation
    python -m cloud.run export     # rebuild site/data/*.json
    python -m cloud.run all        # all three, in order
    python -m cloud.run due [--manual]  # gate: run=true/false to $GITHUB_OUTPUT (health.due)

Environment: MET_USER_AGENT, FROST_CLIENT_ID, EARTH_ENGINE_PROJECT,
EE_SERVICE_ACCOUNT_KEY (JSON text), WEATHERNEXT_ENABLED (default 1),
OPENMETEO_ENABLED (default 1; ECMWF IFS/AIFS via Open-Meteo, no key needed).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import timedelta

from . import frost, health, openmeteo, score, summarize, weathernext, yr
from .config import OBS_FETCH_DAYS, SITE_DATA_DIR, load_stations
from .store import State, _fernet, load_scored
from .timeutil import iso, now_utc


def collect(state: State) -> list[str]:
    stations = load_stations()
    fetched = now_utc()
    rows, yr_err = yr.collect(stations, os.getenv("MET_USER_AGENT", ""), fetched)
    n_yr = state.add_pending(rows)
    n_wn, wn_err = 0, []
    wn_enabled = os.getenv("WEATHERNEXT_ENABLED", "1") == "1"
    if wn_enabled:
        try:
            rows, wn_err = weathernext.collect(stations, fetched)
            n_wn = state.add_pending(rows)
        except Exception as exc:
            wn_err = [f"WeatherNext failed: {exc}"]
    n_ec, ec_err = 0, []
    ec_enabled = os.getenv("OPENMETEO_ENABLED", "1") == "1"
    if ec_enabled:  # ECMWF IFS + AIFS via Open-Meteo: collected and scored, not shown yet
        try:
            rows, ec_err = openmeteo.collect(stations, fetched)
            n_ec = state.add_pending(rows)
        except Exception as exc:
            ec_err = [f"ECMWF (Open-Meteo) failed: {exc}"]
    try:
        fetch_start = (fetched - timedelta(days=OBS_FETCH_DAYS - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0)
        obs, frost_err = frost.collect(stations, fetch_start,
                                       fetched, os.getenv("FROST_CLIENT_ID", ""))
    except Exception as exc:
        obs, frost_err = [], [f"Frost failed: {exc}"]
    n_obs = state.add_obs(obs)
    errors = yr_err + wn_err + ec_err + frost_err
    # Per source, so one source's many errors can never hide another's.
    sources = {"yr": health.source_summary("yr", n_yr, yr_err),
               "wn": health.source_summary("wn", n_wn, wn_err, enabled=wn_enabled),
               "ecmwf": health.source_summary("ecmwf", n_ec, ec_err, enabled=ec_enabled),
               "frost": health.source_summary("frost", n_obs, frost_err)}
    meta = state.meta()
    meta["first_fetch"] = meta.get("first_fetch") or iso(fetched)
    meta.setdefault("runs", []).append({"fetched_at": iso(fetched), "yr_rows": n_yr,
                                        "wn_rows": n_wn, "ecmwf_rows": n_ec, "obs_rows": n_obs,
                                        "errors": errors[:20], "sources": sources})
    state.save_meta(meta)
    print(f"collect {iso(fetched)}: yr={n_yr} wn={n_wn} ecmwf={n_ec} obs={n_obs} errors={len(errors)}")
    for name, s in sources.items():
        print(f"  {name}: rows={s['rows']} errors={s['errors']}"
              + ("" if s["enabled"] else " (disabled)") + (f" first: {s['error']}" if s["error"] else ""))
    for e in errors[:20]:
        print("  !", e)
    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["collect", "score", "export", "all", "check", "due"])
    ap.add_argument("--strict", action="store_true", help="exit 1 if any source reported errors")
    ap.add_argument("--manual", action="store_true", help="due: a manual run always collects")
    a = ap.parse_args(argv)
    _fernet(required=True)
    state = State()
    if a.step == "check":
        runs = state.meta().get("runs", [])
        if not runs:
            return 1
        # CI runs this only AFTER saving successful sources and deploying health.
        return int(any(s.get("errors", 0) for s in runs[-1].get("sources", {}).values()))
    if a.step == "due":
        go, why = health.due(state.meta(), manual=a.manual)
        print(("collect: " if go else "skip: ") + why)
        if os.getenv("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write(f"run={'true' if go else 'false'}\n")
        return 0
    errors = []
    if a.step in ("collect", "all"):
        errors = collect(state)
    if a.step in ("score", "all"):
        print("prepared days (pending retained until origin confirmation):", score.finalize(state) or "none ready")
    if a.step in ("export", "all"):
        summarize.build(load_scored())
        h = health.write(state.meta(), SITE_DATA_DIR)
        print("site data rebuilt; health:", {k: v["status"] for k, v in h["sources"].items()})
    return 1 if (a.strict and errors) else 0


if __name__ == "__main__":
    sys.exit(main())
