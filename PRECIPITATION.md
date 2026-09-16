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

Precipitation scoring and dashboard charts remain disabled. A future scoring
change must apply the canonical interval-end mapping, identical observed targets,
comparable lead-time rules, and the existing collected-before-valid-time rule.

