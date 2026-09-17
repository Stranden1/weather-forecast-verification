"""Persist verified archive availability alongside existing WeatherNext forecasts.

Only temperature means with matching stored provenance are certified. This never
changes forecast values, original timestamps, or local retrieval timestamps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import database
from collectors import weathernext as wn

SCHEMA = '''CREATE TABLE IF NOT EXISTS weathernext_verified_history (
    run_id INTEGER NOT NULL,
    valid_at TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    lead_hours REAL NOT NULL,
    source_collection TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    mean_value REAL NOT NULL,
    original_available_at TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    PRIMARY KEY (run_id, valid_at),
    FOREIGN KEY (run_id, valid_at) REFERENCES forecasts(run_id, valid_at)
)'''


def register_verified_history(manifest):
    """Atomically validate/register a completed backfill manifest; safe to repeat."""
    from backfill_weathernext_temperature import validate_plan, validate_metadata

    plan = validate_plan(manifest['plan'])
    if manifest.get('dry_run') is not False or not manifest.get('finished_at'):
        raise ValueError('A completed saved backfill is required')
    if set(manifest['completed_runs']) != set(plan):
        raise ValueError('Incomplete backfill manifest')
    coordinates = manifest['coordinates']
    station_ids = [row['station_id'] for row in coordinates]
    if not coordinates or len(set(station_ids)) != len(station_ids) or set(station_ids) != set(manifest['station_ids']):
        raise ValueError('Invalid station coverage in manifest')
    if len({row['id'] for row in coordinates}) != len(coordinates):
        raise ValueError('Duplicate station location IDs')
    for issued, hours in plan.items():
        validate_metadata(issued, hours, manifest['image_metadata'][issued])
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    verified_at = database.utc_now_iso()
    collection = wn.FIELDS['air_temperature'][0]
    with database.connect() as con:
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('BEGIN IMMEDIATE')
        records = []
        for issued in plan:
            for image in manifest['image_metadata'][issued]:
                valid = wn.iso(image['end_time'])
                available = datetime.fromtimestamp(float(image['ingestion_time_utc']), timezone.utc).isoformat()
                for location in coordinates:
                    row = con.execute('''
                        SELECT r.id, r.issued_at, f.valid_at, f.lead_hours,
                               f.air_temperature, s.value, s.asset_id,
                               s.latitude, s.longitude, s.unit, l.station_id
                        FROM forecast_runs r JOIN forecasts f ON f.run_id=r.id
                        JOIN locations l ON l.id=r.location_id
                        JOIN weathernext_samples s ON s.run_id=f.run_id AND s.valid_at=f.valid_at
                        WHERE r.provider=? AND r.location_id=? AND r.issued_at=?
                          AND f.valid_at=? AND s.metric='air_temperature' AND s.statistic='mean'
                    ''', (wn.PROVIDER, location['id'], issued, valid)).fetchone()
                    if row is None:
                        raise ValueError(f'Missing stored temperature point: {issued}, {valid}, {location["id"]}')
                    asset = row['asset_id']
                    expected_asset = image['system:index']
                    if asset not in (expected_asset, collection + '/' + expected_asset):
                        raise ValueError('Stored asset differs from verified temperature image')
                    if (row['lead_hours'] != image['forecast_hour'] or row['unit'] != 'degC'
                            or row['air_temperature'] != row['value'] or not math.isfinite(row['value'])
                            or row['station_id'] != location['station_id']
                            or abs(row['latitude'] - location['latitude']) > 1e-8
                            or abs(row['longitude'] - location['longitude']) > 1e-8):
                        raise ValueError('Stored station, lead, units or mean differs from backfill evidence')
                    records.append((row['id'], valid, issued, row['lead_hours'], collection,
                                    asset, row['value'], available, verified_at, digest))
        # Validate the whole manifest before even adding the table.
        con.execute(SCHEMA)
        added = 0
        for record in records:
            prior = con.execute('SELECT * FROM weathernext_verified_history WHERE run_id=? AND valid_at=?', record[:2]).fetchone()
            if prior is not None and tuple(prior)[:8] != record[:8]:
                raise ValueError('Conflicting historical verification; existing evidence was preserved')
            added += con.execute('INSERT OR IGNORE INTO weathernext_verified_history VALUES (?,?,?,?,?,?,?,?,?,?)', record).rowcount
    return {'verified_points': len(records), 'added': added}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    args = parser.parse_args()
    print(json.dumps(register_verified_history(json.loads(Path(args.manifest).read_text(encoding='utf-8')))))
