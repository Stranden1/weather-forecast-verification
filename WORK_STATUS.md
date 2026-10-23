# Work status

## Fewer false failure emails from collect — 2026-10-23 (Claude)

Owner asked why GitHub still emails "All jobs have failed". All 9 failed collect runs since
29 Sep were one-off network errors (8 Open-Meteo timeouts or cut-off replies, 1 Frost outage);
data was saved and the site deployed each time, and the next run passed. The red came from the
final `cloud.run check` step, which failed on any source error in the latest run.

**Done** (branch `claude/collect-retries`, from origin/main 463ef25; not pushed)
- `cloud/openmeteo.py` `_get`: also retries (3 tries, 10 s / 20 s back-off) on timeouts,
  dropped connections and truncated or empty JSON. 4xx errors still fail at once.
- `cloud/health.py` `persistent_errors`, used by `cloud.run check`: the step fails only when the
  same source (Yr archive included) has errors in 2 runs in a row (`FAIL_AFTER_RUNS`). It now
  prints which sources erred, so the log says why.
- Tests: 178 cloud tests pass (4 new methods; two existing check tests updated).

**Remaining:** push when the owner says so (the Codex branch `codex/scorecard-corrections`
points at the same commit as origin/main; local `main` is stale at 39c2617).
