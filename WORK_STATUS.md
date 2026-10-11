# Work status

_The latest task's checkpoint only. Archive it in CHANGELOG.md when replacing it._

**Data note, 2026-10-11:** `data/weather.db` and its 7z archive were deleted and are lost (no
copy was made). The cloud `history/` is the only record.
See CHANGELOG.md.

## "Biggest differences" in the map panel — 2026-10-11 (Claude)

**Done and pushed 2026-10-11 (8cf486c).** Step 3 of the dashboard plan (AgnosticBrain
`plans/weatherapp-dashboard.md`).

- Page (`site/app.js` `renderDiffs()`): with no station selected, the map panel lists up to 3
  stations per service where its average error is at least 10% smaller (`DIFF_MIN`), biggest gap
  first, for the map's variable and horizon. Only stations with at least `min_days_for_verdict`
  (7) days count. Names open the station details; the details get a "← Biggest differences" link.
  The page now opens on the list instead of Oslo's details.
- Temperature rows on the Yr side also show WeatherNext's height-adjusted error (e.g. Losistua
  1 day: Yr 0.85, WeatherNext 1.89, height-adjusted 0.66 °C, so height explains it).
- Export: `stations.json` gains `days` per station (the plan said "page only", but the page could
  not check the 7-day rule from `n` alone). Test added in `test_sampling`.
- "Clearly" is a 10% gap, not a per-station significance test; rain uses WeatherNext's average,
  like the map colours (NEXT_STEPS item 5 covers the median on those views).
- Live history, 1 day temperature: Yr closer at Losistua, E6 Langfjordbotn, E6 Mjøsbrua;
  WeatherNext at Norne, Johan Castberg, Aasta Hansteen (offshore). Wind: Yr at Valdresflye (65%).
- 128 cloud tests pass. (`MigrateTest.test_runs_marked_by_retrieval_time` used to error on
  Windows: it left a read connection open, so the temp `w.db` was locked at cleanup. Fixed the same
  day by closing it; 5 runs in a row pass.) Checked in the browser with data rebuilt from history: all three
  variables, 1/3/10 day horizons (10 days: "no station has 7 days"), click-through and back,
  375 px light, dark; no horizontal scroll, no console errors.

Next: plan step 4, station freshness warning (`last_obs` in meta.json).
