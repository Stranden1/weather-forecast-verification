# Project status

_Updated 2026-09-16_

## Summary

WeatherApp is a runnable local Windows benchmark comparing Yr/MET and Google
WeatherNext forecasts against Frost observations across 50 active Norwegian
stations. Data collection, storage, scoring, background scheduling, and the
Streamlit dashboard are operational.

## Current capabilities

- Collects Yr/MET forecasts and Frost temperature/wind observations.
- Collects 360-hour WeatherNext forecasts for the shared station network,
  including means, percentiles, precipitation, wind components, and pressure.
- Shows a compact Forecast vs Actual temperature view with run selection,
  WeatherNext p10–p90 uncertainty, elapsed Frost observations, errors, and MAE.
- Shows station metadata/maps, overall temperature and wind accuracy, and
  WeatherNext collection status/history.
- Dashboard browsing is read-only; manual collection controls are separated in
  the collapsed Admin section.
- Daily-use UI polish adds consistent metric cards, compact selectors and table
  rows, softer forecast chart styling, and a horizontal MAE dot plot. Status,
  logs, and manual controls remain in compact collapsed expanders.

## Live state

- Authoritative database: `data/weather.db`
- Active stations: 50
- Total forecast runs / points: 2,304 / 227,838
- Frost observation rows: 177,856
- Latest WeatherNext run: 2026-09-15 12:00 UTC
- WeatherNext forecast points / statistic values: 36,000 / 756,000
- Latest background collection finished successfully at 2026-09-15 22:11 UTC;
  WeatherNext added zero rows because that model run was already stored.

## Validation

All 18 regression tests and the disposable-database dashboard test pass. The
compact dashboard was also checked in a browser with production data.

## Known limits

- Forecast vs Actual currently covers temperature only.
- WeatherNext rainfall is stored but not scored until interval alignment is
  validated.
- Accuracy becomes more meaningful as additional model cycles and observations
  accumulate.

## Version control — 2026-09-16

Private remote: https://github.com/Stranden1/weather-forecast-verification.
Code, tests, setup scripts, docs and a 50-station metadata snapshot are versioned.
Secrets, live data, environments and scratch artifacts remain local. All 18 tests,
fixture UI test and production dashboard render passed; existing deprecation warnings
are non-fatal. Application code and scheduling were not changed for Git setup.
