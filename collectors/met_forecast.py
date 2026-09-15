from __future__ import annotations

import time
from datetime import datetime, timezone

import requests

from database import connect

URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_locationforecast(lat: float, lon: float, user_agent: str, session: requests.Session | None = None) -> dict:
    if not user_agent or "your-email@example.com" in user_agent:
        raise ValueError("Set MET_USER_AGENT to a real identifying User-Agent/contact first.")
    session = session or requests.Session()
    r = session.get(
        URL,
        params={"lat": round(lat, 4), "lon": round(lon, 4)},
        headers={"User-Agent": user_agent},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def save_forecast(location_id: int, payload: dict) -> tuple[int, int]:
    props = payload["properties"]
    issued_at = props["meta"]["updated_at"]
    retrieved_at = _iso(datetime.now(timezone.utc))
    issued_dt = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))

    with connect() as con:
        con.execute(
            """
            INSERT OR IGNORE INTO forecast_runs(provider, location_id, issued_at, retrieved_at)
            VALUES ('MET', ?, ?, ?)
            """,
            (location_id, issued_at, retrieved_at),
        )
        run = con.execute(
            "SELECT id FROM forecast_runs WHERE provider='MET' AND location_id=? AND issued_at=?",
            (location_id, issued_at),
        ).fetchone()
        run_id = run["id"]

        added = 0
        for ts in props["timeseries"]:
            valid_at = ts["time"]
            valid_dt = datetime.fromisoformat(valid_at.replace("Z", "+00:00"))
            lead_hours = (valid_dt - issued_dt).total_seconds() / 3600
            details = ts["data"]["instant"]["details"]
            temp = details.get("air_temperature")
            wind = details.get("wind_speed")
            precip = None
            if "next_1_hours" in ts["data"]:
                precip = ts["data"]["next_1_hours"].get("details", {}).get("precipitation_amount")

            cur = con.execute(
                """
                INSERT OR IGNORE INTO forecasts(
                    run_id, valid_at, lead_hours, air_temperature, wind_speed, precipitation_1h
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, valid_at, lead_hours, temp, wind, precip),
            )
            added += cur.rowcount
    return run_id, added


def collect_all(user_agent: str) -> dict:
    result = {"locations": 0, "rows_added": 0, "errors": []}
    with connect() as con:
        locations = con.execute(
            "SELECT * FROM locations WHERE active=1 ORDER BY name"
        ).fetchall()

    session = requests.Session()
    for i, loc in enumerate(locations):
        try:
            payload = fetch_locationforecast(loc["latitude"], loc["longitude"], user_agent, session=session)
            _, added = save_forecast(loc["id"], payload)
            result["locations"] += 1
            result["rows_added"] += added
        except Exception as exc:
            result["errors"].append(f"{loc['name']}: {exc}")
        # Be polite to api.met.no instead of sending a large burst.
        if i < len(locations) - 1:
            time.sleep(0.12)
    return result
