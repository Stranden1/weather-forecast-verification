"""Google WeatherNext 3 collector via Earth Engine (service-account friendly).

Only the forecast hours that fall inside a verification horizon window are
sampled (about 60 of the 360 hours), for temperature, wind and hourly
precipitation, with mean/p10/p50/p90. Two initializations are used, as a person
checking at that moment would: the newest hourly run (48 h long) for short
targets, and the newest 6-hourly synoptic run (360 h long) for the rest.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone

from .config import wanted_leads
from .timeutil import hours_between, iso, parse

PREFIX = "projects/gcp-public-data-weathernext/assets/weathernext_3_0_0_"
# column prefix -> (collection, band, scale m, statistics)
FIELDS = {
    "t": (PREFIX + "0p05deg", "station_head_temperature_2m", 5000, ("mean", "p10", "p50", "p90")),
    "w": (PREFIX + "0p1deg", "wind_speed_10m", 10000, ("mean", "p10", "p50", "p90")),
    "p": (PREFIX + "0p1deg", "total_precipitation_1hr", 10000, ("mean", "p50", "p90")),
}
HOURLY_MAX = 48
SYNOPTIC_MAX = 360


def convert(col: str, value: float) -> float:
    if col == "t":
        return value - 273.15  # K -> degC
    if col == "p":
        return value * 1000.0  # m -> mm
    return value


def column(col: str, stat: str) -> str:
    return col if stat == "mean" else f"{col}_{stat}"


class EarthEngineSource:
    def __init__(self, project: str | None = None, key_json: str | None = None):
        import ee
        project = project or os.getenv("EARTH_ENGINE_PROJECT")
        key_json = key_json or os.getenv("EE_SERVICE_ACCOUNT_KEY")
        if key_json:
            key = json.loads(key_json)
            creds = ee.ServiceAccountCredentials(key["client_email"], key_data=key_json)
            ee.Initialize(creds, project=project or key.get("project_id"))
        else:  # local use with `earthengine authenticate`
            ee.Initialize(project=project)
        ee.data.setDeadline(120000)
        self.ee = ee

    def hours(self, collection: str, init: str) -> set[int]:
        ee = self.ee
        return set(int(h) for h in ee.ImageCollection(collection)
                   .filter(ee.Filter.eq("start_time", init))
                   .aggregate_array("forecast_hour").getInfo())

    def sample(self, collection, bands, scale, init, hours, stations):
        ee = self.ee
        points = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([s["longitude"], s["latitude"]]), {"station": s["station_id"]})
            for s in stations])
        images = (ee.ImageCollection(collection).filter(ee.Filter.eq("start_time", init))
                  .filter(ee.Filter.inList("forecast_hour", hours)).select(bands))

        def reduce(image):
            image = ee.Image(image)
            res = image.reduceRegions(collection=points, reducer=ee.Reducer.first(),
                                      scale=scale, tileScale=4)
            return res.map(lambda f: ee.Feature(None, f.toDictionary()).set({
                "end_time": image.get("end_time"), "forecast_hour": image.get("forecast_hour")}))

        fc = ee.FeatureCollection(images.toList(len(hours)).map(reduce)).flatten()
        try:
            return [f["properties"] for f in fc.getInfo()["features"]]
        except Exception as exc:  # split oversized requests, as the local collector does
            if "memory" not in str(exc).lower() or len(hours) == 1:
                raise
            mid = len(hours) // 2
            return (self.sample(collection, bands, scale, init, hours[:mid], stations)
                    + self.sample(collection, bands, scale, init, hours[mid:], stations))


def latest_init(source, fetched: datetime, step: int, needed_max: int, lookback: int = 24) -> str | None:
    """Newest initialization whose needed hours are complete in every collection."""
    base = fetched.replace(minute=0, second=0, microsecond=0)
    base -= timedelta(hours=base.hour % step)
    collections = {f[0] for f in FIELDS.values()}
    for n in range(0, lookback, step):
        init = iso(base - timedelta(hours=n))
        if all(set(range(1, needed_max + 1)) <= source.hours(c, init) for c in collections):
            return init
    return None


def plan(fetched: datetime, hourly_init: str | None, synoptic_init: str | None) -> dict[str, list[int]]:
    """Forecast hours to sample per initialization. Each target gets one init."""
    targets: dict[datetime, str] = {}
    first = fetched.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    for _, lo, hi in wanted_leads():
        t = first
        while hours_between(t, fetched) <= hi:
            if hours_between(t, fetched) >= lo:
                for init, max_h in ((hourly_init, HOURLY_MAX), (synoptic_init, SYNOPTIC_MAX)):
                    if init and 1 <= hours_between(t, parse(init)) <= max_h:
                        targets.setdefault(t, init)
                        break
            t += timedelta(hours=1)
    out: dict[str, list[int]] = {}
    for t, init in targets.items():
        out.setdefault(init, []).append(int(hours_between(t, parse(init))))
    return {k: sorted(v) for k, v in out.items()}


def collect(stations: list[dict], fetched: datetime, source=None,
            batch_hours: int = 12) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    source = source or EarthEngineSource()
    hourly = latest_init(source, fetched, 1, HOURLY_MAX, lookback=12)
    synoptic = latest_init(source, fetched, 6, SYNOPTIC_MAX, lookback=36)
    if not synoptic:
        errors.append("WeatherNext: no complete synoptic run in the last 36 h")
    rows: dict[tuple[str, str], dict] = {}
    for init, hours in plan(fetched, hourly, synoptic).items():
        by_collection: dict[str, list[str]] = {}
        for col, (coll, band, scale, stats) in FIELDS.items():
            by_collection.setdefault(coll, []).append(col)
        for coll, cols in by_collection.items():
            bands = [f"{FIELDS[c][1]}_{s}" for c in cols for s in FIELDS[c][3]]
            scale = FIELDS[cols[0]][2]
            for i in range(0, len(hours), batch_hours):
                chunk = hours[i:i + batch_hours]
                try:
                    props = source.sample(coll, bands, scale, init, chunk, stations)
                except Exception as exc:
                    errors.append(f"WeatherNext {init} {coll[-7:]} h{chunk[0]}-{chunk[-1]}: {exc}")
                    continue
                for pr in props:
                    target = iso(parse(pr["end_time"]))
                    lead = hours_between(parse(target), fetched)
                    row = rows.setdefault((pr["station"], target), {
                        "provider": "wn", "station": pr["station"], "fetched_at": iso(fetched),
                        "issued_at": init, "target": target, "lead_h": round(lead, 3)})
                    for c in cols:
                        for s in FIELDS[c][3]:
                            raw = pr.get(f"{FIELDS[c][1]}_{s}")
                            if raw is None or not math.isfinite(float(raw)):
                                continue
                            v = convert(c, float(raw))
                            if c in ("w", "p") and v < 0:
                                v = 0.0 if v > -1e-6 else None
                            row[column(c, s)] = v
    return list(rows.values()), errors
