# Next steps

_Open items only. Remove an item when it is done and record it in `CHANGELOG.md`.
Updated 2026-09-28._

## Open items

### Needs the user
1. **WeatherNext forecast values stay off** (policy in DECISIONS.md, "WeatherNext terms"): the
   terms don't clearly say values for past times may be published. To change that, first ask
   weathernext@google.com. Storm replays (PLAN_REPLAYS step 2) show Yr and measured values only
   until then.
   Current day files are encrypted and pushed. Older plaintext Git commits/caches
   remain accessible: coordinate historical cleanup before claiming raw values are
   no longer publicly retrievable. No main-history rewrite has been performed.
2. **Stop the Windows task** after the parallel week: compare cloud and local results around
   2 Oct (a week of complete cloud data), and deploy/verify the recovery fixes below
   before stopping it. Keep `data/weather.db`.

### Pipeline
3. First reliability run and page health verified (36497119777). No new day was ready;
   check coverage metadata and new-day finalization when a future day is prepared.
4. GitHub starts the 6-hourly schedule 3–5 h late (e.g. the 00:17 UTC slot ran at 05:18 on
   27 Sep). The latest gap reached 9 h 21 min (28 Sep). If a gap exceeds 9 h the page's
   health line warns; consider an external trigger then.

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
