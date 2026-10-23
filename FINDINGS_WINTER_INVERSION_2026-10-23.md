# Calm-night check of the height adjustment — 2026-10-23 (Claude)

Autumn baseline for step 4 of `PLAN_WINTER_READINESS.html`. Read-only: encrypted history
(origin/main, 48 day files through 22 Oct) was read in memory from a scratch copy; no history,
state, scoring or page files changed. Script and aggregate output (no forecast values):
`work/winter-inversion/analyze.py`, `results.json` (local; `work/` is ignored by Git).

## Method

- Rows: land stations with a known model-cell height, 6/12/24/48 h, observation, Yr and
  WeatherNext all present. Period 15 Sep – 22 Oct 2026 (38 days; WeatherNext starts 15 Sep).
- `dz` = WeatherNext cell height − station height for the row's sampling method. Main group:
  cell 100 m or more above the station (12 stations), where the adjustment warms WeatherNext.
- Night = target 17–05 UTC. Calm night = night with observed 10 m wind below 2 m/s. Nights
  without a wind observation are "unknown". No cloud data, so "calm" is not "clear".
- 95% intervals for MAE(adjusted) − MAE(WeatherNext) from resampling whole days (2,000 draws).
  Rows repeat targets across horizons; days, not rows, are the independent unit.

## Results (MAE °C; bias = forecast − observed)

Cell 100 m or more above the station (12 stations):

| | Hours | Yr | WN | WN adjusted | Adjusted − WN [95%] | Bias WN / adjusted |
|---|---|---|---|---|---|---|
| Calm nights | 6,518 | 1.60 | 1.63 | 1.48 | −0.16 [−0.24, −0.06] | −0.25 / **+0.93** |
| Other nights | 7,750 | 1.11 | 1.97 | 1.08 | −0.89 [−0.95, −0.82] | −1.90 / −0.64 |
| Day | 15,032 | 1.28 | 1.47 | 1.04 | −0.43 [−0.49, −0.36] | −1.05 / +0.15 |
| All | 32,808 | 1.37 | 1.65 | 1.19 | −0.46 [−0.52, −0.40] | −1.05 / +0.15 |

- **The adjustment still helps overall, but on calm nights its gain almost disappears** (−0.16
  against −0.89 °C on other nights), and its bias turns **warm by +0.93 °C**. That is the
  expected sign of cold air pooling below the model cell: the standard lapse rate assumes the
  air gets colder with height, which is not true in a ground inversion.
- Per station, calm nights only (descriptive, ≥30 hours): the adjustment is **worse** at
  E134 Grønliheia (+0.48 °C, dz 137 m), Røros (+0.35, 106 m) and Karasjok (+0.12, 160 m), the
  inland cold-air-pool sites. Raw WeatherNext is already too warm there on calm nights
  (+0.6 to +1.7 °C) and the adjustment adds more. It is about neutral at Geilo and Revsbotn and
  clearly better at Bergen, Vangsnes, Langfjordbotn, Sunndalsøra and Losistua (−0.3 to −1.2 °C).
- One station has its cell 100 m or more **below** it (Flermoberget, 922 hours over 14 days):
  the adjustment cools it and is worse at night (+0.4 to +0.6 °C). Few days; anecdotal.
- Stations with small dz (27): adjusted and raw are nearly equal, as expected.

## Caveats

- Autumn, not winter: 38 days, few long cold calm spells. The real test is December–February.
- Wind-only "calm" mixes clear and cloudy calm nights; cloudy calm nights do not form strong
  inversions, so the true clear-night effect is probably larger than shown.
- Night in UTC fits winter time; until 25 Oct (summer time) it is 19–07 Oslo time.
- Same data as earlier height-adjustment results; nothing here was tuned. Do not fit a lapse
  rate or a calm-night rule on this period and then judge it on the same period.

## For the owner (no change made)

1. Keep the height-adjusted line as it is for now; it is still clearly better on average.
2. Rerun about the 1st of Nov, Dec, Jan, Feb and Mar. If the January run still shows the warm
   calm-night bias at inland valley stations, decide then between: a caveat on the page for
   those stations, no adjustment on calm nights, or no adjustment at named cold-air-pool sites.
   Any rule must be fixed before it is judged on later data.
