$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$script = Join-Path $root "background_collect.py"
$taskName = "WeatherApp Background Collector"

if (-not (Test-Path $python)) {
    throw "Python environment not found. Run run_windows.bat once first."
}

$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $script + '"') -WorkingDirectory $root
$first = (Get-Date).Date.AddMinutes(10)
if ($first -le (Get-Date)) { $first = $first.AddDays(1) }
$trigger = New-ScheduledTaskTrigger -Once -At $first -RepetitionInterval (New-TimeSpan -Hours 6)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Collect MET/Yr forecasts and Frost observations for WeatherApp every 6 hours." -Force | Out-Null
Write-Host "Installed: $taskName"
Write-Host "Runs every 6 hours. Missed runs start when Windows becomes available again."
