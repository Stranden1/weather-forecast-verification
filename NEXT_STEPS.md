# Next steps

_Open items only. Updated 2026-11-13. Completed work is in CHANGELOG.md._

## Order of work

**Next: owner approves pushing review part A** (6 local commits, 13 Nov; see WORK_STATUS.md). After the push, check the first runs: gate log "last complete run … min ago", collection every 150 min, `tests.yml` green on `cloud/requirements-lock.txt`.

Then the rest of `docs/reviews/REVIEW_2026-11_fable.md`, one part per session (owner decisions recorded in DECISIONS.md, 13 Nov):
- **Part B:** block bootstrap in `summarize.bootstrap_diff` (finding 2). Show the owner a before/after table of verdicts that change before committing; update SCORING.md.
- **Part C:** Norwegian simple front page and split status line (suggested order, steps 1–2).
- **Part D:** hit rates within 1 °C / 2 m/s in `summarize.stats()`, icon rows, dumbbell chart (steps 3–4).
- Left from part A, each needing its own small decision: finding 6 (history read and verified twice per run); finding 8's retired stations in `meta.json`, `allow_nan=False` on export (would stop the run before state is published), `WX_STATE_KEY` only on the Python steps, self-hosted fonts; one retry for a failed Yr station inside a run.

All five REVIEW_2026-10-14 tasks are done (task 2's first archive windows checked 16 Oct: 49/49, closed manifests, 0 errors). Follow the one-page summary in PLAN_FORECAST_ARCHIVE.md, one task per session. Open owner reviews:

- **ECMWF note (live since 26 Oct):** static and dated (docs/findings/FINDINGS_FOUR_PRODUCT_2026-10-26.md). Rerun `work/four-product-2026-10-26/analyze.py` once winter data exist (about February) and revise or remove the note if the ranking changes (DECISIONS.md, 26 Oct). The blend stays Yr + WeatherNext only; no offshore wording change before winter data.
- **Winter calm-night reruns:** run `work/winter-inversion/analyze.py <history dir>` about the 1st of Nov, Dec, Jan, Feb and Mar (needs `.env` with `WX_STATE_KEY` and current history from origin/main). Baseline: docs/findings/FINDINGS_WINTER_INVERSION_2026-10-23.md. The owner decides after the January run whether the height-adjusted line changes (DECISIONS.md, 23 Oct).
- `docs/findings/FINDINGS_PRESSURE_PILOT_2026-10-15.md`: a fair pressure comparison needs an ECMWF ensemble-mean series.
- Yr archive: occasionally confirm each day has am/pm folders with 49 stations and a manifest, and that `health.json.yr_archive.errors` is 0. A missed window shows as a partial/missing manifest.

## Operations

1. Ormen Lange (SN76933): temperature has only Frost qualityCode 6 (model-filled) since 15 Oct 10:00 UTC, so no new scored rows. Owner decision 29 Oct: keep active; re-check about 1 Dec and, if still code 6, retire it with `"active": 0` (DECISIONS.md, 29 Oct).
   Ytterøyane Fyr (SN57770) has the same problem since 1 Nov 17:00 UTC (temperature and wind code 6). Owner to decide whether the same 1 Dec rule applies.
2. Confirm Revsbotn's resumed reporting in exact-hour cloud observations; keep it active. Fresh 10-minute Frost records were verified at 11:40/11:50 UTC on 12 Oct. Enningdalen and Alvheim recovered. Finalized-score warnings can lag live recovery.
3. Timer token renewed 26 Oct 2026; it expires **26 Oct 2027**. Renew before then. Enter it directly in cron-job.org job 8590224, never chat/files. Keep the timer and hourly fallback; since 13 Nov (part A, after push) the gate gives a steady 2.5 h and retries at the next tick when Yr or WeatherNext delivered nothing.
4. Confirm a separate secure copy of `WX_STATE_KEY` and encrypted `history/`, and validate an isolated recovery from that copy. Current history decrypts; independent backup recovery remains unverified. No full project backup is needed.
5. Old plaintext Git objects/caches: coordinate cleanup only if the publication policy still requires it. Never rewrite current immutable day files or main history as routine maintenance.

## Next product/data decisions

- Yr rain-probability reliability still needs a verified provider threshold and matching observed interval. Four-product and pressure studies follow the approved order above; broader coherent WeatherNext/ECMWF snapshot capture remains a later decision.
- Choose prospective quality/provenance fields and any alternative WeatherNext rain outputs (native versus satellite-calibrated/experimental), before broader variable/network expansion. No collection expansion has started.
- Consider partial-provider replays only after deciding how to explain missing counterpart hours; never present an incomplete total as a full day.
- Revisit results at 30 paired days, after another month and during winter. Hold thresholds/metrics steady; investigate land/offshore, sampling-method cohorts, and height adjustment in cold valleys before making recommendations.

## Housekeeping

- Deprecate/remove only legacy unpaired entry points in `scoring/scorer.py`; the module has actively used helpers.
- Address NumPy timedelta/pandas concatenation warnings before dependency upgrades. Upgrades go through `cloud/requirements-lock.txt` in their own commit (DECISIONS.md, 13 Nov). Boolean inversion in event filtering was corrected in the rain checkpoint.
- Keep `work/temperature-backfill/first-run.json` and `second-run.json` as provenance. Retain `work/scorecard-2026-10-12/` and private `work/forecast-comparison-2026-10-12/` evidence for review; archive other evidence only deliberately.

## Standing rules

- Cloud history is the only retained record. Never delete, rewrite or reset day files. Local database and archive are lost; do not restart the retired PC collector as cloud maintenance.
- Past WeatherNext values are enabled in the published project; require targets at least one hour old and retain attribution. Disable through `WX_PUBLISH_FORECAST_VALUES=0` if needed.
- Preserve one shared active station network and revalidate measurement height/unit metadata when changing it. Retired station histories remain in aggregate scores.
- Protect credentials outside Git. PowerShell secret updates should use `gh secret set --body`, not a pipe that may add a BOM.
