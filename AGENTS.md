# Working agreement

Work incrementally. Keep the application runnable after each major change.
Do not leave a partially applied database migration. Commit/write and validate
each stage before moving to the next. If approaching usage limits or unable to
complete the remaining work, stop at a safe checkpoint and report exactly what
is complete and what remains.

`E:\WeatherApp\data\weather.db` is authoritative. Never delete, reset, replace,
or copy an earlier trial database over it. Preserve existing stations, MET/Yr
forecasts and Frost observations. Schema migrations must be additive and checked
before and after. Do not create new full project backups or hash the whole project
as routine preparation; the user has already backed up the important data.

Use the existing `.venv`. WeatherNext must use the same active station network as
MET/Frost. Change or restart the scheduled task only after the relevant integration
has passed validation. Preserve `.env` secrets and never include them in reports.

Read `WEATHERNEXT.md` before changing the local WeatherNext integration.

## Handoff documents (since 2026-09-26)

Keep them short; nothing is lost, because `CHANGELOG.md` and Git keep the history.

- `PROJECT_STATUS.md`: current state only, about one page. **Rewrite** it; never append
  dated sections. Keep its `## Summary` heading (Project HQ reads it).
- `NEXT_STEPS.md`: open items only. Remove an item when it is done.
- `WORK_STATUS.md`: the latest task's checkpoint only (what is done, what remains).
  At the end of a task, move the previous entry to the top of `CHANGELOG.md`, then write yours.
- `CHANGELOG.md`: dated record of completed work, newest first. Add to the top; don't rewrite.
- `DECISIONS.md`: rules and choices that must be kept. Add a dated section for new ones.

At the end of each substantial task, update the ones whose contents changed.

## Cloud pipeline (added 2026-09-23)

A separate compact pipeline lives in `cloud/`, `site/`, `history/` and
`.github/workflows/`. It does not use or modify `data/weather.db` (the one-off
`cloud/migrate_sqlite.py` only reads it). Read `PLAN_WEBPAGE.md` before changing it.
`history/` day files are written once and never edited. Several assistants
(ChatGPT/Codex and Claude) work here: check `git status` first and work one at a time.
