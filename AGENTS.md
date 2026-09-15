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

Read `WORK_STATUS.md` and `WEATHERNEXT.md` before resuming this integration.
Keep a concrete completion/remaining-work checkpoint in `WORK_STATUS.md`.
At the end of future substantial tasks, also update `PROJECT_STATUS.md`,
`NEXT_STEPS.md`, and `DECISIONS.md` when their contents are affected.
