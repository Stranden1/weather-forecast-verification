# Work status

## Four-product rerun at 29 paired days — 2026-10-26 (Claude)

Owner asked to run the rerun planned for ~27 Oct now. Main fast-forwarded to origin/main for
current history (through 25 Oct).

**Done**
- `work/four-product-2026-10-26/analyze.py`: unchanged copy of the 15 Oct script (same cohort
  rules, day-block intervals, seed); the 15 Oct results are kept. Run is read-only.
- FINDINGS_FOUR_PRODUCT_2026-10-26.md: 29 days at 6–12 h (27 Sep – 25 Oct). Every 15 Oct
  conclusion holds with tighter intervals: Yr vs WeatherNext too close to call, IFS clearly worst,
  AIFS beats IFS but trails Yr, Yr+WeatherNext average beats all four, adding ECMWF worsens it.
  Offshore, IFS wind is now also clearly better than Yr.

- Owner chose option 1 (DECISIONS.md, 26 Oct): `site/index.html` gets a static "What about
  ECMWF?" note in "How to read this fairly" (29 days, IFS/AIFS behind Yr and WeatherNext at
  6–48 h, AIFS beat IFS, run-age caveat, not part of the average). ECMWF/Open-Meteo attribution
  was already on the page. Checked in the local preview; 178 cloud tests pass.

**Remaining:** none. Revisit the note if a winter rerun changes the ranking.
