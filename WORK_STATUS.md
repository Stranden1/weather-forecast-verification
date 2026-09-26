# Work status

_The latest task's checkpoint only. When a new task finishes, move this entry to the top of
`CHANGELOG.md` and replace it._

## Documentation cleanup — 2026-09-26 (Claude)

Done, following REVIEW_2026-09-23 §4:

- `PROJECT_STATUS.md` rewritten as current state only (about one page, keeps a `## Summary`
  heading, which Project HQ's overview reads).
- `NEXT_STEPS.md` rewritten as open items only. Items already done were dropped. Checked
  facts: cloud WeatherNext works since 25 Sep 04:58 UTC; cloud 23 Sep is empty, 24 Sep has Yr
  only, 25 Sep has WeatherNext from 05 UTC; `--strict` exists but the workflow does not use it.
- The old work log moved to `CHANGELOG.md`, newest first, wording unchanged. A script checked
  that every line is there. The old dated sections of PROJECT_STATUS/NEXT_STEPS are in Git
  history (commit `7e01378`).
- README: removed "rainfall is not yet scored", added the cloud pipeline and Project HQ.
- AGENTS.md and CLAUDE.md: the new rules for these files.
- Project HQ committed first as its own commit (`7e01378`, Codex's work, unchanged).

No code, data, history or schedule changed. 79 local + 43 cloud + 8 HQ tests pass.
Not pushed.
