# Project status

_Updated 2026-09-28. Current state only; history is in CHANGELOG.md._

## Summary

WeatherApp compares Yr/MET and WeatherNext with Frost at 50 Norwegian stations.
The cloud pipeline/public dashboard and local Windows collector run in parallel;
ECMWF IFS/AIFS are also collected but not yet ranked on the page. The requested
reliability and encrypted-history fixes are implemented and tested locally.
Push/deployment awaits user review; older public plaintext Git copies still need
coordinated cleanup before publication protection can be considered complete.

## Current capabilities

- Local: authoritative data/weather.db, full forecasts/observations, Streamlit
  comparisons and six-hourly collection. This task did not modify that system.
- Cloud: paired horizon snapshots, daily scoring, encrypted immutable history,
  aggregate page JSON, trends, maps, uncertainty and baseline diagnostics.
- Sampling method is recorded; height-adjusted WeatherNext remains a separate
  labelled temperature comparison. Steadiness is exported but not displayed.
- Project HQ provides a local read-only viewer of handoff documents.

## Reliability changes ready for deployment

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

154 local/cloud tests pass. Project HQ: 7 passed, 1 Windows symlink skip. Failure
recovery was exercised with temporary Git remotes. All 58 generated page JSON
files match pre-encryption exports except generation time; original scores unchanged.

Last checked live cloud run (28 Sep 13:55 UTC): all sources successful; summaries
cover 23 dates through 27 Sep. Local collection finished 16:18 UTC with status ok.
The local checkout includes scored-day commits through be13ed1. New fixes have not
been pushed; live scheduling and behavior still use the previous implementation.

## Limits and next actions

Review/authorize deployment, then verify a live cycle before retiring the PC
collector. Current-file encryption does not remove old plaintext commits/caches;
coordinate that cleanup separately. Preserve a secure backup of WX_STATE_KEY,
which now protects scored history as well as pending forecasts.

Model findings remain preliminary, especially after the sampling change and for
ECMWF. Height adjustment uses proxy terrain and a fixed lapse rate; AIFS hourly
rain is interpolated. NEXT_STEPS.md holds open work; DECISIONS.md holds policies.
