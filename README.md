# WeatherApp

Checks which forecast is more accurate in Norway: Yr/MET or Google WeatherNext 3,
against Frost observations at a shared Norwegian station network. Temperature, wind and
hourly precipitation are scored. Start with [PROJECT_STATUS.md](PROJECT_STATUS.md).

The cloud is the only live pipeline:

- **Cloud pipeline** (`cloud/`, `site/`, `.github/workflows/`): collects every 3 hours on
  GitHub Actions, keeps only scored rows in `history/`, and publishes a static scorecard on
  GitHub Pages. See [PLAN_WEBPAGE.md](PLAN_WEBPAGE.md) and [SETUP_CLOUD.md](SETUP_CLOUD.md).
- **Legacy local app**: retired on 11 Oct 2026. Its database and 7z archive were deleted
  without a backup and are lost. The code below remains for reference and fixture tests.
  Encrypted `history/` is the only retained record; keep `WX_STATE_KEY` safe outside Git.

**Project HQ** (`project_hq/`) is a local, read-only viewer of the project documents:
`.\.venv\Scripts\python.exe -B project_hq\run.py`, then open http://127.0.0.1:8510.

**Private forecast comparison** (`private_forecast/`) reads future Yr/WeatherNext
snapshots from encrypted cloud state, without collecting or publishing them.
See [PRIVATE_FORECAST.md](PRIVATE_FORECAST.md). It needs no local database; the
current timeline explicitly shows gaps in the saved verification snapshots.

## Legacy local installation (retired)

The existing `.env` and `.venv` remain. These legacy commands cannot recover the lost
database, and local collection is not part of the cloud maintenance workflow:

```powershell
cd E:\WeatherApp
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Alternatively, double-click `run_windows.bat`; it also checks dependencies.
The dashboard reads stored data; collection is an explicit Admin action or the
existing background task. Git commits and pushes do not collect or change data.

## Install on another computer

Use Python 3.11 or newer (the current installation is tested with Python 3.13).
From your cloned project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env  # New installations only; never overwrite your existing .env
```

Edit `.env` locally: set `MET_USER_AGENT` to identify your app/contact and set
`FROST_CLIENT_ID`. Do not enter a Frost client secret. For WeatherNext, set your
Earth Engine project, authenticate with `.\.venv\Scripts\earthengine.exe authenticate`,
and follow [WEATHERNEXT.md](WEATHERNEXT.md) before enabling automatic collection.
Run the app and use Admin to build/refresh the station network and collect initial
MET/Frost data. A clone does not include historical observations or forecasts.
The station snapshot in `config/stations.json` documents the existing network;
it is not automatically imported and does not replace the live database.

Do not reinstall the retired Windows task during cloud maintenance. A new local installation
would be a separate collection project, with no copy of the lost full history.

## Tests

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s cloud/tests -t .
```

Optional page regression checks use a disposable export of history and installed Playwright/Chrome:

```powershell
node tests/scorecard_ui_test.cjs <temporary-export-directory> work/scorecard-preview
```

Expose the installed Playwright package through `NODE_PATH` if needed. The browser check
blocks external requests by default; `WX_TEST_MAP_TILES=1` permits OpenStreetMap tiles.
It checks both themes at 1280 and 375 px, period/rain consistency, station selection,
single-point replays and horizontal overflow. Screenshots stay in ignored `work/`.
The legacy `tests/dashboard_ui_test.py` uses a disposable database, not production data.

## What Git stores

Source code, collectors, scoring, additive schema/migration code, tests, requirements,
launch/task scripts, sanitized `.env.example`, station metadata in `config/`, and
documentation. `database.py` defines the base schema; the WeatherNext collector
contains its additive migration. Keep the authoritative local database intact.

## What stays local

`.env` and credentials, `.venv`, all `data/` (including live SQLite files, database
backups and collection logs), Python caches, `work/` experiments and validation
artifacts, `outputs/`, screenshot folders, editor settings and temporary files.
GitHub is a code backup, not a backup of your weather history or authentication.
Existing backups remain local. Never copy a trial database over `data/weather.db`.

## Normal Git workflow

```powershell
git status
git add .
git diff --cached --stat
git diff --cached
git commit -m "Describe the change"
git push
```

Review staged changes for secrets before committing. See `PROJECT_STATUS.md`,
`NEXT_STEPS.md`, `WORK_STATUS.md`, `DECISIONS.md` and `CHANGELOG.md` for the project
handoff. References to `work/` in those documents refer to local-only evidence.


The dashboard also offers fair shared-target Overall Accuracy and a future Model
Disagreement view. See [SCORING.md](SCORING.md) for the variable audit and matching
rules, including exact observation times and comparable forecast leads.


### Long-range temperature comparison

Open **Long-range temperature** for retrospective Yr/WeatherNext temperature MAE
at 3, 5, 7 and 9 days. The compact table shows shared sample counts and evaluation
dates; choose a station or time window, and expand details for bias and actual
leads. Verified historical WeatherNext forecasts qualify using original publication
time. Actual local retrieval timestamps and operational accuracy rules are kept.
The existing database stores verification alongside forecasts; no extra service is
needed. See `SCORING.md` and `WEATHERNEXT.md` for details.
