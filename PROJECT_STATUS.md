# Project status

_Updated 2026-10-12. Current state only; history is in CHANGELOG.md._

## Summary

The cloud is the only live pipeline. The PC collector was retired on 11 Oct; weather.db and its archive were deleted and are lost. Encrypted `history/` is the only retained record; preserve it and protect `WX_STATE_KEY` separately.

Collection has run every 2.5–3.0 hours since the external timer began on 6 Oct. Live data verified on 12 Oct: 37 scored days through 11 Oct, 224,292 rows, with 25 paired days at the one-day horizon. Source status is healthy. One-day temperature/rain-median comparisons are too close; WeatherNext currently has a small overall wind advantage. These are short, mixed station/method cohorts.

## Current work

Local branch `codex/scorecard-corrections` starts from Wisting's retirement commit. Checkpoints 1–2 correct daily rain boundaries and replay labels/publication timing, rain median views and calendar period scopes; 140 cloud tests pass. Mobile clarity and practical event views are in progress. No new collection or deployment is authorized by this checkpoint.

## Operations and retained capabilities

- Cloud retains selected horizons, Yr/WeatherNext values, quantiles, probabilities, observations and IFS/AIFS. Full local runs are lost; fixed-run daily analyses need a separate prospective retention decision.
- Wisting is inactive in local config (49 active stations); retirement is not yet published. Revsbotn resumed 10-minute reports on 12 Oct; Enningdalen and Alvheim report again. Page warnings use finalized scored history, so lag current recovery.
- The live blend has a day-resampled uncertainty interval; map/list differences are descriptive, not station significance tests.
- GitHub fallback and external timer remain unchanged. Watch Ubuntu runner migration from 19 Oct; renew timer token before 5 Nov 17:15 UTC.
- Existing plaintext Git objects and secure history/key recovery remain separate open operational items. No history files were rewritten.

NEXT_STEPS.md tracks open work; WORK_STATUS.md holds the active checkpoint.
