# Work status

## Pressure backfill pilot (task 4) — 2026-10-15 (Claude)

**Done**
- Read-only MSLP pilot for the eight §6 stations: 28 fixed 00/12 UTC runs (29 Sep–12 Oct), leads
  6–120 h every 6 h, WeatherNext (Earth Engine) and IFS/AIFS (Open-Meteo Single Runs API) against
  Frost QFF. Findings: `FINDINGS_PRESSURE_PILOT_2026-10-15.md`. Script, raw responses and output:
  `work/pressure-pilot-2026-10-15/` (ignored; raw holds past WeatherNext values, keep private).
- Backfill was complete for all three products (28/28 runs, every value). WeatherNext MAE is lowest
  at every lead and station, but it is an ensemble mean against single ECMWF runs, so this is not a
  fair model verdict. IFS and AIFS are about equal.
- No code, history, state or page changes. 171 cloud tests pass.

**Remaining:** owner review. Possible next step: an ECMWF ensemble-mean series for a fair comparison.
Task 2 slot checks (15 Oct) are still open; task 5 follows.
