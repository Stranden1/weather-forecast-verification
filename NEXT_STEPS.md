# Next steps

_Open items only. Remove an item when it is done and record it in `CHANGELOG.md`.
Updated 2026-10-11._

## Open items

### Needs the user
1. **Windows task kept running (checks 6, 8 and 11 Oct).** For 26 Sep - 1 Oct the cloud missed 7% (26 Sep)
   rising to 26-28% (29 Sep - 1 Oct) of the 6 h - 2 day station-hours the PC scored, because GitHub
   ran the 6-hourly slots late or not at all. Values agree where both have the same forecast.
   8 Oct check (7 Oct, 45 shared stations): cloud 92-93% of the PC overall, 99.9% on horizon
   slots the timer covered; all forecast gaps predate the timer (CHANGELOG.md, 8 Oct entry).
   11 Oct check (9-10 Oct; results `work/coverage-compare/2026-10-09_10.json`, ignored): timer-era
   coverage 100.0% at every horizon the timer has reached (6 h - 2 d both days, 3 d on 10 Oct),
   Yr and WeatherNext. Overall Yr 100.0/98.3%, WeatherNext 98.4/95.2%; every gap is at 3-10 days
   on forecasts fetched before the timer. The 5, 7 and 10 day horizons are not timer-era yet: first
   fully timer-era target days are 12, 14 and 17 Oct. Final check ~18 Oct:
   `python work/coverage-compare/compare_cov.py 2026-10-15 2026-10-16 2026-10-17`, with a fresh
   `$TMP/obs.enc` from `git show origin/state:obs.csv.gz`. Stop the task only when timer-era
   coverage stays >=99% at every horizon and the user approves.
   Keep `data/weather.db`.

### Pipeline
2. **Station freshness and network drift.** Cloud/local networks overlap at 45/50 stations.
   Local weekly discovery changes the active database network; cloud uses a fixed snapshot.
   Reconcile deliberately while preserving history. Investigate SN1120 (Enningdalen) and
   SN20925 (Wisting): latest cloud observations are 30 Sep 23:00 and 21:00 UTC respectively;
   SN1120 is also stale locally. Add per-station freshness/coverage warnings so overall
   Frost OK cannot hide missing stations. Do not silently remove them from scoring history.
3. **Measure the activated timer.** Job 8590224 is enabled with :07/:37 UTC POST
   requests and failure/recovery/disable notifications. External test returned 204;
   run 37495000121 succeeded and correctly skipped at 65 min. Verify recurring HTTP
   204 responses, a timer-triggered collection once >=150 min old, and an advancing
   public health timestamp. Then evaluate several days of coverage. GitHub hourly
   fallback remains; prior gaps reached 9 h 21 min. Renew the repository-only token
   before 5 Nov 2026 (expires 17:15 UTC); enter it directly in the timer, never chat/files.
4. **Old plaintext history:** coordinate cleanup of earlier public Git commits/caches if
   publication protection requires it; no main-history rewrite has been performed.

### Features
- **ECMWF IFS and AIFS on the page**: collected and scored from 27 Sep (not shown yet). Once
  a week or two of scored days exist, add them to the horizon chart/table. AIFS hourly rain is
  a 6-hour amount spread over the hours: compare it on 6 h totals, not hourly.
5. **Replays with incomplete WeatherNext (idea, needs the user):** 15 Sep (46.8 mm at Bergen) is
   left out because WeatherNext has 4 of 24 hours; Yr has full totals. Show Yr-only points, or explain.
- **Show the differences (agreed plan, 11 Oct; AgnosticBrain `plans/weatherapp-dashboard.md`).**
  Steps 1 ("Both, averaged" tile) and 2 ("Which way do they miss?" card) are done and pushed 11 Oct
  (WORK_STATUS.md, CHANGELOG.md). Remaining, with the agreed choices:
  - Step 3 "Biggest differences" in the map panel when no station is selected: 3 stations per
    service, at least 7 days of data, page only (stations.json as it is).
  - Step 4 station freshness: `last_obs` per station in meta.json; warn in the health line and
    grey-ring the map marker after 2 days without measurements (covers item 2's warning part).
  - ECMWF on the page stays deferred (item above).
6. **Rain median on the remaining rain views:** the map, "Over time" chart and "Patterns" table still
   use WeatherNext's average; the headline views now lead with the median (done 28 Sep).
7. **Revisit the results** at about 30 paired days, and again once winter arrives. Watch whether
   the height adjustment over-warms cold valley stations (Røros, Dividalen, Grønliheia).

### Housekeeping
8. `scoring/scorer.py` still holds the old hour-floored join (`strftime` on `observed_at`),
   off the dashboard path. Mark it deprecated or remove it.
9. `work/` holds ~20 MB of local evidence. Keep `work/temperature-backfill/first-run.json` and
   `second-run.json` (original availability metadata); the rest can be archived.
10. Address dependency deprecation warnings before library/Python upgrades (NumPy timedeltas,
    pandas concatenation and boolean inversion in replay filtering).
11. Correct stale publication wording in SETUP_CLOUD.md: it still says the workflow forces
    forecast values off, although the repository variable enables past values.

## Standing reminders
- Past WeatherNext values are live (`WX_PUBLISH_FORECAST_VALUES=1`, verified 5 Oct);
  only target times at least 1 h old may be shown. Set the variable to 0 to disable them.
- Watch the first workflow run after the announced 19 Oct Ubuntu runner image change.
- Both working state and scored history use `WX_STATE_KEY` (GitHub secret, local `.env`).
  Losing all key copies means losing access to both. Keep a separate secure key backup.
- Restart the local Streamlit dashboard before any manual WeatherNext fetch from Admin; a
  running process keeps old code in memory.
- If Yr collection becomes Delayed or Stale, check promptly: missed Yr history cannot be recovered.
- Revalidate wind height/unit metadata when changing the station network or collectors.
- Keep separate backups of `data/weather.db` and credentials; GitHub holds neither.
- Setting GitHub secrets from PowerShell 5.1 by piping adds a BOM; use `gh secret set --body`.
