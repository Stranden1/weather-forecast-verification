# Work status

## Outside review on Claude Fable 5.2 — 2026-11-12 (Claude)

Followed `BRIEF_FABLE_REVIEW.md`. Report only: no code, workflow, scoring or history changes.

**Done**
- `docs/reviews/REVIEW_2026-11_fable.md`: code and robustness findings ranked by impact, and a
  readability proposal (Norwegian front page, simple and detailed layers, status line).
- Checked against the live page and its public JSON (19:07 UTC run, 12 Nov) and the GitHub run
  log. 178 cloud tests pass. `history/` was not decrypted and `.env` was not read.
- Top code findings: the gate counts a run as a success when Yr or WeatherNext delivered
  nothing; the day bootstrap treats correlated days as independent (ranges too narrow);
  dependencies are unpinned and reinstalled every run.

**Remaining:** the owner reads the review and answers its five decisions (last section).
Nothing is implemented. Ytterøyane Fyr and Ormen Lange are still due about 1 Dec, and the
Nov winter calm-night rerun is still due.
