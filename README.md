# WeatherApp

Checks which forecast is more accurate in Norway: Yr/MET or Google WeatherNext 3,
against Frost observations at a shared network of 50 stations. Temperature, wind and
hourly precipitation are scored. Start with [PROJECT_STATUS.md](PROJECT_STATUS.md).

It has two parts:

- **Cloud pipeline** (`cloud/`, `site/`, `.github/workflows/`): collects every 6 hours on
  GitHub Actions, keeps only scored rows in `history/`, and publishes a static scorecard on
  GitHub Pages. See [PLAN_WEBPAGE.md](PLAN_WEBPAGE.md) and [SETUP_CLOUD.md](SETUP_CLOUD.md).
- **Local app** (this page, below): a Windows scheduled task stores full forecast history in
  SQLite, with a detailed Streamlit dashboard. It runs in parallel until the cloud pipeline
  is proven.

**Project HQ** (`project_hq/`) is a local, read-only viewer of the project documents:
`.\.venv\Scripts\python.exe -B project_hq\run.py`, then open http://127.0.0.1:8510.

## Run the existing local installation

Your existing `.env`, `.venv`, database and scheduled task remain in place.
From PowerShell:

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

The existing Windows scheduled task does not need reinstalling. On a new machine,
use `install_background_task.bat` only after manual collection is validated.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe tests/dashboard_ui_test.py
```

The UI test uses a disposable database and checks that browsing makes no writes.

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
