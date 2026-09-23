"""Command-line entry point used by GitHub Actions (and locally).

    python -m cloud.run collect    # Yr + WeatherNext snapshot, recent Frost obs
    python -m cloud.run score      # score finished days, prune working data
    python -m cloud.run export     # rebuild site/data/*.json
    python -m cloud.run all        # all three, in order

Environment: MET_USER_AGENT, FROST_CLIENT_ID, EARTH_ENGINE_PROJECT,
EE_SERVICE_ACCOUNT_KEY (JSON text), WEATHERNEXT_ENABLED (default 1).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import timedelta

from . import frost, score, summarize, weathernext, yr
from .config import OBS_KEEP_DAYS, load_stations
from .store import State, load_scored
from .timeutil import iso, now_utc


def collect(state: State) -> list[str]:
    stations = load_stations()
    fetched = now_utc()
    errors: list[str] = []
    rows, err = yr.collect(stations, os.getenv("MET_USER_AGENT", ""), fetched)
    errors += err
    n_yr = state.add_pending(rows)
    n_wn = 0
    if os.getenv("WEATHERNEXT_ENABLED", "1") == "1":
        try:
            rows, err = weathernext.collect(stations, fetched)
            errors += err
            n_wn = state.add_pending(rows)
        except Exception as exc:
            errors.append(f"WeatherNext failed: {exc}")
    try:
        obs, err = frost.collect(stations, fetched - timedelta(days=OBS_KEEP_DAYS - 1), fetched,
                                 os.getenv("FROST_CLIENT_ID", ""))
        errors += err
    except Exception as exc:
        obs = []
        errors.append(f"Frost failed: {exc}")
    n_obs = state.add_obs(obs)
    meta = state.meta()
    meta["first_fetch"] = meta.get("first_fetch") or iso(fetched)
    meta.setdefault("runs", []).append({"fetched_at": iso(fetched), "yr_rows": n_yr,
                                        "wn_rows": n_wn, "obs_rows": n_obs, "errors": errors[:20]})
    state.save_meta(meta)
    print(f"collect {iso(fetched)}: yr={n_yr} wn={n_wn} obs={n_obs} errors={len(errors)}")
    for e in errors[:20]:
        print("  !", e)
    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["collect", "score", "export", "all"])
    ap.add_argument("--strict", action="store_true", help="exit 1 if any source reported errors")
    a = ap.parse_args(argv)
    state = State()
    errors = []
    if a.step in ("collect", "all"):
        errors = collect(state)
    if a.step in ("score", "all"):
        print("scored days:", score.finalize(state) or "none ready")
    if a.step in ("export", "all"):
        summarize.build(load_scored())
        print("site data rebuilt")
    return 1 if (a.strict and errors) else 0


if __name__ == "__main__":
    sys.exit(main())
