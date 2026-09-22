"""Read-only dashboard accuracy queries; retain the existing row-level scoring rules."""
import pandas as pd
from scoring.scorer import _scoreboard


def load_accuracy_rows(con, metric):
    if metric not in ('air_temperature', 'wind_speed'):
        raise ValueError('Unsupported metric')
    # Materialize hour keys once instead of formatting timestamps for every
    # candidate pair in the location join. Keep every matching observation,
    # including sub-hourly values, exactly as the original scorer does.
    return pd.read_sql_query(f'''
        WITH observation_hours AS MATERIALIZED (
            SELECT location_id, strftime('%Y-%m-%dT%H:00:00Z',observed_at) AS hour,
                   {metric} AS value FROM observations WHERE {metric} IS NOT NULL
        )
        SELECT l.name AS location, l.station_id, r.provider, r.issued_at,
               f.valid_at, f.lead_hours, f.{metric} AS forecast_value,
               o.value AS observed_value, ABS(f.{metric}-o.value) AS abs_error,
               f.{metric}-o.value AS signed_error
        FROM forecasts f JOIN forecast_runs r ON r.id=f.run_id
        JOIN locations l ON l.id=r.location_id
        JOIN observation_hours o ON o.location_id=r.location_id
            AND o.hour=strftime('%Y-%m-%dT%H:00:00Z',f.valid_at)
        WHERE f.{metric} IS NOT NULL
    ''', con)


def accuracy_board(rows, metric):
    return _scoreboard(rows, 'MAE_C' if metric == 'air_temperature' else 'MAE_ms')

# Shared-target comparison uses the same bucket edges and MAE/bias aggregator as
# the original scorer. Legacy queries above remain available to existing callers.
from scoring.scorer import BANDS, LABELS, paired_score_rows
from forecast_comparison import VARIABLES


def utc_now(now=None):
    value = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    return value.tz_localize("UTC") if value.tzinfo is None else value.tz_convert("UTC")


def load_forecast_rows(con, metric, start=None, end=None, location_id=None):
    if metric not in VARIABLES:
        raise ValueError("Unsupported metric")
    if metric == 'precipitation_1h':
        from scoring.precipitation import load_rows
        return load_rows(con, start, end, location_id)
    where = [f"f.{metric} IS NOT NULL", "l.active=1", "r.provider IN ('MET','WeatherNext3-mean')", "f.lead_hours>=0"]
    params = []
    for operator, value in ((">=", start), ("<=", end)):
        if value is not None:
            where.append(f"julianday(f.valid_at) {operator} julianday(?)")
            params.append(utc_now(value).isoformat())
    if location_id is not None:
        where.append("r.location_id=?")
        params.append(location_id)
    rows = pd.read_sql_query(f"""
        SELECT r.location_id, l.station_id, COALESCE(l.station_name,l.name) AS station,
               r.id AS run_id, r.provider, r.issued_at, r.retrieved_at,
               f.valid_at, f.lead_hours, f.{metric} AS value
        FROM forecasts f JOIN forecast_runs r ON r.id=f.run_id
        JOIN locations l ON l.id=r.location_id WHERE {' AND '.join(where)}
    """, con, params=params)
    for column in ("valid_at", "issued_at", "retrieved_at"):
        rows[column] = pd.to_datetime(rows[column], utc=True, format="mixed")
    return rows


def pair_forecasts(rows, now=None, latest_only=False, deduplicate=True):
    """One pair per target/bucket: nearest leads (<=3h), newest pair breaks ties.

    Disagreements instead use latest available runs per station, with both leads
    shown; their run ages can differ. No errors are used to select either pair.
    deduplicate=False exposes all eligible pairs for whole-run UI selection only.
    """
    now = utc_now(now)
    rows = rows[(rows.issued_at <= now) & (rows.retrieved_at <= now)].copy()
    rows["horizon"] = pd.cut(rows.lead_hours, BANDS, labels=LABELS, right=False)
    keys = ["location_id", "station_id", "station", "valid_at"]
    if latest_only:
        rows = rows[rows.issued_at == rows.groupby(["location_id", "provider"]).issued_at.transform("max")]
    else:
        rows = rows[rows.retrieved_at <= rows.valid_at].dropna(subset=["horizon"])
        keys.append("horizon")
    frames = []
    for provider, prefix in (("MET", "met"), ("WeatherNext3-mean", "wn")):
        frame = rows[rows.provider == provider][keys + ["run_id", "issued_at", "lead_hours", "value"]]
        frames.append(frame.rename(columns={c: f"{prefix}_{c}" for c in ["run_id", "issued_at", "lead_hours", "value"]}))
    pairs = frames[0].merge(frames[1], on=keys, how="inner")
    pairs["lead_gap"] = (pairs.met_lead_hours - pairs.wn_lead_hours).abs()
    if not latest_only:
        pairs = pairs[pairs.lead_gap <= 3.0]
    pairs = pairs.sort_values(["lead_gap", "wn_issued_at", "met_issued_at", "met_run_id", "wn_run_id"],
                              ascending=[True, False, False, False, False])
    if deduplicate:
        pairs = pairs.drop_duplicates(keys)
    return pairs.reset_index(drop=True)


def load_shared_pairs(con, metric, days=7, location_id=None, now=None):
    now = utc_now(now)
    start = None if days is None else now - pd.Timedelta(days=days)
    matcher = pair_forecasts
    if metric == 'precipitation_1h':
        from scoring.precipitation import pair_rows
        matcher = pair_rows
    pairs = matcher(load_forecast_rows(con, metric, start, now, location_id), now)
    return _with_exact_observations(con, pairs, metric, now)


def _with_exact_observations(con, pairs, metric, now):
    if pairs.empty:
        pairs["actual_value"] = pd.Series(dtype=float)
        return pairs
    observations = pd.read_sql_query(f"""
        SELECT location_id, observed_at AS valid_at, {metric} AS actual_value
        FROM observations WHERE {metric} IS NOT NULL
        AND julianday(observed_at) BETWEEN julianday(?) AND julianday(?)
    """, con, params=(pairs.valid_at.min().isoformat(), now.isoformat()))
    observations.valid_at = pd.to_datetime(observations.valid_at, utc=True, format="mixed")
    grouped = observations.groupby(["location_id", "valid_at"]).actual_value.agg(["min", "max"]).reset_index()
    grouped = grouped[grouped["min"] == grouped["max"]].rename(columns={"min": "actual_value"})
    matched = pairs.merge(grouped[["location_id", "valid_at", "actual_value"]], on=["location_id", "valid_at"], how="inner")
    if metric == 'precipitation_1h':
        from scoring.precipitation import clean_observed_pairs
        matched = clean_observed_pairs(matched)
    return matched


def shared_accuracy(pairs, metric):
    if metric == 'precipitation_1h':
        from scoring.precipitation import summary
        return summary(pairs)
    return accuracy_board(paired_score_rows(pairs), metric)


def model_disagreement(con, metric="air_temperature", hours=72, now=None):
    now = utc_now(now)
    rows = load_forecast_rows(con, metric, now, now + pd.Timedelta(hours=hours))
    latest = pd.read_sql_query("""
        SELECT location_id, provider, MAX(issued_at) AS issued_at FROM forecast_runs
        WHERE julianday(issued_at)<=julianday(?) AND julianday(retrieved_at)<=julianday(?)
        GROUP BY location_id, provider
    """, con, params=(now.isoformat(), now.isoformat()))
    latest.issued_at = pd.to_datetime(latest.issued_at, utc=True, format="mixed")
    rows = rows.merge(latest, on=["location_id", "provider", "issued_at"], how="inner")
    rows = rows[rows.valid_at > now]
    pairs = pair_forecasts(rows, now, latest_only=True)
    pairs["difference"] = (pairs.met_value - pairs.wn_value).abs()
    return pairs.sort_values(["difference", "valid_at", "station_id"], ascending=[False, True, True]).reset_index(drop=True)


HORIZONS=(72,120,168,216)


def horizon_pairs(rows, observations, horizon, cutoff, operational=False):
    candidates=rows[(rows.valid_at<=cutoff) & (rows.issued_at<rows.valid_at)
                    & ((rows.lead_hours-horizon).abs()<=3)].copy()
    availability='retrieved_at' if operational else 'available_at'
    candidates=candidates[candidates[availability]<=candidates.valid_at]
    keys=['location_id','station_id','station','valid_at']
    fields=['run_id','issued_at','retrieved_at','available_at','lead_hours','value']
    parts=[]
    for provider,prefix in [('MET','met'),('WeatherNext3-mean','wn')]:
        sub=candidates[candidates.provider==provider][keys+fields]
        parts.append(sub.rename(columns={c:f'{prefix}_{c}' for c in fields}))
    pairs=parts[0].merge(parts[1],on=keys,how='inner')
    pairs['lead_gap']=(pairs.met_lead_hours-pairs.wn_lead_hours).abs()
    pairs=pairs[pairs.lead_gap<=3].sort_values(
        ['lead_gap','wn_issued_at','met_issued_at','wn_run_id','met_run_id'],ascending=[True,False,False,False,False])
    pairs=pairs.drop_duplicates(['location_id','valid_at'])
    pairs=pairs.merge(observations,on=['location_id','valid_at'],how='inner')
    pairs['horizon']=horizon
    for prefix in ['met','wn']:
        pairs[prefix+'_error']=pairs[prefix+'_value']-pairs.actual
        pairs[prefix+'_abs_error']=pairs[prefix+'_error'].abs()
    return pairs



def load_long_range_temperature(con, days=None, location_id=None, now=None):
    """Exact 3/5/7/9-day targets, including certified historical temperatures.

    Missing verification falls back to local retrieval-before-target. Reads only;
    older databases without the optional provenance table remain supported.
    """
    now = utc_now(now)
    start = None if days is None else now - pd.Timedelta(days=days)
    rows = load_forecast_rows(con, 'air_temperature', start, now, location_id)
    rows = rows[rows.lead_hours.between(69, 219)].copy()
    rows['available_at'] = rows.retrieved_at
    if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='weathernext_verified_history'").fetchone():
        from collectors.weathernext import FIELDS
        verified = pd.read_sql_query("""
            SELECT v.run_id, v.valid_at, v.original_available_at
            FROM weathernext_verified_history v
            JOIN forecast_runs r ON r.id=v.run_id AND r.issued_at=v.issued_at
            JOIN forecasts f ON f.run_id=v.run_id AND f.valid_at=v.valid_at
                AND f.lead_hours=v.lead_hours AND f.air_temperature=v.mean_value
            JOIN weathernext_samples s ON s.run_id=v.run_id AND s.valid_at=v.valid_at
                AND s.metric='air_temperature' AND s.statistic='mean'
                AND s.asset_id=v.asset_id AND s.value=v.mean_value AND s.unit='degC'
            WHERE r.provider='WeatherNext3-mean' AND v.source_collection=?
                AND julianday(v.original_available_at)>=julianday(v.issued_at)
                AND julianday(v.original_available_at)<=julianday(v.valid_at)
        """, con, params=(FIELDS['air_temperature'][0],))
        for col in ['valid_at', 'original_available_at']:
            verified[col] = pd.to_datetime(verified[col], utc=True, format='mixed')
        rows = rows.merge(verified, on=['run_id', 'valid_at'], how='left', validate='many_to_one')
        rows['available_at'] = rows.original_available_at.fillna(rows.retrieved_at)
    # Stored leads must agree with original timestamps; malformed rows fail closed.
    derived = (rows.valid_at - rows.issued_at).dt.total_seconds() / 3600
    rows = rows[(derived - rows.lead_hours).abs() < 1e-7]
    observed = pd.read_sql_query("""
        SELECT location_id, observed_at AS valid_at, air_temperature AS actual
        FROM observations WHERE air_temperature IS NOT NULL
          AND julianday(observed_at)<=julianday(?)
          AND (? IS NULL OR julianday(observed_at)>=julianday(?))
    """, con, params=(now.isoformat(), None if start is None else start.isoformat(),
                      None if start is None else start.isoformat()))
    observed.valid_at = pd.to_datetime(observed.valid_at, utc=True, format='mixed')
    grouped = observed.groupby(['location_id', 'valid_at']).actual.agg(['min', 'max']).reset_index()
    observed = grouped[grouped['min'] == grouped['max']].rename(columns={'min':'actual'})[['location_id','valid_at','actual']]
    return pd.concat([horizon_pairs(rows, observed, horizon, now) for horizon in HORIZONS], ignore_index=True)


def long_range_summary(pairs):
    """Always return four rows; empty horizons have zero samples and no score."""
    result = []
    for horizon in HORIZONS:
        group = pairs[pairs.horizon == horizon]
        row = dict(horizon=horizon, samples=len(group), stations=group.location_id.nunique(),
                   period_start=group.valid_at.min(), period_end=group.valid_at.max(),
                   historical_samples=int((group.wn_retrieved_at > group.valid_at).sum()),
                   yr_mae=group.met_abs_error.mean(), wn_mae=group.wn_abs_error.mean(),
                   yr_bias=group.met_error.mean(), wn_bias=group.wn_error.mean(),
                   difference=group.wn_abs_error.mean()-group.met_abs_error.mean(),
                   yr_lead_min=group.met_lead_hours.min(), yr_lead_max=group.met_lead_hours.max(),
                   wn_lead_min=group.wn_lead_hours.min(), wn_lead_max=group.wn_lead_hours.max(),
                   mean_gap=group.lead_gap.mean(), max_gap=group.lead_gap.max())
        result.append(row)
    return pd.DataFrame(result)


CHART_WINDOWS = {"72 h": 72, "7 days": 168, "Full run": None}


def automatic_run_pair(con, location_id, metric="air_temperature", window="72 h", now=None):
    """Newest useful whole-run pair, using the operational fair matcher.

    Prefer pairs with exact observed targets in the displayed window. Rank by
    the pair's older issue descending, then its newer issue and stable IDs.
    With no observed pair, prefer a fair pair with future targets, then any fair
    pair. No selection uses errors or the number of observations as a ranking.
    """
    hours = CHART_WINDOWS[window]
    now = utc_now(now)
    rows = load_forecast_rows(con, metric, location_id=location_id)
    starts = rows.groupby('run_id').valid_at.min()
    rows = rows[(rows.issued_at < rows.valid_at) & (rows.issued_at <= now) & (rows.retrieved_at <= now)]
    matcher = pair_forecasts
    if metric == 'precipitation_1h':
        from scoring.precipitation import pair_rows
        matcher = pair_rows
    pairs = matcher(rows, now, deduplicate=False)
    if hours is not None and not pairs.empty:
        starts_pair = pd.concat([pairs.met_run_id.map(starts), pairs.wn_run_id.map(starts)], axis=1).min(axis=1)
        pairs = pairs[pairs.valid_at <= starts_pair + pd.Timedelta(hours=hours)]
    if pairs.empty:
        reason = "No fair run pair is available for this station/window."
        if rows.empty or rows.provider.nunique() < 2:
            reason += " Both sources need stored forecasts for the selected variable."
        else:
            met = rows[rows.provider == 'MET'].issued_at.drop_duplicates()
            wn = rows[rows.provider == 'WeatherNext3-mean'].issued_at.drop_duplicates()
            gap = min(abs((m-w).total_seconds())/3600 for m in met for w in wn)
            if gap > 3:
                reason += f" Closest stored issue-time gap: {gap:.1f} h (maximum 3 h)."
            else:
                reason += " No common targets meet the lead-bucket and collected-before-target rules in this window."
        return {'pair': None, 'reason': reason}
    observed = _with_exact_observations(con, pairs[pairs.valid_at <= now], metric, now)
    choices = observed
    reason = None
    if choices.empty:
        future = pairs[pairs.valid_at > now]
        choices = future if not future.empty else pairs
        reason = "Fair runs selected; no shared exact-time Frost observations in this chart window yet."
    choices = choices.copy()
    choices['older_issue'] = choices[['met_issued_at','wn_issued_at']].min(axis=1)
    choices['newer_issue'] = choices[['met_issued_at','wn_issued_at']].max(axis=1)
    chosen = choices.sort_values(['older_issue','newer_issue','met_run_id','wn_run_id'], ascending=False).iloc[0]
    result = {}
    for prefix in ['met','wn']:
        run_id = int(chosen[prefix+'_run_id'])
        source = rows[rows.run_id == run_id].iloc[0]
        result[prefix] = {'id': run_id, 'issued_at': source.issued_at.isoformat(), 'retrieved_at': source.retrieved_at.isoformat()}
    result['shared_samples'] = int(((observed.met_run_id == chosen.met_run_id) & (observed.wn_run_id == chosen.wn_run_id)).sum())
    return {'pair': result, 'reason': reason}


def selected_run_pairs(timeline, met_run, wn_run, now=None, metric="air_temperature"):
    """Expose the same operational fair matcher to selected-run UI summaries."""
    from forecast_comparison import past_rows
    now = utc_now(now)
    if metric == 'precipitation_1h':
        from scoring.precipitation import selected_pairs
        return selected_pairs(timeline, met_run, wn_run, now)
    frames = []
    for prefix, provider, run in [('met','MET',met_run), ('wn','WeatherNext3-mean',wn_run)]:
        frame = timeline[['valid_at',prefix+'_lead_hours',prefix+'_value']].rename(
            columns={prefix+'_lead_hours':'lead_hours',prefix+'_value':'value'}).dropna()
        frame['run_id'] = run['id']
        frame['provider'] = provider
        frame['issued_at'] = utc_now(run['issued_at'])
        frame['retrieved_at'] = utc_now(run['retrieved_at'])
        frame['location_id'] = 0
        frame['station_id'] = ''
        frame['station'] = ''
        frames.append(frame)
    rows = pd.concat(frames, ignore_index=True)
    rows = rows[(rows.lead_hours >= 0) & (rows.issued_at < rows.valid_at)]
    paired = pair_forecasts(rows, now)
    elapsed = past_rows(timeline, now)
    return elapsed[elapsed.valid_at.isin(paired.valid_at)].dropna(subset=['met_abs_error','wn_abs_error'])
