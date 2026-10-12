# Work status

## Private forecast comparison — 2026-10-12 (Codex)

**Complete and validated locally on `codex/scorecard-corrections`; not pushed/deployed.**

### Done
- Owner chose a private forecast UI. `private_forecast/` reads fetched encrypted cloud state in memory and serves only on loopback; no retired database or collector required.
- Active stations, 24/48-hour windows, temperature/wind/precipitation, same-fetch comparisons, ranges, honest gaps, issue ages, median rain, largest-gap shortcut, tables and both themes.
- Private data/access controls: no credential delivery, caching, external assets, state/history writes or public export. No capture expansion or scheduling change.
- Eight private tests pass; the existing 143 cloud tests also pass. Browser checks pass at 1280/375/320 px in light/dark, including missing-hour line/range breaks, missing providers, rain median, empty stations, keyboard selection and prominent mobile values. No captured JS errors or page-wide overflow.
- Private screenshots, validation.json and aggregate disagreement.json are in ignored `work/forecast-comparison-2026-10-12/`; never publish future-value screenshots. The validation server is stopped.
- PRIVATE_FORECAST.md gives launch instructions; FORECAST_PLAN.md gives evidence, ranked next work and the proposed finish line. Earlier scorecard checkpoint is archived atop CHANGELOG.md.

### When returning
Review the private viewer; see Git log for its local checkpoint. Earlier scorecard commits are now on `origin/main` at `39c2617`, with CI passed. At 15:10 UTC the live page was still the previous version: run 38267891738 gated/skipped collection and deployment. Verify the next actual deployment. This new viewer has not been pushed or deployed; this task performed neither action.

The private timeline intentionally has gaps: current cloud capture saves scoring windows. Approve prospective bounded 48-hour capture before collector changes, then choose fixed daily/night scope. Daily extrema/totals cannot be recovered from lost full local runs or inferred from incomplete timelines.

Rain-probability reliability and IFS/AIFS views remain proposals using retained data. Then collect through winter and review occasionally; more station/variable counts are lower priority. Operations still need the 19 Oct runner check, before-5-Nov token renewal and independent history/key recovery confirmation (NEXT_STEPS.md).

**Data:** cloud history is the only retained record; keep it and WX_STATE_KEY safe. No history edits, push, workflow dispatch, secret rotation or collector changes in this task.
