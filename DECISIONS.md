# Decisions

_Updated 2026-09-17_

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
- Collection health measures completed retrievals, never the newest forecast or
  observation valid time. `data/background.log` is the lightweight source of
  truth: legacy finalized summaries are supported, and new background runs append
  explicit source-level OK/ERROR/SKIPPED outcomes without changing collector data.
- The verified six-hour schedule uses conservative health thresholds: OK at no
  more than 8 hours since success, Delayed above 8 through 12 hours, and Stale /
  attention needed above 12 hours or when no success is known. A latest explicit
  failure is Delayed immediately rather than hidden by a recent success.
- A recent Yr gap means consecutive successful Yr completions more than 12 hours
  apart within the last 7 days. Only report the gap; do not reconstruct or backfill
  missing Yr history automatically.
- Forecast vs Actual selects Yr/MET and WeatherNext runs independently, defaults
  to Trondheim-Voll and the newest runs, and uses Frost at the exact forecast valid time as actual.
- Selected-run MAE uses elapsed matched hours and the established lead-time
  buckets for both temperature and wind speed; leads must be within 3 hours.
- WeatherNext p10–p90 is displayed as uncertainty, not as a confidence guarantee.
- Selected-run lead-time MAE uses horizontal dots (provider colors and distinct
  shapes), avoiding oversized bars when only one bucket has observations. Sample
  counts remain in tooltips/details; scoring and matching rules are unchanged.
- UI polish retains the existing tabs, native controls and light/dark theme
  support. Summary MAE labels stay compact; shared-hour scope is explained in
  help text and the chart caption. Operational controls stay collapsed.
- Frost hourly precipitation uses the exact element
  `sum(precipitation_amount PT1H)` in `mm`, with `PT1H` resolution and `PT0H`
  offset. Preserve Frost `referenceTime` unchanged as the interval end: a value
  at `T` represents `[T-1h, T)`.
- The canonical precipitation comparison key is Frost `referenceTime = T`,
  WeatherNext `end_time = T`, and Yr/MET `valid_at + 1h = T`. Never compare Yr's
  raw `valid_at` directly to the Frost precipitation timestamp.
- Request Frost precipitation only for active stations registered with the exact
  supported element. Keep rainfall scoring disabled until the canonical mapping,
  forecast availability, identical targets, and comparable leads are enforced in
  the scoring path.

- GitHub stores code history privately; keep separate local database/credential backups.
- config/stations.json is a metadata snapshot only. The live database remains authoritative.
- Preserve reusable dashboard UI testing under tests/ and local audit evidence under work/.
- Trust only E:/WeatherApp via the user's Git safe.directory setting because the
  sandbox created .git under a different Windows account.


## Accuracy expansion — 2026-09-16

- Enable temperature and wind speed only. The wind audit covered all current active
  stations with wind data (10 m, m/s); station 10-minute means and model grid values
  have representativeness differences. See SCORING.md for scope and sources.
- Exact-time observations replace hourly flooring/averaging in dashboard scores;
  identical duplicates count once and ambiguous values are excluded. No data edits.
- Overall comparison uses one closest-lead pair per station/time/existing bucket,
  maximum 3-hour lead gap, and only forecasts collected before valid time. Matching
  is independent of error. Counts and units are always visible; no composite score.
- Reuse existing bucket constants and MAE/bias aggregation. Keep the legacy query
  compatible, but remove it from the dashboard comparison path.
- Disagreement uses latest stored runs, shows their ages separately, and is not a
  performance score. Selection navigates to the existing read-only forecast view.
- No schema, collectors, scheduling, secret or live-history changes were needed.


## Historical temperature backfill — 2026-09-17

- Select historical initialization/hour slices from existing Yr + exact Frost
  long-range targets. Avoid an entire-year archive mirror; use the same 50 active
  coordinates and 0.05° station-head temperature collection.
- Reuse WeatherNext normalization, six-statistic storage and atomic idempotent
  writes; no schema or separate forecast database. Historical runs may be sparse.
- Validate all planned image metadata before writing, including original init,
  target, lead, asset identity and Earth Engine ingestion before target. Retain
  metadata in local run manifests; do not falsify retrieved_at.
- Keep retrospective analysis separate from production eligibility. For archives,
  use verified original Earth Engine availability; production keeps local
  retrieval-before-target. Explicit nominal ±3h windows and ≤3h lead gap apply
  to both providers, with exact Frost targets and one closest-lead pair per
  station/time/horizon. Deduplication must never depend on forecast error.
- Report temperature mean MAE, signed bias, WN-minus-Yr MAE difference, shared
  counts, actual lead ranges, and individual cases. Do not claim a broad winner
  from the short sample or tiny 3/5-day differences; leads are close, not equal.
- Archive backfill adds no wind/precipitation forecasts, dashboard feature,
  calibration, composite score or scheduled-task change. Preserve all prior
  rows and validate an identical second run before declaring completion.


## Verified retrospective view — 2026-09-17

- Persist point-specific temperature verification in one additive table in the
  existing SQLite database; the dashboard must not depend on work/ JSON files.
- Verify original availability, asset, initialization, lead, units, mean value
  and station identity before atomic registration. Retain an evidence digest;
  conflicting evidence aborts without replacing existing records.
- Retrospective scoring accepts verified original publication before target.
  Unverified data must satisfy local retrieval-before-target. Preserve actual
  retrieval timestamps and the independent operational evaluation rules.
- Reuse the audited exact nominal-horizon matcher in dashboard_scores.py.
  Old databases without verification remain readable and cannot accidentally
  admit uncertified late-collected forecasts.
- Use a compact Long-range temperature tab with one row per 3/5/7/9-day horizon,
  shared counts and actual matched periods. Empty horizons show zero samples
  and no score. Bias and actual lead ranges belong in expandable details.
- Future saved historical temperature backfills register provenance automatically.
  No new provider, background service, runtime dependency or schedule change.


## Checkpoint grouping — 2026-09-17

- Preserve the already-mixed validated dashboard, scoring, archive and collection
  health changes in one checkpoint commit. An artificial historical split would
  add risk because the source, tests and documentation are interdependent.
- Checkpoint preparation changes documentation only; no application behavior,
  live database, credentials or schedule changes. Keep runtime evidence ignored.
- This checkpoint is local; pushing is a separate user-controlled action.
