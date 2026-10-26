# Project status

_Updated 2026-10-26. Current state only; history is in CHANGELOG.md._

## Summary

The cloud pipeline is the only live collection system. The PC collector was retired on 11 Oct; weather.db and its archive were deleted and are lost. Encrypted history/ is the retained scoring record. Protect it and WX_STATE_KEY independently.

Simplified M1 Yr archive is deployed and enabled since 14 Oct 21:54 UTC. Its first real windows (15 Oct am and pm) each captured 49/49 stations with closed manifests and 0 errors (checked 16 Oct). It retains full existing Yr responses twice daily in a separate private Git repository, using the existing key, first-published per-station selection, slot-window retries and immutable partial/missing manifests. Raw bytes preserve native fields/intervals and precision. No durable spool, extra normal weather requests or schedule change. The immutable activation cutoff prevents false missing records for earlier windows.

The private transport checks repository privacy, scopes the new credential, adds only encrypted objects and verifies pushed bytes. Archive failures remain separate from weather-source success/gating and are reported after main publication. Existing history/state/scoring and shared 49-station network are unchanged. Activation run 38643799647: 0 archive errors, policy file written to Stranden1/yr-archive, main health unchanged.

Validation: all 171 cloud tests pass with archive and transport tests using synthetic keys and temporary bare Git remotes. Two read-only acquisition probes each captured 49/49 active stations, with zero errors and exact encrypted readback: ~0.459 MB and 8–11 seconds per batch, suggesting ~0.335 GB/year plus manifests. Real private-GitHub slots are now verified; independent backup recovery remains unverified. Evidence: work/yr-archive-2026-10-14/; existing NumPy/pandas deprecation warnings remain.

## Local page and data checkpoints

Task 1 scorecard revisions are committed as 944cd2d, with handoffs/reviews in 4e622eb. The journal style covers the whole page, supported blend findings are visible, published horizon values are primary, and station counts/caveats explain the map. The latest sentence shows both land counts and explicit ties; offshore unanimity is stated plainly. Earlier 1280/375/320 light/dark browser checks passed. Latest sentence checks also pass at all three widths in both themes; evidence: work/map-counts-2026-10-14/. Earlier full-page evidence: work/scorecard-revisions-2026-10-14/. Published 14 Oct 21:40 UTC (collect run 38641643498); live files match site/.

Last verified retained data: 37 scored days through 11 Oct, 224,292 rows, 25 paired one-day days. One-day temperature Yr 0.91 vs WeatherNext 0.92 °C, too close to call. Live check 23 Oct 18:10 UTC: the latest collect ran all four sources with 0 errors; 197 of 200 collect runs since 16 Oct passed (the 3 failures were one-off Open-Meteo/Frost network errors); history/ holds 48 scored days, 5 Sep–22 Oct, with no gaps; Yr archive errors 0. The private forecast viewer is in the repo; PRIVATE_FORECAST.md describes launch.

## Next and operations

- Archive: first two real slots verified 16 Oct (49/49, closed manifests, 0 errors). Four-product comparison rerun on 26 Oct at 29 paired days (FINDINGS_FOUR_PRODUCT_2026-10-26.md) confirms the 15 Oct ranking with tighter intervals: at 6–48 h Yr and WeatherNext are too close to call, IFS is clearly worst, AIFS beats IFS but trails Yr, and the Yr+WeatherNext average beats all four. The page now carries a static, dated ECMWF note with the run-age caveat (DECISIONS.md, 26 Oct); ECMWF stays out of the blend. Task 4 (pressure pilot, FINDINGS_PRESSURE_PILOT_2026-10-15.md): WeatherNext and IFS/AIFS pressure backfill completely for the eight pilot stations; WeatherNext's ensemble mean has the lowest error, which is not a fair test against single ECMWF runs. Task 5 done: PLAN_FORECAST_ARCHIVE.md opens with a one-page summary and is the only forecast plan (FORECAST_PLAN.md replaced).
- Winter readiness is live (pushed 23 Oct, 463ef25): rain/mixed/snow wet-hour rows with a snow-undercatch caveat, and the height-adjusted WeatherNext column on the freezing card. Calm-night baseline (FINDINGS_WINTER_INVERSION_2026-10-23.md): the height adjustment helps overall but turns warm-biased on calm nights at inland valley stations; monthly reruns to March, owner decision after January.
- Independent key/history backup and recovery remain owner actions. Older plaintext Git objects remain a separate cleanup decision.
- Timer/fallback unchanged; last cadence audit found 2.5–3.0-hour gaps. Wisting inactive; 49 active stations share the network. Revsbotn resumed reports on 12 Oct; finalized warnings can lag recovery.
- Ubuntu runner migration done: collect runs pass on Ubuntu 24.04.5 since 19 Oct, and the first `tests.yml` run on the new runner passed on 23 Oct (463ef25).
- Failure alerts: since 23 Oct the collect workflow turns red only when the same source errs in 2 runs in a row, and Open-Meteo requests retry on timeouts and truncated replies (DECISIONS.md, 23 Oct).
- Renew the timer token before 5 Nov 17:15 UTC / 18:15 Oslo.

NEXT_STEPS.md holds open work; WORK_STATUS.md holds the latest checkpoint.
