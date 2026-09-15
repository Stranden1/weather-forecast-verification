@echo off
setlocal
cd /d %~dp0

set PYTHON_CMD=
where py >nul 2>nul
if %errorlevel% equ 0 set PYTHON_CMD=py
if not defined PYTHON_CMD (
  where python >nul 2>nul
  if %errorlevel% equ 0 set PYTHON_CMD=python
)

if not defined PYTHON_CMD (
  echo Python was not found.
  echo Install Python 3.11 or newer from python.org, then run this file again.
  pause
  exit /b 1
)

if not exist .venv (
  echo Creating local Python environment...
  %PYTHON_CMD% -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --disable-pip-version-check -q -r requirements.txt

if not exist .env copy .env.example .env >nul

set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set STREAMLIT_SERVER_HEADLESS=false

echo.
echo Starting Weather Benchmark V0.2...
echo.
streamlit run app.py
