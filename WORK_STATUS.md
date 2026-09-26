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

Remaining (see NEXT_STEPS item 1):
- **The public `state` branch holds 10,900 future WeatherNext forecast rows** in
  `pending.csv.gz` (checked 26 Sep ~15:10 UTC). Proposed fix, not yet approved: encrypt the
  state files with a key in a GitHub secret.
- Then update the page attribution to the exact CC BY citation and decide
  `WX_PUBLISH_FORECAST_VALUES`.
