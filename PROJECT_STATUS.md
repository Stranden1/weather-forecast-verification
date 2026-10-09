# Project status

_Updated 2026-10-09. Current state only; history is in CHANGELOG.md._

## Summary

The local collector and cloud dashboard work, but cloud cadence and station freshness
need attention. Before timer activation, health reported 10/16 expected collections
in 48 h, with gaps up to 9 h 21 min. Keep the PC collector running. cron-job.org job
8590224 is now enabled at :07/:37 UTC. Its external test returned 204 and the resulting
GitHub run correctly respected the 150-minute gate. Since then (6 Oct 16:37 UTC) the
cloud has collected every 2.5-3.0 h.

**PC collector: not yet safe to retire (8 Oct check).** On 7 Oct, the only finished day
since the timer, the cloud had 92-93% of the PC's scored station-hours on the 45 shared
stations; all forecast gaps were runs GitHub skipped before the timer. On horizon slots
the timer covered (6 h-1 day) it had 99.9%; the one miss was a late Frost observation.
Longer horizons can't be judged until ~12 Oct (2 days) and ~18 Oct (10 days). Details in
CHANGELOG.md (8 Oct entry).

## Current capabilities

- Local: authoritative data/weather.db, full forecasts/observations, Streamlit
  comparisons and six-hourly collection at 50 active stations.
- Cloud: paired snapshots, encrypted immutable history, daily scoring, trends,
  maps, uncertainty, baseline diagnostics, monthly summaries and storm replays.
- Live page: 31 scored days through 5 Oct, 174,911 rows. Past WeatherNext values
  are enabled, restricted to targets at least 1 h old, with attribution.
- Collection uses an external request every 30 min, the hourly GitHub fallback and
  a 150-minute gate. trigger=timer respects the gate; manual bypasses it.
- The horizon card leads with a WeatherNext-minus-Yr difference chart (95% ranges, verdict colours,
  horizons under 7 days hidden); an Error size view and the full table remain (9 Oct).
- ECMWF IFS/AIFS are collected but not ranked on the page; steadiness is exported
  but not displayed. Height-adjusted temperature stays a separate comparison.

## Latest verification

- Local task: Ready, result 0, completed 6 Oct at 12:14 Oslo; next run 18:10.
  All three sources report OK; recent forecast retrievals cover 50 stations.
- Cloud scheduled run 37485951770 at 15:15 UTC on 6 Oct succeeded, including
  collection and Pages deployment.
- Observation coverage for 4-5 Oct: 93.9% and 95.1%, neither late-finalized.
- Browser: dashboard renders, rain filter works, no captured console errors.
- Tests: 119 cloud tests passed again after rebase, and CI 37453257669 passed;
  79 local tests passed in the preceding review. Existing warnings remain.
- Timer run 37453257515 passed: skipped at 135 minutes, with downstream steps skipped;
  state revision and public health timestamp stayed unchanged.
- External timer test 37495000121 passed at 16:21 UTC: skipped at 65 minutes, with
  collection/persistence/Pages skipped. Service confirms the recurring job is enabled.
- Database reads succeed; file is 6.21 GB, with 267 GB free on E:. Read-only SQLite
  quick_check was interrupted at 45 seconds; full integrity remains unverified.

## Open findings and next actions

- Cloud/local station networks overlap at 45/50. Local discovery refreshes weekly;
  cloud config/stations.json is a fixed snapshot. Reconcile before comparing coverage.
- Enningdalen (SN1120) has no observations after 30 Sep 23:00 UTC locally or in cloud;
  Wisting (SN20925, cloud only) stops at 30 Sep 21:00 UTC. Aggregate Frost OK does not
  reveal these station outages. Add station freshness/coverage warnings.
- Local commits were rebased over the two scored-history commits and pushed with
  user approval. History day files remain unchanged.
- Re-run the coverage comparison on ~12 Oct and ~18 Oct before retiring the PC task
  (CHANGELOG.md, 8 Oct). Renew the token before 5 Nov 2026.
- The 1-day headline has 19 paired days despite 31 total scored days; October has
  five days, correctly below the seven-day monthly verdict threshold.

NEXT_STEPS.md holds open work. Earlier plaintext Git history remains a separate
cleanup concern; keep secure backups of the database and encryption key.
