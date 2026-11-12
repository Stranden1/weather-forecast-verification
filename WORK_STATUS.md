# Work status

## Repository cleanup before an outside review — 2026-11-12 (Claude)

Owner wants Claude Fable 5.2 to review the project and the page's readability for ordinary
people, and asked to tidy up first.

**Done**
- Checked: main fast-forwarded to origin (history through 11 Nov, 68 days, no gaps);
  178 cloud tests pass; collect runs every ~30 min succeed with 0 source errors; live
  health.json shows Yr archive errors 0.
- Moved, unchanged, with `git mv`: the retired PC collector (root `app.py`, `database.py`,
  `collectors/`, `scoring/`, root `test_*.py`, `.bat`/`.ps1` task scripts, `START_HERE.txt`,
  `tests/dashboard_ui_test.py`, `PRECIPITATION.md`, `WEATHERNEXT.md`) to `legacy/`;
  older findings, reviews and finished plans to `docs/findings/`, `docs/reviews/`,
  `docs/plans/`. Each folder has a README. References updated in the active docs,
  `cloud/replay.py` and `cloud/heights.py` comments; `CHANGELOG.md` keeps old paths.
  `cloud/` imports nothing from the moved files; `requirements.txt` stays (Project HQ).
- Ytterøyane Fyr (SN57770): Frost has only qualityCode 6 (model-filled) for temperature and
  wind since 1 Nov 17:00 UTC, the same pattern as Ormen Lange. Station still valid in Frost.
  No new scored rows, which is correct; the page header shows a station history warning.
- `BRIEF_FABLE_REVIEW.md`: scope, hard rules and the two review tracks (code/robustness and
  readability for ordinary people) for the Fable session. Report goes to `docs/reviews/`.

**Remaining:** run the Fable review in its own session. Owner decides on Ytterøyane Fyr
together with Ormen Lange about 1 Dec. The Nov winter calm-night rerun is still due.
