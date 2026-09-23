# Setting up cloud collection and the webpage

About 20 minutes, once. Nothing here touches your local `data/weather.db`.

## 1. Check for secrets, then make the repository public

Free GitHub Pages and unlimited Actions minutes need a public repo. Your
`.gitignore` has always excluded `.env`, but check the whole history first
(ask Claude Code to run this, or run it in PowerShell in E:\WeatherApp):

```powershell
git log --all -p | Select-String -Pattern "FROST_CLIENT_ID=\w|client_secret|private_key|BEGIN .*KEY"
```

No output means nothing was found. Then on GitHub: **Settings → General →
Danger Zone → Change visibility → Public**.

## 2. Turn on GitHub Pages

**Settings → Pages → Build and deployment → Source: GitHub Actions.**
The site address will be `https://stranden1.github.io/weather-forecast-verification/`.

## 3. Add secrets

**Settings → Secrets and variables → Actions → New repository secret**:

| Name | Value |
|---|---|
| `MET_USER_AGENT` | Same as in your `.env`, e.g. `WeatherApp/1.0 you@example.com` |
| `FROST_CLIENT_ID` | Same as in your `.env` (the client ID only, no secret) |
| `EARTH_ENGINE_PROJECT` | `weatherapp-508323` |
| `EE_SERVICE_ACCOUNT_KEY` | The whole JSON key file from step 4 |

## 4. Earth Engine service account (a login for the robot)

In the Google Cloud console, with project **weatherapp-508323** selected:

1. **IAM & Admin → Service Accounts → Create service account.** Name: `weather-bot`.
2. Grant roles **Earth Engine Resource Viewer** and **Service Usage Consumer**. Done.
3. Open the new account → **Keys → Add key → Create new key → JSON**. A file downloads.
4. Open that file in Notepad, copy everything, paste as the `EE_SERVICE_ACCOUNT_KEY`
   secret. Then delete the downloaded file.

If WeatherNext later fails with a permission error, the service account may
also need to be registered at https://code.earthengine.google.com/register for
the same project (noncommercial).

## 5. First run

**Actions → Collect, score and publish → Run workflow.** It takes a few minutes.
Open the log: the `collect` line shows how many Yr, WeatherNext and Frost rows
were saved and lists any errors. The first scores appear about a day later.

## 6. Bring in the existing history (once)

On your PC, in E:\WeatherApp (Claude Code can do this):

```powershell
.\.venv\Scripts\python.exe -m cloud.migrate_sqlite --db data\weather.db --until YYYY-MM-DD
```

Use the UTC date of the first cloud run for `--until`. It only reads the
database. Then commit and push the new files in `history/`.

## 7. Switch off the PC collector (after about a week)

Once the page looks right, run `remove_background_task.bat`. Keep
`data/weather.db` as an archive, or delete it once you're happy.

## Optional settings

**Settings → Secrets and variables → Actions → Variables**:

- `WEATHERNEXT_ENABLED` = `0` pauses WeatherNext collection.
- `WX_PUBLISH_FORECAST_VALUES` = `1` shows WeatherNext's raw values in the
  station chart. Read the WeatherNext real-time terms of use first.
