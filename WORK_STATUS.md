# Work status

## Simplified M1 Yr archive (review task 2) — 2026-10-14 (Codex)

**Implemented and validated locally; disabled by default. No GitHub push, deployment or activation.**

### Done
- Encrypted create-only raw Yr objects, first-published per-station capture in 08:30–13:00 / 20:30–01:00 UTC windows, immutable attempt/closure manifests and explicit partial/missing slots. Activation cutoff prevents pre-activation missing records; no durable spool.
- Optional raw-response hook preserves normal scored rows/network/request count. Separate private-Git transport checks privacy, scopes credentials, allows only new encrypted files, performs normal pushes and verifies new remote bytes. All tests publish only to temporary local remotes.
- Same WX_STATE_KEY; sanitized request metadata and exact JSON bytes retain all supplied fields/precision. Scoring, retained history, state persistence and schedule unchanged. Archive errors are separate, with safe health counts and the final workflow check after main publication.
- All 171 cloud tests pass; focused tests cover policy/crypto, failed hooks/uploads/readback, frozen partial retries, private-repo guards and main gate independence. Logs: work/yr-archive-2026-10-14/.
- Two read-only 49/49-station acquisition probes: zero collector/hook errors, exact encrypted readback, ~0.459 MB each, 10.367/8.315 seconds. Back-to-back outside production windows; operational slot capture remains unverified. Raw pilot output is encrypted and ignored.
- SETUP_YR_ARCHIVE.md gives the owner private-repo/token/variable steps and the concrete activation checkpoint. Core writer/policy stage committed as 1b722ef; integration/configuration checkpoint committed as 4df6b34. Previous scorecard checkpoint preserved atop CHANGELOG.md.

### Remaining
- Owner creates an initialized private archive repo and repo-only push credential; save it directly as WX_YR_ARCHIVE_TOKEN in the public project's Actions secrets. Keep WX_YR_ARCHIVE_ENABLED=0.
- Agree the first nominal UTC cutoff, verify private setup, then obtain explicit push/activation OK. Inspect two real cloud slots and unchanged main scoring after activation. Independent key/history recovery remains an owner action.
- Tasks 3–5 await their own sessions; no comparison/pressure study or plan consolidation started.

**Protected:** history day files, site/data, public UI, model network, pending/scoring rules, secrets and scheduling. Existing deprecation warnings remain. No production state mutation or full project backup.
