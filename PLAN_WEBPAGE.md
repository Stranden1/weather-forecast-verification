# Plan: compact cloud pipeline + public webpage

_Written 2026-09-23 by Claude. Status is tracked in the checklist at the bottom._

## Goal

Show, publicly and over months, whether **Yr** or **Google WeatherNext** predicts
Norwegian weather better. Keep only the data needed to answer that, run collection
in the cloud (not on the PC), and publish a free static webpage.

## Why the current setup is heavy

Every 6 h the local app stores WeatherNext's full 360-hour forecast for 6
variables × 6 statistics × 50 stations, forever: ~1.5 M rows/day, a 2.4 GB SQLite
file, heading for ~100 GB/year. Almost none of it is needed for scoring.

## New design (built in `cloud/`, `site/`, `.github/workflows/`)

1. **Snapshot only what gets scored.** Each run saves, per station, only the
   forecast hours whose lead falls within ±3 h of a verification horizon:
   6 h, 12 h, 1, 2, 3, 5, 7 and 10 days. Temperature, wind and hourly rain;
   WeatherNext mean/p10/p50/p90; Yr from the `complete` endpoint (adds Yr's
   own p10/p90 and rain min/max/probability).
2. **Score once, then discard.** When a UTC day is over (plus 6 h for late
   observations), each station/hour/horizon gets one row: Yr, WeatherNext and
   the Frost measurement. The snapshots for that day are deleted.
3. **Keep scored days forever** as `history/YYYY/YYYY-MM-DD.csv.gz`
   (~50–60 KB/day, ~20 MB/year). Written once, never edited.
4. **Webpage** (`site/`) reads small JSON summaries built from `history/`.

### Fairness rules (new)

- **Same moment, same head start.** Yr and WeatherNext are taken from the same
  collection run, so they have identical leads. "1 day ahead" = what you could
  see 24 h before. The closest run to each horizon is used; errors never choose.
- WeatherNext uses its newest **hourly** run (48 h long) for short targets and
  the newest **6-hourly** run for long ones, as a user checking would.
- WeatherNext is scored on both its **mean** and **median** (mean smooths
  extremes, which flatters average error).
- **Verdicts need evidence**: 95% block-bootstrap interval (days as the unit) on
  MAE difference; "too close to call" if it includes zero; none before 7 days.
- The site explains Yr's **home advantage** (station-corrected first 2–3 days).
- Rain: hourly amounts on 6 h–2 d horizons (Yr is 6-hourly beyond ~2.5 days),
  with wet-hour POD / FAR / CSI. Canonical interval-end keys as in PRECIPITATION.md.

### Storage where

| What | Where | Size |
|---|---|---|
| Pending snapshots + recent Frost obs | `state` branch, **replaced** each run (no history) | ~0.5 MB |
| Scored days | `history/` on main, one file per day | ~20 MB/year |
| Webpage JSON | built in the workflow, deployed to Pages, **not committed** | <1 MB |

### Cloud collection

GitHub Actions, every 6 h (`.github/workflows/collect.yml`): collect → score →
export → deploy Pages. Secrets: `MET_USER_AGENT`, `FROST_CLIENT_ID`,
`EARTH_ENGINE_PROJECT`, `EE_SERVICE_ACCOUNT_KEY`. Setup: `SETUP_CLOUD.md`.

### Licensing

Yr/Frost: CC BY 4.0 with attribution (on the page). WeatherNext **real-time**
data has separate Google DeepMind terms. Until read, the page publishes only
error statistics, not WeatherNext forecast values (`WX_PUBLISH_FORECAST_VALUES=0`).

## Webpage views

- Headline tiles: 1-day error for each, verdict with uncertainty range.
- Error by horizon (6 h → 10 days): Yr, WeatherNext mean, WeatherNext median.
- Over time: daily error + 7-day rolling line, per horizon.
- Map: which service wins per station; station panel with last 7 days measured vs forecast.
- Patterns to watch: frost / mild / warm, wind strength, wet vs dry vs heavy rain,
  lowland / hills / mountain; uncertainty honesty (inside p10–p90 ≈ 80%?); rain detection.
- How to read this fairly + attribution.

## Existing local app

Unchanged. `app.py`, the Windows task and `data/weather.db` keep working. Run
both in parallel for a week, compare, then stop the Windows task. The Streamlit
app can stay as a private deep-dive tool.

## Steps and status

- [x] 1. Cloud pipeline code: `cloud/` (collectors, snapshot store, scoring, summaries). 8 unit tests pass.
- [x] 2. Static webpage: `site/` (vendored Chart.js + Leaflet, light/dark, mobile). Previewed with demo data.
- [x] 3. Workflows: `collect.yml` (every 6 h) and `tests.yml`.
- [x] 4. Migration script: `cloud/migrate_sqlite.py` (read-only on weather.db).
- [ ] 5. **User/Claude Code, locally:** check Git history for secrets, then make the repo public
       and enable Pages (SETUP_CLOUD.md steps 1–2). *2026-09-23: history and the new files
       scanned, no secrets found; making the repo public and enabling Pages are still to do.*
- [ ] 6. **User:** add secrets and the Earth Engine service account (SETUP_CLOUD.md steps 3–4).
- [ ] 7. **Claude Code, locally:** run `python -m unittest discover -s cloud/tests -t .`, commit
       `cloud/ site/ .github/ history/.gitkeep PLAN_WEBPAGE.md SETUP_CLOUD.md`, push.
       *2026-09-23: tests pass (8), committed; workflows moved to `.github/workflows/`; not pushed.*
- [ ] 8. Run the workflow manually once; check the log and the `state` branch.
- [ ] 9. **Claude Code, locally:** run the migration with `--until` = first cloud day; check a
       few days against the Streamlit app; commit `history/`.
- [ ] 10. After ~1 week of parallel running: compare, then remove the Windows task.
- [ ] 11. Later: read WeatherNext real-time terms → decide `WX_PUBLISH_FORECAST_VALUES`.
- [ ] 12. Later: consolidate handoff docs (current-state PROJECT_STATUS, open-items NEXT_STEPS, CHANGELOG).
