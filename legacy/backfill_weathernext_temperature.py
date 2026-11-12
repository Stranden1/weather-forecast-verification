"""Focused historical WeatherNext temperature backfill. Dry run unless --save.

The plan maps original UTC initialization timestamps to forecast-hour lists.
Reuse operational normalization and atomic/idempotent inserts. Never rewrite
retrieved_at to simulate historical local collection. No dashboard/scorer changes.
"""
from __future__ import annotations

from contextlib import closing
import argparse
import json
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import database
from collectors import weathernext as wn

METRIC = 'air_temperature'


def active_locations():
    with closing(sqlite3.connect(database.DB_PATH.resolve().as_uri()+'?mode=ro', uri=True)) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute('SELECT * FROM locations WHERE active=1 ORDER BY id')]


def validate_plan(plan):
    if not plan:
        raise ValueError('Empty backfill plan')
    result = {}
    for issued, hours in plan.items():
        normalized = wn.iso(issued)
        init = wn.utc(normalized)
        if init.hour % 6 or init.minute or init.second:
            raise ValueError('Historical long-range backfill requires a synoptic initialization')
        if not hours or any(type(h) is not int or not 1 <= h <= 360 for h in hours):
            raise ValueError('Invalid planned forecast hours')
        if normalized in result:
            raise ValueError('Duplicate initialization in plan')
        result[normalized] = sorted(set(hours))
    return dict(sorted(result.items()))


def image_metadata(source, issued, hours):
    ee = source.ee
    images = (ee.ImageCollection(wn.FIELDS[METRIC][0])
              .filter(ee.Filter.eq('start_time', issued))
              .filter(ee.Filter.inList('forecast_hour', hours)))
    fields = ['start_time', 'end_time', 'forecast_hour', 'ingestion_time_utc', 'system:index']
    return images.toList(len(hours)+1).map(lambda im: ee.Image(im).toDictionary(fields)).getInfo()


def validate_metadata(issued, hours, metadata):
    if len(metadata) != len(hours) or {m['forecast_hour'] for m in metadata} != set(hours):
        raise ValueError(f'Missing or duplicate historical images: {issued}; requested {hours}')
    for row in metadata:
        valid = wn.utc(row['end_time'])
        if wn.iso(row['start_time']) != issued or (valid-wn.utc(issued)).total_seconds()/3600 != row['forecast_hour']:
            raise ValueError(f'Historical image timestamp mismatch: {issued}')
        ingestion = row.get('ingestion_time_utc')
        # Epoch seconds according to Earth Engine. Retain original property too.
        if ingestion is None or not wn.utc(issued).timestamp() <= float(ingestion) <= valid.timestamp():
            raise ValueError(f'Historical image not demonstrably available before valid time: {issued}, {row["forecast_hour"]}')


def backfill(plan, source, write=False, metadata_loader=image_metadata, progress=None, checkpoint=None):
    plan = validate_plan(plan)
    locations = active_locations()
    if not locations:
        raise ValueError('No active stations')
    by_id = {l['id']: l for l in locations}
    metadata = {}
    # Validate every planned image before production writes begin.
    for issued, hours in plan.items():
        metadata[issued] = metadata_loader(source, issued, hours)
        validate_metadata(issued, hours, metadata[issued])
        if progress:
            progress(f'Preflight {issued}: {len(hours)} historical images available before valid time')
    report = {'started_at': database.utc_now_iso(), 'dry_run': not write,
              'station_ids': [l['station_id'] for l in locations],
              'coordinates': [{k:l[k] for k in ['id','station_id','latitude','longitude']} for l in locations],
              'plan': plan, 'image_metadata': metadata, 'completed_runs': [],
              'sample_values_added': 0, 'sampled_points': 0}
    def record():
        if checkpoint:
            path = Path(checkpoint)
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
            temporary.replace(path)
    record()
    for issued, hours in plan.items():
        added = 0
        for start in range(0,len(hours),12):
            selected = hours[start:start+12]
            for offset in range(0,len(locations),50):
                batch = locations[offset:offset+50]
                rows = source.sample_batch(wn.FIELDS[METRIC][0], [METRIC], issued, selected, batch)
                expected = {(l['id'],h) for l in batch for h in selected}
                if len(rows)!=len(expected) or {(r['location_id'],r['forecast_hour']) for r in rows}!=expected:
                    raise ValueError(f'Incomplete station/hour coverage: {issued}')
                samples = [wn.normalize(row,METRIC,issued,row['asset_id'],by_id[row['location_id']]) for row in rows]
                expected_assets = {m['forecast_hour']:m['system:index'] for m in metadata[issued]}
                if any(row['asset_id'].split('/')[-1]!=expected_assets[row['forecast_hour']] for row in rows):
                    raise ValueError('Sample asset does not match preflight metadata')
                if write:
                    added += wn.save_samples(samples)
                report['sampled_points'] += len(samples)
        report['sample_values_added'] += added
        report['completed_runs'].append(issued)
        record()
        if progress:
            progress(f'Saved {issued}: {len(hours)*len(locations)} points sampled; {added} statistic values added')
    report['finished_at'] = database.utc_now_iso()
    if write:
        from weathernext_history import register_verified_history
        report['verification'] = register_verified_history(report)
    record()
    return report


def main():
    load_dotenv(Path(__file__).resolve().parent/'.env')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--save', action='store_true')
    parser.add_argument('--report', required=True, help='Local JSON checkpoint/output path')
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
    source = wn.EarthEngineSource(os.environ.get('EARTH_ENGINE_PROJECT','weatherapp-508323'))
    result = backfill(plan, source, args.save, progress=lambda x:print(x,flush=True), checkpoint=args.report)
    print(json.dumps({k:result[k] for k in ['dry_run','sampled_points','sample_values_added','finished_at']},indent=2))


if __name__=='__main__':
    main()
