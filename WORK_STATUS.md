# Work status

_The latest task's checkpoint only. Archive it in CHANGELOG.md when replacing it._

**Data note, 2026-10-11:** `data/weather.db` and its 7z archive were deleted and are lost (no
copy was made). The cloud `history/` is the only record.
See CHANGELOG.md.

## Station freshness warning — 2026-10-11 (Claude)

**Done, committed locally, not pushed.** Step 4, the last step, of the dashboard plan
(AgnosticBrain `plans/weatherapp-dashboard.md`, now done).

- Export (`cloud/summarize.py`): each station in `meta.json` gains `last_obs`, the latest scored
  hour with any measurement (temperature, wind or rain), or null if it never reported. Test added.
- Page (`site/app.js` `silentStations()`): a station is "without measurements" when `last_obs` is
  more than 48 h (`NO_OBS_H`, decision 4) before the end of `meta.last_day`. Stations that never
  reported are left out (the map already says "No data yet").
  - Health line: "1 station has no measurements since 30 Sept (WISTING [SN20925])", which turns the
    line into a warning. Several stations: "N stations have no measurements for over 2 days",
    names listed up to 3.
  - Map: a grey ring around the marker (separate outer circle, fixed #5f5f5f because the OSM tiles
    are light in both themes; a dashed border on the dot was tried first and was hard to see).
    Tooltip and station details say since when. The map's legend line mentions the ring.
- Live history now: only Wisting (SN20925, Barents Sea) is silent, last measurement 30 Sep 21:00 UTC.
  Enningdalen (SN1120) has recovered (10 Oct 23:00).
- Wisting sits just outside the map's default view in a narrow window (73.5° N); zooming out
  shows it. Not changed here.
- 129 cloud tests pass. Checked in the browser with data rebuilt from history: health line,
  ring, tooltip, station details; no console errors.

Next: plan finished. NEXT_STEPS item 5 (rain median on the remaining views) or ECMWF on the page.
