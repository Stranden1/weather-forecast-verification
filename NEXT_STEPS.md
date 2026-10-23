# Next steps

_Open items only. Updated 2026-10-23. Completed work is in CHANGELOG.md._

## Order of work

All five REVIEW_2026-10-14 tasks are done (task 2's first archive windows checked 16 Oct: 49/49, closed manifests, 0 errors). Follow the one-page summary in PLAN_FORECAST_ARCHIVE.md, one task per session. Open owner reviews:

- **~27 Oct, four-product rerun:** at 30 paired days, rerun `work/four-product-2026-10-15/analyze.py` on the longer period (same cohort rules, day-block intervals). If IFS/AIFS still trail Yr and WeatherNext, the owner decides then whether the page gets an ECMWF section (DECISIONS.md, 16 Oct). The blend stays Yr + WeatherNext only; no offshore wording change.
- **Winter calm-night reruns:** run `work/winter-inversion/analyze.py <history dir>` about the 1st of Nov, Dec, Jan, Feb and Mar (needs `.env` with `WX_STATE_KEY` and current history from origin/main). Baseline: FINDINGS_WINTER_INVERSION_2026-10-23.md. The owner decides after the January run whether the height-adjusted line changes (DECISIONS.md, 23 Oct).
- `FINDINGS_PRESSURE_PILOT_2026-10-15.md`: a fair pressure comparison needs an ECMWF ensemble-mean series.
- Yr archive: occasionally confirm each day has am/pm folders with 49 stations and a manifest, and that `health.json.yr_archive.errors` is 0. A missed window shows as a partial/missing manifest.

## Operations

2. Confirm Revsbotn's resumed reporting in exact-hour cloud observations; keep it active. Fresh 10-minute Frost records were verified at 11:40/11:50 UTC on 12 Oct. Enningdalen and Alvheim recovered. Finalized-score warnings can lag live recovery.
3. Renew the repository-only timer token **before 5 Nov 2026 17:15 UTC / 18:15 Oslo**. Enter it directly in cron-job.org job 8590224, never chat/files. Keep the timer and hourly fallback; cadence since activation was verified at 2.5–3.0 h.
4. Confirm a separate secure copy of `WX_STATE_KEY` and encrypted `history/`, and validate an isolated recovery from that copy. Current history decrypts; independent backup recovery remains unverified. No full project backup is needed.
5. Old plaintext Git objects/caches: coordinate cleanup only if the publication policy still requires it. Never rewrite current immutable day files or main history as routine maintenance.

## Next product/data decisions

- Yr rain-probability reliability still needs a verified provider threshold and matching observed interval. Four-product and pressure studies follow the approved order above; broader coherent WeatherNext/ECMWF snapshot capture remains a later decision.
- Choose prospective quality/provenance fields and any alternative WeatherNext rain outputs (native versus satellite-calibrated/experimental), before broader variable/network expansion. No collection expansion has started.
- Consider partial-provider replays only after deciding how to explain missing counterpart hours; never present an incomplete total as a full day.
- Revisit results at 30 paired days, after another month and during winter. Hold thresholds/metrics steady; investigate land/offshore, sampling-method cohorts, and height adjustment in cold valleys before making recommendations.

## Housekeeping

- Deprecate/remove only legacy unpaired entry points in `scoring/scorer.py`; the module has actively used helpers.
- Address NumPy timedelta/pandas concatenation warnings before dependency upgrades. Boolean inversion in event filtering was corrected in the rain checkpoint.
- Keep `work/temperature-backfill/first-run.json` and `second-run.json` as provenance. Retain `work/scorecard-2026-10-12/` and private `work/forecast-comparison-2026-10-12/` evidence for review; archive other evidence only deliberately.

## Standing rules

- Cloud history is the only retained record. Never delete, rewrite or reset day files. Local database and archive are lost; do not restart the retired PC collector as cloud maintenance.
- Past WeatherNext values are enabled in the published project; require targets at least one hour old and retain attribution. Disable through `WX_PUBLISH_FORECAST_VALUES=0` if needed.
- Preserve one shared active station network and revalidate measurement height/unit metadata when changing it. Retired station histories remain in aggregate scores.
- Protect credentials outside Git. PowerShell secret updates should use `gh secret set --body`, not a pipe that may add a BOM.
