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
TOO_CLOSE = "too_close"


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


def _clauses(groups: dict[str, list[int]], all_h: list[int], words: dict[str, str]) -> list[str]:
    """Winners first (by their shortest horizon), then "too close to call".

    `words` maps a verdict to its wording; "not enough days yet" is left out here
    because it goes in the month's final line.
    """
    wins = sorted((min(hs), f"{words[v]} {horizon_phrase(hs, all_h)}")
                  for v, hs in groups.items() if v in WINNER)
    out = [c for _, c in wins]
    if TOO_CLOSE in groups:
        out.append(f"{words[TOO_CLOSE]} {at(horizon_phrase(groups[TOO_CLOSE], all_h))}")
    return out


def _variable_line(v: dict, var: str) -> str | None:
    """"Temperature: Yr ahead 6 hours out; too close to call at 1 day out." or None."""
    all_h = list(v[var])
    words = {"yr": "Yr ahead", "weathernext": "WeatherNext ahead", TOO_CLOSE: "too close to call"}
    clauses = _clauses(_group(v[var]), all_h, words)
    if not clauses:
        return None
    line = f"{VAR_NAME[var].capitalize()}: {'; '.join(clauses)}."
    if var == "t":  # height-adjusted WeatherNext: a short second sentence, only where it differs
        differs = {h: a for h, a in v.get("t_adj", {}).items()
                   if a not in (None, NOT_ENOUGH) and a != v["t"].get(h)}
        if differs:
            line += f" Height-adjusted: {'; '.join(_clauses(_group(differs), all_h, words))}."
    return line


# Rain leads with WeatherNext's median; its average comes second.
RAIN_MEDIAN = {"weathernext": "ahead", "yr": "behind Yr", TOO_CLOSE: "too close to call"}
RAIN_MEAN = {"yr": "Yr beats WeatherNext's average", "weathernext": "WeatherNext's average beats Yr",
             TOO_CLOSE: "too close to call against WeatherNext's average"}


def _rain_line(v: dict[int, dict[str, str]]) -> str | None:
    all_h = list(v)
    parts = []
    median = _clauses(_group({h: v[h]["median"] for h in all_h}), all_h, RAIN_MEDIAN)
    if median:
        parts.append("WeatherNext's median " + ", ".join(median))
    mean = _group({h: v[h]["mean"] for h in all_h})
    decided = [x for x in mean if x != NOT_ENOUGH]
    if len(decided) == 1 and NOT_ENOUGH not in mean:  # one verdict everywhere: no horizons needed
        parts.append(RAIN_MEAN[decided[0]])
    else:
        parts += _clauses(mean, all_h, RAIN_MEAN)
    return f"Rain: {'; '.join(parts)}." if parts else None


def _not_enough_line(v: dict) -> str | None:
    """All "not enough days yet" horizons in one line, naming variables only if they differ."""
    per_var = {"temperature": [h for h, x in v["t"].items() if x == NOT_ENOUGH],
               "wind": [h for h, x in v["w"].items() if x == NOT_ENOUGH],
               "rain": [h for h, x in v["p"].items() if NOT_ENOUGH in x.values()]}
    all_h = {"temperature": list(v["t"]), "wind": list(v["w"]), "rain": list(v["p"])}
    phrases = {k: at(horizon_phrase(hs, all_h[k])) for k, hs in per_var.items() if hs}
    if not phrases:
        return None
    if len(set(phrases.values())) == 1 and len(phrases) == len(per_var):
        return f"Not enough days yet {next(iter(phrases.values()))}."
    if set(phrases) <= {"temperature", "wind"} and len(set(phrases.values())) == 1 \
            and per_var["temperature"] == per_var["wind"]:
        return f"Not enough days yet {phrases['temperature']}."
    return "Not enough days yet: " + "; ".join(f"{k} {p}" for k, p in phrases.items()) + "."


def day_range(first: str, last: str) -> str:
    """"5–27 Sep", or "5 Sep" for a single day."""
    a, b = int(first[8:10]), int(last[8:10])
    mon = MONTH_NAMES[int(last[5:7]) - 1][:3]
    return f"{a} {mon}" if a == b else f"{a}–{b} {mon}"


def compared_phrase(first_day: str, compared: list[str]) -> str:
    """How many days had both Yr and WeatherNext for the same forecast."""
    n = len(compared)
    if not n:
        return "no days with both models yet"
    unit = "day" if n == 1 else "days"
    if compared[0] == first_day:
        return f"both models compared on {n} {unit}"
    first = compared[0]
    return f"both models compared from {int(first[8:10])} {MONTH_NAMES[int(first[5:7]) - 1][:3]}, {n} {unit}"


def describe(label: str, in_progress: bool, first_day: str, last_day: str, compared: list[str],
             verdicts: dict) -> str:
    """The month's text: a header line, one line per variable, then "not enough days yet".

    `compared` lists the days with both Yr and WeatherNext; `verdicts` is what
    `month_verdicts` returns. Lines are separated by newlines.
    """
    head = (f"{label}{' so far' if in_progress else ''} "
            f"({day_range(first_day, last_day)}; {compared_phrase(first_day, compared)})")
    lines = [_variable_line(verdicts, "t"), _variable_line(verdicts, "w"), _rain_line(verdicts["p"]),
             _not_enough_line(verdicts)]
    return "\n".join([head] + [x for x in lines if x])


def compared_days(df: pd.DataFrame) -> list[str]:
    """Days with at least one row where Yr, WeatherNext and the measurement all exist."""
    both = pd.Series(False, index=df.index)
    for var in ("t", "w", "p"):
        cols = [f"obs_{var}", f"yr_{var}", f"wn_{var}"]
        if all(c in df for c in cols):
            both |= df[cols].notna().all(axis=1)
    return sorted(df.loc[both, "target"].astype(str).str[:10].unique()) if len(df) else []


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
            compared = compared_days(df)
            verdicts = month_verdicts(df)
            in_progress = key == this_month
            label = MONTH_NAMES[int(key[5:7]) - 1]
            months.append({
                "month": key, "label": label, "in_progress": in_progress,
                "first_day": days[0], "last_day": days[-1], "days": len(days),
                "text": describe(label, in_progress, days[0], days[-1], compared, verdicts),
                "verdicts": {k: {str(h): x for h, x in val.items()} for k, val in verdicts.items()},
            })
    return {"as_of": f"{now:%Y-%m-%d}", "horizons": SUMMARY_HORIZONS, "months": months}
