"""Month-by-month summary paragraphs for the webpage (`site/data/summary.json`).

Each calendar month (UTC, by target day) is scored with the same pairing, bootstrap
verdicts and 7-day minimum as the rest of the page (`summarize.stats`). The text is
built from fixed sentence templates: no free-written text, no forecast values, and a
winner is named only where the verdict says so.
"""
from __future__ import annotations

import pandas as pd

from .config import PRECIP_HORIZONS
from .summarize import paired, stats

SUMMARY_HORIZONS = [6, 24, 48, 72, 120]  # 6 h, 1, 2, 3 and 5 days
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]
HORIZON_LABEL = {6: "6 hours", 24: "1 day", 48: "2 days", 72: "3 days", 120: "5 days"}
VAR_NAME = {"t": "temperature", "w": "wind"}
WINNER = {"yr": "Yr", "weathernext": "WeatherNext"}
NO_WINNER = {"too_close": "too close to call", "not_enough_data": "not enough days yet"}
NOT_ENOUGH = "not_enough_data"


def _spans(subset: list[int], all_h: list[int]) -> list[list[int]]:
    """Split horizons into runs that are neighbours in the horizon list."""
    runs: list[list[int]] = []
    last = None
    for i in sorted(all_h.index(h) for h in subset):
        if runs and i == last + 1:
            runs[-1].append(all_h[i])
        else:
            runs.append([all_h[i]])
        last = i
    return runs


def horizon_phrase(subset: list[int], all_h: list[int]) -> str:
    """Group horizons: "6 hours out", "1–2 days out", "1 day and 3 days out", "from 3 days",
    "at all horizons". Neighbouring horizons form one range; a range that reaches the
    last horizon reads "from …"."""
    parts = []
    for run in _spans(subset, all_h):
        if len(run) == len(all_h):
            return "at all horizons"
        if len(run) == 1:
            parts.append(HORIZON_LABEL[run[0]])
        elif run[-1] == all_h[-1]:
            parts.append(f"from {HORIZON_LABEL[run[0]]}")
        elif run[0] < 24:
            parts.append(f"{HORIZON_LABEL[run[0]]} to {HORIZON_LABEL[run[-1]]}")
        else:
            parts.append(f"{run[0] // 24}–{HORIZON_LABEL[run[-1]]}")
    if not any(p.startswith("from ") for p in parts):
        return " and ".join(parts) + " out"
    return " and ".join(p if p.startswith("from ") else p + " out" for p in parts)


def at(phrase: str) -> str:
    """"1 day out" -> "at 1 day out", so a bare "too close to call" reads properly."""
    return f"at {phrase}" if phrase[0].isdigit() else phrase


def _group(verdicts: dict[int, str]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for h, v in verdicts.items():
        out.setdefault(v, []).append(h)
    return out


def _temperature_wind(v: dict) -> list[str]:
    """Winners first, then "too close to call", then "not enough days yet"."""
    groups = {var: _group(v[var]) for var in VAR_NAME}
    all_h = {var: list(v[var]) for var in VAR_NAME}
    wins = []
    for order, var in enumerate(VAR_NAME):
        for verdict, hs in groups[var].items():
            if verdict in WINNER:
                wins.append((WINNER[verdict], order, min(hs),
                             f"{WINNER[verdict]} ahead on {VAR_NAME[var]} {horizon_phrase(hs, all_h[var])}"))
    clauses = [c for *_, c in sorted(wins)]
    for verdict, label in NO_WINNER.items():
        t, w = groups["t"].get(verdict), groups["w"].get(verdict)
        if t and w and t == w:  # same horizons for both: no need to name the variable
            clauses.append(f"{label} {at(horizon_phrase(t, all_h['t']))}")
        else:
            clauses += [f"{label} on {VAR_NAME[var]} {at(horizon_phrase(hs, all_h[var]))}"
                        for var, hs in (("t", t), ("w", w)) if hs]
    # Height-adjusted WeatherNext: one clause, and only where its verdict differs.
    differs = {h: a for h, a in v.get("t_adj", {}).items() if a is not None and a != v["t"].get(h)}
    if differs:
        bits = []
        for verdict, hs in _group(differs).items():
            what = f"{WINNER[verdict]} ahead" if verdict in WINNER else NO_WINNER[verdict]
            phrase = horizon_phrase(hs, all_h["t"])
            bits.append(f"{what} {at(phrase) if verdict in NO_WINNER else phrase}")
        clauses.append("height-adjusted temperature differs: " + ", ".join(bits))
    return clauses


RAIN_LENS = {  # mean = WeatherNext's average, median = WeatherNext's median
    "mean": {"yr": "Yr ahead on average error", "weathernext": "WeatherNext ahead on average error",
             "too_close": "too close to call on average error",
             NOT_ENOUGH: "not enough days yet on average error"},
    "median": {"yr": "Yr ahead of WeatherNext's median", "weathernext": "WeatherNext's median ahead",
               "too_close": "WeatherNext's median too close to call",
               NOT_ENOUGH: "not enough days yet for WeatherNext's median"},
}


def _rain(v: dict[int, dict[str, str]]) -> str:
    all_h = list(v)
    if all(x == NOT_ENOUGH for lens in v.values() for x in lens.values()):
        return "not enough days yet"
    parts = []
    for lens in ("mean", "median"):
        groups = _group({h: v[h][lens] for h in all_h})
        for verdict, hs in sorted(groups.items(), key=lambda kv: min(kv[1])):
            phrase = horizon_phrase(hs, all_h)
            where = "" if len(groups) == 1 else " " + (at(phrase) if verdict in NO_WINNER else phrase)
            parts.append(RAIN_LENS[lens][verdict] + where)
    return "; ".join(parts)


def day_range(first: str, last: str) -> str:
    a, b = int(first[8:10]), int(last[8:10])
    return str(a) if a == b else f"{a}–{b}"


def describe(label: str, in_progress: bool, first_day: str, last_day: str, days: int,
             verdicts: dict) -> str:
    """The month's paragraph. `verdicts` is what `month_verdicts` returns."""
    head = (f"{label}{' so far' if in_progress else ''} "
            f"({day_range(first_day, last_day)}, {days} day{'' if days == 1 else 's'})")
    return f"{head}: {'; '.join(_temperature_wind(verdicts))}. Rain: {_rain(verdicts['p'])}."


def month_verdicts(df: pd.DataFrame) -> dict:
    """Bootstrap verdict per variable and horizon for one month of scored rows.

    Temperature and wind: verdicts for as-published WeatherNext; `t_adj` holds the
    height-adjusted one. Rain: verdicts for WeatherNext's average and its median.
    """
    v: dict = {"t": {}, "w": {}, "p": {}, "t_adj": {}}
    for var in ("t", "w", "p"):
        need = [f"obs_{var}", f"yr_{var}", f"wn_{var}"]
        for h in SUMMARY_HORIZONS:
            if var == "p" and h not in PRECIP_HORIZONS:
                continue
            d = paired(df[df.h == h], var) if len(df) and all(c in df for c in need) else pd.DataFrame()
            s = stats(d, with_base=False, median_ci=var == "p") if len(d) else {}
            if var == "p":
                v["p"][h] = {"mean": s.get("verdict", NOT_ENOUGH), "median": s.get("verdict_50", NOT_ENOUGH)}
            else:
                v[var][h] = s.get("verdict", NOT_ENOUGH)
                if var == "t" and "verdict_h" in s:
                    v["t_adj"][h] = s["verdict_h"]
    return v


def build_summary(scored: pd.DataFrame, now: pd.Timestamp | None = None) -> dict:
    """This month so far plus every completed month, newest first. Verdicts and text only."""
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    this_month = f"{now:%Y-%m}"
    months = []
    if len(scored) and "target" in scored:
        target = scored.target.astype(str)
        for key in sorted(target.str[:7].unique(), reverse=True):
            if key > this_month:  # nothing is scored for the future
                continue
            in_month = target.str[:7] == key
            df = scored[in_month]
            days = sorted(target[in_month].str[:10].unique())
            verdicts = month_verdicts(df)
            in_progress = key == this_month
            label = MONTH_NAMES[int(key[5:7]) - 1]
            months.append({
                "month": key, "label": label, "in_progress": in_progress,
                "first_day": days[0], "last_day": days[-1], "days": len(days),
                "text": describe(label, in_progress, days[0], days[-1], len(days), verdicts),
                "verdicts": {k: {str(h): x for h, x in val.items()} for k, val in verdicts.items()},
            })
    return {"as_of": f"{now:%Y-%m-%d}", "horizons": SUMMARY_HORIZONS, "months": months}
