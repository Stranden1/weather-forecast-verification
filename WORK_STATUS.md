# Work status

_The latest task's checkpoint only. When a new task finishes, move this entry to the top of
`CHANGELOG.md` and replace it._

## Early cloud days filled; WeatherNext terms read — 2026-09-26 (Claude)

Done:
- 23 and 24 Sep cloud day files replaced once from the PC database (user's OK), recorded in
  DECISIONS.md. 7,910 / 8,274 rows, all with WeatherNext, marked `nn5km`. `weather.db` only read.
- WeatherNext terms read: catalog page "Terms of Use" and the real-time terms PDF
  (https://storage.googleapis.com/weathernext-public/terms-of-use.pdf, last modified 3 Sep 2026).
  Data for times ≥ 1 hour ago is CC BY 4.0 with a fixed citation. Newer and future data falls
  under the real-time terms: internal use, value-added services, and only controlled sharing
  of the data itself.

- Fixed the same day: the public `state` branch held future WeatherNext forecasts. State files
  are now Fernet-encrypted (`cloud/store.py`, key `WX_STATE_KEY` as a GitHub secret and in local
  `.env`); plain files stay readable. Verified after a manual run at 15:25 UTC: both files
  encrypted, readable with the key, all sources OK, new rows `bilinear`. 44 cloud tests pass.
  Old plain versions may stay reachable on GitHub by commit hash for a while.
- Page attribution now uses WeatherNext's exact CC BY citation; `FINDINGS_2026-09-26.md`
  committed with it.

Remaining: the user sets `WX_PUBLISH_FORECAST_VALUES=1` (NEXT_STEPS item 1).
