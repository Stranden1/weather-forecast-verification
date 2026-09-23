"""Yr / MET Norway locationforecast collector (the `complete` product).

`complete` adds Yr's own uncertainty: 10th/90th percentiles for temperature and
wind, and min/max/probability for precipitation, so both providers' uncertainty
can be checked against what actually happened.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

import requests

from .config import wanted_leads
from .timeutil import hours_between, iso, parse

URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"


def fetch(lat: float, lon: float, user_agent: str, session: requests.Session) -> dict:
    if not user_agent or "example.com" in user_agent:
        raise ValueError("Set MET_USER_AGENT to an identifying app name and contact e-mail.")
    r = session.get(URL, params={"lat": round(lat, 4), "lon": round(lon, 4)},
                    headers={"User-Agent": user_agent}, timeout=30)
    r.raise_for_status()
    return r.json()


def in_window(lead: float) -> bool:
    return any(lo <= lead <= hi for _, lo, hi in wanted_leads())


def extract(payload: dict, station: str, fetched: datetime) -> list[dict]:
    """Return pending rows for targets inside a horizon window.

    Instant values (temperature, wind) belong to the step time. Yr's
    `next_1_hours` precipitation covers [time, time+1h) and is keyed by the
    interval END, matching Frost `referenceTime` and WeatherNext `end_time`.
    """
    props = payload["properties"]
    issued = iso(parse(props["meta"]["updated_at"]))
    rows: dict[str, dict] = {}

    def row(target: datetime) -> dict | None:
        lead = hours_between(target, fetched)
        if lead <= 0 or not in_window(lead):
            return None
        key = iso(target)
        return rows.setdefault(key, {
            "provider": "yr", "station": station, "fetched_at": iso(fetched),
            "issued_at": issued, "target": key, "lead_h": round(lead, 3)})

    for step in props["timeseries"]:
        t0 = parse(step["time"])
        inst = step["data"].get("instant", {}).get("details", {})
        r = row(t0)
        if r is not None:
            r["t"] = inst.get("air_temperature")
            r["t_p10"] = inst.get("air_temperature_percentile_10")
            r["t_p90"] = inst.get("air_temperature_percentile_90")
            r["w"] = inst.get("wind_speed")
            r["w_p10"] = inst.get("wind_speed_percentile_10")
            r["w_p90"] = inst.get("wind_speed_percentile_90")
        nxt = step["data"].get("next_1_hours", {}).get("details")
        if nxt:
            r = row(t0 + timedelta(hours=1))
            if r is not None:
                r["p"] = nxt.get("precipitation_amount")
                r["p_min"] = nxt.get("precipitation_amount_min")
                r["p_max"] = nxt.get("precipitation_amount_max")
                r["p_prob"] = nxt.get("probability_of_precipitation")
    return list(rows.values())


def collect(stations: list[dict], user_agent: str, fetched: datetime,
            pause: float = 0.12) -> tuple[list[dict], list[str]]:
    session = requests.Session()
    out, errors = [], []
    for i, s in enumerate(stations):
        try:
            payload = fetch(s["latitude"], s["longitude"], user_agent, session)
            out.extend(extract(payload, s["station_id"], fetched))
        except Exception as exc:  # one bad station must not stop the run
            errors.append(f"Yr {s['station_id']}: {exc}")
        if i < len(stations) - 1:
            time.sleep(pause)  # be polite to api.met.no
    return out, errors
