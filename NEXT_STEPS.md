# Next steps

_Open items only. Updated 2026-10-14. Completed work is in CHANGELOG.md._

## Order of work

Follow REVIEW_2026-10-14.md, one task per session:

- **Task 2 activation checkpoint:** simplified M1 Yr archive is implemented and validated locally, disabled. Follow SETUP_YR_ARCHIVE.md: owner creates an initialized private archive repo and repository-only push token, stored directly as WX_YR_ARCHIVE_TOKEN. Configure repo and immutable first UTC cutoff; keep ENABLED=0 until explicit push/activation OK. Then verify two actual cloud slots and unchanged scoring/health. Local evidence: work/yr-archive-2026-10-14/. No durable spool or object storage; existing WX_STATE_KEY is reused.
- Task 3: read-only four-product temperature/wind comparison from existing history; short findings file, no page changes before review.
- Task 4: read-only WeatherNext/IFS/AIFS pressure backfill study for the plan's eight-station pilot; short findings file.
- Task 5: consolidate FORECAST_PLAN.md into PLAN_FORECAST_ARCHIVE.md (or mark replaced), adding a one-page summary.
- Scorecard publication remains pending; do not push without authorization. Local evidence: work/scorecard-revisions-2026-10-14/.

## Deployment follow-up

1. Verify the next real collect/deploy of scorecard commit `39c2617`, now on `origin/main` with CI passed. The 15:07 UTC run 38267891738 gated/skipped deployment; at 15:10 UTC the live page was still the previous version. Review the new private forecast viewer on `codex/scorecard-corrections`; that checkpoint remains local. Rebase over any newer immutable history commits before an approved push. Private future-value screenshots must never be published.

## Operations

2. Confirm Revsbotn's resumed reporting in exact-hour cloud observations; keep it active. Fresh 10-minute Frost records were verified at 11:40/11:50 UTC on 12 Oct. Enningdalen and Alvheim recovered. Finalized-score warnings can lag live recovery.
3. Watch a real collecting/deploying run and tests after the Ubuntu runner migration begins **19 Oct 2026**. Existing Python 3.12/workflows are unchanged.
4. Renew the repository-only timer token **before 5 Nov 2026 17:15 UTC / 18:15 Oslo**. Enter it directly in cron-job.org job 8590224, never chat/files. Keep the timer and hourly fallback; cadence since activation was verified at 2.5–3.0 h.
5. Confirm a separate secure copy of `WX_STATE_KEY` and encrypted `history/`, and validate an isolated recovery from that copy. Current history decrypts; independent backup recovery remains unverified. No full project backup is needed.
6. Old plaintext Git objects/caches: coordinate cleanup only if the publication policy still requires it. Never rewrite current immutable day files or main history as routine maintenance.

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
