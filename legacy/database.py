from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "weather.db"
APP_VERSION = "0.2.2"

# These five are retained as anchor/test stations. V0.2 can add dozens more
# automatically from Frost without deleting any history already collected.
SEED_STATIONS = [
    ("Trondheim", "SN68860", "TRONDHEIM - VOLL", 63.4107, 10.4538),
    ("Oslo", "SN18700", "OSLO - BLINDERN", 59.9423, 10.7200),
    ("Bergen", "SN50540", "BERGEN - FLORIDA", 60.3830, 5.3327),
    ("Tromsø", "SN90450", "TROMSØ", 69.6537, 18.9368),
    ("Røros", "SN10380", "RØROS LUFTHAVN", 62.5773, 11.3518),
]

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    station_id TEXT,
    station_name TEXT,
    station_class TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    discovered_at TEXT,
    elevation_m REAL,
    county TEXT,
    municipality TEXT,
    station_holders TEXT,
    wmo_id TEXT,
    icao_codes TEXT,
    site_group TEXT,
    source_valid_from TEXT,
    source_valid_to TEXT
);

CREATE TABLE IF NOT EXISTS forecast_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    location_id INTEGER NOT NULL,
    issued_at TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    FOREIGN KEY(location_id) REFERENCES locations(id),
    UNIQUE(provider, location_id, issued_at)
);

CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    valid_at TEXT NOT NULL,
    lead_hours REAL NOT NULL,
    air_temperature REAL,
    wind_speed REAL,
    precipitation_1h REAL,
    FOREIGN KEY(run_id) REFERENCES forecast_runs(id) ON DELETE CASCADE,
    UNIQUE(run_id, valid_at)
);

CREATE TABLE IF NOT EXISTS observation_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    element TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_name TEXT,
    distance_km REAL,
    latitude REAL,
    longitude REAL,
    checked_at TEXT NOT NULL,
    FOREIGN KEY(location_id) REFERENCES locations(id),
    UNIQUE(location_id, element)
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    source_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    air_temperature REAL,
    wind_speed REAL,
    precipitation_1h REAL,
    FOREIGN KEY(location_id) REFERENCES locations(id),
    UNIQUE(location_id, source_id, observed_at)
);

CREATE TABLE IF NOT EXISTS collection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT
);

CREATE INDEX IF NOT EXISTS idx_forecasts_valid ON forecasts(valid_at);
CREATE INDEX IF NOT EXISTS idx_observations_time ON observations(observed_at);
"""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _columns(con: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}


def _ensure_column(con: sqlite3.Connection, table: str, name: str, ddl: str) -> None:
    if name not in _columns(con, table):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db() -> None:
    """Create/migrate the DB in place. V0.2 never resets V0.1.3 history."""
    with connect() as con:
        con.executescript(SCHEMA)

        # Non-destructive migration from V0.1.3.
        _ensure_column(con, "locations", "station_id", "TEXT")
        _ensure_column(con, "locations", "station_name", "TEXT")
        _ensure_column(con, "locations", "station_class", "TEXT")
        _ensure_column(con, "locations", "active", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(con, "locations", "discovered_at", "TEXT")
        _ensure_column(con, "locations", "elevation_m", "REAL")
        _ensure_column(con, "locations", "county", "TEXT")
        _ensure_column(con, "locations", "municipality", "TEXT")
        _ensure_column(con, "locations", "station_holders", "TEXT")
        _ensure_column(con, "locations", "wmo_id", "TEXT")
        _ensure_column(con, "locations", "icao_codes", "TEXT")
        _ensure_column(con, "locations", "site_group", "TEXT")
        _ensure_column(con, "locations", "source_valid_from", "TEXT")
        _ensure_column(con, "locations", "source_valid_to", "TEXT")
        _ensure_column(con, "observations", "wind_speed", "REAL")
        _ensure_column(con, "observations", "precipitation_1h", "REAL")

        # Indexes that reference V0.2 columns MUST be created only after the
        # ALTER TABLE migration above. Older V0.1.3 databases do not have
        # station_id when SCHEMA first runs.
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_locations_station "
            "ON locations(station_id)"
        )
        try:
            con.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_locations_station_unique "
                "ON locations(station_id) WHERE station_id IS NOT NULL"
            )
        except sqlite3.IntegrityError:
            # Should not occur for V0.1.3, but don't block startup if a user has
            # hand-edited the DB. Discovery will still work by location name.
            pass

        con.execute(
            "INSERT INTO app_meta(key, value) VALUES('app_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (APP_VERSION,),
        )


def seed_locations() -> None:
    now = utc_now_iso()
    with connect() as con:
        for display_name, station_id, station_name, lat, lon in SEED_STATIONS:
            existing = con.execute(
                "SELECT id FROM locations WHERE station_id=? OR name=? LIMIT 1",
                (station_id, display_name),
            ).fetchone()
            if existing:
                location_id = existing["id"]
                con.execute(
                    """
                    UPDATE locations
                    SET latitude=?, longitude=?, station_id=?, station_name=?,
                        station_class=COALESCE(station_class, 'C'), active=1,
                        discovered_at=COALESCE(discovered_at, ?)
                    WHERE id=?
                    """,
                    (lat, lon, station_id, station_name, now, location_id),
                )
            else:
                cur = con.execute(
                    """
                    INSERT INTO locations(
                        name, latitude, longitude, station_id, station_name,
                        station_class, active, discovered_at
                    ) VALUES (?, ?, ?, ?, ?, 'C', 1, ?)
                    """,
                    (display_name, lat, lon, station_id, station_name, now),
                )
                location_id = cur.lastrowid

            # The five anchors are known to have temperature observations.
            con.execute(
                """
                INSERT INTO observation_sources(
                    location_id, element, source_id, source_name, distance_km,
                    latitude, longitude, checked_at
                ) VALUES (?, 'air_temperature', ?, ?, 0, ?, ?, ?)
                ON CONFLICT(location_id, element) DO UPDATE SET
                    source_id=excluded.source_id,
                    source_name=excluded.source_name,
                    latitude=excluded.latitude,
                    longitude=excluded.longitude,
                    checked_at=excluded.checked_at
                """,
                (location_id, station_id, station_name, lat, lon, now),
            )


def set_meta(key: str, value: str) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO app_meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def get_meta(key: str, default: str | None = None) -> str | None:
    with connect() as con:
        row = con.execute("SELECT value FROM app_meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def log_collection_start(mode: str) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO collection_log(started_at, mode, status) VALUES (?, ?, 'running')",
            (utc_now_iso(), mode),
        )
        return cur.lastrowid


def log_collection_finish(log_id: int, status: str, message: str = "") -> None:
    with connect() as con:
        con.execute(
            "UPDATE collection_log SET finished_at=?, status=?, message=? WHERE id=?",
            (utc_now_iso(), status, message[:4000], log_id),
        )
