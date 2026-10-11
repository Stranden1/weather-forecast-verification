# Work status

_The latest task's checkpoint only. Archive it in CHANGELOG.md when replacing it._

## "Which way do they miss?" card — 2026-10-11 (Claude)

**Done, committed, not pushed.** Step 2 of the dashboard plan (AgnosticBrain
`plans/weatherapp-dashboard.md`). Step 1 (a6e6e31) is not pushed either.

- Export (`cloud/summarize.py`): new `bias_by_hour()` beside `conditions()` writes `bias.json`:
  per variable and horizon, 4 blocks of 6 h in Oslo local time (summer/winter time handled) with
  n, days, bias_yr, bias_wn, bias_wn50 and, for temperature, bias_wnh. All days; no period split.
- Page: new card "Which way do they miss?" after the steadiness card, with its own horizon picker.
  Horizontal bars from a zero line (right = too warm/strong/wet). Temperature adds an outlined
  height-adjusted WeatherNext bar; rain uses WeatherNext's median, as the tiles do. A lead line
  gives the all-hours bias from leaderboard.json; table view; note for blocks under 7 days.
- `renderBias()` returns early if its section is missing, so a cached old index.html with the
  new app.js still renders (seen once in testing, before the guard).
- Live history, temperature 1 day: Yr +0.18 °C (+0.23 at night, +0.10 by day), WeatherNext
  -0.29 °C, height-adjusted about 0. At 7 days Yr leans +0.55 °C.
- 125 cloud tests pass (3 new: Oslo blocks incl. winter time; build writes bias.json). Checked in
  the browser with data rebuilt from history: desktop and 375 px, dark and light, all three
  variables, horizon picker; no horizontal scroll, no errors after the guard.

Next: plan step 3, "Biggest differences" in the map panel (page only).
