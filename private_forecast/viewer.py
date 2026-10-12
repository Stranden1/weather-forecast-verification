"""Serve future forecasts on loopback only, without exporting them to disk.

This viewer reads an already fetched Git state ref. It never collects forecasts,
writes state/history, or serves the project directory or credentials.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import subprocess
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

from cloud.config import ROOT, WN_ACCESS_NOTE, WN_REALTIME_NOTICE, load_stations
from cloud.store import plaintext_bytes
from cloud.summarize import display_name

ASSETS = Path(__file__).parent / "static"
FIELDS = ("t", "t_p10", "t_p90", "w", "w_p10", "w_p90", "p",
          "p_p50", "p_p90", "p_prob")


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def timestamp(value):
    dt = pd.to_datetime(value, utc=True, errors="coerce")
    return None if pd.isna(dt) else dt.to_pydatetime()


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z") if dt else None


def snapshot(frame, stations, now=None, revision=""):
    """Latest shared fetch, retaining provider gaps and original issue times.

    Do not stitch older snapshots into a smooth future forecast. Precipitation
    timestamps remain interval ends, and WeatherNext's displayed rain is p50.
    """
    now = now or datetime.now(timezone.utc)
    required = {"provider", "station", "fetched_at", "issued_at", "target"}
    if not required.issubset(frame.columns):
        raise ValueError("Pending state is missing forecast identity columns")
    d = frame.copy()
    active = {s["station_id"] for s in stations}
    d = d[d.station.isin(active) & d.provider.isin(["yr", "wn"])]
    for col in ("fetched_at", "issued_at", "target"):
        d[col] = pd.to_datetime(d[col], utc=True, errors="coerce")
    d = d.dropna(subset=["fetched_at", "target"])
    groups = d.groupby("fetched_at").provider.agg(set)
    shared = groups[groups.apply(lambda providers: {"yr", "wn"}.issubset(providers))]
    if shared.empty:
        raise ValueError("No shared Yr / WeatherNext collection exists in pending state")
    fetched = shared.index.max().to_pydatetime()
    d = d[(d.fetched_at == fetched) & (d.target > now)
          & (d.target <= now + timedelta(hours=48))]
    if d.duplicated(["provider", "station", "target"]).any():
        raise ValueError("Pending state has ambiguous duplicate provider targets")
    for col in FIELDS:
        if col not in d:
            d[col] = None
    out = []
    for s in sorted(stations, key=lambda s: display_name(s["name"]).casefold()):
        local = d[d.station == s["station_id"]]
        points = {}
        for row in local.to_dict("records"):
            key = iso(timestamp(row["target"]))
            points.setdefault(key, {"time": key})[row["provider"]] = {
                "issued": iso(timestamp(row["issued_at"])),
                **{col: number(row[col]) for col in FIELDS},
            }
        out.append({"id": s["station_id"], "name": display_name(s["name"]),
                    "points": [points[k] for k in sorted(points)]})
    return {"loaded": iso(now), "collected": iso(fetched), "revision": revision,
            "window_end": iso(now + timedelta(hours=48)), "stations": out,
            "notices": ["Forecasts from MET Norway (Yr), licensed CC BY 4.0.",
                        WN_ACCESS_NOTE, WN_REALTIME_NOTICE]}


def load_snapshot(ref="origin/state"):
    # Resolve to a commit before reading, so a concurrent fetch cannot mix refs.
    revision = subprocess.check_output(
        ["git", "rev-parse", "--verify", ref + "^{commit}"], cwd=ROOT).decode().strip()
    raw = subprocess.check_output(
        ["git", "show", revision + ":pending.csv.gz"], cwd=ROOT)
    frame = pd.read_csv(io.BytesIO(plaintext_bytes(raw)), compression="gzip",
                        dtype={"station": str, "provider": str})
    return snapshot(frame, load_stations(), revision=revision)


def make_server(loader, port=8765):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; "
                             "script-src 'self'; style-src 'self'; img-src 'self' data:; "
                             "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            super().end_headers()

        def do_GET(self):
            host = self.headers.get("Host", "")
            allowed = {f"127.0.0.1:{self.server.server_port}",
                       f"localhost:{self.server.server_port}"}
            if host not in allowed:
                self.send_error(403, "Local host required")
                return
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + host:
                self.send_error(403, "Local origin required")
                return
            path = urlsplit(self.path).path
            if path == "/api/forecasts":
                try:
                    body = json.dumps(loader(), allow_nan=False).encode("utf-8")
                except Exception:
                    # Decryption/process exceptions must never reach the browser.
                    self.send_error(503, "Cannot read cloud state; check the local key and fetched state ref")
                    return
                kind = "application/json; charset=utf-8"
            elif path in ("/", "/index.html", "/app.js", "/style.css"):
                name = "index.html" if path == "/" else path[1:]
                body = (ASSETS / name).read_bytes()
                kind = {"index.html": "text/html", "app.js": "text/javascript",
                        "style.css": "text/css"}[name] + "; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--state-ref", default="origin/state")
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    loader = lambda: load_snapshot(args.state_ref)
    try:
        initial = loader()
        server = make_server(loader, args.port)
    except Exception:
        parser.exit(1, "Cannot start: check the fetched state ref, .env key and local port.\n")
    print(f"Private forecast comparison: http://127.0.0.1:{server.server_port}")
    print(f"Cloud snapshot: {initial['collected']}. No network fetch or collection is performed.")
    print("Keep this viewer private. Stop with Ctrl+C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
