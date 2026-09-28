# Work status

## Monthly summary + rain median headline — 2026-09-28 (Claude, Sonnet)

Done (committed locally, not pushed):
- `cloud/monthly.py` + `summarize.build` write `site/data/summary.json`: this month so far plus
  every completed month (UTC, by target day), verdicts for temperature/wind at 6 h, 1, 2, 3, 5 days
  and rain at 6 h, 1, 2 days, using the existing `paired`/`stats` (same pairing, bootstrap, 7-day
  minimum). Text is fixed templates; verdicts and text only, no forecast values.
- Page: "Month by month" block under the health line (current month, collapsed "Earlier months").
- Rain views (tiles, horizon chart, table, "Catching rain") lead with WeatherNext's median (solid),
  average dashed; one sentence explains why. Rain verdict/CI now also computed for the median
  (`verdict_50`, `diff_50`, `ci_50_*`); the tile shows the average-based verdict as a second line.
- 23 new tests (`cloud/tests/test_monthly.py`); 177 root+cloud tests and 8 HQ tests pass.
  Checked with `?demo` (desktop dark, 375 px) and a real-data build (September text below).

Remaining:
- User to read the September text, then say whether to push.
- Rain "Who wins where" map, "Over time" chart and "Patterns" table still use WeatherNext's average
  (not in the requested list); change them if the headline should match everywhere.
- Verify the deployed page after the first run that includes summary.json.
