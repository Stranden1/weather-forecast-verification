# Work status

## Review part B: block bootstrap for the verdict test — 2026-11-13/14 (Claude)

Owner asked for part B ("Da kan du gjøre plan B"), saw the before/after table and approved the
commit (14 Nov). One code commit (6446f9a) plus this handoff, **not pushed**; with parts A and C
that is 13 local commits. Recorded in DECISIONS.md and SCORING.md (13 Nov).

**Done**
- `summarize.bootstrap_diff` resamples blocks of **4 consecutive scored days** (circular block
  bootstrap, `BLOCK_DAYS`; `block_indices`). Same 2000 resamples, seed and 95 % rule. Scores,
  pairing, cohorts, thresholds and the blend are unchanged.
- Block length from the autocorrelation of the daily WeatherNext − Yr difference on all 69 days
  (5 Sep–12 Nov, read from a copy of origin's `history/`): median lag-1 0.34, 0.34–0.51 for
  temperature/wind up to 3 days; the AR(1) plug-in rule gives 3.4–4.2. Fixed before comparing
  verdicts.
- Before/after on the full export: 3 of 130 exported verdicts and 2 monthly cells change
  (table in DECISIONS.md). Nothing else in the export changed.
- 13 new tests (`cloud/tests/test_bootstrap.py`); 199 cloud tests pass.
- Owner chose to leave the blend test (`bootstrap_gain`) on single days.

**Remaining:** owner approves the push of parts A, B and C. Part D (hit rates, dumbbell) waits for
its own session. Analysis scripts: `work/block-bootstrap-2026-11-13/` (git-ignored).
