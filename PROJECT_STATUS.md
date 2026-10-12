# Project status

_Updated 2026-10-12. Current state only; history is in CHANGELOG.md._

## Summary

Cloud collection is healthy and is the only live pipeline. The PC collector was retired on 11 Oct; weather.db and its archive were deleted and are lost. Encrypted `history/` is the only retained record. Protect it and `WX_STATE_KEY` independently.

Verified data: 37 scored days through 11 Oct, 224,292 rows; 25 paired days at one day. Main one-day temperature/rain-median results are too close; WeatherNext has a small overall wind advantage. Regional/event differences are more informative, but are short-sample descriptions rather than station winner claims.

## Ready for review

Local branch `codex/scorecard-corrections` has three validated checkpoints after Wisting's retirement commit. It corrects UTC daily rain aggregation, median/date-scope consistency and station wording; adds a compact first answer and accessible controls/tables; and shows catches/misses/false alarms for freezing, wind and wet hours with land/offshore groups. Monthly and detailed analyses remain available in disclosures.

143 cloud tests pass. Browser checks pass in both themes at 1280/375/320 px, with no captured JS errors or page-wide overflow. Real-history export is ~937 KB. Phone answer now appears at y=409 px; collapsed page length ~5,332 px versus ~10,085 px previously. Screenshots/logs are in `work/scorecard-2026-10-12/`. The scorecard commits are now on `origin/main` at `39c2617`, and CI passed (run 38266975312). At the 15:10 UTC check, the live page was still the previous version; run 38267891738 gated/skipped deployment. Verify the next actual collecting/deploying run.

The owner chose a private prediction view. `private_forecast/` now reads future Yr/WeatherNext snapshots from fetched encrypted cloud state on loopback only, with station/24–48 h selection, ranges, gaps, issue ages, largest-gap navigation and tables. Eight private data/access tests and browser checks in both themes at all three widths pass. It needs no database and changes no collection. Start with `PRIVATE_FORECAST.md`; the ranked finish plan is `FORECAST_PLAN.md`. Private screenshots stay in ignored `work/forecast-comparison-2026-10-12/`.

## Operations and remaining choices

- Since 6 Oct timer activation, measured collection gaps were 2.5–3.0 h. Timer/fallback and workflows are unchanged.
- Wisting is inactive locally (49 active stations); existing historical scores remain. Revsbotn resumed reports on 12 Oct; Enningdalen and Alvheim recovered. Finalized-history warnings can lag raw recovery.
- Full local runs are lost. The private timeline is incomplete because current capture keeps scoring windows. Complete 48-hour/daily forecasts require prospective retention; new variables/quality fields and model comparisons need a scope decision.
- All history decrypts with the current local key; a recovery from an independent backup is unverified.
- Watch Ubuntu runner migration from 19 Oct. Renew timer token before 5 Nov 17:15 UTC. Older plaintext Git objects remain a separate policy/cleanup item.

NEXT_STEPS.md holds open work; WORK_STATUS.md holds the completed checkpoint and review instructions.
