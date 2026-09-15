@echo off
cd /d %~dp0
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_background_task.ps1"
if %errorlevel% neq 0 (
  echo.
  echo Task installation failed. The error above explains why.
) else (
  echo.
  echo Background collection is now installed.
)
pause
