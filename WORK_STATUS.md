# Work status

## Scorecard corrections and presentation — 2026-10-12 (Codex)

**Complete and validated locally on `codex/scorecard-corrections`; not pushed or deployed.**

### Checkpoints
- `3373c75`: UTC rain-day totals/events and final-hour publication gate; 132 tests passed.
- `d1f9669`: consistent rain medians, calendar periods and matched uncertainty across statistical views; 140 tests passed.
- Final presentation/events checkpoint: concise answer, optional detail, accessible station selector/chart tables and event detection with land/offshore groups; 143 tests passed. See Git log for its commit.

### Verification
- Existing .venv; all 143 cloud tests pass. Real-history rebuild: 37 days, 224,292 rows; JSON 936,986 bytes. No history changes.
- Browser smoke check passes at 1280, 375 and 320 px in both themes, including filter/rain consistency, all-station selection and single-point replays. No captured JS errors or page-wide overflow.
- Phone answer y=409 px, first tile y=547 px, collapsed height 5,332 px versus previous ~10,085 px. Screenshots and validation.json: `work/scorecard-2026-10-12/` (ignored, retained).
- Prepared Wisting retirement predates this branch. Revsbotn resumed 10-minute observations at 11:40/11:50 UTC on 12 Oct; kept active. Scores can lag current recovery.
- All encrypted history files decrypt using the current key. A separate backup/restore from an independent key copy has NOT been verified.

### When returning
Review this branch against `main`, then publish if satisfied; include/rebase any new scored-history commits first. No push, workflow dispatch, secret rotation, collector change or new data capture was performed.

Choose additional collection separately: coherent daily runs, observation quality/provenance and alternative WeatherNext rain fields. IFS/AIFS and Yr probability views remain proposals. See NEXT_STEPS.md for the 19 Oct runner and before-5-Nov token work.

**Data:** the PC collector is retired; weather.db and archive are lost. `history/` is the only retained record; protect `WX_STATE_KEY` independently.
