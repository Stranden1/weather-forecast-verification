# Decisions

_Updated 2026-09-16_

- SQLite remains the local source of truth; WeatherNext extends the existing
  forecast model rather than introducing a separate datastore.
- Yr/MET, WeatherNext, and Frost share one active station network and coordinates.
- WeatherNext uses provider ID `WeatherNext3-mean`; ensemble statistics remain in
  `weathernext_samples`, while compatible means also populate `forecasts`.
- Collection writes are additive and idempotent. Repeating a completed run adds
  zero values and does not replace history.
- The scheduled sequence is station refresh when needed, Yr/MET, Frost, then
  WeatherNext. A WeatherNext failure is reported without undoing earlier work.
- Dashboard browsing opens the database read-only. Explicit Admin collection
  actions are the only dashboard paths that invoke writers.
- Dashboard and stored timestamps are UTC.
- Forecast vs Actual selects Yr/MET and WeatherNext runs independently, defaults
  to Trondheim-Voll and the newest runs, and uses Frost's hourly mean as actual.
- Selected-run MAE uses elapsed matched hours and the established lead-time
  buckets; temperature is the only detailed comparison for now.
- WeatherNext p10–p90 is displayed as uncertainty, not as a confidence guarantee.
- Selected-run lead-time MAE uses horizontal dots (provider colors and distinct
  shapes), avoiding oversized bars when only one bucket has observations. Sample
  counts remain in tooltips/details; scoring and matching rules are unchanged.
- UI polish retains the existing tabs, native controls and light/dark theme
  support. Summary MAE labels stay compact; shared-hour scope is explained in
  help text and the chart caption. Operational controls stay collapsed.
- WeatherNext precipitation remains stored but unscored pending interval-alignment
  validation.

- GitHub stores code history privately; keep separate local database/credential backups.
- config/stations.json is a metadata snapshot only. The live database remains authoritative.
- Preserve reusable dashboard UI testing under tests/ and local audit evidence under work/.
- Trust only E:/WeatherApp via the user's Git safe.directory setting because the
  sandbox created .git under a different Windows account.
