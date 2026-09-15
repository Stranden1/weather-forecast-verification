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
