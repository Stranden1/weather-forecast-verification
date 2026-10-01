# Project status

_Updated 2026-09-28. Current state only; history is in CHANGELOG.md._

## Summary

WeatherApp compares Yr/MET and WeatherNext with Frost at 50 Norwegian stations.
The cloud pipeline/public dashboard and local Windows collector run in parallel;
ECMWF IFS/AIFS are also collected but not yet ranked on the page. The requested
reliability and encrypted-history fixes were pushed as 3e6ec36 (about 20:24 UTC); first
scheduled run verified successfully (28 Sep 23:16 UTC); older public plaintext Git copies still need
coordinated cleanup before publication protection can be considered complete.
A monthly summary paragraph and a rain view led by WeatherNext's median are live.

## Current capabilities

- Local: authoritative data/weather.db, full forecasts/observations, Streamlit
  comparisons and six-hourly collection. This task did not modify that system.
- Cloud: collects every 3 h (since 1 Oct; 6 h before), paired horizon snapshots, daily scoring,
  encrypted immutable history, aggregate page JSON, trends, maps, uncertainty and baseline diagnostics.
- Page top: a fixed-template paragraph per calendar month (this month "so far", earlier
  months collapsed) from `summary.json`, naming a winner only where the bootstrap verdict does.
  Rain views lead with WeatherNext's median; temperature and wind with its average.
- Sampling method is recorded; height-adjusted WeatherNext remains a separate
  labelled temperature comparison. Steadiness is exported but not displayed.
- Project HQ provides a local read-only viewer of handoff documents.

## Reliability changes verified in the first scheduled run

- All 23 current history files are encrypted with WX_STATE_KEY. Exact original
  compressed bytes and 126,109 rows are preserved. CI decrypts in memory; public
  exports force forecast values off. Local decrypt is documented in SETUP_CLOUD.md.
- Prepare a day at >=80% coverage of configured stations x24 UTC hours. Retry
  incomplete days until day-end +72h, then record coverage and late-finalization.
- Push history first, verify exact files/metadata in origin, then prune only the
  confirmed days and publish encrypted state with a lease. Failures remain recoverable.
- Only an absent state branch starts fresh; restore/decryption failures abort.
  Source failures mark the run red after saving data and publishing health.

## Verification and last checked live state

177 local/cloud tests pass (154 before the monthly summary). Project HQ: 7 passed, 1 Windows symlink skip. Failure
recovery was exercised with temporary Git remotes. All 58 generated page JSON
files match pre-encryption exports except generation time; original scores unchanged.

Last checked live cloud run: 36497119777, 28 Sep 23:16 UTC, all steps and sources
successful. Page health matches; 7 of 8 runs in 48 h after a 9 h 21 min gap.
No new scored day was ready, so new coverage metadata was not exercised.
Monthly summary is live. Verification heartbeat is paused.

## Limits and next actions

Compare cloud/local coverage before retiring the PC collector. Current-file encryption does not remove old plaintext commits/caches;
coordinate that cleanup separately. Preserve a secure backup of WX_STATE_KEY,
which now protects scored history as well as pending forecasts.

Model findings remain preliminary, especially after the sampling change and for
ECMWF. Height adjustment uses proxy terrain and a fixed lapse rate; AIFS hourly
rain is interpolated. NEXT_STEPS.md holds open work; DECISIONS.md holds policies.
