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


# ---------------------------------------------------------------------------------------------
# Storm replays: what each service said before a notable event (PLAN_REPLAYS.md, step 2).
#
# Events are chosen from the MEASUREMENTS only, never from forecast errors, so the list is
# not tilted toward one service's misses. Each replay point reuses the scored history row for
# that horizon (same fetch and lead for both services); no new pairing.
# ---------------------------------------------------------------------------------------------

RAIN_DAY_MM = 20.0      # station-day total, all 24 hours measured
STRONG_WIND_MS = 15.0   # hourly mean wind
COLD_C = -5.0           # hourly temperature
EVENT_TYPES = {
    "rain": {"label": "Heavy rain", "var": "p", "unit": "mm"},
    "wind": {"label": "Strong wind", "var": "w", "unit": "m/s"},
    "cold": {"label": "Cold snap", "var": "t", "unit": "°C"},
}
KEEP_RECENT = 30
KEEP_TOP_PER_TYPE = 5


def _observations(scored: pd.DataFrame) -> pd.DataFrame:
    """One measured row per station and hour (identical across horizons)."""
    cols = ["station", "target", "obs_t", "obs_w", "obs_p"]
    o = scored.reindex(columns=cols).drop_duplicates(["station", "target"])
    o = o.assign(day=o.target.astype(str).str[:10])
    for c in cols[2:]:
        o[c] = pd.to_numeric(o[c], errors="coerce")
    return o


def find_events(scored: pd.DataFrame, offshore: set[str] = frozenset()) -> list[dict]:
    """Notable days per type, stations on the same UTC day grouped, most extreme first.

    Uses only `obs_*` columns, so changing any forecast never changes the list. Strong wind
    counts land stations only: at the offshore platforms 15 m/s is an ordinary day.
    """
    if scored.empty or "target" not in scored:
        return []
    o = _observations(scored)
    found: dict[tuple[str, str], list[dict]] = {}
    rain = o.groupby(["day", "station"]).obs_p.agg(["sum", "count"]).reset_index()
    for r in rain[(rain["count"] >= 24) & (rain["sum"] >= RAIN_DAY_MM)].itertuples():
        found.setdefault((r.day, "rain"), []).append({"station": r.station, "value": round(float(r.sum), 1)})
    for kind, col, test, pick in (("wind", "obs_w", lambda s: s >= STRONG_WIND_MS, "max"),
                                  ("cold", "obs_t", lambda s: s <= COLD_C, "min")):
        hit = o[test(o[col]) & ~(o.station.isin(offshore) if kind == "wind" else False)]
        for (day, station), g in hit.groupby(["day", "station"]):
            found.setdefault((day, kind), []).append(
                {"station": station, "value": round(float(getattr(g[col], pick)()), 1)})
    events = []
    for (day, kind), stations in found.items():
        extreme = (lambda s: s["value"]) if kind != "cold" else (lambda s: -s["value"])
        stations = sorted(stations, key=extreme, reverse=True)
        events.append({"id": f"{day}-{kind}", "day": day, "type": kind,
                       "label": EVENT_TYPES[kind]["label"], "unit": EVENT_TYPES[kind]["unit"],
                       "station": stations[0]["station"], "value": stations[0]["value"],
                       "stations": stations})
    return events


def select_events(events: list[dict]) -> list[dict]:
    """The most recent 30 plus the 5 most extreme of each type; newest first."""
    keep = {e["id"] for e in sorted(events, key=lambda e: e["day"], reverse=True)[:KEEP_RECENT]}
    for kind in EVENT_TYPES:
        same = [e for e in events if e["type"] == kind]
        sign = -1 if kind == "cold" else 1
        keep |= {e["id"] for e in sorted(same, key=lambda e: sign * e["value"], reverse=True)[:KEEP_TOP_PER_TYPE]}
    return sorted((e for e in events if e["id"] in keep), key=lambda e: (e["day"], e["id"]), reverse=True)


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce") if col in df else pd.Series(np.nan, index=df.index)


def replay(scored: pd.DataFrame, event: dict, publish_values: bool,
           cutoff: pd.Timestamp | None = None) -> dict:
    """The countdown for an event's headline station: each service's forecast per horizon.

    Rain: day total, i.e. the sum of the 24 hourly forecasts made H hours before each hour;
    a horizon is shown only when all 24 hours exist for both services. Wind and cold: the
    most extreme measured hour that has forecasts at the most horizons, so every horizon is
    compared on the same hour. WeatherNext values are included only when `publish_values`
    is set and the target is at least PUBLISH_MIN_AGE_H in the past (`cutoff`).
    """
    kind, var = event["type"], EVENT_TYPES[event["type"]]["var"]
    d = scored[(scored.station == event["station"])
               & (scored.target.astype(str).str[:10] == event["day"])].copy()
    d["h"] = pd.to_numeric(d["h"], errors="coerce")
    out = {k: event[k] for k in ("id", "day", "type", "label", "unit", "station", "value", "stations")}
    points = []
    if kind == "rain":
        out["what"] = "day total"
        for h in sorted(PRECIP_HORIZONS, reverse=True):
            g = d[d.h == h]
            yr, wn, wn50 = _num(g, "yr_p"), _num(g, "wn_p"), _num(g, "wn_p_p50")
            ok = yr.notna() & wn.notna()
            if g.target.nunique() == 24 and ok.sum() == 24:
                points.append({"h": int(h), "yr": _r(yr.sum(), 1), "wn": _r(wn.sum(), 1),
                               "wn50": _r(wn50.sum(), 1) if wn50.notna().sum() == 24 else None})
        out["observed"] = event["value"]
    else:
        obs = _num(d, f"obs_{var}")
        trigger = (obs >= STRONG_WIND_MS) if kind == "wind" else (obs <= COLD_C)
        cand = d[obs.notna()].assign(obs=obs, hit=trigger)
        both = cand[_num(cand, f"yr_{var}").notna() & _num(cand, f"wn_{var}").notna()]
        if len(both):
            # Hours that meet the event threshold first, then the most horizons, then the most extreme.
            per_hour = both.groupby("target").agg(hit=("hit", "first"), n=("h", "nunique"),
                                                  obs=("obs", "first")).reset_index()
            sign = -1 if kind == "cold" else 1
            per_hour = per_hour.sort_values(["hit", "n", "obs"], ascending=[False, False, sign < 0])
            hour = per_hour.iloc[0]
            out["what"] = f"at {str(hour.target)[11:16]} UTC"
            out["target"] = str(hour.target)
            out["observed"] = _r(hour.obs, 1)
            g = both[both.target == hour.target].drop_duplicates("h").sort_values("h", ascending=False)
            for r in g.itertuples():
                points.append({"h": int(r.h), "yr": _r(getattr(r, f"yr_{var}"), 1),
                               "wn": _r(getattr(r, f"wn_{var}"), 1)})
        else:
            out["observed"] = event["value"]
    last_target = pd.Timestamp(f"{event['day']}T23:00:00Z") if kind == "rain" else (
        pd.Timestamp(out["target"]) if "target" in out else pd.Timestamp(f"{event['day']}T23:00:00Z"))
    show_wn = publish_values and (cutoff is None or last_target <= cutoff)
    if not show_wn:
        for p in points:
            p.pop("wn", None)
            p.pop("wn50", None)
    out["wn_shown"] = bool(show_wn)
    out["points"] = points
    return out


def build_replays(scored: pd.DataFrame, publish_values: bool, now: pd.Timestamp | None = None,
                  offshore: set[str] = frozenset()) -> tuple[list[dict], dict[str, dict]]:
    """Index for events.json and one replay per event (events/<id>.json)."""
    from .config import PUBLISH_MIN_AGE_H
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    now = now.tz_localize("UTC") if now.tzinfo is None else now
    cutoff = now - pd.Timedelta(PUBLISH_MIN_AGE_H, unit="h")
    replays = {}
    for e in select_events(find_events(scored, offshore)):
        r = replay(scored, e, publish_values, cutoff)
        if r["points"]:
            replays[e["id"]] = r
    index = [{k: r[k] for k in ("id", "day", "type", "label", "unit", "station", "value")}
             | {"n_stations": len(r["stations"])} for r in replays.values()]
    return index, replays
