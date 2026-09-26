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


## Cloud pipeline — next (2026-09-23)

Deployed 2026-09-23; history migrated up to 2026-09-22. Open items:
- The *Service Usage Consumer* role is granted (2026-09-23). WeatherNext now fails with
  "ImageCollection asset ... not found (does not exist or caller does not have access)".
  The service account is not allowlisted for WeatherNext data, although the user's
  own account is. **User:** request access for the service account via the WeatherNext
  Data Request form or weathernext@google.com (usually 5–7 business days).
- Cloud-scored days start 2026-09-23. Horizons ≥72 h are thin for ~10 days, and
  WeatherNext is missing until the IAM fix, while the PC collector has both. Decide
  whether to replace those transition day files once from `weather.db` (this would be
  an exception to "written once").
- Done 2026-09-24: `run.py` stores and prints a per-source summary, and the page's health
  line shows each source. The workflow still stays green when a source returns 0 rows;
  consider `--strict` once all sources work.
- After pushing the 2026-09-24 improvements: baselines start filling in as the state
  builds up 12 days of observations. The 10-day horizon gets its first baselines about
  10 days after deployment.
- Setting secrets by piping from PowerShell 5.1 adds a BOM; use `gh secret set --body`. Stop the Windows task only after about a week in parallel.
Do not spend more effort on local rain-query speed; the new design replaces it.

## WeatherNext height / sampling — follow-up (2026-09-26)

- **Push needed** for the cloud collector and page to use the bilinear sampling and the
  height-adjusted line (user's OK). The PC collector already switched at 16:00 UTC.
- After the 16:10 UTC Windows run: check that `weather.db` WeatherNext values for 26 Sep 06Z+
  look sane and that `migrate_sqlite --fill-missing-wn` marks them `bilinear`.
- Revisit at ~30 paired days and in winter: the lapse correction over-warms cold-pool valleys
  (Røros, Dividalen, Grønliheia); consider flagging that on the page if it grows.
- Restart the local Streamlit dashboard before any manual WeatherNext fetch (stale imports).

## Storm replays + forecast steadiness — planned 2026-09-25

Plan: `PLAN_REPLAYS.md`, not started. It first needs the user's decision on
`WX_PUBLISH_FORECAST_VALUES` (WeatherNext terms), because replays show forecast values.
