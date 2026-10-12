# Work status

_The latest task's checkpoint only. Archive it in CHANGELOG.md when replacing it._

**Data note, 2026-10-11:** `data/weather.db` and its 7z archive were deleted and are lost (no
copy was made). The cloud `history/` is the only record.
See CHANGELOG.md.

## Retire Wisting (SN20925) — 2026-10-12 (Claude)

**Done, committed, not pushed.**

- Frost returns 404 for SN20925 (source, time series and observations; name search finds nothing;
  Alvheim works with the same credentials). Last measurement 30 Sep 21:00 UTC. No renamed
  successor nearby (Hjelmsøybanken II SN20924 is 3° further west, a different site).
- `config/stations.json`: `"active": 0` for SN20925, nothing else changed.
- Checked on a rebuild from history, with and without the change: `rows` 224292 and `days` 37
  unchanged; leaderboard identical (1 day temp: n 25438, Yr 0.914, WeatherNext 0.917);
  `stations.json` still has SN20925's scores; `meta.json` 49 stations (Wisting gone). Page: 49
  markers, no console errors. `history/` tree hash unchanged. Tests: 130 OK.
- New on the page: Revsbotn - Danielsvika has been silent since 9 Oct (see NEXT_STEPS item 1).
