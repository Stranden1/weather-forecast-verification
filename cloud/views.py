"""Period-scoped page views, calculated from immutable history without changing scoring."""
from __future__ import annotations

import pandas as pd

from .config import HORIZONS, PRECIP_HORIZONS, VARIABLES
from .summarize import _r, paired, coverage, conditions, bias_by_hour, events


def primary_pairs(scored: pd.DataFrame, var: str) -> pd.DataFrame:
    """Shared point-error cohort; rain uses the median with no mean fallback."""
    d = paired(scored, var)
    if var == "p":
        if "e_wn50" not in d:
            return d.iloc[0:0]
        d = d[d.e_wn50.notna()].copy()
        d["e_wn"] = d.e_wn50
    return d


def build_views(scored: pd.DataFrame, periods: dict, elevation: dict) -> dict:
    from .replay import steadiness
    views = {}
    for period, dates in periods.items():
        scope = scored[scored.target.astype(str).str[:10].between(dates["start"], dates["end"])]
        view = {name: {} for name in ("stations", "trend", "patterns", "bias", "calibration", "rain", "steadiness")}
        for var in VARIABLES:
            for name in ("stations", "trend", "patterns", "bias", "calibration"):
                view[name][var] = {}
            for h in PRECIP_HORIZONS if var == "p" else HORIZONS:
                raw = scope[scope.h == h]
                d = primary_pairs(raw, var)
                if d.empty:
                    continue
                key = str(h)
                agg = dict(n=("e_yr", "size"), days=("day", "nunique"),
                           yr=("e_yr", lambda s: s.abs().mean()), wn=("e_wn", lambda s: s.abs().mean()))
                if "e_wnh" in d:
                    agg["wnh"] = ("e_wnh", lambda s: s.abs().mean())
                st = d.groupby("station").agg(**agg)
                view["stations"][var][key] = {
                    sid: {"n": int(r.n), "days": int(r.days), "yr": _r(r.yr), "wn": _r(r.wn),
                          **({"wnh": _r(r.wnh)} if "wnh" in agg else {})} for sid, r in st.iterrows()}
                t = d.groupby("day").agg(n=("e_yr", "size"), yr=("e_yr", lambda s: s.abs().mean()),
                                         wn=("e_wn", lambda s: s.abs().mean()))
                view["trend"][var][key] = [{"day": day, "n": int(r.n), "yr": _r(r.yr), "wn": _r(r.wn)}
                                           for day, r in t.iterrows()]
                view["patterns"][var][key] = conditions(d, var, elevation)
                view["bias"][var][key] = bias_by_hour(d)
                if var in ("t", "w"):
                    # Inside-range rates, scores and widths all use the same provider cohort.
                    cols = [f"obs_{var}", f"yr_{var}", f"yr_{var}_p10", f"yr_{var}_p90",
                            f"wn_{var}_p10", f"wn_{var}_p50", f"wn_{var}_p90"]
                    common = raw.reindex(columns=list(dict.fromkeys([*raw.columns, *cols]))).dropna(subset=cols)
                    view["calibration"][var][key] = coverage(common, var, h)
                else:
                    view["rain"][key] = events(d.assign(e_wn=d.wn_p - d.obs_p))
            revisions = scope
            if var == "p":
                revisions = scope.assign(wn_p=scope.get("wn_p_p50"))
            view["steadiness"][var] = steadiness(revisions, var)
        views[period] = view
    return views
