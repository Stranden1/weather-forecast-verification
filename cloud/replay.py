"""How forecasts for the same moment change as it gets closer (see PLAN_REPLAYS.md).

Everything here reads the scored history only. Each history row already holds
Yr and WeatherNext from the same fetch at one horizon, so following one
station/target across horizons shows how each service revised its forecast.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import HORIZONS, PRECIP_HORIZONS
from .summarize import _r, bootstrap_diff, verdict

# A revision at least this large counts when asking "did it move toward the truth?".
MIN_REVISION = {"t": 0.2, "w": 0.5, "p": 0.1}
# Two consecutive revisions in opposite directions, each at least this large, is a flip-flop.
FLIP_SIZE = {"t": 1.0, "w": 2.0, "p": 0.5}
PROVIDERS = ("yr", "wn")


def _wide(scored: pd.DataFrame, var: str) -> pd.DataFrame:
    """One row per station/target; columns (field, horizon) for both providers."""
    hs = PRECIP_HORIZONS if var == "p" else HORIZONS
    cols = [f"obs_{var}", f"yr_{var}", f"wn_{var}"]
    d = scored[scored.h.isin(hs)].dropna(subset=cols)
    if d.empty:
        return pd.DataFrame()
    d = d.drop_duplicates(["station", "target", "h"])
    fields = {"obs": f"obs_{var}", "yr": f"yr_{var}", "wn": f"wn_{var}",
              "yr_iss": "yr_issued", "wn_iss": "wn_issued"}
    w = d.set_index(["station", "target", "h"]).reindex(columns=list(fields.values()))
    w.columns = list(fields)
    return w.unstack("h")


def _step(w: pd.DataFrame, var: str, long_h: int, short_h: int) -> tuple[pd.DataFrame, int]:
    """Revisions from `long_h` to `short_h` where both services issued a new forecast.

    Returns the usable rows and how many were left out because a service's issue
    time had not changed (a repeat of the same forecast, not a revision). An
    unknown issue time counts as a new forecast.
    """
    need = [(f, h) for f in ("obs", "yr", "wn") for h in (long_h, short_h)]
    if not all(c in w.columns for c in need):
        return pd.DataFrame(), 0
    x = w.dropna(subset=need)
    new = pd.Series(True, index=x.index)
    for p in PROVIDERS:
        a, b = x[(f"{p}_iss", long_h)], x[(f"{p}_iss", short_h)]
        new &= ~(a.notna() & (a.astype(str) == b.astype(str)))
    x = x[new]
    obs = x[("obs", short_h)]
    out = pd.DataFrame({"day": x.index.get_level_values("target").astype(str).str[:10]},
                       index=x.index)
    for p in PROVIDERS:
        out[f"r_{p}"] = x[(p, short_h)] - x[(p, long_h)]
        out[f"el_{p}"] = (x[(p, long_h)] - obs).abs()
        out[f"es_{p}"] = (x[(p, short_h)] - obs).abs()
    return out, int((~new).sum())


def _step_stats(s: pd.DataFrame, var: str) -> dict:
    out = {"n": int(len(s)), "days": int(s.day.nunique())}
    for p in PROVIDERS:
        moved = s[s[f"r_{p}"].abs() >= MIN_REVISION[var]]
        out[p] = {"rev": _r(s[f"r_{p}"].abs().mean()), "moved": int(len(moved)),
                  "toward": _r((moved[f"es_{p}"] < moved[f"el_{p}"]).mean()) if len(moved) else None}
    out["diff"] = _r(out["wn"]["rev"] - out["yr"]["rev"])
    # Same day-block bootstrap as the accuracy verdict, on revision size.
    lo, hi = bootstrap_diff(s.assign(e_yr=s.r_yr, e_wn=s.r_wn))
    out.update(ci_lo=_r(lo), ci_hi=_r(hi), steadier=verdict(lo, hi))
    return out


def _flips(w: pd.DataFrame, var: str, hs: list[int]) -> dict:
    """Share of forecasts (per 100) that flip-flopped at least once.

    Uses every run of three consecutive horizons where both services issued new
    forecasts at each step, on the same targets for both services.
    """
    size = FLIP_SIZE[var]
    flipped = {p: pd.Series(False, index=w.index) for p in PROVIDERS}
    seen = pd.Series(False, index=w.index)
    for a, b, c in zip(hs, hs[1:], hs[2:]):
        s1, _ = _step(w, var, a, b)
        s2, _ = _step(w, var, b, c)
        both = s1.index.intersection(s2.index)
        if not len(both):
            continue
        seen.loc[both] = True
        for p in PROVIDERS:
            r1, r2 = s1.loc[both, f"r_{p}"], s2.loc[both, f"r_{p}"]
            f = (r1 * r2 < 0) & (r1.abs() >= size) & (r2.abs() >= size)
            flipped[p].loc[both] |= f
    n = int(seen.sum())
    out = {"n": n, "size": size}
    for p in PROVIDERS:
        out[p] = _r(100 * flipped[p][seen].mean(), 1) if n else None
    return out


def steadiness(scored: pd.DataFrame, var: str) -> dict:
    """Revision size, "moved toward the truth" and flip-flops for one variable."""
    if scored.empty or "h" not in scored:
        return {"steps": [], "flip": {"n": 0}}
    scored = scored.assign(h=pd.to_numeric(scored["h"], errors="coerce"))
    w = _wide(scored, var)
    if w.empty:
        return {"steps": [], "flip": {"n": 0}}
    hs = sorted({h for h in w.columns.get_level_values("h")}, reverse=True)
    steps = []
    for long_h, short_h in zip(hs, hs[1:]):
        s, same = _step(w, var, long_h, short_h)
        if s.empty:
            continue
        st = {"from": int(long_h), "to": int(short_h), "same_issue": same}
        st.update(_step_stats(s, var))
        steps.append(st)
    return {"steps": steps, "flip": _flips(w, var, hs)}
