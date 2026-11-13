# Work status

## Review part C: Norwegian front page — 2026-11-13 (Claude)

Owner asked for part C in the same session as part A ("Da kan du ta C"). Two local commits on
top of part A's six, **not pushed**. Decision recorded in DECISIONS.md (13 Nov, decision 5).

**Done**
- `site/`: a simple front layer, Norwegian by default with a remembered NO | EN toggle and
  `Intl` number/date formats: verdict table with story sentences, forecast vs measured (Oslo
  first), day-by-day calendar, blend tip, frost icons, three fairness lines, sources and terms.
  Only the existing verdict names a winner. Every earlier card is unchanged behind
  "Vis kart, alle stasjoner og detaljerte tall" (`?visning=detaljert`), still in English.
- Status split: an "updated" line that turns amber only for a failed run, no run in 8 h, or a
  source failing twice in a row (new `health.json` → `failing`, tested); a neutral station line.
- Checked against the live public JSON (12–13 Nov) at 1280, 375 and 320 px in light and dark,
  plus English and the details layer: no horizontal overflow, no console errors, map and charts
  render. Screenshots: `work/front-page-2026-11-13/`. Amber cases checked with altered copies of
  `health.json`. 186 cloud tests pass. `tests/scorecard_ui_test.cjs` now opens the details; it
  passes up to its map-drag step, which times out the same way on the code before this change.

**Remaining:** owner looks at the screenshots and approves the push (with part A). Part B
(block bootstrap) and part D (hit rates, dumbbell) wait for their own sessions. The detailed
cards and the monthly text are not translated yet.
