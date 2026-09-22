"""Hourly precipitation adapters and metrics; database reads only.

Canonical target T is the end of [T-1h,T). Never apply instantaneous-variable
joins to raw MET valid_at. Pair ordering comes from the shared operational matcher.
"""
import numpy as np
import pandas as pd

METRIC = 'precipitation_1h'
WET_THRESHOLD = 0.1  # mm in a physical one-hour interval; wet is strictly greater.
BANDS = [0, 12, 24, 48, 72]
LABELS = ['0–12h', '12–24h', '24–48h', '48–72h']
DRY_CONTEXT = ('Most observed hours are dry, so all-hour MAE can reward forecasts that '
               'predict little rain. Wet-hour and event metrics provide important additional context.')


def valid_amount(values):
    values = pd.to_numeric(values, errors='coerce')
    return np.isfinite(values) & (values >= 0)


def load_rows(con, start=None, end=None, location_id=None, run_ids=None):
    """Read MET next-hour amounts and WeatherNext normalized means as end targets.

    Sample retrieval (not run retrieval) controls WeatherNext availability. A
    malformed lead, off-hour target, wrong unit or invalid amount fails closed.
    """
    frames = []
    for provider in ['MET', 'WeatherNext3-mean']:
        met = provider == 'MET'
        table = 'forecasts f' if met else 'weathernext_samples s JOIN forecasts f ON f.run_id=s.run_id AND f.valid_at=s.valid_at'
        value = 'f.precipitation_1h' if met else 's.value'
        retrieved = 'r.retrieved_at' if met else 's.retrieved_at'
        target = "julianday(f.valid_at, '+1 hour')" if met else 'julianday(f.valid_at)'
        where = ['l.active=1', 'r.provider=?', f'{value} IS NOT NULL']
        params = [provider]
        if not met:
            where += ["s.metric='precipitation_1h'", "s.statistic='mean'", "s.unit='mm'"]
        for op, bound in [('>=', start), ('<=', end)]:
            if bound is not None:
                where.append(f'({target}) {op} julianday(?)')
                params.append(pd.Timestamp(bound).isoformat())
        if location_id is not None:
            where.append('r.location_id=?'); params.append(location_id)
        if run_ids is not None:
            where.append('r.id IN (' + ','.join('?' for _ in run_ids) + ')')
            params.extend(run_ids)
        frame = pd.read_sql_query(f'''
            SELECT r.location_id,l.station_id,COALESCE(l.station_name,l.name) station,
                   r.id run_id,r.provider,r.issued_at,{retrieved} retrieved_at,
                   f.valid_at stored_time,f.lead_hours stored_lead,{value} value
            FROM {table} JOIN forecast_runs r ON r.id=f.run_id
            JOIN locations l ON l.id=r.location_id WHERE {' AND '.join(where)}
        ''', con, params=params)
        for col in ['stored_time', 'issued_at', 'retrieved_at']:
            frame[col] = pd.to_datetime(frame[col], utc=True, format='mixed', errors='coerce')
        frame['valid_at'] = frame.stored_time + pd.Timedelta(hours=1 if met else 0)
        frame['lead_hours'] = (frame.valid_at-frame.issued_at).dt.total_seconds()/3600
        native_lead = (frame.stored_time-frame.issued_at).dt.total_seconds()/3600
        frame = frame[valid_amount(frame.value) & (frame.valid_at == frame.valid_at.dt.floor('h'))
                      & ((native_lead-frame.stored_lead).abs() < 1e-7)]
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def pair_rows(rows, now=None, deduplicate=True):
    """One canonical fair policy for overall, selected-run and automatic pairing."""
    from dashboard_scores import pair_forecasts
    start = rows.valid_at-pd.Timedelta(hours=1)
    rows = rows[valid_amount(rows.value) & (rows.issued_at < start)
                & (rows.retrieved_at < start) & (rows.lead_hours >= 0)
                & (rows.valid_at == rows.valid_at.dt.floor('h'))]
    pairs = pair_forecasts(rows, now, deduplicate=False)
    met_bucket = pd.cut(pairs.met_lead_hours, BANDS, labels=LABELS, right=False)
    wn_bucket = pd.cut(pairs.wn_lead_hours, BANDS, labels=LABELS, right=False)
    pairs = pairs[(met_bucket == wn_bucket) & met_bucket.notna()].copy()
    pairs['horizon'] = met_bucket.loc[pairs.index]
    if deduplicate:
        pairs = pairs.drop_duplicates(['location_id', 'valid_at', 'horizon'])
    return pairs.reset_index(drop=True)


def clean_observed_pairs(pairs):
    return pairs[valid_amount(pairs.actual_value)
                 & (pairs.valid_at == pairs.valid_at.dt.floor('h'))].copy()


def load_timeline(con, location_id, met_run_id, wn_run_id):
    """Inspection timeline; fairness is applied separately to shared summaries."""
    rows = load_rows(con, location_id=location_id, run_ids=[met_run_id, wn_run_id])
    frames = []
    for prefix, run_id, provider in [('met', met_run_id, 'MET'), ('wn', wn_run_id, 'WeatherNext3-mean')]:
        fields = ['valid_at', 'lead_hours', 'value', 'retrieved_at']
        frame = rows[(rows.run_id == run_id) & (rows.provider == provider)][fields]
        frames.append(frame.rename(columns={c: prefix+'_'+c for c in fields if c != 'valid_at'}))
    timeline = frames[0].merge(frames[1], on='valid_at', how='outer')
    observed = pd.read_sql_query('''SELECT observed_at valid_at,precipitation_1h actual_value
        FROM observations WHERE location_id=? AND precipitation_1h IS NOT NULL''', con, params=(location_id,))
    observed.valid_at = pd.to_datetime(observed.valid_at, utc=True, format='mixed', errors='coerce')
    grouped = observed.groupby('valid_at').actual_value.agg(['min', 'max']).reset_index()
    observed = grouped[grouped['min'] == grouped['max']].rename(columns={'min':'actual_value'})
    observed = clean_observed_pairs(observed)
    timeline = timeline.merge(observed[['valid_at','actual_value']], on='valid_at', how='left')
    # Rainfall uncertainty is deliberately omitted; the three interval-aligned amounts suffice.
    timeline['wn_p10'] = float('nan'); timeline['wn_p90'] = float('nan')
    return timeline.sort_values('valid_at').reset_index(drop=True)


def selected_pairs(timeline, met_run, wn_run, now):
    frames = []
    for prefix, provider, run in [('met','MET',met_run), ('wn','WeatherNext3-mean',wn_run)]:
        fields = ['valid_at',prefix+'_lead_hours',prefix+'_value',prefix+'_retrieved_at']
        frame = timeline[fields].rename(columns={prefix+'_'+c:c for c in ['lead_hours','value','retrieved_at']}).dropna()
        frame = frame.assign(run_id=run['id'],provider=provider,issued_at=pd.Timestamp(run['issued_at']),
                             location_id=0,station_id='',station='')
        frames.append(frame)
    pairs = pair_rows(pd.concat(frames, ignore_index=True), now)
    observed = timeline[(timeline.valid_at <= now) & timeline.actual_value.notna()]
    pairs = clean_observed_pairs(pairs.merge(observed[['valid_at','actual_value']], on='valid_at', validate='many_to_one'))
    for prefix in ['met','wn']:
        pairs[prefix+'_abs_error'] = (pairs[prefix+'_value']-pairs.actual_value).abs()
    return pairs


def metrics(pairs):
    """Shared amount/event metrics. Undefined rates/empty MAE are NaN, never zero."""
    wet = pairs.actual_value > WET_THRESHOLD
    result = []
    for prefix, provider in [('met','Yr/MET'),('wn','WeatherNext')]:
        error = pairs[prefix+'_value']-pairs.actual_value
        rain = pairs[prefix+'_value'] > WET_THRESHOLD
        hits = int((rain & wet).sum()); misses = int((~rain & wet).sum())
        false = int((rain & ~wet).sum()); dry = int((~rain & ~wet).sum())
        ratio = lambda n,d: n/d if d else float('nan')
        result.append(dict(provider=provider, samples=len(pairs), wet=int(wet.sum()), dry=int((~wet).sum()),
                           mae=error.abs().mean(), wet_mae=error[wet].abs().mean(), bias=error.mean(),
                           hits=hits, misses=misses, false_alarms=false, correct_dry=dry,
                           POD=ratio(hits,hits+misses), FAR=ratio(false,hits+false),
                           CSI=ratio(hits,hits+misses+false)))
    return pd.DataFrame(result)


def summary(pairs):
    """Four explicit buckets, including empty buckets and actual lead coverage."""
    result = []
    for label in LABELS:
        group = pairs[pairs.horizon == label]
        for row in metrics(group).to_dict('records'):
            row.update(horizon=label, stations=group.location_id.nunique(),
                       period_start=group.valid_at.min(), period_end=group.valid_at.max(),
                       yr_lead_min=group.met_lead_hours.min(), yr_lead_max=group.met_lead_hours.max(),
                       wn_lead_min=group.wn_lead_hours.min(), wn_lead_max=group.wn_lead_hours.max())
            result.append(row)
    return pd.DataFrame(result)
