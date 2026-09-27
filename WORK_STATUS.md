# Work status

_The latest task's checkpoint only. When a new task finishes, move this entry to the top of
`CHANGELOG.md` and replace it._

## ECMWF IFS and AIFS added to the cloud collector — 2026-09-27 (Claude)

Done (DECISIONS.md, "ECMWF IFS and AIFS via Open-Meteo"):
- `cloud/openmeteo.py` collects `ecmwf_ifs` and `ecmwf_aifs025_single` from Open-Meteo in the
  same run as Yr/WeatherNext, same horizon windows, with station heights (`elevation`).
- New scored columns `ifs_issued/t/w/p`, `aifs_issued/t/w/p`, filled from the fetch Yr and
  WeatherNext already select; pairing rules unchanged; old history files untouched.
- Attribution: Open-Meteo and ECMWF lines added to `ATTRIBUTION`. Not shown on the page otherwise.
- Tests: `cloud/tests/test_openmeteo.py` with a recorded response
  (`cloud/tests/fixtures/openmeteo_ecmwf.json`, Oslo + Troll B, 26 Sep 22:08 UTC). A health test
  that had started calling Open-Meteo live now mocks it. 132 tests (80 local + 52 cloud) and 8 HQ pass.
- Live dry run (no state written): 50 stations, 4,600 rows, 4.4 s, no errors.

Pushed. Confirmed on 27 Sep: the 05:19 UTC cloud run stored 4,800 ECMWF rows with no errors, and the page shows the new credit lines. The local task's runs since 26 Sep 16:10 UTC use bilinear sampling (Losistua's WeatherNext temperature rose ~1.2 °C from the old higher cell). First scored day with ECMWF: 27 Sep.
