# Work status

## Cloud collection every 3 hours — 2026-10-01 (Claude, Sonnet)

Done:
- `collect.yml` cron `17 */6 * * *` → `17 */3 * * *` (00:17, 03:17 … 21:17 UTC). Page copy and README say "every 3 hours".
- `cloud/health.py`: `RUN_EVERY_H = 3`, so a full 48 h window expects 16 runs. Expected runs are counted per
  period (`expected_runs`, `RUN_EVERY_CHANGED_AT` = 1 Oct 18:00 UTC) so the 48 h after the change don't show a
  false "Check:" for the 6-hourly runs already in the log. Remove `PREVIOUS_RUN_EVERY_H` and
  `RUN_EVERY_CHANGED_AT` after 3 Oct.
- `site/app.js` `STALE_H` 9 → 6 h (interval + the same 3 h allowance for GitHub delays).
- `cloud/store.py` keeps 120 run records (was 60): the same 15 days at 8 runs/day.
- Checked and left unchanged, nothing assumes 6-hourly runs: horizon windows (±3 h, closest lead per target, so
  denser runs only get closer to nominal), scoring/finalization (UTC-day based), pending/obs pruning (day based),
  WeatherNext init choice (lead is measured from each fetch), ECMWF/Open-Meteo calls (~400/day vs 10,000 limit).
- Tests: 182 pass (one new health test for the cadence change; existing health tests moved to 3 h spacing).
- The Codex handoff docs left uncommitted were committed unchanged first (0db42e8).

Remaining:
- Not touched, on purpose: the local Windows task, `install_background_task.ps1`, `collection_health.py` and the
  Streamlit health caption ("Expected every 6 h · OK ≤8 h"). The task is to be stopped after the parallel week.
- Watch the first days: GitHub may still start slots late, and a gap over 6 h makes the page warn. Pending state
  now grows about twice as fast (more runs per day); check its size after a few days.
