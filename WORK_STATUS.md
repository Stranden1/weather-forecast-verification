# Work status

_The latest task's checkpoint only. Archive it in CHANGELOG.md when replacing it._

## Horizon chart redesign — 2026-10-09 (Claude)

**Done.** The user found "Error by how far ahead" hard to read: the naive line (2-3 °C, 5.3 at
10 days) set the y-axis, the four model lines were squeezed at the bottom, the 10-day point came
from 1 day (47 forecasts), and WeatherNext's average and median overlapped. Site only
(`site/app.js`, `index.html`, `style.css`); no scoring, export, data or workflow changes.

- The card is now "Who is closer, by how far ahead" with a Difference / Error size switch.
  Difference (default): WeatherNext error - Yr error per horizon, with the existing 95% day-block
  range as a bar and a zero line. Points and bars are coloured by the existing verdict
  (blue = Yr, orange = WeatherNext, grey = too close). Temperature adds the height-adjusted
  series (hollow triangles); rain shows the median (headline) and the average (hollow squares).
- Both views hide horizons with fewer than `min_days_for_verdict` (7) days and say which.
  The table keeps every horizon. Error size: Yr, WeatherNext, plus the height-adjusted (temperature)
  or average (rain) line; no naive line, no median line for temperature/wind.
- The naive baseline is now called "same as yesterday" in the tiles, table and "How to read" text.
- Checked locally against the live JSON (copied into ignored `site/data/`) in dark/light, desktop
  and 375 px mobile: no page errors, no horizontal scroll. 119 cloud tests pass (none cover the JS).
- Added `.claude/launch.json` (`site`: local static server on port 8765) for previews.

Pushed 2026-10-11 (21f7b2c). Next: the steadiness card (NEXT_STEPS 5). The 9 Oct
analysis of model differences (in the conversation, not stored) suggested further cards:
see NEXT_STEPS "Show the differences".
