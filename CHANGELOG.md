# Changelog

## Push and Yr archive activation — 2026-10-14 (Claude)

- Rebased the scorecard, map-sentence and Yr archive commits onto `origin/main`; `history/` byte-identical to origin. 171 cloud tests pass. Pushed to `main` (09abaf0, owner OK); CI tests and collect run 38641643498 succeeded; live page matches `site/` and shows the new design.
- Owner fixed setup: `WX_YR_ARCHIVE_REPO=Stranden1/yr-archive` (private, README on `main`). Secret `WX_YR_ARCHIVE_TOKEN` present (not read). `WX_YR_ARCHIVE_START_AT=2026-10-15T08:30:00Z`.
- Set `WX_YR_ARCHIVE_ENABLED=1` at 21:54 UTC (owner OK). Manual collect run 38643799647: all steps success. `health.json.yr_archive`: enabled, status idle, 0 captured, 0 errors, published. Archive repo got one bot commit with only `forecast/yr/v1/policy.json.gz.fernet`. Main health unchanged: yr 1323, wn 2352, ecmwf 4606, frost 5594 rows, 0 errors each.

**Remaining:** inspect the first two real windows (15 Oct 08:30–13:00 and 20:30–01:00 UTC): 49/49 stations, slot index/manifest objects, 0 archive errors, unchanged main health. To stop, set ENABLED=0 (remote objects stay).

## Map sentence: both land counts — 2026-10-14 (Codex)

- Updated the generated sentence to show both Yr and WeatherNext land counts. Offshore unanimity reads “WeatherNext lower at all 13”; ties are explicitly counted when present. Existing eligibility, period/horizon filters and descriptive-only caveat remain.
- Browser checks at 1280/375/320 px in light/dark, JS syntax and whitespace checks pass. Evidence: work/map-counts-2026-10-14/. Committed locally; no push.
- Waiting for the owner to complete SETUP_YR_ARCHIVE.md and explicitly authorize push/activation. Archive remains disabled. Implementation commits: 1b722ef and 4df6b34; setup checkpoint: 11281fc. Prior archive checkpoint is preserved atop CHANGELOG.md.

No scoring, station-network, history, secrets, collector, archive or scheduling change.

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

## Scorecard revisions (review task 1) — 2026-10-14 (Codex)

**Complete, validated and committed locally (`944cd2d`). No push or deployment.**

### Done
- Finished the journal style across all sections, including expanded analysis/month/methodology; kept the earlier critique and map refinements.
- Added the supported blend finding, published-first horizon styling, selected-period land/offshore counts, height/lake caveats, intact replay attribution footnotes and repository footer link. Wholly empty sections hide.
- Added station offshore metadata from the existing classification; unknown remains null and is omitted from grouped counts. Scores and station membership unchanged.
- Passed 143 cloud tests and 1280/375/320 light/dark browser checks, including real fonts/tiles, expanded lower sections, empty-data cases and the prior interaction regressions. JS syntax and Git whitespace checks pass. Evidence: work/scorecard-revisions-2026-10-14/.
- Copied owner decisions to DECISIONS.md and updated current handoffs. Prior checkpoint preserved atop CHANGELOG.md. Existing plan/review documents retained as supplied.

### Remaining
- Next session: task 2, simplified M1 Yr archive, disabled-by-default validation first; enable only with owner OK. Tasks 3–5 remain in the review order. No archive implementation started here.
- Public deployment and independent owner key/history backup remain pending.

**Protected:** history, site/data, scoring/pairing, collectors, shared station network, secrets and scheduling unchanged. No live-health audit. Existing deprecation warnings remain.

## Smaller zoomable station markers — 2026-10-14 (Codex)

**Requested map refinement complete and validated locally. Prototype remains uncommitted; not pushed/deployed.**

### Done
- All station markers are round: 8 px at overview, growing gently up to 12 px with zoom. Thin outlines and smaller missing-measurement rings reduce crowding. Separate transparent 24 px click areas, accessible labels and Enter/Space selection remain.
- Mouse-wheel zoom enabled; button/pinch zoom and panning retained, with a short hint. Colours, equal/missing-data legend, station selection, cohorts and scores unchanged.
- Passed browser regression checks at 1280/375/320 px in both themes with real fonts/tiles: overview/regional views, marker scaling, panning, button/desktop wheel zoom, keyboard markers, themes, filters, charts/tables, no page overflow or captured JS errors. JS syntax and Git whitespace checks pass. Cloud code is unchanged; its 143 tests last passed on 13 Oct.
- Latest screenshots and browser-tests.log: work/scorecard-map-refinement-2026-10-14/. Reused isolated read-only public fixtures. Preview servers stopped; no live-health audit.

### Remaining
- Owner direction approval before extending the prototype to the other sections. After that work, repeat relevant checks and commit validated steps; do not push. Other open work stays in NEXT_STEPS.md.

**Protected:** history, site/data, scoring/pairing, collectors, shared station network, secrets and scheduling unchanged. Existing review documents untouched. Previous checkpoint archived atop CHANGELOG.md.

## Smaller zoomable station markers — 2026-10-14 (Codex)

- Replaced the 16 px circles/squares and heavy outlines with round 8 px overview dots and thin outlines. Dots grow gently with zoom, capped at 12 px; missing-measurement rings shrink accordingly. The separate 24 px transparent click area and keyboard labels/Enter/Space remain.
- Enabled mouse-wheel zoom, retained pinch/button zoom and panning, and added a short zoom hint. Provider colours, equal/missing-data meanings, selection, periods and descriptive comparisons are unchanged. The owner's preference supersedes the previous circle/square styling.
- Browser regression checks passed at 1280/375/320 px, both themes, with real fonts/tiles: overview and regional zooms, panning, desktop wheel/button zoom, marker sizing, keyboard selection, theme/filter/chart/table checks, and no page overflow or captured JS errors. Screenshots/log: work/scorecard-map-refinement-2026-10-14/. Reused read-only public fixtures; cloud code is unchanged, with 143 cloud tests last passed on 13 Oct.
- Handoffs updated. Prototype remains uncommitted; no push/deployment, history/data/scoring, collection, station network, secrets or scheduling changes. Existing review documents untouched.

## Previous critique-fix checkpoint — archived 2026-10-14

## Scorecard critique fixes — 2026-10-13 (Codex)

**Requested fixes complete and validated locally. Prototype remains uncommitted; not pushed/deployed.**

### Done
- Fixed mobile filter overlap; 44 px filter/zoom targets. Station and horizon selectors are together, with a wrapping legend below the map.
- Solid blue circles/orange squares show lower observed error; solid neutral means equal error, hollow means no paired data. Enter/Space select map stations. Percentages visibly say “lower error”; height adjustment is explained in station details.
- Theme follows the system until chosen, updates on system changes, names its next action and saves explicit choices. Tidied small type/corners, moved dates beside the verdict context, added a confirmed-verdict text/rule cue, removed redundant Stations navigation and softened warning styling. The existing eight-hour stale threshold is preserved.
- Passed 143 cloud tests and browser checks at 1280/375/320 px in light/dark with real fonts/tiles, zero page overflow/captured JS errors, unobstructed zoom, theme persistence, filters, station charts/tables, keyboard markers, height explanation and synthetic equal/missing/winner/tie cases.
- Evidence: work/scorecard-review-fixes-2026-10-13/ (screenshots, browser-tests.log, cloud-tests.log). Reused the isolated read-only public fixtures in work/scorecard-direction-2026-10-13/data. Preview servers stopped; no live-health audit.

### Remaining
- Owner direction approval before extending the prototype to events, horizons, replays and detailed analyses. Hide wholly empty sections and consolidate methodology while preserving controls, tables, disclosures and attribution.
- After the remaining design work, repeat relevant checks and commit validated steps; do not push. Operational/private-viewer items remain in NEXT_STEPS.md.

**Protected:** history, site/data, scoring/pairing, collectors, shared station network, secrets and scheduling unchanged. Existing untracked review documents untouched. Previous checkpoint archived atop CHANGELOG.md.

## Scorecard critique fixes — 2026-10-13 (Codex)

- Fixed mobile filter/map overlap by making filters scroll with the page below 761 px. Filters and map zoom controls have 44 px touch targets.
- Station selectors sit together; the legend is below the map. Full-strength provider colours and circle/square markers distinguish lower error; solid neutral means equal error, hollow means no paired data. Markers support Enter/Space and have descriptive accessible labels. Local differences remain descriptive, without station winner claims.
- Percentages visibly say “lower error”; height adjustment is explained in station details. Dates now precede the headline; a heavier rule and text cue appear only for an existing confirmed provider verdict. Removed the redundant Stations navigation link.
- Theme defaults to the system until explicitly chosen; the button names its next action, system changes update unchosen themes, and choices persist. Added 12 px eyebrow/13 px metadata tokens, square interface corners and a quieter health warning; the existing eight-hour stale threshold is unchanged.
- Validation passed: 143 cloud tests; browser checks at 1280/375/320 px in both themes with real fonts/tiles, no page overflow or captured JS errors, uncovered zoom, theme persistence, station charts/tables, keyboard markers, height explanation, and synthetic equal/missing/winner/tie cases. Evidence: work/scorecard-review-fixes-2026-10-13/. Sandbox temp/local-Git limitations were resolved using workspace temp fixtures and an approved test run; existing dependency warnings remain.
- No history, site/data, scoring, collection, station network, secrets, schedule, push or deployment changes. Prototype remains uncommitted; remaining-section redesign awaits direction approval.

## Previous direction checkpoint — archived 2026-10-13

## Public scorecard direction prototype — 2026-10-13 (Codex)

**Prototype complete; awaiting owner approval. Uncommitted, not pushed/deployed.**

### Done
- Read AGENTS.md, the prior checkpoint, DECISIONS.md and PLAN_WEBPAGE.md; checked Git. The existing untracked REVIEW_2026-10-11.md and REVIEW_2026-10-11_codex.md are untouched.
- Changed presentation in site/index.html, style.css and app.js for the opening and “Where the errors differ” only. Weather-journal identity, serif headline verdict, prominent blue Yr/orange WeatherNext values, blend in details, paper light default and saved dark-mode control.
- Moved the station section directly below the opening; map imagery matches the theme and provider colours stay exact. Empty comparison lists and missing station chart/table disappear; station-map methodology is in “How to read this fairly”. Other sections retain their current layout.
- Previewed with the existing .venv and python -m http.server 8765 --directory site, loopback only. Existing site/data lacks views.json, so screenshots used a read-only history export in an isolated ignored work/ fixture; no existing data files were changed.
- Browser checks pass at 1280/375/320 px in both themes: zero horizontal overflow and captured JS errors, scores stay side by side, actual fonts/tiles loaded, filters/station chart/table work, keyboard focus/selection and theme persistence pass.
- Screenshots and validation.json: work/scorecard-direction-2026-10-13/. Numbers remain Yr 0.91 vs WeatherNext 0.92 °C, “Too close to call.” The preview server is stopped.

### Remaining after approval
- Apply the approved direction to events, horizons, replays and detailed analyses; hide wholly empty sections and consolidate remaining methodology while preserving controls, disclosures, tables and required nearby attribution.
- Refine chart styling and verify every existing feature at phone width in both themes. Run the full cloud suite and appropriate browser regression checks, then commit validated steps and update changed handoffs. Do not push.
- The design direction is a proposal, not a final DECISIONS.md rule yet.

**Protected:** no scoring/pairing, Python pipeline, site/data, history, station network, secrets, scheduled tasks, push or deployment changes. Prior private-viewer and operational follow-ups remain in NEXT_STEPS.md; the prior handoff is archived atop CHANGELOG.md.

## Public scorecard design prototype — 2026-10-13 (Codex)

- Prototyped the hero and station section only: weather-journal masthead, Newsreader/DM Sans typography, paper light default, explicit saved dark mode, headline verdict, two prominent provider scores, blend/supporting scores in a disclosure, and map-led station comparisons.
- Map imagery adapts to the theme while provider marker colours remain unchanged. Empty comparison lists and missing station charts/tables are hidden. Map methodology moved into the existing fairness disclosure.
- Browser validation: 1280/375/320 px, light/dark, no page overflow or captured JS errors; side-by-side values, fonts, real map tiles, filters, station selection/table, keyboard focus and saved theme checked. Public-data screenshots and validation.json are in ignored work/scorecard-direction-2026-10-13/.
- Read-only history export went to an isolated preview fixture; existing site/data, history, pipeline, scoring, pairing, secrets and scheduling were unchanged. The two pre-existing untracked review documents were untouched.
- Stopped at the requested direction-approval checkpoint. Prototype remains uncommitted; the full redesign, full test suite and validated commits await approval. No push or deployment.

## Previous private-viewer handoff — archived 2026-10-13

## Private forecast comparison — 2026-10-12 (Codex)

**Complete and validated locally on `codex/scorecard-corrections`; not pushed/deployed.**

### Done
- Owner chose a private forecast UI. `private_forecast/` reads fetched encrypted cloud state in memory and serves only on loopback; no retired database or collector required.
- Active stations, 24/48-hour windows, temperature/wind/precipitation, same-fetch comparisons, ranges, honest gaps, issue ages, median rain, largest-gap shortcut, tables and both themes.
- Private data/access controls: no credential delivery, caching, external assets, state/history writes or public export. No capture expansion or scheduling change.
- Eight private tests pass; the existing 143 cloud tests also pass. Browser checks pass at 1280/375/320 px in light/dark, including missing-hour line/range breaks, missing providers, rain median, empty stations, keyboard selection and prominent mobile values. No captured JS errors or page-wide overflow.
- Private screenshots, validation.json and aggregate disagreement.json are in ignored `work/forecast-comparison-2026-10-12/`; never publish future-value screenshots. The validation server is stopped.
- PRIVATE_FORECAST.md gives launch instructions; FORECAST_PLAN.md gives evidence, ranked next work and the proposed finish line. Earlier scorecard checkpoint is archived atop CHANGELOG.md.

### When returning
Review the private viewer; see Git log for its local checkpoint. Earlier scorecard commits are now on `origin/main` at `39c2617`, with CI passed. At 15:10 UTC the live page was still the previous version: run 38267891738 gated/skipped collection and deployment. Verify the next actual deployment. This new viewer has not been pushed or deployed; this task performed neither action.

The private timeline intentionally has gaps: current cloud capture saves scoring windows. Approve prospective bounded 48-hour capture before collector changes, then choose fixed daily/night scope. Daily extrema/totals cannot be recovered from lost full local runs or inferred from incomplete timelines.

Rain-probability reliability and IFS/AIFS views remain proposals using retained data. Then collect through winter and review occasionally; more station/variable counts are lower priority. Operations still need the 19 Oct runner check, before-5-Nov token renewal and independent history/key recovery confirmation (NEXT_STEPS.md).

**Data:** cloud history is the only retained record; keep it and WX_STATE_KEY safe. No history edits, push, workflow dispatch, secret rotation or collector changes in this task.

## Private forecast comparison and finish plan — 2026-10-12 (Codex)

- Owner chose an internal side-by-side prediction UI. Added `private_forecast/`, independent of the retired database/collector; read-only encrypted cloud state on loopback, no external assets or collection.
- Same-fetch provider comparison, original issue times, 24/48-hour windows, active stations, temperature/wind ranges, median precipitation, honest gaps, numeric tables, largest-gap navigation and both themes. Local state is re-read once a minute for ages/expired targets; GitHub refresh remains explicit.
- Host/Origin checks, explicit asset allowlist, no caching or credential/error disclosure; no plaintext forecast export. Public site and its future-value gate are unchanged.
- Validated 8 private data/access tests and all 143 cloud tests. Playwright/Chrome passes at 1280/375/320 px in both themes, no captured JS errors or page-wide overflow, plus gap/median/missing-provider/empty-station checks. Evidence stays private in ignored `work/forecast-comparison-2026-10-12/`.
- A 13:37 UTC snapshot across 49 stations had typical next-two-day shared-hour gaps of 0.66 °C and 1.36 m/s; wet/dry disagreement was 8.9%. Prediction disagreement is not measured error. Current saved timelines are incomplete.
- Added PRIVATE_FORECAST.md launch/check instructions and FORECAST_PLAN.md ranked scope: complete bounded 48-hour capture, fixed daily verification, probability reliability, existing four-model data, then winter reviews/maintenance.
- Complete capture remains a proposal; no collectors, history, secrets, workflows or deployed settings changed. No push/deploy. The test server was stopped after validation.
- Separately observed the earlier scorecard commits on origin/main at 39c2617, with CI run 38266975312 passed. The 15:07 UTC collect run 38267891738 skipped downstream steps; the 15:10 UTC live page/health still reflected the previous version. Verify the next real deployment. This task did not push those commits.

## Scorecard corrections and presentation — 2026-10-12 (Codex)

**Complete and validated locally on `codex/scorecard-corrections`; not pushed or deployed.**

### Checkpoints
- `3373c75`: UTC rain-day totals/events and final-hour publication gate; 132 tests passed.
- `d1f9669`: consistent rain medians, calendar periods and matched uncertainty across statistical views; 140 tests passed.
- Final presentation/events checkpoint: concise answer, optional detail, accessible station selector/chart tables and event detection with land/offshore groups; 143 tests passed. See Git log for its commit.

### Verification
- Existing .venv; all 143 cloud tests pass. Real-history rebuild: 37 days, 224,292 rows; JSON 936,986 bytes. No history changes.
- Browser smoke check passes at 1280, 375 and 320 px in both themes, including filter/rain consistency, all-station selection and single-point replays. No captured JS errors or page-wide overflow.
- Phone answer y=409 px, first tile y=547 px, collapsed height 5,332 px versus previous ~10,085 px. Screenshots and validation.json: `work/scorecard-2026-10-12/` (ignored, retained).
- Prepared Wisting retirement predates this branch. Revsbotn resumed 10-minute observations at 11:40/11:50 UTC on 12 Oct; kept active. Scores can lag current recovery.
- All encrypted history files decrypt using the current key. A separate backup/restore from an independent key copy has NOT been verified.

### When returning
Review this branch against `main`, then publish if satisfied; include/rebase any new scored-history commits first. No push, workflow dispatch, secret rotation, collector change or new data capture was performed.

Choose additional collection separately: coherent daily runs, observation quality/provenance and alternative WeatherNext rain fields. IFS/AIFS and Yr probability views remain proposals. See NEXT_STEPS.md for the 19 Oct runner and before-5-Nov token work.

**Data:** the PC collector is retired; weather.db and archive are lost. `history/` is the only retained record; protect `WX_STATE_KEY` independently.

## Scorecard corrections: presentation and events checkpoint — 2026-10-12 (Codex)

- A concise one-day answer and compact tiles lead the page. Monthly prose, forecast changes, bias, trends, uncertainty and methodology remain available in disclosures.
- Added descriptive threshold detection from existing history: air temperature <0 °C, mean wind >=10 m/s, precipitation >0.1 mm/h (water equivalent). Shared-hour catches, misses, false alarms and event-only error are shown for all/land/offshore, by horizon and selected period. No event winner verdicts.
- Every active station is reachable through a keyboard-accessible selector; trend/station/replay charts have data tables. Controls have honest group semantics; light muted-text contrast improved; tiny uncertainty endpoints retain enough decimals to explain verdicts.
- Healthy collection is compact with expandable source details (including ECMWF); station warnings explicitly refer to finalized history, not current recovery.
- Validated 143 cloud tests and the reusable `tests/scorecard_ui_test.cjs`: light/dark at 1280, 375 and 320 px; rain/filter consistency, station selection, one-point measured references, no captured JS errors or page-wide overflow. Real-history JSON is 936,986 bytes for 224,292 rows.
- Mobile answer at y=409 px, first tile y=547 px, collapsed page height 5,332 px (previous live height ~10,085 px). Desktop height 3,548 px. Screenshots retained in ignored `work/scorecard-2026-10-12/`.
- Updated retired-PC and publication guidance. History, collectors, encryption keys, workflows and deployed settings remain unchanged. Local branch only; publication awaits review.

## Scorecard corrections: periods and rain checkpoint — 2026-10-12 (Codex)

- Added `views.json`: period-scoped map, trends, Patterns, bias, rain detection, matched uncertainty and steadiness. Legacy exports remain compatible.
- Rain views use the median on common available hours, never silently substitute the mean; recent series include gated hourly medians.
- Last 30 days means the final scored UTC target date plus the preceding 29 calendar days. Trends include missing calendar dates, stop lines at gaps, and offer a data table.
- Station differences are labelled descriptive; station/replay requests cannot overwrite newer filter selections. Station outage text identifies finalized-history scope.
- Validated 140 cloud tests; real-history rebuild 224,292 rows (new views 224,720 bytes); browser checks pass for rain, dates, gaps and selection changes, with no JS errors or mobile overflow.
- Local checkpoint only. Next: compact first answer, keyboard/data accessibility and practical event comparisons.

## Scorecard corrections: rain checkpoint — 2026-10-12 (Codex)

- Corrected UTC rain-day selection to interval ends 01:00 through next midnight; raw history untouched.
- Publication gate now waits until the final midnight interval is at least one hour old.
- Replays label sums of hourly medians accurately and show the measured point when only one horizon exists.
- Validated 132 cloud tests, including midnight-boundary regressions; real-history export reads 224,292 rows.
- Work is on local branch `codex/scorecard-corrections`; publication pending. Next: rain metrics/date scopes and first-screen clarity.

## Retire Wisting (SN20925) — 2026-10-12 (Claude)

**Done, committed, not pushed.**

- Frost returns 404 for SN20925 (source, time series and observations; name search finds nothing;
  Alvheim works with the same credentials). Last measurement 30 Sep 21:00 UTC. No renamed
  successor nearby (Hjelmsøybanken II SN20924 is 3° further west, a different site).
- `config/stations.json`: `"active": 0` for SN20925, nothing else changed.
- Checked on a rebuild from history, with and without the change: `rows` 224292 and `days` 37
  unchanged; leaderboard identical (1 day temp: n 25438, Yr 0.914, WeatherNext 0.917);
  `stations.json` still has SN20925's scores; `meta.json` 49 stations (Wisting gone). Page: 49
  markers, no console errors. `history/` tree hash unchanged. Tests: 130 OK.
- New on the page: Revsbotn - Danielsvika has been silent since 9 Oct (see NEXT_STEPS item 1).

## Consistent station names — 2026-10-12 (Claude)

**Done, committed, not pushed.**

- `cloud/summarize.py` `display_name()`: strips a trailing `[SNnnnnn]`, leaves mixed-case names alone,
  title-cases ALL-CAPS ones (E/FV road numbers, II/III, FPSO, A/B kept; "i"/"og" lowercase after
  the first word). Used for `name` and `county` in `meta.json` only; `config/stations.json` and
  `history/` untouched.
- Test `DisplayNameTest` (cloud/tests/test_sampling.py). Suite: 130 tests OK.
- Rebuilt `site/data/` and read all 50 names and counties: all fine. Browser check not done.
  `app.js` line 554 still strips `[SN..]` itself; harmless now.

## Consistent station names — 2026-10-12 (Claude)

`display_name()` in `cloud/summarize.py` tidies station names and counties in `meta.json`
(ID tag removed, ALL-CAPS to Norwegian title case). Test added; 130 tests pass.

## Station freshness warning — 2026-10-11 (Claude)

**Done and pushed 2026-10-11 (5710d38).** Step 4, the last step, of the dashboard plan
(AgnosticBrain `plans/weatherapp-dashboard.md`, now done).

- Export (`cloud/summarize.py`): each station in `meta.json` gains `last_obs`, the latest scored
  hour with any measurement (temperature, wind or rain), or null if it never reported. Test added.
- Page (`site/app.js` `silentStations()`): a station is "without measurements" when `last_obs` is
  more than 48 h (`NO_OBS_H`, decision 4) before the end of `meta.last_day`. Stations that never
  reported are left out (the map already says "No data yet").
  - Health line: "1 station has no measurements since 30 Sept (WISTING [SN20925])", which turns the
    line into a warning. Several stations: "N stations have no measurements for over 2 days",
    names listed up to 3.
  - Map: a grey ring around the marker (separate outer circle, fixed #5f5f5f because the OSM tiles
    are light in both themes; a dashed border on the dot was tried first and was hard to see).
    Tooltip and station details say since when. The map's legend line mentions the ring.
- Live history now: only Wisting (SN20925, Barents Sea) is silent, last measurement 30 Sep 21:00 UTC.
  Enningdalen (SN1120) has recovered (10 Oct 23:00).
- Map default view (follow-up, same day): the map now fits all stations instead of a fixed
  centre/zoom, so Wisting (73.5° N) shows without zooming out. Quarter zoom steps (`zoomSnap`
  0.25); bottom padding = attribution bar height + 12 px (it wraps to two lines on a phone).
  Leaflet adds the tile layer only once the map has a view, and a fit before that came out a
  quarter step too tight, so the map gets a rough `setView` first, then `fitBounds`. Checked at
  375, 768 and 1400 px: all 50 stations inside the map and clear of the attribution bar.
- 129 cloud tests pass. Checked in the browser with data rebuilt from history: health line,
  ring, tooltip, station details; no console errors.

Next: plan finished. NEXT_STEPS item 5 (rain median on the remaining views) or ECMWF on the page.

## "Biggest differences" in the map panel — 2026-10-11 (Claude)

**Done and pushed 2026-10-11 (8cf486c).** Step 3 of the dashboard plan (AgnosticBrain
`plans/weatherapp-dashboard.md`).

- Page (`site/app.js` `renderDiffs()`): with no station selected, the map panel lists up to 3
  stations per service where its average error is at least 10% smaller (`DIFF_MIN`), biggest gap
  first, for the map's variable and horizon. Only stations with at least `min_days_for_verdict`
  (7) days count. Names open the station details; the details get a "← Biggest differences" link.
  The page now opens on the list instead of Oslo's details.
- Temperature rows on the Yr side also show WeatherNext's height-adjusted error (e.g. Losistua
  1 day: Yr 0.85, WeatherNext 1.89, height-adjusted 0.66 °C, so height explains it).
- Export: `stations.json` gains `days` per station (the plan said "page only", but the page could
  not check the 7-day rule from `n` alone). Test added in `test_sampling`.
- "Clearly" is a 10% gap, not a per-station significance test; rain uses WeatherNext's average,
  like the map colours (NEXT_STEPS item 5 covers the median on those views).
- Live history, 1 day temperature: Yr closer at Losistua, E6 Langfjordbotn, E6 Mjøsbrua;
  WeatherNext at Norne, Johan Castberg, Aasta Hansteen (offshore). Wind: Yr at Valdresflye (65%).
- 128 cloud tests pass. (`MigrateTest.test_runs_marked_by_retrieval_time` used to error on
  Windows: it left a read connection open, so the temp `w.db` was locked at cleanup. Fixed the same
  day by closing it; 5 runs in a row pass.) Checked in the browser with data rebuilt from history: all three
  variables, 1/3/10 day horizons (10 days: "no station has 7 days"), click-through and back,
  375 px light, dark; no horizontal scroll, no console errors.

Next: plan step 4, station freshness warning (`last_obs` in meta.json).

## "Which way do they miss?" card — 2026-10-11 (Claude)

**Done and pushed 2026-10-11 (a69cdf3; step 1 a6e6e31 with it).** Step 2 of the dashboard plan
(AgnosticBrain `plans/weatherapp-dashboard.md`). CI run 38138056010 passed. The live page shows
both after the next scheduled publish run.

- Export (`cloud/summarize.py`): new `bias_by_hour()` beside `conditions()` writes `bias.json`:
  per variable and horizon, 4 blocks of 6 h in Oslo local time (summer/winter time handled) with
  n, days, bias_yr, bias_wn, bias_wn50 and, for temperature, bias_wnh. All days; no period split.
- Page: new card "Which way do they miss?" after the steadiness card, with its own horizon picker.
  Horizontal bars from a zero line (right = too warm/strong/wet). Temperature adds an outlined
  height-adjusted WeatherNext bar; rain uses WeatherNext's median, as the tiles do. A lead line
  gives the all-hours bias from leaderboard.json; table view; note for blocks under 7 days.
- `renderBias()` returns early if its section is missing, so a cached old index.html with the
  new app.js still renders (seen once in testing, before the guard).
- Live history, temperature 1 day: Yr +0.18 °C (+0.23 at night, +0.10 by day), WeatherNext
  -0.29 °C, height-adjusted about 0. At 7 days Yr leans +0.55 °C.
- 125 cloud tests pass (3 new: Oslo blocks incl. winter time; build writes bias.json). Checked in
  the browser with data rebuilt from history: desktop and 375 px, dark and light, all three
  variables, horizon picker; no horizontal scroll, no errors after the guard.

Next: plan step 3, "Biggest differences" in the map panel (page only).

**"Both, averaged" tile range, 2026-10-11:** `stats()` now adds `avg_gain_lo/hi` and `verdict_avg`
(better / worse / too_close / not_enough_data) from a day-block bootstrap of 1 - MAE(avg)/MAE(better
single service), the better service fixed on the full sample (`bootstrap_gain`). The tile shows the
95% range and a badge. Now: temperature 1 day +11% (+9 to +13%), wind +7% (+5 to +9%), both clear;
at 7 days too close to call. 128 cloud tests pass.

## PC collector retired; weather.db archived and deleted — 2026-10-11 (Claude)

- Scheduled task "WeatherApp Background Collector" deleted (user's decision after the 11 Oct
  coverage check: timer-era cloud coverage 100% at every horizon reached).
- `data/weather.db` (7.7 GB, WAL empty) compressed to `outputs/weather_db_2026-10-11.7z`
  (520 MB; extraction verified identical by SHA-256). The user copied it to a spare drive; then
  `weather.db`, `-wal` and `-shm` were deleted. The cloud `history/` is now the live record.
- Correction, later the same day: the 7z was then also deleted (with `rm`, bypassing the Recycle
  Bin) on the mistaken understanding that a copy existed; there was none. A search of all drives
  found no copy. E: is an NVMe SSD (TRIM), so recovery was judged unlikely and skipped. Lost: the
  raw local forecasts/observations. Kept: every scored day in `history/`. Docs now say `history/`
  is the only record.
- CLAUDE.md, AGENTS.md, PROJECT_STATUS.md and NEXT_STEPS.md updated to match.

## Averaged forecast tile — 2026-10-11 (Claude)

**Done and pushed 2026-10-11 (a6e6e31).** Step 1 of the dashboard plan (AgnosticBrain
`plans/weatherapp-dashboard.md`; HTML version in local `work/plans/better-dashboard.packed.html`).
All five plan decisions were kept as suggested.

- Export (`cloud/summarize.py`): `paired()` adds `e_avg` = midpoint of Yr and WeatherNext minus the
  observation, temperature and wind only (not rain). `stats()` adds `mae_avg`, `bias_avg` and
  `avg_gain` (1 - avg MAE / the better single MAE) to every stats block, so leaderboard.json and
  patterns.json gain them. Verdicts, ranges and scoring are unchanged.
- Page: a fourth tile "Both, averaged" (with "N% better than the better of the two" and a note that
  it is our blend, not a service) and a "Both, averaged" column in the horizon table. Tiles go
  4 across, 2x2 below 1000 px, 1 column below 760 px. Rain keeps three tiles.
- Live history (24 days at 1 day): temperature 0.80 vs Yr 0.90 / WeatherNext 0.91 °C (11% better);
  wind 1.33 vs 1.46 / 1.43 m/s (7%).
- 122 cloud tests pass (3 new in `test_improvements.py`). Checked in the browser against data
  rebuilt from history into ignored `site/data/`: desktop, 900 px and 375 px, all three variables,
  no console errors, no horizontal scroll.

Next: plan step 2, the "Which way do they miss?" bias card (`bias.json`).

## Steadiness card — 2026-10-11 (Claude)

**Done and pushed 2026-10-11 (85bf9d6).** New card "How steady are the forecasts?" under the horizon card,
showing the existing `steadiness.json` (PLAN_REPLAYS step 3). Site only (`site/app.js`,
`index.html`, `style.css`); no scoring, export, data or workflow changes.

- Horizontal bars per horizon step (7 d -> 5 d ... 12 h -> 6 h): average size of each service's
  change for the same station/hour, with the existing day-block verdict ("Yr steadier",
  "WeatherNext steadier", "Too close to call") under each step label and in the tooltip.
- Flip-flops per 100 forecasts above the chart (temperature now Yr 3.1 vs WeatherNext 0.6).
- Note: steps with fewer than `min_days_for_verdict` days are hidden (10 d -> 7 d has 3 days);
  the "moved closer to the measurement" share range per service (about 50-70%, a coin toss is
  50%); caveats (ensemble average moves less; Yr corrected with station data near the event;
  steady is not accurate). All days so far: the period switch does not apply (the JSON has no
  period split). Rain uses WeatherNext's average, as `cloud/replay.py` does; labelled so.
- Table view keeps every step, with "moved closer" percentages, forecasts and days.
- The JS repeats `MIN_REVISION` from `cloud/replay.py` (0.2 °C / 0.5 m/s / 0.1 mm) for the
  caption; change both together.
- Checked against the live JSON (refreshed into ignored `site/data/`) at desktop and 375 px,
  dark and light, all three variables: no page errors, no horizontal scroll. 119 cloud tests pass
  (none cover the JS).

Step 4 hand check done the same day (see PLAN_REPLAYS.md). Next: the
"Show the differences" ideas in NEXT_STEPS.

**Replay hand check (PLAN_REPLAYS step 4), 2026-10-11:** the 15 Sep western Norway rain day is
absent from the page by design (WeatherNext has 4 of 24 hours); measured totals in history are
right. The published 16 Sep SN50540 replay matches hand sums from history exactly. Open idea, not
agreed: show Yr-only rain points when WeatherNext is incomplete (15 Sep has full Yr totals at
every horizon), or say on the page why big early days are missing.

## Horizon chart redesign — 2026-10-09 (Claude)

**Done.** The user found "Error by how far ahead" hard to read: the naive line (2-3 °C, 5.3 at
10 days) set the y-axis, the four model lines were squeezed at the bottom, the 10-day point came
from 1 day (47 forecasts), and WeatherNext's average and median overlapped. Site only
(`site/app.js`, `index.html`, `style.css`); no scoring, export, data or workflow changes.

- The card is now "Who is closer, by how far ahead" with a Difference / Error size switch.
  Difference (default): WeatherNext error - Yr error per horizon, with the existing 95% day-block
  range as a bar and a zero line. Points and bars are coloured by the existing verdict
  (blue = Yr, orange = WeatherNext, grey = too close). Temperature adds the height-adjusted
  series (hollow triangles); rain shows the median (headline) and the average (hollow squares).
- Both views hide horizons with fewer than `min_days_for_verdict` (7) days and say which.
  The table keeps every horizon. Error size: Yr, WeatherNext, plus the height-adjusted (temperature)
  or average (rain) line; no naive line, no median line for temperature/wind.
- The naive baseline is now called "same as yesterday" in the tiles, table and "How to read" text.
- Checked locally against the live JSON (copied into ignored `site/data/`) in dark/light, desktop
  and 375 px mobile: no page errors, no horizontal scroll. 119 cloud tests pass (none cover the JS).
- Added `.claude/launch.json` (`site`: local static server on port 8765) for previews.

Pushed 2026-10-11 (21f7b2c). Next: the steadiness card (NEXT_STEPS 5). The 9 Oct
analysis of model differences (in the conversation, not stored) suggested further cards:
see NEXT_STEPS "Show the differences".

## Can the PC collector retire? Cloud vs local coverage — 2026-10-08 (Claude)

**Recommendation: not yet**, because only one finished day (7 Oct) exists since the timer
went live (6 Oct 16:37 UTC), and on that day only the 6 h, 12 h and 1-day horizons were
fetched under the timer. The 2-10 day forecasts for 7 Oct were fetched 27 Sep - 6 Oct,
when GitHub skipped runs. Where the timer could have collected, the cloud matched the PC
(99.9%). Re-run on 12 Oct (9-11 Oct: all horizons up to 2 days fully timer-era) and about
18 Oct (10-day horizon). Retire when timer-era coverage stays >=99% at every horizon.

Method (`work/coverage-compare/compare_cov.py`, ignored; results `2026-10-07.json`):
weather.db opened `mode=ro`; cloud day file, `state` pending/obs decrypted in memory only.
Both sides use the cloud's rule: lead = target - fetch time (local `retrieved_at`),
within ±3 h of each page horizon; a station-hour counts when the side has a forecast and
an observation. 45 shared stations. Excluded, cloud only: SN20925 Wisting, SN76956 Goliat
FPSO, SN92895 E6 Langfjordbotn, SN94190 Revsbotn, SN96310 Mehamn; local only (added by
the 4 Oct discovery): SN71990 Buholmråsa, SN78800 Varntresk, SN92750 Hasvik, SN94640 E69
Nordkapp, SN96850 Tana bru.

7 Oct, cloud station-hours as % of local (Yr and WeatherNext give the same pattern):

| Horizon | Yr snapshots cloud/local | Yr cloud/local | % | WN % |
|---|---|---|---|---|
| 6 h | 9 / 5 | 1036 / 1039 | 99.7 | 99.7 |
| 12 h | 8 / 5 | 996 / 1039 | 95.9 | 95.9 |
| 1 day | 7 / 5 | 949 / 1039 | 91.3 | 91.3 |
| 2 days | 5 / 5 | 862 / 1039 | 83.0 | 83.0 |
| 3 days | 4 / 4 | 170 / 172 | 98.8 | 143 (PC has fewer) |
| 5 days | 4 / 4 | 170 / 172 | 98.8 | 87.3 |
| 7 days | 3 / 4 | 126 / 172 | 73.3 | 74.7 |
| 10 days | - | 0 / 0 (Yr too short) | - | 87.3 |
| **All** | | 4309 / 4672 | **92.2** | **93.2** (7426 / 7966) |
| **Timer-era slots** | | 1824 / 1826 | **99.9** | **99.9** |

- Every forecast gap is a cloud run GitHub skipped before the timer (e.g. none between
  6 Oct 08:43 and 15:16, or 5 Oct 02:03 and 18:32). Since the timer: 16 runs, gaps
  2.5-3.0 h, none over 3 h. The cloud never scored a station-hour the PC lacked, except
  WeatherNext 3 days, where the PC's 6-hourly fetches give fewer snapshots.
- The other cloud misses are late Frost observations: SN20961 and SN76938 at 00Z,
  SN76939 at 16Z (the only timer-era miss). They were not in at day preparation (8 Oct
  06:08 UTC) and are in the cloud state now; the PC refetches and has them. That is a
  permanent ~0.3% loss for the cloud at those hours, by design (prepare at +6 h).
- Yr 1400 vs 1350 rows: not a missing station, on neither side. Every cloud run has all 50
  stations; runs alternate 28 or 27 rows per station (also on 6 Oct). The difference is the
  10-day bucket: Yr's forecast reaches ~237-238 h after some fetch times (08:38, 14:07)
  and ends just short of the 237-243 h window after others (06:07, 11:37).

No database writes, history-file edits or Windows task changes.

Remaining: re-run the script on 12 Oct and ~18 Oct (`python work/coverage-compare/compare_cov.py
2026-10-09 2026-10-10 2026-10-11`; it needs fresh `$TMP/obs.enc` from `git show
origin/state:obs.csv.gz` and adjusting `TIMER` only if the timer changes). Then the user decides.

## External timer activated — 2026-10-06 (Codex)

- User saved the repository-scoped token directly in cron-job.org. External test
  returned HTTP 204 at 16:21 UTC; GitHub run 37495000121 succeeded and skipped at
  65 minutes without --manual. Collection, persistence and Pages were skipped.
- Enabled existing job 8590224 at :07/:37 UTC and verified the saved dashboard
  showed one enabled job with an upcoming execution. GitHub hourly fallback remains.
- Recorded token expiry (5 Nov 2026, 17:15 UTC), setup and handoffs without reading
  or recording the credential. Prior 119 cloud/79 local tests and CI passed;
  activation introduced no application code changes.
- Recurring executions, the first external due collection and multi-day cadence
  remain follow-up checks. Keep the PC collector until cloud coverage is proven.

## Timer diagnosis and activation checkpoint — 2026-10-06 (Codex)

Archived WORK_STATUS before activation:
- Diagnosed missed GitHub starts rather than gate rejection: scheduled runs reached
  the gate at 406 and 561 minutes after success and correctly collected.
- User approved push/live verification and cron-job.org as the independent timer.
- Preserved the health review, rebased local commits onto two new scored-history
  commits and pushed. Timer commit 0d97cf8; expanded setup docs 1bbd7c4.
- 119 cloud tests and CI 37453257669 passed. Timer run 37453257515 skipped at 135
  minutes; downstream actions, state SHA and public health stayed unchanged.
- Saved job 8590224 disabled, with :07/:37 UTC POST, timer JSON, request headers
  and failure/recovery/disable notifications. Prepared repository-only token form,
  Actions: Read and write, required read-only Metadata, expiry 5 Nov 2026.
- At that checkpoint, user token generation/entry, testing and activation remained;
  no external timer was active. Multi-day coverage and station findings remained open.
- No database writes, immutable-history edits, Windows task changes or tokens in
  files/chat. Push permission had been explicitly granted.

## Timer diagnosis and deployed dispatch gate — 2026-10-06 (Codex)

- Confirmed missed GitHub starts: scheduled gate logs show 406/561-minute ages;
  the gate allowed collection correctly. Workflow and repository were active.
- User approved pushing and using cron-job.org. Preserved health notes, rebased
  unpushed commits onto the two new scored-history commits, with no history edits.
- Pushed timer support (rebased 0d97cf8) and expanded setup/verification docs (1bbd7c4).
- All 119 cloud tests and CI 37453257669 passed. Live timer run 37453257515 skipped
  at 135 minutes; downstream actions skipped, state and public health unchanged.
- Independent :07/:37 UTC timer still awaits service sign-in and token entry. No
  recurring external job is active yet; this is not a completed cadence fix.

## Project health review - 2026-10-06 (Codex)

Done:
- Checked local task/logs, read-only database summaries, live cloud runs/state,
  station configurations, scored-day coverage and the public dashboard.
- Local collector completed at 12:14 Oslo; all sources OK, task Ready/result 0.
- Cloud run 37438015907 confirms upgraded actions and Pages deployment work.
  Live page: 31 days through 5 Oct, 174,911 rows; coverage 93.9-95.1% for 4-5 Oct.
- Cloud cadence remains poor: 10/16 runs in 48 h, maximum recent gap 9 h 21 min.
- Confirmed 45/50 cloud/local station overlap. Cloud observations for SN1120 and
  SN20925 stop on 30 Sep; aggregate Frost status remains OK.
- 79 local tests passed; 119 cloud tests passed earlier this session after timer edits.
  Browser renders and rain filter works, with no captured console errors.
- Database reads succeeded. SQLite quick_check hit its 45-second limit without a
  completed result; full integrity is unverified.
- Updated handoffs and archived the previous timer checkpoint.

Remaining:
- User's OK to push is still required. Integrate remote scored-history commits first.
- Deploy/configure and verify the timer, reconcile station networks, investigate
  stale observations and add station-level health warnings; then recompare coverage.
- Longer database integrity check if needed; other open work is in NEXT_STEPS.md.

Only handoff documents changed and remain uncommitted. No database writes, history
edits, configuration changes, task restarts, workflow dispatches, commits or pushes.

## Project health review - 2026-10-06 (Codex)

- Local collector completed 12:14 Oslo; task Ready/result 0, all sources OK. 79 local
  tests pass; 119 cloud tests passed earlier this session after timer edits.
- Live run 37438015907 confirms upgraded actions, persistence and Pages work; removed
  that completed follow-up. Live data: 31 days through 5 Oct, 174,911 rows. Observation
  coverage for 4-5 Oct is 93.9%/95.1%, neither late-finalized.
- Cloud cadence remains deficient: 10/16 collections in 48 h, maximum gap 9 h 21 min.
- Found cloud/local network drift (45/50 overlap) and stale Frost observations at
  SN1120/SN20925 since 30 Sep. Overall source OK currently hides station-level gaps.
- Browser renders and rain filter works with no captured console errors. Database
  reads succeed; full quick_check exceeded its 45-second budget and remains unverified.
- Refreshed handoffs only, left uncommitted. No runtime/database/remote changes or push.

## External timer dispatch - 2026-10-06 (Codex)

Done:
- Added the workflow_dispatch choice `trigger` (`manual` default, or `timer`).
- Only dispatches with `trigger=manual` pass `--manual`; timer runs respect the
  existing 150-minute gate. Hourly cron and collection concurrency are unchanged.
- SETUP_CLOUD.md documents the timer POST, headers, JSON, expected 204 response
  and repo-only fine-grained token with Actions: Read and write; placeholders only.
- Recorded the decision and refreshed handoff docs, preserving the earlier pending
  health-review edits and archiving the previous checkpoint in CHANGELOG.md.
- All 119 cloud tests pass using the existing .venv, including gate boundary and
  manual-bypass tests. Existing dependency/resource warnings remain.
- Five gate expression cases and unchanged schedule/concurrency verified locally;
  `git diff --check` passes.

Remaining:
- Await the user's OK to push, then configure the external timer and verify live
  timer skips/collections and the default manual bypass (SETUP_CLOUD.md).
- Existing deployment, coverage and feature follow-ups remain in NEXT_STEPS.md.

Committed locally only; no push or live dispatch. No database, history
day files, credentials, collector code or Windows scheduled-task changes.

## External timer dispatch - 2026-10-06 (Codex)

- Added `workflow_dispatch.inputs.trigger` (`manual` default, `timer` alternative).
  The gate bypass requires both a dispatch event and `trigger=manual`; timer runs
  respect the existing 150-minute interval. Hourly cron and concurrency are unchanged.
- Added external timer setup to SETUP_CLOUD.md, including the POST request, 204
  response and repo-scoped Actions: Read and write token permission; no real token.
- Updated DECISIONS and handoff docs, preserving pre-existing health-review changes.
- Validation: 119 cloud tests passed with the existing .venv. Existing warnings remain.
- Five gate expression cases and unchanged cron/concurrency checked locally;
  `git diff --check` passed.
- Local commit only; push awaits the user's OK. No live dispatch or timer configured.

## Project health review - 2026-10-05 (Codex)

Done:
- Checked clean Git state, latest GitHub runs/settings, public health/meta/monthly JSON,
  recent scored-day metadata, read-only database summaries and local task state.
- 119 cloud and 79 local tests pass using the existing .venv (198 total).
- Cloud run 37231498979 passed all collection/persistence/Pages steps and reported no
  source errors. Published data: 29 days through 3 Oct, 160,259 rows, 9/16 collections in 48 h.
- WeatherNext past values are already enabled and published; removed that stale open item.
- Coverage metadata verified for 2-3 Oct (~95%, not late-finalized); removed that stale item.
- Local collector finished successfully at 00:14 Oslo on 5 Oct; 50 active stations.
- Refreshed PROJECT_STATUS/NEXT_STEPS; archived the previous checkpoint in CHANGELOG.

Remaining:
- Verify a collecting/deploying run with the new actions and a real scheduled gate skip.
- Recompare cloud/local forecast coverage before stopping the PC task; scheduling is still
  the main operational concern. Evaluate the hourly trigger over several days.
- Feature/housekeeping items remain in NEXT_STEPS; no application fixes made in this review.

Only handoff documents changed. No authoritative database writes, collector/task changes,
secret changes, workflow dispatch, commits or pushes were performed.

## Project health review - 2026-10-05 (Codex)

- Fresh validation: 119 cloud + 79 local tests passed. Clean checkout before review.
- Cloud run 37231498979 passed all steps/sources; public health/meta checked on 5 Oct:
  29 scored days through 3 Oct, 160,259 rows, 9/16 collections in the published 48 h window.
- Confirmed WX_PUBLISH_FORECAST_VALUES=1 (set 4 Oct 20:13 UTC) and live publication;
  removed the completed activation item from NEXT_STEPS.
- Verified 2-3 Oct coverage metadata (94.9%/94.7%, neither late-finalized); removed
  the completed first new-day verification item. Observation coverage is not forecast coverage.
- Local database read-only check: 50 active stations; four latest background runs successful,
  most recent finished 5 Oct 00:14 Oslo. Scheduled task remains enabled/Ready.
- Refreshed handoff notes; no database, application, task, credentials or remote changes.

## Workflow actions off Node.js 20 — 2026-10-04 (Claude)

Done (pushed as 1eb4140; "Cloud pipeline tests" run 37236715635 green, 119 tests, the Node.js 20
warning is gone):
- `collect.yml` and `tests.yml`: checkout v4 → v7, setup-python v5 → v7, configure-pages v5 → v6,
  upload-pages-artifact v3 → v5 (uses upload-artifact v7), deploy-pages v4 → v5; all node24.
- Breaking changes checked against our use: upload-pages-artifact v4+ leaves out dotfiles (`site/`
  has none); setup-python v7 dropped `pip-install` (unused; `cache`/`cache-dependency-path`
  remain); checkout v6+ credential file and v7 fork-PR block don't apply (`persist-credentials:
  false`, no `pull_request_target`/`workflow_run`).
- Run #44 (12:21 UTC 4 Oct) failed only on ECMWF/Open-Meteo (read timeouts, 0 rows); Yr,
  WeatherNext and Frost were fine.

Remaining:
- The new actions in `collect.yml` first run on the next collect run; check it deploys Pages.
- Gate not yet seen in action: as of 21:36 UTC 4 Oct GitHub had started no scheduled run since
  18:38 (none at 19:23, 20:23, 21:23; #46 at 20:17 was manual). Check that scheduled runs resume,
  and that a skipped run leaves `state` and Pages untouched and adds no run record (NEXT_STEPS 4).
- Still open: the user sets `WX_PUBLISH_FORECAST_VALUES`; replay steadiness on the page.
- `ubuntu-latest` moves to Ubuntu 26 from 19 Oct (runner notice); watch the first run after that.

## Hourly trigger with a 150-minute gate — 2026-10-04 (Claude)

Done (pushed 4 Oct as a6a78d7, 788be89; tests workflow green):
- Rebased the 2 local commits (storm replays; WeatherNext terms decision) onto origin's
  "Store encrypted scored days" (2 Oct day); 197 tests passed after the rebase.
- `collect.yml`: cron `23 * * * *` (was `17 */3 * * *`), `workflow_dispatch` kept, concurrency
  group kept. A gate step after restore runs `python -m cloud.run due` (`--manual` on dispatch);
  every later step needs `steps.due.outputs.run == 'true'`.
- `cloud/health.py`: `MIN_GAP_MIN` = 150 and `due(meta, now, manual)` from `last_success`;
  `RUN_EVERY_H` = 3 unchanged; `PREVIOUS_RUN_EVERY_H`, `RUN_EVERY_CHANGED_AT` and their test removed.
- DECISIONS.md "WeatherNext terms": Google's 4 Oct reply (1-hour rule on target time) replaces
  the open-ambiguity / no-reply wording; new rule: never show WeatherNext values for future target
  times. NEXT_STEPS item 1 updated. Code already cuts off on target time (summarize, replay).
- Tests: 2 new (gate rules; the `due` command writes `run=false/true` to `GITHUB_OUTPUT`).

## Past WeatherNext values and storm replays — 2026-10-02 (Claude)

Done (not pushed; shown to the user first):
- DECISIONS.md "WeatherNext terms": the user's decision to publish past WeatherNext values under
  CC BY 4.0, our reading, the open ambiguity, the 26 Sep email to weathernext@google.com as the
  user reported it (no reply), and removal if Google asks.
- Values only for targets at least `PUBLISH_MIN_AGE_H` = 1 h old (`summarize.build` recent
  series and `replay`). The workflow reads the repository variable `WX_PUBLISH_FORECAST_VALUES`
  (default 0) instead of a hard-coded 0. **Not yet turned on:** the user sets the variable.
- The CC BY citation and the real-time notice sit under every chart that draws WeatherNext
  values (station chart, storm replays), from `meta.wn_value_attribution`.
- Storm replays (PLAN_REPLAYS step 2, card of step 3): `find_events`, `select_events`, `replay`,
  `build_replays` in `cloud/replay.py`; `events.json` + `events/<id>.json`. Real history gives
  17 events (11 wind, 5 rain, 1 cold).
- Tests: 197 pass (12 new replay/publishing tests); page checked locally with the real history,
  desktop and 375 px (a too-wide event picker was fixed).

Remaining: push (user's OK), then the user sets the repository variable. Steadiness on the page
(PLAN_REPLAYS step 3 rest), the 15 Sep hand check (step 4: that day has no complete rain horizon,
so it has no replay).

## Cloud collection every 3 hours — 2026-10-01 (Claude, Sonnet)

Done:
- `collect.yml` cron `17 */6 * * *` → `17 */3 * * *` (00:17, 03:17 … 21:17 UTC). Page copy and README say "every 3 hours".
- `cloud/health.py`: `RUN_EVERY_H = 3`, so a full 48 h window expects 16 runs. Expected runs are counted per
  period (`expected_runs`, `RUN_EVERY_CHANGED_AT` = 1 Oct 18:00 UTC) so the 48 h after the change don't show a
  false "Check:" for the 6-hourly runs already in the log. Remove `PREVIOUS_RUN_EVERY_H` and
  `RUN_EVERY_CHANGED_AT` after 3 Oct.
- `site/app.js` `STALE_H` 9 → 8 h (3 h interval + 5 h allowance for GitHub delays seen at 3–5 h; first set to 6 h, raised at the user's request).
- `cloud/store.py` keeps 120 run records (was 60): the same 15 days at 8 runs/day.
- Checked and left unchanged, nothing assumes 6-hourly runs: horizon windows (±3 h, closest lead per target, so
  denser runs only get closer to nominal), scoring/finalization (UTC-day based), pending/obs pruning (day based),
  WeatherNext init choice (lead is measured from each fetch), ECMWF/Open-Meteo calls (~400/day vs 10,000 limit).
- Tests: 182 pass (one new health test for the cadence change; existing health tests moved to 3 h spacing).
- The Codex handoff docs left uncommitted were committed unchanged first (0db42e8).

Remaining:
- Not touched, on purpose: the local Windows task, `install_background_task.ps1`, `collection_health.py` and the
  Streamlit health caption ("Expected every 6 h · OK ≤8 h"). The task is to be stopped after the parallel week.
- Watch the first days: GitHub may still start slots late, and a gap over 8 h makes the page warn. Pending state
  now grows about twice as fast (more runs per day); check its size after a few days.

## First scheduled reliability run verified — 2026-09-29 (Codex)

Done:
- Run 36497119777 (28 Sep 23:16 UTC, commit 661ef8d, descendant of 3e6ec36) passed every step: restore, collect, history confirmation/state publication, export, Pages and final source check.
- Zero source errors: Yr 1,350; WeatherNext 2,400; ECMWF 4,500; Frost 5,887 rows.
- Live health.json matches collection at 23:16:55 UTC; rendered page shows fresh data, Yr/Frost/WeatherNext checkmarks and 7 of 8 runs in 48 h. Monthly summary is also live.
- Follow-up completed; heartbeat paused. No collection schedules or local database changed.

Remaining at the time:
- Scheduling gap reached 9 h 21 min; consider external triggering separately.
- No new day was ready: new-day coverage metadata/finalization still needs a future live cycle (failure tests already passed).

Evidence: https://github.com/Stranden1/weather-forecast-verification/actions/runs/36497119777

## Monthly summary + rain median headline — 2026-09-28 (Claude, Sonnet)

Done (committed locally, not pushed):
- `cloud/monthly.py` + `summarize.build` write `site/data/summary.json`: this month so far plus
  every completed month (UTC, by target day), verdicts for temperature/wind at 6 h, 1, 2, 3, 5 days
  and rain at 6 h, 1, 2 days, using the existing `paired`/`stats` (same pairing, bootstrap, 7-day
  minimum). Text is fixed templates; verdicts and text only, no forecast values.
- Page: "Month by month" block under the health line (current month, collapsed "Earlier months").
- Rain views (tiles, horizon chart, table, "Catching rain") lead with WeatherNext's median (solid),
  average dashed; one sentence explains why. Rain verdict/CI now also computed for the median
  (`verdict_50`, `diff_50`, `ci_50_*`); the tile shows the average-based verdict as a second line.
- 23 new tests (`cloud/tests/test_monthly.py`); 177 root+cloud tests and 8 HQ tests pass.
  Checked with `?demo` (desktop dark, 375 px) and a real-data build (September text below).

Remaining:
- User to read the September text, then say whether to push.
- Rain "Who wins where" map, "Over time" chart and "Patterns" table still use WeatherNext's average
  (not in the requested list); change them if the headline should match everywhere.
- Verify the deployed page after the first run that includes summary.json.

## Reliability changes pushed — 2026-09-28 (Codex)

Done:
- User authorized deployment; pushed 3e6ec36 to origin/main around 20:24 UTC.
- Confirmed clean checkout, no newer remote main commits, and evidence of 154 passing tests.
- Created heartbeat verify-weatherapp-reliability-deployment to check every 30 minutes.

Remaining (carried to NEXT_STEPS item 3):
- Check the next scheduled run using the changes: Actions logs and published page health line.
- Older plaintext Git commits/caches require separately coordinated cleanup.

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

## Project health and Claude change review — 2026-09-28 (Codex)

Done:
- Reviewed cloud collectors, scoring, sampling/height changes, encryption,
  workflow recovery, and the handoff documents. Findings: REVIEW_2026-09-28.md.
- Verified live cloud collection (28 Sep 13:55 UTC): all four sources succeeded;
  23 scored dates / 126,109 rows through 27 Sep. Local collection also succeeded.
- Ran 132 local/cloud tests: all passed. HQ: 7 passed, 1 Windows symlink skip.
- Reproduced empty-day finalization in disposable state; verified public history
  includes WeatherNext values despite the documented statistics-only policy.
- Archived the preceding checkpoint and refreshed status/open items.

Remaining:
- Resolve public scored-data storage versus the forecast-publication policy.
- Fix observation-outage finalization, state-restore failure handling, persistence
  ordering, and failure reporting before cloud-only cutover. See the review.

Review only: no application, database, history, secret, or schedule changes. No
pull, commit, or push. Local HEAD remains 17ae2a8; remote main has two newer scored-day commits.

## ECMWF IFS and AIFS added to the cloud collector — 2026-09-27 (Claude)

Done (DECISIONS.md, "ECMWF IFS and AIFS via Open-Meteo"):
- `cloud/openmeteo.py` collects `ecmwf_ifs` and `ecmwf_aifs025_single` from Open-Meteo in the
  same run as Yr/WeatherNext, same horizon windows, with station heights (`elevation`).
- New scored columns `ifs_issued/t/w/p`, `aifs_issued/t/w/p`, filled from the fetch Yr and
  WeatherNext already select; pairing rules unchanged; old history files untouched.
- Attribution: Open-Meteo and ECMWF lines added to `ATTRIBUTION`. Not shown on the page otherwise.
- Tests: `cloud/tests/test_openmeteo.py` with a recorded response
  (`cloud/tests/fixtures/openmeteo_ecmwf.json`, Oslo + Troll B, 26 Sep 22:08 UTC). A health test
  that had started calling Open-Meteo live now mocks it. 132 tests (80 local + 52 cloud) and 8 HQ pass.
- Live dry run (no state written): 50 stations, 4,600 rows, 4.4 s, no errors.

Pushed. Confirmed on 27 Sep: the 05:19 UTC cloud run stored 4,800 ECMWF rows with no errors, and the page shows the new credit lines. The local task's runs since 26 Sep 16:10 UTC use bilinear sampling (Losistua's WeatherNext temperature rose ~1.2 °C from the old higher cell). First scored day with ECMWF: 27 Sep.

Dated record of completed work, newest first. Moved here from `WORK_STATUS.md` on
2026-09-26 with the wording unchanged; entries describe the state at the time they were
written and may be superseded by later ones. Before that date `PROJECT_STATUS.md` and
`NEXT_STEPS.md` also carried dated sections summarizing the same work; their full text
is in Git history (commit `7e01378`). Paths under `work/` and `outputs/` are local-only evidence.

## Early cloud days filled; WeatherNext terms read — 2026-09-26 (Claude)

Done:
- 23 and 24 Sep cloud day files replaced once from the PC database (user's OK), recorded in
  DECISIONS.md. 7,910 / 8,274 rows, all with WeatherNext, marked `nn5km`. `weather.db` only read.
- WeatherNext terms read: catalog page "Terms of Use" and the real-time terms PDF
  (https://storage.googleapis.com/weathernext-public/terms-of-use.pdf, last modified 3 Sep 2026).
  Data for times ≥ 1 hour ago is CC BY 4.0 with a fixed citation. Newer and future data falls
  under the real-time terms: internal use, value-added services, and only controlled sharing
  of the data itself.

- Fixed the same day: the public `state` branch held future WeatherNext forecasts. State files
  are now Fernet-encrypted (`cloud/store.py`, key `WX_STATE_KEY` as a GitHub secret and in local
  `.env`); plain files stay readable. Verified after a manual run at 15:25 UTC: both files
  encrypted, readable with the key, all sources OK, new rows `bilinear`. 44 cloud tests pass.
  Old plain versions may stay reachable on GitHub by commit hash for a while.
- Attribution updated to Google's current wording (terms PDF 4(b) citation naming Google Earth
  Engine, catalog CC BY citation, ECMWF acknowledgement link), shown one per line with clickable
  links; same text in `FINDINGS_2026-09-26.md`. DECISIONS.md "WeatherNext terms" quotes the
  clauses. Policy: error statistics only; `WX_PUBLISH_FORECAST_VALUES` stays off.

Remaining: none. Publishing values would need Google's confirmation first (NEXT_STEPS item 1).

## Documentation cleanup — 2026-09-26 (Claude)

Done, following REVIEW_2026-09-23 §4:

- `PROJECT_STATUS.md` rewritten as current state only (about one page, keeps a `## Summary`
  heading, which Project HQ's overview reads).
- `NEXT_STEPS.md` rewritten as open items only. Items already done were dropped. Checked
  facts: cloud WeatherNext works since 25 Sep 04:58 UTC; cloud 23 Sep is empty, 24 Sep has Yr
  only, 25 Sep has WeatherNext from 05 UTC; `--strict` exists but the workflow does not use it.
- The old work log moved to `CHANGELOG.md`, newest first, wording unchanged. A script checked
  that every line is there. The old dated sections of PROJECT_STATUS/NEXT_STEPS are in Git
  history (commit `7e01378`).
- README: removed "rainfall is not yet scored", added the cloud pipeline and Project HQ.
- AGENTS.md and CLAUDE.md: the new rules for these files.
- Project HQ committed first as its own commit (`7e01378`, Codex's work, unchanged).

No code, data, history or schedule changed. 79 local + 43 cloud + 8 HQ tests pass.
Pushed 26 Sep 14:59 UTC with all earlier local commits, after merging three CI scored-day
files from `origin/main`. GitHub's cloud tests passed on the push.

## WeatherNext cold bias: sampling fix and height-adjusted line — 2026-09-26 (Claude)

Investigation (deep-thinker, read-only EE): `INVESTIGATION_COLD_BIAS_2026-09-26.md`. Cause:
the ~5 km cell's terrain is up to 400 m above low fjord/valley stations; plus lake/fjord/urban
night warmth at Mjøsbrua, Sunndalsøra, Oslo; plus a sampling artefact (15/50 stations read a
neighbouring cell). Done, per DECISIONS.md "WeatherNext sampling and station height":
- Both collectors now sample bilinearly on the native grid (`resample("bilinear")`, 100 m).
  Verified live against hand-computed bilinear for all 50 stations. Scored rows carry
  `wn_sampling`; PC switch time `LOCAL_BILINEAR_SINCE` = 2026-09-26 16:00 UTC (the Windows
  task's next run was 16:10 UTC). A running Streamlit dashboard keeps the old code in memory:
  restart it before any manual WeatherNext fetch from Admin.
- `cloud/heights.py` + `config/wn_heights.json` (GMTED2010 cell heights per station and
  method; regenerate with `python -m cloud.heights`, read-only EE).
- Page: height-adjusted WeatherNext (temperature, 6.5 °C/km, land only) in the tile, verdict
  tile, horizon chart/table and station panel; 15 stations flagged; "How to read" bullet.
  Primary verdict and all 50 stations unchanged. Real history: height-adjusted MAE
  0.76/0.78/0.80/0.85 at 6/12/24/48 h vs Yr 0.81/0.84/0.89/0.97.
- 43 cloud tests, 122 total pass. Page checked with real history (desktop, 375 px). No history
  file rewritten; `weather.db` only read. Not pushed.

## Forecast steadiness (PLAN_REPLAYS step 1) — 2026-09-25 (Claude)

New `cloud/replay.py`: `steadiness(scored, var)` gives the revision size per horizon
step, the share of revisions that moved toward the observation, flip-flops per 100
forecasts, and a day-block bootstrap on the revision difference. `summarize.build`
writes `steadiness.json`. The page does not show it yet (step 3). 35 cloud tests pass.
The history files were only read. Plan and results: PLAN_REPLAYS.md. Git works here
only through GitHub Desktop's `git.exe` (not on PATH). Not pushed.

## Cloud pipeline improvements — 2026-09-24 (Claude)

Added the naive "same as before" baseline and skill score, a pinball score and range
width for the uncertainty ranges, and a health line under the page title. Details are
in PLAN_WEBPAGE.md → "Improvements". New: `cloud/health.py` and
`cloud/tests/test_improvements.py` (17 tests; 25 in total pass). Checked the page with
`python -m cloud.demo` (`site/index.html?demo`) and with the real history. Existing
`history/` files are untouched. Review changes: baseline offset from the actual lead,
skill as a percentage, Days/Forecasts columns removed from the horizon table. No
history files had been written since the baseline change, so none were regenerated.
Pushed after the user's OK.

Found uncommitted work by another assistant in `cloud/migrate_sqlite.py` and
`cloud/tests/test_pipeline.py`: a `--from … --fill-missing-wn` option that replaces
cloud day files without WeatherNext with the PC copy. It was not documented, and its
test passes. It is kept and committed as its own commit, separate from this work,
so the user can review or drop it before pushing.

## Cloud pipeline commit and secret scan — 2026-09-23 (Claude)

Fixed the Codex sandbox "setup refresh had errors": `.git` was owned by
`CodexSandboxOffline`, so the non-elevated setup could not add its deny ACE.
The user reset the owner of `.git` to their own account.

Scanned all Git history and all uncommitted files for secrets. No `.env` values
or keys were found, and `.env` has never been committed. The EE key is used only
in memory. Moved the workflows from `cloud/github-workflows/` to
`.github/workflows/`. `cloud/tests` pass (8). Committed the pipeline code, then the
docs, as separate commits.

Deployed the same day: pushed, made the repo public, Pages source set to GitHub Actions,
all four secrets set. The first manual run collected no Yr data because the secrets had a
BOM from a PowerShell pipe; after they were set again, run 2 gave yr=1400, obs=3530,
wn=0. WeatherNext is blocked by a missing IAM role (user action, see NEXT_STEPS).
The migration (`--until 2026-09-23`, read-only) wrote 18 day files for 09-05..09-22.
`weather.db` was only read. The Windows task is unchanged and should keep running
in parallel.

## Forecast vs Actual history window investigation — 2026-09-23

Completed a read-only reproduction for Trondheim-Voll. Forecast vs Actual offers
72 h, 7 days, and Full run; it has no 24 h option. The selected run query is
bounded by run IDs, not a requested historical observation window. Both forecast
series and Frost observations are joined over the selected runs' valid timestamps,
then 72 h/7 days clips the chart from the earliest valid timestamp. The reproduced
automatic pair was the newest fair observed pair (Yr issue 22 Sep 21:31 UTC,
WeatherNext issue 23 Sep 00:00). Forecast rows spanned 22 Sep 22:00–8 Oct 00:00;
the plotted 72 h and 7 day extents ended 25 Sep 22:00 and 29 Sep 22:00. Frost
observations available in the pair ended 23 Sep 16:00. Older observations have
no forecast points in these selected runs, so this is not a query or x-axis loss.
Run coverage and newest-pair selection explain the short historical portion.

Added a concise UI caption explaining the span origin, limited elapsed history,
and how Manual runs can inspect older forecasts. No scoring, pairing, query,
database, or scientific behavior changed. The full regression suite and dashboard
fixture interaction check passed. Separate checkpoint commit created; no push.

## All-station precipitation optimization — 2026-09-23

Completed the first bounded query optimization. Baseline on a fixed 7-day,
all-station snapshot took 6.60/8.71 s for 1h, 8.74/8.58 s for 6h, and
8.51/8.60 s for 24h (first/repeat calls). Query timing showed the WeatherNext
sample read dominated (5.7–7.7 s); `EXPLAIN QUERY PLAN` showed a full scan of
the 12.1m-row `weathernext_samples` table. A disposable SQLite copy confirmed a
partial expression index on `julianday(valid_at), run_id`, restricted to hourly
precipitation means in mm, serves a bounded search while retaining the existing
forecast primary-key lookup.

Retained that additive index and the equivalent `julianday(s.valid_at)` bound in
the WeatherNext sample SQL. The index was created transactionally in the
authoritative DB; `weathernext_samples` stayed at 12,122,400 rows and the query
plan uses the new index. Pair CSVs and metric records are identical for all
three modes: 12,225 hourly pairs, 2,255 six-hour pairs, and 351 daily pairs.
Production first/repeat timings: 3.94/6.05 s (1h), 6.01/5.86 s (6h), and
5.89/5.97 s (24h), about 31–35% lower on average. The audit's ~7.9 s baseline
is reduced but the 1.5 s target is not met.

Two further candidates were rejected after disposable-copy tests: a wider
covering sample index and a forecast-time expression index driving the join.
Neither materially improved the read. Three implementation attempts were used;
stop here rather than risk restructuring pair/scoring logic. Full suite: 79
tests passed. Expanded fixture UI passed with zero DB writes. No collection
behavior, stations, scoring rules, history, schedule, or secrets changed. Local
checkpoint commit created, not pushed.

## Long-range temperature query optimization — 2026-09-23

Completed three bounded iterations against fixed all-history, 7-day, 24-hour,
and Trondheim-Voll snapshots. Baselines were 7.06/7.58/5.74 s for all-station
all-history/7-day/24-hour and 6.11/5.18 s for Trondheim-Voll all-history/7-day.
The verified-history query returned 4,400 rows but SQLite began from all provider
runs and walked the 12.1m-row sample table. A `CROSS JOIN` loop-order constraint
starts at the 4,400-row manifest and uses existing run/time primary-key probes;
its exact result is unchanged and its query time fell from 2.6–4.9 s to 13–29 ms.

The existing inclusive 69–219 h stored-lead filter is now also applied in SQL
before Pandas materialization. This preserves the post-load filter and timestamp
consistency check. The Frost observation read now adds the selected station and
date bounds directly in SQL, removing its prior all-station read for a single
station. For all five fixed combinations, every paired row and all four horizon
summary records match the saved pre-change output exactly. Final first-pass
fixed-snapshot times: 1.51 s (all history), 1.13 s (7 days), 0.73 s (24 h),
0.15 s (Trondheim-Voll all history), 0.13 s (Trondheim-Voll 7 days). A broader
read-only profile later measured 2.88 s all-station/all-history and 0.15 s for
one station; no cache is used.

Validation: full suite 79 tests; expanded fixture dashboard interaction and
zero-write checks; production read-only profiles for Forecast vs Actual,
automatic pairing, Overall Accuracy, precipitation 1h/6h/24h, Long-range,
Model Disagreement, collection health and WeatherNext status. No database rows,
scoring rules, station network, collectors, scheduling, or secrets changed for
this target. The precipitation target's one additive index is documented above.
Checkpoint commit created locally, not pushed. Remaining largest bottleneck is
all-station precipitation at about 5.6 s; further query work should be separate.

## Precipitation Git checkpoint review — 2026-09-23

Reviewed all 13 modified/new files: hourly precipitation scoring, canonical
Forecast vs Actual, Overall accuracy, POD/FAR/CSI, associated tests and benchmark/
production documentation. No unrelated or suspicious changes found. No application
behavior, live database, credentials, collector or scheduled-task changes in this
checkpoint task.

Revalidation: all 69 unit/regression tests passed; the expanded dashboard fixture
interaction suite passed, including rainfall filters, automatic/manual selection,
partial/empty buckets, previous views and unchanged fixture history. Secret and
runtime-file scans passed. Existing deprecation warnings are non-fatal.

The user now explicitly authorized committing this previously uncommitted work.
Checkpoint message: `Checkpoint hourly precipitation verification`. All reviewed
source/tests/docs are included; local database, secrets, logs, screenshots and
analysis evidence remain ignored. Nothing remains for this checkpoint task.
No push requested or performed. Earlier uncommitted notes record prior task states.

## Optional accumulated precipitation checkpoint — 2026-09-23

Completed: 6h fixed UTC and 24h UTC-day scoring in scoring/precipitation.py,
with one run per provider, all exact aligned hours, strict pre-start issue
and component retrieval, common start-lead buckets, <=3h lead gap and
error-independent pair ordering. Central thresholds are >0.1/0.5/1.0 mm
for 1h/6h/24h. Overall accuracy has a precipitation-only selector, default
1h; Forecast vs Actual remains hourly. Counts, distinct periods, dates,
amount/event metrics and actual lead ranges are shown.

Fixed-snapshot production reproduction matches every benchmark pair and
metric: 2,110 six-hour pairs / 796 distinct station periods, and 293
daily pairs / 160 distinct station-days, 29 stations. The live read-only
6h/24h dashboard render and fixture interaction checks passed. Focused
aggregation tests cover complete boundaries, missing hours, run mixing,
availability, threshold edges, metrics, lead pairing and read-only access.
No database/schema, collector, station network, scheduled task or historical
data change. The existing hourly checkpoint was pushed to origin/main
before this work; the new implementation commit must remain local.
Validation complete: all 76 regression tests, expanded fixture dashboard UI, live read-only 6h/24h render, fixed-snapshot pair/metric reproduction and git diff --check pass. No remaining implementation work. Create the local checkpoint commit; do not push the new commit.

## WeatherNext dashboard status optimization — 2026-09-23

Completed: pushed the pre-existing validated 6h/24h precipitation commit
`51839a8` unchanged. Split WeatherNext's cheap log/latest-run summary from
exact sample/forecast counts. Routine Streamlit reruns request only the summary;
the status expander offers explicit count refresh with a check time. Counts in
the current session clear after a scheduled attempt, newer run or successful
manual WeatherNext fetch. No cache TTL is needed. Source-level collection
health remains uncached; stored backfills without a finalized success are
labelled collection unverified.

Read-only live timings: old status calls 5.27–5.36 s versus new summary
0.12–0.13 s; Station network reruns 5.48 s versus 0.22–0.23 s.
Forecast vs Actual initial render 6.82 s versus 1.42 s. Explicit exact counts
still take about 5.10 s and only run on request. The live location, run,
forecast, observation and WeatherNext sample row counts were unchanged across
profiling. Evidence: ignored work/architecture-review/status-before.json and
status-after.json.

Validation: 79 unit tests pass, including focused cheap-summary/no-backfill
tests; disposable dashboard interaction and zero-write checks pass. Live
read-only AppTest rendered Forecast vs Actual, Overall Accuracy, Long-range,
Model Disagreement and precipitation 1h/6h/24h without errors. Background
collection tests pass; the scheduled task was not restarted or changed.

Remaining: no work for this bounded status task after its local checkpoint
commit. All-station rain and long-range query costs remain separate future
optimization tasks. Do not push the new local optimization commit automatically.

## Front-page usability checkpoint — 2026-09-22

Completed: automatic fair run pairing is the Forecast vs Actual default. It uses
the existing operational matcher and prefers the newest pair with exact observed
targets in the selected station/variable/chart window. Ranking: earlier issue,
later issue, then run IDs descending; never errors or sample counts. With no
observed pair it prefers a fair future pair and explains the missing observations.
No eligible pair produces a data-based explanation and an inspection-only label.
Advanced independent dropdowns remain available in Manual runs, including older
automatically selected runs. Disagreement drill-through preserves manual choices.
Selected-run MAE describes the displayed window with the same fairness rules.

Collection health is one healthy text summary plus collapsed details. Active
failures/delays remain visible; stale Yr retains its unrecoverable-history warning.
Resolved recent gaps remain inspectable within details. Health thresholds and
source-level logging are unchanged. No database, collector, backfill, long-range
scoring or scheduled-task change. No .env edits. The existing Streamlit process
was restarted once after stale imports were detected; its browser render then passed.

Validation: all 59 unit/regression tests pass. Eight focused pairing regressions
cover older fair pairs, newest qualification, missing pairs, variables/stations,
future fallback, retrieval/bucket constraints, exact timestamps/window limits and
conflicting observations. The expanded fixture UI test covers automatic/manual
selection, no-pair messages, collapsed healthy status, resolved gaps, active/stale
Yr warnings, long-range/disagreement navigation, and zero database writes.
A live read-only snapshot confirmed operational temperature/wind and long-range
scorer output identical to HEAD. Production render and browser screenshot passed;
all production connections were enforced read-only and .env remained unchanged.

Live Trondheim-Voll example captured 2026-09-21 22:16:54 UTC (72h window):
- Independent newest runs: Yr 21 Sep 21:30:08 / WeatherNext 21 Sep 12:00;
  latest common observed target 22:00 had leads 0.498h / 10h. Zero fair matches,
  so both shared MAEs were empty.
- Automatic runs: Yr 21 Sep 03:30:15 / WeatherNext 21 Sep 06:00. Five eligible
  shared observations; Yr MAE 1.100°C, WeatherNext MAE 1.514°C. All matched rows
  retain the same bucket, exact-observation and collected-before-target rules.

Evidence is local under work/auto-pair/ (tests, live example, unchanged-score audit
and screenshot). Worktree was clean before this bounded task; only related source,
tests and handoff documentation are included in its checkpoint. No push requested.
Remaining: none for this task. Existing dependency deprecation warnings are non-fatal.

## Read-only precipitation benchmark — 2026-09-22

Complete: canonical interval-end verification on a read-only/query-only SQLite
snapshot. No production code, dashboard, database, collector, schedule or secret
change. Current Frost: 17,160 hourly values, 29 stations, 2,943 non-zero.
Fair shared counts at 0–12/12–24/24–48/48–72h: 0/3,116/4,244/3,359.
The final bucket only covers Yr 50.34–56.50h and WeatherNext 48–54h.
Both forecasts issued and retrieved before interval start, leads to the same end,
same existing AND requested buckets, gap <=3h; error-independent deduplication.
There are 4,534 distinct station/hour targets across 10,719 bucket pairs.

Yr all-hour MAE 0.171/0.167/0.162mm vs WeatherNext 0.186/0.185/0.180mm.
WeatherNext wet-hour MAE and detection are better, with substantially more false
alarms. Dry/non-event observations are 84–86%; always-zero MAE beats both models
in this short sample. All-hour MAE alone is misleading. No numeric/duplicate/
source/timestamp corruption found; station biases and timing sensitivity remain
limitations. No justified change to the canonical one-hour mapping.

13 existing alignment/fair-pair tests passed; all matched intervals verified with
canonical helpers, scalar MAE and event counts reconciled. Full method, counts,
amount/event tables, five cases, station and lag checks, readiness assessment and
CSV evidence: work/precipitation-benchmark/REPORT.md (local ignored evidence).
Ready for a separately requested implementation with explicit dates/counts and
wet/event context; insufficient history for a stable general model ranking.
Remaining: none for this analysis. No commit or push; only handoff docs changed.

## Production hourly precipitation checkpoint — 2026-09-22

Complete: first-class precipitation in Forecast vs Actual and Overall accuracy.
The new bounded scoring/precipitation.py adapter reads existing tables, shifts
Yr to physical interval end, uses WN sample-level retrievals, validates amounts/
units/leads, and calls the existing pair_forecasts infrastructure. All rainfall
summaries and automatic/manual selection share its eligibility. Both issue and
retrieval strictly precede interval start; same existing + rainfall buckets,
<=3h gap; closest leads/newest run ties; no error-dependent pair selection.

Central wet threshold is >0.1mm/hour. Production exposes all-hour MAE, wet-hour
MAE, bias and hit/miss/false-alarm/correct-dry counts, POD, FAR and CSI. Undefined
rates are missing. The dashboard puts wet MAE/event skill in context, with a
compact amount/event table, dry-hour note, actual dates/counts/stations/leads,
empty 0–12h state and dynamic partial 48–72h label. Three forecast/actual amount
series are aligned to the physical hour; rainfall uncertainty is omitted.

Current all-history snapshot 2026-09-22 16:24 UTC, 29 stations per populated bucket:
- 0–12h: no samples/scores.
- 12–24h: 3,232 pairs, 507 wet; Yr/WN MAE 0.166894/0.181293mm,
  wet MAE 0.704339/0.584580mm; POD 0.654832/0.923077,
  FAR 0.492355/0.621971, CSI 0.400483/0.366484.
- 24–48h: 4,417 pairs, 659 wet; Yr/WN MAE 0.162825/0.180188mm,
  wet MAE 0.692868/0.563616mm; POD 0.664643/0.908953,
  FAR 0.508418/0.644932, CSI 0.393885/0.342873.
- Partial 48–72h: 3,501 pairs, 485 wet; Yr/WN MAE 0.158983/0.175437mm,
  wet MAE 0.792784/0.618118mm; POD 0.569072/0.892784,
  FAR 0.535354/0.665895, CSI 0.343711/0.321217.
  Actual Yr 50.34–56.50h / WN 48–54h, not full 72h coverage.

Validation: all 69 unit/regression tests pass, including 10 new rainfall tests;
fixture UI checks cover rainfall automatic/manual, amount/event context, filters,
empty and partial buckets plus all previous pages and zero fixture DB writes.
Live AppTest covers rainfall chart/accuracy/buckets and long-range/disagreement
with every production DB connection forced read-only and .env unchanged. Browser
rendering of rainfall chart and compact aggregate/partial views passed. Dashboard
process alone was restarted to load modules; scheduled collection was untouched.

All 10,719 original benchmark pairs, run IDs, leads and values match production
on the fixed overlap ending 22 Sep 10:00 UTC. Two additional pairs at that endpoint
come from newly filled Frost observations at FV17 Våg and Nyrud, absent from the
saved benchmark snapshot. Temperature/wind and long-range outputs were identical
to HEAD on the same read-only snapshot. No DB/schema, collector, station, schedule
or secret changes. Statistical limits remain: short correlated history, unequal
leads and gauge/grid representation. No winner/composite/calibration added.

Evidence: work/precipitation-production/ (current/fixed CSVs, benchmark identity,
new-observation audit, test logs, live read-only UI audit and screenshots).
Remaining: none for this requested implementation. The four benchmark handoff
files were already modified at start; preserved and extended. Clean-start commit
condition was not met: no commit, staging or push. Existing deprecation warnings
are non-fatal. Application remains runnable.

## Collection health checkpoint — 2026-09-17

Completed: a compact dashboard table now shows Yr/MET, WeatherNext, and Frost last
successful retrieval, UTC-safe age, and OK/Delayed/Stale state. It is placed above
the existing tabs; WeatherNext details, collection logs, and manual controls remain
collapsed. The table reads actual completed collection outcomes rather than valid
forecast/observation times.

The existing six-hour Windows schedule was inspected and left unchanged. Thresholds
are OK through 8 hours, Delayed above 8 through 12, and Stale above 12. A latest
source error yields Delayed immediately. Stale Yr displays the unrecoverable-history
warning. Recent Yr gaps are consecutive successes more than 12 hours apart in a
7-day window.

For historical continuity, the parser reads existing finalized combined log lines.
Going forward, `background_collect.py` appends a stable source-level outcome as
each collector completes, so a later Frost or WeatherNext failure cannot hide a
successful Yr retrieval. Missing credentials/disabled collection are recorded as
SKIPPED and do not advance last success. No database schema was added.

Validation: 51 unit/regression tests pass; the isolated background-run test records
all three source completions; the disposable Streamlit test verifies healthy and
stale rendering, the exact Yr warning, long-range temperature behavior, and zero
database writes. Production is currently OK for all three sources with last success
at 2026-09-17 04:13 UTC and no recent Yr gap. Database counts remain 4,504 runs,
344,008 forecast points, and 189,084 observation rows.

Remaining: no feature work is pending. The next ordinary scheduled run will be the
first production run to emit the new explicit per-source lines; legacy summaries
remain sufficient until then.

## Historical WeatherNext temperature checkpoint — 2026-09-17

Completed: focused 0.05° station-head archive backfill for the existing 50 active
stations, using existing normalization/storage and six temperature statistics.
34 initializations (2026-09-05 12:00 through 2026-09-13 18:00 UTC), 88 selected
image slices, and leads 72/120/168/216h added 4,400 forecast points, 1,700
station/run rows and 26,400 statistic values. Valid range: 2026-09-08 12:00
through 2026-09-16 18:00 UTC. These historical runs contain sparse temperature
horizons, not full hourly/multivariable forecasts.

Identical second execution added zero values. Duplicate run/point/statistic keys
are all zero. Before/after row-content checks preserved every existing station,
run, forecast, observation and WeatherNext statistic. MET remains 209,254 points;
WeatherNext grew 108,000 → 112,400; Frost temperature/wind/precipitation remain
171,313 / 171,037 / 13,344 non-null values. No migration was required.

Read-only retrospective shared counts at 72/120/168/216h: 1,603 / 1,215 / 824 /
438. Yr MAE: 1.077 / 1.325 / 1.490 / 1.532 °C; WeatherNext mean MAE: 1.065 /
1.300 / 1.708 / 1.720 °C. Exact Frost targets, both nominal ±3h and pair gap ≤3h,
one error-independent closest-lead pair per station/target/horizon. Largest gap:
2.677h. All 50 stations contribute at each horizon. The short period and usually
shorter WeatherNext lead limit conclusions, especially the tiny 3/5-day gaps.

Original Earth Engine ingestion was checked before each valid time and retained
in local manifests. Local retrieved_at stays truthful. Production scoring still
requires local retrieval before valid time: operational long-range shared counts
remain zero. No production scorer, UI, scheduled-task, secret or other collector
changes were made for this task.

Validation: all 39 unit/regression tests pass; fixture UI interactions pass with
zero writes; production dashboard render passes with no exceptions. Existing
non-fatal dependency deprecation warnings remain.

Evidence and exact commands: outputs/temperature-backfill/REPORT.md. All 4,080
matches, aggregate metrics, actual lead distributions and four individual cases
are saved as CSV/JSON there. Plans, original image metadata, preservation checks
and logs are retained under work/temperature-backfill/. Both folders stay local
and ignored. Reusable helpers are backfill_weathernext_temperature.py and
analyze_historical_temperature.py; coverage is in test_weathernext_backfill.py.
Source/doc changes are local and uncommitted; no push was requested.

Remaining: none of this task. Continue operational collection for live-collected
long-horizon validation. Dashboard additions, rainfall and calibration scoring
require separate work. Never restore an old database to undo this additive task.

## Verified retrospective scoring and compact view — 2026-09-17

Completed: historical-verified WeatherNext temperatures now qualify for
retrospective scoring through the existing database. An additive
`weathernext_verified_history` table links each point to its verified original
publication time, exact asset, initialization, lead and mean value. Registration
checks the complete saved backfill manifest and stored station/sample identity
inside one transaction. Existing forecast values and retrieved_at are unchanged.
4,400 points registered; identical registration added zero. Before/after
row-content checks confirmed every existing station, forecast and observation
was preserved; foreign-key checks passed. Future saved temperature backfills
register their verified provenance automatically.

The new **Long-range temperature** tab shows four compact 3/5/7/9-day rows:
Yr and WeatherNext MAE, signed MAE difference, shared sample count, matched dates,
plus the actual overall evaluation period in UTC. Filters select evaluation
window and station; an expander shows bias, actual leads, original availability
rules and counts of historical samples. No score is shown for an empty horizon.

Scoring reuses the audited exact-horizon matcher: original issue and verified
availability before target, exact Frost time, both nominal ±3h, pair gap ≤3h,
and one error-independent closest-lead pair per station/time/horizon. Missing
or inconsistent verification falls back to collected-before-target eligibility.
Operational Overall accuracy and selected-run scoring retain their existing
rules. Temperature is the only historically certified variable.

Validation: 45 unit/regression tests pass, including idempotency, conflicting
provenance rollback, missing-table compatibility, malformed leads, exact-time
observations, period/station filters, zero-sample summaries and read-only scoring.
The expanded fixture UI test passes, including historical scores, date/count
labels, filter/empty states and zero database writes. Live browser verification
confirmed the compact table and all four horizons with production data.

The database-backed scorer reproduces all 4,080 audited historical comparisons:
1,603 / 1,215 / 824 / 438 samples. Each horizon ends September 16 18:00 UTC and
starts September 8 / 10 / 12 / 14 at 12:00 UTC respectively. Scores match the prior
report exactly; read-only query plus summary took approximately 1.5 seconds.
Evidence: work/retrospective-view/ (migration checks, test logs, live summary and
screenshot). Runtime evidence and database remain ignored by Git. The existing
scheduled collection continued normally during the pause in this task.

Remaining: none for the requested retrospective eligibility/view. No new provider,
service, dependency in requirements, or collection/scheduling change. Changes are
local and uncommitted; no commit or push was requested.

## Git checkpoint review — 2026-09-17

Reviewed the complete mixed worktree against the prior implementation checkpoints.
The source/test/doc changes belong to shared accuracy and model disagreement,
historical temperature backfill, verified retrospective scoring, the compact
3/5/7/9-day view, collection health and per-source completion logging. No unrelated
or suspicious changes were found. These interdependent changes are grouped in one
checkpoint: `Checkpoint long-range verification and collection health`.

Validation at checkpoint: all 51 unit/regression tests pass; the fixture dashboard
interaction test passes, including healthy/stale health states, long-range filters
and zero database writes. Production dashboard startup and both requested views
pass with enforced read-only database connections. Current shared long-range counts
are 1,607 / 1,219 / 828 / 442; all three collection sources report OK, last success
2026-09-17 10:12 UTC. The existing .env is unchanged. No collector, backfill,
migration, scheduled-task action, or application behavior change was performed.

Only reviewed source, tests and documentation belong in this checkpoint. Database,
credentials, logs, environments, screenshots and generated evidence remain ignored
and local. Validation evidence is under work/checkpoint-review/. Commit is local;
no push is requested. No feature work remains for this checkpoint task.

## Dashboard completion — 2026-09-16

Compact dashboard work is complete. Final validation: all 18 regression tests and
the disposable-database UI test passed; grouped accuracy bars were checked in the
browser with production data. No dashboard migration, collector change, scheduled
task change or historical-data write was performed. No dashboard work remains.

## UI polish completion — 2026-09-16

- Completed the focused daily-use visual pass in `app.py`: balanced compact run
  controls, subtle consistent metric cards, refined thinner forecast lines and
  softer uncertainty band, compact horizontal MAE dots with provider shapes,
  26px result rows with one-decimal numbers and missing-value dashes, and
  collapsed system status/logs/admin sections. Existing tabs and scoring remain.
- Validation: all 18 regression tests and the existing disposable-database UI
  interaction test pass (including no database writes). Live browser review
  confirmed the chart, table, cards, and collapsed operational sections.
- Complete; no UI work remains. Database, schema, collectors, secrets, and
  scheduled task were not modified. Operational follow-up remains below.

## GitHub setup checkpoint — 2026-09-16

- Initialized Git in place; application behavior and scheduled task unchanged.
- Private remote: https://github.com/Stranden1/weather-forecast-verification
- Ignores cover secrets, environments, runtime data, logs, screenshots and scratch work.
  No local database, backups or working files were removed.
- Updated README/quick start; retained the fixture UI test under tests/ and exported
  50 active stations as metadata in config/stations.json (not auto-imported).
- All 18 regression tests, fixture UI test and production dashboard render passed.
  Staged secret scan found no local credential values or recognized token/key patterns.
- Complete: initial commit ef2871b pushed to main; private visibility verified. Remote commit/tree matched locally, with 37 code/config/documentation files and no runtime data. No GitHub setup work remains.

## Accuracy dashboard checkpoint — 2026-09-16

Completed: variable audit (SCORING.md); wind Forecast vs Actual; exact-time observed
values; paired Overall Accuracy with variable/period/station/lead filters, MAE,
bias, equal sample counts, MAE difference and daily trends; future Model Disagreement
with station/run navigation. Existing scoring buckets/aggregation are reused.

Validated: 27 unit/regression tests; expanded fixture UI test including all new
controls, empty states, drill-through and unchanged fixture database; live local
Streamlit startup and browser checks with production data. No browser page errors.
All-history pairing plus disagreement queries took about 0.7 seconds per variable.
The read-only audit found 785 temperature and 676 wind station/time/bucket pairs;
counts will grow as normal collection continues.

No database migration or historical-data write, collector change, task restart,
credential change or new provider. Application remains runnable. Existing runtime
deprecation warnings are non-fatal. Files are local, not committed/pushed in this task.

Remaining: no requested dashboard feature is pending. Continue ordinary collection,
then evaluate longer matched history. Precipitation/pressure/direction/cloud scoring
remain deliberately disabled pending compatible observations/definitions. The newer
15 September 18:00 WeatherNext cycle is stored, satisfying the earlier cycle follow-up.

## Frost hourly precipitation checkpoint — 2026-09-16

Completed: the existing Frost collector now requests
`sum(precipitation_amount PT1H)` only for capable active stations and stores it in
the existing `observations.precipitation_1h` field. Frost `referenceTime` remains
the canonical end of `[T-1h, T)`. The normal `sync_recent` and background path now
include precipitation; temperature and wind collection is unchanged.

Production backfill: 13,118 station-hours across 29 of 50 active stations, from
2026-08-26 16:00 through 2026-09-16 14:00 UTC; 2,162 values are non-zero. Total
observation rows are 184,259. Existing non-null temperature and wind counts are
168,873 and 168,580 after a normal collection run. An exact-range rerun changed
none of these counts; duplicate keys and off-hour precipitation rows are both zero.

Alignment sanity check: for Bergen-Florida (`SN50540`) and
`[2026-09-15 23:00, 2026-09-16 00:00 UTC)`, Frost stores 10.1 mm at end time
00:00, WeatherNext stores 3.373389 mm at end time 00:00, and Yr/MET stores
6.6 mm at start/`valid_at` 23:00. These are three forecasts/measurements for the
same physical hour, not an accuracy score.

Validation: 31 focused tests pass. They cover exact Frost metadata, supported
station filtering, timestamp preservation and cross-provider interval mapping,
merge preservation, rejection of incompatible intervals, and idempotency. The
ordinary combined Frost run completed with no errors. No schema, scorer,
dashboard, station-network, provider, secret, or scheduled-task changes were made.

Remaining before rainfall scoring: teach the scoring path to compare by canonical
interval end (`Frost T = WeatherNext T = Yr valid_at + 1h`) while enforcing the
existing retrieved-before-target rule, identical observed targets, and comparable
lead times. Rainfall scoring remains disabled.

## WeatherNext integration checkpoint — 2026-09-15

### Completed

- Added concise project handoff documents: `PROJECT_STATUS.md`, `NEXT_STEPS.md`,
  and `DECISIONS.md`. They reflect the live database and scheduled collection
  state as of 2026-09-16.
- Dashboard compact-layout pass completed: Forecast vs Actual is the first tab,
  with station/run/window selectors on one row, compact metrics, a 72-hour default
  chart, amber Frost actuals, WeatherNext p10–p90 shading, recent results and MAE.
  Network and overall accuracy are separate tabs; supported Streamlit versions
  load tab bodies only when selected. Manual actions/settings are in collapsed
  **Admin / Manual controls**. WeatherNext status is secondary and logs collapsed.
  Dashboard startup no longer seeds or migrates the database: browsing uses a
  read-only connection. Collectors, schema, historical data and scheduling were
  not changed. All 18 regression tests passed. The new fixture UI test verifies
  selection changes, future-observation masking, collapsed Admin and zero data writes.
  A dashboard-only read query now precomputes observation-hour keys while retaining
  the original scoring rules; production reads completed in approximately 2.3 seconds
  for temperature and 5.2 seconds for wind. Accuracy bars are grouped by provider,
  not stacked. The browser layout was checked at 1280×720 with real stored data.
- Added a read-only **Forecast vs Actual** temperature section to the Streamlit
  dashboard. It defaults to Trondheim-Voll, offers independent recent Yr/MET and
  WeatherNext run selectors, overlays hourly Frost observations and WeatherNext's
  p10–p90 interval, lists elapsed-hour errors, and compares MAE by lead-time bucket.
  All 17 tests and the disposable-database Streamlit startup check pass. A read-only
  production check confirmed the default view has both current runs, 360 temperature
  timestamps, a complete uncertainty band, and matched elapsed Frost hours.
- Added a compact, read-only WeatherNext dashboard status panel backed by the
  authoritative database and finalized WeatherNext entries in `data/background.log`.
  It shows stored run/row totals, collection timing and additions, collector state,
  and the 15 most recent WeatherNext background outcomes in a collapsible table.
- The authoritative `E:\WeatherApp` was updated incrementally; no database was replaced.
- New collector, CLI, app control, and guarded background integration are installed.
- Additive `weathernext_samples` table and `weathernext_values` view are installed.
- Temperature, wind speed and hourly precipitation: mean plus five percentiles.
  Wind u/v means and mean sea-level pressure are included with explicit units.
- Earth Engine authenticated successfully against `weatherapp-508323`.
- All 13 tests passed in the original Python 3.13.15 environment, SDK 1.7.43.
- Streamlit startup passed on a disposable database; WeatherNext control is present.
- Live run 2026-09-15T06:00:00Z passed 360-hour validation for Trondheim-Voll,
  three stations and all 50 active stations. Full repeat for Trondheim added zero rows.
- 50 WeatherNext runs, 18,000 forecast points and 378,000 statistic values are stored.
- Initial historical rows were unchanged immediately after the full live test.
- A later ordinary scheduled MET/Frost run was reconciled: no rows lost; two
  missing measurements filled; five source-check timestamps refreshed. The newer
  authoritative data was preserved.
- `.env` now sets `EARTH_ENGINE_PROJECT=weatherapp-508323` and `WEATHERNEXT_ENABLED=1`.
- The existing Scheduled Task was inspected, not modified or restarted. It already
  targets the correct Python, script, working directory and user account.

### Remaining

No manual setup or integration work remains. The enabled WeatherNext branch ran
successfully in the ordinary scheduled collection beginning 2026-09-15 22:10 UTC.
It selected the already-stored 12:00 UTC model run and correctly added zero values;
the dashboard now reports **waiting for new run**. The next operational check is a
scheduled collection of a genuinely newer model cycle.

Rainfall is stored with units in the normalized table. Rainfall scoring/interval
alignment with MET and Frost was not part of this first integration and is not enabled.

### Resume evidence

- `work/integration-status.json`: final integration state.
- `work/live-validation.json`: completed live stages and WeatherNext row counts.
- `work/history-before.json`: original history baseline (retain unchanged).
- `work/history-after-live-validation.json`: exact preservation after live testing.
- `work/scheduled-update-reconciliation.json`: expected later background additions.
- `work/history-after-scheduled-before-enable.json`: subsequent validated baseline.

The application is runnable and all migrations are complete. To disable only
automatic WeatherNext collection, set `WEATHERNEXT_ENABLED=0`; retain its schema
and history. Do not restore an older database over the current database.

