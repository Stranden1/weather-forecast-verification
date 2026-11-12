"""Opt-in WeatherNext collector; no authentication or network work on import."""
from __future__ import annotations

import math
import os
from datetime import datetime, timezone, timedelta

from database import connect, utc_now_iso

PROVIDER = 'WeatherNext3-mean'
PREFIX = 'projects/gcp-public-data-weathernext/assets/weathernext_3_0_0_'
STATS = ('mean', 'p10', 'p25', 'p50', 'p75', 'p90')
# Bilinear interpolation on the native grid at the station point, read at this small scale.
# The earlier scale=5000/10000 made Earth Engine resample first and could return a
# neighbouring cell (DECISIONS.md, 2026-09-26; cloud.config.LOCAL_BILINEAR_SINCE).
POINT_SCALE_M = 100
FIELDS = {
    'air_temperature': (PREFIX + '0p05deg', 'station_head_temperature_2m', POINT_SCALE_M),
    'wind_speed': (PREFIX + '0p1deg', 'wind_speed_10m', POINT_SCALE_M),
    'precipitation_1h': (PREFIX + '0p1deg', 'total_precipitation_1hr', POINT_SCALE_M),
    'wind_u': (PREFIX + '0p1deg', 'u_component_of_wind_10m', POINT_SCALE_M),
    'wind_v': (PREFIX + '0p1deg', 'v_component_of_wind_10m', POINT_SCALE_M),
    'air_pressure_at_sea_level': (PREFIX + '0p1deg', 'mean_sea_level_pressure', POINT_SCALE_M),
}
METRIC_STATS = {m: STATS if m in ('air_temperature','wind_speed','precipitation_1h') else ('mean',) for m in FIELDS}
UNITS = {'air_temperature':'degC','wind_speed':'m/s','precipitation_1h':'mm',
         'wind_u':'m/s','wind_v':'m/s','air_pressure_at_sea_level':'hPa'}
SCHEMA = '''CREATE TABLE IF NOT EXISTS weathernext_samples (
    run_id INTEGER NOT NULL REFERENCES forecast_runs(id),
    valid_at TEXT NOT NULL,
    metric TEXT NOT NULL,
    statistic TEXT NOT NULL,
    value REAL NOT NULL,
    asset_id TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    retrieved_at TEXT NOT NULL,
    unit TEXT NOT NULL,
    PRIMARY KEY(run_id, valid_at, metric, statistic)
)'''


def migrate(con):
    con.execute(SCHEMA)
    con.execute("""CREATE INDEX IF NOT EXISTS idx_weathernext_rain_valid
        ON weathernext_samples(julianday(valid_at),run_id)
        WHERE metric='precipitation_1h' AND statistic='mean' AND unit='mm'""")
    # Additive upgrade if the early trial schema was already installed.
    columns = {r[1] for r in con.execute('PRAGMA table_info(weathernext_samples)')}
    if 'unit' not in columns:
        con.execute('ALTER TABLE weathernext_samples ADD COLUMN unit TEXT')
        for metric,unit in UNITS.items():
            con.execute('UPDATE weathernext_samples SET unit=? WHERE metric=? AND unit IS NULL',(unit,metric))
    con.execute('''CREATE VIEW IF NOT EXISTS weathernext_values AS
        SELECT r.provider,l.station_id,r.issued_at AS init_time,s.valid_at AS valid_time,
               f.lead_hours,s.metric AS variable,s.statistic,s.value,s.unit,s.asset_id,
               s.latitude,s.longitude,s.retrieved_at
        FROM weathernext_samples s JOIN forecast_runs r ON r.id=s.run_id
        JOIN locations l ON l.id=r.location_id
        JOIN forecasts f ON f.run_id=s.run_id AND f.valid_at=s.valid_at''')


def wind_direction(u, v):
    """Meteorological FROM direction of the mean vector; calm is undefined."""
    return None if math.hypot(u,v) < 1e-6 else math.degrees(math.atan2(-u,-v)) % 360


def utc(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamp must include a UTC offset')
    return dt.astimezone(timezone.utc)


def iso(value):
    return utc(value).isoformat(timespec='seconds').replace('+00:00', 'Z')


def normalize(properties, metric, issued_at, asset_id, location):
    """Validate each sample before any database write; missing pixels stay missing."""
    issued, valid = utc(issued_at), utc(properties['end_time'])
    lead = (valid-issued).total_seconds()/3600
    if iso(properties['start_time']) != iso(issued_at):
        raise ValueError('Mixed forecast initializations')
    if lead != int(properties['forecast_hour']) or not 1 <= lead <= 360:
        raise ValueError('Invalid forecast lead time')
    if issued.hour % 6 and lead > 48:
        raise ValueError('Interim run exceeds 48 hours')
    _, band, _ = FIELDS[metric]
    values = {}
    for stat in METRIC_STATS[metric]:
        raw = properties.get(band+'_'+stat)
        if raw is None:
            continue
        value = float(raw)
        if not math.isfinite(value) or (metric in ('wind_speed','precipitation_1h') and value < 0):
            raise ValueError('Invalid weather value')
        values[stat] = (value-273.15 if metric == 'air_temperature' else
                        value*1000 if metric == 'precipitation_1h' else
                        value/100 if metric == 'air_pressure_at_sea_level' else value)
    if set(values) != set(METRIC_STATS[metric]):
        raise ValueError(f'Missing {metric} statistics at {location["id"]}, {valid}')
    percentiles = [values[s] for s in STATS[1:] if s in values]
    if percentiles != sorted(percentiles):
        raise ValueError(f'Unordered percentiles: {metric}')
    return dict(location_id=location['id'], latitude=location['latitude'],
                longitude=location['longitude'], issued_at=iso(issued_at),
                valid_at=iso(properties['end_time']), lead_hours=lead,
                metric=metric, values=values, asset_id=asset_id)


def save_samples(samples):
    """One atomic batch. Retries fill missing metrics, never replace history."""
    now = utc_now_iso()
    with connect() as con:
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('BEGIN IMMEDIATE')
        migrate(con)
        added = 0
        for row in samples:
            metric = row['metric']
            if metric not in FIELDS:
                raise ValueError('Unsupported metric')
            con.execute('INSERT OR IGNORE INTO forecast_runs(provider,location_id,issued_at,retrieved_at) VALUES (?,?,?,?)',
                        (PROVIDER,row['location_id'],row['issued_at'],now))
            run_id = con.execute('SELECT id FROM forecast_runs WHERE provider=? AND location_id=? AND issued_at=?',
                                 (PROVIDER,row['location_id'],row['issued_at'])).fetchone()[0]
            for stat,value in row['values'].items():
                cur = con.execute('''INSERT OR IGNORE INTO weathernext_samples
                    (run_id,valid_at,metric,statistic,value,asset_id,latitude,longitude,retrieved_at,unit)
                    VALUES (?,?,?,?,?,?,?,?,?,?)''',
                    (run_id,row['valid_at'],metric,stat,value,row['asset_id'],row['latitude'],row['longitude'],now,UNITS[metric]))
                added += cur.rowcount
            con.execute('INSERT OR IGNORE INTO forecasts(run_id,valid_at,lead_hours) VALUES (?,?,?)',
                        (run_id,row['valid_at'],row['lead_hours']))
            if metric in ('air_temperature','wind_speed'):
                con.execute(f'UPDATE forecasts SET {metric}=COALESCE({metric},?) WHERE run_id=? AND valid_at=?',
                            (row['values']['mean'],run_id,row['valid_at']))
            # MET precipitation is forward-looking at valid_at. WeatherNext's 1hr
            # accumulation remains explicit in the normalized table until interval
            # alignment is validated; do not silently put it in MET's time slot.
    return added


class EarthEngineSource:
    def __init__(self, project):
        if not project:
            raise ValueError('Set EARTH_ENGINE_PROJECT first')
        try:
            import ee
        except ImportError as exc:
            raise RuntimeError('Install earthengine-api in the existing .venv first') from exc
        ee.Initialize(project=project)
        ee.data.setDeadline(120000)
        self.ee = ee

    def latest_run(self, hours=360):
        # Search recent synoptic runs, verifying BOTH collections before choosing.
        now = datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
        now -= timedelta(hours=now.hour % 6)
        for n in range(12):
            candidate = (now-timedelta(hours=6*n)).isoformat().replace('+00:00','Z')
            if all(set(range(1,hours+1)).issubset(self.hours(c,candidate))
                   for c in {f[0] for f in FIELDS.values()}):
                return candidate
        raise RuntimeError('No complete synoptic run found in the past 72 hours')

    def sample_batch(self, collection, metrics, issued_at, hours, locations):
        ee = self.ee
        bands = [FIELDS[m][1]+'_'+s for m in metrics for s in METRIC_STATS[m]]
        scale = FIELDS[metrics[0]][2]
        points = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([l['longitude'],l['latitude']]),
            {'location_id':l['id']}) for l in locations])
        images = (ee.ImageCollection(collection).filter(ee.Filter.eq('start_time',issued_at))
            .filter(ee.Filter.inList('forecast_hour',hours)).filterBounds(points.geometry()).select(bands))
        def reduce(image):
            image=ee.Image(image)
            result=image.resample('bilinear').reduceRegions(collection=points,reducer=ee.Reducer.first(),scale=scale,tileScale=4)
            return result.map(lambda feature: ee.Feature(None,feature.toDictionary()).set({
                'start_time':image.get('start_time'),'end_time':image.get('end_time'),
                'forecast_hour':image.get('forecast_hour'),'asset_id':image.id()}))
        # List.map explicitly permits returning feature collections.
        result=ee.FeatureCollection(images.toList(len(hours)).map(reduce)).flatten()
        try:
            return [f['properties'] for f in result.getInfo()['features']]
        except Exception as exc:
            if 'memory' not in str(exc).lower():
                raise
            # Keep the query bounded when an upstream image is unusually expensive.
            if len(hours)>1:
                middle=len(hours)//2
                return (self.sample_batch(collection,metrics,issued_at,hours[:middle],locations)+
                        self.sample_batch(collection,metrics,issued_at,hours[middle:],locations))
            if len(locations)>1:
                middle=len(locations)//2
                return (self.sample_batch(collection,metrics,issued_at,hours,locations[:middle])+
                        self.sample_batch(collection,metrics,issued_at,hours,locations[middle:]))
            raise

    def hours(self, collection, issued_at):
        ee = self.ee
        return (ee.ImageCollection(collection).filter(ee.Filter.eq('start_time', issued_at))
                .aggregate_array('forecast_hour').getInfo())

    def sample(self, collection, band, scale, issued_at, hour, locations):
        ee = self.ee
        filtered = (ee.ImageCollection(collection)
                    .filter(ee.Filter.eq('start_time',issued_at))
                    .filter(ee.Filter.eq('forecast_hour',hour)))
        image = ee.Image(filtered.first()).select([band+'_'+s for s in STATS])
        points = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([l['longitude'],l['latitude']]),
                                                 {'location_id':l['id']}) for l in locations])
        reduced = image.resample('bilinear').reduceRegions(collection=points,reducer=ee.Reducer.first(),scale=scale,tileScale=4)
        def metadata(feature):
            return feature.set({'start_time':image.get('start_time'), 'end_time':image.get('end_time'),
                                'forecast_hour':image.get('forecast_hour'), 'asset_id':image.id()})
        return [f['properties'] for f in reduced.map(metadata).getInfo()['features']]


def collect(project, issued_at=None, hours=1, station_limit=1, write=False, source=None,
            station_ids=None, metrics=None, progress=None, time_batch=12):
    """Explicit run, bounded point batches, dry run by default. No global reduction."""
    metrics = tuple(metrics or FIELDS)
    if not set(metrics).issubset(FIELDS) or not 1 <= time_batch <= 24:
        raise ValueError('Invalid metrics or time batch')
    source = source or EarthEngineSource(project)
    issued_at = iso(issued_at or source.latest_run(hours))
    if not 1 <= hours <= (48 if utc(issued_at).hour % 6 else 360):
        raise ValueError('Invalid forecast horizon for this initialization')
    if station_limit is not None and not 1 <= station_limit <= 200:
        raise ValueError('Station limit must be 1..200')
    with connect() as con:
        locations = [dict(r) for r in con.execute('SELECT * FROM locations WHERE active=1 ORDER BY id')]
    if station_ids:
        locations = [l for l in locations if l['station_id'] in station_ids]
        if {l['station_id'] for l in locations} != set(station_ids):
            raise ValueError('Requested station is not active or does not exist')
    locations = locations[:station_limit] if station_limit else locations
    if not locations:
        raise ValueError('No active stations in this database')
    for collection in {FIELDS[m][0] for m in metrics}:
        available = set(source.hours(collection,issued_at))
        missing = set(range(1,hours+1))-available
        if missing:
            raise ValueError(f'Run incomplete in {collection}: missing {len(missing)} requested hours')
    report = dict(issued_at=issued_at, locations=len(locations), hours=hours,
                  sample_values_added=0, batches=0, dry_run=not write, preview=[])
    if hasattr(source,'sample_batch'):
        for start in range(1,hours+1,time_batch):
            selected_hours=list(range(start,min(start+time_batch,hours+1)))
            for offset in range(0,len(locations),50):
                batch=locations[offset:offset+50]
                by_id={l['id']:l for l in batch}
                samples=[]
                for collection in sorted({FIELDS[m][0] for m in metrics}):
                    selected_metrics=[m for m in metrics if FIELDS[m][0]==collection]
                    rows=source.sample_batch(collection,selected_metrics,issued_at,selected_hours,batch)
                    expected={(l['id'],h) for l in batch for h in selected_hours}
                    if len(rows)!=len(expected) or {(r['location_id'],r['forecast_hour']) for r in rows}!=expected:
                        raise ValueError('Incomplete station/hour coverage')
                    for row in rows:
                        for metric in selected_metrics:
                            samples.append(normalize(row,metric,issued_at,row['asset_id'],by_id[row['location_id']]))
                if not report['preview']:
                    report['preview']=samples[:len(metrics)]
                if write:
                    report['sample_values_added']+=save_samples(samples)
                report['batches']+=1
                if progress:
                    progress(f"WeatherNext {issued_at}: hours {selected_hours[0]}–{selected_hours[-1]}, {len(batch)} stations; added {report['sample_values_added']} values")
        return report
    for hour in range(1,hours+1):
        for offset in range(0,len(locations),10):
            batch = locations[offset:offset+10]
            by_id = {l['id']:l for l in batch}
            samples = []
            for metric in metrics:
                collection,band,scale = FIELDS[metric]
                rows = source.sample(collection,band,scale,issued_at,hour,batch)
                if len(rows) != len(batch) or {r['location_id'] for r in rows} != set(by_id):
                    raise ValueError('Earth Engine returned incomplete station coverage')
                for row in rows:
                    if int(row['forecast_hour']) != hour:
                        raise ValueError('Unexpected forecast hour')
                    samples.append(normalize(row,metric,issued_at,row['asset_id'],by_id[row['location_id']]))
            if not report['preview']:
                report['preview'] = samples[:2]
            if write:
                report['sample_values_added'] += save_samples(samples)
            report['batches'] += 1
    return report


def collect_all(progress=None):
    return collect(os.getenv('EARTH_ENGINE_PROJECT','weatherapp-508323'),hours=360,
                   station_limit=None,write=True,progress=progress)
