# Project status

_Updated 2026-10-15. Current state only; history is in CHANGELOG.md._

## Summary

The cloud pipeline is the only live collection system. The PC collector was retired on 11 Oct; weather.db and its archive were deleted and are lost. Encrypted history/ is the retained scoring record. Protect it and WX_STATE_KEY independently.

Simplified M1 Yr archive is deployed and enabled since 14 Oct 21:54 UTC; first save window is 15 Oct 08:30 UTC. It retains full existing Yr responses twice daily in a separate private Git repository, using the existing key, first-published per-station selection, slot-window retries and immutable partial/missing manifests. Raw bytes preserve native fields/intervals and precision. No durable spool, extra normal weather requests or schedule change. The immutable activation cutoff prevents false missing records for earlier windows.

The private transport checks repository privacy, scopes the new credential, adds only encrypted objects and verifies pushed bytes. Archive failures remain separate from weather-source success/gating and are reported after main publication. Existing history/state/scoring and shared 49-station network are unchanged. Activation run 38643799647: 0 archive errors, policy file written to Stranden1/yr-archive, main health unchanged.

Validation: all 171 cloud tests pass with archive and transport tests using synthetic keys and temporary bare Git remotes. Two read-only acquisition probes each captured 49/49 active stations, with zero errors and exact encrypted readback: ~0.459 MB and 8–11 seconds per batch, suggesting ~0.335 GB/year plus manifests. These back-to-back probes were outside scheduled windows; actual private-GitHub slots and independent backup recovery remain unverified. Evidence: work/yr-archive-2026-10-14/; existing NumPy/pandas deprecation warnings remain.

## Local page and data checkpoints

Task 1 scorecard revisions are committed as 944cd2d, with handoffs/reviews in 4e622eb. The journal style covers the whole page, supported blend findings are visible, published horizon values are primary, and station counts/caveats explain the map. The latest sentence shows both land counts and explicit ties; offshore unanimity is stated plainly. Earlier 1280/375/320 light/dark browser checks passed. Latest sentence checks also pass at all three widths in both themes; evidence: work/map-counts-2026-10-14/. Earlier full-page evidence: work/scorecard-revisions-2026-10-14/. Published 14 Oct 21:40 UTC (collect run 38641643498); live files match site/.

Last verified retained data: 37 scored days through 11 Oct, 224,292 rows, 25 paired one-day days. One-day temperature Yr 0.91 vs WeatherNext 0.92 °C, too close to call. No fresh live pipeline-health audit was performed here. The 21:37 UTC collect on 14 Oct ran all four sources with 0 errors. The private forecast viewer is in the repo; PRIVATE_FORECAST.md describes launch.

## Next and operations

- Archive: inspect the first two real slots on 15 Oct (49/49 stations, manifests, 0 errors). Task 3 (four-product comparison) is in FINDINGS_FOUR_PRODUCT_2026-10-15.md, awaiting review: at 6–48 h Yr and WeatherNext are too close to call, IFS is clearly worst, AIFS beats IFS, and the Yr+WeatherNext average beats all four. Task 4 (pressure pilot, FINDINGS_PRESSURE_PILOT_2026-10-15.md): WeatherNext and IFS/AIFS pressure backfill completely for the eight pilot stations; WeatherNext's ensemble mean has the lowest error, which is not a fair test against single ECMWF runs. Task 5 remains.
- Independent key/history backup and recovery remain owner actions. Older plaintext Git objects remain a separate cleanup decision.
- Timer/fallback unchanged; last cadence audit found 2.5–3.0-hour gaps. Wisting inactive; 49 active stations share the network. Revsbotn resumed reports on 12 Oct; finalized warnings can lag recovery.
- Check Ubuntu runner migration from 19 Oct; renew timer token before 5 Nov 17:15 UTC / 18:15 Oslo.

NEXT_STEPS.md holds open work; WORK_STATUS.md holds the latest checkpoint.
