# Pressure (MSLP) backfill pilot — 2026-10-15 (Claude)

Task 4 from REVIEW_2026-10-14.md; pilot design from PLAN_FORECAST_ARCHIVE.md §6. Read-only:
no history, state, scoring, collection, workflow or page changes. Script, raw responses and full
aggregate output are local only (ignored): `work/pressure-pilot-2026-10-15/` (`pilot.py`, `raw/`,
`results.json`). The raw files contain past WeatherNext values; keep them private.

## What was done

- **Stations:** the eight pilot stations, all below 150 m: Oslo, Jomfruland, Bergen, Trondheim,
  Røst, Tromsø, Karasjok and Vardø.
- **Runs:** 28 fixed runs (00 and 12 UTC, 29 Sep 00 – 12 Oct 12). Leads 6–120 h every 6 h, which
  are AIFS's native steps. All values in a comparison come from **one run** per product. This is
  different from the live pipeline, which mixes runs.
- **WeatherNext:** `mean_sea_level_pressure_mean` from the 0.1° Earth Engine collection,
  bilinear at the station point (as the collector does), Pa ÷ 100.
- **IFS HRES and AIFS Single:** Open-Meteo's Single Runs API (`run=…`), `pressure_msl`, in hPa.
- **Observations:** Frost `air_pressure_at_sea_level` (QFF). Only exact UTC hours, offset PT0H and
  series 0 were kept. Identical reports from PT1H/PT10M/PT1M series were merged into one value.
  3 station-hours where reports disagreed were excluded, never averaged. No QFE, QNH or height
  correction was used.

## Can it be backfilled? Yes, completely

- **WeatherNext:** 28/28 runs, 160/160 values each. Earth Engine's `ingestion_time_utc` puts
  delivery at 7.0–8.6 h after the run start, with two late runs (10.5 h and 13.7 h). One request for
  all 20 hours at once stalled for over 10 minutes; batches of 5 hours ran quickly.
- **IFS/AIFS:** 28/28 runs, every requested value present, one request per run.
  Open-Meteo's grid point is 3–10 km from the stations, which matters little for sea-level pressure.
- **Frost:** 3,061 of 3,072 station-hours (16 days); only Røst has gaps (380/384).
- **Common cohort:** 4,191 rows (all three products plus an observation). Each target appears in up
  to 20 runs, so rows are not independent. 95% intervals come from resampling whole target days.
- **Not recoverable by backfill:** when each value first became available to us. The ingestion
  time above is Earth Engine's own record; Open-Meteo gives none. Yr pressure exists only from the
  archive (since 15 Oct).

## Results (hPa; bias = forecast − observed)

| Lead | n | WeatherNext MAE | IFS MAE | AIFS MAE | 6 h tendency MAE (WN / IFS / AIFS) |
|---|---:|---:|---:|---:|---|
| 6–24 h | 895 | **0.35** | 0.40 | 0.43 | 0.28 / 0.33 / 0.32 |
| 30–48 h | 896 | **0.46** | 0.58 | 0.60 | 0.35 / 0.42 / 0.43 |
| 54–72 h | 864 | **0.75** | 1.13 | 1.07 | 0.54 / 0.71 / 0.70 |
| 78–120 h | 1,536 | **1.77** | 2.46 | 2.38 | 0.94 / 1.27 / 1.06 |
| All | 4,191 | **0.97** | 1.34 | 1.31 | 0.61 / 0.80 / 0.71 |

- **WeatherNext is lowest at every lead bin and at all eight stations.** Against IFS: −0.05
  [−0.07, −0.03] at 6–24 h, growing to −0.70 [−1.11, −0.30] at 78–120 h.
- **IFS and AIFS are about equal.** AIFS is slightly worse at 6–24 h (+0.04 [+0.01, +0.07]);
  every later bin is unclear.
- **Biases are small:** WeatherNext −0.1, IFS +0.2, AIFS +0.3 hPa overall. AIFS reaches +0.7 at
  78–120 h. Pressure tendency (how fast it changes) gives the same order.

## Main caveat: ensemble mean versus single runs

WeatherNext's value is the **mean of its ensemble**; IFS HRES and AIFS Single are **single
deterministic runs**. Averaging an ensemble smooths away unpredictable detail, which lowers MAE
more and more as lead grows. That fits the widening gap, so this pilot **does not show that
WeatherNext is a better pressure model**. A fair test needs an ensemble mean on the ECMWF side, for
example the ECMWF ensemble mean, if Open-Meteo's Single Runs API serves it (not checked).
Other limits: 16 days in one autumn, 8 stations, and Frost QFF reduction at each station is
not reviewed. These are products, not a clean AI-versus-physics test.

## Suggestions for review (nothing changed)

1. Pressure backfill works for WeatherNext and IFS/AIFS, so there is no urgency to collect it live.
   Yr pressure is the only part that must come from the archive.
2. Next study step, if wanted: add an ECMWF ensemble-mean series, then extend to the other
   complete low stations from §6. Keep offshore and mountain stations as separate exploratory
   groups, and the Norne/Goliat/Aasta series conflicts excluded until a series policy is chosen.
3. Do not put pressure on the public page until Yr has enough archived runs for a four-product
   comparison.
