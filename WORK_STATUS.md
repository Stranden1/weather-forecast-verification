# Work status

_The latest task's checkpoint only. When a new task finishes, move this entry to the top of
`CHANGELOG.md` and replace it._

## Past WeatherNext values and storm replays — 2026-10-02 (Claude)

Done (not pushed; shown to the user first):
- DECISIONS.md "WeatherNext terms": the user's decision to publish past WeatherNext values under
  CC BY 4.0, our reading, the open ambiguity, the 26 Sep email to weathernext@google.com as the
  user reported it (no reply), and removal if Google asks.
- Values only for targets at least `PUBLISH_MIN_AGE_H` = 1 h old (`summarize.build` recent
  series and `replay`). The workflow reads the repository variable `WX_PUBLISH_FORECAST_VALUES`
  (default 0) instead of a hard-coded 0. **Not yet turned on:** the user sets the variable.
- The CC BY citation and the real-time notice sit under every chart that draws WeatherNext
  values (station chart, storm replays), from `meta.wn_value_attribution`.
- Storm replays (PLAN_REPLAYS step 2, card of step 3): `find_events`, `select_events`, `replay`,
  `build_replays` in `cloud/replay.py`; `events.json` + `events/<id>.json`. Real history gives
  17 events (11 wind, 5 rain, 1 cold).
- Tests: 197 pass (12 new replay/publishing tests); page checked locally with the real history,
  desktop and 375 px (a too-wide event picker was fixed).

Remaining: push (user's OK), then the user sets the repository variable. Steadiness on the page
(PLAN_REPLAYS step 3 rest), the 15 Sep hand check (step 4: that day has no complete rain horizon,
so it has no replay).
