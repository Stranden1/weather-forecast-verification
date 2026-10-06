# Work status

_The latest task's checkpoint only. When a new task finishes, move this entry to the top of
CHANGELOG.md and replace it._

## External timer dispatch - 2026-10-06 (Codex)

Done:
- Added the workflow_dispatch choice `trigger` (`manual` default, or `timer`).
- Only dispatches with `trigger=manual` pass `--manual`; timer runs respect the
  existing 150-minute gate. Hourly cron and collection concurrency are unchanged.
- SETUP_CLOUD.md documents the timer POST, headers, JSON, expected 204 response
  and repo-only fine-grained token with Actions: Read and write; placeholders only.
- Recorded the decision and refreshed handoff docs, preserving the earlier pending
  health-review edits and archiving the previous checkpoint in CHANGELOG.md.
- All 119 cloud tests pass using the existing .venv, including gate boundary and
  manual-bypass tests. Existing dependency/resource warnings remain.
- Five gate expression cases and unchanged schedule/concurrency verified locally;
  `git diff --check` passes.

Remaining:
- Await the user's OK to push, then configure the external timer and verify live
  timer skips/collections and the default manual bypass (SETUP_CLOUD.md).
- Existing deployment, coverage and feature follow-ups remain in NEXT_STEPS.md.

Committed locally only; no push or live dispatch. No database, history
day files, credentials, collector code or Windows scheduled-task changes.
