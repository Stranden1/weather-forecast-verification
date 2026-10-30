# Work status

## Four-product rerun at 29 paired days — 2026-10-26 (Claude)

Owner asked to run the rerun planned for ~27 Oct now. Main fast-forwarded to origin/main for
current history (through 25 Oct).

**Done**
- `work/four-product-2026-10-26/analyze.py`: unchanged copy of the 15 Oct script (same cohort
  rules, day-block intervals, seed); the 15 Oct results are kept. Run is read-only.
- FINDINGS_FOUR_PRODUCT_2026-10-26.md: 29 days at 6–12 h (27 Sep – 25 Oct). Every 15 Oct
  conclusion holds with tighter intervals: Yr vs WeatherNext too close to call, IFS clearly worst,
  AIFS beats IFS but trails Yr, Yr+WeatherNext average beats all four, adding ECMWF worsens it.
  Offshore, IFS wind is now also clearly better than Yr.

- Owner chose option 1 (DECISIONS.md, 26 Oct): `site/index.html` gets a static "What about
  ECMWF?" note in "How to read this fairly" (29 days, IFS/AIFS behind Yr and WeatherNext at
  6–48 h, AIFS beat IFS, run-age caveat, not part of the average). ECMWF/Open-Meteo attribution
  was already on the page. Checked in the local preview; 178 cloud tests pass.

- Owner renewed the cron-job.org timer token on 26 Oct; new expiry 26 Oct 2027. Recorded in
  SETUP_CLOUD.md, NEXT_STEPS.md, PROJECT_STATUS.md and PLAN_FORECAST_ARCHIVE.md.

- Health check 28 Oct 20:35 UTC: **the timer has sent no dispatch since 26 Oct 20:07 UTC**
  (first miss 20:37, right after the token change). Only the hourly GitHub schedule runs:
  9 runs in 48 h, gaps up to 7.3 h; all succeeded, 0 source errors. Yr archive windows
  27 Oct am and 28 Oct am got only a missing manifest (no run in 08:30–13:00 UTC); lost.
  Scored day 27 Oct is complete, but its 6 h lead median rose to 6.4 h (5.9 before).
  ECMWF note is live.
- Ormen Lange (SN76933), checked 29 Oct: still in Frost (no validTo) and reporting, but every
  hourly temperature since 15 Oct 10:00 UTC has qualityCode 6 ("very uncertain, model data":
  MET fills it with model values). `cloud/frost.py` asks only for codes 0–4, so nothing enters
  history; this is correct. Our history already scored 180 rows (23 hours, 15–16 Oct) from the
  failing sensor before MET re-flagged them (0.05 % of temperature rows; e.g. 5.3 °C stored
  where Frost now has ~10 °C). Immutable; note for any future QC/observation-vintage dataset.
  Its wind has never been scored. Owner decided (DECISIONS.md, 29 Oct): keep it active, set
  `"active": 0` if Frost still has only code 6 on 1 Dec.

- 29 Oct: cron-job.org History showed 401 after 26 Oct; owner fixed the header and a Test run
  returned 204, but GitHub got no run from the test nor at 10:07/10:37 UTC (only the 10:06
  schedule run).

- 30 Oct: fixed. The job had been auto-disabled by cron-job.org after the 401s ("Enable job"
  off). Owner re-enabled it; test dispatch 00:20 UTC and the scheduled timer run 00:37 UTC both
  reached GitHub and succeeded. Timer outage lasted 26 Oct 20:37 – 30 Oct 00:37 UTC.

**Remaining:** none for the timer. Revisit the ECMWF note if a winter rerun changes the ranking;
re-check Ormen Lange about 1 Dec.
