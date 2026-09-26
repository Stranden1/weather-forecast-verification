"""ECMWF IFS HRES and AIFS Single via Open-Meteo's ECMWF API (free, non-commercial, CC BY 4.0).

One request per batch of stations fetches both models, for the same horizon windows
as Yr and WeatherNext, in the same collection run. Each station's elevation is sent,
so Open-Meteo adapts temperature to the station's height. Values are hourly: IFS HRES
is hourly to 90 h, AIFS is 6-hourly and Open-Meteo interpolates it to hours (so AIFS
hourly rain is spread over the 6 hours). `precipitation` is the preceding-hour sum,
so its time is already the interval END, as for Frost, Yr and WeatherNext.

Rate limits (free API): 600 calls/min, 5,000/hour, 10,000/day. A location with up to
10 variables and 2 weeks counts as one call, so one run is ~50 calls (~200/day).
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone

import requests

from .config import wanted_leads
from .timeutil import hours_between, iso

URL = "https://api.open-meteo.com/v1/ecmwf"
META_URL = "https://api.open-meteo.com/data/{model}/static/meta.json"
# provider column prefix -> Open-Meteo model
MODELS = {"ifs": "ecmwf_ifs", "aifs": "ecmwf_aifs025_single"}
VARIABLES = {"t": "temperature_2m", "w": "wind_speed_10m", "p": "precipitation"}
FORECAST_DAYS = 11  # covers the 240 h horizon + 3 h tolerance
BATCH = 25          # stations per request (keeps URLs short)
USER_AGENT = "weather-forecast-verification (github.com/Stranden1/weather-forecast-verification)"


def in_window(lead: float) -> bool:
    return any(lo <= lead <= hi for _, lo, hi in wanted_leads())


def _get(session, url, params=None, tries: int = 3, wait: float = 10.0):
    """GET with a short, polite back-off on rate limiting or server errors."""
    for attempt in range(tries):
        r = session.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=60)
        if r.status_code in (429, 500, 502, 503, 504) and attempt < tries - 1:
            time.sleep(wait * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()


def elevation_param(stations: list[dict]) -> str:
    # "nan" = no station height known: Open-Meteo then uses the grid cell's height.
    return ",".join("nan" if s.get("elevation_m") is None else f"{float(s['elevation_m']):g}"
                    for s in stations)


def request_params(stations: list[dict]) -> dict:
    return {
        "latitude": ",".join(f"{s['latitude']:.4f}" for s in stations),
        "longitude": ",".join(f"{s['longitude']:.4f}" for s in stations),
        "elevation": elevation_param(stations),
        "hourly": ",".join(VARIABLES.values()),
        "models": ",".join(MODELS.values()),
        "wind_speed_unit": "ms",
        "forecast_days": FORECAST_DAYS,
        "timezone": "GMT",
    }


def issued_times(session) -> dict[str, str | None]:
    """Latest run (initialisation) per model, from Open-Meteo's model metadata."""
    out = {}
    for name, model in MODELS.items():
        try:
            meta = _get(session, META_URL.format(model=model), tries=2, wait=5)
            out[name] = iso(datetime.fromtimestamp(meta["last_run_initialisation_time"], timezone.utc))
        except Exception:
            out[name] = None  # issue time is informative only; pairing uses the fetch time
    return out


def extract(payload: dict, station: str, fetched: datetime, issued: dict) -> list[dict]:
    """Pending rows (one per model and target hour) inside a horizon window."""
    hourly = payload.get("hourly") or {}
    rows = []
    for i, t in enumerate(hourly.get("time", [])):
        target = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        lead = hours_between(target, fetched)
        if lead <= 0 or not in_window(lead):
            continue
        for name, model in MODELS.items():
            vals = {}
            for col, var in VARIABLES.items():
                series = hourly.get(f"{var}_{model}")
                v = series[i] if series and i < len(series) else None
                if v is not None and math.isfinite(float(v)):
                    vals[col] = float(v)
            if vals:
                rows.append({"provider": name, "station": station, "fetched_at": iso(fetched),
                             "issued_at": issued.get(name), "target": iso(target),
                             "lead_h": round(lead, 3), **vals})
    return rows


def collect(stations: list[dict], fetched: datetime, session=None) -> tuple[list[dict], list[str]]:
    session = session or requests.Session()
    issued = issued_times(session)
    out, errors = [], []
    for k in range(0, len(stations), BATCH):
        batch = stations[k:k + BATCH]
        try:
            data = _get(session, URL, request_params(batch))
            payloads = data if isinstance(data, list) else [data]
            if len(payloads) != len(batch):
                raise ValueError(f"expected {len(batch)} locations, got {len(payloads)}")
            for s, payload in zip(batch, payloads):
                out.extend(extract(payload, s["station_id"], fetched, issued))
        except Exception as exc:  # one failed batch must not stop the run
            errors.append(f"ECMWF (Open-Meteo) stations {k + 1}-{k + len(batch)}: {exc}")
        if k + BATCH < len(stations):
            time.sleep(1.0)
    return out, errors
