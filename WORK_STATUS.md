# Work status

## Cloud reliability and encrypted history — 2026-09-28 (Codex)

Done:
- Read DECISIONS/PLAN_WEBPAGE; used current model and a separate read-only reviewer
  with user approval because Claude Opus was unavailable.
- Pulled only the two newer scored-day commits (base be13ed1), preserving review notes.
- Encrypted all 23 current day files with the existing key. Exact original gzip
  bytes and all 126,109 rows verified; 58 generated page JSON files unchanged
  except generation time. Local decrypt documented in SETUP_CLOUD.md.
- Day preparation requires >=80% configured station-hour coverage, retries to
  UTC day-end +72h, then records coverage/late_finalized. Metadata is written
  before the day; pending forecasts stay until exact origin confirmation.
- Restore starts fresh only for an absent branch; clone/decrypt/schema errors
  abort. History is pushed first, confirmed in origin, then exact days are pruned
  and encrypted state is pushed with a lease. Source errors are reported after saves.
- Failure tests cover missing observations, boundaries/timeout, interrupted file
  writes, failed restore/history push, interruption between pushes, retry, and leases.
- Validation: 154 local/cloud tests pass. HQ: 7 pass, 1 Windows symlink skip.
- Handoff/policy/setup docs updated. Completed locally for review; no push. See Git log for the commit.

Remaining:
- User review before push; then validate the first deployed run and cloud/local coverage.
- Old plaintext Git commits/caches remain publicly retrievable. Current-file
  encryption does not erase them; coordinated historical cleanup remains necessary.

No data/weather.db, local collectors, secrets or running scheduled tasks changed.
Evidence: work/reliability-tests.txt and work/history-encryption-validation.json.
