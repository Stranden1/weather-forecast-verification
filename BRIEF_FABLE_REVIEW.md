# Brief: outside review by Fable (November 2026)

Written 2026-11-12 for a review session on Claude Fable 5.2. Read `AGENTS.md` and
`CLAUDE.md` first; they still apply.

## What the project is

A public scorecard that checks, every day, whether Yr (MET Norway) or Google's
WeatherNext 3 forecast was closer to what 49 Norwegian weather stations measured
(temperature, wind, hourly rain). Live page:
https://stranden1.github.io/weather-forecast-verification/

## What is live (review this)

- `cloud/`: collection, scoring and site export, run by `.github/workflows/collect.yml`
  every ~30 min (cron-job.org timer plus an hourly GitHub fallback).
- `site/`: the public page (`index.html`, `app.js`, `style.css`; Chart.js and Leaflet in
  `site/vendor/`). Site JSON is built in CI, not stored in Git.
- `history/`: encrypted, immutable scored days (5 Sep 2026 onward). The only record.
- `private_forecast/`, `project_hq/`: small local tools.
- `config/stations.json`, `config/wn_heights.json`: station network and grid heights.

Ignore `legacy/` (retired PC collector, its database is lost) and `docs/` (older
findings, reviews and finished plans) unless you need background.

## Hard rules (do not break)

- Never edit, delete, rewrite or re-encrypt anything in `history/`.
  Never print, log or move `WX_STATE_KEY` or anything from `.env`.
- Do not change scoring rules, metrics, thresholds or the Yr+WeatherNext blend.
  `DECISIONS.md` and `SCORING.md` record why each rule exists. You may *recommend*
  changes, with reasons, but do not make them.
- Do not change the workflow, timer or secrets, and do not push.
- First round is a written report only: no code changes.

## What we want from you

Two tracks, one report: `docs/reviews/REVIEW_2026-11_fable.md`.

**1. Code and robustness.** Real bugs, fragile spots and simplifications in `cloud/`
and `site/app.js`. For each finding: file and line, what goes wrong and when, how
sure you are, and a suggested fix. Rank by impact. Skip style nitpicks.

**2. Readability for ordinary people.** Today the page is written for experts
(English, "average error in °C", 95 % intervals, signed bias). The owner wants it
easy for ordinary Norwegians to read, with more than one way to see the results.
Assess the page and propose a concrete design. Ideas already on the table, to
accept, change or reject with reasons:

- Norwegian language (with English kept or as a toggle).
- A "Simple / Detailed" switch: simple view first, today's expert view kept.
- Hit rate instead of mean error ("Yr was within 1 °C 7 times out of 10"), shown as
  an icon array.
- "Forecast vs what happened" line chart for one station, observed line in bold.
- A calendar with one square per day, coloured by which service was closer.
- "Error size" as the default horizon view; the difference-with-interval view for experts.
- Dumbbell chart for station comparisons.
- The yellow "Check" health line in the header: it has shown a station warning for
  weeks (two offshore stations with model-filled data), which looks like a fault to
  visitors. Propose how status should be shown to the public.

Any new number on the page must be computable from data the export already has, or
say exactly what the export (`cloud/summarize.py`, `cloud/views.py`) would need to add.
Keep the fairness caveats (home advantage, ensemble mean, grid height); propose plainer
wording rather than removing them.

## Already known (no need to report again)

- Ormen Lange (SN76933) and Ytterøyane Fyr (SN57770) only have Frost quality code 6
  (model-filled) data, since 15 Oct and 1 Nov. The pipeline correctly skips it.
  Owner decision on retiring them is due about 1 Dec.
- NumPy timedelta / pandas concat deprecation warnings.
- Legacy unpaired entry points in the old scorer (now in `legacy/`).
- Independent backup and recovery of `WX_STATE_KEY` and `history/` is an owner action.

## How to check things

- Tests: `.venv\Scripts\python.exe -m unittest discover -s cloud/tests -t .` (178 pass,
  about 2 minutes).
- Page: the live URL above shows current data. The local preview (`.claude/launch.json`,
  name `site`) serves `site/`, but `site/data/` there is a stale local export.
- Handoff state: `PROJECT_STATUS.md`, `NEXT_STEPS.md`, `WORK_STATUS.md`, `DECISIONS.md`.
