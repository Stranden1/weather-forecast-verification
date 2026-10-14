# Forecast archive and scientific expansion plan

_Design audit: 14 October 2026. Implementation requires owner approval. No production code, scoring, schedules, secrets, station configuration or historical files were changed._

## 1. Recommendation and evidence boundary

**Retain two forecast snapshots daily for the existing shared station network, separately from scored history. Start with complete Yr responses and trustworthy acquisition metadata.** Expand the same archive to coherent WeatherNext and explicitly identified ECMWF runs, with pressure, dew point and a small set of cloud predictors. Keep roughly ten days of forecast trajectory per snapshot, not every model cycle or any full global grids. Budget **3–5 GB/year of new encrypted forecast objects**, plus approximately 0.1 GB/year for observation/provenance records and 0.23 GB/year for current scored history. Reserve 6 GB/year per copy pending a measured full-network pilot; three independent copies require about 18 GB/year of capacity.

The most urgent losses are the delivered Yr trajectories and revisions, discarded Yr fields/intervals, and acquisition/observation-version provenance. Many WeatherNext and ECMWF values can be retrieved retrospectively; that is different from recovering the exact product that was available and received operationally. Do not delay the inexpensive Yr capture while designing an ideal native ECMWF archive.

Pressure is feasible: **35/49 active stations returned MSLP observations; 27/49 had at least 160/168 unambiguous hourly values over 7–13 October. All 22 land stations with MSLP had 168/168.** Start scientific verification with the eight low-elevation land stations specified below. Dew point/humidity is the next direct verification candidate; cloud cover is especially valuable as an explanatory predictor of cold-night errors.

### What was actually checked

- Working branch: `codex/scorecard-corrections`; HEAD `f868c2b` (private forecast comparison). Recent commits include `39c2617`, `d1f9669`, `3373c75`, `f546205`, `bdd645b`. Existing uncommitted scorecard and handoff edits were present before this audit and remain untouched.
- Read the working agreement, current handoffs, decisions, `PLAN_WEBPAGE.md`, `SCORING.md`, `WEATHERNEXT.md`, `FORECAST_PLAN.md`, cloud collectors/storage/scoring/export/replay/health/persistence and the collection workflow. Code takes precedence over old prose. `SCORING.md` and much of `WEATHERNEXT.md` describe the retired local app, not current cloud behavior.
- `config/stations.json` has 49 active stations; retired stations remain in history. The configured SQLite path is absent. The reported deletion of the database and its archive on 11 October is recorded in `AGENTS.md`; this audit did not search for undeclared backups or attempt recovery.
- Read-only decryption of all **37 local day files, 5 September–11 October**, succeeded: **224,292 rows**, 12,322,856 encrypted bytes. No forecast values or credentials were printed or saved. This validates the current working key, **not an independently recoverable backup**.
- Remote directory inspection found **39 day files through 13 October**. Local quantitative results below use the 37-file checkout; no pull, rebase or history update was performed.
- Live workflow [38595325114](https://github.com/Stranden1/weather-forecast-verification/actions/runs/38595325114) collected, persisted and deployed successfully on 14 October. Public [health](https://stranden1.github.io/weather-forecast-verification/data/health.json) at 16:10 UTC reported collection at 16:07:50 UTC (18:07:50 Oslo), all four source groups healthy, 18 runs in 48 hours against 16 expected. Nearby dispatches occurred every 30 minutes; a scheduled fallback also ran. This is evidence of recent operation, not an availability guarantee or an inspection of the external timer's credentials.
- Read-only live probes: Frost metadata and seven days of MSLP; one complete Yr forecast for Trondheim; one two-model Open-Meteo response; one historical Open-Meteo run; 12 hours × 49 stations from one historical WeatherNext initialization. Results are summarized here; production collectors were never invoked.

## 2. Current architecture and retention audit

```text
Yr complete JSON ───────────────┐
WeatherNext EE point samples ───┼─> horizon-filtered pending rows ─┐
Open-Meteo IFS/AIFS hourly JSON ┘     encrypted state branch      │
Frost exact-hour observations ─────> recent observation state ────┤
                                                               v
                                  choose station/target/horizon row
                                  join observations and baseline
                                                               v
                             immutable encrypted history day + metadata
                                  push and verify remote bytes
                                                               v
                                prune confirmed pending targets
                                                               v
                            summaries / revisions / storm replays
                                      → static Pages site
```

`cloud/run.py` records one UTC `fetched` value **before** sequential Yr, WeatherNext, Open-Meteo and Frost collection. It calls `State.add_pending()` after each provider. The workflow uses an hourly `:23` trigger and external dispatches; `cloud/health.py` gates collection until 150 minutes after its last success. A “success” for this gate means at least one enabled source delivered rows, not all stations/providers succeeded. Jobs serialize under `concurrency: collect`, timeout 40 minutes, Python 3.12 on `ubuntu-latest`.

The live pipeline keeps lead windows ±3 hours around **6, 12, 24, 48, 72, 120, 168, 240 hours**, measured from collection start. `score_targets()` prefers rows with **both Yr and WeatherNext temperature**, then closest lead, then later fetch. This temperature-based preference is not variable-specific. IFS/AIFS attach to the selected Yr/WeatherNext row; independent ECMWF-only rows do not survive this left join. Rain forecast fields are cleared beyond the first four horizons. Rows lacking every observation disappear, even when forecasts were successfully collected.

At UTC day-end +6 hours, a day can finalize with ≥80% of configured station-hours having **any** finite temperature/wind/rain observation. It waits up to day-end +72 hours otherwise. This is not an 80% completeness guarantee for each variable or station. Sidecars record expected stations, coverage, preparation time and ciphertext hash. Pending rows are pruned only after exact remote publication confirmation. Frost refetch spans five calendar days; observation state retains 15 days, extended if necessary for pending baselines. Run diagnostics retain 120 records. State is replaced using a lease; it is working memory, not a durable snapshot archive.

`cloud/store.py` serializes numeric CSV values to **three decimals**, then gzip and Fernet. The precision discarded at this point cannot be recreated from scored history. History stores forecast values as well as observations, not just error totals. Summary JSON is rebuildable output, not a substitute for those rows.

### Retention gap matrix

“Permanent” below means the selected scored row, not every API response. R = normally recoverable from a provider archive for supported periods; C = conditional reconstruction, not an exact operational replay; N = no reliable recovery path established.

| Provider / variable or record | API offers / actual request | Temporary retention | Permanent retention | Discarded and future consequence | Recovery |
|---|---|---|---|---|---|
| Yr temperature, wind | Complete point response, full timeline, central value and p10/p90; lat/lon rounded to four decimals, no explicit station altitude sent | Only horizon-window instants | Selected central/p10/p90, update time | Other lead hours and delivery revisions; no full issued trajectory or reliable daily extrema | **N** for exact Locationforecast response. Historical model grids are not the identical postprocessed product |
| Yr precipitation | Response contains available 1h/6h/12h products, bounds/probabilities | Only `next_1_hours` amount/min/max/probability; target shifted to interval end | Those fields at h=6/12/24/48 only | 6h/12h probabilities, amounts, interval identity outside hourly product, unselected revisions; long-range precipitation experiments | **N** for exact delivered products |
| Yr MSLP, dew point/RH, cloud/layers/fog, gusts/direction, period temperature extrema, symbols | Already delivered by `complete`, subject to location/range availability | Not extracted | Nothing | Historical predictor studies and new-variable verification against Yr cannot be recreated from history | **N** for exact delivered values |
| WeatherNext temperature | 0.05° station head, six statistics; request mean/p10/p50/p90 | Selected leads with initialization and sampling label | Same four selected statistics | p25/p75, omitted hours, run continuity, original precision | **R/C**: historical EE sampling demonstrated; exact original asset/sampling/version and receipt evidence may be unavailable |
| WeatherNext wind | 0.1° speed, six statistics; request mean/p10/p50/p90 | Same | Same | Other hours/statistics and u/v; directional and event trajectories | **R/C** |
| WeatherNext precipitation | Three distinct products available; request model-native `total_precipitation_1hr`, mean/p50/p90 | Selected leads, including long leads | Selected short-horizon mean/p50/p90 | Long rain leads; p10/p25/p75; IMERG/experimental rain comparisons | **R/C**; alternative products are different predictands, never silently substituted |
| WeatherNext MSLP, dew point, clouds | Available bands, not currently requested | None | None | Missing predictors now; means/quantiles alone also lack member trajectories | **R/C** from retained provider assets; no indefinite retention promise established |
| IFS and AIFS t/w/p | `/v1/ecmwf`, explicit two models, 11 days, hourly output, station elevations, m/s; two batches of ≤25 stations | Windowed hourly service output plus separately fetched latest initialization metadata | Selected same-fetch values and initialization; rain only short horizons | Rest of response; exact service version, interpolation and model-cycle mixture; all ECMWF-only candidates | **R/C**: individual historical run endpoint tested; exact previous seamless API response remains uncertain |
| IFS/AIFS pressure, dew/RH, cloud, gust/snow fields | Not requested in production; probe found pressure/dew/RH/cloud for both, IFS gusts, no AIFS gusts | None | None | No existing all-provider predictor cohort | **R/C** for archived runs/fields, not necessarily identical historical service processing |
| Frost temperature/wind/hourly rain | Requests default levels/offsets, qualities 0–4; main series and exact-hour timestamps | Latest non-null delivery wins; recent rolling window | Observation on selected forecast targets plus naive baseline values | Unmatched observations, previous versions, quality codes, sensor/level/time-resolution metadata, receipt timestamps | **R** for currently archived observations; **N/C** for first-delivered versions and operational availability |
| Frost new variables/subhourly/extrema | Available by station/element; not requested in production | None | None | Not present in history; observations can be joined later where provider retains them | Usually **R**, after station/series/period/QC validation; no promise that every element exists |
| Forecast/observation provenance | HTTP headers, response geometry, asset IDs, ingestion metadata, quality flags often available | Only provider/station/job-start/issued/target/rounded lead and WN sampling | Subset of these plus coverage sidecars | Actual receipt chronology, source grid and station versions, rejection reasons | **N** for actual receipt; **C** for source metadata recoverable later |

The local database's complete runs, extra WeatherNext statistics/pressure/u-v, and associated local retrieval history are lost as project records. Portions of their *values* can be re-sampled from upstream archives. Do not describe that as recovery of the database, its revision history or its original operational availability.

### Six different clocks

| Meaning | Existing field / problem | Archive rule |
|---|---|---|
| Model initialization | `wn_issued` is initialization; IFS/AIFS `issued` is a separately observed latest-model time | Store `model_init_at`, product/cycle/version; nullable when not supplied |
| Product update/publication | Yr `issued_at` is `meta.updated_at`, not initialization; HTTP modification can differ | Preserve `product_updated_at`, HTTP dates and source-specific publication evidence separately |
| Provider availability | WN `ingestion_time_utc` is available but dropped; Open-Meteo has availability/modification metadata | Preserve original value, units, scope and parsed timestamp; publication can be per asset, not one time per run |
| Actual retrieval | Current `fetched_at` is job start, before requests finish | Keep job start plus request start and response receipt per response/EE chunk; never rewrite old fields |
| Forecast target / interval | Instant target, or rain interval end; native interval otherwise implicit | Store valid time and explicit interval start/end/operator; target minus init is model lead |
| Observation time / receipt | `referenceTime` survives as target; delivery time does not | Retain reference time, time offset, duration, observation receipt and revision identity; target minus response receipt is operational lead |

A forecast is eligible operationally only if its actual receipt precedes the verified instant or **interval start**. The current job-start convention cannot prove this for every individual response; report it as a legacy limitation. Yr cannot supply a truly coherent single numerical-model run through Locationforecast: one response is a coherent **delivered product snapshot**, blending model domains, postprocessing and forecast ranges. A list of station responses is also acquired over a time span, not simultaneously.

## 3. Provider capabilities and what “continuous” means

### Yr / MET

Preserve the complete response unchanged, including geometry/altitude, units, all timeseries members and overlapping period products. The Trondheim probe returned **87 instants**, **56 one-hour**, **81 six-hour** and **75 twelve-hour** objects; these overlap and must not be summed together. It contained pressure, dew point, humidity, cloud layers, gusts and temperature quantiles. Short/medium-range boundary changes with issuance; do not hardcode “60 hourly steps”. Nordic short-range forecasts use MEPS and postprocessing; longer ranges incorporate ECMWF. See [MET data model](https://docs.api.met.no/doc/locationforecast/datamodel.html).

`updated_at` describes product updates, while native time spacing and `next_N_hours` describe physical support. In the probe, product update was 15:29:28 UTC, HTTP Last-Modified 16:07:56, and server Date 16:29:04. None should be relabelled model initialization. Preserve all three. See [point JSON definitions](https://docs.api.met.no/doc/ForecastJSON.html).

MET model archives can support separate raw-model experiments, but reproducing a historical point product requires its contemporary postprocessing, model selection, geometry and update state. The [Locationforecast FAQ](https://docs.api.met.no/doc/locationforecast/FAQ.html) describes differing source products. Yr's 21-day/subseasonal products are separate from this 10-day endpoint; defer them rather than silently expanding scope. Their probability definitions must not be borrowed for hourly Locationforecast.

### WeatherNext 3

**Six-hourly initialization is not six-hourly output.** Both interim and synoptic surface runs have native **hourly** forecast steps. Interim initializations cover 48 hours; 00/06/12/18 UTC cycles cover 360 hours. Current cloud selection switches initialization within a snapshot. For the research archive, select one synoptic initialization and retain every step 1–264; this covers approximately ten days after delivery with a latency margin. Retaining 264 instead of 360 explicitly defers day-12–15 research. See [model specifications](https://developers.google.com/weathernext/guides/models).

Keep product names exact: station-head temperature/dew point on 0.05° and gridded wind/rain/MSLP/cloud on 0.1°. EE exposes mean/p10/p25/p50/p75/p90, not individual members. Capture initialization, valid time, forecast hour, asset ID and `ingestion_time_utc`, plus grid projection and sampling policy. [EE catalog](https://developers.google.com/earth-engine/datasets/catalog/projects_gcp-public-data-weathernext_assets_weathernext_3_0_0_0p1deg).

Backfill was demonstrated for `2026-09-15T06:00:00Z`, hours 1–12, both collections, all 49 stations. New pressure/dew/cloud fields were finite in the sampled batch. This is strong evidence that these omitted fields are recoverable for that run, not a completeness audit of all historical cycles. Do not backdate retrieval when backfilling. EE's documented ingestion field is source availability evidence; capture it before assets or metadata can change.

Target EE delivery for 00/12 UTC synoptic runs is approximately 08:10/20:10 UTC; interim runs target initialization +7h25. These are estimates with variable delay, not evidence of availability. [Dissemination schedule](https://developers.google.com/weathernext/guides/dissemination).

### ECMWF through Open-Meteo

Current IFS is `ecmwf_ifs` (9 km HRES); AIFS is `ecmwf_aifs025_single` (0.25°). The service emits hourly values. IFS input spacing changes from hourly to three-hourly after 90 h and six-hourly after 144 h; AIFS is six-hourly. **Retain the received hourly values as service output, with interpolation flags; never claim they are independent native hourly predictions.** Temperature is height-adjusted by the service. The returned coordinate can differ from the requested station. [ECMWF API](https://open-meteo.com/en/docs/ecmwf-api).

The normal forecast endpoint and separately queried latest-model metadata do not establish that every returned value belongs to that initialization. Preserve that response as `coherence=service_snapshot_unverified`. An additional run-pinned product can use the [Single Runs API](https://open-meteo.com/en/docs/single-runs-api): a read-only request for `run=2026-10-12T00:00`, both current model IDs, returned 264 temperature/MSLP values per model. General historical coverage is documented; only that sample was tested here. Require repeated-cycle and horizon tests before treating the new adapter as validated.

Native source preservation is an explicit limitation: hourly service responses cannot recover exact original GRIB accumulations, grid values or spatial interpolation. Store them losslessly at **provider response resolution**, plus known underlying cadence and `native_value_unverified`. For truly native research, add separate run-pinned ECMWF GRIB point extraction later, preserving units, grid, step type and start/end steps. Open-data IFS is 0.25°, a different distribution from the current 9 km product; label it separately. ECMWF's own public endpoint retains only its most recent 12 runs, so it is not a long-term backup. [ECMWF Open Data](https://www.ecmwf.int/en/forecasts/datasets/open-data).

Do not confuse [Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) (stitched initial portions of successive forecasts), reanalysis, fixed previous-run offsets and a full archived initialization. Only the last can support a coherent run experiment. None recreates our original retrieval time.

## 4. Once versus twice daily

All options keep the existing scoring pipeline unchanged. B and C add an independent archive.

| Property | A: existing horizon storage | B: one full snapshot/day | C: two full snapshots/day — recommended |
|---|---|---|---|
| Timing | About 8 collections/day, selected rows retained | First due collection after 08:30 UTC | First due collection after 08:30 and 20:30 UTC |
| Run target | Latest short/long mixture | WN 00 UTC synoptic | WN 00 and 12 UTC synoptic |
| Trajectory | Sparse per individual fetch; some targets covered across successive fetches | One continuous delivered product/run | Two continuous products/runs |
| Daily accuracy | Rolling-horizon hourly errors; not a fixed daily forecast | Fixed morning decision product | Morning/evening decisions and overnight changes |
| Revisions | Selected unequal horizon steps already supported | Roughly 24h transitions | Roughly 12h transitions; better onset/track-change chronology |
| Events | Existing observed-event replays | One pre-event snapshot may be stale | Better chance of retaining the last substantial pre-event update |
| Sampling bias | Current horizon/provider selection | One cycle and time-of-day | Two opposite cycles; still not all cycles |
| Failure tolerance | Missed forecast cannot be recollected operationally | Missed slot can remove the day's only full capture | Another scheduled opportunity, not independent infrastructure |
| Cost | Existing budget | About half C | See measured estimates below |

Twice daily materially improves revision and overnight-event studies, but **does not double independent sample size** and cannot resolve every three-hour forecast change. Neither cadence retains all hourly WeatherNext runs. Daily scores should use a predeclared morning or evening decision cohort, not pick whichever snapshot later scored best. Compare fixed decision time separately from fixed initialization: they answer different questions.

Proposed slot semantics: use existing due collections; do not change cron/timer cadence. An 08:30 slot accepts the first eligible collection before 13:00 UTC; a 20:30 slot before 01:00 next day. Bind WN to the named 00/12 cycle, not whichever later cycle scores best. Select and record what is available at actual receipt; late/missing subproducts get explicit coverage entries. A late backfill can fill a separate retrospective object but never masquerade as on-time capture. Store `slot_date`, nominal cutoff, actual receipt and delay. An outage beyond the window creates a missing-slot record. Allow no error-based or event-based capture selection.

For WN, archive hours 1–264 of the fixed initialization, including early hours already past at retrieval; mark those ineligible for operational scoring. If the short-range private viewer later needs the freshest interim run as well, add a separately labelled 48h interim object. It adds about 48/264 = 18% to WN sample volume per slot and is **not** included in the recommended minimum. Keep current short-range scoring unchanged.

## 5. Proposed archive, schema and sizing

### Capture contract

1. **Yr:** complete raw response per station, all delivered periods and fields, plus sanitized request/response metadata. This is already transferred by production and costs no extra forecast request when the sink shares that response. Keeping the small whole response is safer and simpler than repeatedly expanding a field whitelist.
2. **WN:** 49 stations × 264 native hourly steps, one initialization per slot. Five variables × six statistics: station-head temperature, station-head dew point, 10m wind speed, native hourly precipitation and MSLP. Add total/low cloud **means** as explanatory predictors: **32 scalar bands**. Cloud quantiles, high/mid cloud, alternative rain products, u/v, full members and days 12–15 are explicit deferred additions; upstream backfill remains conditional. Preserve every returned quantile of the five verification variables.
3. **IFS/AIFS:** t/w/p, MSLP, dew point, RH, total/low cloud; retain full 11-day service responses and model metadata. Gust/snow probe support does not require adding them to routine capture yet. A run-pinned companion is preferred for coherence once validated; retain its identity separately from any production-service response. Never replace historical service forecasts with retrospectively improved processing.
4. **All collection attempts:** small permanent acquisition manifests, including non-archive slots, provider latency/status, station failures and selection reasons. This captures ephemeral operational evidence at little cost without keeping every trajectory.
5. **Observations:** an append-only daily observation-vintage sidecar. Save the exact delivered t/w/p plus MSLP and, after metadata validation, humidity/dew point on supported members of the same network; retain quality/series/height/interval and receipt. Save first versions and changes, not all identical five-day refetches. An independent latest-QC analysis view may be rebuilt later. Do not change the immutable scored observations.

Forecast collection uses the same 49-station network throughout. Pressure verification may use a declared subset; that does not create a different WeatherNext station network. Snapshot station metadata and `wn_heights.json`, including effective dates. The existing `site_group` is unreliable for some offshore stations; use reviewed classifications with provenance, not its label alone.

### Physical format and logical schema (version 1)

Prefer gzip-compressed UTF-8 JSON envelopes with arrays of values, then Fernet encryption, using existing cryptography dependencies. Keep raw Yr/Open-Meteo response content in the envelope, and compact named-band arrays for EE samples. JSON numeric round trips must preserve returned precision; do **not** reuse `float_format="%.3f"`. Preserve original values/units; normalized analysis tables are derived, versioned outputs. Lossless compression matters more than CSV versus Parquet at this scale; Parquet can be evaluated later without replacing source objects.

| Entity | Required fields / meaning |
|---|---|
| Envelope | `schema_version`, `archive_id`, `slot_date`, `slot`, `job_id`, collector Git revision, creation time, key ID, acquisition policy version |
| Request | provider, exact endpoint/product/model/collection, sanitized query, request ID, request-start/response-received timestamps, response status, permitted caching headers; **no authorization, user contact or tokens** |
| Run evidence | `model_init_at` nullable, `product_updated_at` nullable, `published_at` nullable, availability evidence type/raw value/unit, product/model version, asset IDs, source metadata before/after retrieval, `coherence` classification |
| Network | station ID, requested coordinates/elevation, source-returned geometry, active membership, station metadata version/effective dates, classification/height source, measurement metadata references |
| Sampling | native grid/projection/transform, source/returned cell coordinates when known, requested coordinate, spatial interpolation, EE scale/tileScale, elevation adjustment, model-orography source and whether it is an estimate |
| Forecast datum | variable and native field name, statistic or quantile, native unit/value, target instant or interval start/end, aggregation operator, model lead, operational lead, supplied cadence, underlying native cadence, derivation/interpolation/missing/QC flags |
| Observation datum | full source ID, element, reference time, offset, resolution, level/height/unit, series ID, quality code/flags, original value, receipt time, revision/content ID |
| Coverage | expected and received stations/steps/fields per product, missing reasons, unavailable run/field, conflict records, deadline/late flags; no invented zero values |
| Manifest | immutable object IDs, byte lengths, ciphertext SHA-256, schema/key IDs, safe counts; final completion manifest references every successful component |

Unknown values remain null with a reason; do not turn Yr update time into an initialization, static DEM into known model orography, or “now” into provider publication. Bilinear interpolation of marginal quantiles is itself a derived point product, not member-wise interpolation followed by an exact quantile calculation. Retain the method so later work can distinguish it.

Example object layout (proposed, **not created**):

```text
forecast/v1/2026/10/14/am/<capture-id>/yr/<station-id>.json.gz.fernet
forecast/v1/2026/10/14/am/<capture-id>/wn/<init>/<collection>-h001-012.json.gz.fernet
forecast/v1/2026/10/14/am/<capture-id>/openmeteo/<model>/<batch-id>.json.gz.fernet
forecast/v1/2026/10/14/am/<capture-id>/manifest.json.fernet
observations/v1/2026/10/14/<receipt-batch-id>.json.gz.fernet
network/v1/<metadata-version>.json.gz.fernet
```

Use create-if-absent writes and verified readback. A retry of the **same acquired payload** reuses the persisted object bytes/ID; a fresh response gets a new acquisition ID, even if its values match. Fernet produces different ciphertext on repeated encryption, so ciphertext equality is not semantic deduplication. Compare an internal plaintext digest under encryption, never publish future-value digests as a substitute for confidential storage. Conflicting content under an existing immutable ID is a hard failure. Partial manifests and later completion manifests are new objects; never overwrite a finalized snapshot to “repair” it. The analytical slot selection remains fixed and auditable.

**Retry durability is an activation prerequisite.** A directory on an Actions runner disappears with the runner. Current `cloud/persistence.py:publish_state()` commits only `pending.csv.gz`, `obs.csv.gz` and `meta.json`; placing a spool beside them will not preserve it. Before cloud activation, implement either a second durable encrypted destination or an explicitly validated, bounded encrypted retry-file allowlist in state publication/restore. The latter would be an additive persistence change requiring its own failure tests and approval, with no alteration of existing pending/history data. Never evict unconfirmed payloads silently when the spool reaches its limit: report lost capture opportunities separately, preserve already staged payloads, and keep the existing scoring pipeline operating. The local M1 writer alone is not a production-durable spool.

### Size estimates: measured anchors and explicit assumptions

All MB/GB are decimal. Measurements used `.venv`, in-memory compression, no full project backup or whole-project hashing.

| Anchor | Uncompressed | Gzip | Notes |
|---|---:|---:|---|
| Current scored day, mean of latest seven local days | 2.405 MB | 0.478 MB | Actual encrypted mean 0.637 MB/day |
| One complete Yr response | 92,735 B | 6,955 B | Trondheim, 14 October; ×49 ≈4.54 MB / 0.341 MB per slot |
| One two-model Open-Meteo response | 29,951 B | 6,661 B | 264 hours; ten requested fields including gust/snow; ×49 ≈1.47 MB / 0.326 MB; conservative proxy for eight routine fields |
| WN 12h ×49, 28 bands | 312,005 B | 122,287 B | Historical 15 September run; compact arrays, all sampled values finite |
| WN recommended 264h ×49, 32 bands | ≈7.84 MB | ≈3.07 MB | Extrapolation: 22 chunks × measured bytes ×32/28; new p25/p75 pressure/dew point assumed similar entropy |

One expanded snapshot is approximately **14 MB raw, 3.8 MB compressed, 5 MB encrypted**, including a metadata allowance. Allow **4–7 MB encrypted per snapshot** for weather-dependent compression, metadata and run-pinned ECMWF companion responses. This is a sample-based estimate, not a full archive benchmark. Fernet's base64 wrapping adds roughly one third after compression plus small per-object overhead; encrypt **after** compression. Fragment size, dictionaries and repeated metadata matter.

| Growth | A: current permanent history | B: additional once-daily archive | C: additional twice-daily archive |
|---|---:|---:|---:|
| Uncompressed/day | ≈2.4 MB | ≈14 MB (12–20) | ≈28 MB (24–40) |
| Gzip/day | ≈0.48 MB | ≈3.8 MB (3–5.25) | ≈7.6 MB (6–10.5) |
| Encrypted/day | ≈0.64 MB | ≈5 MB (4–7) | ≈10 MB (8–14) |
| Encrypted/30 days | ≈19 MB | 120–210 MB | 240–420 MB |
| Encrypted/year | ≈0.23 GB | 1.46–2.56 GB | **2.92–5.11 GB** |

Observation/provenance allowance: start with **0.1 GB/year**, measure version churn and revise; not a guarantee for subhourly observation capture. The Yr-only first milestone is approximately **0.33 GB/year** for twice-daily payloads, plus metadata. Full members would multiply storage/workload substantially and are outside these figures.

### Requests, compute and scheduling overhead

| Work | A: current | B: incremental/day | C: incremental/day |
|---|---|---|---|
| Yr HTTP | 49 per collect, ≈392/day at 8 runs | **0** if reusing already fetched responses | **0** with same integration; standalone retry up to 49 per slot |
| Open-Meteo HTTP | 2 forecast batches +2 model metadata per collect, ≈32/day | 0 for expanded existing responses; up to 4 forecast requests for separate model/run-pinned companion | Up to 8 companion forecast requests; metadata read-before/after may add 4/day |
| Open-Meteo quota accounting | Multiple stations/models can be weighted calls; do not equate HTTP batches with quota units | Conservatively budget ~98 location/model units per new slot, plus variable/date multipliers | ~196/day extra before multipliers; verify current accounting during pilot |
| Frost HTTP | 4 per collect, ≈32/day, repeating five days | Add elements to validated batches or up to 2 new pressure/auxiliary batches per collect | Same as B: observation freshness is independent of snapshot cadence |
| EE reductions | At 48 selected hours: ≈8 sample requests/collect, 2 collections ×4 chunks; metadata probes extra | 44 sample requests for 264h across 2 collections; ≤44 extra conservatively | ≤88 extra/day; same-run overlap can reduce this, do not assume it |
| EE scalar samples | ≈49×48×11×8 =207,000/day for existing t/w/p statistics | 49×264×32 =413,952 | 827,904 |
| Actions elapsed | Observed latest job ≈190 s including all scoring/export/deploy | Budget +2–5 min/day | Budget +4–10 min/day, ≈2–5 runner-hours/month |

EE sample probe took 1.52 s for the 0.05° chunk and 3.51 s for the 0.1° chunk. Multiplying by 22 gives approximately 111 seconds of sample calls per slot before metadata, extra bands, retries, serialization and upload; this motivates the 2–5 minute allowance, not a measured full-run duration. Existing completeness checks query possible initializations and add RPCs. Avoid running full 360-hour completeness checks for a 264-hour archive when the shorter contract suffices. Do not silently weaken current scoring's separate run-selection rule.

Adding bands to existing collections generally increases returned values and server computation without adding a new collection scan, but can trigger memory splitting. Benchmark EE quota/workload and two consecutive archive slots before enabling integration. Bound archive work so the 40-minute production timeout retains substantial headroom; preserve scoring/state publication even if archive upload is unavailable. Missing archive pieces must trigger an explicit archive-health failure and durable encrypted retry spool, not block existing history pruning indefinitely. No paid-service cost estimate is claimed: storage provider, requests, egress and backup prices must be checked when chosen.

### Where to store it

Prefer a **private, versioned object-storage bucket with create-only collector rights**, and an independent backup destination with separate credentials. Keep source/schema/manifests or safe summaries in Git, not multi-GB/year ciphertext blobs. Ciphertext does not delta-compress usefully; clone and CI checkout costs grow with every committed object. A private Git repository is an acceptable short bridge at Yr-only scale, but does not solve long-term growth or independent recovery. Git LFS and expiring Actions artifacts are not a backup policy. Do not move or rewrite current `history/` as part of this proposal.

Use a separately escrowed archive key/key ID, leaving `WX_STATE_KEY` and existing ciphertext untouched. New keys require recoverable key mapping; rotation retains old decryptors. Versioning alone is insufficient if the same compromised credential can delete every version. Independent retention and restore evidence matter more than the vendor name.

## 6. MSLP feasibility and pilot network

### Physical comparability

MET exposes `air_pressure_at_sea_level` in hPa. WN provides `mean_sea_level_pressure` in Pa on the 0.1° grid with hourly steps; normalize by dividing by 100 only in derived analysis. The EE probe verified available pressure statistics. Both IFS/AIFS returned `pressure_msl` in hPa in the live service and historical-run probe. Native ECMWF parameter `msl` is available; preserve source units rather than assuming the API and GRIB match. The provider sources are linked in section 3.

Frost's live element metadata defines `air_pressure_at_sea_level` as pressure reduced using actual atmospheric conditions (QFF), and `surface_air_pressure` as pressure at station reference height (QFE). Both API units are **hPa**, despite CF reference units Pa. Surface-pressure metadata lists a default 2 m sensor level; this is not evidence that every sea-level reduction has a documented sensor height or algorithm. **Do not substitute QFE, QNH or a standard-atmosphere height correction for QFF.** Relevant endpoints: [element definitions](https://frost.met.no/elements/v0.jsonld?ids=air_pressure_at_sea_level,surface_air_pressure), [time series](https://frost.met.no/observations/availableTimeSeries/v0.jsonld), [observations](https://frost.met.no/observations/v0.jsonld); these may require the configured Frost client authentication.

Lower terrain sensitivity makes MSLP a useful complementary check on synoptic systems, pressure gradients and timing. It does **not** isolate dynamical model quality: mountain reductions depend on assumed column temperature, local station calibration remains relevant, and models share analyses/observations. Low-elevation errors and 3h/6h pressure-tendency errors are a stronger first test than an all-station pressure leaderboard. A sparse Norwegian network supports point-pressure/gradient diagnostics; detailed cyclone tracks require spatial fields or an independent event catalogue.

### Reproducible seven-day coverage check

Queried all 49 active IDs for `2026-10-07T00:00:00Z/2026-10-14T00:00:00Z`, treating the upper bound as exclusive in analysis. Metadata search used the same dates, default offsets and series 0. Observations requested default levels/offsets and qualities 0–4; analysis kept finite hPa values at exact UTC hours, offset PT0H, series 0. Identical station/hour values collapsed; disagreements were excluded. No interpolation or zero fill. Available resolutions included PT1M/PT10M/PT1H/PT3H. Returned qualifying observation entries had quality codes 0/1. Full physical comparability still requires metadata review; counts below are **data availability**, not certification of instruments.

**35 stations with MSLP; 5,558 unambiguous station-hours; 27 with ≥160/168; 25 with 168/168.** Land/offshore classification here uses station identity/county, checked against the known network, rather than the misleading generic `site_group` strings.

| Station | Area / setting | Elevation m | Unambiguous hours /168 | Conflicting hours |
|---|---|---:|---:|---:|
| SN10380 Røros lufthavn | Trøndelag, inland | 625 | 168 | 0 |
| SN18700 Oslo–Blindern | Oslo, urban | 94 | 168 | 0 |
| SN20949 Gina Krog | North Sea | 65 | 168 | 0 |
| SN20961 Alvheim | North Sea | 40 | 107 | 0 |
| SN25630 Geilo–Oldebråten | Buskerud, mountain | 772 | 168 | 0 |
| SN34130 Jomfruland | Telemark coast | 3 | 168 | 0 |
| SN44610 Kvitsøy–Nordbø | Rogaland coast | 21 | 168 | 0 |
| SN50540 Bergen–Florida | Vestland coast | 12 | 168 | 0 |
| SN53101 Vangsnes | Vestland fjord | 49 | 168 | 0 |
| SN57770 Ytterøyane fyr | Vestland coast | 26 | 168 | 0 |
| SN63420 Sunndalsøra III | Møre og Romsdal, fjord/valley | 6 | 168 | 0 |
| SN65940 Sula | Trøndelag coast | 5 | 168 | 0 |
| SN68860 Trondheim–Voll | Trøndelag | 127 | 168 | 0 |
| SN76909 Johan Castberg | Continental shelf | 53 | 167 | 0 |
| SN76922 Statfjord A | North Sea | 71 | 130 | 0 |
| SN76929 Yme | North Sea | 50 | 165 | 0 |
| SN76930 Norne | Norwegian Sea | 33 | 115 | 53 |
| SN76933 Ormen Lange | Norwegian Sea network category | 0 | 168 | 0 |
| SN76938 Ula | North Sea | 111 | 157 | 0 |
| SN76939 Valhall A | North Sea | 95 | 150 | 0 |
| SN76956 Goliat FPSO | Barents Sea | 46 | 146 | 22 |
| SN76957 Troll B | North Sea | unknown | 106 | 0 |
| SN76963 Kristinfeltet | Norwegian Sea | 45 | 168 | 0 |
| SN77040 Aasta Hansteen | Norwegian Sea | 64 | 115 | 53 |
| SN80102 Solvær III | Nordland coast | 10 | 168 | 0 |
| SN85890 Røst lufthavn | Nordland coast | 4 | 168 | 0 |
| SN86740 Bø i Vesterålen III | Nordland coast | 8 | 168 | 0 |
| SN87110 Andøya | Nordland coast | 10 | 168 | 0 |
| SN89940 Dividalen II | Troms inland | 204 | 168 | 0 |
| SN90450 Tromsø | Troms | 100 | 168 | 0 |
| SN93700 Kautokeino | Finnmark inland | 307 | 168 | 0 |
| SN96310 Mehamn lufthavn | Finnmark coast | 13 | 168 | 0 |
| SN97251 Karasjok–Markannjarga | Finnmark inland | 131 | 168 | 0 |
| SN98550 Vardø radio | Finnmark coast | 10 | 168 | 0 |
| SN99540 Nyrud | Finnmark inland | 56 | 168 | 0 |

No MSLP series/value returned for these 14 active IDs in this window: **SN1120, SN120, SN12590, SN13760, SN2970, SN33430, SN41825, SN60980, SN70850, SN76245, SN81790, SN84210, SN92895, SN94190**. Do not extrapolate that absence to every historical period. Surface-pressure metadata also covered 35 IDs, but station-pressure values were not separately audited.

The Norne/Goliat/Aasta conflicts involve coexisting **PT10M and PT3H series at source `:0`, timeSeriesId 0**. A follow-up 7 October query confirmed this metadata distinction. Do not average conflicting reports or pick a value because it favors a forecast; select a documented series policy after instrument/series investigation. Excluding them is conservative and can lower reported coverage.

**Pilot: eight stations**, all complete in the check and below 150 m: SN18700 Oslo, SN34130 Jomfruland, SN50540 Bergen, SN68860 Trondheim, SN85890 Røst, SN90450 Tromsø, SN97251 Karasjok, SN98550 Vardø. This spans southern urban/coastal, west coast, central, northern coast and northern inland settings. Keep high mountains and offshore as separately labelled exploratory extensions.

Pilot metrics: MAE and signed bias in hPa; RMSE as a secondary extreme-sensitive measure; tendency error `(forecast(T)-forecast(T−6h)) − (obs(T)-obs(T−6h))` in hPa/6h. Both forecast endpoints must come from one run/product snapshot and both observations from the agreed series. Compare all four products on AIFS-native six-hour target times first; pressure trough timing can be an exploratory event diagnostic. Preserve raw pressure for all stations so the subset can expand later without recapture.

## 7. Additional variables: scientific priority

Frost counts below are **metadata availability in the same seven-day window**, not a live-value coverage audit except for MSLP. Sources and sampling procedures are given above.

| Rank / candidate | Provider support and observation evidence | Comparability / useful science | Prospectively needed? / decision |
|---|---|---|---|
| 1. MSLP | All four; Frost 35 IDs, values verified | Larger-scale errors and tendencies; reduction/height caveats | Capture Yr now; WN/ECMWF backfill conditional. Implement eight-station pilot after archive validation |
| 2. Dew point and RH | Yr; WN station-head dew point; IFS/AIFS dew/RH live probe; Frost RH **49**, dew point **46** IDs | 2 m moisture, dewpoint depression, saturation and cold-night diagnosis; RH is temperature-dependent and bounded | Capture forecasts now. Prefer direct dew point; derived RH must name the formula. Do not compute ensemble mean RH by pretending mean temperature/dew point preserve nonlinear/member covariance |
| 3. Total/low cloud | Yr and WN; both ECMWF service products returned values; Frost total cloud **11** IDs in **octas**, irregular 10min/3h/6h schedules | Explanatory clear-night/inversion predictor first; visual sky cover, ceilometer estimates and model area fraction differ | Retain cheap forecast means now; direct leaderboard deferred. Keep observing method/height layers; 1 octa=12.5 percentage points only for ordinary 0–8 cover codes, not missing/obscured codes |
| 4. Gusts | Yr short range; IFS service present; AIFS probe all null; WN catalog has no gust field | Warning-relevant extremes, but gust ≠ 10-minute mean wind | Yr raw archive preserves existing gusts. Investigate matched intervals before new collection/scoring. Frost hourly maximum-gust metadata: **22** IDs |
| 5. Snow/phase | ECMWF service snowfall exists; Yr symbols give categorical phase context; WN surface catalog lacks a matching snowfall/depth field; Frost snow depth **10** IDs | Depth, fresh-snow depth, snow water equivalent and falling precipitation phase are different quantities | Defer leaderboard; retain incidental Yr phase symbols. Snow-depth observations can usually be backfilled. Temperature near zero plus rain is not proof of observed snow/freezing rain |
| Cross-cutting: complete daily summaries | Complete trajectories rather than another scalar API variable | Daily sampled high/low, freezing hours, frost nights, rain totals and event timing | Highest urgency is trajectory capture. Existing rolling-horizon rows are insufficient for a coherent fixed daily forecast |

Cloud hypotheses should compare clear/cloudy **forecast** strata for operational use and independently observed cloud strata for explanatory validation. Snow cover, wind, humidity, elevation and season confound a simple cloud-versus-temperature relationship. Forecast-cloud correlation with temperature error does not establish that cloud error caused it.

For gusts, the ECMWF service documentation describes a preceding **three-hour** maximum of three-second gusts; hourly API timestamps do not make it a preceding-hour maximum. Yr's period support also needs confirmation. Aggregate complete hourly Frost maxima to the matching three-hour interval where appropriate; do not compare point gusts with differing windows. Predeclare exploratory thresholds such as ≥15, ≥20 and ≥25 m/s with counts; these are research thresholds, not universal warning criteria. WeatherNext wind-speed quantiles cannot be relabelled gusts.

Snowfall output in centimetres may be derived from water equivalent with a fixed ratio; it is not observed snow-depth change after settling, melt and drifting. Phase verification needs an appropriate present-weather/precipitation-type observation and compatible intervals, not just `surface_snow_thickness`.

Daily summaries must declare UTC versus Europe/Oslo boundaries, including 23/25-hour DST days. Count complete physical intervals; never fill missing hours with zero. A sum of mean hourly rain can estimate a mean total for a coherent ensemble, but a sum of medians/quantiles is **not** the median/quantile of that total. Hourly-sampled extrema are not true daily extrema. Six-hourly trajectories cannot resolve hours below freezing or true hourly onset. Retain Yr's supplied period extrema as distinct products. Existing observed daily totals/events can be reused only where every required observation exists; future fixed-run daily accuracy requires the new archive.

## 8. Analyses already possible

### Inventory: extend these; do not reimplement them

- `cloud/summarize.py`: paired temperature/wind/rain MAE/bias; WeatherNext mean/median; naive baseline; height adjustment; fixed **50/50 temperature and wind blend**; day-block bootstrap; p10–p90 coverage, width and pinball; rain wet-hour MAE/POD/FAR/CSI and weather-condition groups.
- `cloud/replay.py`: revisions across selected horizons, movement toward observations, flip-flops, observed-event selection and storm replays. These are not full hourly revision histories. Unknown issue times currently count as changed; a stricter future revision analysis must disclose/exclude unknown identity.
- `cloud/views.py`/`cloud/monthly.py`: period/land-offshore views and monthly summaries; `site/` already has event/replay/calibration UI. The private viewer already displays forecast disagreement.
- Legacy local code has run-specific 6h/24h precipitation scoring and disagreement features. The lost SQLite inputs prevent treating those as currently operational cloud capabilities. Do not promise to recover them by simply exposing the old UI.
- **Yr probability reliability/Brier scoring is not implemented in cloud.** Retaining `p_prob` is not the same as verifying it. Current pinball substitutes Yr's central value for p50; that assumption is not proof of a true median. Rain `p_min/p_max` are not automatically p10/p90.

### Three immediately useful, read-only studies

1. **Four-product temperature/wind comparison:** filter the intersection of finite observation + Yr + WN + IFS + AIFS on the existing station/target/horizon/fetch row. The local audit found **57,018 temperature rows (50 historical stations), 49,314 wind rows (44), and 31,686 rain rows (29)** across **15 days, 27 September–11 October**. These counts include repeated targets across horizons; they are not independent samples. Use the retained historical network, disclose retired stations, and provide a fixed-current-network sensitivity view. Compare actual lead distributions, not just horizon names. Rain is exploratory because AIFS's distributed hourly amounts are not native hourly forecasts; native-aligned accumulations are preferable once available.
2. **Disagreement as an error predictor:** predeclare absolute Yr–WN differences (and four-model spread), fixed physical bins or training-period quantiles; then compare future absolute errors and which provider performs better within those bins. Select cases from predictions, never errors. Use a later held-out time block for bin/threshold assessment. Report whether disagreement adds value beyond lead, season, location and spread; the current private disagreement list is not this outcome study.
3. **Conditional calibration / geography audit:** reuse existing temperature/wind quantiles and errors to examine range coverage, width, per-quantile loss, day/night and elevation/land-offshore differences. Match both providers on a common quantile-valid cohort; current displayed coverage can use different provider denominators even though pinball uses a common cohort. Stratify WN sampling method and do not fit a universal lapse correction to this same evaluation period.

These analyses can run immediately without new data collection; their conclusions remain descriptive with the short available history. Four products are not four independent experiments in “AI versus physics”: Yr blends/postprocesses models and observations, WN uses station training and ECMWF analysis, AIFS shares ECMWF infrastructure/inputs, and Open-Meteo modifies service output. Treat them as forecast **products** with different resolutions, cycles and processing.

### Probability work: capture is ready; event definition is not

The local archive has **68,459 nonmissing Yr `p_prob` rows**, values 0–100. Code establishes that these came from `next_1_hours` and align with `[target−1h,target)`. However, the primary Locationforecast documentation examined describes chance of precipitation without establishing the exact amount threshold and strict/inclusive comparison for this product/period. The 21-day/subseasonal product documents a different daily threshold; it is not evidence for hourly probabilities. **Do not silently use the site's >0.1 mm wet-hour definition.** Obtain a product-specific authoritative definition (including changes over time); do not send unsolicited correspondence as part of this task.

Once verified, compute Brier score `mean((p/100 − event)^2)`, fixed reliability bins with sample/event counts and uncertainty, sharpness and Brier skill against a training-only climatology on the same cohort. Keep interval-specific thresholds and definitions versioned. Use a few bins at first, merge or suppress sparsely populated bins, and test calibration by horizon before finer season/condition splits. Mean precipitation thresholding is not a probability. Quantiles alone do not identify exact threshold probabilities, full CRPS, member rank histograms or joint daily event probabilities. Per-quantile pinball at known p10/p90 avoids pretending Yr's central value is a verified p50.

### Dependence and history length

Keep every station/target together across horizons, providers and observation vintages. Use day or preferably multi-day weather-system blocks when estimating uncertainty; the existing one-day bootstrap is a useful start but does not remove serial dependence across storm days. Use station/region resampling or held-out regions for spatial generalization, and avoid treating thousands of station-hours as thousands of independent experiments. Predeclare comparisons and report multiple-comparison/exploratory status. Coast/inland and mountain/valley labels require a reviewed metadata table; elevation alone is not valley exposure.

Several weeks suffice to debug cohorts and describe individual events. Several months and winter are needed for stable condition comparisons; hold at least a full seasonal cycle before broad annual claims. Rare extremes may require years. Seven days, the UI's current minimum for a verdict, is not a scientific sample-size guarantee for new subgroups.

## 9. MOS and corrected-forecast experiment

Do not train during this task. The first experiment should target temperature; wind follows with nonnegative outputs, rain later with occurrence/amount separation. Preserve **inputs as available at prediction time**, not a subsequently reconstructed best forecast.

### Baselines and ordered model ladder

1. Each uncorrected provider, WN mean and median where appropriate, current fixed 50/50 Yr–WN blend, and the existing naive same-hour observation baseline on identical eligible rows. The fixed blend already exists and needs no training.
2. Global/horizon historical bias correction using only previously available observations. For MAE, median residual correction is a sensible benchmark; mean residual correction targets mean bias/RMSE. Name which was used.
3. Station/lead correction with shrinkage toward global or region effects and a minimum number of independent training days; unseen/poorly covered stations fall back to the global correction.
4. Regularized nonnegative blending weights summing to one; learn only within training folds. Compare with fixed 50/50 and the best provider selected **on training data**, not the eventual test winner.
5. Nonlinear models only if the simpler methods show repeatable out-of-sample benefit and enough seasonal coverage exists.

Preserve provider raw/normalized values, marginal quantiles, run/response identity, all clocks, station coordinates/version/elevation and model-height estimate/version, lead and actual forecast age, local/UTC hour and season, sampling/postprocessing flags, pressure/dew/cloud predictors, missingness/rejection flags and observation vintage/receipt. Training labels may use a declared final-QC observation version, but online predictors and corrections must respect its actual availability. For old history the naive baseline's observation time precedes collection; **its delivery time is unknown**, so label it an approximate operational baseline rather than claiming full availability proof.

### Leakage controls and generalization test

- Freeze a forecast decision record at issuance and evaluate only after the target interval finishes. Never replace it with a later revision, even if provider initialization is the same.
- Use rolling-origin training/validation/test blocks; no random row split. At each cutoff, every training target must have ended and its observation have been received. Future target rows generated by earlier runs are not training labels yet.
- Keep every occurrence of a target/interval, including all horizons/providers and overlapping daily accumulations, in one side of each split. Use a conservative purge of the maximum target span (up to about 11 days for this archive) when splitting by issue date, and an additional storm-block gap where feasible. Do not rely on a nominal gap without checking interval intersections.
- Fit bias factors, weights, imputation, scaling, climatology, bin boundaries and feature selection inside the training fold. Historical whole-period corrections are not valid out-of-sample predictors.
- Start with expanding training windows and a locked final month once enough history exists. Later test winter/summer and rolling seasons; leave entire stations or regions out to measure transferability. Report station-specific performance separately from unseen-location performance.
- Log training end time, observation-availability cutoff, model/config version, included data IDs and every out-of-sample prediction. Later retraining creates a new version, never rewrites old experimental predictions.
- Judge paired MAE/bias/RMSE changes and event/calibration side effects on exactly the same rows. Use weather-block uncertainty and station-level distributions, not just pooled improvement. A model that improves the average but worsens cold nights or a region needs that disclosed.

Existing history supports initial temperature/wind experiments at saved horizons, with legacy provenance limitations. It cannot provide coherent daily labels/predictors or lost Yr pressure/cloud/dew features retrospectively. No model should be trained yet merely because row count looks large.

## 10. Operational reliability, backup and scientific integrity

These are separate from feature recommendations and require explicit authorization before operational changes.

| Risk | Current evidence | Proposed action |
|---|---|---|
| History/key loss | Cloud history is sole retained project record; local decryption works; independent recovery unverified | Validate independent ciphertext **and key** recovery before expanding valuable retention |
| Missed snapshots | Healthy recent run, but dispatch success can be a gate skip | Monitor successful provider/station captures and slot manifests, not workflow green ticks alone |
| Partial Frost failures | Provider rows can be nonzero while a station/variable is absent | Add per-station/element expected cadence, latest observation and completeness; do not let aggregate ≥80% hide persistent outages |
| Model failures hidden by gate | Any enabled source with rows counts as success | Separate archive freshness and provider health from general job success; preserve healthy sources |
| Network drift | Wisting inactive; current 49 versus historical 50 | Version membership/metadata; freeze denominators for each target day and expose changing cohorts |
| Immutable observations | Later Frost corrections cannot update scored days | New QC/observation-vintage analysis dataset only; never rewrite `history/` |
| Ubuntu migration | Workflow uses `ubuntu-latest` | Observe tests and a real collecting/persisting/deploying run after migration; pin/change only with approval |
| External timer credential | Documented expiry 5 November 2026, 17:15 UTC /18:15 Oslo | Owner renews scoped repository-only token before expiry; verify a due collection and a gate skip; keep fallback |
| Repository growth | Current history ≈0.23 GB/year; expanded ciphertext several GB/year | Separate object archive; no Git rewrite/cleanup or migration of existing days in this task |
| WeatherNext publication | Existing future-value restriction; past-value project policy documented | New archive remains private/encrypted, never enters `site/` or Pages artifacts |

GitHub's [runner announcement](https://github.com/actions/runner-images/issues/14748) confirms rollout begins **19 October 2026**, with completion planned by **19 November**. This matches the operational deadline in the handoffs. `SETUP_CLOUD.md` records timer job **8590224**, every 30 minutes at :07/:37; its line saying recurring operation still needs verification is older than the current successful dispatch evidence. Token expiry is a documented project fact, not independently inspected secret/token state. A fallback on the same GitHub Actions infrastructure protects against timer failure, not a GitHub-wide outage. Do not reactivate the retired PC collector.

Google's [current model licensing description](https://developers.google.com/weathernext/guides/models#data-licensing-and-terms-of-use) distinguishes future/recent targets from targets at least one hour old. Preserve the project's target-time cutoff and required notices for any later authorized public derived output. This design neither expands public forecast publication nor cleans old plaintext Git objects; those remain separate decisions. Encryption does not erase previously published plaintext.

### Isolated backup-and-restore validation procedure (not executed here)

1. Inventory only indispensable objects: immutable encrypted `history/` days/sidecars, network and sampling metadata, schema/code revision, and optionally the latest encrypted working state plus future archive objects. No full project copy is needed.
2. Obtain an **existing independent backup**, or create an approved narrow encrypted data backup on a separate failure domain. Back up keys through a separate secure recovery channel. A clone and `.env` on this PC are not independent recovery.
3. On a disposable isolated directory or another machine, restore from that backup only. Do not access the live checkout's key or history to make a failed test pass. Supply the escrowed key through the normal secure mechanism; no printing, command-line literal key, report capture or plaintext artifact upload.
4. Verify the backup manifest's file list, ciphertext sizes/digests and authenticated decryption; parse gzip/schema. Check all copied day files for readable rows, expected dates, station coverage and known aggregate counts. Legacy days without sidecars need an explicit inventory, not fabricated old coverage.
5. Rebuild representative aggregates into a disposable private output directory with forecast-value publication disabled. Compare stored expected aggregates/counts at numerical tolerance appropriate to the source precision. Read-only export tests must not invoke collectors, `publish`, real remotes or scheduled tasks.
6. Exercise wrong/missing key, truncated file, missing day/sidecar and unknown schema failures. All must fail visibly without resetting an archive or pretending an empty state is valid. State-resume mechanics, if tested, use a temporary bare Git remote only.
7. Record a **nonsecret** recovery report: backup identity, backup date, verified key ID, object/day counts, restored target range, checks passed, failures and recovery duration. Restore success means the independent copy and independent key worked together. Protect/remove temporary plaintext deliberately after verification.
8. Proposed targets: immutable-data RPO ≤24h, working-state RPO one collection, RTO ≤1 day. Verify a small rotating sample monthly and a full archive restore quarterly/after key changes. Approve the schedule/storage before automating it; do not create reminders or jobs as part of this design.

## 11. Staged roadmap

Scores are 1–5: value/urgency higher is better/more urgent; complexity higher is harder. Costs are incremental and rough; rows overlap where the same archive supplies several features.

| Category / work | Value | Urgency | Complexity | Data/storage cost | Dependencies | Recoverability | Recommendation |
|---|---:|---:|---:|---|---|---|---|
| **A: Yr full responses twice daily** | 5 | 5 | 2 | ≈0.33 GB/year + metadata, no extra normal API call | Encrypted sink, slot policy, private destination | Exact product generally not recoverable | **Implement first**, after approval |
| A: acquisition manifests + network/sampling versions | 5 | 5 | 2 | Small; included in 0.1 GB/year allowance | Timestamp/identity schema | Receipt history irretrievable | Implement with first capture |
| A: independent archive/key recovery | 5 | 5 | 2 | Narrow duplicate datasets; no full project backup | Separate key escrow and backup | Irrecoverable if all keys/copies lost | Approve and verify immediately |
| A: coherent WN/ECMWF snapshots + pressure/dew/cloud | 5 | 4 | 3 | Brings total to ≈3–5 GB/year | First sink, run validation, EE benchmark | Values often backfillable; as-received provenance not | Implement next; two daily slots |
| A: observation vintages/QC metadata | 4 | 4 | 3 | Initial ≈0.1 GB/year total allowance; measure | Frost series policy, append-only identities | Final observations backfillable; old deliveries not | Implement alongside new-variable capture |
| **B: four-product temperature/wind** | 5 | 3 | 2 | No new collection | Shared cohort and interpolation disclosures | Existing history sufficient | Implement read-only analysis soon |
| B: disagreement versus future error | 4 | 3 | 2 | No new collection | Forecast-based bins, held-out period | Existing saved horizons sufficient | Implement; exploratory now |
| B: conditional quantile/geographic audit | 4 | 3 | 2 | No new collection | Correct cohorts, metadata categories | Existing t/w fields sufficient | Extend existing metrics |
| B: Yr probability reliability/Brier | 4 | 3 | 2 | No new collection for saved hourly cases | Authoritative threshold/interval/version | Saved p_prob sufficient once defined | **Investigate definition**, then implement |
| B: eight-station MSLP pilot | 4 | 4 | 3 | Marginal within archive | Series/height review, prospective Yr pressure | Frost/WN/ECMWF often recoverable, Yr missing | Implement after capture validation |
| B: daily fixed-decision summaries | 5 | 4 | 3 | No extra if archive exists | Complete intervals, DST and native-step policy | Past coherent Yr runs unavailable | Implement after enough new snapshots |
| B: per-station health + runner/token checks | 5 | 5 | 2 | Negligible data | Approved operational changes | Missed forecasts not always recoverable | Operational priority, separate approval |
| **C: dew point verification, cloud diagnosis** | 4 | 3 | 3 | Included forecast fields; observation audit | Complete metadata and seasonal cases | Observations often backfillable | Dew point first; cloud explanatory |
| C: MOS bias/shrinkage/learned weights | 5 | 2 | 3 | Small prediction/model logs | Time-ordered data and multiple seasons | Existing horizons support limited start | Defer training; preserve prerequisites |
| C: gust/phase/snow leaderboard | 3 | 2 | 4 | Small values, substantial compatibility work | Matching intervals/physical quantities | Partial provider archives | Investigate; defer scoring |
| C: native ECMWF extraction, WN alternative rain | 4 | 2 | 4 | Download/compute potentially much larger than point output | Exact source/product/archive access | Conditional; native recent GRIB has short retention | Targeted feasibility study, distinct products |
| C: full ensembles/nonlinear correction | 4 | 1 | 5 | Much larger compute/storage than summary bands | Demonstrated simpler-model benefit; member continuity | Provider archive access conditional | Defer |

## 12. Exact first implementation milestone

**Milestone M1: a disabled-by-default, independently encrypted Yr snapshot sidecar, two slots/day, plus all-run acquisition manifests and a local recovery test.** It should preserve today's hardest-to-recover data without changing scoring selection or requiring a new weather-model integration. No deployment is authorized by this plan.

### Files and responsibilities

| Proposed file/change | Contract |
|---|---|
| New `cloud/archive.py` | Pure versioned envelope creation, lossless raw-payload storage, compression/encryption, create-only writes and readback validation; separate from `State` and scored-day writer |
| New `cloud/archive_policy.py` | UTC slot assignment, deadlines, stable acquisition IDs, first-eligible selection, explicit missing/late/partial rules, no observation/error input |
| `cloud/yr.py` | Optional sink callback receiving raw response, sanitized headers/geometry and actual request/receipt timestamps **before** `extract()` discards data; disabled path preserves existing return signature and numerical output |
| `cloud/run.py` | Optional archive context and manifests; invoke current collectors/scorer unchanged; preserve successful raw acquisitions if archive persistence later fails |
| New `cloud/archive_storage.py` | Local private directory backend first; object-store adapter later with conditional creation, encrypted retry spool and separate archive health |
| Before activation: `cloud/persistence.py` or independent spool backend | Explicit durable retry mechanism; existing state publication ignores arbitrary added files. Validate bounded capacity, encryption and upload/restore failure handling before enabling capture |
| New `cloud/tests/test_archive.py`, `test_archive_policy.py` | Synthetic fixtures; no production network/state/keys. Test the contracts below |
| Later `cloud/weathernext.py`, `cloud/openmeteo.py` adapters | Fixed-cycle 264h capture, 32 bands, asset/metadata evidence, service versus run-pinned identity, shared active stations |
| Later `cloud/frost.py` observation adapter | Preserve raw quality/series metadata in sidecar; add validated pressure/dew fields without changing legacy observation/scoring columns |
| Later workflow/env configuration | Only after validated local and isolated live pilot plus owner approval; private destination/key configuration, no cron change required |

Do **not** extend `PENDING_COLUMNS`/`SCORED_COLUMNS` merely to carry archival data: that retains unnecessary coupling and still drops unselected forecasts. Do not change history serialization, migrate SQLite or alter current pressure-free scores. This is a companion archive, not a database migration.

### Incremental acceptance gates

1. Implement the local archive writer/policy and fixtures in the existing `.venv`; run focused archive tests. A round trip preserves original payload values, native 1h/6h periods, nulls and timestamps. No loss to three decimals. No unknown-schema silent fallback.
2. Add the disabled sink. Fixture collections with it disabled/enabled must produce identical pending rows and selected scores; new output goes only to the separate temporary archive root. Run the existing cloud suite via `.\.venv\Scripts\python.exe -m unittest discover -s cloud/tests`. No UI tests are needed until UI behavior changes.
3. Validate two explicit read-only acquisition pilots into an isolated encrypted location: 49-station full Yr snapshots, first-slot selection and retry behavior. Measure bytes/runtime and zero extra normal Yr requests. Freeze successful per-station responses; missing stations are reported, not silently replaced from a different nominal snapshot. Repeat receipt timestamps honestly on actual retries.
4. Verify independent readback with a **test key from its separate test escrow**, then perform the approved real-history recovery procedure separately. Local same-key roundtrip is not independent backup validation.
5. Present a concrete deployment diff, storage/key setup instructions and pilot evidence for approval. Only after approval enable the sink. Compare subsequent production scoring coverage and health; turning the feature off must stop new sidecar work without deleting any objects.

Required meaningful tests: slot boundary/cross-midnight/DST neutrality; missing/late provider; duplicate identical versus conflicting object; process interruption between chunk and final manifest; write/upload/readback failure and recoverable spool; wrong/missing key; corrupt gzip/token; no secrets in serialized headers; no future data in public exports; missing station/field remains missing; unchanged station network; exact rain interval boundaries and no double counting overlapping Yr 1h/6h/12h fields. For M2 add mixed-initialization rejection, delayed EE ingestion, per-chunk retrieval, all band units, incomplete 264h run, Open-Meteo metadata race and six-hour AIFS flags. For pressure add conflicting PT10M/PT3H observations, QFE exclusion, hPa/Pa conversion and complete tendency endpoints.

**Safe stopping point:** M1 can be validated and left disabled with no production changes. A later approved activation begins irreversible-value preservation. Coherent WN/ECMWF capture and MSLP scoring remain separate validated stages; do not leave an enabled half-configured archive or alter operational schedules to compensate for an unvalidated integration.

## 13. Audit completion / next-session handoff

Only this planning document was created. The existing modified files remain: `CHANGELOG.md`, `DECISIONS.md`, `NEXT_STEPS.md`, `PROJECT_STATUS.md`, `WORK_STATUS.md`, `site/app.js`, `site/index.html`, `site/style.css`, `tests/scorecard_ui_test.cjs`; existing untracked reviews `REVIEW_2026-10-11.md` and `REVIEW_2026-10-11_codex.md` remain. In accordance with this task's specific one-document request, no handoff rewrite was made over that work. No commit, push, deployment, schedule change, model training or backup operation occurred.

Open scientific checks are explicit: Locationforecast hourly probability threshold; pressure reduction/instrument metadata beyond the pilot availability check; native ECMWF provenance versus service output; full-network snapshot bytes/runtime; independent key-and-data restoration. These do not prevent approval of the narrow Yr capture milestone. The next implementation session should first recheck Git status and coordinate with the existing scorecard work, then implement only the approved stage.
