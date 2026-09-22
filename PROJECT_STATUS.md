# Project status

_Updated 2026-09-22_

## Summary

WeatherApp is a runnable local Windows benchmark comparing Yr/MET and Google
WeatherNext forecasts against Frost observations across 50 active Norwegian
stations. Data collection, storage, scoring, background scheduling, and the
Streamlit dashboard are operational.

## Current capabilities

- Long-range temperature retrospectively compares Yr and verified historical
  WeatherNext at 3/5/7/9 days, with actual evaluation dates and shared counts.

- Collects Yr/MET forecasts and Frost temperature, wind, and supported hourly
  precipitation observations.
- Collects 360-hour WeatherNext forecasts for the shared station network,
  including means, percentiles, precipitation, wind components, and pressure.
- Shows a compact Forecast vs Actual temperature/wind/hourly precipitation view with automatic fair
  run pairing and optional advanced manual selection,
  WeatherNext p10–p90 uncertainty, elapsed Frost observations, errors, and MAE.
- Shows station metadata/maps, overall temperature, wind and hourly precipitation accuracy, and
  WeatherNext collection status/history.
- Shows compact collection health for Yr/MET, WeatherNext, and Frost using
  completed retrieval timestamps, age, and conservative OK/Delayed/Stale states.
- Dashboard browsing is read-only; manual collection controls are separated in
  the collapsed Admin section.
- Daily-use UI polish adds consistent metric cards, compact selectors and table
  rows, softer forecast chart styling, and a horizontal MAE dot plot. Status,
  logs, and manual controls remain in compact collapsed expanders.

## Live state (read-only snapshot, 2026-09-17 local time)

- Authoritative database: `data/weather.db`; active stations: 50.
- Total forecast runs / points: 4,504 / 344,008.
- Frost observation rows: 189,084.
- Frost hourly precipitation: 13,344 station-hours at 29 active stations;
  2,243 non-zero values, 2026-08-26 16:00 through 2026-09-16 22:00 UTC.
- Latest operational WeatherNext initialization: 2026-09-16 18:00 UTC.
- WeatherNext forecast points / statistic values: 130,400 / 2,672,400.
- Includes 4,400 sparse historical temperature points at 72/120/168/216h;
  these archive runs do not contain full hourly/multivariable coverage.

## Validation

All 69 unit/regression tests pass. Front-page automatic/manual/no-pair behavior,
compact health states and existing pages pass fixture UI and live render checks. The compact retrospective and collection-health views also passed
fixture interaction tests and a live browser check. The additive verification
table contains 4,400 historical points; registration preserved all prior data. Historical temperature ingestion was repeated
with zero additions and zero duplicate keys; every pre-existing domain row was
preserved. The fixture dashboard interaction test and production-data render
also pass. Existing dependency deprecation warnings are non-fatal.

## Known limits

- Fair comparisons require shared exact-time observations and forecast leads within 3 hours in the same bucket; initial overlapping history is short.
- Hourly precipitation scoring is enabled with canonical intervals and wet/event
  context. Short leads currently have no fair samples; 48–72h coverage is partial.

## Frost hourly precipitation — 2026-09-16

- The normal Frost run now requests `sum(precipitation_amount PT1H)` only for the
  29 active stations advertising that exact element.
- Frost `referenceTime` is stored unchanged as the interval end. See
  `PRECIPITATION.md` for the cross-provider mapping.
- The historical backfill added 13,118 values without changing existing
  temperature or wind values. Repeating the same range produced no database
  changes, no duplicate keys, and no off-hour timestamps.
- No scoring, dashboard, station-network, provider, schema, or scheduled-task
  changes were made for this work.
- Accuracy becomes more meaningful as additional model cycles and observations
  accumulate.

## Collection health — 2026-09-17

- The dashboard reads finalized source outcomes from `data/background.log`, not
  forecast valid times. Existing combined summaries provide historical continuity;
  future runs add one stable completion line per source.
- The Windows task is scheduled every 6 hours. Health is OK through 8 hours,
  Delayed through 12 hours, and Stale / attention needed after 12 hours. A failed
  latest attempt is Delayed immediately; an absent success is Stale.
- Yr success intervals longer than 12 hours within the last 7 days are reported.
  A stale Yr state warns that missed long-range forecast history may be unrecoverable.
- Current state at validation: Yr/MET, WeatherNext, and Frost all OK; last success
  2026-09-17 04:13 UTC; no recent Yr gap detected.
- No schema, schedule, provider, scoring, station-network, forecast, or observation
  history changes were made.

## Version control — 2026-09-16

Private remote: https://github.com/Stranden1/weather-forecast-verification.
Code, tests, setup scripts, docs and a 50-station metadata snapshot are versioned.
Secrets, live data, environments and scratch artifacts remain local. All 18 tests,
fixture UI test and production dashboard render passed; existing deprecation warnings
are non-fatal. Application code and scheduling were not changed for Git setup.


## Accuracy dashboard expansion — 2026-09-16

- Forecast vs Actual supports temperature and wind speed, exact-time Frost values,
  uncertainty bands, run/lead information, individual errors and matched MAE.
- Overall Accuracy filters variable, valid-time period, station and existing lead
  bucket; shows paired MAE, bias, shared count, MAE difference, daily trends and details.
- Model Disagreement ranks future latest-run differences and opens a chosen station,
  variable and run pair in Forecast vs Actual.
- SCORING.md records the variable audit, matching rules and limitations. Rainfall,
  pressure, direction and cloud scoring remain disabled.
- Audit validation: 27 regression tests; expanded disposable-database UI test
  (including no writes); live browser checks of wind accuracy, forecasts and
  disagreement navigation. Production queries took about 0.7 seconds per variable
  for all-history matching plus the 72-hour disagreement query.
- Source changes are local and uncommitted; no push was requested for this task.


## Historical temperature comparison — 2026-09-17

Backfilled 34 WeatherNext initializations from September 5 12:00 to September 13
18:00 UTC, selecting only 88 temperature images needed by existing long-range
Yr/Frost cases. All six statistics were added for all 50 active stations.

Retrospective shared counts at 72/120/168/216h: 1,603 / 1,215 / 824 / 438.
Yr MAE: 1.077 / 1.325 / 1.490 / 1.532 °C; WeatherNext MAE: 1.065 / 1.300 /
1.708 / 1.720 °C. Both leads are within nominal ±3h and pair gaps ≤3h. These
short-period results need cautious interpretation; WeatherNext usually has a
roughly 2.4-hour shorter lead. Original Earth Engine availability is verified,
but local collection occurred later, so production scoring still excludes the
backfilled points from operational long-range matches. Its rules are unchanged.

Full local report, lead distributions and individual cases:
`outputs/temperature-backfill/REPORT.md`. The source helpers and tests are local,
uncommitted additions. No UI, schema, other collector or scheduling changes.


## Retrospective view available — 2026-09-17

The **Long-range temperature** tab now uses database-persisted historical
verification. Original publication before target makes certified archive points
eligible for this retrospective view; truthful local retrieval dates remain
unchanged. The separate operational views keep their existing rules. A compact
four-row table shows MAE, difference, shared count and each horizon's evaluation
period, with station/window filters and expandable bias/lead details. See the
latest WORK_STATUS.md checkpoint and SCORING.md for validation and semantics.


## Validated Git checkpoint — 2026-09-17

The mixed dashboard/scoring/backfill/health worktree was reviewed and validated as
one coherent checkpoint. All 51 tests, fixture dashboard interactions and a live
read-only dashboard render passed, including long-range temperature and Collection
health. No application behavior or live data was changed during checkpoint review.
The checkpoint message is `Checkpoint long-range verification and collection health`;
use Git history for its hash. No push was requested. Earlier uncommitted notes above
record the state at the time of each implementation task.


## Front-page usability — 2026-09-22

Forecast vs Actual defaults to **Automatic fair pair** for the station, variable
and chart window. It reuses the operational matcher: exact shared Frost targets,
issued/collected before target, same lead bucket and a maximum 3-hour lead gap.
Among pairs with observations, the newest pair is chosen by older initialization,
then newer initialization and stable run IDs. Errors and sample counts do not rank
pairs. If no observed pair exists, a fair future pair is preferred; missing matches
have a concise data-based explanation. Independent dropdowns remain in Advanced /
Manual run selection, and disagreement drill-through enters Manual runs.

Healthy collectors occupy one status line and a collapsed details panel. Active
source delays/failures and stale Yr warnings remain prominent; resolved recent gaps
remain in details. Thresholds, logging, collectors, schema and history are unchanged.
The existing dashboard process was restarted once to clear stale Python imports;
no scheduled collection task was changed or restarted.


## Exploratory precipitation benchmark — 2026-09-22

Read-only analysis completed; precipitation production scoring remains disabled.
The snapshot has 17,160 Frost rainfall hours at 29 stations. Fair 12–24/24–48/
partial 48–72h sample counts are 3,116/4,244/3,359; 0–12h is empty under strict
availability and same-bucket rules. Both issue and collection precede interval
start; canonical interval mapping and <=3h lead gaps are preserved. Yr has lower
all-hour MAE, WeatherNext lower wet-hour MAE and more hits but more false alarms.
Dry hours dominate; only one week is paired. Data structure/alignment supports
careful future implementation, not a stable winner claim. Full local evidence:
work/precipitation-benchmark/REPORT.md. No production code or data changes.


## Production precipitation — 2026-09-22

Hourly precipitation is available in the existing Forecast vs Actual and Overall
accuracy selectors. Automatic/manual comparisons share one fair precipitation
matcher, reusing the established closest-lead infrastructure. Charts align Yr,
WeatherNext mean and Frost to physical interval end; no rainfall uncertainty band.
Wet-hour MAE, all-hour MAE, bias, POD, FAR and CSI appear with counts/dates and
actual lead ranges. Dry-hour context is shown once per view; no winner/combined score.

Read-only snapshot 2026-09-22 16:24 UTC: 0/3,232/4,417/3,501 shared pairs in
0–12/12–24/24–48/partial 48–72h, 29 stations in each populated bucket. The original
10,719 benchmark pairs reproduce exactly; two additional fixed-period pairs are
newly filled observations. Temperature/wind/long-range outputs are unchanged.
69 unit tests and expanded fixture UI checks pass. No database, collector,
schedule, station or secret changes. Only the dashboard process was restarted.
