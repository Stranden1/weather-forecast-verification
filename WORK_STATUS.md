# Work status

## Scorecard corrections and presentation — 2026-10-12 (Codex)

**Checkpoint 1 validated; local branch `codex/scorecard-corrections`, not pushed.**

- UTC rain totals/events now include interval ends 01:00 through next midnight. Final-hour publication protection tightened.
- Hourly-median sums labelled correctly; single-point replays retain a visible measured reference.
- 132 cloud tests pass; real-history export succeeds (37 days, 224,292 rows). No history, collectors, secrets or workflows changed.
- Wisting retirement was already committed before this branch; Revsbotn resumed 10-minute measurements on 12 Oct at 11:40/11:50 UTC. Keep Revsbotn active.

**Remaining in this task:** consistent rain representations and calendar-date filters; careful station wording; compact first answer/accessibility; practical event comparisons from existing data; final browser verification and handoff.

**Data:** PC collector retired; weather.db and archive are lost. `history/` and `WX_STATE_KEY` are essential.
