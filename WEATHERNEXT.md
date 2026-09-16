# Google WeatherNext 3

WeatherNext uses the existing active Frost stations from `data/weather.db`.
The existing database remains authoritative. No database was replaced.

## Status

Integration is enabled in the authoritative project, `E:\WeatherApp`.
All 13 tests passed in the existing Python 3.13 environment, and the Streamlit
startup test passed. Authentication succeeded for `weatherapp-508323` using
Earth Engine SDK 1.7.43. The 2026-09-15 06:00 UTC run passed 360-hour live tests
for Trondheim-Voll, three stations, and all 50 active stations. Repeating the
Trondheim run added zero rows. Saved: 50 runs, 18,000 forecast points and 378,000
statistic values. See `work/live-validation.json` and `work/integration-status.json`.

`WEATHERNEXT_ENABLED=1` is set in `.env`. The existing Scheduled Task was verified
and left unchanged; its next normal run will include WeatherNext. It was not
manually restarted as part of this integration.

## Existing environment and authentication

Run each line separately in PowerShell:

```powershell
cd E:\WeatherApp
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\earthengine.exe authenticate
.\.venv\Scripts\python.exe -m unittest test_weathernext -v
```

Authentication uses your account; initialization explicitly uses project
`weatherapp-508323`. Credentials stay in Earth Engine's standard local store.

## Manual collection

Use the app's **Fetch WeatherNext now** button for all active stations and the
latest complete 360-hour synoptic run. Or use the CLI:

```powershell
# One-station preview; does not save forecast rows.
.\.venv\Scripts\python.exe collect_weathernext.py --station-id SN68860
# Save the latest complete 360-hour run for all active stations.
.\.venv\Scripts\python.exe collect_weathernext.py --hours 360 --stations 0 --save
```

`--issued-at` selects an exact initialization for repeatability. Run selection
checks all required hours in both resolutions. Sampling is limited to requested
bands, at most 12 hours and 50 station points per batch, with smaller queries on
Earth Engine memory errors. Earlier committed batches survive interruption;
rerunning fills missing data and never replaces existing saved values.

## Storage

- Provider: `WeatherNext3-mean` in `forecast_runs` and `forecasts`.
- Temperature mean and wind-speed mean use the existing scoreboards.
- `weathernext_samples`: individual statistics, asset ID, sampled coordinates,
  retrieval time and unit. Unique key: run, valid time, variable, statistic.
- `weathernext_values`: view with provider, station ID, initialization, valid time,
  lead hours, variable, statistic, value and unit.
- Temperature and wind speed: mean, p10, p25, p50, p75, p90.
- Hourly precipitation: the same six statistics, converted metres → millimetres.
- Wind u/v means: m/s. `wind_direction(u,v)` calculates meteorological FROM
  direction of the mean vector; calm has no defined direction. This is not an
  ensemble mean of direction angles.
- Mean sea-level pressure: Pa → hPa. Temperature: K → °C.

Rainfall is retained in the normalized table. The Frost collector now stores the
validated hourly observation element, but scoreboards remain limited to
temperature and wind. See `PRECIPITATION.md` for the canonical interval-end
mapping required by any future rainfall scoring work.

No existing columns or tables were dropped or renamed. Existing records were
checked before/after migration using row counts and row-content comparisons.

## Background collection

The validated configuration in `.env` is:

```dotenv
EARTH_ENGINE_PROJECT=weatherapp-508323
WEATHERNEXT_ENABLED=1
```

The existing background runner collects MET, Frost, then WeatherNext. WeatherNext
failures are logged and return a failing exit status without preventing earlier
MET/Frost work. No browser login is attempted in the scheduled job. Keep
`WEATHERNEXT_ENABLED=0` to disable WeatherNext without affecting MET or Frost.

The existing task points at `E:\WeatherApp\.venv\Scripts\python.exe` and
`background_collect.py`, uses the current user's account, and has a 30-minute
execution limit. The full live validation completed within that window.

## Validation and rollback

`work/live_validation.py` tests Trondheim-Voll temperature through 360 hours,
then all variables, repeat collection, three stations, and the full active set.
It checked existing history after each step and recorded results in
`work/live-validation.json`. It does not enable scheduling.

The original before/after history checks are preserved. After live validation,
the ordinary scheduled run at 18:10 local time added 4,357 MET forecast points
and 2,245 observation rows. It filled two previously missing Frost values and
refreshed five source-check timestamps. Existing measured values were not
overwritten and no historical rows were lost. This was reconciled read-only in
`work/scheduled-update-reconciliation.json` before enabling WeatherNext.
`history-after-scheduled-before-enable.json` is the next validated checkpoint;
the initial baseline was not replaced. Running the original strict audit after
normal collection can report expected changes; investigate them rather than
restoring old data or silently resetting the baseline.

To disable automatic WeatherNext collection, set `WEATHERNEXT_ENABLED=0`.
Keep the additive table and collected history; MET/Frost does not depend on it.
Do not restore a trial database over the current database.

Sources: [Earth Engine WeatherNext guide](https://developers.google.com/weathernext/guides/earth-engine),
[gridded catalog](https://developers.google.com/earth-engine/datasets/catalog/projects_gcp-public-data-weathernext_assets_weathernext_3_0_0_0p1deg),
[station catalog](https://developers.google.com/earth-engine/datasets/catalog/projects_gcp-public-data-weathernext_assets_weathernext_3_0_0_0p05deg).
