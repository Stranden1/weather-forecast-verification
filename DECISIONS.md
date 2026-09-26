# Decisions

_Updated 2026-09-23_

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
- Forecast vs Actual defaults to Trondheim-Voll and the newest useful fair run
  pair. Advanced manual mode retains independent run selection. Both use Frost
  at the exact forecast valid time as actual.
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
  supported element. Production rainfall scoring now enforces the canonical
  mapping, availability before interval start, identical targets and comparable
  leads; see the production decision below.

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


## Automatic front-page pairing and health presentation — 2026-09-22

- Reuse pair_forecasts for eligibility rather than invent another fair matcher.
  The default scorer path and its target deduplication remain unchanged; the UI
  can request all eligible pairs before choosing one whole-run pair.
- For the selected station/variable/window, prioritize pairs with exact observed
  targets. Choose the maximum (earlier issue, later issue, MET run ID, WN run ID).
  Neither forecast error nor sample count determines which pair is selected.
- If there are no observed pairs, prefer a fair pair with future targets, then
  the newest remaining fair pair. Explain missing observations explicitly. If
  no eligible pair exists, label latest independent runs as inspection-only and
  report a measured issue gap when it exceeds 3h; otherwise explain target eligibility.
- Apply 72h/168h windows from the first stored valid time of either selected run;
  Full run has no such cut. Front-page summaries describe the displayed window.
  Preserve exact targets, issued/collected-before-valid, lead buckets and ≤3h gap.
- Manual mode keeps independent dropdowns, including a selected older automatic
  run outside the usual recent list. Disagreement inspection opens manual mode.
- Healthy status uses text plus a single summary line; source details and resolved
  recent gaps stay collapsed. Active source problems and stale Yr warnings stay
  visible. Do not change health thresholds or source-completion logging.


## Exploratory precipitation analysis — 2026-09-22

- Keep this benchmark outside production scoring/dashboard; no data edits.
- Use canonical interval-end leads for both models and require original issue
  and metric retrieval strictly before interval start. WeatherNext rainfall uses
  normalized mean samples and sample-level retrieval timestamps.
- Requested [0,12)/[12,24)/[24,48)/[48,72)h summaries retain existing bucket equality
  as an additional conservative condition, <=3h gaps and the existing closest-gap/
  newest-run tie order. Deduplicate once per station/end/requested bucket.
- Wet is >0.1mm per hour, dry/non-event <=0.1mm. Retain amount, wet-only and event
  results separately; no composite. Empty buckets have no score. Partial coverage
  is explicit. Never choose timestamp alignment or forecast pairs using errors.
- The local report supports cautious future implementation, not a stable model
  ranking. Production rainfall remains disabled; analysis artifacts stay ignored.


## Production precipitation verification — 2026-09-22

- Promote the validated read-only rainfall adapter into scoring/precipitation.py;
  share its pair_rows path across overall, automatic and manual selected-run
  scoring. It calls existing pair_forecasts rather than copying its pair order.
- Keep benchmark's additional same precipitation-bucket check, strict availability
  before interval start, canonical end leads, and sample-level WN retrieval.
- Centralize >0.1mm/hour wet threshold; amount, wet-hour and POD/FAR/CSI results
  accompany each other. Undefined rates are missing. No winner or weather score.
- Integrate existing variable/station/period/lead patterns. Dynamic actual lead
  ranges expose partial 48–72h coverage. Plot interval-end hourly amounts without
  adding uncertainty work, accumulation scoring or probability calibration.
- Temperature/wind, long-range and disagreement behavior remain unchanged.
  No data/schema, collector, schedule or station-network changes.
- Preserve existing benchmark document edits; clean-start commit condition was
  not met, so leave validated work uncommitted. No push requested.


## Optional accumulated precipitation — 2026-09-23

- Keep canonical hourly scoring and Forecast vs Actual unchanged; offer
  optional 6h/24h verification in Overall accuracy, with 1h default.
- Use fixed UTC periods, all exact component hours, and one run per provider.
  Exclude incomplete periods. Do not mix runs or fill absent hours with zero.
- Measure both accumulated leads to period start. Both issues and every
  sample retrieval must be before start. Require the same precipitation
  start-lead bucket, a lead gap <=3h, and error-independent closest-lead/
  newest-run ordering. Show actual lead ranges and distinct period counts.
- Centralize strict wet thresholds >0.1 mm/hour, >0.5 mm/6h and >1 mm/day.
  Keep MAE, bias, observed-wet MAE and event metrics separate; no winner score.
- The local read-only benchmark is the validation reference. Its 2,110
  six-hour and 293 daily pairs reproduce exactly at the fixed snapshot.
  No schema, data, collector, station network or schedule change is needed.

## WeatherNext dashboard status performance — 2026-09-23

Routine dashboard reruns read the latest stored model run and finalized collection
outcomes without counting the WeatherNext sample table. Collection health for
Yr, Frost and WeatherNext remains separately computed from source-level log
outcomes on every rerun. Stored or backfilled forecasts alone do not establish
a successful collection.

Exact WeatherNext forecast/statistic counts are requested explicitly in the
status expander. Their displayed snapshot includes a check time, and is cleared
after a new scheduled attempt, a newer run, or a successful manual WeatherNext
fetch. No TTL, schema change or collector-side summary is needed.

## All-station precipitation query — 2026-09-23

Use a partial SQLite expression index on
`weathernext_samples(julianday(valid_at), run_id)` for precipitation mean samples
in mm, with matching `julianday(s.valid_at)` bounds in the read query. This keeps
mixed timestamp comparison semantics and changes the plan from a whole-table scan
to a bounded sample-index search. The additive index changes no data or scoring.
Tested covering-index and forecast-driven alternatives did not improve the path;
do not broaden this into a matcher rewrite without separate evidence and validation.

## Long-range temperature query performance — 2026-09-23

For retrospective scoring, filter the existing inclusive 69–219 h lead range in
SQL before Pandas materialization, while retaining the later timestamp-derived
lead consistency check. Keep verified-history as the outer loop with SQLite
`CROSS JOIN` ordering so each manifest point probes existing primary keys rather
than scanning all WeatherNext runs/samples. Scope Frost reads by the selected
station and date range. These changes preserve eligibility and matching; exact
fixed-snapshot pairs and scores were checked. No cache or index was needed.

## Compact cloud pipeline — 2026-09-23 (Claude)

- Goal: long-term public "who is more accurate" without ~100 GB/year of raw data.
- Store only forecast hours within ±3 h of horizons 6/12/24/48/72/120/168/240 h;
  score each UTC day once (6 h after it ends) and delete its snapshots.
- Pair Yr and WeatherNext from the SAME collection run; lead = target − fetch
  time for both. Closest run to each horizon; runs with both providers preferred;
  ties to the later run. Errors never influence selection.
- WeatherNext: newest hourly init (≤48 h) for short targets, newest synoptic
  otherwise; mean, p10, p50, p90. Score mean and median.
- Yr from the `complete` endpoint (p10/p90, rain min/max/probability).
- Hourly rain only for 6 h–48 h horizons; interval-end keys as in PRECIPITATION.md.
- Verdicts: 95% block bootstrap by day on the MAE difference; none before 7 days.
- Working state on a force-pushed `state` branch; permanent `history/` on main;
  site JSON built in CI and never committed.
- Publish WeatherNext error statistics only until its real-time terms are read.

## Cloud pipeline scoring additions — 2026-09-24 (Claude)

- Naive baseline = observation at target − 24·⌈lead/24⌉ h, using the actual lead (review
  decision), so it is always measured at or before fetch time. Skill = 1 − MAE_model /
  MAE_naive, on rows with a baseline only; no skill value when the naive MAE is 0. The
  page shows skill as "N% better/worse than a naive guess".
- Existing `history/` day files are not rewritten to add baselines (written once).
- Pinball score and p10–p90 width are compared on rows where both providers have all
  three quantiles; Yr's main value is its p50. The "inside range" hit rate stays per provider.
- Frost fetch window (4 days) and observation retention (12 days) are now separate settings.
- health.json publishes statuses and counts only, never raw error messages.

## WeatherNext sampling and station height — 2026-09-26 (Claude)

Evidence: `INVESTIGATION_COLD_BIAS_2026-09-26.md`.

- WeatherNext values are now **interpolated bilinearly from the native grid** (0.05° for
  temperature, 0.1° for wind/rain/pressure) at the station point, as in Google's own station
  verification. Before, `reduceRegions(scale=5000/10000)` without a grid made Earth Engine
  resample first, and 15 of 50 stations got a neighbouring cell (e.g. Losistua 1165 m
  instead of its own 858 m cell). Verified live: all 50 stations match a hand-computed
  bilinear value within 0.03 K / 0.01 m/s.
- The change applies from a dated cutoff, never to written history. Scored rows carry
  `wn_sampling` (`bilinear`, or `nn5km` for the old method; empty in files written before
  the change means `nn5km`). The cloud collector marks its rows directly. The PC collector
  switched at `LOCAL_BILINEAR_SINCE` = 2026-09-26 16:00 UTC (between its 10:10 and 16:10
  UTC runs); `migrate_sqlite` marks a WeatherNext run `bilinear` only if every value was
  retrieved after that time. `weather.db` values already stored are not re-fetched.
- As-published WeatherNext stays the primary score, and no station is dropped.
- A **height-adjusted** WeatherNext temperature is shown as a separate, labelled line:
  `wn_t + 6.5 °C/km × (model cell height − station height)`, land stations only. The cell
  height is the GMTED2010 mean over the cell (Google does not publish its grid heights),
  bilinearly weighted for `bilinear` rows. It is our adjustment, not Google's product.
- Stations with a cell–station height difference of ≥ 100 m are flagged on the page.
  E6 Mjøsbrua, Sunndalsøra III and Oslo-Blindern are flagged as not explained by height
  (night-time lake / fjord-head / urban warmth).
