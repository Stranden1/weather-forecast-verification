# Next steps

_Open items only. Remove an item when it is done and record it in `CHANGELOG.md`.
Updated 2026-10-06._

## Open items

### Needs the user
1. **Windows task kept running (5 Oct check).** For 26 Sep - 1 Oct the cloud missed 7% (26 Sep)
   rising to 26-28% (29 Sep - 1 Oct) of the 6 h - 2 day station-hours the PC scored, because GitHub
   ran the 6-hourly slots late or not at all. Values agree where both have the same forecast.
   Re-run the comparison around 5 Oct for 2-4 Oct (first days with 3-hourly runs); stop the
   task with `remove_background_task.bat` if the cloud then matches. Keep `data/weather.db`.

### Pipeline
2. **Verify the next collection uses the upgraded workflow actions and deploys Pages.**
   CI passed (37236715635); the latest collecting run checked (37231498979) used the old actions.
3. GitHub ran schedules late or not at all: the 6-hourly one 3–5 h late, the 3-hourly one only
   8 times in 48 h (runs #33–#43, gaps 4.4–9.4 h). Since 4 Oct the cron fires hourly
   and a gate skips runs until the last successful collect is 150 min old (DECISIONS.md, "Hourly
   trigger"). After a few days, check the gaps between collecting runs (the page expects 16 per
   48 h) and how many hourly runs GitHub actually started. External timer dispatch support is
   implemented locally (6 Oct); **wait for the user's OK before pushing**. Then configure the
   timer using SETUP_CLOUD.md, verify HTTP 204 and check a recent-success `trigger=timer` run
   skips while one at least 150 min after success collects. Also verify the default manual
   dispatch bypasses the gate. At the 5 Oct check, live health showed 9/16; no scheduled gate
   skip was yet verified. Check a skip leaves state/Pages untouched and adds no run record.
4. **Old plaintext history:** coordinate cleanup of earlier public Git commits/caches if
   publication protection requires it; no main-history rewrite has been performed.

### Features
- **ECMWF IFS and AIFS on the page**: collected and scored from 27 Sep (not shown yet). Once
  a week or two of scored days exist, add them to the horizon chart/table. AIFS hourly rain is
  a 6-hour amount spread over the hours: compare it on 6 h totals, not hourly.
5. **Finish storm replays and steadiness:** replay exports and the page card are implemented;
   steadiness display and remaining hand checks/review in `PLAN_REPLAYS.md` are open.
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
