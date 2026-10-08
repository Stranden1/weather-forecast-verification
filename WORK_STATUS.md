# Work status

_The latest task's checkpoint only. Archive it in CHANGELOG.md when replacing it._

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
