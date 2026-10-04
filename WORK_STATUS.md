# Work status

_The latest task's checkpoint only. When a new task finishes, move this entry to the top of
`CHANGELOG.md` and replace it._

## Workflow actions off Node.js 20 — 2026-10-04 (Claude)

Done (pushed as 1eb4140; "Cloud pipeline tests" run 37236715635 green, 119 tests, the Node.js 20
warning is gone):
- `collect.yml` and `tests.yml`: checkout v4 → v7, setup-python v5 → v7, configure-pages v5 → v6,
  upload-pages-artifact v3 → v5 (uses upload-artifact v7), deploy-pages v4 → v5; all node24.
- Breaking changes checked against our use: upload-pages-artifact v4+ leaves out dotfiles (`site/`
  has none); setup-python v7 dropped `pip-install` (unused; `cache`/`cache-dependency-path`
  remain); checkout v6+ credential file and v7 fork-PR block don't apply (`persist-credentials:
  false`, no `pull_request_target`/`workflow_run`).
- Run #44 (12:21 UTC 4 Oct) failed only on ECMWF/Open-Meteo (read timeouts, 0 rows); Yr,
  WeatherNext and Frost were fine.

Remaining:
- The new actions in `collect.yml` first run on the next collect run; check it deploys Pages.
- Gate not yet seen in action: as of 21:36 UTC 4 Oct GitHub had started no scheduled run since
  18:38 (none at 19:23, 20:23, 21:23; #46 at 20:17 was manual). Check that scheduled runs resume,
  and that a skipped run leaves `state` and Pages untouched and adds no run record (NEXT_STEPS 4).
- Still open: the user sets `WX_PUBLISH_FORECAST_VALUES`; replay steadiness on the page.
- `ubuntu-latest` moves to Ubuntu 26 from 19 Oct (runner notice); watch the first run after that.
