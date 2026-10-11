# Work status

_The latest task's checkpoint only. Archive it in CHANGELOG.md when replacing it._

## Steadiness card — 2026-10-11 (Claude)

**Done and pushed 2026-10-11 (85bf9d6).** New card "How steady are the forecasts?" under the horizon card,
showing the existing `steadiness.json` (PLAN_REPLAYS step 3). Site only (`site/app.js`,
`index.html`, `style.css`); no scoring, export, data or workflow changes.

- Horizontal bars per horizon step (7 d -> 5 d ... 12 h -> 6 h): average size of each service's
  change for the same station/hour, with the existing day-block verdict ("Yr steadier",
  "WeatherNext steadier", "Too close to call") under each step label and in the tooltip.
- Flip-flops per 100 forecasts above the chart (temperature now Yr 3.1 vs WeatherNext 0.6).
- Note: steps with fewer than `min_days_for_verdict` days are hidden (10 d -> 7 d has 3 days);
  the "moved closer to the measurement" share range per service (about 50-70%, a coin toss is
  50%); caveats (ensemble average moves less; Yr corrected with station data near the event;
  steady is not accurate). All days so far: the period switch does not apply (the JSON has no
  period split). Rain uses WeatherNext's average, as `cloud/replay.py` does; labelled so.
- Table view keeps every step, with "moved closer" percentages, forecasts and days.
- The JS repeats `MIN_REVISION` from `cloud/replay.py` (0.2 °C / 0.5 m/s / 0.1 mm) for the
  caption; change both together.
- Checked against the live JSON (refreshed into ignored `site/data/`) at desktop and 375 px,
  dark and light, all three variables: no page errors, no horizontal scroll. 119 cloud tests pass
  (none cover the JS).

Next: PLAN_REPLAYS step 4 (15 Sep hand check) and the
"Show the differences" ideas in NEXT_STEPS.
