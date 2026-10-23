# Work status

## Fewer false failure emails from collect — 2026-10-23 (Claude)

Owner asked why GitHub still emails "All jobs have failed". All 9 failed collect runs since
29 Sep were one-off network errors (8 Open-Meteo timeouts or cut-off replies, 1 Frost outage);
data was saved and the site deployed each time, and the next run passed. The red came from the
final `cloud.run check` step, which failed on any source error in the latest run.

**Done** (branch `claude/collect-retries`, pushed and fast-forwarded into main on 23 Oct)
- `cloud/openmeteo.py` `_get`: also retries (3 tries, 10 s / 20 s back-off) on timeouts,
  dropped connections and truncated or empty JSON. 4xx errors still fail at once.
- `cloud/health.py` `persistent_errors`, used by `cloud.run check`: the step fails only when the
  same source (Yr archive included) has errors in 2 runs in a row (`FAIL_AFTER_RUNS`). It now
  prints which sources erred, so the log says why.
- Tests: 178 cloud tests pass (4 new methods; two existing check tests updated).

- PROJECT_STATUS.md and NEXT_STEPS.md refreshed: winter readiness is live and the first
  `tests.yml` run on the Ubuntu runner passed (23 Oct, 463ef25).

**Remaining:** none. The next failure email should only come from a source failing twice in a row.
