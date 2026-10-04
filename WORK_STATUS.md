# Work status

_The latest task's checkpoint only. When a new task finishes, move this entry to the top of
`CHANGELOG.md` and replace it._

## Hourly trigger with a 150-minute gate — 2026-10-04 (Claude)

Done (not pushed; shown to the user first):
- Rebased the 2 local commits (storm replays; WeatherNext terms decision) onto origin's
  "Store encrypted scored days" (2 Oct day); 197 tests passed after the rebase.
- `collect.yml`: cron `23 * * * *` (was `17 */3 * * *`), `workflow_dispatch` kept, concurrency
  group kept. A gate step after restore runs `python -m cloud.run due` (`--manual` on dispatch);
  every later step needs `steps.due.outputs.run == 'true'`.
- `cloud/health.py`: `MIN_GAP_MIN` = 150 and `due(meta, now, manual)` from `last_success`;
  `RUN_EVERY_H` = 3 unchanged; `PREVIOUS_RUN_EVERY_H`, `RUN_EVERY_CHANGED_AT` and their test removed.
- DECISIONS.md "WeatherNext terms": Google's 4 Oct reply (1-hour rule on target time) replaces
  the open-ambiguity / no-reply wording; new rule: never show WeatherNext values for future target
  times. NEXT_STEPS item 1 updated. Code already cuts off on target time (summarize, replay).
- Tests: 2 new (gate rules; the `due` command writes `run=false/true` to `GITHUB_OUTPUT`).

Remaining: push (user's OK). Then watch the gaps (NEXT_STEPS item 4). The two items from the
previous task still apply: the user sets `WX_PUBLISH_FORECAST_VALUES`; replay steadiness on the page.
