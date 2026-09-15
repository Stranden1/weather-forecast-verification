from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

import requests

from database import connect

OBS_URL = "https://frost.met.no/observations/v0.jsonld"
ELEMENTS = "air_temperature,wind_speed"


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _base_source_id(source_id: str) -> str:
    return source_id.split(":", 1)[0].upper()


def _chunks(items: list[str], n: int) -> Iterable[list[str]]:
    for i in range(0, len(items), n):
        yield items[i : i + n]


def fetch_observations(source_ids: list[str], start: datetime, end: datetime, client_id: str) -> list[dict]:
    params = {
        "sources": ",".join(source_ids),
        "referencetime": f"{_utc_iso(start)}/{_utc_iso(end)}",
        "elements": ELEMENTS,
        "timeoffsets": "default",
        "levels": "default",
        "qualities": "0,1,2,3,4",
    }
    r = requests.get(OBS_URL, params=params, auth=(client_id, ""), timeout=90)
    if r.status_code == 404:
        return []
    if not r.ok:
        detail = r.text[:1000].replace("\n", " ")
        raise RuntimeError(f"Frost observation lookup failed ({r.status_code}): {detail}")
    return r.json().get("data", [])


def save_observation_rows(rows: list[dict], source_to_location: dict[str, int]) -> int:
    changed = 0
    with connect() as con:
        for row in rows:
            source_id_full = str(row.get("sourceId", ""))
            source_id = _base_source_id(source_id_full)
            location_id = source_to_location.get(source_id)
            ref_time = row.get("referenceTime")
            if not location_id or not ref_time:
                continue

            temp = None
            wind = None
            for obs in row.get("observations", []):
                ts_id = obs.get("timeSeriesId")
                if ts_id not in (None, 0, "0"):
                    continue
                element = obs.get("elementId")
                value = obs.get("value")
                if value is None:
                    continue
                if element == "air_temperature" and temp is None:
                    temp = value
                elif element == "wind_speed" and wind is None:
                    wind = value

            if temp is None and wind is None:
                continue
            cur = con.execute(
                """
                INSERT INTO observations(
                    location_id, source_id, observed_at, air_temperature, wind_speed
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(location_id, source_id, observed_at) DO UPDATE SET
                    air_temperature=COALESCE(excluded.air_temperature, observations.air_temperature),
                    wind_speed=COALESCE(excluded.wind_speed, observations.wind_speed)
                """,
                (location_id, source_id, ref_time, temp, wind),
            )
            changed += cur.rowcount
    return changed


def sync_recent(client_id: str, days: int = 10) -> dict:
    if not client_id:
        raise ValueError("FROST_CLIENT_ID is missing.")
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    result = {"locations": 0, "rows_added": 0, "errors": []}

    with connect() as con:
        rows = con.execute(
            """
            SELECT id, station_id FROM locations
            WHERE active=1 AND station_id IS NOT NULL
            ORDER BY station_id
            """
        ).fetchall()
    source_to_location = {str(r["station_id"]).upper(): r["id"] for r in rows}
    source_ids = list(source_to_location)

    for chunk in _chunks(source_ids, 25):
        try:
            data = fetch_observations(chunk, start, now, client_id)
            result["rows_added"] += save_observation_rows(data, source_to_location)
            result["locations"] += len(chunk)
        except Exception as exc:
            result["errors"].append(f"{chunk[0]}…{chunk[-1]}: {exc}")
    return result
