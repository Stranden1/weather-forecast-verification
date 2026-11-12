from __future__ import annotations

import pandas as pd

from database import connect

BANDS = [0, 18, 36, 60, 84, 144, 216, 999]
LABELS = ["0–18h", "18–36h", "36–60h", "60–84h", "3.5–6d", "6–9d", "9d+"]


def _scored_rows(forecast_col: str, observed_col: str) -> pd.DataFrame:
    if forecast_col not in {"air_temperature", "wind_speed"}:
        raise ValueError("Unsupported forecast metric")
    if observed_col not in {"air_temperature", "wind_speed"}:
        raise ValueError("Unsupported observation metric")
    query = f"""
    SELECT
        l.name AS location,
        l.station_id,
        fr.provider,
        fr.issued_at,
        f.valid_at,
        f.lead_hours,
        f.{forecast_col} AS forecast_value,
        o.{observed_col} AS observed_value,
        ABS(f.{forecast_col} - o.{observed_col}) AS abs_error,
        (f.{forecast_col} - o.{observed_col}) AS signed_error
    FROM forecasts f
    JOIN forecast_runs fr ON fr.id = f.run_id
    JOIN locations l ON l.id = fr.location_id
    JOIN observations o
      ON o.location_id = fr.location_id
     AND strftime('%Y-%m-%dT%H:00:00Z', o.observed_at) = strftime('%Y-%m-%dT%H:00:00Z', f.valid_at)
    WHERE f.{forecast_col} IS NOT NULL
      AND o.{observed_col} IS NOT NULL
    """
    with connect() as con:
        return pd.read_sql_query(query, con)


def scored_temperature_rows() -> pd.DataFrame:
    return _scored_rows("air_temperature", "air_temperature")


def scored_wind_rows() -> pd.DataFrame:
    return _scored_rows("wind_speed", "wind_speed")


def _scoreboard(df: pd.DataFrame, mae_name: str) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["horizon"] = pd.cut(df["lead_hours"], bins=BANDS, labels=LABELS, right=False)
    board = (
        df.groupby(["provider", "horizon"], observed=True)
        .agg(
            **{
                mae_name: ("abs_error", "mean"),
                "bias": ("signed_error", "mean"),
                "samples": ("abs_error", "size"),
            }
        )
        .reset_index()
    )
    return board


def temperature_scoreboard() -> pd.DataFrame:
    return _scoreboard(scored_temperature_rows(), "MAE_C")


def wind_scoreboard() -> pd.DataFrame:
    return _scoreboard(scored_wind_rows(), "MAE_ms")


def paired_score_rows(pairs):
    """Use the existing MAE/bias aggregation on identical paired targets."""
    frames = []
    for prefix, provider in (("met", "MET"), ("wn", "WeatherNext3-mean")):
        frame = pairs[["location_id", "station", "station_id", "valid_at", "horizon"]].copy()
        frame["provider"] = provider
        frame["lead_hours"] = pairs[f"{prefix}_lead_hours"]
        frame["signed_error"] = pairs[f"{prefix}_value"] - pairs["actual_value"]
        frame["abs_error"] = frame["signed_error"].abs()
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)
