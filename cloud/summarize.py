"""Build the small JSON files the webpage reads from the scored history."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .config import (ATTRIBUTION, HORIZONS, PRECIP_HORIZONS, PROVIDERS, PUBLISH_FORECAST_VALUES,
                     PUBLISH_MIN_AGE_H, WN_VALUE_ATTRIBUTION,
                     SITE_DATA_DIR, VARIABLES, WET_THRESHOLD_MM, load_stations)
from .heights import adjusted_t, flags, load_heights

MIN_DAYS_FOR_VERDICT = 7
BOOTSTRAP = 2000


_TAG = re.compile(r"\s*\[SN\d+\]\s*$")
_ROAD = re.compile(r"(?:E|FV)\d+")
_KEEP_CAPS = {"II", "III", "FPSO", "A", "B"}
_SMALL = {"I", "OG"}


def display_name(raw):
    """Friendly station/county name: drop a trailing [SNnnnn] tag; title-case ALL-CAPS names."""
    if not raw:
        return raw
    name = _TAG.sub("", raw).strip()
    if name != name.upper():
        return name
    out = []
    for i, tok in enumerate(name.split(" ")):
        if _ROAD.fullmatch(tok) or tok in _KEEP_CAPS:
            out.append(tok)
        elif i and tok in _SMALL:
            out.append(tok.lower())
        else:
            out.append(tok.title())
    return " ".join(out)


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
    if f"wn_{var}_adj" in d:  # height-adjusted WeatherNext (temperature only; our adjustment)
        d["e_wnh"] = d[f"wn_{var}_adj"] - d[f"obs_{var}"]
    if var in ("t", "w"):  # Yr and WeatherNext averaged; not rain, where it spreads drizzle further
        d["e_avg"] = (d[f"yr_{var}"] + d[f"wn_{var}"]) / 2 - d[f"obs_{var}"]
    # Naive baseline; missing (NaN) on rows scored before it existed.
    d["e_base"] = (pd.to_numeric(d[f"base_{var}"], errors="coerce") - d[f"obs_{var}"]
                   if f"base_{var}" in d else np.nan)
    return d


def baseline(d: pd.DataFrame) -> dict | None:
    """Naive "same as before" error and skill = 1 - MAE_model / MAE_naive.

    Uses only rows that have a baseline, for the models too, so older rows
    without one are left out rather than counted as zero skill.
    """
    b = d[d["e_base"].notna()] if "e_base" in d else d.iloc[0:0]
    if not len(b):
        return None
    mae_base = b["e_base"].abs().mean()
    out = {"n": int(len(b)), "mae": _r(mae_base)}
    for p in ("yr", "wn", "wn50", "wnh"):
        if f"e_{p}" in b and b[f"e_{p}"].notna().any():
            mae = b[f"e_{p}"].abs().mean()
            out[f"mae_{p}"] = _r(mae)
            out[f"skill_{p}"] = _r(1 - mae / mae_base) if mae_base > 0 else None
    return out


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


def bootstrap_gain(d: pd.DataFrame, best: str, seed: int = 1) -> tuple[float | None, float | None]:
    """95% interval for 1 - MAE(average of both) / MAE(`best` service), resampling whole days."""
    per_day = d.groupby("day").agg(a_avg=("e_avg", lambda s: s.abs().sum()),
                                  a_best=(f"e_{best}", lambda s: s.abs().sum()))
    k = len(per_day)
    if k < MIN_DAYS_FOR_VERDICT:
        return None, None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, k, size=(BOOTSTRAP, k))
    gain = 1 - per_day.a_avg.to_numpy()[idx].sum(1) / per_day.a_best.to_numpy()[idx].sum(1)
    return float(np.percentile(gain, 2.5)), float(np.percentile(gain, 97.5))


def verdict(lo, hi) -> str:
    if lo is None:
        return "not_enough_data"
    if hi < 0:
        return "weathernext"
    if lo > 0:
        return "yr"
    return "too_close"


def stats(d: pd.DataFrame, with_ci: bool = True, with_base: bool = True,
          median_ci: bool = False) -> dict:
    """`median_ci` adds a diff and verdict for WeatherNext's median (rain headlines it)."""
    out = {"n": int(len(d)), "days": int(d.day.nunique()) if len(d) else 0}
    if not len(d):
        return out
    for p in ("yr", "wn", "wn50", "wnh", "avg"):
        if f"e_{p}" in d and d[f"e_{p}"].notna().any():
            out[f"mae_{p}"] = _r(d[f"e_{p}"].abs().mean())
            out[f"bias_{p}"] = _r(d[f"e_{p}"].mean())
    out["diff"] = _r(out["mae_wn"] - out["mae_yr"])
    if "mae_avg" in out:  # share by which the average beats the better single service
        best = "yr" if d.e_yr.abs().mean() <= d.e_wn.abs().mean() else "wn"
        if d[f"e_{best}"].abs().mean() > 0:
            out["avg_gain"] = _r(1 - d.e_avg.abs().mean() / d[f"e_{best}"].abs().mean())
            if with_ci:  # better/worse than the better single service, with the same day-block test
                lo, hi = bootstrap_gain(d, best)
                out.update(avg_gain_lo=_r(lo), avg_gain_hi=_r(hi),
                           verdict_avg="not_enough_data" if lo is None
                           else "better" if lo > 0 else "worse" if hi < 0 else "too_close")
    if "mae_wnh" in out:
        out["diff_h"] = _r(out["mae_wnh"] - out["mae_yr"])
    if with_ci:
        lo, hi = bootstrap_diff(d)
        out.update(ci_lo=_r(lo), ci_hi=_r(hi), verdict=verdict(lo, hi))
        if "mae_wnh" in out:  # a second verdict for the height-adjusted line; the first stays primary
            lo, hi = bootstrap_diff(d.assign(e_wn=d.e_wnh))
            out.update(ci_h_lo=_r(lo), ci_h_hi=_r(hi), verdict_h=verdict(lo, hi))
        if median_ci and d.get("e_wn50") is not None and d.e_wn50.notna().any():
            dm = d[d.e_wn50.notna()]  # like for like: only forecasts that have a median
            lo, hi = bootstrap_diff(dm.assign(e_wn=dm.e_wn50))
            out.update(diff_50=_r(dm.e_wn50.abs().mean() - dm.e_yr.abs().mean()),
                       ci_50_lo=_r(lo), ci_50_hi=_r(hi), verdict_50=verdict(lo, hi))
    if with_base and (b := baseline(d)):
        out["base"] = b
    return out


def events(d: pd.DataFrame) -> dict:
    """Wet-hour detection (> 0.1 mm/h): probability of detection, false alarms, CSI."""
    wet = d.obs_p > WET_THRESHOLD_MM
    out = {"wet_hours": int(wet.sum()), "dry_hours": int((~wet).sum())}
    # wn50 = WeatherNext's median: the headline rain value; wn = its average.
    for p, col in (("yr", "yr_p"), ("wn", "wn_p"), ("wn50", "wn_p_p50")):
        if col not in d:
            continue
        dd = d[d[col].notna()]  # a missing forecast must not count as "no rain"
        wet_p = dd.obs_p > WET_THRESHOLD_MM
        f = dd[col] > WET_THRESHOLD_MM
        hits, misses, fa = int((f & wet_p).sum()), int((~f & wet_p).sum()), int((f & ~wet_p).sum())
        out[p] = {"pod": _r(hits / (hits + misses)) if hits + misses else None,
                  "far": _r(fa / (hits + fa)) if hits + fa else None,
                  "csi": _r(hits / (hits + misses + fa)) if hits + misses + fa else None,
                  "wet_mae": _r(dd.loc[wet_p, f"e_{p}"].abs().mean()) if wet_p.any() else None}
    return out


QUANTILES = (0.1, 0.5, 0.9)


def quantile_columns(p: str, var: str) -> list[str]:
    """p10/p50/p90 columns. Yr has no p50, so its main value stands in for it."""
    mid = f"{p}_{var}_p50" if p == "wn" else f"{p}_{var}"
    return [f"{p}_{var}_p10", mid, f"{p}_{var}_p90"]


def pinball(obs: pd.Series, preds: list[pd.Series]) -> float:
    """Mean quantile (pinball) loss over the 10th, 50th and 90th percentiles.

    Lower is better. It rewards ranges that are both honest and narrow.
    """
    y = obs.to_numpy(float)
    losses = []
    for q, f in zip(QUANTILES, preds):
        u = y - f.to_numpy(float)
        losses.append(np.maximum(q * u, (q - 1) * u))
    return float(np.mean(losses))


def coverage(df: pd.DataFrame, var: str, h: int) -> dict:
    """How well each provider's 10th-90th range describes the uncertainty.

    `inside`: share of observations inside the range (ideal ~80%), per provider.
    `q`: pinball score and mean p10-p90 width, on rows where BOTH providers have
    all three quantiles, so the two are compared on the same forecasts.
    """
    d = df[df.h == h]
    out = {}
    o = pd.to_numeric(d[f"obs_{var}"], errors="coerce")
    for p in ("yr", "wn"):
        lo, hi = d.get(f"{p}_{var}_p10"), d.get(f"{p}_{var}_p90")
        if lo is None or hi is None:
            continue
        m = lo.notna() & hi.notna() & o.notna()
        if m.sum():
            out[p] = {"inside": _r(((o[m] >= lo[m]) & (o[m] <= hi[m])).mean()), "n": int(m.sum())}
    cols = {p: quantile_columns(p, var) for p in ("yr", "wn")}
    if all(c in d for cs in cols.values() for c in cs):
        num = d[[c for cs in cols.values() for c in cs]].apply(pd.to_numeric, errors="coerce")
        m = o.notna() & num.notna().all(axis=1)
        if m.sum():
            q = {"n": int(m.sum())}
            for p, cs in cols.items():
                q[p] = {"pinball": _r(pinball(o[m], [num.loc[m, c] for c in cs])),
                        "width": _r((num.loc[m, cs[2]] - num.loc[m, cs[0]]).mean())}
            out["q"] = q
    return out


SNOW_MAX_C = 0.0  # observed 2 m temperature at or below: snow
RAIN_MIN_C = 2.0  # at or above: rain; between the two: mixed


def phase(obs_t: pd.Series) -> pd.Series:
    """Precipitation phase from the observed 2 m temperature at the hour.

    A proxy, not a present-weather sensor. Gauges catch less snow than falls in wind,
    so snow hours are shown apart rather than corrected. Missing temperature: "unknown".
    """
    t = pd.to_numeric(obs_t, errors="coerce")
    out = pd.Series("mixed", index=t.index)
    out[t <= SNOW_MAX_C] = "snow"
    out[t >= RAIN_MIN_C] = "rain"
    return out.where(t.notna(), "unknown")


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
        wet = o > WET_THRESHOLD_MM
        ph = phase(d["obs_t"]) if "obs_t" in d else pd.Series("unknown", index=d.index)
        groups += [("Dry hours", o <= WET_THRESHOLD_MM), ("Wet hours", wet),
                   ("Wet, rain (2 °C and above)", wet & (ph == "rain")),
                   ("Wet, mixed (0 to 2 °C)", wet & (ph == "mixed")),
                   ("Wet, snow (0 °C and below)", wet & (ph == "snow")),
                   ("Heavy (> 2 mm/h)", o > 2)]
    elev = d.station.map(elevation)
    groups += [("Lowland (< 200 m)", elev < 200), ("Hills (200–600 m)", (elev >= 200) & (elev < 600)),
               ("Mountain (≥ 600 m)", elev >= 600)]
    out = []
    for label, mask in groups:
        s = stats(d[mask.fillna(False)], with_ci=False, with_base=False)
        s["label"] = label
        out.append(s)
    return out


HOUR_BLOCKS = (("Night (00–06)", 0), ("Morning (06–12)", 6), ("Day (12–18)", 12), ("Evening (18–24)", 18))


def bias_by_hour(d: pd.DataFrame) -> list[dict]:
    """Which way do they miss: signed error (bias) in 4 blocks of 6 h, Oslo local time."""
    hour = pd.to_datetime(d.target, utc=True).dt.tz_convert("Europe/Oslo").dt.hour
    out = []
    for label, lo in HOUR_BLOCKS:
        s = stats(d[(hour >= lo) & (hour < lo + 6)], with_ci=False, with_base=False)
        out.append({"label": label, **{k: s[k] for k in
                    ("n", "days", "bias_yr", "bias_wn", "bias_wn50", "bias_wnh") if k in s}})
    return out


def build(scored: pd.DataFrame, out_dir: Path = SITE_DATA_DIR, stations=None,
          publish_values: bool = PUBLISH_FORECAST_VALUES, heights: dict | None = None,
          now: pd.Timestamp | None = None) -> dict:
    out_dir = Path(out_dir)
    (out_dir / "recent").mkdir(parents=True, exist_ok=True)
    stations = stations or load_stations()
    heights = load_heights() if heights is None else heights
    station_flags = flags(heights)
    offshore = {sid for sid, h in heights.get("stations", {}).items() if h.get("offshore")}
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
    if "wn_t" in scored and heights.get("stations"):
        scored["wn_t_adj"] = adjusted_t(scored, heights)
    days = sorted(scored.target.astype(str).str[:10].unique())
    end_day = days[-1] if days else None
    start30 = (pd.Timestamp(end_day) - pd.Timedelta(days=29)).strftime("%Y-%m-%d") if end_day else None
    periods = {"all": {"start": days[0] if days else None, "end": end_day},
               "last30": {"start": start30, "end": end_day}}
    last30 = [day for day in days if day >= start30] if start30 else []

    board, trend, per_station, calib, patterns, rain, bias = {}, {}, {}, {}, {}, {}, {}
    for var in VARIABLES:
        hs = PRECIP_HORIZONS if var == "p" else HORIZONS
        board[var], trend[var], per_station[var], calib[var], patterns[var], bias[var] = {}, {}, {}, {}, {}, {}
        for h in hs:
            d = paired(scored[scored.h == h], var) if len(scored) else pd.DataFrame()
            if var == "p" and not d.empty and "e_wn50" in d:
                d = d[d.e_wn50.notna()]  # one shared cohort for the median headline and its mean alternative
            if d.empty:
                continue
            key = str(h)
            board[var][key] = {"all": stats(d, median_ci=var == "p"),
                               "last30": stats(d[d.day.isin(last30)], median_ci=var == "p")}
            t = d.groupby("day").agg(n=("e_yr", "size"), mae_yr=("e_yr", lambda s: s.abs().mean()),
                                     mae_wn=("e_wn", lambda s: s.abs().mean())).reset_index()
            trend[var][key] = [{"day": r.day, "n": int(r.n), "yr": _r(r.mae_yr), "wn": _r(r.mae_wn)}
                               for r in t.itertuples()]
            agg = dict(n=("e_yr", "size"), days=("day", "nunique"), yr=("e_yr", lambda s: s.abs().mean()),
                       wn=("e_wn", lambda s: s.abs().mean()))
            if "e_wnh" in d:
                agg["wnh"] = ("e_wnh", lambda s: s.abs().mean())
            st = d.groupby("station").agg(**agg).reset_index()
            per_station[var][key] = {r.station: {"n": int(r.n), "days": int(r.days), "yr": _r(r.yr), "wn": _r(r.wn),
                                                 **({"wnh": _r(r.wnh)} if "wnh" in agg else {})}
                                     for r in st.itertuples()}
            if var in ("t", "w"):
                calib[var][key] = coverage(scored[scored.h == h], var, h)
            patterns[var][key] = conditions(d, var, elevation)
            bias[var][key] = bias_by_hour(d)
            if var == "p":
                rain[key] = events(d)

    dump("leaderboard.json", board)
    dump("trend.json", trend)
    dump("stations.json", per_station)
    dump("calibration.json", calib)
    dump("patterns.json", patterns)
    dump("rain.json", rain)
    dump("bias.json", bias)

    from .views import build_views
    dump("views.json", build_views(scored, periods, elevation, offshore) if days else {})

    from .replay import steadiness
    dump("steadiness.json", {var: steadiness(scored, var) for var in VARIABLES})

    from .monthly import build_summary
    dump("summary.json", build_summary(scored, now))

    # WeatherNext values are published only for targets at least PUBLISH_MIN_AGE_H ago (CC BY
    # 4.0 historic data); scored days are always older, but the rule is enforced here anyway.
    now_ts = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    now_ts = now_ts.tz_localize("UTC") if now_ts.tzinfo is None else now_ts
    cutoff = now_ts - pd.Timedelta(PUBLISH_MIN_AGE_H, unit="h")

    from .replay import build_replays
    (out_dir / "events").mkdir(exist_ok=True)
    index, replays = build_replays(scored, publish_values, now_ts, offshore)
    dump("events.json", index)
    for eid, r in replays.items():
        (out_dir / "events" / f"{eid}.json").write_text(
            json.dumps(r, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Recent hourly series at the 24 h horizon for the "predicted vs actual" chart.
    start7 = (pd.Timestamp(end_day) - pd.Timedelta(days=6)).strftime("%Y-%m-%d") if end_day else ""
    recent = scored[(scored.h == 24) & (scored.target.astype(str).str[:10] >= start7)]
    for sid, g in recent.groupby("station"):
        g = g.sort_values("target")
        old_enough = pd.to_datetime(g.target, utc=True) <= cutoff
        series = {"time": g.target.tolist()}
        for var in ("t", "w", "p"):
            series[f"obs_{var}"] = [_r(x, 2) if pd.notna(x) else None for x in g[f"obs_{var}"]]
            series[f"yr_{var}"] = [_r(x, 2) if pd.notna(x) else None for x in g[f"yr_{var}"]]
            if publish_values:
                series[f"wn_{var}"] = [_r(x, 2) if pd.notna(x) and ok else None
                                       for x, ok in zip(g[f"wn_{var}"], old_enough)]
        if publish_values:
            series["wn_p_p50"] = [_r(x, 2) if pd.notna(x) and ok else None
                                   for x, ok in zip(g.get("wn_p_p50", pd.Series(np.nan, index=g.index)), old_enough)]
        (out_dir / "recent" / f"{sid}.json").write_text(json.dumps(series, separators=(",", ":")),
                                                         encoding="utf-8")

    # Latest hour with any measurement per station, so the page can flag stations that stopped reporting.
    obs_cols = [c for c in ("obs_t", "obs_w", "obs_p") if c in scored]
    measured = scored.dropna(subset=obs_cols, how="all") if obs_cols else scored.iloc[0:0]
    last_obs = measured.groupby("station").target.max().astype(str).to_dict() if len(measured) else {}

    meta = {
        "generated_at": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "first_day": days[0] if days else None, "last_day": days[-1] if days else None,
        "days": len(days), "rows": int(len(scored)),
        "periods": periods, "view_metrics": {"t": "mean", "w": "mean", "p": "median"},
        "horizons": HORIZONS, "precip_horizons": PRECIP_HORIZONS,
        "variables": VARIABLES, "providers": PROVIDERS,
        "publish_forecast_values": publish_values, "min_days_for_verdict": MIN_DAYS_FOR_VERDICT,
        "attribution": ATTRIBUTION,
        "wn_value_attribution": WN_VALUE_ATTRIBUTION,  # shown next to every chart with WeatherNext values
        "stations": [{"id": s["station_id"], "name": display_name(s.get("name") or s.get("station_name")),
                      "lat": s["latitude"], "lon": s["longitude"], "elev": s.get("elevation_m"),
                      "offshore": heights.get("stations", {}).get(s["station_id"], {}).get("offshore"),
                      "county": display_name(s.get("county")), "last_obs": last_obs.get(s["station_id"]),
                      **({"flag": station_flags[s["station_id"]]} if s["station_id"] in station_flags else {})}
                     for s in stations],
    }
    dump("meta.json", meta)
    return files
