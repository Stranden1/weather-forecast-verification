from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from collectors.frost_observations import sync_recent
from collectors.met_forecast import collect_all
from collectors.station_network import discover_and_save
from database import (
    connect,
    get_meta,
    init_db,
    log_collection_finish,
    log_collection_start,
    seed_locations,
)

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "data" / "background.log"
load_dotenv(BASE_DIR / ".env")


def _write_log(text: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{stamp}  {text}\n")


def _needs_station_refresh(target: int) -> bool:
    with connect() as con:
        active = con.execute("SELECT COUNT(*) FROM locations WHERE active=1").fetchone()[0]
    if active < target:
        return True
    raw = get_meta("last_station_discovery")
    if not raw:
        return True
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return True
    return (datetime.now(timezone.utc) - dt).days >= 7


def _collect_weathernext(messages: list[str]) -> bool:
    """Isolate WeatherNext failures from MET and Frost. Enable after live verification."""
    if os.getenv('WEATHERNEXT_ENABLED','0').strip() != '1':
        messages.append('WeatherNext disabled')
        return True
    try:
        from collectors.weathernext import collect_all as collect_weathernext
        result = collect_weathernext(progress=_write_log)
        messages.append(f'WeatherNext={result["sample_values_added"]} new values; run={result["issued_at"]}')
        return True
    except Exception as exc:
        messages.append(f'WeatherNext ERROR {type(exc).__name__}: {exc}')
        return False


def main() -> int:
    init_db()
    seed_locations()
    log_id = log_collection_start("background")
    ua = os.getenv("MET_USER_AGENT", "").strip()
    frost = os.getenv("FROST_CLIENT_ID", "").strip()
    target = max(5, min(200, int(os.getenv("TARGET_STATIONS", "50") or 50)))
    auto_discover = os.getenv("AUTO_DISCOVER_STATIONS", "1").strip() != "0"

    messages = []
    try:
        if frost and auto_discover and _needs_station_refresh(target):
            discovery = discover_and_save(frost, target=target)
            messages.append(f"network={discovery}")

        met = collect_all(ua)
        messages.append(f"MET={met}")

        if frost:
            obs = sync_recent(frost, days=3)
            messages.append(f"Frost={obs}")
        else:
            messages.append("Frost skipped: no client ID")

        wn_ok = _collect_weathernext(messages)
        message = " | ".join(messages)
        _write_log(("OK  " if wn_ok else "PARTIAL ERROR  ") + message)
        log_collection_finish(log_id, "ok" if wn_ok else "error", message)
        return 0 if wn_ok else 1
    except Exception as exc:
        message = f"ERROR {type(exc).__name__}: {exc}"
        _write_log(message)
        log_collection_finish(log_id, "error", message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
