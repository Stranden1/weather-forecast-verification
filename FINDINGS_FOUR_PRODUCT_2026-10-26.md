# Four-product rerun at 29 paired days — 2026-10-26 (Claude)

Rerun of FINDINGS_FOUR_PRODUCT_2026-10-15.md, as DECISIONS.md (16 Oct) asked, so the owner can
decide again about an ECMWF section on the page. Read-only: encrypted `history/` from origin/main
(through 25 Oct) was read in memory; no history, state, scoring, collection or page files changed.
Script: `work/four-product-2026-10-26/analyze.py`, an unchanged copy of the 15 Oct script (same
cohort rules, 6/12/24/48 h, day-block 95% intervals, 2,000 draws, same seed). Output:
`results.json` beside it (local, ignored). The 15 Oct results are untouched.

## Cohort

- 27 Sep 09 UTC – 25 Oct 23 UTC: **29 days** at 6–12 h (28 at 24 h, 27 at 48 h). The 26 Oct day
  file arrives tomorrow; one more day will not change any conclusion below.
- 6–48 h: temperature 112,076 rows / 50 stations (was 61,731 / 17 days); wind 98,652 / 44.
- Still includes retired Wisting (SN20925); current 49-station network only changes every MAE
  by ≤0.002. Still one autumn period with no winter weather: descriptive, not a verdict.

## Main results, 6–48 h (MAE; bias = forecast − observed)

| | Yr | WN | IFS | AIFS | Yr+WN average | Average of four |
|---|---|---|---|---|---|---|
| Temperature °C | 0.97 (+0.13) | **0.96** (−0.31) | 1.23 (−0.43) | 1.02 (−0.06) | 0.86 | 0.91 |
| Wind m/s | **1.65** (+0.39) | 1.68 (−0.09) | 1.85 (−0.41) | 1.80 (−0.55) | 1.51 | 1.57 |

Difference from Yr (MAE, 95% interval), with the 15 Oct value in brackets:

| | Temperature °C | Wind m/s |
|---|---|---|
| WN | −0.01 [−0.04, +0.03] unclear (+0.02) | +0.03 [0.00, +0.07] unclear (+0.03) |
| IFS | **+0.26** [+0.22, +0.31] (+0.24) | **+0.21** [+0.17, +0.26] (+0.22) |
| AIFS | **+0.05** [+0.02, +0.07] (+0.06) | **+0.15** [+0.09, +0.22] (+0.16) |
| Yr+WN average | **−0.11** [−0.13, −0.09] (−0.10) | **−0.14** [−0.16, −0.11] (−0.12) |
| Average of four | −0.06 [−0.08, −0.04] (−0.06) | −0.08 [−0.11, −0.05] (−0.07) |

**Every 15 Oct conclusion holds, with narrower intervals:**

- **Yr vs WN: still too close to call** overall for both variables. By horizon: Yr is clearly
  lower at 6 h (both variables) and 12 h (wind); WN is clearly lower at 48 h (both variables).
- **IFS is clearly worst** at every short horizon, for both variables.
- **AIFS beats IFS** at every short horizon. AIFS trails Yr, except at 48 h temperature (unclear).
- **Both ECMWF products under-forecast wind** (−0.4/−0.6 m/s; −0.7/−0.8 m/s on land).
- **Yr+WN average beats every single product** at every short horizon. Adding IFS and AIFS still
  makes it worse: on land the average of four is level with Yr for wind.
- Height-adjusted WN temperature (not the headline): 0.84 °C, lowest of all. The 23 Oct calm-night
  baseline found it turns warm-biased at inland valley stations; that is a separate study.

## Land and offshore (6–48 h)

| MAE | Yr | WN | IFS | AIFS |
|---|---|---|---|---|
| Temperature land (36 st.) | **1.03** | 1.09 | 1.42 | 1.14 |
| Temperature offshore (14) | 0.77 | **0.58** | 0.67 | 0.65 |
| Wind land (31) | **1.63** | 1.78 | 1.96 | 1.91 |
| Wind offshore (13) | 1.69 | **1.39** | 1.56 | 1.50 |

- On land Yr is clearly lowest of the four, for both variables.
- Offshore Yr is clearly **highest** of the four for both variables. New since 15 Oct: IFS wind is
  now also clearly lower than Yr offshore (was unclear), so all three model products beat Yr there.
  Yr's offshore bias is still high: +0.27 °C and +0.93 m/s.
- Per-station lowest MAE (≥200 rows): temperature land WN 18, Yr 11, AIFS 6, IFS 1; offshore
  WN 10, AIFS 4. Wind land Yr 14, WN 11, IFS 5, AIFS 1; offshore WN 10, AIFS 3.

## Caveats (unchanged)

- **Run age** at fetch time (median): Yr 0.6 h, WN 7.6 h, AIFS 9.1 h, IFS 10.1 h. This favours Yr
  at short horizons and is the main reason the ECMWF gap should not be read as model skill alone.
- Height handling and interpolation differ (see the 15 Oct file). Four **products**, not a clean
  AI-versus-physics experiment.
- 72–240 h still has ~8× fewer rows (17 days at 240 h): anecdotal, not used above.

## For the owner's decision (no page change made)

The 16 Oct condition, "decide again only if the ranking holds", is met: the ranking is the same
and the intervals are tighter. Options:

1. **Add a short ECMWF note** (recommended if you want it now): "Over 29 autumn days, ECMWF IFS and
   AIFS were behind Yr and WeatherNext at 6–48 h; AIFS beat IFS." With the run-age caveat, and no
   ECMWF numbers in the blend.
2. **Keep it on hold until winter** data confirm the ranking under snow and cold-valley conditions.

Unchanged either way: the published blend stays Yr + WeatherNext only (DECISIONS.md, 16 Oct).
The offshore result now has 29 days behind it, but the 16 Oct decision also asks for winter data
before any "Yr is weakest offshore" wording.
