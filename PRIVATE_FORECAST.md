# Private forecast comparison

This local viewer compares future Yr and WeatherNext forecasts from encrypted cloud
working state. It is independent of the retired PC collector and needs no database.
It reads forecasts; it does not collect, write history, or publish anything.

## Open it

In Windows PowerShell, from `E:\WeatherApp`, using the existing `.venv` and `.env`:

```powershell
git fetch origin state
.\.venv\Scripts\python.exe -B -m private_forecast
```

Open http://127.0.0.1:8765. Stop with Ctrl+C. If that port is occupied, add
`--port 8766`. The server always listens on this PC's loopback address; it has no
network-facing bind option. It reads `origin/state` by default. No dependencies
need installing in the current environment.

Re-read uses the latest state ref fetched to the PC. It does not fetch from GitHub;
run `git fetch origin state` again to update that ref. Original provider issue times
and the cloud collection time remain visible. Snapshots older than eight hours are
marked old; the viewer never fills gaps with older runs. It re-reads that local ref
once a minute to update ages and remove expired targets, without a network fetch.

## What is ready

- All active station choices, 24/48-hour windows, temperature/wind/precipitation,
  light/dark themes, uncertainty bands, shared-hour differences, a largest-gap
  shortcut and numeric tables.
- Latest collection with both providers, keeping missing counterpart hours visible.
  WeatherNext temperature/wind use the mean; precipitation uses the median.
- Correct hourly precipitation end times; no daily totals or high/low from sparse data.
- Local-only data API, no external assets, no file export, no credential exposure,
  no caching, blocked nonlocal Host/Origin headers, and an explicit asset allowlist.

The timeline is **incomplete by design**: current collection saves verification
windows rather than every forecast hour. Lines/ranges stop at gaps. A Yr-style
continuous forecast needs a separately agreed, compact prospective capture. This
viewer does not enable that capture or claim a model will be right.

## Keep it private

Current project policy permits public WeatherNext values only once targets are at
least one hour old. This viewer shows future values for the owner's internal use;
never expose the server, forward its port, copy values into public site JSON, or
publish its screenshots. `WX_STATE_KEY` stays in Python's environment and is never
sent to the browser. Git contains the viewer source, not decrypted forecasts.

Private screenshot evidence is in ignored `work/forecast-comparison-2026-10-12/`.
Google's experimental-data notice and access source remain displayed.
See [WeatherNext terms](https://storage.googleapis.com/weathernext-public/terms-of-use.pdf)
and DECISIONS.md for the publication rule.

## Checks

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s private_forecast/tests -t .
node tests/private_forecast_ui_test.cjs http://127.0.0.1:8765 work/private-forecast-preview
```

The optional browser check needs installed Playwright/Chrome, with `NODE_PATH`
pointing to Playwright if it is outside the project. It checks 1280/375/320 px in
both themes and blocks external browser requests. Screenshots contain private
future values and belong only in ignored local evidence directories.
