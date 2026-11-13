# Work status

## Review part A: robustness — 2026-11-13 (Claude)

Owner answered the five decisions in `docs/reviews/REVIEW_2026-11_fable.md` (all yes, cadence
2.5 h; recorded in DECISIONS.md, 13 Nov) and asked for part A only. Six local commits, **not pushed**.

**Done** (each step tested; 185 cloud tests pass, was 178)
- Finding 1 + 5, gate (`cloud/health.py`): a run where Yr or WeatherNext delivered no rows is
  not complete, so the next 30-min tick collects again (Frost alone is not enough). After a
  complete run the gate waits 145 min (was 150, which lost to the timer by ~1 s), so the
  cadence is a steady 2.5 h. Workflow text, SETUP_CLOUD.md and PLAN_WEBPAGE.md updated.
- Finding 3: CI installs `cloud/requirements-lock.txt` (34 exact versions the tests pass with,
  checked to resolve unchanged on Linux / Python 3.12). `test_dependencies.py` fails on drift.
- Finding 4: notable days keep the fixed bars but list only the 3 most extreme days per type
  per calendar month (measurements only). Page text says so.
- Finding 7: the seven unread exports are gone (nothing else read them); tests use `views.json`.
- Finding 8: a failed data download now says "Could not load the data…" instead of "No data
  published yet" (checked in the browser for network, parse and 404 cases); stale steadiness
  comment fixed.

**Left as is (finding 8):** retired Wisting in `meta.json` / station-count mismatch,
`allow_nan=False` (a NaN would then stop the export before state is published, so it needs its
own design), `WX_STATE_KEY` scoped per step, `T24:00:00Z` (valid per the JS spec; Safari untested),
self-hosted fonts. Not done by request: finding 6 (history read twice) and the in-run Yr retry.

**Remaining:** owner approves the push. Then check the first runs: gate log says "last complete
run … min ago", collection every 150 min, `tests.yml` green on the lock file. Parts B, C, D wait
for their own sessions.
