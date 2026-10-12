# Next steps

_Open items only. Remove an item when it is done and record it in `CHANGELOG.md`.
Updated 2026-10-12._

## Open items

### Pipeline
1. **Station recovery.** Wisting is retired locally, with history preserved; publication pending. Revsbotn resumed 10-minute measurements on 12 Oct at 11:40/11:50 UTC: keep it active and verify recovery in subsequent exact-hour collection. Enningdalen and Alvheim have recovered. Finalized-history warnings lag raw observation recovery.
2. **Measure the activated timer.** Job 8590224 is enabled with :07/:37 UTC POST
   requests and failure/recovery/disable notifications. External test returned 204;
   run 37495000121 succeeded and correctly skipped at 65 min. Verify recurring HTTP
   204 responses, a timer-triggered collection once >=150 min old, and an advancing
   public health timestamp. Then evaluate several days of coverage. GitHub hourly
   fallback remains; prior gaps reached 9 h 21 min. Renew the repository-only token
   before 5 Nov 2026 (expires 17:15 UTC); enter it directly in the timer, never chat/files.
3. **Old plaintext history:** coordinate cleanup of earlier public Git commits/caches if
   publication protection requires it; no main-history rewrite has been performed.

### Features
- **ECMWF IFS and AIFS on the page**: collected and scored from 27 Sep (not shown yet). Once
  a week or two of scored days exist, add them to the horizon chart/table. AIFS hourly rain is
  a 6-hour amount spread over the hours: compare it on 6 h totals, not hourly.
4. **Replays with incomplete WeatherNext (idea, needs the user):** 15 Sep (56.3 mm at Bergen, corrected UTC day) is
   left out because WeatherNext has 4 of 24 hours; Yr has full totals. Show Yr-only points, or explain.
6. **Revisit the results** at about 30 paired days, and again once winter arrives. Watch whether
   the height adjustment over-warms cold valley stations (Røros, Dividalen, Grønliheia).

### Housekeeping
7. `scoring/scorer.py` still holds the old hour-floored join (`strftime` on `observed_at`),
   off the dashboard path. Mark it deprecated or remove it.
8. `work/` holds ~20 MB of local evidence. Keep `work/temperature-backfill/first-run.json` and
   `second-run.json` (original availability metadata); the rest can be archived.
9. Address dependency deprecation warnings before library/Python upgrades (NumPy timedeltas,
    pandas concatenation and boolean inversion in replay filtering).
10. Correct stale publication wording in SETUP_CLOUD.md: it still says the workflow forces
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
- Keep `WX_STATE_KEY` and other credentials backed up outside GitHub; without the key `history/` is unreadable.
- Setting GitHub secrets from PowerShell 5.1 by piping adds a BOM; use `gh secret set --body`.
