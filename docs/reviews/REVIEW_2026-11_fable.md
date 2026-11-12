# Outside review, November 2026 (Claude Fable 5.2)

_Written 2026-11-12, following `BRIEF_FABLE_REVIEW.md`. Report only: no code, workflow,
scoring or history was changed._

## What I looked at, and what I did not

- Read all of `cloud/` (except `demo.py` and `migrate_sqlite.py`), `site/app.js`,
  `site/index.html`, both workflows, and the handoff and decision documents.
- Loaded the live page at desktop and phone width, and downloaded its public JSON
  (`meta`, `leaderboard`, `views`, `trend`, `events`, `summary`, `health`) as of the
  19:07 UTC run on 12 Nov. Every number quoted below comes from those files or from
  GitHub's run log.
- Ran the cloud tests locally: 178 pass (pandas 2.3.3, numpy 2.5.2).
- **Not done:** I did not decrypt `history/` or touch `.env`, so I ran no export locally
  and could not compute any new statistic from raw rows. Where a proposal needs a number
  the export does not have, I say what to add instead of guessing. Safari was not tested.

## Short version

The pipeline is careful where it matters most. Publication is history first, then state
under a lease; restore fails closed; pairing never looks at errors; the WeatherNext age
gate is on target time. I found no bug that corrupts scored history.

The three findings I would act on first:

1. A collect run counts as a success, and holds the next one back 2.5 hours, even when
   Yr or WeatherNext delivered nothing. Two such runs in a row leave permanent holes.
2. The "95 %" verdicts treat days as independent. The published daily differences are
   clearly correlated from one day to the next, so the ranges are too narrow and at
   least one "Yr is ahead" verdict is probably not safe.
3. Dependencies are unpinned and reinstalled on every run, so an upstream pandas or
   numpy release reaches the production collector with no test run in between.

For readability: the data already on the page tells a simple story that the page does
not tell. Yr is closer for the next few hours, it is a dead heat for tomorrow, and
Google is closer from two days out. I propose a Norwegian front page built around that
one table, with the expert page kept one click away.

---

## Part 1. Code and robustness

Ranked by impact. "Sure" is how confident I am that the problem is real, not how soon it
will bite.

### 1. A run with no forecasts still counts as a success and delays the retry

- **Where:** `cloud/health.py:61-64` (`failed`), used by `due` at `cloud/health.py:118-129`.
- **What goes wrong:** `failed()` is true only when *no* enabled source delivered a row.
  Frost almost always delivers, so a run where Yr returned 0 rows (api.met.no down), or
  where WeatherNext returned 0 rows (Earth Engine quota or permission error), is recorded
  as `last_success`. The gate then skips every timer tick for 150 minutes. Yr also has no
  retry inside a run (`cloud/yr.py:103-110`: one attempt per station, 30 s timeout).
- **When it matters:** horizon windows are 6 hours wide and runs are about 3 hours apart,
  so one bad run costs nothing. Two bad runs in a row (a 6-hour outage) leave targets
  with no Yr+WeatherNext pair at some horizons. Those rows are written to `history/`
  without a pair and can never be repaired, and the page loses them from every score.
  `cloud.run check` turns the job red only on the second failure, by which time the
  holes exist.
- **Sure:** high on the logic. I did not search the run history for a past instance;
  current runs show 0 source errors.
- **Fix:** let the gate ask a narrower question: "did the last run get rows from both
  forecast sources?" If not, collect again at the next 30-minute tick. Per-source
  summaries already exist in each run record (`run.py:74-77`), so this is a few lines in
  `health.due`. Add one retry with a short pause for a failed Yr station. The 14 Oct
  review listed this as a quick win; the per-source records were added, but the gate
  still uses the any-source rule.

### 2. Verdict ranges are too narrow: days are not independent

- **Where:** `cloud/summarize.py:86-102` (`bootstrap_diff`), also `bootstrap_gain` and the
  steadiness verdicts in `cloud/replay.py:71`.
- **What goes wrong:** the bootstrap resamples single days, which assumes the daily
  WeatherNext-minus-Yr difference on one day says nothing about the next. It does. From
  the live `trend.json`, the lag-1 autocorrelation of the daily difference is:

  | Ahead | Temperature | Wind | Rain |
  | --- | --- | --- | --- |
  | 6 h | 0.38 | 0.37 | 0.27 |
  | 12 h | 0.36 | 0.37 | 0.29 |
  | 1 day | 0.42 | 0.48 | 0.11 |
  | 2 days | 0.41 | 0.45 | −0.05 |
  | 3 days | 0.44 | 0.25 | |
  | 5 days | 0.42 | 0.07 | |

  With 44–58 days per horizon the uncertainty of each figure is about ±0.13, so values
  near 0.4 are real. Weather regimes last several days, and the same forecast run feeds
  neighbouring target days. At a correlation of 0.4 the true range is roughly 1.5 times
  wider than the one published.
- **What it changes:** most verdicts survive. Wind at 12 hours does not look safe: its
  published range is 0.014 to 0.077 m/s ("Yr is ahead"), and widened by 1.5 it crosses
  zero. Verdicts whose range ends within about a quarter of its width from zero are all
  doubtful. The monthly summaries are hit harder, because they run the same test on 11
  to 31 days.
- **Related:** the page shows about 60 verdicts (variables × horizons × two periods,
  plus height-adjusted, median and blend). At 95 % each, two or three will be wrong by
  chance even with perfect ranges. Nothing on the page says so.
- **Sure:** medium-high that the ranges are too narrow; the size of the correction is an
  estimate from daily averages, not from rows.
- **Fix (a scoring decision, so the owner decides and records it in `DECISIONS.md`):**
  resample blocks of consecutive days (a moving-block bootstrap, block length fixed in
  advance at about 4 days, not tuned on results). It is a small change inside
  `bootstrap_diff` and `bootstrap_gain`, and history is untouched. Until then, add one
  plain sentence to the fairness notes: with this many comparisons a few verdicts will
  be wrong, and a verdict that flips between "all time" and "last 30 days" is weak.

### 3. Dependencies are unpinned and installed fresh on every run

- **Where:** `cloud/requirements.txt` (`pandas>=2.2,<4`, `numpy>=1.26`, and so on),
  installed by `collect.yml` on each run. `tests.yml` runs only on pushes that touch
  `cloud/`, `site/` or the workflows.
- **What goes wrong:** the day pandas or numpy publishes a release, the collector runs
  on it with no test in between. The code leans on behaviour that upstream is known to
  be changing: `GroupBy.agg("last")` skipping empty values (`store.py:122-123`, which is
  what stops a late Frost delivery from erasing a value), concatenating empty frames
  (`store.py:110,120`), string handling of timestamps (`.astype(str).str[:10]` in many
  places), and the timedelta maths in `score.py:56-57`. The known deprecation warnings
  are exactly the early notice of such changes.
- **When:** unknown. The likely outcome is a loud crash and an email. The worse one is a
  silent change in what gets written to immutable history. A crash that lasts over a day
  also loses forecast snapshots for good.
- **Sure:** high that the exposure exists.
- **Fix:** commit a lock file with exact versions (for example `pip-compile` output) and
  install from it. Upgrade on purpose, in a commit that triggers `tests.yml`.

### 4. "Notable days" now lists every day

- **Where:** `cloud/replay.py:131-133` (fixed thresholds), `192-199` (`select_events`).
- **What goes wrong:** a cold snap is any hour at or below −5 °C, and strong wind is
  15 m/s at any land station. In the live `events.json` every day from 1 to 11 November
  is a cold snap and ten of those eleven days are a wind event (often the same exposed
  road station, E6 Langfjordbotn or Revsbotn). The list already has 41 entries. Through
  the winter "the 30 most recent" will cover about ten days, and the dropdown will be an
  undifferentiated daily log. The offshore wind exception was added for the same reason.
- **Sure:** high; visible on the live page today.
- **Fix:** make the bar relative. Either require an event to be unusual for that station
  (for example its coldest or windiest 2 % of hours so far), or keep the fixed bars but
  publish only the top few events per calendar month and type. Both use measurements
  only, so the "never chosen from forecast errors" rule holds.

### 5. The 150-minute gate loses a race with the 30-minute timer by about one second

- **Where:** `cloud/health.py:23` (`MIN_GAP_MIN = 150`), `118-129`.
- **What goes wrong:** the timer fires every 30 minutes and the gate is exactly five
  ticks. The gate runs a second or two *earlier* in the job than the moment the previous
  run stamped as `fetched_at`. Example from the run log: last success 19:07:44, gate
  step of the next eligible run at 21:37:43, age 149.98 minutes, skipped. So the real
  cadence is usually 180 minutes, sometimes 150, decided by runner jitter. This matches
  the "2.5–3.0 h" cadence in `PROJECT_STATUS.md`.
- **Impact:** low. Nothing is lost, but the cadence is not what the constant says.
- **Sure:** high.
- **Fix:** pick the intent and make it deterministic: 145 for a steady 2.5 hours, or 175
  for a steady 3 hours. An owner decision, since it changes cadence.

### 6. Each run re-reads, re-verifies and re-summarises the whole history, twice

- **Where:** `cloud/run.py:130-133` (export inside `all`) plus the separate
  "Rebuild page" step in `collect.yml`; `cloud/persistence.py:95-96` called twice
  (`160`, `163`), each running the full preflight in `cloud/history_crypto.py:19-21`;
  `cloud/persistence.py:105-124` verifying every day file against origin;
  `cloud/score.py:233-236` rewriting every day's record in `meta.json`.
- **What goes wrong:** nothing today. In the 19:07 run the export step took 26 seconds
  and publication 16. Every day file is decrypted and parsed about seven times per run,
  and the full bootstrap export runs twice. All of it grows in a straight line with
  history: about 2.5 minutes per export after one year, twice per run.
- **Sure:** high.
- **Fix:** in CI run `collect` and `score` before publication and `export` once after it.
  In `confirmed_history`, verify only days not yet in `finalized_days`. Keep the full
  verification as a weekly job or a manual command.

### 7. Seven exported files are no longer read by the page

- **Where:** `cloud/summarize.py:359-364,370` write `trend.json`, `stations.json`,
  `calibration.json`, `patterns.json`, `rain.json`, `bias.json` and `steadiness.json`.
  `site/app.js:56` loads only `meta`, `leaderboard`, `health`, `summary`, `events` and
  `views`; the same content, per period, is inside `views.json`.
- **What goes wrong:** double work in every export, and a trap. The old `stations.json`
  and `trend.json` score rain with WeatherNext's average, while the page (through
  `views.py:10-18`) uses the median. Anyone who reuses the old files gets numbers that
  disagree with the page.
- **Sure:** high. Only tests read the old files.
- **Fix:** delete the seven dumps and the loop code that only feeds them
  (`summarize.py:339-356`), and point the tests at `views.json`.

### 8. Smaller points

- **Station counts disagree.** The header says "49 active collection stations"; the
  events card says "at 50 stations" because history keeps retired Wisting. A retired
  station is not in `meta.stations`, so it cannot be selected, and a replay headlined
  by one would show its raw ID (`app.js:676`). Low impact. Export retired stations in
  `meta.json` with `"active": false`.
- **A failed download looks like an empty project.** `app.js:57` turns any fetch or
  parse error into `{}`, and the page then says "No data published yet" (`app.js:864`).
  Show "Could not load the data, try again" instead. On the export side, write JSON
  with `allow_nan=False` (`summarize.py:309`) so a stray NaN stops the deploy and the
  old page stays up, rather than publishing a file browsers cannot parse. I found no
  path that produces one today.
- **The key is visible to every step.** `WX_STATE_KEY` is set for the whole job in
  `collect.yml`, including the three Pages actions that do not need it. Set it only on
  the four Python steps. Low risk (they are GitHub's own actions), cheap to tighten.
- **`T24:00:00Z`** (`app.js:49`) parses in Chromium. I could not test Safari; if it
  returns NaN there, the missing-station logic switches off silently. Adding one day to
  `T00:00:00Z` avoids the question. Low confidence that it is a problem.
- **Stale comment** at `app.js:330-331` says steadiness ignores the period switch; the
  code uses the selected period.
- **Google Fonts** are loaded from Google's servers (`index.html:16-18`), which sends
  each visitor's IP address to Google. For a public Norwegian page it is simpler to
  serve the two fonts from `site/vendor/`.

### Checked and found sound

History-first publication with byte-for-byte confirmation before pruning
(`persistence.publish`); the leased state push; restore that only starts fresh when the
branch is truly absent; write-once day files with the sidecar written first; pairing
that prefers runs with both providers and never reads errors; rain keyed by interval
end for all sources; the one-hour target-time gate on WeatherNext values in both the
station series and the replays; the Yr archive kept apart from source health.

---

## Part 2. Readability for ordinary people

### What the page is like for a visitor today

On a phone the first screen shows: an English title, a yellow "Check: … station history
warning", two rows of buttons, "TEMPERATURE / 1 DAY AHEAD", UTC dates, and then "Too
close to call" above 0.99 and 0.97 "°C avg. error". The page is 6,200 pixels tall on a
phone, with 8 dropdowns and 11 fold-out sections.

Three things get in the way of an ordinary reader:

1. **The best story is not told.** The headline is fixed at one day ahead, which is the
   one place where nothing is decided. The pattern across horizons is clear and simple,
   but it only exists as a difference chart with error bars.
2. **The words are for forecasters.** "Average error", "95 % range", "paired
   station-hours", "bias", "horizon", "UTC target dates". WeatherNext is a name almost
   nobody in Norway knows.
3. **The page looks broken when it is not.** The yellow "Check" has been there for weeks
   because of two offshore stations.

### The story the data already tells

From the live `leaderboard.json`, all 68 days, using the verdicts the page already shows
(rain uses WeatherNext's median, as the page does):

| | 6 hours | Tomorrow | 2 days | 5 days | 10 days |
| --- | --- | --- | --- | --- | --- |
| Temperature | Yr | even | Google | Google | even |
| Wind | Yr | even | Google | Google | even |
| Rain | Yr | even | Google | not scored | not scored |

Two more findings an ordinary reader can use, both already exported:

- Taking the midpoint of the two forecasts gives about 10 % less error than the better
  one alone, for tomorrow's temperature.
- Frost, one day ahead: Yr caught 6 of 10 freezing hours, Google almost 8 of 10. But
  about 1 in 4 of Google's frost warnings were false alarms, against 1 in 8 for Yr.

### Proposed front page

Norwegian, one column, nothing to choose before the answer is visible. Numbers below are
the real ones from the live data, with two exceptions that are placeholders: the
"innenfor 1 grad" hit rates (not exported yet) and the Oslo sentence under the line chart
(the browser can compute it from `recent/<station>.json`).

```
┌────────────────────────────────────────────────────────┐
│ ☀  Yr mot Google                            [ NO | EN ]│
│    Hvem treffer best på været i Norge?                 │
│                                                        │
│ Hver dag sjekker vi varslene fra Yr og fra Googles     │
│ KI-modell WeatherNext mot det 49 målestasjoner faktisk │
│ målte.                                                 │
│ ● Oppdatert for 3 timer siden · 68 dager sjekket       │
├────────────────────────────────────────────────────────┤
│ KORT FORTALT                                           │
│ Yr er best de nærmeste timene.                         │
│ Google er best fra to dager fram.                      │
│ For i morgen er det dødt løp.                          │
│                                                        │
│              Om 6 t   I morgen  Om 2 d   Om 5 d  Om 10 d│
│ Temperatur   [ Yr ]   [ likt ]  [Google] [Google] [likt]│
│ Vind         [ Yr ]   [ likt ]  [Google] [Google] [likt]│
│ Regn         [ Yr ]   [ likt ]  [Google]    –       –  │
│                                                        │
│ Blå = Yr nærmest · Oransje = Google nærmest ·          │
│ Grå = for jevnt til å kåre en vinner                   │
│ Trykk på en rute for å se tallene.                     │
├────────────────────────────────────────────────────────┤
│ HVOR OFTE TREFFER DE?      Temperatur · varsel i morgen│
│ Yr      ●●●●●●●○○○   7 av 10 innenfor 1 grad           │
│ Google  ●●●●●●●○○○   7 av 10 innenfor 1 grad           │
│ I snitt bommer begge med omtrent 1,0 grad.             │
├────────────────────────────────────────────────────────┤
│ VARSEL MOT VIRKELIGHET          Sted: [ Oslo        ▾ ]│
│ Siste 7 dager, varselet slik det så ut dagen før       │
│   ━━ Målt   ── Yr   ── Google                          │
│   (linjediagram, målt temperatur i tykk svart strek)   │
│ I Oslo denne uka bommet Yr i snitt 0,8°, Google 0,9°.  │
├────────────────────────────────────────────────────────┤
│ DAG FOR DAG                 Temperatur · varsel i morgen│
│ sep  ▢▢■■▢■■■▢▢■▢■■■▢▢■■▢■■■■▢▢                        │
│ okt  ■■▢▢■■▢■■■▢▢■▢■■■▢▢■■▢■■■■▢▢■▢■                   │
│ nov  ■▢▢■■▢■■■▢▢                                       │
│ Yr nærmest 29 dager · Google nærmest 27 dager          │
├────────────────────────────────────────────────────────┤
│ TIPS  Ser du på begge og tar midt imellom, bommer du   │
│ omtrent 10 % mindre enn med den beste alene.           │
├────────────────────────────────────────────────────────┤
│ KULDEGRADER   Fanget varselet at det ble frost?        │
│ Yr      ●●●●●●○○○○  6 av 10 frosttimer varslet         │
│ Google  ●●●●●●●●○○  nesten 8 av 10                     │
│ Men Google varslet oftere frost som ikke kom:          │
│ 1 av 4 ganger, mot 1 av 8 for Yr.                      │
├────────────────────────────────────────────────────────┤
│ ER DETTE RETTFERDIG?  (tre korte punkter, se under)    │
│                                                        │
│ [ Vis kart, alle stasjoner og detaljerte tall  → ]     │
└────────────────────────────────────────────────────────┘
```

The last button opens today's expert page, unchanged in content.

### The ideas in the brief: what I would choose

| Idea | Verdict | Why |
| --- | --- | --- |
| Norwegian language | **Accept**, Norwegian as default, English as a toggle | The readers are Norwegian and Yr is a household name. Details below. |
| Simple / Detailed switch | **Accept, as one page in two layers** | The simple layer is the page; "Vis detaljer" reveals the existing cards. Not two parallel pages: that doubles what must be tested and kept in step. Remember the choice, and support a link such as `?visning=detaljert`. |
| Verdict table (new) | **Add as the headline** | It is the clearest thing the data says, needs no new numbers, and replaces five separate "how far ahead" dropdowns with one glance. |
| Hit rate as an icon array | **Accept, next to the average error, not instead of it** | "7 of 10 within one degree" is easier than "0.99 °C average error". But the winner must still come only from the existing test. See the rule below. |
| Forecast vs what happened | **Accept, move it to the front** | It already exists, hidden behind a click on the map. It is the most trust-building chart: people see the forecast follow the measured line. Default to Oslo; list the big towns first. |
| Calendar, one square per day | **Accept** | It shows the day-to-day swing, which is the honest explanation of "dead heat". Needs a third state for "about equal" and a count line. |
| Error size as default horizon view | **Accept for the simple layer**, with a verdict label under each horizon | Two rising lines read as "the further ahead, the bigger the miss". The lines nearly overlap, which is the message. The difference chart with ranges stays in the detailed layer. |
| Dumbbell chart for stations | **Accept, in the detailed layer only** | Good for "where do they differ", but 49 rows is long on a phone. Show the 10 largest gaps and a "show all" control. It can replace the "Biggest differences" lists. |
| Status line | **Change**, see below | Separate "is the page up to date" from "are all stations reporting". |

**Drop from the simple layer** (keep in detailed): steadiness and flip-flops, range
scores and widths, bias by time of day, the patterns table, CSI, storm replays in their
current form (finding 4), and the height-adjusted figures. Each is sound, but each needs
a paragraph of explanation before it means anything.

**Reject:** a 100-icon grid (too heavy on a phone; ten icons plus the exact percentage
is enough) and hit rate as a *replacement* for average error (it throws away how big the
misses are, which matters most on the bad days).

### One rule to keep the simple view honest

Only one thing on the page may name a winner: the existing verdict. Hit rates, the
calendar count and the station comparison are descriptions. They get no "winner"
styling, and where a description points the other way from the verdict the page says so
in words ("Google traff litt oftere innenfor én grad, men forskjellen er for liten til å
kåre en vinner"). Otherwise a reader sees two scoreboards that disagree.

### Language

- `lang="nb"`, Norwegian text as default, and a small NO | EN toggle. Keep the strings
  in one table in `app.js`. The month-by-month text is written in English by
  `cloud/monthly.py`; the verdicts behind it are already exported in `summary.json`, so
  build the sentences in the browser in both languages and stop exporting prose.
- Call the services "Yr" and "Google (WeatherNext)", shortened to "Google" in tight
  places. Say once, at the top, what WeatherNext is.
- Numbers and dates the Norwegian way: "0,99", "11. nov.", Norwegian time. Today the
  page mixes "59,254" or "59 254" (browser-dependent) with "0.99". Use
  `Intl.NumberFormat("nb-NO")` and `Intl.DateTimeFormat` everywhere. UTC belongs in the
  detailed layer only.
- The required Google and ECMWF attribution wording must stay in English, exactly as
  quoted in `DECISIONS.md`. Put one Norwegian sentence in front of it.

Suggested wording:

| Today | Simple layer |
| --- | --- |
| Average error 0.99 °C | Bommer i snitt med 1,0 grad |
| Too close to call | For jevnt til å kåre en vinner (short: "likt") |
| Yr is ahead | Yr treffer best |
| 1 day ahead | Varsel for i morgen |
| Horizon | Hvor langt fram |
| 95 % range of the difference | (detailed layer only) "Usikkerhet i forskjellen" |
| Bias +0.3 °C | Varsler i snitt 0,3 grader for varmt |
| Paired station-hours | Sammenligninger |
| Same as yesterday | "Samme vær som i går"-gjetning |
| Observed events caught | Så mange av frosttimene ble varslet |
| False alarms | Varslet, men kom ikke |

### Fairness notes in plain words

Keep all three, short, on the front page, each with a "les mer" link to today's longer
text:

- **Yr har hjemmebane.** Yr justerer varslene sine med ferske målinger fra norske
  værstasjoner, også flere av dem vi sjekker mot.
- **Google-varselet er et gjennomsnitt av mange mulige utfall.** Det gir litt mindre
  bom i snitt, men kan dempe ekstremvær. For regn bruker vi derfor det midterste
  utfallet.
- **Google regner for ruter på omtrent 5 km.** I bratt terreng ligger ruta ofte høyere
  enn stasjonen, og da blir varselet for kaldt (omtrent 0,65 grader per 100 meter).

### How status should be shown

Today one yellow line mixes two unrelated questions. Split them:

1. **Is the page up to date?** One quiet line at the top: "● Oppdatert for 3 timer
   siden". It turns amber, with a plain sentence, only when the reader should doubt
   freshness: the last run failed, there has been no run for over 8 hours, or a forecast
   source has failed twice in a row. These are the existing thresholds.
2. **Are all stations reporting?** Not a warning. A neutral fact where stations are
   shown: "47 av 49 stasjoner leverer målinger", and on the two stations: "Ingen
   godkjente målinger siden 16. okt. MET fyller inn modellverdier her, og dem bruker vi
   ikke." Make it amber only if a large share is silent, for example more than one in
   five, because that would weaken the scores.

The owner should be able to add a public note per station in `config/stations.json`
(for example `"public_note"`), exported in `meta.json`, so that a known case reads as
explained rather than as a fault.

### What the export needs

| Element | Data | Export change |
| --- | --- | --- |
| Verdict table | `leaderboard.json` verdicts | None |
| "Bommer i snitt" figures | `leaderboard.json` | None |
| Forecast vs what happened | `recent/<station>.json` | None |
| Calendar | `views.json` → `trend` (daily error per service) | None. "About equal" is a display rule, for example a gap under 5 %; state it under the calendar. |
| Blend tip | `avg_gain`, `verdict_avg` | None. Show only when the verdict is "better", as today. |
| Frost / wind / rain "caught" icons | `views.json` → `practical` (`pod`, `far`) | None |
| Rain hit rate | Same, for rain: "varslet x av 10 regntimer" and "regnet x av 10 ganger det ble varslet" | None |
| Dumbbell | `views.json` → `stations` | None |
| Temperature and wind hit rate | Not exported | In `summarize.stats()` add, per service, the share of paired forecasts with absolute error at or under a fixed limit: `within_yr`, `within_wn` (and `within_wnh`, `within_avg` where those exist). Put the limits in `meta.json`. It flows into `leaderboard.json` for both periods. |
| Status | Computed in `app.js` from `last_obs` | None needed. Tidier: let `cloud/health.py` export `stations: {active, reporting, silent: [...]}` so the rule lives in one place. |
| Norwegian month text | `summary.json` verdicts | None, if the sentences are built in the browser |

The hit-rate limit is a new published measure, so it needs an owner decision in
`DECISIONS.md`. I suggest 1 °C and 2 m/s, chosen now for being round and easy to say,
before anyone has seen which service they favour. I have not seen the result either.

### Suggested order

1. Status line and Norwegian text with the number and date formats. No new data, and it
   removes the two things that most make the page look foreign or broken.
2. The simple layer from existing data: verdict table, forecast vs what happened,
   calendar, blend tip, frost icons, three fairness lines. Expert cards move behind
   "Vis detaljer".
3. The hit-rate export and its icon rows, after the owner fixes the limits.
4. Dumbbell chart and the relative "notable days" rule (finding 4).

Check each step at 1280, 375 and 320 pixels in both themes, as before.

---

## Decisions for the owner

1. Should the gate retry at once when Yr or WeatherNext delivered nothing (finding 1)?
2. Should the verdict test resample blocks of days (finding 2)? This changes published
   verdicts, so it belongs in `DECISIONS.md` either way.
3. Is the intended cadence 2.5 or 3 hours (finding 5)?
4. Hit-rate limits: 1 °C and 2 m/s?
5. Norwegian by default with an English toggle, and "Google (WeatherNext)" as the name?
