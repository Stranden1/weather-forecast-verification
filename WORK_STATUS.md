# Work status

_The latest task's checkpoint only. Archive it in CHANGELOG.md when replacing it._

## Averaged forecast tile — 2026-10-11 (Claude)

**Done, committed, not pushed.** Step 1 of the dashboard plan (AgnosticBrain
`plans/weatherapp-dashboard.md`; HTML version in local `work/plans/better-dashboard.packed.html`).
All five plan decisions were kept as suggested.

- Export (`cloud/summarize.py`): `paired()` adds `e_avg` = midpoint of Yr and WeatherNext minus the
  observation, temperature and wind only (not rain). `stats()` adds `mae_avg`, `bias_avg` and
  `avg_gain` (1 - avg MAE / the better single MAE) to every stats block, so leaderboard.json and
  patterns.json gain them. Verdicts, ranges and scoring are unchanged.
- Page: a fourth tile "Both, averaged" (with "N% better than the better of the two" and a note that
  it is our blend, not a service) and a "Both, averaged" column in the horizon table. Tiles go
  4 across, 2x2 below 1000 px, 1 column below 760 px. Rain keeps three tiles.
- Live history (24 days at 1 day): temperature 0.80 vs Yr 0.90 / WeatherNext 0.91 °C (11% better);
  wind 1.33 vs 1.46 / 1.43 m/s (7%).
- 122 cloud tests pass (3 new in `test_improvements.py`). Checked in the browser against data
  rebuilt from history into ignored `site/data/`: desktop, 900 px and 375 px, all three variables,
  no console errors, no horizontal scroll.

Next: plan step 2, the "Which way do they miss?" bias card (`bias.json`).
