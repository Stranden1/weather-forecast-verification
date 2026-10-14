# Project status

_Updated 2026-10-14. Current state only; history is in CHANGELOG.md._

## Summary

The cloud pipeline is the only live collection system. The PC collector was retired on 11 Oct; weather.db and its archive were deleted and are lost. Encrypted history/ is the only retained record. Protect it and WX_STATE_KEY independently.

Last verified retained data: 37 scored days through 11 Oct, 224,292 rows, 25 paired one-day days. One-day temperature is Yr 0.91 vs WeatherNext 0.92 °C, too close to call. These are the existing public validation fixtures, not a fresh live-health audit.

## Local scorecard ready

Task 1 of REVIEW_2026-10-14.md is complete. The journal styling now covers events, horizons, replays, expanded analysis, monthly summaries and methodology. The blend finding appears below the scores only with a supported better verdict. Published horizon values are primary; height adjustments use smaller hollow grey markers and thin dashed ranges. The map reports land/offshore counts for the selected period/horizon, and the biggest differences show existing height/lake notes. Replay notices retain their full wording as footnotes; Open source links to the repository. Wholly empty sections hide.

The export adds an offshore field from the existing height metadata (unknown stays null). Scoring, station membership, collectors, history, site/data, secrets and scheduling are unchanged. Earlier prototype improvements are retained. Changes are committed locally; no push/deployment.

Validation: 143 cloud tests; browser checks at 1280/375/320 px in light/dark, with real fonts/map tiles, expanded sections, filters, charts/tables, keyboard and zoom behavior, blend visibility, map counts and empty data. Evidence: work/scorecard-revisions-2026-10-14/. Existing NumPy/pandas deprecation warnings remain.

The earlier scorecard corrections are on origin/main at 39c2617 with CI passed; a subsequent real deployment still needs verification. The private forecast viewer remains available on codex/scorecard-corrections; PRIVATE_FORECAST.md describes launch. Future-value screenshots remain private in ignored work/.

## Next and operations

- Next session: simplified M1 Yr archive, approved in REVIEW_2026-10-14.md. Separate private repo, one existing encryption key, no spool; validate disabled first and obtain owner OK before enabling. Then four-product comparison, pressure pilot and plan consolidation, in that order.
- Independent key/history backup and recovery are owner actions, still unverified. Older plaintext Git objects remain a separate cleanup decision.
- Timer/fallback and workflows unchanged; last cadence audit found 2.5–3.0-hour gaps. Wisting inactive; 49 active stations share the network. Revsbotn resumed reports on 12 Oct; finalized-score warnings can lag recovery.
- Check Ubuntu runner migration from 19 Oct; renew timer token before 5 Nov 17:15 UTC / 18:15 Oslo.

NEXT_STEPS.md holds open work; WORK_STATUS.md holds the latest checkpoint.
