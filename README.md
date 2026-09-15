# WeatherApp

Local Windows weather forecast verification dashboard. Compares Yr/MET and Google
WeatherNext 3 forecasts with Frost observations across a shared Norwegian station
network. Stores forecast history in SQLite and displays temperature comparisons,
WeatherNext uncertainty, station maps, and temperature/wind accuracy in Streamlit.
WeatherNext rainfall is stored but is not yet scored.

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
`WORK_STATUS.md`, `NEXT_STEPS.md` and `DECISIONS.md` for the project handoff.
Historical references to `work/` in those documents refer to local-only evidence.
