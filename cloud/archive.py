"""Append-only, encrypted Yr responses and simple slot manifests.

No State/history writes, weather requests, or durable retry spool. Failed uploads
lose this runner's capture; the next collection can try again inside the window.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import date, datetime
from pathlib import Path

from .archive_policy import POLICY_VERSION, Slot, active_slot, closed_slots, utc
from .store import _fernet

SCHEMA = 1
ARCHIVE_PATH = Path("forecast/yr/v1")
SUFFIX = ".json.gz.fernet"
SAFE_HEADERS = {"date", "expires", "last-modified", "etag", "content-type"}


def stamp(at: datetime) -> str:
    return utc(at).isoformat().replace("+00:00", "Z")


def read_object(path: Path) -> dict:
    """Authenticate before parsing; no plaintext/unknown-schema fallback."""
    if path.is_symlink():
        raise ValueError("Archive objects must be regular files")
    obj = json.loads(gzip.decompress(_fernet(required=True).decrypt(path.read_bytes())))
    if not isinstance(obj, dict) or obj.get("schema_version") != SCHEMA:
        raise ValueError("Unsupported archive schema")
    return obj


def write_object(path: Path, obj: dict) -> dict:
    """Publish a fully written temporary inode without replacing an existing ID."""
    if obj.get("schema_version") != SCHEMA:
        raise ValueError("Unsupported archive schema")
    if path.exists():
        existing = read_object(path)
        if existing != obj:
            raise ValueError("Conflicting immutable archive object")
        return existing
    content = json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    encrypted = _fernet(required=True).encrypt(gzip.compress(content, mtime=0))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".archive-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encrypted)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)  # atomic create-only publication
        except FileExistsError:
            existing = read_object(path)
            if existing != obj:
                raise ValueError("Conflicting immutable archive object")
        stored = read_object(path)
        if stored != obj:
            raise ValueError("Archive readback mismatch")
        return stored
    finally:
        Path(temporary).unlink(missing_ok=True)


def network(stations: list[dict]) -> list[dict]:
    """Only station fields; do not serialize env, credentials or contacts."""
    rows = []
    for s in stations:
        sid = s["station_id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", sid):
            raise ValueError("Unsafe archive station ID")
        rows.append({k: s.get(k) for k in
                     ("station_id", "latitude", "longitude", "elevation_m")})
    if not rows or len({s["station_id"] for s in rows}) != len(rows):
        raise ValueError("Archive needs a nonempty unique station network")
    return sorted(rows, key=lambda s: s["station_id"])


class Capture:
    def __init__(self, root: Path, start_day: date, stations: list[dict], at: datetime,
                 revision: str | None = None, job_id: str | None = None,
                 not_before: datetime | None = None):
        self.root = Path(root)
        self.start_day = start_day
        self.not_before = utc(not_before) if not_before else Slot(start_day, "am").start
        if self.not_before.date() != start_day:
            raise ValueError("Archive start date and timestamp disagree")
        self.network = network(stations)
        self.slot = active_slot(at, start_day)
        if self.slot and self.slot.start < self.not_before:
            self.slot = None
        self.id = uuid.uuid4().hex
        self.started = stamp(at)
        self.revision, self.job_id = revision, job_id
        self.errors: list[str] = []
        self.received: list[str] = []
        self.late: list[str] = []
        self.closed: list[dict] = []
        write_object(self.root / ("policy" + SUFFIX), {
            "schema_version": SCHEMA, "provider": "yr", "policy_version": POLICY_VERSION,
            "start_date": start_day.isoformat(), "start_at": stamp(self.not_before),
            "key_reference": "WX_STATE_KEY"})
        if self.slot:
            if (self.slot_path(self.slot) / ("manifest" + SUFFIX)).exists():
                raise ValueError("Archive slot is already closed")
            path = self.slot_path(self.slot) / ("index" + SUFFIX)
            if not path.exists():
                write_object(path, {"schema_version": SCHEMA, "policy_version": POLICY_VERSION,
                                    **self.slot.record(), "stations": self.network})
            elif read_object(path)["stations"] != self.network:
                raise ValueError("Station network changed inside the archive slot")

    def slot_path(self, slot: Slot) -> Path:
        return self.root / slot.directory

    def station_path(self, slot: Slot, sid: str) -> Path:
        return self.slot_path(slot) / "yr" / (sid + SUFFIX)

    def sink(self, station: dict, body: bytes, metadata: dict) -> None:
        """Collector hook. A capture failure never stops scored-row extraction."""
        try:
            self._capture(station, body, metadata)
        except Exception:
            self.errors.append("Yr archive: response capture failed")

    def _capture(self, station: dict, body: bytes, metadata: dict) -> None:
        if not self.slot:
            return
        sid = station["station_id"]
        if sid not in {s["station_id"] for s in self.network}:
            raise ValueError("Station outside archive network")
        started = datetime.fromisoformat(metadata["request_started_at"].replace("Z", "+00:00"))
        received = datetime.fromisoformat(metadata["response_received_at"].replace("Z", "+00:00"))
        if received < started or not self.slot.contains(started) or not self.slot.contains(received):
            self.late.append(sid)
            return
        path = self.station_path(self.slot, sid)
        if path.exists():
            read_object(path)  # already selected: never replace with a fresher response
            return
        raw = body.decode("utf-8")
        payload = json.loads(raw)
        if not payload.get("properties", {}).get("timeseries"):
            raise ValueError("Missing Yr forecast timeseries")
        obj = {"schema_version": SCHEMA, "policy_version": POLICY_VERSION,
               **self.slot.record(), "acquisition_id": self.id + "-" + sid,
               "collector_revision": self.revision, "job_id": self.job_id,
               "collection_started_at": self.started, "station": next(s for s in self.network if s["station_id"] == sid),
               "request": {"endpoint": metadata["endpoint"],
                           "query": {k: metadata["query"][k] for k in ("lat", "lon")},
                           "request_started_at": metadata["request_started_at"],
                           "response_received_at": metadata["response_received_at"],
                           "status": metadata["status"],
                           "headers": {k.lower(): v for k, v in metadata["headers"].items() if k.lower() in SAFE_HEADERS}},
               "response_json": raw}
        write_object(path, obj)
        self.received.append(sid)

    def inventory(self, slot: Slot, expected: list[dict]) -> tuple[list[dict], list[str]]:
        records, missing = [], []
        for s in expected:
            sid = s["station_id"]
            path = self.station_path(slot, sid)
            if not path.exists():
                missing.append(sid)
                continue
            obj = read_object(path)
            if obj.get("station") != s or obj.get("slot_date") != slot.day.isoformat() or obj.get("slot") != slot.name:
                raise ValueError("Archive object identity mismatch")
            content = path.read_bytes()
            records.append({"station_id": sid, "object": path.relative_to(self.root).as_posix(),
                            "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        return records, missing

    def finish(self, at: datetime) -> dict:
        if self.slot:
            records, missing = self.inventory(self.slot, self.network)
            if missing:
                self.errors.append(f"Yr archive: {len(missing)} station(s) missing in active slot")
            write_object(self.slot_path(self.slot) / "attempts" / (self.id + SUFFIX), {
                "schema_version": SCHEMA, **self.slot.record(), "attempt_id": self.id,
                "collection_started_at": self.started, "finished_at": stamp(at),
                "new_station_ids": self.received, "late_station_ids": self.late,
                "missing_station_ids": missing, "objects": records,
                "capture_errors": len(self.errors)})
        for slot in closed_slots(self.start_day, at):
            if slot.start < self.not_before:
                continue
            path = self.slot_path(slot) / ("manifest" + SUFFIX)
            if path.exists():
                continue
            index = self.slot_path(slot) / ("index" + SUFFIX)
            expected = read_object(index)["stations"] if index.exists() else self.network
            records, missing = self.inventory(slot, expected)
            status = "partial" if records and missing else "missing" if missing else "complete"
            manifest = {"schema_version": SCHEMA, "policy_version": POLICY_VERSION,
                        **slot.record(), "recorded_at": stamp(at), "status": status,
                        "stations": expected, "network_known_during_slot": index.exists(),
                        "missing_station_ids": missing, "objects": records}
            write_object(path, manifest)
            self.closed.append(manifest)
        incomplete = sum(m["status"] != "complete" for m in self.closed)
        if incomplete:
            self.errors.append(f"Yr archive: {incomplete} closed slot(s) incomplete")
        return {"enabled": True, "status": "error" if self.errors else "partial" if self.late else "ok" if self.received or self.closed else "idle",
                "captured_stations": len(self.received), "closed_slots": len(self.closed),
                "incomplete_slots": incomplete, "errors": len(self.errors)}
