# Next steps

_Updated 2026-09-22_

The temperature/wind dashboard, fair Overall Accuracy and Model Disagreement are
complete. A newer WeatherNext run (15 September 18:00 UTC) is present in the live
history; the earlier first-new-cycle follow-up is satisfied by stored data.

1. Accumulate more paired model cycles before drawing conclusions; use shared counts
   and one lead bucket when assessing daily changes.
2. In a separate task, add precipitation scoring only after implementing the
   canonical interval-end join (`Frost T = WeatherNext T = Yr valid_at + 1h`),
   identical observed targets, comparable lead buckets, and collected-before-valid
   eligibility. Pressure, direction and cloud cover still require observed ground truth.
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
