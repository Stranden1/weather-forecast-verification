# Work status

## Winter readiness built — 2026-10-23 (Claude)

Owner chose the suggested default for all five plan decisions (DECISIONS.md, 23 Oct).

**Done** (local commits, not pushed)
- 07093ab: precipitation Patterns table gets wet rain / mixed / snow rows, phased by the observed
  2 m temperature (snow ≤ 0 °C, rain ≥ 2 °C); the rain card notes snow undercatch in wind.
- 8246f76: the freezing card scores the height-adjusted WeatherNext line (all and land groups;
  offshore has no adjustment, so no column there).
- Tests: 174 cloud tests pass (3 new). Browser check on regenerated demo data
  (`?demo`): the three phase rows sum to the wet-hours total; the third freezing column shows on
  all/land and not offshore; no sideways scroll at 375 px.
- Calm-night study, autumn baseline: FINDINGS_WINTER_INVERSION_2026-10-23.md. At the 12
  stations whose cell is ≥100 m above them, the adjustment helps overall (−0.46 °C) but on calm
  nights the gain shrinks to −0.16 and the bias turns +0.93 °C warm; it is worse on calm nights
  at Grønliheia, Røros and Karasjok. Script `work/winter-inversion/analyze.py` is local only
  (`work/` is ignored).

**Remaining:** push when the owner says so (the page changes and the first `tests.yml` run on the
new runner follow the push). Monthly study reruns Nov–Mar; owner decision after January.
