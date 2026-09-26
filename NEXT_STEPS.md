# Next steps

_Open items only. Remove an item when it is done and record it in `CHANGELOG.md`.
Updated 2026-09-26._

## Open items — 2026-09-26

### Needs the user
1. **WeatherNext data terms (read 26 Sep).** Forecasts for times ≥ 1 hour ago are CC BY 4.0;
   anything newer or future falls under the real-time terms, which only allow controlled
   sharing. **Urgent:** the public `state` branch holds future WeatherNext forecasts
   (`pending.csv.gz`), which those terms don't allow to be published. Fix proposed: encrypt the
   state files. After that, `WX_PUBLISH_FORECAST_VALUES=1` looks allowed for past forecasts with
   the exact CC BY citation.
2. **Decide what to do with `FINDINGS_2026-09-26.md`**, the untracked first-results note:
   commit it or delete it.
3. **Stop the Windows task** after the parallel week: compare cloud and local results around
   2 Oct (a week of complete cloud data), then stop it. Keep `data/weather.db`.

### After the push (pushed 26 Sep 14:59 UTC)
4. Check the first cloud run's rows are marked `wn_sampling = bilinear` and the page shows the
   height-adjusted line and station notes.
5. Check the local 16:10 UTC run on 26 Sep: `weather.db` WeatherNext values for that run should
   look sane, and `migrate_sqlite` should mark them `bilinear`.
6. Turn on `--strict` in `.github/workflows/collect.yml` now that all sources work, so a
   failing source makes the run red.

### Features
7. **Storm replays and steadiness on the page:** `PLAN_REPLAYS.md` steps 2–5 (step 1 done).
8. **WeatherNext median as the headline rain value**, with the average as the dashed line
   (FINDINGS recommendation 2).
9. **Revisit the results** at about 30 paired days, and again once winter arrives. Watch whether
   the height adjustment over-warms cold valley stations (Røros, Dividalen, Grønliheia).

### Housekeeping
10. `scoring/scorer.py` still holds the old hour-floored join (`strftime` on `observed_at`),
    off the dashboard path. Mark it deprecated or remove it.
11. `work/` holds ~20 MB of local evidence. Keep `work/temperature-backfill/first-run.json` and
    `second-run.json` (original availability metadata); the rest can be archived.

## Standing reminders
- Restart the local Streamlit dashboard before any manual WeatherNext fetch from Admin; a
  running process keeps old code in memory.
- If Yr collection becomes Delayed or Stale, check promptly: missed Yr history cannot be recovered.
- Revalidate wind height/unit metadata when changing the station network or collectors.
- Keep separate backups of `data/weather.db` and credentials; GitHub holds neither.
- Setting GitHub secrets from PowerShell 5.1 by piping adds a BOM; use `gh secret set --body`.
