@echo off
setlocal
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo Run run_windows.bat once first so the Python environment exists.
  pause
  exit /b 1
)
.venv\Scripts\python.exe background_collect.py
echo.
echo Background collection finished. See data\background.log for details.
pause
