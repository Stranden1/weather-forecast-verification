"""One-off: convert the local 2.4 GB weather.db into compact scored day files.

Opens the database READ-ONLY and never modifies it. It rebuilds, for every
past Yr collection, the same "snapshot" the cloud collector takes (Yr from that
run, plus the newest WeatherNext run that had been collected by then), then
applies exactly the same scoring as the cloud pipeline.

    python -m cloud.migrate_sqlite --db data/weather.db --until 2026-10-01

--until is exclusive: use the first UTC day the cloud collector owns.
Existing day files are never overwritten, with one exception:

    python -m cloud.migrate_sqlite --db data/weather.db --from 2026-09-23 \
        --until 2026-10-05 --fill-missing-wn

rewrites cloud-scored days that contain NO WeatherNext values at all (e.g. while
the cloud service account was waiting for WeatherNext access), using the PC
collector's copy, and only when that copy does contain WeatherNext values.
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .config import SCORED_DIR, wanted_leads
from .score import score_targets
from .store import scored_path, write_scored

WN = "WeatherNext3-mean"
WN_METRICS = {"air_temperature": "t", "wind_speed": "w", "precipitation_1h": "p"}
WN_STATS = {"mean": "", "p10": "_p10", "p50": "_p50", "p90": "_p90"}
GRACE_MIN = 60  # WN is collected minutes after Yr in the same background run


def ts(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True, format="mixed", errors="coerce")


def fmt(s: pd.Series) -> pd.Series:
    return s.dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def in_windows(lead: pd.Series) -> pd.Series:
    m = pd.Series(False, index=lead.index)
    for _, lo, hi in wanted_leads():
        m |= lead.between(lo, hi)
    return m


def station_pending(con, loc_id: int, station: str) -> pd.DataFrame:
    runs = pd.read_sql_query(
        "SELECT id, provider, issued_at, retrieved_at FROM forecast_runs WHERE location_id=?",
        con, params=(loc_id,))
    runs["issued"], runs["retrieved"] = ts(runs.issued_at), ts(runs.retrieved_at)
    met = runs[runs.provider == "MET"]
    if met.empty:
        return pd.DataFrame()
    f = pd.read_sql_query(
        f"SELECT run_id, valid_at, air_temperature t, wind_speed w, precipitation_1h p "
        f"FROM forecasts WHERE run_id IN ({','.join(map(str, met.id))})", con)
    f["valid"] = ts(f.valid_at)
    f = f.merge(met[["id", "issued", "retrieved"]], left_on="run_id", right_on="id")
    inst = f[["run_id", "issued", "retrieved", "valid", "t", "w"]].rename(columns={"valid": "target"})
    pr = f[["run_id", "issued", "retrieved", "valid", "p"]].copy()
    pr["target"] = pr.pop("valid") + pd.Timedelta(hours=1)  # Yr next_1_hours -> interval end
    yr = inst.merge(pr, on=["run_id", "issued", "retrieved", "target"], how="outer")
    yr["lead_h"] = (yr.target - yr.retrieved).dt.total_seconds() / 3600
    yr = yr[in_windows(yr.lead_h)]
    yr = yr.assign(provider="yr", station=station, fetched_at=fmt(yr.retrieved),
                   issued_at=fmt(yr.issued), target=fmt(yr.target))

    wn_runs = runs[runs.provider == WN]
    out = [yr]
    if not wn_runs.empty:
        s = pd.read_sql_query(
            f"SELECT run_id, valid_at, metric, statistic, value, retrieved_at FROM weathernext_samples "
            f"WHERE run_id IN ({','.join(map(str, wn_runs.id))}) "
            f"AND metric IN ('air_temperature','wind_speed','precipitation_1h') "
            f"AND statistic IN ('mean','p10','p50','p90')", con)
        s["col"] = s.metric.map(WN_METRICS) + s.statistic.map(WN_STATS)
        s = s[s.col.isin(["t", "t_p10", "t_p50", "t_p90", "w", "w_p10", "w_p50", "w_p90",
                          "p", "p_p50", "p_p90"])]
        avail = s.groupby("run_id").retrieved_at.max().pipe(ts).rename("available")
        wide = s.pivot_table(index=["run_id", "valid_at"], columns="col", values="value",
                             aggfunc="first").reset_index()
        wide["target"] = ts(wide.valid_at)
        wn_runs = wn_runs.merge(avail, left_on="id", right_index=True)
        rows = []
        for fetch in sorted(met.retrieved.dropna().unique()):
            fetch = pd.Timestamp(fetch)
            ok = wn_runs[(wn_runs.available <= fetch + pd.Timedelta(minutes=GRACE_MIN))
                         & (wn_runs.issued < fetch)]
            if ok.empty:
                continue
            run = ok.sort_values("issued").iloc[-1]
            w = wide[wide.run_id == run.id].copy()
            w["lead_h"] = (w.target - fetch).dt.total_seconds() / 3600
            w = w[in_windows(w.lead_h)]
            if w.empty:
                continue
            w = w.assign(fetched_at=fetch.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         issued_at=run.issued.strftime("%Y-%m-%dT%H:%M:%SZ"))
            rows.append(w)
        if rows:
            wn = pd.concat(rows, ignore_index=True)
            wn = wn.assign(provider="wn", station=station, target=fmt(wn.target))
            out.append(wn)
    return pd.concat(out, ignore_index=True)


def observations(con, loc_id: int, station: str) -> pd.DataFrame:
    o = pd.read_sql_query(
        "SELECT observed_at, air_temperature t, wind_speed w, precipitation_1h p "
        "FROM observations WHERE location_id=?", con, params=(loc_id,))
    o["time"] = ts(o.observed_at)
    o = o[o.time.dt.minute.eq(0) & o.time.dt.second.eq(0)]
    # Several source rows can exist per hour; keep a value only if they agree.
    agg = o.groupby("time").agg(**{c: (c, lambda s: s.dropna().iloc[0]
                                       if s.dropna().nunique() == 1 else None) for c in "twp"})
    agg = agg.reset_index()
    agg["time"] = fmt(agg.time)
    agg["station"] = station
    return agg


def has_wn(path: Path) -> bool:
    df = pd.read_csv(path, usecols=lambda c: c == "wn_t")
    return "wn_t" in df and df.wn_t.notna().any()


def migrate(db: Path, until: date, out_root: Path = SCORED_DIR, log=print,
            start: date | None = None, fill_missing_wn: bool = False) -> list[str]:
    con = sqlite3.connect(f"file:{Path(db).resolve().as_posix()}?mode=ro", uri=True)
    try:
        locs = pd.read_sql_query(
            "SELECT id, UPPER(station_id) station FROM locations WHERE active=1 AND station_id IS NOT NULL",
            con)
        pend, obs = [], []
        for i, r in enumerate(locs.itertuples(), 1):
            pend.append(station_pending(con, r.id, r.station))
            obs.append(observations(con, r.id, r.station))
            log(f"station {i}/{len(locs)} {r.station}")
    finally:
        con.close()
    pending = pd.concat(pend, ignore_index=True)
    ob = pd.concat(obs, ignore_index=True)
    first = start or pd.to_datetime(pending.target.min()).date()
    written, day = [], first
    while day < until:
        path = scored_path(day, out_root)
        if path.exists() and fill_missing_wn and not has_wn(path):
            p = pending[pending.target.str.startswith(day.isoformat())]
            o = ob[ob.time.str.startswith(day.isoformat())]
            sc = score_targets(p, o)
            if sc.wn_t.notna().any():
                path.unlink()
                write_scored(day, sc, out_root)
                written.append(day.isoformat())
                log(f"{day}: replaced cloud file without WeatherNext ({len(sc)} rows)")
            else:
                log(f"{day}: PC copy has no WeatherNext either, kept")
        elif path.exists():
            log(f"{day}: exists, kept")
        else:
            p = pending[pending.target.str.startswith(day.isoformat())]
            o = ob[ob.time.str.startswith(day.isoformat())]
            sc = score_targets(p, o)
            write_scored(day, sc, out_root)
            written.append(day.isoformat())
            log(f"{day}: {len(sc)} scored rows")
        day += timedelta(days=1)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="data/weather.db")
    ap.add_argument("--until", required=True, help="exclusive UTC date, YYYY-MM-DD")
    ap.add_argument("--out", default=str(SCORED_DIR))
    ap.add_argument("--from", dest="start", help="first UTC date to process, YYYY-MM-DD")
    ap.add_argument("--fill-missing-wn", action="store_true",
                    help="replace existing day files that contain no WeatherNext values")
    a = ap.parse_args(argv)
    migrate(Path(a.db), date.fromisoformat(a.until), Path(a.out),
            start=date.fromisoformat(a.start) if a.start else None,
            fill_missing_wn=a.fill_missing_wn)


if __name__ == "__main__":
    main()
