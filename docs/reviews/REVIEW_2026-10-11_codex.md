# Independent WeatherApp inspection — 11 October 2026 (Codex)

## Summary

The project works, and the external timer has substantially improved cloud collection. All **125 cloud tests and 79 local tests pass**. The live page contains **36 scored days, 215,743 rows, through 10 October**. Its one-day headline numbers reproduce from encrypted history. There is no established overall winner: temperature, wind, and rain using WeatherNext's median are all too close to call at one day.

The main problems are interpretation and visibility: a rain replay's calendar-day boundary is wrong, green collection status hides individual station outages, rain views silently switch between WeatherNext's mean and median, and the mobile page takes too long to reach a simple answer. The cloud has useful unused data, but it cannot replace every analysis supported by the PC's full forecasts.

**Keep the PC collector running for now.** The eligible timer-era coverage checks pass for the horizons reached so far. Longer horizons, the drifting station network, and the desired future analyses still need decisions. The database is growing approximately **0.31 GB/day**, or **112 GB/year** at the recent rate.

## Scope, method and verification

- Followed AGENTS.md and read the requested handoff documents, PLAN_WEBPAGE.md, WEATHERNEXT.md and the September review. Recorded independent findings before opening Claude's REVIEW_2026-10-11.md.
- Ran `git status`, `git log --oneline -20` and, after network approval, `git fetch`. HEAD is `84e102c`, one commit ahead of origin/main; the difference is NEXT_STEPS.md only. Initially the only untracked file was Claude's review. No pull, commit or push.
- Used the existing `.venv` and disabled Python bytecode writes. The first sandboxed test attempt failed on Windows Temp permissions; the rerun with working disposable fixtures passed. These were environment errors, not application failures.
- Ran the requested cloud suite, all root `test_*.py` modules, `tests/dashboard_ui_test.py`, and Project HQ tests. Results: **125 + 79 unit tests passed**, dashboard interactions passed with fixture history unchanged, HQ **7 passed / 1 skipped** because Windows symlink creation needs privileges.
- SQLite connections used `mode=ro` and `PRAGMA query_only=ON`. History was decrypted in memory. A read-only `quick_check` was interrupted after **55.9 seconds**: database integrity remains unverified, rather than failed.
- Recreated page JSON from history in memory using the existing exporter with past-value publication enabled, matching live settings. Served unchanged `site/` files locally. Bundled Node Playwright used installed Chrome; no packages were installed. Browser responses were supplied from local files and memory because the sandbox blocked direct browser networking. Real map tiles were fetched separately after approval. This verifies rendering and interactions, not browser-to-production transport; live health and scores were independently fetched over HTTPS.
- No application, database, history, workflow, settings or handoff files were edited. Only this report was created in the project. Approved screenshots and inspection evidence are outside the project in Windows Temp. Secrets were loaded only in memory and never printed.

### Operational snapshot

All 15 recent GitHub runs returned success: 11 collection-workflow dispatches and 4 test runs. A successful dispatch can be a gate skip, so I inspected steps too. [Run 38139953673](https://github.com/Stranden1/weather-forecast-verification/actions/runs/38139953673) collected and deployed at **11 October 12:37–12:39 UTC**. [Run 38141910598](https://github.com/Stranden1/weather-forecast-verification/actions/runs/38141910598) correctly skipped collection and deployment at 13:07 UTC.

The [live health JSON](https://stranden1.github.io/weather-forecast-verification/data/health.json) reported last collection **12:37:39 UTC**, all four sources OK, **17 actual collections / 16 expected** over 48 hours. The page caps this to “16 of 16.” The restored remote state contains **42 collections since the timer began**, spaced **2.500–3.002 hours** apart. The public line omits ECMWF although its status is in the JSON (`site/app.js:587`).

Windows task: **Ready**, result **0**, last start **11 October 12:10:02 Oslo**, next run **18:10 Oslo**, zero missed runs. It still uses the existing `.venv`, `background_collect.py`, and a 30-minute limit. The local log records all three sources OK and completion at **12:12:48 Oslo**.

## Broken / urgent

### B1 — Rain replays label a shifted 24-hour window as a day total

**Verified data correctness problem.** Frost/Yr/WeatherNext rain timestamps are interval ends. `cloud/replay.py:147` groups observations by the end timestamp's date; `:209` applies the same grouping to forecast totals. Ends 00:00–23:00 cover **23:00 on the previous day through 23:00 on the labelled day**, rather than midnight to midnight.

Recomputed from deduplicated observations in history, with all 24 hours present in both calculations:

| Bergen date | Current replay window | UTC midnight-to-midnight |
|---|---:|---:|
| 15 September | 46.8 mm | **56.3 mm** |
| 16 September | 22.4 mm | **12.3 mm** |

Thus the 16 September replay meets the site's 20 mm “heavy rain day” threshold only under the shifted window. The hourly headline scoring remains correctly aligned; this finding concerns daily aggregation and event selection. Decide whether days mean UTC or Oslo civil days, then use interval boundaries consistently. Oslo days also require handling 23/25-hour daylight-saving days. Evidence: PRECIPITATION.md:5, `cloud/replay.py:147`, `:163`, `:209`, and screenshot **rain-replay.png**.

### B2 — Source success hides stale stations and missing observations

Remote state at inspection showed these latest exact-hour observations:

| Station | Last observation, UTC | Approximate age on 11 October |
|---|---|---:|
| SN20925 Wisting | 30 September 21:00 | 10 days 16 hours |
| SN20961 Alvheim | 9 October 22:00 | 39 hours |
| SN94190 Revsbotn | 9 October 14:00 | 47 hours |

**Enningdalen SN1120 has recovered**, including exact-hour local observations through 11 October 09:00 UTC; the older handoff warning is stale. Alvheim is stale locally as well. A two-day warning would already flag Wisting; Revsbotn is approaching it. The live line still says Frost ✓ because it reports source totals, not station freshness (`cloud/health.py:89`, `site/app.js:587`).

Recent daily observation coverage is **95.25% on 9 October and 93.25% on 10 October**, with no late finalization. These figures measure station-hours with *any* finite variable, not completeness for each variable. They are below 100% but above the deliberate 80% preparation threshold (`cloud/score.py:147`, `:184`). Coverage and stale-station warnings should be visible before new rankings.

### B3 — Retirement needs the remaining dated checks and a scope decision

Re-executed the existing coverage comparison in memory against read-only SQLite and fresh remote state, suppressing its output-file write. On the **45 shared stations**, timer-era overlap is **100% at every eligible tested horizon** on 9–10 October: 6 hours through 2 days on both dates, WeatherNext's partial 3-day timer-era slots on 9 October, and both services' full 3-day slots on 10 October. Remaining forecast gaps precede timer activation.

The script's overall cloud/local row-count ratio can hide misses with extra cloud hours: on 9 October Yr reports **100%** despite **43 missing and 43 extra** hours. Actual overlap is **99.1%**; WeatherNext's overall ratio is 98.4%, but overlap is **94.6%**. Timer-era calculations already use intersections and are sound. Evidence: `work/coverage-compare/compare_cov.py:79`, `:85`, `:100`; fresh calculation described above.

- **Around 12 October:** check 9–11 October; the first fully timer-era 5-day target date is 12 October.
- **14 October:** first fully timer-era 7-day target date.
- **Around 18 October:** evaluate completed 15–17 October, including the first fully timer-era 10-day target date, 17 October. Apply the existing **at least 99% overlap at every eligible horizon** criterion; explain zero denominators and small samples.
- Reconcile the five different stations on each side and decide which full-forecast analyses must survive before stopping the task. Retaining weather.db preserves past data, but does not collect future full runs.

Evidence: NEXT_STEPS.md:17 and the freshly reproduced comparison. No task was stopped or changed.

### B4 — Two upcoming operational deadlines

**19 October 2026:** both workflows use `ubuntu-latest` (`collect.yml:33`, `tests.yml:8`). Today's run used Ubuntu **24.04.5**; its check annotation explicitly says migration to Ubuntu 26 begins on 19 October, linking [GitHub's runner announcement](https://github.com/actions/runner-images/issues/14748). Watch both tests and a real collecting/deploying run after the change. This is a compatibility risk, not a current failure.

**Before 5 November 2026:** renew the external timer's repository-scoped token. Recorded expiry is **17:15 UTC / 18:15 Oslo** (`SETUP_CLOUD.md:102`). The hourly GitHub fallback remains, but previously missed runs; expiry can bring back coverage gaps. I did not read the token or access the timer account's notification configuration.

## Visual

### V1 — The main answer is too far down on a phone

The page looks orderly at 1280 px, with useful difference charts, table alternatives and distinct chart shapes. Settled layouts have **no page-wide horizontal overflow**, including an expanded table; dark mode renders correctly and there were no captured JavaScript errors.

However, at **375 × 812**, the first score tile begins at **y=887 px** and the verdict at **y=1430 px**. The top screen is largely the monthly paragraph, its qualification, the introduction and filters. Total default page height is **10,174 px** on mobile and **6,464 px** on desktop. A first-time visitor gets several conditional results before understanding the main one-day answer. Desktop is understandable within ten seconds with careful reading; mobile does not provide an easy ten-second answer.

Propose one short lead answer, a compact comparison, then optional detail. The exact layout is a user choice; another full card would worsen the current problem. Evidence: `site/index.html:16`, `:29`, `site/style.css:160`; desktop/mobile top screenshots and full-page screenshots below.

### V2 — “WeatherNext” changes meaning between rain sections

Tiles, horizon verdicts and bias use the **median**. The map, station series, trend and Patterns use the **mean**, often labelled just WeatherNext (`cloud/summarize.py:267`, `:275`, `site/app.js:398`, `:459`, `:533`). At one day the two rain errors are **0.131 vs 0.158 mm**, so this distinction changes the result. A visitor can see a median headline with no clear winner and a mean-based view favouring Yr without an obvious explanation. Steadiness at least explicitly says it uses the average.

Use one declared rain default throughout, or label every exception beside the number. Evidence: **rain-map.png**, `site/app.js:29`, `:398`, `:459`.

### V3 — Filters and time-axis labels promise more than they do

“Last 30 days” controls tiles/horizons and slices trend entries, while the map, Patterns, calibration, bias and steadiness remain all-time. Bias/steadiness disclose that in small notes; the other affected views do not clearly do so. The monthly text also remains independent of the variable/period selection.

Moreover “7-day rolling” means **seven available entries**, not seven calendar days (`site/app.js:390`). At the 5-day horizon, the seven entries ending 1 October begin **20 September**, because 25–29 September are absent. A categorical axis spaces 24 September and 30 September like adjacent days. “Last 30 days” in the trend similarly means 30 entries (`:397`), potentially spanning more than 30 days when gaps occur. Current headline dates do not expose that latter problem yet. This should be corrected or labelled explicitly; do not visually bridge missing observations as uninterrupted time.

### V4 — Accessibility gaps are measurable

Light-mode muted text has contrast **4.03:1 against the background** and **4.25:1 against cards**, below the **4.5:1** minimum for ordinary small text. Dark-mode muted text is **5.16:1** against cards. The light-mode captions, tile labels and table headers need darker text. Evidence: `site/style.css:7`, `:53`, `:73`, `:91`, `:130`; calculated from computed browser colours using the [W3C contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

Station circle markers have no keyboard-selectable equivalent: only map controls/attribution enter the focus order. Add a station selector or searchable list. The existing map conveys relative error through colour, without per-station uncertainty; “Who wins where” implies more evidence than is calculated. Canvases provide little accessible data, and the station canvas has no label at all (`site/app.js:463`). Horizon/bias/steadiness tables help, but trend, station and replay need accessible equivalents. `radiogroup` containers hold pressed buttons rather than radio controls (`site/index.html:31`, `site/app.js:43`), with no radio-group arrow-key behaviour.

### V5 — A one-point replay hides the measured reference

The 16 September Bergen replay contains only the 6-hour point. The measured dataset has one point, zero point radius and therefore no line segment. The legend says Measured, but the **22.4 mm reference is invisible in the chart**. Its text remains visible. Evidence: `site/app.js:512`, **rain-replay.png**. A horizontal reference or visible point would avoid this.

## Data

### D1 — Headline numbers are correct; scope matters more than rounding

Independent direct error calculations match the [live leaderboard](https://stranden1.github.io/weather-forecast-verification/data/leaderboard.json):

| One-day forecast | Yr mean absolute error | WeatherNext error | Paired hours / days | Verdict |
|---|---:|---:|---:|---|
| Temperature | 0.901 °C | 0.909 °C mean | 24,340 / 24 | Too close |
| Wind | 1.464 m/s | 1.425 m/s mean | 20,930 / 24 | Too close |
| Hourly rain | 0.136 mm | 0.131 mm median; 0.158 mean | 14,520 / 24 | Median too close; mean loses |

Temperature's difference range is **−0.026 to +0.038 °C**; wind's **−0.081 to +0.004 m/s**; rain median's **−0.013 to +0.002 mm**. The page rounds the last upper bound to 0.00, which makes the verdict less intuitive. These are station-hour pairs, not independent forecasts; whole-day resampling is correctly used for verdicts (`cloud/summarize.py:61`). There are no duplicate station/target/horizon keys and no missing medians in these headline cohorts.

The midpoint of Yr and WeatherNext gives **0.802 °C** temperature error, **11.0%** below the better single service, and **1.329 m/s** wind error, **6.7%** lower. Those gains reproduce, but have **no uncertainty interval or independent future validation** (`cloud/summarize.py:101`). Treat them as descriptive results so far, not guaranteed improvements.

### D2 — Cohorts, regions and station weighting should be explicit

The 36-day banner includes days without a one-day WeatherNext pair; the headline uses 24 days. One-day wind uses **44 stations**, rain **29**, temperature **50** over the full record. Fourteen stations are classified as offshore in the height metadata; they supply **26.5% of temperature** and **27.5% of wind** headline pairs. A national station-hour average is therefore not a population-weighted answer for Norwegian towns.

The cloud and PC currently share **45/50** stations. Local-only: SN71990, SN78800, SN92750, SN94640, SN96850. Cloud-only: SN20925, SN76956, SN92895, SN94190, SN96310. Local weekly discovery and fixed cloud config explain the drift (`background_collect.py:43`, `cloud/config.py:15`). Preserve old station identities/history when reconciling.

Sampling also changed on 26 September. One-day temperature contains **13,210 bilinear pairs** and **11,130 earlier-method pairs**, with a transition day contributing to both. “Last 30 days” is not a clean current-method comparison. Displaying method/date cohorts, land/offshore, region and elevation groups can answer more useful questions without altering immutable history. Small groups need day counts and uncertainty, not winner colours alone.

### D3 — Additional models are ready for a careful temperature/wind comparison

IFS and AIFS each have **75,556 non-null temperature/wind rows over 14 dates** in stored history. At one day, **12,005 common temperature pairs over 13 days** give Yr **0.910**, WeatherNext **0.916**, IFS **1.105**, AIFS **0.946 °C**. Common wind pairs number **10,396**, with errors **1.550 / 1.568 / 1.769 / 1.677 m/s** respectively. These descriptive checks are not verdicts.

Use the intersection where all displayed providers and observations exist; do not compare their newer subset against the 24-day Yr/WeatherNext headline. Open-Meteo temperature is adjusted to station elevation, while primary WeatherNext temperature is not (`cloud/openmeteo.py:59`). AIFS rain is distributed from six-hour values; hourly ranking would compare different temporal detail. A six-hour evaluation needs complete aligned periods and a declared forecast-run convention.

Also, this is a comparison of delivered products. Yr combines regional forecasts, post-processing and ECMWF ensemble forecasts; it is not one raw “physics model.” [MET's data-model documentation](https://docs.api.met.no/doc/locationforecast/datamodel.html) explains that distinction.

### D4 — Probability and uncertainty have immediate explanatory value

Yr rain probability is retained in **63,975 scored rows**, including **16,195 one-day rows**, but never exported as a reliability view (`cloud/yr.py:71`, `cloud/score.py:24`). “When it says 70%, how often does it rain?” and a probability-error score are feasible. First verify the provider's precipitation threshold and match its period to observed events. WeatherNext's stored quantiles are not exact rain probabilities or ensemble members; any probability reconstructed from them must be labelled approximate.

Calibration by horizon is **already calculated and selectable on the page**, but buried under Patterns. A compact overview would help. Temperature inside-range rates, Yr/WeatherNext: **84.3/74.8% at one day**, **85.0/74.7% at two**, **59.4/73.9% at three**, **67.3/73.0% at seven**. The intended p10–p90 rate is about 80%. At one day wind is only **46.8/46.0%**, an important limitation missed by a temperature-only story. Current inside-range rates use different provider cohorts; paired range score/width use a common cohort. Compare coverage on common pairs too (`cloud/summarize.py:164`).

### D5 — Practical event scores and disagreement are possible, with limits

- **Frost yes/no and wind thresholds:** hourly paired values support detection, missed events and false alarms by horizon. “Below freezing” MAE currently conditions on observed frost; it does not answer whether a forecast correctly warned of frost.
- **Rain yes/no:** already partly available. At one day, **86.2% of matched hours are dry**. Yr catches **71.2%** of wet hours with **49.1%** false alarms; WeatherNext median catches **86.1%** with **54.9%** false alarms. Lower amount error alone cannot decide which warning behaviour a visitor prefers.
- **Disagreement:** stored paired values can show whether errors and blend gains change when services disagree strongly, and identify persistent station/time-of-day differences. Distinguish past analysis from a future recommendation.
- **Daily max/min and rain tomorrow:** complete hourly observations support sampled-hour extrema and complete daily amounts; they are not exact instrument-reported daily extrema. The cloud's same-horizon hours often come from different runs. Aggregating them describes a rolling-lead forecast, not “the complete forecast issued yesterday.” A fixed-run daily product needs coherent whole-day forecasts retained prospectively, or the PC's full runs.
- **Daily ensemble median:** the replay sums hourly medians (`cloud/replay.py:221`); that is not generally the median of the daily total. Keep that label explicit. Stored marginal quantiles cannot recover cross-hour ensemble dependence.

## Code / operations

### C1 — September's major persistence defects are fixed

Restore fails closed, encrypted history is pushed and checked before pending rows are pruned, state pushes have an explicit lease, and source failures are reported after persistence/deployment. Verified tests cover missing/wrong-key state, failed pushes, interrupted publication and stale leases (`cloud/persistence.py:69`, `:105`, `:146`; `cloud/tests/test_persistence.py:74`, `:113`, `:129`, `:160`). All **36** history files authenticate/decrypt; **13** newer sidecars verify against their exact encrypted day files. No evidence of a current persistence failure.

Day preparation is deliberately irreversible once immutable history is secured. It waits for 80% overall observation coverage or the 72-hour deadline, but it can miss later observations at individual stations even on an otherwise complete day. That tradeoff should be visible rather than described as complete coverage (`cloud/score.py:184`).

### C2 — The PC is expensive, but retirement is not feature-equivalent replacement

Read-only database measurements: **7,743,541,248 bytes (7.74 decimal GB)**, **38,204,400 WeatherNext statistic rows**, **2,453,776 forecast points**, **407,258 observations**, zero free pages. E: has approximately **264 GB free**. Compared with the recorded 6 October **6.21 GB** snapshot, the rounded estimate is **307 MB/day**, **112 GB/year**. Actual recent collection adds **1,512,000 statistic rows/day** on 8–10 October, corroborating the mechanism. This is a multi-day estimate, not a directly measured allocation delta for each individual day. Evidence: read-only SQL, local log, PROJECT_STATUS.md:50.

Cloud encrypted history totals **11.66 MB**; the latest four days average approximately **0.65 MB/day**, around **0.24 GB/year** if comparable. Recreated page JSON is approximately **626 KB**. The cloud's compact design is therefore working. Its state branch has bounded reachable snapshots; force replacement does not itself guarantee immediate cleanup of unreachable Git objects by the hosting service.

The PC retains complete runs, additional WeatherNext statistics/variables and private retrospective analyses. Cloud history retains selected horizons and summary statistics. Before retiring, decide whether those future capabilities are dispensable or whether some compact extra collection is needed. Keep weather.db and existing provenance manifests either way. Full SQLite integrity was not established during this bounded inspection.

### C3 — Local task result can conceal partial failures

`background_collect.py:92` and `:104` correctly log MET/Frost source errors, but final status/exit at `:113–115` depends only on WeatherNext's success. A returned MET/Frost result with nonempty errors can therefore produce task result 0 and collection status “ok.” This is a verified code path, not a failure observed in today's healthy run. Preserve source-level checks and eventually make final task status reflect all attempted sources.

### C4 — Small debt needs a targeted cleanup

Only the legacy unpaired query functions in `scoring/scorer.py:14–73` use the unsafe hour-floored observation join. The dashboard uses exact paired scoring; **the module also contains actively used helpers**, so deleting the whole module would break imports. Deprecate/remove just the obsolete entry points after checking their test use.

Tests emit pandas concatenation warnings, NumPy timedelta warnings and Python's deprecated boolean inversion (`cloud/replay.py:168`). The local UI also emits Streamlit's `use_container_width` removal warning. Broad dependency ranges, including unbounded NumPy and cloud pandas `<4`, make future upgrades a compatibility risk. CI runs cloud tests only (`.github/workflows/tests.yml:14`); the local and browser checks I ran are not covered there.

Documentation is stale in specific places: PROJECT_STATUS still says 31 days, no steadiness display, Enningdalen stale and 6.21 GB; `SETUP_CLOUD.md:147` says forecast-value publication is forced off. Live publication is on and target-age gating remains enforced. Old plaintext Git objects and encryption-key backups remain recorded concerns; this inspection did not rescan all historical objects or make a legal finding. No handoff documents were edited.

## Comparison with Claude's 11 October review

**Agreement:** healthy collection, reproduced headline errors and blend gains, a long page, keyboard-inaccessible map markers, value in rain probabilities/regions/disagreement, ECMWF now having roughly two weeks of history, storage near 300 MB/day, and the dated retirement/runner/token work. A compact answer and section navigation are reasonable options.

**Disagreement or qualification:**

1. “Height-adjusted WeatherNext ... ahead at every horizon” is too broad for all-time results. It is ahead through **5 days**, **too close at 7 days**, and has **no verdict at 10 days** (only 3 paired days). October's monthly summary uses a smaller horizon set and is a different claim.
2. The replay's existing sums reproduce, but their end-date grouping is not a UTC midnight-to-midnight day. Hand-summing the same grouping does not validate that boundary. The 16 September example changes both amount and event classification.
3. The blend is promising, but calling it the strongest result needs qualification: its gain currently has no uncertainty interval or future validation.
4. Calibration needs a wind warning as well as the temperature story. WeatherNext temperature is near 75% through seven days, but ten-day coverage is **62.3%** on a very small sample.
5. An “AI versus physics” story must explain product processing, common cohorts and elevation differences. Daily fixed-run forecasts and daily ensemble probabilities are not automatically recoverable from the current cloud summaries.
6. Station-relative event thresholds could diversify replays, but a 98th percentile estimated from roughly one month is unstable. Exposed lighthouse readings are valid measurements; flag representativeness and choose event definitions in advance rather than dropping stations because their errors look large.

**Additional findings:** new station outages/recovery; exact overlap versus offsetting cloud/local counts; incorrect calendar-day rainfall windows; summed-median meaning; invisible measured line in single-point replays; measured light-mode contrast; seven-entry versus seven-calendar-day smoothing; local partial-failure exit status; fresh test/task/database checks. My previews matched the live past-value setting, avoiding the local/live publication mismatch Claude noted.

## Ranked possible next tasks

All are proposals. “Decision” means a product, data or retirement choice needed before implementation. Effort: **S** = usually under a day, **M** = roughly 1–3 days, **L** = several days; these are estimates. Risk refers to implementation/interpretation risk, not severity of the current finding.

| Rank | Possible task | Value | Effort | Risk | User decision? |
|---:|---|---|:---:|---|---|
| 1 | Correct rain-day boundaries; clarify summed medians; show one-point measured references | Prevents wrong daily amounts and event labels | M | Medium: crosses dates and event selection | **Yes:** UTC or Oslo day |
| 2 | Add per-station/per-variable freshness and coverage, including near-two-day warnings | Green health becomes trustworthy | S | Low: export/UI additions | No product choice if retaining the agreed two-day rule |
| 3 | Reconcile/version the cloud and PC station registry while preserving historical identities | Makes coverage and future comparisons consistent | M | Medium: sampling scope | **Yes:** fixed network or governed refresh |
| 4 | Finish 12/18 October overlap checks and document the PC retirement capability checklist | Saves about 112 GB/year while protecting required future analyses | M | Medium/high if retired prematurely | **Yes:** stop date and retained capabilities |
| 5 | Put a short answer/compact scorecard first; reduce monthly prose; add section navigation | A phone visitor understands the result quickly | M | Low | **Yes:** preferred first question and layout |
| 6 | Make rain representation and period scope consistent; use calendar dates/gap-aware trend smoothing | Removes apparent contradictions and misleading continuity | M | Medium: metric/cohort changes must be explicit | **Yes:** global filter scope; median default is already established |
| 7 | Fix light contrast and control semantics; add station selector and accessible chart data | Makes the page usable with low vision, keyboard or screen reader | M | Low | No fundamental product choice |
| 8 | Expose paired uncertainty calibration by horizon and Yr rain-probability reliability | Explains confidence and warning usefulness | M | Medium: thresholds/common cohorts | **Yes:** prioritize probability versus point error |
| 9 | Show current-sampling cohorts, land/offshore/regions, and error when services disagree | Reveals where aggregate ties conceal useful differences | M | Medium: small groups/multiple comparisons | **Yes:** geography, weighting and minimum evidence |
| 10 | Add IFS/AIFS as clearly labelled secondary temperature/wind comparisons on common pairs | Adds useful model context from existing history | M | Medium: elevation/product differences | **Yes:** expand beyond the site's Yr-versus-WeatherNext focus |
| 11 | Design daily max/min, frost-night and daily-rain products with coherent runs and complete periods | Answers practical everyday questions | L | Medium/high: retention and daily definitions | **Yes:** rolling lead or one fixed forecast run |
| 12 | Operational maintenance: token/runner checks, partial-failure status, dependency warnings, legacy query/docs, focused browser smoke checks | Prevents silent regressions and stale guidance | M | Low/medium | **Yes:** schedule token renewal and approve any settings changes separately |

Do not start by adding every suggested card. Correct daily semantics and operational visibility first; then choose one clear visitor question. A Norwegian-language option, linked repository footer and social preview are reasonable later polish, below correctness and accessibility.

## Questions to settle before building

1. **What should a visitor learn first?** Which service to use in Norway at a chosen horizon, where they differ, or how different forecasting models perform? Should the first screen show one-day results or several horizons together?
2. **Which station network should future collection use?** Freeze a reviewed 50-station network, or keep a controlled refresh process? Should land/offshore results be separate, and should national averages weight stations equally or retain station-hour weighting?
3. **What must survive PC retirement?** Are complete-run daily forecasts, private full-run browsing, additional variables/statistics and historical eligibility work still required? Retain extra compact inputs before retirement if those future analyses matter.
4. **What does a day mean?** UTC or Oslo calendar days; a fixed forecast issued before the day, or rolling forecasts made the same number of hours before each target? Define night/frost periods separately.
5. **What rain question matters most?** Amount accuracy, chance of rain, missing rain, or unnecessary warnings? Use the median by default as agreed, but keep probability and false-alarm tradeoffs visible.
6. **How should filters and experimental results behave?** One period across every statistical section, or explicitly scoped controls? Should four-model comparisons, the blend and the height estimate remain secondary until more current-method/winter evidence exists?

## Screenshot evidence

Saved with permission outside the repository. These paths point into Windows Temp; retain them elsewhere manually if you want permanent evidence alongside a future committed report. Full-page captures include the actual map tiles; top captures show the first-visitor experience.

- [1280 px light, first screen](<C:/Users/Martin Stranden/AppData/Local/Temp/WeatherApp-review-2026-10-11-codex/desktop-light-top.png>) · [full page](<C:/Users/Martin Stranden/AppData/Local/Temp/WeatherApp-review-2026-10-11-codex/desktop-light.png>)
- [1280 px dark, first screen](<C:/Users/Martin Stranden/AppData/Local/Temp/WeatherApp-review-2026-10-11-codex/desktop-dark-top.png>) · [full page](<C:/Users/Martin Stranden/AppData/Local/Temp/WeatherApp-review-2026-10-11-codex/desktop-dark.png>)
- [375 px light, first screen](<C:/Users/Martin Stranden/AppData/Local/Temp/WeatherApp-review-2026-10-11-codex/mobile-light-top.png>) · [full page](<C:/Users/Martin Stranden/AppData/Local/Temp/WeatherApp-review-2026-10-11-codex/mobile-light.png>)
- [375 px dark, first screen](<C:/Users/Martin Stranden/AppData/Local/Temp/WeatherApp-review-2026-10-11-codex/mobile-dark-top.png>) · [full page](<C:/Users/Martin Stranden/AppData/Local/Temp/WeatherApp-review-2026-10-11-codex/mobile-dark.png>)
- [Rain map and station labels](<C:/Users/Martin Stranden/AppData/Local/Temp/WeatherApp-review-2026-10-11-codex/rain-map.png>)
- [Bergen 16 September rain replay](<C:/Users/Martin Stranden/AppData/Local/Temp/WeatherApp-review-2026-10-11-codex/rain-replay.png>)

## Terms used

**MAE:** mean absolute error, the average size of a miss. **Bias:** signed average miss, showing consistently too high/low. **Mean / median:** arithmetic average / middle outcome. **Horizon:** how far ahead the forecast was available. **Paired:** same station/time compared on common available data. **Calibration:** whether stated uncertainty agrees with observed frequency. **Bootstrap:** estimating uncertainty by resampling whole days. **Brier score:** average squared error of a probability forecast. **p10–p90:** the forecast's middle 80% range. **IFS:** ECMWF's numerical weather forecasting system. **AIFS:** ECMWF's AI forecasting system. **ECMWF:** European Centre for Medium-Range Weather Forecasts. **CI:** automated checks on repository changes. **UTC:** the common world time reference. **Bilinear:** interpolation between four nearby grid points. **Lease:** a check preventing an older state snapshot from overwriting a newer one.
