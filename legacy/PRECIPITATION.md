# Hourly precipitation convention

WeatherApp stores Frost hourly precipitation in `observations.precipitation_1h`
using the exact element `sum(precipitation_amount PT1H)`. Accepted Frost metadata
is unit `mm`, time resolution `PT1H`, and time offset `PT0H`.

The stored Frost `referenceTime` is preserved unchanged as `observed_at`. It is
the end of the accumulation interval: a value at `T` describes `[T-1h, T)`.

The canonical comparison key for the same physical one-hour interval is:

| Provider | Stored time | Canonical interval end |
| --- | --- | --- |
| Frost | `referenceTime = T` | `T` |
| WeatherNext | `end_time = T` | `T` |
| Yr/MET | `valid_at = T-1h` for `next_1_hours` | `valid_at + 1h = T` |

Consequently, raw Yr/MET `valid_at` must never be joined directly to Frost
`referenceTime` for precipitation.

Collection is limited to active stations registered in `observation_sources` for
`precipitation_1h`. Unsupported stations are not requested. The existing unique
observation key and UPSERT path make repeated collection idempotent and merge
precipitation without replacing temperature or wind.

Production scoring and dashboard views now use this canonical interval-end mapping.
Both issue and local metric retrieval precede interval START, with comparable
end leads and identical observations. Wet is strictly >0.1 mm/hour. All-hour
MAE is accompanied by wet-hour and POD/FAR/CSI context; see SCORING.md for the
complete eligibility, deduplication and metric definitions.



## Optional 6h and 24h verification

Overall accuracy offers 1h (default), fixed non-overlapping UTC 6h
(00–06, 06–12, 12–18, 18–24) and UTC calendar-day 24h totals. Forecast
vs Actual remains hourly. Every period requires all six or 24 aligned
Frost/Yr/WeatherNext hours, with one complete run per provider. No partial
sum or missing-hour zero fill is scored.

Both issue and every component retrieval precede period start. Accumulated
lead is measured from issue to period START for both providers; both leads
must share a precipitation bucket and differ by no more than 3h. Closest
lead gap, then newest runs and stable IDs choose pairs without consulting
errors. Hourly interval-end leads and matching stay unchanged.

Wet thresholds are strictly >0.1 mm/hour, >0.5 mm/6h and >1.0 mm/day,
centralized in scoring/precipitation.py. The interface shows amount and
observed-wet MAE, bias, POD/FAR/CSI, counts, UTC dates and actual lead
ranges. The 24h sample is preliminary: the validated snapshot has 160
distinct station-days (293 period/lead pairs); 6h has 796 distinct
station-periods (2,110 pairs). See SCORING.md and the local benchmark
work/precipitation-aggregation-benchmark/REPORT.md.
