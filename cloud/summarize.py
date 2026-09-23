"""Build the small JSON files the webpage reads from the scored history."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import (ATTRIBUTION, HORIZONS, PRECIP_HORIZONS, PROVIDERS, PUBLISH_FORECAST_VALUES,
                     SITE_DATA_DIR, VARIABLES, WET_THRESHOLD_MM, load_stations)

MIN_DAYS_FOR_VERDICT = 7
BOOTSTRAP = 2000


def _r(x, n=3):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def paired(df: pd.DataFrame, var: str) -> pd.DataFrame:
    """Rows where the observation and BOTH providers exist for this variable."""
    cols = [f"obs_{var}", f"yr_{var}", f"wn_{var}"]
    d = df.dropna(subset=cols).copy()
    d["day"] = d.target.astype(str).str[:10]
    d["e_yr"] = d[f"yr_{var}"] - d[f"obs_{var}"]
    d["e_wn"] = d[f"wn_{var}"] - d[f"obs_{var}"]
    if f"wn_{var}_p50" in d:
        d["e_wn50"] = d[f"wn_{var}_p50"] - d[f"obs_{var}"]
    return d


def bootstrap_diff(d: pd.DataFrame, seed: int = 1) -> tuple[float | None, float | None]:
    """95% interval for MAE(WeatherNext) - MAE(Yr), resampling whole days.

    Errors on the same day are strongly correlated across stations and hours, so
    days (not individual rows) are the independent unit.
    """
    per_day = d.groupby("day").agg(n=("e_yr", "size"),
                                  a_yr=("e_yr", lambda s: s.abs().sum()),
                                  a_wn=("e_wn", lambda s: s.abs().sum()))
    k = len(per_day)
    if k < MIN_DAYS_FOR_VERDICT:
        return None, None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, k, size=(BOOTSTRAP, k))
    n = per_day.n.to_numpy()[idx].sum(1)
    diff = (per_day.a_wn.to_numpy()[idx].sum(1) - per_day.a_yr.to_numpy()[idx].sum(1)) / n
    return float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))


def verdict(lo, hi) -> str:
    if lo is None:
        return "not_enough_data"
    if hi < 0:
        return "weathernext"
    if lo > 0:
        return "yr"
    return "too_close"


def stats(d: pd.DataFrame, with_ci: bool = True) -> dict:
    out = {"n": int(len(d)), "days": int(d.day.nunique()) if len(d) else 0}
    if not len(d):
        return out
    for p in ("yr", "wn", "wn50"):
        if f"e_{p}" in d and d[f"e_{p}"].notna().any():
            out[f"mae_{p}"] = _r(d[f"e_{p}"].abs().mean())
            out[f"bias_{p}"] = _r(d[f"e_{p}"].mean())
    out["diff"] = _r(out["mae_wn"] - out["mae_yr"])
    if with_ci:
        lo, hi = bootstrap_diff(d)
        out.update(ci_lo=_r(lo), ci_hi=_r(hi), verdict=verdict(lo, hi))
    return out


def events(d: pd.DataFrame) -> dict:
    """Wet-hour detection (> 0.1 mm/h): probability of detection, false alarms, CSI."""
    wet = d.obs_p > WET_THRESHOLD_MM
    out = {"wet_hours": int(wet.sum()), "dry_hours": int((~wet).sum())}
    for p in ("yr", "wn"):
        f = d[f"{p}_p"] > WET_THRESHOLD_MM
        hits, misses, fa = int((f & wet).sum()), int((~f & wet).sum()), int((f & ~wet).sum())
        out[p] = {"pod": _r(hits / (hits + misses)) if hits + misses else None,
                  "far": _r(fa / (hits + fa)) if hits + fa else None,
                  "csi": _r(hits / (hits + misses + fa)) if hits + misses + fa else None,
                  "wet_mae": _r(d.loc[wet, f"e_{p}"].abs().mean()) if wet.any() else None}
    return out


def coverage(df: pd.DataFrame, var: str, h: int) -> dict:
    """How often the observation fell inside each provider's 10th-90th range (ideal ~80%)."""
    d = df[df.h == h]
    out = {}
    for p in ("yr", "wn"):
        lo, hi, o = d.get(f"{p}_{var}_p10"), d.get(f"{p}_{var}_p90"), d[f"obs_{var}"]
        if lo is None or hi is None:
            continue
        m = lo.notna() & hi.notna() & o.notna()
        if m.sum():
            out[p] = {"inside": _r(((o[m] >= lo[m]) & (o[m] <= hi[m])).mean()), "n": int(m.sum())}
    return out


def conditions(d: pd.DataFrame, var: str, elevation: dict) -> list[dict]:
    """Patterns to watch: how errors change with weather type and terrain."""
    groups = []
    o = d[f"obs_{var}"]
    if var == "t":
        groups += [("Below freezing", o < 0), ("0 to 15 °C", (o >= 0) & (o < 15)), ("15 °C and above", o >= 15)]
    elif var == "w":
        groups += [("Light (< 5 m/s)", o < 5), ("Moderate (5–10 m/s)", (o >= 5) & (o < 10)),
                   ("Strong (≥ 10 m/s)", o >= 10)]
    else:
        groups += [("Dry hours", o <= WET_THRESHOLD_MM), ("Wet hours", o > WET_THRESHOLD_MM),
                   ("Heavy (> 2 mm/h)", o > 2)]
    elev = d.station.map(elevation)
    groups += [("Lowland (< 200 m)", elev < 200), ("Hills (200–600 m)", (elev >= 200) & (elev < 600)),
               ("Mountain (≥ 600 m)", elev >= 600)]
    out = []
    for label, mask in groups:
        s = stats(d[mask.fillna(False)], with_ci=False)
        s["label"] = label
        out.append(s)
    return out


def build(scored: pd.DataFrame, out_dir: Path = SITE_DATA_DIR, stations=None,
          publish_values: bool = PUBLISH_FORECAST_VALUES) -> dict:
    out_dir = Path(out_dir)
    (out_dir / "recent").mkdir(parents=True, exist_ok=True)
    stations = stations or load_stations()
    elevation = {s["station_id"]: s.get("elevation_m") for s in stations}
    files = {}

    def dump(name, obj):
        (out_dir / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
                                    encoding="utf-8")
        files[name] = True

    if scored.empty:
        scored = pd.DataFrame(columns=["target", "station", "h"])
    scored = scored.copy()
    scored["h"] = pd.to_numeric(scored["h"], errors="coerce")
    days = sorted(scored.target.astype(str).str[:10].unique())
    last30 = days[-30:]

    board, trend, per_station, calib, patterns, rain = {}, {}, {}, {}, {}, {}
    for var in VARIABLES:
        hs = PRECIP_HORIZONS if var == "p" else HORIZONS
        board[var], trend[var], per_station[var], calib[var], patterns[var] = {}, {}, {}, {}, {}
        for h in hs:
            d = paired(scored[scored.h == h], var) if len(scored) else pd.DataFrame()
            if d.empty:
                continue
            key = str(h)
            board[var][key] = {"all": stats(d), "last30": stats(d[d.day.isin(last30)])}
            t = d.groupby("day").agg(n=("e_yr", "size"), mae_yr=("e_yr", lambda s: s.abs().mean()),
                                     mae_wn=("e_wn", lambda s: s.abs().mean())).reset_index()
            trend[var][key] = [{"day": r.day, "n": int(r.n), "yr": _r(r.mae_yr), "wn": _r(r.mae_wn)}
                               for r in t.itertuples()]
            st = d.groupby("station").agg(n=("e_yr", "size"), yr=("e_yr", lambda s: s.abs().mean()),
                                          wn=("e_wn", lambda s: s.abs().mean())).reset_index()
            per_station[var][key] = {r.station: {"n": int(r.n), "yr": _r(r.yr), "wn": _r(r.wn)}
                                     for r in st.itertuples()}
            if var in ("t", "w"):
                calib[var][key] = coverage(scored[scored.h == h], var, h)
            patterns[var][key] = conditions(d, var, elevation)
            if var == "p":
                rain[key] = events(d)

    dump("leaderboard.json", board)
    dump("trend.json", trend)
    dump("stations.json", per_station)
    dump("calibration.json", calib)
    dump("patterns.json", patterns)
    dump("rain.json", rain)

    # Recent hourly series at the 24 h horizon for the "predicted vs actual" chart.
    recent = scored[(scored.h == 24) & scored.target.astype(str).str[:10].isin(days[-7:])]
    for sid, g in recent.groupby("station"):
        g = g.sort_values("target")
        series = {"time": g.target.tolist()}
        for var in ("t", "w", "p"):
            series[f"obs_{var}"] = [_r(x, 2) if pd.notna(x) else None for x in g[f"obs_{var}"]]
            series[f"yr_{var}"] = [_r(x, 2) if pd.notna(x) else None for x in g[f"yr_{var}"]]
            if publish_values:
                series[f"wn_{var}"] = [_r(x, 2) if pd.notna(x) else None for x in g[f"wn_{var}"]]
        (out_dir / "recent" / f"{sid}.json").write_text(json.dumps(series, separators=(",", ":")),
                                                         encoding="utf-8")

    meta = {
        "generated_at": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "first_day": days[0] if days else None, "last_day": days[-1] if days else None,
        "days": len(days), "rows": int(len(scored)),
        "horizons": HORIZONS, "precip_horizons": PRECIP_HORIZONS,
        "variables": VARIABLES, "providers": PROVIDERS,
        "publish_forecast_values": publish_values, "min_days_for_verdict": MIN_DAYS_FOR_VERDICT,
        "attribution": ATTRIBUTION,
        "stations": [{"id": s["station_id"], "name": s.get("name") or s.get("station_name"),
                      "lat": s["latitude"], "lon": s["longitude"], "elev": s.get("elevation_m"),
                      "county": s.get("county")} for s in stations],
    }
    dump("meta.json", meta)
    return files
