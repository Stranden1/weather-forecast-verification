"""Shared settings for the compact cloud pipeline.

Design (see PLAN_WEBPAGE.md): every collection run snapshots, for each station,
only the forecast hours that fall inside a verification horizon window. Once the
actual weather is known the snapshot is scored and discarded; only the compact
scored rows are kept permanently.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIONS_FILE = ROOT / "config" / "stations.json"

# Working state (pending snapshots, recent observations). In GitHub Actions this
# lives on a separate `state` branch that is force-pushed, so it never grows the
# repository history.
STATE_DIR = Path(os.getenv("WX_STATE_DIR", ROOT / "state"))
# Permanent compact history: one gzipped CSV per UTC day, written once.
SCORED_DIR = Path(os.getenv("WX_SCORED_DIR", ROOT / "history"))
# Small JSON files read by the static webpage.
SITE_DATA_DIR = Path(os.getenv("WX_SITE_DATA_DIR", ROOT / "site" / "data"))

# Hours ahead, measured from the moment both forecasts were fetched together
# ("what you could see at the same time"). A snapshot counts for horizon H when
# its lead is within +/- HORIZON_TOLERANCE hours; the closest one is used.
HORIZONS = [6, 12, 24, 48, 72, 120, 168, 240]
HORIZON_TOLERANCE = 3.0
# Yr publishes hourly steps to roughly 2.5 days, then 6-hourly steps. Hourly
# precipitation is therefore only scored on the short horizons.
PRECIP_HORIZONS = [6, 12, 24, 48]
# How long a finished UTC day waits for late Frost observations before scoring.
FINALIZE_DELAY_HOURS = 6
MIN_OBSERVATION_COVERAGE = 0.8
FINALIZE_MAX_AGE_DAYS = 3  # measured from the end of the UTC target day
# Observations kept in working state (days). The naive baseline for the 10-day
# horizon needs the observation 10 days before each target (~15k rows, still small).
OBS_KEEP_DAYS = 15  # 11-day baseline lookback + three-day finalization delay + margin
# Each run re-fetches this many recent days from Frost, to catch late observations.
OBS_FETCH_DAYS = 5  # refetch the complete oldest day still waiting for coverage

WET_THRESHOLD_MM = 0.1  # strictly greater than -> wet hour (same as the local app)

VARIABLES = {
    "t": {"name": "Temperature", "unit": "°C"},
    "w": {"name": "Wind speed", "unit": "m/s"},
    "p": {"name": "Hourly precipitation", "unit": "mm"},
}

PROVIDERS = {
    "yr": "Yr (MET Norway)",
    "wn": "Google WeatherNext 3 (ensemble mean)",
    "wn50": "Google WeatherNext 3 (ensemble median)",
    # Our adjustment, not Google's product: temperature moved from the model cell's
    # height to the station's height at 6.5 °C/km (cloud/heights.py).
    "wnh": "Google WeatherNext 3, height-adjusted (our adjustment)",
}

# How WeatherNext grid values are read at a station (DECISIONS.md, 2026-09-26).
# "bilinear": interpolated from the four surrounding cells of the native grid.
# "nn5km": the earlier method (scale=5000/10000 without a grid), which Earth Engine
# resampled onto a coarser grid, so 15 of 50 stations got a neighbouring cell.
# Rows without a value (all history before the change) used "nn5km".
WN_SAMPLING = "bilinear"
WN_SAMPLING_OLD = "nn5km"
# The PC collector (collectors/weathernext.py) switched to bilinear at this time;
# migrate_sqlite marks WeatherNext runs retrieved from then on as bilinear.
LOCAL_BILINEAR_SINCE = "2026-09-26T16:00:00Z"

# Pending snapshot columns (one row per provider, station, target hour).
VALUE_COLUMNS = [
    "t", "t_p10", "t_p50", "t_p90",
    "w", "w_p10", "w_p50", "w_p90",
    "p", "p_p50", "p_p90", "p_min", "p_max", "p_prob",
]
PENDING_COLUMNS = (["provider", "station", "fetched_at", "issued_at", "target", "lead_h"]
                   + VALUE_COLUMNS + ["sampling"])

OBS_COLUMNS = ["station", "time", "t", "w", "p"]

# The WeatherNext real-time data has its own terms of use. Until you have read
# them, publish only aggregated error statistics, not WeatherNext forecast values.
PUBLISH_FORECAST_VALUES = os.getenv("WX_PUBLISH_FORECAST_VALUES", "0") == "1"

# WeatherNext wording is quoted exactly from Google (DECISIONS.md, "WeatherNext terms").
# We publish error statistics only. Our forecasts were fetched while real-time and scored
# once the time had passed, so both required citations are shown: the real-time terms'
# "findings" citation (section 4(b)) and the Earth Engine catalog's CC BY 4.0 citation for
# historic data. The last line is the catalog's acknowledgement of upstream data.
# Required WeatherNext notices, quoted exactly (DECISIONS.md, "WeatherNext terms"). They are
# shown in the page footer and again next to every chart that shows WeatherNext values.
WN_ACCESS_NOTE = "WeatherNext 3 forecasts accessed via Google Earth Engine."
WN_REALTIME_NOTICE = (
    "© 2024-6 Google LLC, whose machine learning models were used to create the experimental "
    "data made available under the following licence terms "
    "https://storage.googleapis.com/weathernext-public/terms-of-use.pdf. This data is intended "
    "for experimental modelling only and is not intended, validated, or approved for real world use.")
WN_CCBY_CITATION = (
    "© 2026 DeepMind Technologies Limited's machine learning models used to create the "
    "experimental data made available at https://developers.google.com/earth-engine/datasets/"
    "catalog/projects_gcp-public-data-weathernext_assets_weathernext_3_0_0_0p05deg under "
    "CC BY 4.0 licence terms. This data is intended for experimental modelling only and is not "
    "intended, validated, or approved for real world use.")
WN_VALUE_ATTRIBUTION = [WN_ACCESS_NOTE, WN_CCBY_CITATION, WN_REALTIME_NOTICE]
# WeatherNext values are published only for target times at least this long ago: data for a
# time 1 hour ago or more is CC BY 4.0; newer and future data falls under the real-time terms.
PUBLISH_MIN_AGE_H = 1

ATTRIBUTION = [
    "Forecasts and observations from MET Norway (Yr, Frost), licensed CC BY 4.0.",
    WN_ACCESS_NOTE,
    WN_REALTIME_NOTICE,
    WN_CCBY_CITATION,
    "WeatherNext 3 was generated using data and products of the European Centre for "
    "Medium-Range Weather Forecasts (ECMWF), as well as additional third-party providers: "
    "https://storage.googleapis.com/weathernext-public/weathernext-3-attributions-acknowledgements.pdf",
    # ECMWF IFS/AIFS via Open-Meteo (collected, not shown yet). Open-Meteo's licence page
    # requires "Weather data by Open-Meteo.com" linked to https://open-meteo.com/; ECMWF's
    # licence asks services for this copyright, source, licence and disclaimer wording and a
    # note of modifications.
    "Weather data by Open-Meteo.com (https://open-meteo.com/), licensed CC BY 4.0.",
    "This service is based on data and products of the European Centre for Medium-Range "
    "Weather Forecasts (ECMWF). Source: www.ecmwf.int. This data is published under a Creative "
    "Commons Attribution 4.0 International (CC BY 4.0) https://creativecommons.org/licenses/by/4.0/. "
    "ECMWF does not accept any liability whatsoever for any error or omission in the data, their "
    "availability, or for any loss or damage arising from their use. Modified: Open-Meteo "
    "interpolates the IFS and AIFS forecasts to hourly values and adjusts temperature to each "
    "station's height.",
]


def load_stations(path: Path = STATIONS_FILE) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    stations = [s for s in data["stations"] if s.get("active", 1)]
    for s in stations:
        s["station_id"] = str(s["station_id"]).upper()
    return stations


def horizon_window(horizon: int) -> tuple[float, float]:
    return horizon - HORIZON_TOLERANCE, horizon + HORIZON_TOLERANCE


def wanted_leads(max_lead: float = 1e9) -> list[tuple[int, float, float]]:
    return [(h, *horizon_window(h)) for h in HORIZONS if h - HORIZON_TOLERANCE <= max_lead]
