from __future__ import annotations

import sqlite3

import pandas as pd


MET_PROVIDER = "MET"
WEATHERNEXT_PROVIDER = "WeatherNext3-mean"
from scoring.scorer import BANDS as LEAD_BINS, LABELS as LEAD_LABELS

VARIABLES = {"air_temperature": ("Temperature", "°C"), "wind_speed": ("Wind speed", "m/s"),
             "precipitation_1h": ("Hourly precipitation", "mm/h")}


def comparison_stations(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute(
        """
        SELECT id, name, station_id, COALESCE(station_name, name) AS station_name
        FROM locations
        WHERE active=1
        ORDER BY CASE WHEN station_id='SN68860' THEN 0 ELSE 1 END, station_name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def recent_runs(
    con: sqlite3.Connection, location_id: int, provider: str, limit: int = 12
) -> list[dict]:
    rows = con.execute(
        """
        SELECT id, issued_at, retrieved_at
        FROM forecast_runs
        WHERE location_id=? AND provider=?
        ORDER BY issued_at DESC
        LIMIT ?
        """,
        (location_id, provider, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def load_timeline(con, location_id, met_run_id, wn_run_id, metric="air_temperature"):
    """Exact valid-time observations only; never average future sub-hour readings."""
    if metric not in VARIABLES:
        raise ValueError("Unsupported metric")
    if metric == 'precipitation_1h':
        from scoring.precipitation import load_timeline as rainfall_timeline
        return rainfall_timeline(con, location_id, met_run_id, wn_run_id)
    frames = []
    for prefix, run_id in (("met", met_run_id), ("wn", wn_run_id)):
        frame = pd.read_sql_query(f"""
            SELECT f.valid_at, f.lead_hours AS {prefix}_lead_hours,
                   f.{metric} AS {prefix}_value
            FROM forecasts f JOIN forecast_runs r ON r.id=f.run_id
            WHERE f.run_id=? AND r.location_id=? AND f.{metric} IS NOT NULL AND f.lead_hours>=0
        """, con, params=(run_id, location_id))
        frame["valid_at"] = pd.to_datetime(frame["valid_at"], utc=True, format="mixed")
        frames.append(frame)
    timeline = frames[0].merge(frames[1], on="valid_at", how="outer")
    quantiles = pd.read_sql_query("""
        SELECT valid_at, MAX(CASE WHEN statistic='p10' THEN value END) AS wn_p10,
               MAX(CASE WHEN statistic='p90' THEN value END) AS wn_p90
        FROM weathernext_samples WHERE run_id=? AND metric=? GROUP BY valid_at
    """, con, params=(wn_run_id, metric))
    quantiles["valid_at"] = pd.to_datetime(quantiles["valid_at"], utc=True, format="mixed")
    observations = pd.read_sql_query(f"""
        SELECT observed_at AS valid_at, {metric} AS actual_value
        FROM observations WHERE location_id=? AND {metric} IS NOT NULL
    """, con, params=(location_id,))
    observations["valid_at"] = pd.to_datetime(observations["valid_at"], utc=True, format="mixed")
    # Duplicate copies of the same value count once. Conflicting exact-time records
    # have no unambiguous ground truth; omit them rather than inventing an average.
    observations = observations.groupby("valid_at").actual_value.agg(["min", "max"]).reset_index()
    observations = observations[observations["min"] == observations["max"]].rename(columns={"min": "actual_value"})
    return (timeline.merge(quantiles, on="valid_at", how="left")
            .merge(observations[["valid_at", "actual_value"]], on="valid_at", how="left")
            .sort_values("valid_at").reset_index(drop=True))


def past_rows(timeline, now=None):
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    rows = timeline[(timeline.valid_at <= now) & timeline.actual_value.notna()].copy()
    for prefix in ("met", "wn"):
        rows[f"{prefix}_abs_error"] = (rows[f"{prefix}_value"] - rows.actual_value).abs()
    return rows


def load_temperature_timeline(con, location_id, met_run_id, wn_run_id):
    return load_timeline(con, location_id, met_run_id, wn_run_id).rename(columns={
        "met_value": "met_temperature", "wn_value": "wn_temperature", "actual_value": "actual_temperature"})


def past_temperature_rows(timeline: pd.DataFrame, now=None) -> pd.DataFrame:
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    else:
        now = now.tz_convert("UTC")
    rows = timeline[
        (timeline["valid_at"] <= now) & timeline["actual_temperature"].notna()
    ].copy()
    rows["met_abs_error"] = (
        rows["met_temperature"] - rows["actual_temperature"]
    ).abs()
    rows["wn_abs_error"] = (
        rows["wn_temperature"] - rows["actual_temperature"]
    ).abs()
    return rows


def mae_by_lead_bucket(past_rows: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for provider, value_column, lead_column in (
        ("Yr/MET", "met_temperature", "met_lead_hours"),
        ("WeatherNext", "wn_temperature", "wn_lead_hours"),
    ):
        available = past_rows.dropna(
            subset=[value_column, lead_column, "actual_temperature"]
        ).copy()
        if available.empty:
            continue
        available["lead bucket"] = pd.cut(
            available[lead_column],
            bins=LEAD_BINS,
            labels=LEAD_LABELS,
            right=False,
        )
        available["absolute error"] = (
            available[value_column] - available["actual_temperature"]
        ).abs()
        grouped = (
            available.groupby("lead bucket", observed=True, sort=False)
            .agg(MAE=("absolute error", "mean"), samples=("absolute error", "size"))
            .reset_index()
        )
        grouped["provider"] = provider
        frames.append(grouped)
    if not frames:
        return pd.DataFrame(columns=["lead bucket", "MAE", "samples", "provider"])
    return pd.concat(frames, ignore_index=True)
