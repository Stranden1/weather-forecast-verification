# Next steps

_Updated 2026-09-23_

The temperature/wind dashboard, fair Overall Accuracy and Model Disagreement are
complete. A newer WeatherNext run (15 September 18:00 UTC) is present in the live
history; the earlier first-new-cycle follow-up is satisfied by stored data.

1. Accumulate more paired model cycles before drawing conclusions; use shared counts
   and one lead bucket when assessing daily changes.
2. Hourly precipitation scoring is implemented. Continue gathering independent
   rain events and reviewing wet-hour/event metrics alongside all-hour MAE.
   Pressure, direction and cloud cover still require observed ground truth.
3. Revalidate wind height/unit metadata when changing the station network or collectors.
4. The validated dashboard/backfill/collection-health work is grouped in a local
   Git checkpoint. Push it when desired; keep runtime data and provenance manifests local.
5. Maintain separate local database and credential backups.

Collection health is complete. While all sources show OK, no intervention is
needed. If Yr becomes Delayed or Stale, inspect the collapsed collection logs and
scheduled-task result promptly because missed historical Yr forecasts may not be
recoverable. The next ordinary scheduled run will begin emitting explicit
per-source completion lines; legacy combined success lines remain supported.


## Historical temperature backfill: complete

The requested focused archive retrieval, duplicate/preservation checks, identical
second run and retrospective 3/5/7/9-day analysis are complete. Read
`outputs/temperature-backfill/REPORT.md` for results and repeat commands. Keep
`work/temperature-backfill/first-run.json` and `second-run.json` alongside local
data: they contain original Earth Engine availability metadata.

Next validation priority is more independently collected operational cycles.
The requested retrospective view is now complete: open **Long-range temperature**.
Verified original publication makes historical temperatures eligible there;
operational scoring still requires collection before target. Continue gathering
more model cycles before treating small MAE differences as stable conclusions.
Keep the verification table with the authoritative database and retain the local
manifests as audit evidence. No further UI work is pending for this request.


## Front-page usability: complete

Automatic fair pairing and compact healthy collection status are complete and
validated. Use Comparison → Manual runs for independent inspection; the chosen
automatic runs and actual match counts remain visible. No scientific scoring or
collection changes are pending from this task. Continue normal collection and
use existing health details for any active failure. Local front-page validation
evidence is retained under work/auto-pair/.


## Precipitation analysis complete — 2026-09-22

Read work/precipitation-benchmark/REPORT.md before a separately requested rainfall
scoring/view implementation. Preserve canonical end targets, issue/retrieval
before interval start, comparable leads and error-independent deduplication.
Show wet-hour accuracy and event counts alongside all-hour MAE, actual dates and
sample counts. Expose empty 0–12h and partial 48–72h coverage. Continue accumulating
independent weather events and reviewing station biases; do not shift timestamps
to optimize scores. No implementation or further analysis is pending in this task.


## Production precipitation complete — 2026-09-22

Use Hourly precipitation in Forecast vs Actual or Overall accuracy. Existing
station, period and lead filters apply; observed dates/counts and partial coverage
are explicit. No implementation remains for this request. Preserve the canonical
interval and shared matcher if extending this later. Longer accumulations,
calibration, probability scoring, new providers/stations remain outside scope.
The worktree began with four uncommitted benchmark documentation updates; those
are preserved. This task remains uncommitted under the clean-start checkpoint
condition. No automatic push.


## Optional accumulated precipitation complete — 2026-09-23

Use Overall accuracy → Hourly precipitation → Accumulation to inspect
1h, 6h or 24h. The hourly view remains default and Forecast vs Actual
remains hourly. The 6h/24h views require complete fixed UTC periods and
one available run per provider; compare shared counts, distinct periods,
dates and actual leads before drawing conclusions. The current 24h
sample has only 160 distinct station-days in the validated snapshot.
Continue collecting independent rain events and model cycles. No further
implementation is pending for this request; calibration, probabilities
and new providers remain separate future work.

## Performance checkpoint — 2026-09-23

The WeatherNext status full scan has been removed from routine dashboard
reruns. Exact counts are available on request in the status expander; source
health remains live. The validated 6h/24h precipitation commit was pushed
before this optimization. The optimization commit remains local.

All-station precipitation and long-range temperature query optimizations are
complete with exact pair and metric reproduction. Long-range is now about 1.5 s
all-station/all-history; all-station rainfall remains about 5–6 s. The next
performance task, if requested, is a separate all-station precipitation query
optimization targeting narrower candidate reads while preserving exact pair
identity and all scoring rules. Do not broaden the previous changes into a
matcher or scoring rewrite.
