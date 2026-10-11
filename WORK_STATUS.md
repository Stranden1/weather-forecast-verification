# Work status

_The latest task's checkpoint only. Archive it in CHANGELOG.md when replacing it._

**Data note, 2026-10-11:** `data/weather.db` and its 7z archive were deleted and are lost (no
copy was made). The cloud `history/` is the only record.
See CHANGELOG.md.

## Consistent station names — 2026-10-12 (Claude)

**Done, committed, not pushed.**

- `cloud/summarize.py` `display_name()`: strips a trailing `[SNnnnnn]`, leaves mixed-case names alone,
  title-cases ALL-CAPS ones (E/FV road numbers, II/III, FPSO, A/B kept; "i"/"og" lowercase after
  the first word). Used for `name` and `county` in `meta.json` only; `config/stations.json` and
  `history/` untouched.
- Test `DisplayNameTest` (cloud/tests/test_sampling.py). Suite: 130 tests OK.
- Rebuilt `site/data/` and read all 50 names and counties: all fine. Browser check not done.
  `app.js` line 554 still strips `[SN..]` itself; harmless now.
