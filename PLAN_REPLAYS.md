# Plan: storm replays + forecast steadiness

_Written 2026-09-25 by Claude. Not started. Status is in the checklist at the bottom._

## Goal

Add two things to the public page that people who are not statisticians find
interesting, using only the scored `history/` files, with no new collection:

1. **Storm replays.** For a notable weather event, show what Yr and WeatherNext
   said 7, 5, 3, 2 and 1 day(s), 12 h and 6 h before, next to what was measured.
2. **Steadiness ("flip-flop").** How much each service changes its forecast for
   the same moment from one horizon to the next, and whether those changes move
   toward the truth.

## What the data allows (checked 2026-09-25, 18 migrated days)

- Each history row is one station, target hour and horizon. The same target
  appears at up to 7 horizons, so how a forecast changed over time can be rebuilt
  directly.
- Horizon rows: 6 h ≈ 20k, 12 h ≈ 20k, 1 d ≈ 19k, 2 d ≈ 18k, 3 d ≈ 9k, 5 d ≈ 7k,
  7 d ≈ 4.5k, **10 d only 5**. Beyond ~2.5 days Yr is 6-hourly, so long horizons
  exist only for 00/06/12/18 UTC targets.
- **Rain is scored only at 6 h–2 d** (`PRECIP_HORIZONS`). Rain replays therefore
  count down 2 days, not 7. Temperature and wind replays go to 7 days.
- In a check of 6 h vs 12 h and 12 h vs 24 h, the WeatherNext and Yr issue times
  always differ. Every revision is a real new forecast. Keep checking this (see rules).
- WeatherNext is present in history only from 2026-09-15 to 09-22 (the cloud
  service account is still blocked). Events before that have Yr only.
- Events already present: 16 station-days with ≥ 20 mm of rain and 143 hours with
  wind ≥ 15 m/s. The best first case is **15 Sep, western Norway**: Bergen-Florida
  46.8 mm, plus three more stations ≥ 20 mm the same day, with both services present.

## Fairness rules

- **Events are chosen only by what was observed**, never by forecast errors, so
  the list is not biased toward one service's misses.
- Every replay value for a horizon uses the existing history row for that horizon
  (same fetch and same lead for both services). No new pairing logic.
- Rain day totals at horizon H = the sum of the 24 hourly H-horizon forecasts
  ("what you'd have seen H hours before each hour"). Shown only when all 24 hours
  exist for both services. The caption says so.
- Wind/temperature replays use the most extreme observed hour **that has forecasts
  at the most horizons**, so every horizon is compared on the same target hour.
- Steadiness is compared on identical station/target/horizon pairs where both
  services have both forecasts. A revision where a service's issue time did not
  change is left out and counted separately.
- Caveats on the page: an ensemble mean is naturally smoother, so it will look
  steadier. Yr's short range is corrected hourly from stations, so it revises more
  near the event. Steadiness alone is not accuracy, so show it next to "moved
  toward the truth".

## Definitions

**Steadiness**, per variable, per consecutive horizon pair (7→5 d, 5→3 d, 3→2 d,
2→1 d, 1 d→12 h, 12→6 h):
- `rev` = mean |forecast(shorter) − forecast(longer)|: the typical revision size.
- `toward` = share of revisions (larger than a small threshold) that reduced the
  absolute error.
- `flip` = flip-flops per 100 target hours: consecutive revisions in opposite
  directions, each ≥ 1 °C / 2 m/s / 0.5 mm.
- Also report `n`, plus a 95% day-block bootstrap interval on the difference in
  `rev`, reusing `bootstrap_diff`'s approach and `MIN_DAYS_FOR_VERDICT`.

**Events**, one row per UTC day and type (stations on the same day are grouped):

| Type | Trigger (observed) | Replay value |
|---|---|---|
| Heavy rain | station-day total ≥ 20 mm, all 24 h observed | day total, 6 h–2 d |
| Strong wind | hourly mean ≥ 15 m/s | selected hour's speed, 6 h–7 d |
| Cold snap | hourly ≤ −5 °C, or the first sub-zero hour of the season at a lowland station | selected hour's temperature, 6 h–7 d |

The headline station is the most extreme one. The others are listed with their
observed values. Keep the most recent 30 events plus the top 5 per type of all time.

## Build

1. `cloud/replay.py` (new, pure functions on the scored DataFrame):
   `steadiness(scored, var) -> dict`, `find_events(scored) -> list[dict]`,
   `replay(scored, event) -> dict`.
2. `cloud/summarize.build` writes `steadiness.json`, `events.json` (index) and
   `events/<id>.json` (id = `YYYY-MM-DD-<type>`, so it is stable across runs).
3. **Publishing gate.** A replay shows WeatherNext **values**. Observation plus
   error also reveals the value. With `WX_PUBLISH_FORECAST_VALUES=0`, replays
   show observed values and Yr, and a note that WeatherNext values wait for its
   terms review (PLAN_WEBPAGE step 11). Steadiness is published aggregated in any case.
4. `site/`: a new card **"Storm replays"** with an event list, a countdown chart
   (x = time before, y = forecast, dashed line = measured) and a small map dot.
   Put a **"How steady are the forecasts?"** row under "Error by how far ahead"
   (revision size by horizon step, plus the "moved toward the truth" percentage).
   Light/dark, 375 px mobile, text labels, not colour alone.
5. `cloud/demo.py`: generate one event of each type, so `site/index.html?demo` shows them.
6. Tests `cloud/tests/test_replay.py`: event triggers and grouping, selection
   independent of forecasts (changing forecasts leaves the event list the same),
   incomplete rain day skipped, the same-issue revision excluded, flip-flop counting,
   the publish gate removing WeatherNext values, stable IDs, empty history.

## Steps and status

- [ ] 0. **User decision:** read the WeatherNext real-time terms and decide
       `WX_PUBLISH_FORECAST_VALUES`. Without it, replays show Yr and observed values only.
- [x] 1. Steadiness: `replay.steadiness` + JSON + tests. Commit.
       *2026-09-25: `cloud/replay.py`, `site/data/steadiness.json` (not shown on the
       page yet), 9 tests (35 cloud tests pass). An unknown issue time counts as new.
       Real history (7 days with both services): WeatherNext revises about half as much
       as Yr at 6 h–2 d (temperature 12→6 h: 0.17 vs 0.34 °C; significant at 1 d→12 h
       and 12→6 h). Temperature flip-flops per 100 forecasts: Yr 2.5 / WN 0.2. Revisions
       move toward the truth only ~50–57% of the time for both. The smoothness of the
       ensemble mean is the expected main cause, so the caveat matters.*
- [ ] 2. Events + replays: `find_events`, `replay`, JSON, publish gate + tests. Commit.
- [ ] 3. Page cards + demo data. Check light/dark/mobile with `?demo` and the real history. Commit.
- [ ] 4. Check the 15 Sep western Norway case by hand against `history/` values.
- [ ] 5. Update PLAN_WEBPAGE, PROJECT_STATUS, NEXT_STEPS and WORK_STATUS. Push only with the user's OK.

Later (not in this plan): rain replays beyond 2 days need the snapshot to keep
6-hourly rain totals at long horizons (a change to `cloud/yr.py` and the snapshot).
