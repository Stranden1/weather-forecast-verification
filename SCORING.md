# Scoring audit and comparison rules

_Audited 2026-09-16; dashboard reads only, no schema or collector changes._

## Variables

| Variable | Yr/MET stored | WeatherNext stored | Frost stored | Dashboard scoring |
| --- | --- | --- | --- | --- |
| Temperature | Yes, °C | Mean + percentiles, °C | Present value, °C | Enabled at exact matching timestamps |
| Wind speed | Yes, m/s at 10 m | Mean + percentiles, m/s at 10 m | Preceding 10-minute mean, m/s | Enabled at exact matching timestamps; gridded vs station representativeness remains a limitation |
| Precipitation | Next-hour mm | Hourly mm in normalized samples | No collected values | Disabled; accumulation alignment not validated |
| Sea-level pressure | Not retained by current MET collector | hPa | Not collected | Disabled |
| Wind direction / u,v | MET direction not retained | u/v means stored | Not collected | Disabled; any future direction scoring must use circular differences |
| Cloud cover | Not retained | Not collected by current collector | Not collected | Disabled |

At audit: 196,193 MET points, 54,000 WeatherNext points, 180,054 observation rows.
The observation collector requests only `air_temperature,wind_speed`, with default
levels/offsets and time series 0. All 44 stations returned by the Frost wind metadata
lookup for 15–16 September used m/s, 10 m above ground, zero offset. Every active
station with stored wind observations was covered. Sampling frequency varies
(1/10 minutes and hourly or longer); sampling frequency is not an averaging window.
Metadata/units are not persisted per observation in the current schema. Revalidate
this audit if the network or collectors change; it is not a universal calibration claim.

Sources checked:
- [MET forecast definitions](https://docs.api.met.no/doc/locationforecast/datamodel.html)
- [Frost elements metadata](https://frost.met.no/api.html#!/elements/getElements)
  (`air_temperature` = present value; `wind_speed` = preceding ten-minute mean)
- [Frost time-series metadata](https://frost.met.no/api.html)
- [WeatherNext catalog](https://developers.google.com/earth-engine/datasets/catalog/projects_gcp-public-data-weathernext_assets_weathernext_3_0_0_0p1deg)
  and the locally validated collector field/unit mapping.

## Exact observed targets

Forecast vs Actual and the new Overall Accuracy view use observed values at the
forecast's exact UTC valid time. They do not interpolate, backfill, floor sub-hour
observations, or average later observations into that time. Identical duplicate
observations count once; conflicting values at one station/time are excluded.
Future observations are hidden. This deliberately replaces the dashboard's former
hourly-average/one-forecast-to-many-observations behavior. Stored history is unchanged.
The old scorer query remains for compatibility; the new UI no longer uses it.

## Fair Overall Accuracy

- Period filters valid time, relative to current UTC, not retrieval/issue date.
- Filter the current active network or one station, and the existing scorer bucket.
- Match the same station, valid time and lead-time bucket for both providers.
- Choose the pair with the smallest lead difference, at most 3 hours. Ties prefer
  newer WeatherNext, then newer MET runs; run IDs resolve remaining ties.
- Select one pair per station/valid time/bucket, without using forecast errors to
  select it. Repeated model runs cannot overweight a target within a bucket.
- Both runs must be issued and collected before valid time. This excludes retrospective
  WeatherNext backfills from the operational comparison.
- Both providers use the same actual value and equal sample counts. Missing either
  forecast or actual removes the target from both providers' comparison.
- Reuse `scoring.scorer.BANDS`, `LABELS` and the existing MAE/bias aggregation.
  MAE is mean absolute error; bias is forecast minus actual. The displayed difference
  is WeatherNext MAE minus Yr/MET MAE. Positive favors Yr/MET.
- All buckets pools station/time/bucket pairs: a station/time can count in more
  than one bucket. Both pair count and distinct station/time target count are shown.
- Daily curves summarize this same shared pool by valid UTC day; their sample/lead
  mix can change between days. Counts appear in tooltips and details.

Leads are close, not identical. This is a controlled comparison of archived forecast
products, not a claim of identical model initialization or station/grid calibration.
Do not combine temperature and wind into a single score. Short history is exploratory.

Selected-run summary MAE also requires shared targets, matching buckets, a lead gap
of at most 3 hours and collection before valid time. Individual observed errors can
still be inspected for runs with different ages; these do not become a fair aggregate.

## Model disagreement

Rank absolute differences at future shared valid times using the latest available
stored run for each provider/station. Both lead times and run issue times are shown;
these can differ substantially. Disagreement is not an accuracy ranking. No actual
observations are required. The top-20 selector opens the corresponding station,
variable and runs in Forecast vs Actual. No alerts or collection are triggered.


## Verified retrospective long-range temperature

The **Long-range temperature** tab is an explicit retrospective evaluation,
separate from operational Overall accuracy and selected-run summary scores.
`dashboard_scores.load_long_range_temperature` accepts WeatherNext temperature
means whose original publication before target is certified in
`weathernext_verified_history`. Local retrieved_at is never rewritten.
Uncertified late-collected forecasts remain ineligible. Operational forecasts
collected before target can participate without historical certification.

Verification binds the exact run, valid time, asset, lead, source collection,
units and mean value; ingestion must be between initialization and target.
The reader rechecks stored evidence against current forecast/sample identity.
No table or invalid evidence grants no historical exception. The importer
validates the complete saved manifest atomically and rejects conflicting evidence.

Each nominal 72/120/168/216h comparison requires both leads within ±3h and a
pair gap ≤3h, exact identical Frost targets, original issues before target,
and one closest-lead pair per station/time/horizon. Matching never uses errors.
Conflicting observations, future targets and inconsistent stored leads are
excluded. Each provider has the same sample count. These explicit nominal
windows intentionally differ from the broader operational scorer buckets.

The view displays the actual matched UTC period, plus each horizon's dates,
sample count, MAE and WN-minus-Yr MAE difference. Details include signed bias,
actual lead ranges and historical sample counts. Station/window filters apply
to target time. Zero samples produce no MAE/bias, not a perfect zero error.
Small samples, correlated targets and unequal leads limit model-ranking claims.


## Default Forecast vs Actual pair selection — 2026-09-22

Automatic fair pair reuses the operational pair_forecasts eligibility logic, with
original issues before valid time: equal target, same existing lead bucket, ≤3h
lead gap and both collected before target. It considers the selected station and
variable across stored runs, not just the newest 12 dropdown entries. Windows are
72h or 168h from the earliest stored valid time of either run; Full run is unbounded.

Choose the newest pair having at least one exact, unambiguous Frost observation in
that window. Newness is ordered by the earlier of the two issues, then the later
issue and stable run IDs, all descending. This deliberately does not minimize
forecast errors, maximize sample count or merely minimize the lead gap. Without
observed pairs, prefer a fair pair with upcoming targets and explain that observed
MAE is unavailable; otherwise select the newest fair pair and explain the empty
observed pool. If none qualifies, show an explicit reason and label independent
latest-run forecasts as inspection-only.

The selected-run MAE helper uses the same operational matcher and displayed chart
window. Manual mode can still inspect unfair pairs, whose shared MAE remains empty
with an explanation. Overall Accuracy, Long-range temperature and Model disagreement
results were compared with the committed implementation on the same live read-only
snapshot and remained unchanged. Health changes are presentation only.
