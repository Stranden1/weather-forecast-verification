# WeatherNext integration checkpoint — 2026-09-15

## Forecast steadiness (PLAN_REPLAYS step 1) — 2026-09-25 (Claude)

New `cloud/replay.py`: `steadiness(scored, var)` gives the revision size per horizon
step, the share of revisions that moved toward the observation, flip-flops per 100
forecasts, and a day-block bootstrap on the revision difference. `summarize.build`
writes `steadiness.json`. The page does not show it yet (step 3). 35 cloud tests pass.
The history files were only read. Plan and results: PLAN_REPLAYS.md. Git works here
only through GitHub Desktop's `git.exe` (not on PATH). Not pushed.

## Cloud pipeline improvements — 2026-09-24 (Claude)

Added the naive "same as before" baseline and skill score, a pinball score and range
width for the uncertainty ranges, and a health line under the page title. Details are
in PLAN_WEBPAGE.md → "Improvements". New: `cloud/health.py` and
`cloud/tests/test_improvements.py` (17 tests; 25 in total pass). Checked the page with
`python -m cloud.demo` (`site/index.html?demo`) and with the real history. Existing
`history/` files are untouched. Review changes: baseline offset from the actual lead,
skill as a percentage, Days/Forecasts columns removed from the horizon table. No
history files had been written since the baseline change, so none were regenerated.
Pushed after the user's OK.

Found uncommitted work by another assistant in `cloud/migrate_sqlite.py` and
`cloud/tests/test_pipeline.py`: a `--from … --fill-missing-wn` option that replaces
cloud day files without WeatherNext with the PC copy. It was not documented, and its
test passes. It is kept and committed as its own commit, separate from this work,
so the user can review or drop it before pushing.

## Cloud pipeline commit and secret scan — 2026-09-23 (Claude)

Fixed the Codex sandbox "setup refresh had errors": `.git` was owned by
`CodexSandboxOffline`, so the non-elevated setup could not add its deny ACE.
The user reset the owner of `.git` to their own account.

Scanned all Git history and all uncommitted files for secrets. No `.env` values
or keys were found, and `.env` has never been committed. The EE key is used only
in memory. Moved the workflows from `cloud/github-workflows/` to
`.github/workflows/`. `cloud/tests` pass (8). Committed the pipeline code, then the
docs, as separate commits.

Deployed the same day: pushed, made the repo public, Pages source set to GitHub Actions,
all four secrets set. The first manual run collected no Yr data because the secrets had a
BOM from a PowerShell pipe; after they were set again, run 2 gave yr=1400, obs=3530,
wn=0. WeatherNext is blocked by a missing IAM role (user action, see NEXT_STEPS).
The migration (`--until 2026-09-23`, read-only) wrote 18 day files for 09-05..09-22.
`weather.db` was only read. The Windows task is unchanged and should keep running
in parallel.

## Forecast vs Actual history window investigation — 2026-09-23

Completed a read-only reproduction for Trondheim-Voll. Forecast vs Actual offers
72 h, 7 days, and Full run; it has no 24 h option. The selected run query is
bounded by run IDs, not a requested historical observation window. Both forecast
series and Frost observations are joined over the selected runs' valid timestamps,
then 72 h/7 days clips the chart from the earliest valid timestamp. The reproduced
automatic pair was the newest fair observed pair (Yr issue 22 Sep 21:31 UTC,
WeatherNext issue 23 Sep 00:00). Forecast rows spanned 22 Sep 22:00–8 Oct 00:00;
the plotted 72 h and 7 day extents ended 25 Sep 22:00 and 29 Sep 22:00. Frost
observations available in the pair ended 23 Sep 16:00. Older observations have
no forecast points in these selected runs, so this is not a query or x-axis loss.
Run coverage and newest-pair selection explain the short historical portion.

Added a concise UI caption explaining the span origin, limited elapsed history,
and how Manual runs can inspect older forecasts. No scoring, pairing, query,
database, or scientific behavior changed. The full regression suite and dashboard
fixture interaction check passed. Separate checkpoint commit created; no push.

## All-station precipitation optimization — 2026-09-23

Completed the first bounded query optimization. Baseline on a fixed 7-day,
all-station snapshot took 6.60/8.71 s for 1h, 8.74/8.58 s for 6h, and
8.51/8.60 s for 24h (first/repeat calls). Query timing showed the WeatherNext
sample read dominated (5.7–7.7 s); `EXPLAIN QUERY PLAN` showed a full scan of
the 12.1m-row `weathernext_samples` table. A disposable SQLite copy confirmed a
partial expression index on `julianday(valid_at), run_id`, restricted to hourly
precipitation means in mm, serves a bounded search while retaining the existing
forecast primary-key lookup.

Retained that additive index and the equivalent `julianday(s.valid_at)` bound in
the WeatherNext sample SQL. The index was created transactionally in the
authoritative DB; `weathernext_samples` stayed at 12,122,400 rows and the query
plan uses the new index. Pair CSVs and metric records are identical for all
three modes: 12,225 hourly pairs, 2,255 six-hour pairs, and 351 daily pairs.
Production first/repeat timings: 3.94/6.05 s (1h), 6.01/5.86 s (6h), and
5.89/5.97 s (24h), about 31–35% lower on average. The audit's ~7.9 s baseline
is reduced but the 1.5 s target is not met.

Two further candidates were rejected after disposable-copy tests: a wider
covering sample index and a forecast-time expression index driving the join.
Neither materially improved the read. Three implementation attempts were used;
stop here rather than risk restructuring pair/scoring logic. Full suite: 79
tests passed. Expanded fixture UI passed with zero DB writes. No collection
behavior, stations, scoring rules, history, schedule, or secrets changed. Local
checkpoint commit created, not pushed.

## Long-range temperature query optimization — 2026-09-23

Completed three bounded iterations against fixed all-history, 7-day, 24-hour,
and Trondheim-Voll snapshots. Baselines were 7.06/7.58/5.74 s for all-station
all-history/7-day/24-hour and 6.11/5.18 s for Trondheim-Voll all-history/7-day.
The verified-history query returned 4,400 rows but SQLite began from all provider
runs and walked the 12.1m-row sample table. A `CROSS JOIN` loop-order constraint
starts at the 4,400-row manifest and uses existing run/time primary-key probes;
its exact result is unchanged and its query time fell from 2.6–4.9 s to 13–29 ms.

The existing inclusive 69–219 h stored-lead filter is now also applied in SQL
before Pandas materialization. This preserves the post-load filter and timestamp
consistency check. The Frost observation read now adds the selected station and
date bounds directly in SQL, removing its prior all-station read for a single
station. For all five fixed combinations, every paired row and all four horizon
summary records match the saved pre-change output exactly. Final first-pass
fixed-snapshot times: 1.51 s (all history), 1.13 s (7 days), 0.73 s (24 h),
0.15 s (Trondheim-Voll all history), 0.13 s (Trondheim-Voll 7 days). A broader
read-only profile later measured 2.88 s all-station/all-history and 0.15 s for
one station; no cache is used.

Validation: full suite 79 tests; expanded fixture dashboard interaction and
zero-write checks; production read-only profiles for Forecast vs Actual,
automatic pairing, Overall Accuracy, precipitation 1h/6h/24h, Long-range,
Model Disagreement, collection health and WeatherNext status. No database rows,
scoring rules, station network, collectors, scheduling, or secrets changed for
this target. The precipitation target's one additive index is documented above.
Checkpoint commit created locally, not pushed. Remaining largest bottleneck is
all-station precipitation at about 5.6 s; further query work should be separate.

## Completed

- Added concise project handoff documents: `PROJECT_STATUS.md`, `NEXT_STEPS.md`,
  and `DECISIONS.md`. They reflect the live database and scheduled collection
  state as of 2026-09-16.
- Dashboard compact-layout pass completed: Forecast vs Actual is the first tab,
  with station/run/window selectors on one row, compact metrics, a 72-hour default
  chart, amber Frost actuals, WeatherNext p10–p90 shading, recent results and MAE.
  Network and overall accuracy are separate tabs; supported Streamlit versions
  load tab bodies only when selected. Manual actions/settings are in collapsed
  **Admin / Manual controls**. WeatherNext status is secondary and logs collapsed.
  Dashboard startup no longer seeds or migrates the database: browsing uses a
  read-only connection. Collectors, schema, historical data and scheduling were
  not changed. All 18 regression tests passed. The new fixture UI test verifies
  selection changes, future-observation masking, collapsed Admin and zero data writes.
  A dashboard-only read query now precomputes observation-hour keys while retaining
  the original scoring rules; production reads completed in approximately 2.3 seconds
  for temperature and 5.2 seconds for wind. Accuracy bars are grouped by provider,
  not stacked. The browser layout was checked at 1280×720 with real stored data.
- Added a read-only **Forecast vs Actual** temperature section to the Streamlit
  dashboard. It defaults to Trondheim-Voll, offers independent recent Yr/MET and
  WeatherNext run selectors, overlays hourly Frost observations and WeatherNext's
  p10–p90 interval, lists elapsed-hour errors, and compares MAE by lead-time bucket.
  All 17 tests and the disposable-database Streamlit startup check pass. A read-only
  production check confirmed the default view has both current runs, 360 temperature
  timestamps, a complete uncertainty band, and matched elapsed Frost hours.
- Added a compact, read-only WeatherNext dashboard status panel backed by the
  authoritative database and finalized WeatherNext entries in `data/background.log`.
  It shows stored run/row totals, collection timing and additions, collector state,
  and the 15 most recent WeatherNext background outcomes in a collapsible table.
- The authoritative `E:\WeatherApp` was updated incrementally; no database was replaced.
- New collector, CLI, app control, and guarded background integration are installed.
- Additive `weathernext_samples` table and `weathernext_values` view are installed.
- Temperature, wind speed and hourly precipitation: mean plus five percentiles.
  Wind u/v means and mean sea-level pressure are included with explicit units.
- Earth Engine authenticated successfully against `weatherapp-508323`.
- All 13 tests passed in the original Python 3.13.15 environment, SDK 1.7.43.
- Streamlit startup passed on a disposable database; WeatherNext control is present.
- Live run 2026-09-15T06:00:00Z passed 360-hour validation for Trondheim-Voll,
  three stations and all 50 active stations. Full repeat for Trondheim added zero rows.
- 50 WeatherNext runs, 18,000 forecast points and 378,000 statistic values are stored.
- Initial historical rows were unchanged immediately after the full live test.
- A later ordinary scheduled MET/Frost run was reconciled: no rows lost; two
  missing measurements filled; five source-check timestamps refreshed. The newer
  authoritative data was preserved.
- `.env` now sets `EARTH_ENGINE_PROJECT=weatherapp-508323` and `WEATHERNEXT_ENABLED=1`.
- The existing Scheduled Task was inspected, not modified or restarted. It already
  targets the correct Python, script, working directory and user account.

## Dashboard completion — 2026-09-16

Compact dashboard work is complete. Final validation: all 18 regression tests and
the disposable-database UI test passed; grouped accuracy bars were checked in the
browser with production data. No dashboard migration, collector change, scheduled
task change or historical-data write was performed. No dashboard work remains.

## UI polish completion — 2026-09-16

- Completed the focused daily-use visual pass in `app.py`: balanced compact run
  controls, subtle consistent metric cards, refined thinner forecast lines and
  softer uncertainty band, compact horizontal MAE dots with provider shapes,
  26px result rows with one-decimal numbers and missing-value dashes, and
  collapsed system status/logs/admin sections. Existing tabs and scoring remain.
- Validation: all 18 regression tests and the existing disposable-database UI
  interaction test pass (including no database writes). Live browser review
  confirmed the chart, table, cards, and collapsed operational sections.
- Complete; no UI work remains. Database, schema, collectors, secrets, and
  scheduled task were not modified. Operational follow-up remains below.

## Remaining

No manual setup or integration work remains. The enabled WeatherNext branch ran
successfully in the ordinary scheduled collection beginning 2026-09-15 22:10 UTC.
It selected the already-stored 12:00 UTC model run and correctly added zero values;
the dashboard now reports **waiting for new run**. The next operational check is a
scheduled collection of a genuinely newer model cycle.

Rainfall is stored with units in the normalized table. Rainfall scoring/interval
alignment with MET and Frost was not part of this first integration and is not enabled.

## Resume evidence

- `work/integration-status.json`: final integration state.
- `work/live-validation.json`: completed live stages and WeatherNext row counts.
- `work/history-before.json`: original history baseline (retain unchanged).
- `work/history-after-live-validation.json`: exact preservation after live testing.
- `work/scheduled-update-reconciliation.json`: expected later background additions.
- `work/history-after-scheduled-before-enable.json`: subsequent validated baseline.

The application is runnable and all migrations are complete. To disable only
automatic WeatherNext collection, set `WEATHERNEXT_ENABLED=0`; retain its schema
and history. Do not restore an older database over the current database.

## GitHub setup checkpoint — 2026-09-16

- Initialized Git in place; application behavior and scheduled task unchanged.
- Private remote: https://github.com/Stranden1/weather-forecast-verification
- Ignores cover secrets, environments, runtime data, logs, screenshots and scratch work.
  No local database, backups or working files were removed.
- Updated README/quick start; retained the fixture UI test under tests/ and exported
  50 active stations as metadata in config/stations.json (not auto-imported).
- All 18 regression tests, fixture UI test and production dashboard render passed.
  Staged secret scan found no local credential values or recognized token/key patterns.
- Complete: initial commit ef2871b pushed to main; private visibility verified. Remote commit/tree matched locally, with 37 code/config/documentation files and no runtime data. No GitHub setup work remains.


## Accuracy dashboard checkpoint — 2026-09-16

Completed: variable audit (SCORING.md); wind Forecast vs Actual; exact-time observed
values; paired Overall Accuracy with variable/period/station/lead filters, MAE,
bias, equal sample counts, MAE difference and daily trends; future Model Disagreement
with station/run navigation. Existing scoring buckets/aggregation are reused.

Validated: 27 unit/regression tests; expanded fixture UI test including all new
controls, empty states, drill-through and unchanged fixture database; live local
Streamlit startup and browser checks with production data. No browser page errors.
All-history pairing plus disagreement queries took about 0.7 seconds per variable.
The read-only audit found 785 temperature and 676 wind station/time/bucket pairs;
counts will grow as normal collection continues.

No database migration or historical-data write, collector change, task restart,
credential change or new provider. Application remains runnable. Existing runtime
deprecation warnings are non-fatal. Files are local, not committed/pushed in this task.

Remaining: no requested dashboard feature is pending. Continue ordinary collection,
then evaluate longer matched history. Precipitation/pressure/direction/cloud scoring
remain deliberately disabled pending compatible observations/definitions. The newer
15 September 18:00 WeatherNext cycle is stored, satisfying the earlier cycle follow-up.

## Frost hourly precipitation checkpoint — 2026-09-16

Completed: the existing Frost collector now requests
`sum(precipitation_amount PT1H)` only for capable active stations and stores it in
the existing `observations.precipitation_1h` field. Frost `referenceTime` remains
the canonical end of `[T-1h, T)`. The normal `sync_recent` and background path now
include precipitation; temperature and wind collection is unchanged.

Production backfill: 13,118 station-hours across 29 of 50 active stations, from
2026-08-26 16:00 through 2026-09-16 14:00 UTC; 2,162 values are non-zero. Total
observation rows are 184,259. Existing non-null temperature and wind counts are
168,873 and 168,580 after a normal collection run. An exact-range rerun changed
none of these counts; duplicate keys and off-hour precipitation rows are both zero.

Alignment sanity check: for Bergen-Florida (`SN50540`) and
`[2026-09-15 23:00, 2026-09-16 00:00 UTC)`, Frost stores 10.1 mm at end time
00:00, WeatherNext stores 3.373389 mm at end time 00:00, and Yr/MET stores
6.6 mm at start/`valid_at` 23:00. These are three forecasts/measurements for the
same physical hour, not an accuracy score.

Validation: 31 focused tests pass. They cover exact Frost metadata, supported
station filtering, timestamp preservation and cross-provider interval mapping,
merge preservation, rejection of incompatible intervals, and idempotency. The
ordinary combined Frost run completed with no errors. No schema, scorer,
dashboard, station-network, provider, secret, or scheduled-task changes were made.

Remaining before rainfall scoring: teach the scoring path to compare by canonical
interval end (`Frost T = WeatherNext T = Yr valid_at + 1h`) while enforcing the
existing retrieved-before-target rule, identical observed targets, and comparable
lead times. Rainfall scoring remains disabled.

## Collection health checkpoint — 2026-09-17

Completed: a compact dashboard table now shows Yr/MET, WeatherNext, and Frost last
successful retrieval, UTC-safe age, and OK/Delayed/Stale state. It is placed above
the existing tabs; WeatherNext details, collection logs, and manual controls remain
collapsed. The table reads actual completed collection outcomes rather than valid
forecast/observation times.

The existing six-hour Windows schedule was inspected and left unchanged. Thresholds
are OK through 8 hours, Delayed above 8 through 12, and Stale above 12. A latest
source error yields Delayed immediately. Stale Yr displays the unrecoverable-history
warning. Recent Yr gaps are consecutive successes more than 12 hours apart in a
7-day window.

For historical continuity, the parser reads existing finalized combined log lines.
Going forward, `background_collect.py` appends a stable source-level outcome as
each collector completes, so a later Frost or WeatherNext failure cannot hide a
successful Yr retrieval. Missing credentials/disabled collection are recorded as
SKIPPED and do not advance last success. No database schema was added.

Validation: 51 unit/regression tests pass; the isolated background-run test records
all three source completions; the disposable Streamlit test verifies healthy and
stale rendering, the exact Yr warning, long-range temperature behavior, and zero
database writes. Production is currently OK for all three sources with last success
at 2026-09-17 04:13 UTC and no recent Yr gap. Database counts remain 4,504 runs,
344,008 forecast points, and 189,084 observation rows.

Remaining: no feature work is pending. The next ordinary scheduled run will be the
first production run to emit the new explicit per-source lines; legacy summaries
remain sufficient until then.


## Historical WeatherNext temperature checkpoint — 2026-09-17

Completed: focused 0.05° station-head archive backfill for the existing 50 active
stations, using existing normalization/storage and six temperature statistics.
34 initializations (2026-09-05 12:00 through 2026-09-13 18:00 UTC), 88 selected
image slices, and leads 72/120/168/216h added 4,400 forecast points, 1,700
station/run rows and 26,400 statistic values. Valid range: 2026-09-08 12:00
through 2026-09-16 18:00 UTC. These historical runs contain sparse temperature
horizons, not full hourly/multivariable forecasts.

Identical second execution added zero values. Duplicate run/point/statistic keys
are all zero. Before/after row-content checks preserved every existing station,
run, forecast, observation and WeatherNext statistic. MET remains 209,254 points;
WeatherNext grew 108,000 → 112,400; Frost temperature/wind/precipitation remain
171,313 / 171,037 / 13,344 non-null values. No migration was required.

Read-only retrospective shared counts at 72/120/168/216h: 1,603 / 1,215 / 824 /
438. Yr MAE: 1.077 / 1.325 / 1.490 / 1.532 °C; WeatherNext mean MAE: 1.065 /
1.300 / 1.708 / 1.720 °C. Exact Frost targets, both nominal ±3h and pair gap ≤3h,
one error-independent closest-lead pair per station/target/horizon. Largest gap:
2.677h. All 50 stations contribute at each horizon. The short period and usually
shorter WeatherNext lead limit conclusions, especially the tiny 3/5-day gaps.

Original Earth Engine ingestion was checked before each valid time and retained
in local manifests. Local retrieved_at stays truthful. Production scoring still
requires local retrieval before valid time: operational long-range shared counts
remain zero. No production scorer, UI, scheduled-task, secret or other collector
changes were made for this task.

Validation: all 39 unit/regression tests pass; fixture UI interactions pass with
zero writes; production dashboard render passes with no exceptions. Existing
non-fatal dependency deprecation warnings remain.

Evidence and exact commands: outputs/temperature-backfill/REPORT.md. All 4,080
matches, aggregate metrics, actual lead distributions and four individual cases
are saved as CSV/JSON there. Plans, original image metadata, preservation checks
and logs are retained under work/temperature-backfill/. Both folders stay local
and ignored. Reusable helpers are backfill_weathernext_temperature.py and
analyze_historical_temperature.py; coverage is in test_weathernext_backfill.py.
Source/doc changes are local and uncommitted; no push was requested.

Remaining: none of this task. Continue operational collection for live-collected
long-horizon validation. Dashboard additions, rainfall and calibration scoring
require separate work. Never restore an old database to undo this additive task.


## Verified retrospective scoring and compact view — 2026-09-17

Completed: historical-verified WeatherNext temperatures now qualify for
retrospective scoring through the existing database. An additive
`weathernext_verified_history` table links each point to its verified original
publication time, exact asset, initialization, lead and mean value. Registration
checks the complete saved backfill manifest and stored station/sample identity
inside one transaction. Existing forecast values and retrieved_at are unchanged.
4,400 points registered; identical registration added zero. Before/after
row-content checks confirmed every existing station, forecast and observation
was preserved; foreign-key checks passed. Future saved temperature backfills
register their verified provenance automatically.

The new **Long-range temperature** tab shows four compact 3/5/7/9-day rows:
Yr and WeatherNext MAE, signed MAE difference, shared sample count, matched dates,
plus the actual overall evaluation period in UTC. Filters select evaluation
window and station; an expander shows bias, actual leads, original availability
rules and counts of historical samples. No score is shown for an empty horizon.

Scoring reuses the audited exact-horizon matcher: original issue and verified
availability before target, exact Frost time, both nominal ±3h, pair gap ≤3h,
and one error-independent closest-lead pair per station/time/horizon. Missing
or inconsistent verification falls back to collected-before-target eligibility.
Operational Overall accuracy and selected-run scoring retain their existing
rules. Temperature is the only historically certified variable.

Validation: 45 unit/regression tests pass, including idempotency, conflicting
provenance rollback, missing-table compatibility, malformed leads, exact-time
observations, period/station filters, zero-sample summaries and read-only scoring.
The expanded fixture UI test passes, including historical scores, date/count
labels, filter/empty states and zero database writes. Live browser verification
confirmed the compact table and all four horizons with production data.

The database-backed scorer reproduces all 4,080 audited historical comparisons:
1,603 / 1,215 / 824 / 438 samples. Each horizon ends September 16 18:00 UTC and
starts September 8 / 10 / 12 / 14 at 12:00 UTC respectively. Scores match the prior
report exactly; read-only query plus summary took approximately 1.5 seconds.
Evidence: work/retrospective-view/ (migration checks, test logs, live summary and
screenshot). Runtime evidence and database remain ignored by Git. The existing
scheduled collection continued normally during the pause in this task.

Remaining: none for the requested retrospective eligibility/view. No new provider,
service, dependency in requirements, or collection/scheduling change. Changes are
local and uncommitted; no commit or push was requested.


## Git checkpoint review — 2026-09-17

Reviewed the complete mixed worktree against the prior implementation checkpoints.
The source/test/doc changes belong to shared accuracy and model disagreement,
historical temperature backfill, verified retrospective scoring, the compact
3/5/7/9-day view, collection health and per-source completion logging. No unrelated
or suspicious changes were found. These interdependent changes are grouped in one
checkpoint: `Checkpoint long-range verification and collection health`.

Validation at checkpoint: all 51 unit/regression tests pass; the fixture dashboard
interaction test passes, including healthy/stale health states, long-range filters
and zero database writes. Production dashboard startup and both requested views
pass with enforced read-only database connections. Current shared long-range counts
are 1,607 / 1,219 / 828 / 442; all three collection sources report OK, last success
2026-09-17 10:12 UTC. The existing .env is unchanged. No collector, backfill,
migration, scheduled-task action, or application behavior change was performed.

Only reviewed source, tests and documentation belong in this checkpoint. Database,
credentials, logs, environments, screenshots and generated evidence remain ignored
and local. Validation evidence is under work/checkpoint-review/. Commit is local;
no push is requested. No feature work remains for this checkpoint task.


## Front-page usability checkpoint — 2026-09-22

Completed: automatic fair run pairing is the Forecast vs Actual default. It uses
the existing operational matcher and prefers the newest pair with exact observed
targets in the selected station/variable/chart window. Ranking: earlier issue,
later issue, then run IDs descending; never errors or sample counts. With no
observed pair it prefers a fair future pair and explains the missing observations.
No eligible pair produces a data-based explanation and an inspection-only label.
Advanced independent dropdowns remain available in Manual runs, including older
automatically selected runs. Disagreement drill-through preserves manual choices.
Selected-run MAE describes the displayed window with the same fairness rules.

Collection health is one healthy text summary plus collapsed details. Active
failures/delays remain visible; stale Yr retains its unrecoverable-history warning.
Resolved recent gaps remain inspectable within details. Health thresholds and
source-level logging are unchanged. No database, collector, backfill, long-range
scoring or scheduled-task change. No .env edits. The existing Streamlit process
was restarted once after stale imports were detected; its browser render then passed.

Validation: all 59 unit/regression tests pass. Eight focused pairing regressions
cover older fair pairs, newest qualification, missing pairs, variables/stations,
future fallback, retrieval/bucket constraints, exact timestamps/window limits and
conflicting observations. The expanded fixture UI test covers automatic/manual
selection, no-pair messages, collapsed healthy status, resolved gaps, active/stale
Yr warnings, long-range/disagreement navigation, and zero database writes.
A live read-only snapshot confirmed operational temperature/wind and long-range
scorer output identical to HEAD. Production render and browser screenshot passed;
all production connections were enforced read-only and .env remained unchanged.

Live Trondheim-Voll example captured 2026-09-21 22:16:54 UTC (72h window):
- Independent newest runs: Yr 21 Sep 21:30:08 / WeatherNext 21 Sep 12:00;
  latest common observed target 22:00 had leads 0.498h / 10h. Zero fair matches,
  so both shared MAEs were empty.
- Automatic runs: Yr 21 Sep 03:30:15 / WeatherNext 21 Sep 06:00. Five eligible
  shared observations; Yr MAE 1.100°C, WeatherNext MAE 1.514°C. All matched rows
  retain the same bucket, exact-observation and collected-before-target rules.

Evidence is local under work/auto-pair/ (tests, live example, unchanged-score audit
and screenshot). Worktree was clean before this bounded task; only related source,
tests and handoff documentation are included in its checkpoint. No push requested.
Remaining: none for this task. Existing dependency deprecation warnings are non-fatal.


## Read-only precipitation benchmark — 2026-09-22

Complete: canonical interval-end verification on a read-only/query-only SQLite
snapshot. No production code, dashboard, database, collector, schedule or secret
change. Current Frost: 17,160 hourly values, 29 stations, 2,943 non-zero.
Fair shared counts at 0–12/12–24/24–48/48–72h: 0/3,116/4,244/3,359.
The final bucket only covers Yr 50.34–56.50h and WeatherNext 48–54h.
Both forecasts issued and retrieved before interval start, leads to the same end,
same existing AND requested buckets, gap <=3h; error-independent deduplication.
There are 4,534 distinct station/hour targets across 10,719 bucket pairs.

Yr all-hour MAE 0.171/0.167/0.162mm vs WeatherNext 0.186/0.185/0.180mm.
WeatherNext wet-hour MAE and detection are better, with substantially more false
alarms. Dry/non-event observations are 84–86%; always-zero MAE beats both models
in this short sample. All-hour MAE alone is misleading. No numeric/duplicate/
source/timestamp corruption found; station biases and timing sensitivity remain
limitations. No justified change to the canonical one-hour mapping.

13 existing alignment/fair-pair tests passed; all matched intervals verified with
canonical helpers, scalar MAE and event counts reconciled. Full method, counts,
amount/event tables, five cases, station and lag checks, readiness assessment and
CSV evidence: work/precipitation-benchmark/REPORT.md (local ignored evidence).
Ready for a separately requested implementation with explicit dates/counts and
wet/event context; insufficient history for a stable general model ranking.
Remaining: none for this analysis. No commit or push; only handoff docs changed.


## Production hourly precipitation checkpoint — 2026-09-22

Complete: first-class precipitation in Forecast vs Actual and Overall accuracy.
The new bounded scoring/precipitation.py adapter reads existing tables, shifts
Yr to physical interval end, uses WN sample-level retrievals, validates amounts/
units/leads, and calls the existing pair_forecasts infrastructure. All rainfall
summaries and automatic/manual selection share its eligibility. Both issue and
retrieval strictly precede interval start; same existing + rainfall buckets,
<=3h gap; closest leads/newest run ties; no error-dependent pair selection.

Central wet threshold is >0.1mm/hour. Production exposes all-hour MAE, wet-hour
MAE, bias and hit/miss/false-alarm/correct-dry counts, POD, FAR and CSI. Undefined
rates are missing. The dashboard puts wet MAE/event skill in context, with a
compact amount/event table, dry-hour note, actual dates/counts/stations/leads,
empty 0–12h state and dynamic partial 48–72h label. Three forecast/actual amount
series are aligned to the physical hour; rainfall uncertainty is omitted.

Current all-history snapshot 2026-09-22 16:24 UTC, 29 stations per populated bucket:
- 0–12h: no samples/scores.
- 12–24h: 3,232 pairs, 507 wet; Yr/WN MAE 0.166894/0.181293mm,
  wet MAE 0.704339/0.584580mm; POD 0.654832/0.923077,
  FAR 0.492355/0.621971, CSI 0.400483/0.366484.
- 24–48h: 4,417 pairs, 659 wet; Yr/WN MAE 0.162825/0.180188mm,
  wet MAE 0.692868/0.563616mm; POD 0.664643/0.908953,
  FAR 0.508418/0.644932, CSI 0.393885/0.342873.
- Partial 48–72h: 3,501 pairs, 485 wet; Yr/WN MAE 0.158983/0.175437mm,
  wet MAE 0.792784/0.618118mm; POD 0.569072/0.892784,
  FAR 0.535354/0.665895, CSI 0.343711/0.321217.
  Actual Yr 50.34–56.50h / WN 48–54h, not full 72h coverage.

Validation: all 69 unit/regression tests pass, including 10 new rainfall tests;
fixture UI checks cover rainfall automatic/manual, amount/event context, filters,
empty and partial buckets plus all previous pages and zero fixture DB writes.
Live AppTest covers rainfall chart/accuracy/buckets and long-range/disagreement
with every production DB connection forced read-only and .env unchanged. Browser
rendering of rainfall chart and compact aggregate/partial views passed. Dashboard
process alone was restarted to load modules; scheduled collection was untouched.

All 10,719 original benchmark pairs, run IDs, leads and values match production
on the fixed overlap ending 22 Sep 10:00 UTC. Two additional pairs at that endpoint
come from newly filled Frost observations at FV17 Våg and Nyrud, absent from the
saved benchmark snapshot. Temperature/wind and long-range outputs were identical
to HEAD on the same read-only snapshot. No DB/schema, collector, station, schedule
or secret changes. Statistical limits remain: short correlated history, unequal
leads and gauge/grid representation. No winner/composite/calibration added.

Evidence: work/precipitation-production/ (current/fixed CSVs, benchmark identity,
new-observation audit, test logs, live read-only UI audit and screenshots).
Remaining: none for this requested implementation. The four benchmark handoff
files were already modified at start; preserved and extended. Clean-start commit
condition was not met: no commit, staging or push. Existing deprecation warnings
are non-fatal. Application remains runnable.


## Precipitation Git checkpoint review — 2026-09-23

Reviewed all 13 modified/new files: hourly precipitation scoring, canonical
Forecast vs Actual, Overall accuracy, POD/FAR/CSI, associated tests and benchmark/
production documentation. No unrelated or suspicious changes found. No application
behavior, live database, credentials, collector or scheduled-task changes in this
checkpoint task.

Revalidation: all 69 unit/regression tests passed; the expanded dashboard fixture
interaction suite passed, including rainfall filters, automatic/manual selection,
partial/empty buckets, previous views and unchanged fixture history. Secret and
runtime-file scans passed. Existing deprecation warnings are non-fatal.

The user now explicitly authorized committing this previously uncommitted work.
Checkpoint message: `Checkpoint hourly precipitation verification`. All reviewed
source/tests/docs are included; local database, secrets, logs, screenshots and
analysis evidence remain ignored. Nothing remains for this checkpoint task.
No push requested or performed. Earlier uncommitted notes record prior task states.


## Optional accumulated precipitation checkpoint — 2026-09-23

Completed: 6h fixed UTC and 24h UTC-day scoring in scoring/precipitation.py,
with one run per provider, all exact aligned hours, strict pre-start issue
and component retrieval, common start-lead buckets, <=3h lead gap and
error-independent pair ordering. Central thresholds are >0.1/0.5/1.0 mm
for 1h/6h/24h. Overall accuracy has a precipitation-only selector, default
1h; Forecast vs Actual remains hourly. Counts, distinct periods, dates,
amount/event metrics and actual lead ranges are shown.

Fixed-snapshot production reproduction matches every benchmark pair and
metric: 2,110 six-hour pairs / 796 distinct station periods, and 293
daily pairs / 160 distinct station-days, 29 stations. The live read-only
6h/24h dashboard render and fixture interaction checks passed. Focused
aggregation tests cover complete boundaries, missing hours, run mixing,
availability, threshold edges, metrics, lead pairing and read-only access.
No database/schema, collector, station network, scheduled task or historical
data change. The existing hourly checkpoint was pushed to origin/main
before this work; the new implementation commit must remain local.
Validation complete: all 76 regression tests, expanded fixture dashboard UI, live read-only 6h/24h render, fixed-snapshot pair/metric reproduction and git diff --check pass. No remaining implementation work. Create the local checkpoint commit; do not push the new commit.

## WeatherNext dashboard status optimization — 2026-09-23

Completed: pushed the pre-existing validated 6h/24h precipitation commit
`51839a8` unchanged. Split WeatherNext's cheap log/latest-run summary from
exact sample/forecast counts. Routine Streamlit reruns request only the summary;
the status expander offers explicit count refresh with a check time. Counts in
the current session clear after a scheduled attempt, newer run or successful
manual WeatherNext fetch. No cache TTL is needed. Source-level collection
health remains uncached; stored backfills without a finalized success are
labelled collection unverified.

Read-only live timings: old status calls 5.27–5.36 s versus new summary
0.12–0.13 s; Station network reruns 5.48 s versus 0.22–0.23 s.
Forecast vs Actual initial render 6.82 s versus 1.42 s. Explicit exact counts
still take about 5.10 s and only run on request. The live location, run,
forecast, observation and WeatherNext sample row counts were unchanged across
profiling. Evidence: ignored work/architecture-review/status-before.json and
status-after.json.

Validation: 79 unit tests pass, including focused cheap-summary/no-backfill
tests; disposable dashboard interaction and zero-write checks pass. Live
read-only AppTest rendered Forecast vs Actual, Overall Accuracy, Long-range,
Model Disagreement and precipitation 1h/6h/24h without errors. Background
collection tests pass; the scheduled task was not restarted or changed.

Remaining: no work for this bounded status task after its local checkpoint
commit. All-station rain and long-range query costs remain separate future
optimization tasks. Do not push the new local optimization commit automatically.
