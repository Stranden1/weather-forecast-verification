# Next steps

_Open items only. Remove an item when it is done and record it in `CHANGELOG.md`.
Updated 2026-10-04._

## Open items

### Needs the user
1. **Turn on WeatherNext values** (user's decision of 2 Oct, DECISIONS.md "WeatherNext terms"):
   `gh variable set WX_PUBLISH_FORECAST_VALUES --body 1 --repo Stranden1/weather-forecast-verification`.
   Claude cannot set repository variables. Effective from the next run; set it to 0 to remove
   the values again (e.g. if Google asks). Older plaintext Git commits/caches remain accessible;
   no main-history rewrite has been performed.
2. **Windows task kept running (2 Oct check).** For 26 Sep - 1 Oct the cloud missed 7% (26 Sep)
   rising to 26-28% (29 Sep - 1 Oct) of the 6 h - 2 day station-hours the PC scored, because GitHub
   ran the 6-hourly slots late or not at all. Values agree where both have the same forecast.
   Re-run the comparison around 5 Oct for 2-4 Oct (first days with 3-hourly runs); stop the
   task with `remove_background_task.bat` if the cloud then matches. Keep `data/weather.db`.

### Pipeline
3. First reliability run and page health verified (36497119777). No new day was ready;
   check coverage metadata and new-day finalization when a future day is prepared.
4. GitHub ran schedules late or not at all: the 6-hourly one 3–5 h late, the 3-hourly one only
   8 times in 48 h (runs #33–#43, gaps 4.4–9.4 h). Since 4 Oct (once pushed) the cron fires hourly
   and a gate skips runs until the last successful collect is 150 min old (DECISIONS.md, "Hourly
   trigger"). After a few days, check the gaps between collecting runs (the page expects 16 per
   48 h) and how many hourly runs GitHub actually started; if gaps still exceed ~4 h, consider an
   external trigger.

### Features
- **ECMWF IFS and AIFS on the page**: collected and scored from 27 Sep (not shown yet). Once
  a week or two of scored days exist, add them to the horizon chart/table. AIFS hourly rain is
  a 6-hour amount spread over the hours: compare it on 6 h totals, not hourly.
5. **Storm replays and steadiness on the page:** `PLAN_REPLAYS.md` steps 2–5 (step 1 done).
6. **Rain median on the remaining rain views:** the map, "Over time" chart and "Patterns" table still
   use WeatherNext's average; the headline views now lead with the median (done 28 Sep).
7. **Revisit the results** at about 30 paired days, and again once winter arrives. Watch whether
   the height adjustment over-warms cold valley stations (Røros, Dividalen, Grønliheia).

### Housekeeping
8. `scoring/scorer.py` still holds the old hour-floored join (`strftime` on `observed_at`),
   off the dashboard path. Mark it deprecated or remove it.
9. `work/` holds ~20 MB of local evidence. Keep `work/temperature-backfill/first-run.json` and
   `second-run.json` (original availability metadata); the rest can be archived.

## Standing reminders
- Both working state and scored history use `WX_STATE_KEY` (GitHub secret, local `.env`).
  Losing all key copies means losing access to both. Keep a separate secure key backup.
- Restart the local Streamlit dashboard before any manual WeatherNext fetch from Admin; a
  running process keeps old code in memory.
- If Yr collection becomes Delayed or Stale, check promptly: missed Yr history cannot be recovered.
- Revalidate wind height/unit metadata when changing the station network or collectors.
- Keep separate backups of `data/weather.db` and credentials; GitHub holds neither.
- Setting GitHub secrets from PowerShell 5.1 by piping adds a BOM; use `gh secret set --body`.
