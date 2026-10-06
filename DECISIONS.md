# Decisions

_Updated 2026-09-28_

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

## ECMWF IFS and AIFS via Open-Meteo — 2026-09-27 (Claude)

- Two more providers are collected in the cloud run, in the same fetch as Yr and WeatherNext
  and for the same horizon windows: `ifs` = ECMWF IFS HRES (`ecmwf_ifs`, 9 km, hourly to 90 h)
  and `aifs` = ECMWF AIFS Single (`ecmwf_aifs025_single`, 0.25°, 6-hourly, interpolated to
  hours by Open-Meteo), from `https://api.open-meteo.com/v1/ecmwf` (`cloud/openmeteo.py`).
- Each station's `elevation_m` is sent as `elevation`, so Open-Meteo adapts temperature to the
  station's height ("nan" when unknown: grid-cell height). Wind in m/s at 10 m. `precipitation`
  is the preceding-hour sum, so its time is the interval end, like Frost, Yr and WeatherNext.
  AIFS hourly rain is a 6-hour amount spread over the hours; treat its hourly rain scores with care.
- Issue time = the model's `last_run_initialisation_time` from Open-Meteo's metadata at fetch
  time (informative only; leads are measured from the fetch, as for the others).
- Scored rows gain `ifs_issued/t/w/p` and `aifs_issued/t/w/p`. They come from the same fetch
  as the row Yr and WeatherNext select; pairing and scoring rules are unchanged. Rain columns
  are blanked beyond 48 h as for the others. Existing history files are not rewritten, so the
  columns start empty.
- Not shown on the page yet; health records them as source `ecmwf` (not drawn).
- Terms: Open-Meteo's free API is for non-commercial use (this site has no ads or
  subscriptions), under CC BY 4.0, with limits of 600 calls/min, 5,000/hour and 10,000/day. One
  location with up to 10 variables and 2 weeks is one call, so a run is ~50 calls (~200/day).
  Requests go in batches of 25 stations, 1 s apart, with back-off on 429/5xx. Attribution:
  "Weather data by Open-Meteo.com" with a link (Open-Meteo licence page) and ECMWF's wording for
  services built on its data, with a note of Open-Meteo's changes (ECMWF licence). ECMWF open
  data (IFS and AIFS) is CC BY 4.0. Turn off with `OPENMETEO_ENABLED=0`.

## WeatherNext terms — 2026-09-26 (Claude)

Sources read on 26 Sep 2026: the real-time terms
(https://storage.googleapis.com/weathernext-public/terms-of-use.pdf, "Last modified: 3 September
2026"), the attributions PDF
(https://storage.googleapis.com/weathernext-public/weathernext-3-attributions-acknowledgements.pdf)
and the "Terms of Use" / "Citations" sections of the Earth Engine catalog page for
`weathernext_3_0_0_0p05deg`. Our reading, not legal advice.

**Real-time vs historic** (terms PDF, preamble):
> "These GDM Real-Time Weather Forecasting Experimental Data Terms of Use apply to any data that
> relates to a time less than 1 hour ago and the future"
> "Any data that relates to a time 1 hour ago or more is licensed under the Creative Commons
> Attribution International License, Version 4.0 (CC BY 4.0)."

**Public sharing** (terms PDF, sections 2–3): real-time data may be used "for any internal
purpose", to create a Value Added Service, and shared only with "clearly identified third parties
via controlled distribution (which does not enable onward sharing), solely for educational
purposes", subsidiaries and contractors. Subsetting or reformatting still counts as
"unmodified Real-Time Experimental Data". A value-added service "from which the Real-Time
Experimental Data cannot be retrieved or reverse engineered without significant technical effort
or expense" may be shared "including by publication"; a retrievable one only via "controlled
transmission or supply to clearly identified and known third parties".

**Attribution**
- Terms PDF, section 4(b), for findings and non-retrievable services: "you must cite the Google
  product or service you used to access the Real-Time Experimental Data and "© 2024-6 Google LLC,
  whose machine learning models were used to create the experimental data made available under
  the following licence terms https://storage.googleapis.com/weathernext-public/terms-of-use.pdf.
  This data is intended for experimental modelling only and is not intended, validated, or
  approved for real world use.""
- Terms PDF, section 4(a), only when sharing real-time data or a retrievable service: a copy of
  the terms, a "Legally Binding Terms of Use" text file, "Copyright 2024-6 Google LLC" and notice
  of modifications. Not applicable to us while we publish error statistics only.
- Catalog "Citations", historic data: "© 2026 DeepMind Technologies Limited's machine learning
  models used to create the experimental data made available at
  https://developers.google.com/earth-engine/datasets/catalog/projects_gcp-public-data-weathernext_assets_weathernext_3_0_0_0p05deg
  under CC BY 4.0 licence terms. This data is intended for experimental modelling only and is
  not intended, validated, or approved for real world use."
- Catalog "Acknowledgements": generated using "data and products of the European Centre for
  Medium-Range Weather Forecasts (ECMWF), as well as additional third-party providers", with the
  attributions PDF linked. That PDF lists the upstream sources (ERA5, ECMWF HRES, EUMETSAT, NOAA,
  NASA, JMA, KMA, …); it states no separate requirement for users of WeatherNext output. We link to it.

**Policy**
- The page publishes WeatherNext **error statistics only** (non-retrievable findings), with the
  real-time 4(b) citation naming Google Earth Engine, the historic CC BY citation and the
  acknowledgement link (`ATTRIBUTION` in `cloud/config.py`, rendered with clickable links).
- ~~Raw WeatherNext forecast values stay off.~~ Superseded on 2 Oct 2026, see below.
- Both working state and scored `history/` day files are encrypted with `WX_STATE_KEY`.
  CI authenticates/decrypts in memory to build aggregate page data. Forecast values in
  page exports follow the 2 Oct decision below; the repository's day files expose ciphertext.
- Encryption at the current branch tip does not erase past plaintext Git objects.
  Previously published history/state copies may remain available via old commits or
  caches until a coordinated repository-history cleanup. Do not claim encryption alone
  removes those copies. No history rewrite or force-push of main is authorized by this task.

**Are values older than one hour publishable?** Yes, answered by Google on 4 Oct 2026 (below):
"relates to a time" means the forecast's **target** (valid) time, not its issue time.

**Decision of 2 Oct 2026 (user): publish past WeatherNext forecast values under CC BY 4.0.**
- Our reading: the terms say data that "relates to a time 1 hour ago or more is licensed under
  the Creative Commons Attribution International License, Version 4.0 (CC BY 4.0)". A forecast
  for a target time at least 1 hour in the past is therefore historic data, and may be
  published with the required citation.
- **Google's answer (4 Oct 2026):** the user asked weathernext@google.com on 26 Sep 2026. Google's
  WeatherNext team replied on 4 Oct 2026 that the 1-hour rule applies to the **target time**: a
  forecast for a time at least 1 hour ago is historic data (CC BY 4.0), and a forecast for a future
  time is real-time data, even if it was issued days ago. Our `PUBLISH_MIN_AGE_H` = 1 rule, applied
  to target time, matches this. (The emails are not in the repository; recorded as the user
  reported them.)
- **Rule: the page must never show WeatherNext values for future target times**, nor for targets
  less than 1 hour ago. Those are real-time data under the real-time terms, however old the run.
  The cutoff is on target time, never on issue/fetch time; keep it that way in any new view.
- If Google asks, we remove the values at once: set `WX_PUBLISH_FORECAST_VALUES` to 0 (the next
  run rebuilds the page without them) and record it here.
- How it is limited: values are published only for target times at least
  `PUBLISH_MIN_AGE_H` = 1 hour in the past (`cloud/summarize.py`, `cloud/replay.py`); the page
  only uses scored, finished days anyway. Future and recent forecasts stay in the encrypted
  `state` branch and never reach the page. `history/` day files stay encrypted for now.
- Attribution: the CC BY citation and the real-time notice (with "accessed via Google Earth
  Engine") are shown directly under every chart that draws WeatherNext values (station chart,
  storm replays), as well as in the footer.
- Switch: the workflow reads the repository variable `WX_PUBLISH_FORECAST_VALUES` (default
  0). It is turned on by setting that variable to 1; the change is in effect from the next run.

## One-off fill of the first cloud days — 2026-09-26 (Claude, user's decision)

- The cloud day files for 23 and 24 Sep had no WeatherNext (the service account had no access
  yet; 23 Sep was empty). With the user's OK they were replaced once from the PC database with
  `migrate_sqlite --from 2026-09-23 --until 2026-09-25 --fill-missing-wn`: 7,910 and 8,274 rows,
  all with WeatherNext, marked `wn_sampling = nn5km`. This is the only exception so far to
  "history files are written once". 25 Sep already had WeatherNext and was kept.

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
- Stations with a cell–station height difference of ≥ 100 m under either sampling method are
  flagged on the page (both figures shown). E6 Mjøsbrua, Sunndalsøra III and Oslo-Blindern
  carry a note that, in the data up to 26 Sep, height explained only part of the error
  (night-time lake / fjord-head / urban warmth).
- Bilinear sampling is chosen because it matches Google's method, not to improve scores. It
  raises the effective cell height at some coastal stations (Sunndalsøra 134 → 318 m, Bergen
  30 → 142 m), so their published WeatherNext values may read colder from 26 Sep on. The
  height-adjusted line accounts for that per row.

## Cloud collection every 3 hours — 2026-10-01 (Claude)

- The GitHub Actions collection runs every 3 hours at minute 17 (`17 */3 * * *`), was every 6 h.
  Applies to the cloud pipeline only; the local Windows task and its health thresholds (6 h, OK ≤8 h)
  are unchanged until the PC collector is retired.
- Pairing, horizons and finalization are unchanged: lead is measured from each fetch and the closest run
  to each horizon wins, so more runs only bring the lead closer to nominal. No history is rewritten.
- Page health: 16 runs expected in a 48 h window; "collection may have stopped" after 8 h
  (3 h interval + 5 h for GitHub's schedule delays, seen at 3–5 h; user's choice). Expected runs are counted
  per period across the change (`cloud/health.py`); drop that transition code after 3 Oct.
- The run log keeps 120 records (15 days at 8 a day).

## Independent timer activation — 2026-10-06 (Codex)

- User approved pushing the timer change and using cron-job.org after diagnosis:
  hourly GitHub starts were missing, with gate logs showing success ages of 406
  and 561 minutes. The gate itself correctly allowed those late runs.
- Use an independent POST every 30 minutes (:07/:37 UTC), retaining the hourly
  GitHub fallback, shared concurrency and 150-minute gate. Collection should be
  roughly every 150-180 minutes when dispatches start promptly; no strict SLA.
- The workflow change is deployed (rebased timer commit 0d97cf8; setup 1bbd7c4).
  Run 37453257515 verified a timer skip at 135 minutes, without state or Pages
  publication. CI 37453257669 passed. On 6 Oct, the user saved the scoped token
  directly in cron-job.org; job 8590224 was enabled after an HTTP 204 external test.
  Resulting run 37495000121 correctly skipped at 65 minutes. Recurring cadence
  remains to be measured; renewal is needed before 5 Nov 2026 (17:15 UTC expiry).
- HTTP 204 proves dispatch acceptance only. Verify subsequent gate decisions,
  collection success and the public health timestamp separately. Enable timer
  failure/disable notifications and renew its scoped token before expiration.

## External timer dispatch respects the gate — 2026-10-06 (Codex)

- `collect.yml` accepts the `workflow_dispatch` choice input `trigger`: `manual`
  (default) or `timer`. Pass `--manual` only for a `workflow_dispatch` event with
  `inputs.trigger == 'manual'`; timer dispatches use the existing 150-minute gate.
- Keep the hourly GitHub schedule (`23 * * * *`) and `collect` concurrency group.
  A skipped timer run has the same behavior as a skipped scheduled run.
- External timers POST the dispatch body documented in `SETUP_CLOUD.md`. Use a
  fine-grained token for this repository only, with Actions: Read and write;
  real tokens belong only in the timer's secret store, never in repository files.
- This refines the 4 Oct decision: dispatch alone no longer implies a gate bypass.
  Deployment and live timer verification wait until the user approves a push.

## Hourly trigger with a 150-minute gate — 2026-10-04 (Claude)

- GitHub ran the 3-hourly cron only 8 times in 48 h (runs #33–#43, gaps 4.4–9.4 h). The cron is now
  hourly (`23 * * * *`); a gate step right after state restore (`python -m cloud.run due`,
  `health.due`) ends the job successfully, without collecting, publishing state or deploying, while
  the last **successful** collect (`last_success`, as on the page) is under `MIN_GAP_MIN` = 150 min
  old. Manual `workflow_dispatch` runs always collect. The `collect` concurrency group stays, so runs
  never overlap.
- The expected cadence stays `RUN_EVERY_H` = 3 (16 runs per 48 h on the health line); skipped runs
  leave no run record. 150 min rather than 180 so a late run doesn't push the next one a whole hour.
- The 6 → 3 h transition code (`PREVIOUS_RUN_EVERY_H`, `RUN_EVERY_CHANGED_AT`) is removed.

## Monthly summary and rain median headline — 2026-09-28 (Claude)

- `site/data/summary.json` is built at export from decrypted history, one entry per UTC calendar
  month (by target day): the current month "so far" plus every completed month. It reuses
  `summarize.paired`/`stats` unchanged: same pairing, 95% day-block bootstrap, 7-day minimum
  (counted within the month). Horizons 6 h, 1, 2, 3, 5 days for temperature and wind; 6 h, 1, 2 days
  for rain (hourly rain is not scored beyond 48 h). It holds verdicts and text only, never forecast
  values, and ECMWF is not shown.
- The text is fixed templates. A winner is named only where the verdict says so; otherwise "too close
  to call" or "not enough days yet". Horizons with the same verdict are grouped ("1–2 days out",
  "from 3 days"). Temperature uses as-published WeatherNext; one "height-adjusted temperature
  differs" clause appears only for horizons where the adjusted verdict differs. Winner clauses are
  ordered by winner name, then temperature before wind. Rain gives two lenses: WeatherNext's average
  and its median, each against Yr. A tie is written "too close to call", not "about equal".
- Rain views lead with WeatherNext's median (solid line, headline value, headline verdict); the
  average is the dashed line and a second verdict line. Reason (FINDINGS 2026-09-26, rec. 2):
  averaging many scenarios spreads light drizzle everywhere. The median verdict is a new statistic
  (`verdict_50`, `diff_50`, `ci_50_*`) computed on forecasts that have a median; scoring, pairing and
  history are unchanged. Temperature and wind keep the average as the main value.

## Encrypted history and recoverable publication — 2026-09-28

- User authorized encrypting existing committed day files as a storage-only exception
  to write-once history. Encrypt original gzip bytes, verify exact decryption equality,
  and never rescore or alter existing observations/forecasts during conversion.
- Every new scored day requires `WX_STATE_KEY`; missing/invalid keys stop writes.
  Existing plaintext remains readable only for controlled migration. The existing
  `.csv.gz` paths now contain Fernet ciphertext. Local decrypt copies belong only in
  ignored `outputs/`; see SETUP_CLOUD.md. Losing the key now loses access to scored
  history as well as pending forecasts; retain the separate secret backup.
- Coverage is unique configured station × exact UTC hour slots with at least one
  finite Frost temperature, wind or rain value, divided by 24 × configured stations.
  The denominator is independent of surviving forecast rows. At day-end +6h, prepare
  a day only at >=80% coverage; otherwise retry until day-end +72h, then prepare the
  available data and set `late_finalized=true`. Record coverage and counts in day meta.
- Preparing a day never deletes pending rows. Write its coverage sidecar before the
  encrypted day, so interrupted writes can retry without losing provenance. Existing
  legacy days have unknown coverage, never fabricated values.
- Publish history to main without force, fetch origin and verify encrypted day blobs
  and matching metadata, then prune only those exact days and publish encrypted state.
  Main push/confirmation failures never reach pruning or state publication. A failed
  state push leaves previous remote state recoverable; reruns reuse immutable history.
- State restore may initialize only when `git ls-remote --exit-code` returns 2 for a
  missing state ref. Authentication/network/clone/decryption/schema failures abort.
  State replacement uses an explicit force-with-lease against the restored commit.
- Keep observations 15 days (longer if retained pending days need their baselines),
  and refetch five UTC calendar days. Report source failures after persistence and
  health publication, rather than using `--strict` to skip those steps.
- Validation uses temporary Git remotes and disposable state. This change is committed
  locally for review; deployment/push remains pending the user's instruction.
