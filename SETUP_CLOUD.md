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
| `WX_STATE_KEY` | The existing Fernet key, also held in local `.env`; keep a separate secure backup |

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

**Actions → Collect, score and publish → Run workflow.** Leave `trigger` at its
default `manual` to bypass the 150-minute gate. It takes a few minutes.
Open the log: the `collect` line shows how many Yr, WeatherNext and Frost rows
were saved and lists any errors. The first scores appear about a day later.

## 6. Bring in the existing history (once)

On your PC, in E:\WeatherApp (Claude Code can do this):

```powershell
.\.venv\Scripts\python.exe -c "from dotenv import load_dotenv; load_dotenv('.env'); from cloud.migrate_sqlite import main; main()" --db data\weather.db --until YYYY-MM-DD
```

Use the UTC date of the first cloud run for `--until`. It only reads the
database. Then commit and push the new files in `history/`.

## 7. Switch off the PC collector (after about a week)

After validating cloud/local coverage and the deployed recovery fixes, stop the
Windows collector only with the user's approval. Keep authoritative `data/weather.db`.

## External timer (optional)

After the updated `collect.yml` is on `main`, configure an independent timer to send
the following request every 30 minutes (for example, at :07 and :37 UTC):

```http
POST https://api.github.com/repos/Stranden1/weather-forecast-verification/actions/workflows/collect.yml/dispatches
Accept: application/vnd.github+json
Authorization: Bearer <token>
Content-Type: application/json

{"ref":"main","inputs":{"trigger":"timer"}}
```

Expected response: **204 No Content** (dispatch accepted; check Actions for the run
result). Use a **fine-grained personal access token**, restricted to
`Stranden1/weather-forecast-verification` only, with repository permission
**Actions: Read and write**. Store the real token only in the timer's secret store;
never put it in documentation, source files or logs. `<token>` above is a placeholder.

`trigger: timer` respects the same 150-minute gate as scheduled runs: a recent
successful collection skips collection, state publication and Pages deployment.
`trigger: manual` bypasses the gate and is the default. The hourly GitHub schedule
(`23 * * * *`) and shared `collect` concurrency group remain enabled.

### Recommended setup and verification

GitHub's scheduled events can be delayed or dropped; changing the cron time alone
does not guarantee collection. An independent service such as
[cron-job.org](https://cron-job.org/en/) can send the POST while the PC is off.

1. Create one job named **WeatherApp collection timer** with the URL, POST method,
   headers and JSON body above. Use UTC and minutes 7 and 37 of every hour, every day
   (`7,37 * * * *`). Keep this separate from the unchanged GitHub hourly cron.
2. Enter the repo-only GitHub token directly in the service's Authorization header
   setting. Never paste it into chat or a tracked file. Record its expiration date
   in your password manager so it can be renewed before dispatches stop.
3. Enable notifications for failed requests and automatic job disabling, and verify
   that the job is enabled. A timer test should return **204**, not an HTML page.
4. Check the resulting GitHub Actions run. When the last successful collection is
   under 150 minutes old, the Gate log must say `skip`, with collection, publication
   and deployment steps skipped. Once due, those steps must run successfully.
5. Check the public health timestamp advances after collection. A 204 only confirms
   GitHub accepted the request; it does not confirm the workflow or collectors succeeded.

To test the timer path with an already-authenticated GitHub CLI after deployment:

```powershell
gh workflow run collect.yml --repo Stranden1/weather-forecast-verification --ref main -f trigger=timer
```

Common failures: **401** means the token is invalid/expired; **403** requires checking
repository access, Actions permission and rate-limit information; **404** requires
checking the endpoint and token's repository access; **422** can mean the deployed
workflow does not yet accept `trigger`, or the ref/input is invalid. Do not send
`trigger=timer` until the updated workflow is on `main`.

The 30-minute requests are wake-up attempts, not collections. With prompt starts,
the gate allows collection roughly every 150-180 minutes; delayed GitHub execution
can still extend that. Keep the PC collector until measured cloud coverage matches.

References: [GitHub schedule limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule),
[cron-job.org request and notification settings](https://docs.cron-job.org/rest-api.html).

## Optional settings

**Settings → Secrets and variables → Actions → Variables**:

- `WEATHERNEXT_ENABLED` = `0` pauses WeatherNext collection.
- The public workflow forces `WX_PUBLISH_FORECAST_VALUES=0`. Keep this policy
  until publication of the underlying values is explicitly resolved.

## Encrypted history and local decryption

Both state and `history/YYYY/YYYY-MM-DD.csv.gz` hold Fernet ciphertext under
`WX_STATE_KEY`. The suffix is retained for compatibility; the files are not directly
readable gzip until decrypted. CI requires the key, decrypts in memory, and builds
only aggregate WeatherNext exports. Keep the existing key backed up: it now protects
scored history too. These commands use the existing `.venv` and never print the key:

```powershell
.\.venv\Scripts\python.exe -m cloud.history_crypto verify --env-file .env
.\.venv\Scripts\python.exe -m cloud.history_crypto decrypt --env-file .env --out outputs\decrypted-history
```

Decryption creates local gzip copies only in ignored `outputs/`; it refuses to
overwrite existing copies. Use a fresh outputs subdirectory on subsequent runs.
Never publish those copies. `cloud.store.load_scored()` reads encrypted history
directly when the key is in the environment. Local migration can be invoked with
the key loaded without displaying it:

```powershell
.\.venv\Scripts\python.exe -c "from dotenv import load_dotenv; load_dotenv('.env'); from cloud.migrate_sqlite import main; main()" --until YYYY-MM-DD
```

One-time storage conversion (preserves original compressed bytes; safe to repeat):

```powershell
.\.venv\Scripts\python.exe -m cloud.history_crypto encrypt --env-file .env
```

**Existing public Git history:** changing current files does not remove plaintext
from earlier commits, tags, pull-request refs or cached copies. Before claiming the
repository contains no publicly retrievable raw WeatherNext data, plan a coordinated
history rewrite and host/cache cleanup. Do not force-push main as an ordinary deploy.
The 28 Sep task prepares and commits the current-file protection locally; it does
not perform a historical rewrite or push.

## Recovery and deployment checks

- Only `ls-remote` status 2 for an absent state branch permits initialization.
  Clone, authentication, missing-file, schema or decrypt errors abort without a push.
- Prepared days retain pending forecasts. History is pushed first, fetched back and
  compared with local encrypted blobs/metadata; only confirmed days may be pruned.
- An interruption after history push leaves old remote state intact. Rerun the job:
  it reads existing days and their original coverage sidecars, then safely reconciles
  state. State pushes use a lease, so a newer remote snapshot cannot be overwritten.
- After deployment, verify all sources, encrypted history/state, per-day coverage in
  state meta, and Pages health. Source errors fail the final status step after successful
  data and the health page are saved. Do not add `--strict` to the collection step.
