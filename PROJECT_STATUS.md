# Project status

_Updated 2026-10-06. Current state only; history is in CHANGELOG.md._

## Summary

The local collector and cloud dashboard work, but cloud cadence and station freshness
need attention. Live health reports 10/16 expected collections in 48 h, with gaps up
to 9 h 21 min. Keep the PC collector running. Timer support is committed locally as
7ee874e; push still awaits the user's OK.

## Current capabilities

- Local: authoritative data/weather.db, full forecasts/observations, Streamlit
  comparisons and six-hourly collection at 50 active stations.
- Cloud: paired snapshots, encrypted immutable history, daily scoring, trends,
  maps, uncertainty, baseline diagnostics, monthly summaries and storm replays.
- Live page: 31 scored days through 5 Oct, 174,911 rows. Past WeatherNext values
  are enabled, restricted to targets at least 1 h old, with attribution.
- Collection aims for every 3 h using an hourly cron and 150-minute gate. The local
  timer change preserves that gate for trigger=timer; manual bypasses it.
- ECMWF IFS/AIFS are collected but not ranked on the page; steadiness is exported
  but not displayed. Height-adjusted temperature stays a separate comparison.

## Latest verification

- Local task: Ready, result 0, completed 6 Oct at 12:14 Oslo; next run 18:10.
  All three sources report OK; recent forecast retrievals cover 50 stations.
- Cloud run 37438015907 (manual, 6 Oct 10:43 Oslo) passed collection, persistence,
  upgraded actions, Pages and final source check. All four sources report no errors.
- Observation coverage for 4-5 Oct: 93.9% and 95.1%, neither late-finalized.
- Browser: dashboard renders, rain filter works, no captured console errors.
- Tests: 119 cloud tests passed earlier this session after the timer edit; 79 local
  tests passed in this review. Existing dependency/resource warnings remain.
- Database reads succeed; file is 6.21 GB, with 267 GB free on E:. Read-only SQLite
  quick_check was interrupted at 45 seconds; full integrity remains unverified.

## Open findings and next actions

- Cloud/local station networks overlap at 45/50. Local discovery refreshes weekly;
  cloud config/stations.json is a fixed snapshot. Reconcile before comparing coverage.
- Enningdalen (SN1120) has no observations after 30 Sep 23:00 UTC locally or in cloud;
  Wisting (SN20925, cloud only) stops at 30 Sep 21:00 UTC. Aggregate Frost OK does not
  reveal these station outages. Add station freshness/coverage warnings.
- Remote main has two newer scored-history commits. Integrate them safely before
  pushing local commits; preserve immutable history and never force-push.
- After push approval, configure the timer, verify skips/collections and compare
  cloud/local coverage on matched stations before retiring the PC task.
- The 1-day headline has 19 paired days despite 31 total scored days; October has
  five days, correctly below the seven-day monthly verdict threshold.

NEXT_STEPS.md holds open work. Earlier plaintext Git history remains a separate
cleanup concern; keep secure backups of the database and encryption key.
