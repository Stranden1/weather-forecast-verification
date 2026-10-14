# Work status

## Push and Yr archive activation — 2026-10-14 (Claude)

**Done**
- Rebased the scorecard, map-sentence and Yr archive commits onto `origin/main`; `history/` byte-identical to origin. 171 cloud tests pass. Pushed to `main` (09abaf0, owner OK); CI tests and collect run 38641643498 succeeded; live page matches `site/` and shows the new design.
- Owner fixed setup: `WX_YR_ARCHIVE_REPO=Stranden1/yr-archive` (private, README on `main`). Secret `WX_YR_ARCHIVE_TOKEN` present (not read). `WX_YR_ARCHIVE_START_AT=2026-10-15T08:30:00Z`.
- Set `WX_YR_ARCHIVE_ENABLED=1` at 21:54 UTC (owner OK). Manual collect run 38643799647: all steps success. `health.json.yr_archive`: enabled, status idle, 0 captured, 0 errors, published. Archive repo got one bot commit with only `forecast/yr/v1/policy.json.gz.fernet`. Main health unchanged: yr 1323, wn 2352, ecmwf 4606, frost 5594 rows, 0 errors each.

**Remaining:** inspect the first two real windows (15 Oct 08:30–13:00 and 20:30–01:00 UTC): 49/49 stations, slot index/manifest objects, 0 archive errors, unchanged main health. To stop, set ENABLED=0 (remote objects stay).
