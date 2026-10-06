# Project status

_Updated 2026-10-06. Current state only; history is in CHANGELOG.md._

## Summary

WeatherApp compares Yr/MET and WeatherNext against Frost at 50 Norwegian stations.
The local Windows collector and public cloud dashboard both work. Cloud collection
timing remains unreliable, so keep the PC collector running until coverage matches.
External timer dispatch support is implemented locally; push awaits the user's OK.
The live page contains 29 scored days through 3 Oct (160,259 rows), monthly summaries,
rain headlines led by WeatherNext's median, and past WeatherNext forecast values.
ECMWF IFS/AIFS are collected but not yet ranked on the page.

## Current capabilities

- Local: authoritative data/weather.db, full forecast/observation history,
  Streamlit comparisons, and six-hourly collection on the active 50-station network.
- Cloud: paired horizon snapshots, daily scoring, encrypted immutable history,
  trends, maps, uncertainty, baseline diagnostics and storm replay exports/page card.
- Collection aims for about every 3 h: hourly GitHub trigger with a 150 min gate.
- Local workflow change: `trigger=timer` dispatches respect that gate;
  `trigger=manual` (default) bypasses it. Setup is documented in SETUP_CLOUD.md.
- Past WeatherNext values are enabled (WX_PUBLISH_FORECAST_VALUES=1); the code
  restricts publication to target times at least 1 h old, with attribution.
- Height-adjusted temperature remains a separate labelled comparison. Steadiness
  is exported but not yet displayed. Project HQ is a local read-only document viewer.

## Reliability and verification

- Encrypted state/history, fail-closed restore, history-first publication with origin
  confirmation, and leased state updates are implemented and covered by tests.
- Days require >=80% configured station-hour observation coverage, with retries
  until day-end +72 h. Recent metadata verifies 94.9% for 2 Oct and 94.7% for 3 Oct;
  neither day was late-finalized. This measures observations, not forecast coverage.
- Last full check (5 Oct): 119 cloud + 79 local tests passed. Dependency warnings remain.
- After the timer change (6 Oct), all 119 cloud tests pass, including gate boundary
  and manual-bypass coverage. Live timer behavior awaits deployment.
- Latest cloud collection checked: run 37231498979, manual, 4 Oct 22:17 Oslo time;
  collection, persistence, Pages and final source check all passed. Published health
  reports zero errors for Yr, WeatherNext, ECMWF and Frost, but only 9/16 expected
  collections in its 48 h window. Last scheduled run checked started 4 Oct 20:38 Oslo.
- Local collector finished successfully on 5 Oct at 00:14 Oslo; the last four
  background collections were successful. Database size is about 5.75 GB (decimal).
- Latest cloud CI passed the action upgrades (37236715635). A collecting/deploying
  run using those upgrades, and a real scheduled gate skip, remain to be verified.

## Findings and next actions

September's paired comparison spans 16 days: Yr leads raw temperature at 6 h;
1-3 day temperature is too close to call. WeatherNext leads wind at 2 days and
its rain median leads at 2 days. Height-adjusted WeatherNext leads temperature
at 6 h-3 days, subject to the proxy-terrain/fixed-lapse-rate limitations.
October has only three scored days, below the seven-day verdict threshold.

Compare cloud/local forecast coverage before retiring the PC collector. After push
approval, configure the external timer and verify gated skips and collection cadence.
Continue replay/steadiness work, ECMWF display, and median rain consistency.
Old plaintext commits/caches remain accessible; current encryption does not remove
them. Keep a secure separate key backup. NEXT_STEPS.md holds open work.
