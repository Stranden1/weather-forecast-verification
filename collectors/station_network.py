from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Iterable

import requests

from database import SEED_STATIONS, connect, set_meta, utc_now_iso

SOURCES_URL = "https://frost.met.no/sources/v0.jsonld"
TIMESERIES_URL = "https://frost.met.no/observations/availableTimeSeries/v0.jsonld"

# We only score temperature/wind in V0.2, but we also detect hourly precipitation
# capability now so the station network is useful when rain scoring is added.
CAPABILITY_QUERIES = {
    "temperature": "air_temperature",
    "wind": "wind_speed",
    "precipitation": "*precipitation_amount*",
}

# This is only a display classification, not a scientific land/sea mask. Frost's
# municipality/county metadata is authoritative when present; the name heuristic
# just helps flag obvious offshore installations when administrative fields are empty.
OFFSHORE_NAME_HINTS = (
    "PLATTFORM", "PLATFORM", "FELT", "FIELD", "EKOFISK", "OSEBERG",
    "GULLFAKS", "STATFJORD", "TROLL", "HEIDRUN", "SNORRE", "DRAUGEN",
    "SLEIPNER", "VALHALL", "GOLIAT", "ORMEN LANGE", "JOHAN SVERDRUP",
    "ÅSGARD", "ASGARD", "NORNE", "KVITEBJØRN", "KVITEBJORN",
)


def _request_json(url: str, client_id: str, params: dict | None = None) -> dict:
    r = requests.get(url, params=params, auth=(client_id, ""), timeout=90)
    if not r.ok:
        detail = r.text[:1000].replace("\n", " ")
        raise RuntimeError(f"Frost request failed ({r.status_code}): {detail}")
    return r.json()


def _parse_coordinates(raw) -> tuple[float, float] | None:
    """Return (lat, lon), tolerating both Frost's legacy string and arrays."""
    if raw is None:
        return None
    if isinstance(raw, str):
        bits = [x.strip() for x in raw.replace("[", "").replace("]", "").split(",")]
        if len(bits) != 2:
            return None
        a, b = float(bits[0]), float(bits[1])
    elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
        a, b = float(raw[0]), float(raw[1])
    else:
        return None

    def lat_like(x: float) -> bool:
        return 55 <= x <= 82

    def lon_like(x: float) -> bool:
        return -15 <= x <= 35

    # Frost output has appeared in both lat/lon-ish legacy serialization and
    # GeoJSON conventions. Detect the Norway-looking coordinate rather than
    # assuming order.
    if lat_like(a) and lon_like(b):
        return a, b
    if lat_like(b) and lon_like(a):
        return b, a
    return a, b


def _as_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        vals = [str(x).strip() for x in value if str(x).strip()]
        return ", ".join(vals) or None
    text = str(value).strip()
    # Some older Frost responses serialize arrays as strings.
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].replace('"', '').strip()
    return text or None


def _site_group(row: dict) -> str:
    municipality = _as_text(row.get("municipality") or row.get("municipalityName"))
    county = _as_text(row.get("county") or row.get("countyName"))
    name = str(row.get("name") or "").upper()
    if municipality or county:
        return "Land / administrative area"
    if any(hint in name for hint in OFFSHORE_NAME_HINTS):
        return "Offshore installation (inferred)"
    return "Marine / remote / unclassified"


def _source_to_station(row: dict) -> dict | None:
    sid = str(row.get("id") or row.get("sourceId") or "").upper()
    if not sid.startswith("SN"):
        return None
    geometry = row.get("geometry") or {}
    coords = _parse_coordinates(geometry.get("coordinates"))
    if not coords:
        return None
    lat, lon = coords
    if not (55 <= lat <= 82 and -15 <= lon <= 35):
        return None
    return {
        "source_id": sid,
        "name": str(row.get("name") or sid),
        "latitude": lat,
        "longitude": lon,
        "elevation_m": row.get("masl"),
        "county": _as_text(row.get("county") or row.get("countyName")),
        "municipality": _as_text(row.get("municipality") or row.get("municipalityName")),
        "station_holders": _as_text(row.get("stationHolders") or row.get("stationHolder")),
        "wmo_id": _as_text(row.get("wmoId") or row.get("wmoIdentifier")),
        "icao_codes": _as_text(row.get("icaoCodes") or row.get("icaoCode")),
        "site_group": _site_group(row),
        "source_valid_from": _as_text(row.get("validFrom")),
        "source_valid_to": _as_text(row.get("validTo")),
        "temperature": False,
        "wind": False,
        "precipitation": False,
    }


def _base_source_id(source_id: str) -> str:
    return source_id.split(":", 1)[0].upper()


def _is_main_series(row: dict) -> bool:
    source_id = str(row.get("sourceId", ""))
    if ":" in source_id and not source_id.endswith(":0"):
        return False
    ts_id = row.get("timeSeriesId")
    if ts_id not in (None, 0, "0"):
        return False
    return True


def _resolution_minutes(value: str | None) -> float | None:
    if not value:
        return None
    value = str(value).upper()
    if value.startswith("PT"):
        text = value[2:]
        hours = minutes = seconds = 0.0
        if "H" in text:
            h, text = text.split("H", 1)
            hours = float(h or 0)
        if "M" in text:
            m, text = text.split("M", 1)
            minutes = float(m or 0)
        if "S" in text:
            s = text.split("S", 1)[0]
            seconds = float(s or 0)
        return hours * 60 + minutes + seconds / 60
    if value == "P1D":
        return 1440
    return None


def _collect_source_pages(payload: dict, client_id: str) -> list[dict]:
    rows: list[dict] = []
    seen_links = set()
    while True:
        rows.extend(payload.get("data", []))
        next_link = payload.get("nextLink")
        if not next_link or next_link in seen_links:
            break
        seen_links.add(next_link)
        payload = _request_json(next_link, client_id)
    return rows


def fetch_active_temperature_sources(client_id: str) -> list[dict]:
    """Fetch currently valid Norwegian SensorSystem sources with temperature."""
    params = {
        "types": "SensorSystem",
        "country": "NO",
        "elements": "air_temperature",
        "validtime": "now",
    }
    payload = _request_json(SOURCES_URL, client_id, params=params)
    out = []
    for row in _collect_source_pages(payload, client_id):
        station = _source_to_station(row)
        if station:
            out.append(station)
    return list({x["source_id"]: x for x in out}.values())


def _chunks(items: list[str], n: int) -> Iterable[list[str]]:
    for i in range(0, len(items), n):
        yield items[i : i + n]


def refresh_active_metadata(client_id: str) -> dict:
    """Refresh descriptive Frost metadata for stations already active in our DB."""
    with connect() as con:
        ids = [r[0] for r in con.execute(
            "SELECT station_id FROM locations WHERE active=1 AND station_id IS NOT NULL"
        ).fetchall()]
    if not ids:
        return {"requested": 0, "updated": 0}

    found: dict[str, dict] = {}
    for chunk in _chunks(ids, 50):
        payload = _request_json(
            SOURCES_URL,
            client_id,
            params={"ids": ",".join(chunk), "types": "SensorSystem"},
        )
        for row in _collect_source_pages(payload, client_id):
            station = _source_to_station(row)
            if station:
                found[station["source_id"]] = station

    with connect() as con:
        for sid, s in found.items():
            con.execute(
                """
                UPDATE locations SET station_name=?, latitude=?, longitude=?,
                    elevation_m=?, county=?, municipality=?, station_holders=?,
                    wmo_id=?, icao_codes=?, site_group=?, source_valid_from=?,
                    source_valid_to=?
                WHERE station_id=?
                """,
                (
                    s["name"], s["latitude"], s["longitude"], s["elevation_m"],
                    s["county"], s["municipality"], s["station_holders"],
                    s["wmo_id"], s["icao_codes"], s["site_group"],
                    s["source_valid_from"], s["source_valid_to"], sid,
                ),
            )
    set_meta("last_station_metadata_refresh", utc_now_iso())
    return {"requested": len(ids), "updated": len(found)}


def detect_recent_capabilities(candidates: list[dict], client_id: str, days: int = 7) -> None:
    ids = [x["source_id"] for x in candidates]
    by_id = {x["source_id"]: x for x in candidates}
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    period = f"{start.isoformat()}/{end.isoformat()}"

    for capability, element_filter in CAPABILITY_QUERIES.items():
        for chunk in _chunks(ids, 40):
            payload = _request_json(
                TIMESERIES_URL,
                client_id,
                params={
                    "sources": ",".join(chunk),
                    "referencetime": period,
                    "elements": element_filter,
                },
            )
            for row in payload.get("data", []):
                if not _is_main_series(row):
                    continue
                sid = _base_source_id(str(row.get("sourceId", "")))
                station = by_id.get(sid)
                if not station:
                    continue
                resolution = _resolution_minutes(row.get("timeResolution"))
                if resolution is not None and resolution > 60:
                    continue
                element_id = str(row.get("elementId", ""))
                if capability == "precipitation":
                    if "PT1H" not in element_id.upper() and element_id != "precipitation_amount":
                        continue
                station[capability] = True


def _haversine_km(a: dict, b: dict) -> float:
    lat1, lon1, lat2, lon2 = map(
        radians, [a["latitude"], a["longitude"], b["latitude"], b["longitude"]]
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(h))


def _grade(station: dict) -> str:
    if station.get("temperature") and station.get("wind") and station.get("precipitation"):
        return "A"
    if station.get("temperature") and (station.get("wind") or station.get("precipitation")):
        return "B"
    return "C"


def _capability_score(station: dict) -> int:
    return int(bool(station.get("temperature"))) + int(bool(station.get("wind"))) + int(bool(station.get("precipitation")))


def select_geographically_distributed(candidates: list[dict], target: int) -> list[dict]:
    candidates = [x for x in candidates if x.get("temperature")]
    if target <= 0 or not candidates:
        return []
    if len(candidates) <= target:
        return candidates

    by_id = {x["source_id"]: x for x in candidates}
    priority_ids = [x[1] for x in SEED_STATIONS]
    selected: list[dict] = [by_id[sid] for sid in priority_ids if sid in by_id]
    selected_ids = {x["source_id"] for x in selected}

    if not selected:
        selected = [max(candidates, key=lambda x: (_capability_score(x), -abs(x["latitude"] - 64.5)))]
        selected_ids = {selected[0]["source_id"]}

    while len(selected) < min(target, len(candidates)):
        best = None
        best_score = -1.0
        for station in candidates:
            if station["source_id"] in selected_ids:
                continue
            nearest = min(_haversine_km(station, chosen) for chosen in selected)
            richness = 1.0 + 0.08 * max(0, _capability_score(station) - 1)
            score = nearest * richness
            if score > best_score:
                best = station
                best_score = score
        if best is None:
            break
        selected.append(best)
        selected_ids.add(best["source_id"])
    return selected


def save_station_network(selected: list[dict]) -> dict:
    now = utc_now_iso()
    seed_ids = {x[1] for x in SEED_STATIONS}
    counts = {"A": 0, "B": 0, "C": 0}

    with connect() as con:
        con.execute("UPDATE locations SET active=0 WHERE station_id IS NOT NULL")

        for s in selected:
            grade = _grade(s)
            counts[grade] += 1
            existing = con.execute(
                "SELECT id, name FROM locations WHERE station_id=? LIMIT 1",
                (s["source_id"],),
            ).fetchone()
            metadata = (
                s["elevation_m"], s["county"], s["municipality"],
                s["station_holders"], s["wmo_id"], s["icao_codes"],
                s["site_group"], s["source_valid_from"], s["source_valid_to"],
            )
            if existing:
                location_id = existing["id"]
                con.execute(
                    """
                    UPDATE locations SET latitude=?, longitude=?, station_name=?,
                        station_class=?, active=1, discovered_at=?, elevation_m=?,
                        county=?, municipality=?, station_holders=?, wmo_id=?,
                        icao_codes=?, site_group=?, source_valid_from=?, source_valid_to=?
                    WHERE id=?
                    """,
                    (
                        s["latitude"], s["longitude"], s["name"], grade, now,
                        *metadata, location_id,
                    ),
                )
            else:
                display_name = f"{s['name']} [{s['source_id']}]"
                cur = con.execute(
                    """
                    INSERT INTO locations(
                        name, latitude, longitude, station_id, station_name,
                        station_class, active, discovered_at, elevation_m, county,
                        municipality, station_holders, wmo_id, icao_codes, site_group,
                        source_valid_from, source_valid_to
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        display_name, s["latitude"], s["longitude"], s["source_id"],
                        s["name"], grade, now, *metadata,
                    ),
                )
                location_id = cur.lastrowid

            for capability, element in [
                ("temperature", "air_temperature"),
                ("wind", "wind_speed"),
                ("precipitation", "precipitation_1h"),
            ]:
                if not s.get(capability):
                    continue
                con.execute(
                    """
                    INSERT INTO observation_sources(
                        location_id, element, source_id, source_name, distance_km,
                        latitude, longitude, checked_at
                    ) VALUES (?, ?, ?, ?, 0, ?, ?, ?)
                    ON CONFLICT(location_id, element) DO UPDATE SET
                        source_id=excluded.source_id,
                        source_name=excluded.source_name,
                        latitude=excluded.latitude,
                        longitude=excluded.longitude,
                        checked_at=excluded.checked_at
                    """,
                    (
                        location_id, element, s["source_id"], s["name"],
                        s["latitude"], s["longitude"], now,
                    ),
                )

        if seed_ids:
            placeholders = ",".join("?" for _ in seed_ids)
            con.execute(
                f"UPDATE locations SET active=1 WHERE station_id IN ({placeholders})",
                tuple(seed_ids),
            )

    set_meta("last_station_discovery", now)
    set_meta("last_station_metadata_refresh", now)
    set_meta("station_target", str(len(selected)))
    return {"selected": len(selected), **counts}


def discover_and_save(client_id: str, target: int = 50) -> dict:
    if not client_id:
        raise ValueError("FROST_CLIENT_ID is missing.")
    candidates = fetch_active_temperature_sources(client_id)
    detect_recent_capabilities(candidates, client_id, days=7)
    verified = [x for x in candidates if x.get("temperature")]
    selected = select_geographically_distributed(verified, target)
    saved = save_station_network(selected)
    saved.update({"candidates": len(candidates), "recent_temperature": len(verified)})
    return saved
