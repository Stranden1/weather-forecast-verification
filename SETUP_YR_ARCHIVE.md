# Simplified M1 Yr archive

_14 Oct 2026. Implemented and validated locally; disabled by default. Nothing pushed or enabled._

Owner approval and work order: REVIEW_2026-10-14.md. This implements its simplified M1,
which overrides the original plan's bucket, second key and durable-spool requirements.

## What it retains

- Full Locationforecast `complete` response bytes for the same active station network.
  The optional hook observes the existing requests before horizon extraction; it adds no
  normal weather requests. Raw JSON keeps every supplied field, 1h/6h/12h period, null,
  timestamp and numeric precision. No new scoring variables or observation vintages.
- UTC windows: **08:30–13:00** and **20:30–01:00 next day**, start inclusive/end exclusive.
  Each request must start and finish within its window. A collection starting outside
  the window does not capture, even if it later crosses the start. No schedule/gate change.
- First successfully published response per station per slot. Successful station objects
  are frozen; a later normal collection may fill missing stations during the same window.
  Attempts identify newly captured, late and missing stations. A network change inside
  a slot fails archive capture rather than silently changing its expected station set.
- After closure, the next collecting run writes an immutable complete/partial/missing
  manifest. If a whole window was missed, the expected network is explicitly labelled
  as the network at detection; past membership is not invented.
- Gzip then Fernet with the existing **WX_STATE_KEY**. All archive objects/manifests
  are encrypted. Request metadata excludes contacts, authorization, cookies and tokens.
  Existing history and state publication are separate.

Storage layout in the private repo:

```text
forecast/yr/v1/policy.json.gz.fernet
forecast/yr/v1/YYYY/MM/DD/am/index.json.gz.fernet
forecast/yr/v1/YYYY/MM/DD/am/yr/SN....json.gz.fernet
forecast/yr/v1/YYYY/MM/DD/am/attempts/<id>.json.gz.fernet
forecast/yr/v1/YYYY/MM/DD/am/manifest.json.gz.fernet
```

`pm` uses the date on which its window starts. Every response records its own request
and receipt times; Yr's `updated_at` stays in the raw response, without being relabelled
as model initialization. Multi-attempt slots are not one simultaneous network snapshot.

## Owner setup, while disabled

1. [Create a new repository](https://github.com/new), suggested name
   **weather-forecast-archive**, select **Private**, and turn **Add README** on.
   Its default branch must be **main**. Do not use the public weather verification repo.
2. [Create a fine-grained token](https://github.com/settings/personal-access-tokens/new).
   Choose your account as resource owner, **Only select repositories**, and select only
   the new archive. Give **Contents: Read and write**; Metadata read access is included.
   Pick an expiry and keep a renewal reminder. This is separate from the timer credential.
   [GitHub's token instructions](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
   explain repository-scoped access and permissions.
3. In **weather-forecast-verification → Settings → Secrets and variables → Actions**,
   save the token directly as a repository **secret** named **WX_YR_ARCHIVE_TOKEN**.
   Do not paste it into chat, Git, scripts or a report.
4. Add these repository **variables**:

   | Variable | Value |
   |---|---|
   | WX_YR_ARCHIVE_ENABLED | **0** until activation approval |
   | WX_YR_ARCHIVE_REPO | `Stranden1/weather-forecast-archive` (or the actual owner/name) |
   | WX_YR_ARCHIVE_START_AT | Agreed first nominal UTC window start, e.g. `2026-10-15T08:30:00Z` |

The start cutoff prevents missing records for windows before activation, including an
earlier morning when starting in the evening. It is stored in immutable archive policy:
do not change it after the first successful publication. Re-enabling later keeps that
cutoff so intervening missed windows remain visible.

The existing WX_STATE_KEY secret is reused; no second key or copy in the archive repo is
needed. The owner's independent key/history backup remains a separate outstanding action.

## Activation checkpoint

The code checks that the destination is a separate private repository with an active main
branch, then uses an isolated shallow clone. Only new authenticated encrypted archive files
may be committed. Pushes are normal fast-forward pushes; each new file is read back and
compared byte for byte. An unexpected tracked-file edit/delete or a conflicting object stops
archive publication. Repository privacy is checked on every enabled collecting run.

**Before deployment:** owner setup, review the local commits/workflow diff, and obtain explicit
approval to push and enable. Then set ENABLED to 1 and inspect the first two real windows:
49-station coverage, actual receipt times, immutable objects/manifests and unchanged main
scoring/health. No activation or GitHub push was performed during implementation.

Failures remain separate from the four collection sources. Archive errors cause the existing
final workflow check to fail **after** main history/state/health publication; safe counts are
also in `health.json.yr_archive`. They do not make the main collection gate count an archive
write as a successful weather source.

There is **no durable spool**. If push fails, the runner's unpublished responses are lost;
the next normal collection can acquire fresh responses within the window. If push succeeded
but confirmation failed, the next clone sees those already retained objects. An outage beyond
the window leaves missing/partial records when repository access recovers. A source response
is never recreated from scored history. Setting ENABLED back to 0 stops new archive work
without deleting any remote objects. Run checkouts are temporary and are cleaned up.

## Local evidence

All 171 cloud tests pass. Synthetic archive tests exercise encryption, exact raw bytes/precision, slot boundaries/cross-midnight/
timezone neutrality, evening activation, partial retry/frozen first responses, closed manifests,
interrupted writes, bad key/schema/token/gzip, header sanitization, disabled-path equivalence,
unchanged scored rows/request count/network, private-repo checks, local-Git uploads and readback,
upload failures and append-only guards. Tests use fixture keys and temporary bare remotes.

Two read-only acquisition pilots on 14 Oct at 20:02 UTC each captured all **49/49** stations
with zero collector/hook errors and exact encrypted readback. Each retained **4,364,232 raw
bytes**, **320,395 raw gzip bytes**, and **458,732 / 458,880 encrypted envelope bytes**, taking
**10.367 / 8.315 seconds**. At two batches/day that suggests about **0.335 GB/year** before
attempt/manifest overhead. These were back-to-back probes outside scheduled windows, not proof
of two operational slots or independent off-PC recovery. No full project backup was made.

Private pilot ciphertext and safe aggregate logs: `work/yr-archive-2026-10-14/` (ignored).
Full cloud test log: `cloud-tests.log` there. Real private-GitHub publication and independent
backup recovery still require owner setup/activation. The public scorecard needs no new UI test
for this additive archive sidecar.
