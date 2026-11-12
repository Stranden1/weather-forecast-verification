# Four-product temperature/wind comparison — 2026-10-15 (Claude)

Task 3 from REVIEW_2026-10-14.md. Read-only: encrypted `history/` was read in memory; no
history, state, scoring, collection or page files changed. Script and full aggregate output
(no forecast values): `work/four-product-2026-10-15/analyze.py`, `results.json` (local, ignored).

## Cohort

- Rows where the observation **and** Yr, WeatherNext (WN), ECMWF IFS HRES and AIFS Single are all
  present, on the row the existing pairing already selected (same fetch, same lead for all four).
- 27 Sep 09 UTC – 13 Oct 23 UTC, 17 days. Temperature 67,250 rows / 50 stations; wind 58,236 / 44.
  Rows repeat the same target across horizons; they are not independent samples.
- Main results use 6/12/24/48 h (temperature 61,731 rows, wind 53,483). From 72 h, Yr only gives
  6-hourly steps, so those horizons have about 8× fewer rows (5 days at 240 h): treat as anecdotal.
- Includes retired Wisting (SN20925). Current 49-station network only: every MAE changes by ≤0.004.
- Uncertainty: 95% intervals from resampling whole days (2,000 draws). 17 days, one autumn period,
  no multi-day weather-system blocks: **exploratory and descriptive, not a verdict**.

## Main results, 6–48 h (MAE; bias = forecast − observed)

| | Yr | WN | IFS | AIFS | Yr+WN average | Average of four |
|---|---|---|---|---|---|---|
| Temperature °C | **0.95** (+0.21) | 0.96 (−0.29) | 1.18 (−0.30) | 1.01 (−0.06) | 0.85 | 0.89 |
| Wind m/s | **1.57** (+0.31) | 1.60 (−0.09) | 1.78 (−0.42) | 1.73 (−0.53) | 1.45 | 1.50 |

Difference from Yr (MAE, 95% interval):

- **Yr vs WN: too close to call** for both variables overall (temperature +0.02 [−0.03, +0.06],
  wind +0.03 [0.00, +0.06]). Yr is lower at 6 h for both; WN wind is lower at 48 h. This matches the page.
- **IFS is clearly worst**: +0.24 °C and +0.22 m/s above Yr, at every short horizon.
- **AIFS beats IFS** at every short horizon, for both variables (temperature 1.01 vs 1.18). AIFS is
  higher than Yr by +0.06 °C and +0.16 m/s; at 48 h its temperature difference is unclear.
- **Both ECMWF products under-forecast wind**: −0.4/−0.5 m/s overall, −0.7/−0.8 m/s on land.
- **Averaging Yr and WN beats every single product** (−0.10 °C, −0.12 m/s vs Yr, clear at every
  horizon). **Adding IFS and AIFS makes the average worse**, not better (four-product average is
  between the Yr+WN average and Yr; on land it is no better than Yr).
- Our height-adjusted WN temperature (not published as the headline) has 0.83 °C, lower than every
  product and both averages. Its lapse rate was not fitted to this period, but this remains
  the same evaluation period: descriptive only.

## Land and offshore (6–48 h)

| MAE | Yr | WN | IFS | AIFS |
|---|---|---|---|---|
| Temperature land (36 st.) | **0.98** | 1.07 | 1.34 | 1.11 |
| Temperature offshore (14) | 0.85 | **0.64** | 0.74 | 0.72 |
| Wind land (31) | **1.54** | 1.69 | 1.88 | 1.83 |
| Wind offshore (13) | 1.65 | **1.34** | 1.52 | 1.46 |

- On land, Yr is clearly lowest of the four for both variables. Offshore, Yr is clearly **highest**
  (worst) for temperature and wind. All three model products are clearly lower there for
  temperature; for wind WN and AIFS are clearly lower and IFS is unclear. WN is lowest offshore.
  Yr's offshore temperature (+0.28 °C) and wind (+0.84 m/s) are biased high.
- Per-station lowest temperature MAE (descriptive, ≥200 rows): land WN 18, Yr 13, AIFS 3, IFS 2;
  offshore WN 10, AIFS 4. Wind: land Yr 14, WN 11, IFS 4, AIFS 2; offshore WN 11, AIFS 2.
  (WN has the lowest MAE at more land stations but a higher land average, probably from larger
  misses at the known height/valley stations; not checked here.)

## Caveats

- **Run age differs.** At fetch time, Yr's issue time is ~0.6 h old (median); WN 7.6 h, AIFS 8.6 h,
  IFS 10.1 h. Same nominal lead, but the ECMWF products and WN start from older data. Yr's issue
  time probably reflects its frequent post-processing update rather than a model start time. This favours Yr, mostly at short horizons.
- **Height handling differs.** Open-Meteo moves IFS/AIFS temperature to the station elevation; WN's
  published value is at its cell height; Yr is post-processed with observations.
- **Interpolation.** AIFS is 6-hourly, interpolated to hours by Open-Meteo. IFS HRES is hourly to 90 h.
- These are four **products**, not a clean AI-versus-physics experiment (PLAN_FORECAST_ARCHIVE §8).
  AIFS beating IFS here is about these point products via Open-Meteo, for this autumn period.

## Suggestions for review (no page change made)

1. Worth showing: "IFS and AIFS are behind Yr and WeatherNext; averaging Yr and WeatherNext beats all
   four" — with the run-age and short-period caveats.
2. Do not add ECMWF to the page's blended figure: it makes the blend worse.
3. Offshore, Yr is the weakest product for temperature and wind; a land/offshore split would make this
   visible. Re-check at 30 paired days and in winter before any wording that sounds like a verdict.
