from __future__ import annotations

import sqlite3

import pandas as pd


MET_PROVIDER = "MET"
WEATHERNEXT_PROVIDER = "WeatherNext3-mean"
LEAD_BINS = [0, 18, 36, 60, 84, 144, 216, float("inf")]
LEAD_LABELS = ["0–18h", "18–36h", "36–60h", "60–84h", "3.5–6d", "6–9d", "9d+"]


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


def load_temperature_timeline(
    con: sqlite3.Connection, location_id: int, met_run_id: int, wn_run_id: int
) -> pd.DataFrame:
    met = pd.read_sql_query(
        """
        SELECT valid_at, lead_hours AS met_lead_hours,
               air_temperature AS met_temperature
        FROM forecasts
        WHERE run_id=? AND air_temperature IS NOT NULL
        """,
        con,
        params=(met_run_id,),
    )
    wn = pd.read_sql_query(
        """
        SELECT f.valid_at, f.lead_hours AS wn_lead_hours,
               f.air_temperature AS wn_temperature,
               p10.value AS wn_p10, p90.value AS wn_p90
        FROM forecasts f
        LEFT JOIN weathernext_samples p10
          ON p10.run_id=f.run_id AND p10.valid_at=f.valid_at
         AND p10.metric='air_temperature' AND p10.statistic='p10'
        LEFT JOIN weathernext_samples p90
          ON p90.run_id=f.run_id AND p90.valid_at=f.valid_at
         AND p90.metric='air_temperature' AND p90.statistic='p90'
        WHERE f.run_id=? AND f.air_temperature IS NOT NULL
        """,
        con,
        params=(wn_run_id,),
    )
    observations = pd.read_sql_query(
        """
        SELECT strftime('%Y-%m-%dT%H:00:00Z', observed_at) AS valid_at,
               AVG(air_temperature) AS actual_temperature
        FROM observations
        WHERE location_id=? AND air_temperature IS NOT NULL
        GROUP BY strftime('%Y-%m-%dT%H:00:00Z', observed_at)
        """,
        con,
        params=(location_id,),
    )

    timeline = met.merge(wn, on="valid_at", how="outer").merge(
        observations, on="valid_at", how="left"
    )
    timeline["valid_at"] = pd.to_datetime(timeline["valid_at"], utc=True)
    return timeline.sort_values("valid_at").reset_index(drop=True)


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
