"""Frost observations: the answer key.

Same element choices as the local app: air_temperature and wind_speed at the
default offsets/levels, and `sum(precipitation_amount PT1H)` whose referenceTime
is the END of the one-hour interval. Only the main series (timeSeriesId 0) and
values exactly on the hour are kept.
"""
from __future__ import annotations

from datetime import datetime

import requests

from .timeutil import iso, parse

URL = "https://frost.met.no/observations/v0.jsonld"
BASIC = "air_temperature,wind_speed"
PRECIP = "sum(precipitation_amount PT1H)"


def fetch(sources: list[str], start: datetime, end: datetime, client_id: str,
          elements: str) -> list[dict]:
    r = requests.get(URL, params={
        "sources": ",".join(sources),
        "referencetime": f"{iso(start)}/{iso(end)}",
        "elements": elements,
        "timeoffsets": "default",
        "levels": "default",
        "qualities": "0,1,2,3,4",
    }, auth=(client_id, ""), timeout=90)
    if r.status_code == 404:  # Frost answers 404 when nothing matches
        return []
    if not r.ok:
        raise RuntimeError(f"Frost {r.status_code}: {r.text[:300]}")
    return r.json().get("data", [])


def parse_rows(data: list[dict]) -> list[dict]:
    out: dict[tuple[str, str], dict] = {}
    for item in data:
        station = str(item.get("sourceId", "")).split(":", 1)[0].upper()
        try:
            t = parse(item["referenceTime"])
        except (KeyError, ValueError):
            continue
        if t.minute or t.second or not station:
            continue
        key = (station, iso(t))
        row = out.setdefault(key, {"station": station, "time": key[1],
                                   "t": None, "w": None, "p": None})
        for obs in item.get("observations", []):
            if obs.get("timeSeriesId") not in (None, 0, "0") or obs.get("value") is None:
                continue
            element, value = obs.get("elementId"), float(obs["value"])
            if element == "air_temperature" and row["t"] is None:
                row["t"] = value
            elif element == "wind_speed" and row["w"] is None and value >= 0:
                row["w"] = value
            elif element == PRECIP and row["p"] is None:
                meta = (obs.get("unit"), obs.get("timeOffset"), obs.get("timeResolution"))
                if meta == ("mm", "PT0H", "PT1H") and value >= 0:
                    row["p"] = value
    return [r for r in out.values() if any(r[k] is not None for k in "twp")]


def collect(stations: list[dict], start: datetime, end: datetime,
            client_id: str) -> tuple[list[dict], list[str]]:
    if not client_id:
        raise ValueError("FROST_CLIENT_ID is missing")
    ids = [s["station_id"] for s in stations]
    data, errors = [], []
    for i in range(0, len(ids), 25):
        chunk = ids[i:i + 25]
        for elements in (BASIC, PRECIP):
            try:
                data.extend(fetch(chunk, start, end, client_id, elements))
            except Exception as exc:
                errors.append(f"Frost {chunk[0]}..{chunk[-1]} {elements}: {exc}")
    # Temperature/wind and precipitation arrive in separate responses; merge them.
    merged: dict[tuple[str, str], dict] = {}
    for r in parse_rows(data):
        m = merged.setdefault((r["station"], r["time"]), dict(r))
        for k in "twp":
            if m[k] is None:
                m[k] = r[k]
    return list(merged.values()), errors
