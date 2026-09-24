"""Turn pending snapshots + observations into permanent scored rows.

Pairing rule ("what you could see at the same moment"): for each station,
target hour and horizon H, use the collection run whose lead (target minus
fetch time) is closest to H, within the tolerance. Yr and WeatherNext therefore
come from the SAME fetch and have identical leads. Runs holding both providers
are preferred; ties go to the later run. Forecast errors never influence which
run is chosen.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from .config import (FINALIZE_DELAY_HOURS, HORIZON_TOLERANCE, HORIZONS, OBS_KEEP_DAYS,
                     PRECIP_HORIZONS, VALUE_COLUMNS)

YR_COLS = ["t", "t_p10", "t_p90", "w", "w_p10", "w_p90", "p", "p_min", "p_max", "p_prob"]
WN_COLS = ["t", "t_p10", "t_p50", "t_p90", "w", "w_p10", "w_p50", "w_p90", "p", "p_p50", "p_p90"]
SCORED_COLUMNS = (["target", "station", "h", "lead_h", "fetched_at", "yr_issued", "wn_issued",
                   "obs_t", "obs_w", "obs_p", "base_t", "base_w", "base_p"]
                  + [f"yr_{c}" for c in YR_COLS] + [f"wn_{c}" for c in WN_COLS])
# Observations needed before a day to give every horizon its naive baseline.
BASELINE_LOOKBACK_DAYS = 11


def baseline_offset_hours(lead_h) -> np.ndarray:
    """Naive "same as before": the observation at the same time of day on the
    latest day already observed at fetch time, i.e. target - 24*ceil(lead/24) h.

    Uses the actual lead, not the nominal horizon, so the naive value is never
    measured after the forecast was fetched (e.g. lead 26.5 h for "1 day" -> 48 h back).
    """
    return 24 * np.ceil(np.asarray(lead_h, dtype=float) / 24)


def obs_window(obs: pd.DataFrame, day: date) -> pd.DataFrame:
    """Observations for `day` plus the lookback its baselines need."""
    t = obs["time"].astype(str)
    lo = (day - timedelta(days=BASELINE_LOOKBACK_DAYS)).isoformat()
    return obs[(t >= lo) & (t < (day + timedelta(days=1)).isoformat())]


def add_baseline(scored: pd.DataFrame, obs: pd.DataFrame) -> pd.DataFrame:
    back = (pd.to_datetime(scored.target, utc=True)
            - pd.to_timedelta(baseline_offset_hours(scored.lead_h), unit="h"))
    scored = scored.assign(base_key=back.dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
    o = obs.rename(columns={"time": "base_key", "t": "base_t", "w": "base_w", "p": "base_p"})
    o = o.drop_duplicates(["station", "base_key"], keep="last")
    scored = scored.drop(columns=["base_t", "base_w", "base_p"], errors="ignore").merge(
        o[["station", "base_key", "base_t", "base_w", "base_p"]], on=["station", "base_key"],
        how="left").drop(columns="base_key")
    # Rain is only scored on the short horizons; keep the baseline consistent with that.
    scored.loc[~scored.h.isin(PRECIP_HORIZONS), "base_p"] = np.nan
    return scored


def _provider(pending: pd.DataFrame, name: str, cols: list[str]) -> pd.DataFrame:
    df = pending[pending.provider == name]
    keep = ["station", "target", "fetched_at", "lead_h", "issued_at"] + cols
    df = df[keep].rename(columns={c: f"{name}_{c}" for c in cols + ["issued_at"]})
    return df.drop_duplicates(["station", "target", "fetched_at"])


def score_targets(pending: pd.DataFrame, obs: pd.DataFrame) -> pd.DataFrame:
    """Score every pending target that has an observation. Pure function.

    `obs` may include earlier days (see obs_window); they only feed the baseline.
    """
    if pending.empty:
        return pd.DataFrame(columns=SCORED_COLUMNS)
    from .config import PENDING_COLUMNS
    pending = pending.reindex(columns=PENDING_COLUMNS)
    for c in VALUE_COLUMNS + ["lead_h"]:
        pending[c] = pd.to_numeric(pending[c], errors="coerce")
    yr = _provider(pending, "yr", YR_COLS)
    wn = _provider(pending, "wn", WN_COLS)
    both = yr.merge(wn, on=["station", "target", "fetched_at"], how="outer", suffixes=("", "_wn"))
    both["lead_h"] = both["lead_h"].fillna(both.pop("lead_h_wn"))
    both["has_both"] = both["yr_t"].notna() & both["wn_t"].notna()
    both = both.rename(columns={"yr_issued_at": "yr_issued", "wn_issued_at": "wn_issued"})

    picks = []
    for h in HORIZONS:
        c = both[(both.lead_h - h).abs() <= HORIZON_TOLERANCE].copy()
        if c.empty:
            continue
        c["h"] = h
        c["dist"] = (c.lead_h - h).abs()
        c = c.sort_values(["station", "target", "has_both", "dist", "fetched_at"],
                          ascending=[True, True, False, True, False])
        c = c.drop_duplicates(["station", "target"], keep="first")
        if h not in PRECIP_HORIZONS:
            for col in [f"yr_{x}" for x in YR_COLS if x.startswith("p")] + \
                       [f"wn_{x}" for x in WN_COLS if x.startswith("p")]:
                c[col] = pd.NA
        picks.append(c)
    if not picks:
        return pd.DataFrame(columns=SCORED_COLUMNS)
    scored = pd.concat(picks, ignore_index=True)

    o = obs.rename(columns={"time": "target", "t": "obs_t", "w": "obs_w", "p": "obs_p"})
    o = o.drop_duplicates(["station", "target"], keep="last")
    scored = scored.merge(o[["station", "target", "obs_t", "obs_w", "obs_p"]],
                          on=["station", "target"], how="inner")
    scored = scored[scored[["obs_t", "obs_w", "obs_p"]].notna().any(axis=1)]
    scored = add_baseline(scored, obs)
    return scored.reindex(columns=SCORED_COLUMNS).sort_values(["target", "station", "h"]) \
                 .reset_index(drop=True)


def days_ready(now: datetime, first_fetch: str | None, done: list[str]) -> list[date]:
    """Complete UTC days after the first collection that are not yet scored."""
    if not first_fetch:
        return []
    start = datetime.fromisoformat(first_fetch.replace("Z", "+00:00")).date()
    last = (now - timedelta(hours=24 + FINALIZE_DELAY_HOURS)).date()
    out, d = [], start
    while d <= last:
        if d.isoformat() not in done:
            out.append(d)
        d += timedelta(days=1)
    return out


def day_slice(df: pd.DataFrame, column: str, day: date) -> pd.Series:
    return df[column].astype(str).str.startswith(day.isoformat())


def finalize(state, now: datetime | None = None, write=None) -> list[str]:
    """Score all ready days, write each once, then drop their working data."""
    from .store import scored_path, write_scored
    exists = (lambda d: scored_path(d).exists()) if write is None else (lambda d: False)
    write = write or write_scored
    now = now or datetime.now(timezone.utc)
    meta = state.meta()
    pending, obs = state.pending(), state.obs()
    written = []
    for day in days_ready(now, meta.get("first_fetch"), meta["finalized_days"]):
        p = pending[day_slice(pending, "target", day)]
        o = obs_window(obs, day)
        if not exists(day):  # e.g. already provided by the one-off migration
            write(day, score_targets(p, o))
        meta["finalized_days"].append(day.isoformat())
        written.append(day.isoformat())
        # Targets on or before this day are no longer needed.
        pending = pending[pending.target.astype(str) >= (day + timedelta(days=1)).isoformat()]
    if written:
        state.replace_pending(pending)
        cutoff = (now - timedelta(days=OBS_KEEP_DAYS)).strftime("%Y-%m-%d")
        state.replace_obs(obs[obs.time.astype(str) >= cutoff])
        state.save_meta(meta)
    return written
