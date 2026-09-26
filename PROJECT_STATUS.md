# Project status

_Current state only, rewritten at the end of each task. Updated 2026-09-26. History: `CHANGELOG.md`._

## Summary

WeatherApp checks which forecast is more accurate in Norway: **Yr** (MET Norway) or Google's
AI model **WeatherNext 3**. Both are compared with **Frost** station measurements at 50
stations. Two systems run side by side while the new one is proven:

| | Cloud pipeline (the future) | Local app (being phased out) |
|---|---|---|
| Where | GitHub Actions every 6 h → public page on GitHub Pages | Windows scheduled task every 6 h → Streamlit `app.py` |
| Stores | Only the scored rows: `history/YYYY/*.csv.gz` (~90 MB/year) | Everything: `data/weather.db`, now 3.08 GB |
| Code | `cloud/`, `site/`, `.github/workflows/` | `app.py`, `collectors/`, `scoring/` |
| Plan | `PLAN_WEBPAGE.md` | `SCORING.md`, `WEATHERNEXT.md` |

## Cloud pipeline

- All three sources have worked on every run since **25 Sep 04:58 UTC**, when WeatherNext
  access for the service account started working (before that only Yr and Frost).
- Scored days: 5–22 Sep migrated from the local database; 23 Sep empty (first run was that
  evening); 24 Sep Yr only; 25 Sep with WeatherNext from 05 UTC. From 26 Sep, complete days.
- The page shows error by horizon, trend, a station map, weather/terrain patterns,
  uncertainty ranges, rain detection, a naive "same as before" baseline with skill, and a
  health line. WeatherNext's forecast values are hidden until its data terms are read;
  its errors are in every score.

## Waiting locally (not pushed)

These are committed on `main` but not on GitHub, so the cloud and the page don't use them yet:

- **Bilinear WeatherNext sampling** on the native grid, recorded per row (`wn_sampling`).
  The local collector already uses it from 26 Sep 16:00 UTC.
- **Height-adjusted WeatherNext temperature** as a separate, labelled line, plus height
  notes for 15 stations. Published values stay the main score; no station is dropped.
- **Forecast steadiness** numbers (`steadiness.json`, not yet shown on the page).
- **Project HQ** (`project_hq/`), a local read-only viewer of these documents: run
  `.\.venv\Scripts\python.exe -B project_hq\run.py` and open http://127.0.0.1:8510.

GitHub has 3 newer scored-day commits from CI; they only add `history/` files and merge cleanly.

## First results (preliminary: about one week with both services)

From `FINDINGS_2026-09-26.md` and `INVESTIGATION_COLD_BIAS_2026-09-26.md`:

- **Temperature:** Yr ahead at short range as published. WeatherNext reads too cold at
  stations whose ~5 km grid area is much higher than the station; after a standard height
  adjustment WeatherNext is ahead at 12 h–1 day (0.78/0.80 vs Yr 0.84/0.89 °C).
- **Wind:** WeatherNext ahead at 1–2 days, especially in stronger wind.
- **Rain:** Yr has the lower average error; WeatherNext's average catches more rain but gives
  many false alarms, and its median is about as good as Yr.
- **Steadiness:** WeatherNext changes its forecast about half as much as Yr between runs.
- WeatherNext's uncertainty ranges are too narrow for wind (50% inside vs 80% ideal).

## Validation

Tests: 79 local-app, 43 cloud-pipeline and 8 Project HQ tests pass (26 Sep).
Run: `.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py"` (local + cloud)
and `.\.venv\Scripts\python.exe -B -m unittest discover -s project_hq -p "test_*.py"`.

## Known limits

- Only about a week of paired data: treat every result as preliminary. Verdicts need 7 days.
- Yr has a home advantage: its first 2–3 days are corrected with these stations' data.
- Hourly rain is scored only up to 2 days ahead; the 10-day horizon has almost no data yet.
- Pressure, wind direction and cloud cover are not scored (no matching observations).

## Where to find things

| File | What it holds |
|---|---|
| `NEXT_STEPS.md` | Open items only |
| `WORK_STATUS.md` | The latest task's checkpoint |
| `CHANGELOG.md` | Everything done so far, newest first |
| `DECISIONS.md` | Rules and choices that must be kept |
| `SCORING.md`, `PRECIPITATION.md` | How the local app matches and scores forecasts |
| `PLAN_WEBPAGE.md`, `SETUP_CLOUD.md` | Cloud pipeline design and setup |
| `PLAN_REPLAYS.md` | Next feature: storm replays and steadiness |
| `REVIEW_2026-09-23.md`, `INVESTIGATION_*.md`, `FINDINGS_*.md` | Reviews and analyses |
