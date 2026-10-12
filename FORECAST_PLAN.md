# A useful finish line for WeatherApp

_2026-10-12. The owner chose a private forecast comparison. First viewer prepared
locally; cloud capture and public deployment are unchanged._

## What the project should answer

1. **What is coming at my place?** A private forecast timeline with readable values,
   ranges and model differences, rather than a duplicate of Yr's icons.
2. **When should I trust each forecast?** A public accuracy page showing matched
   results by lead, region and actual weather conditions.

A national tie is a useful finding. Differences in timing, freezing, wet hours,
wind and uncertainty can matter even when average temperature error is similar.
The project does not need an endless list of metrics to be worthwhile.

## Evidence that the prediction comparison has a purpose

Read-only probe of state commit `b07f6b87f1b01f515d8ca18c202cabc6f2512cd2`, collection
**12 Oct 2026 13:37:47 UTC**, inspected at 14:45 UTC. Same collected snapshot,
same station/target; future targets through collection +48 h, 49 active stations:

| Variable | Shared station-hours | Median absolute difference | Largest tenth begins around | Threshold disagreement |
|---|---:|---:|---:|---:|
| Temperature | 1,029 | 0.66 °C | 2.00 °C | 6.2% on below 0 °C |
| Wind | 1,029 | 1.36 m/s | 3.73 m/s | 9.8% on at least 10 m/s |
| Precipitation | 1,029 | 0.00 mm/h | 0.27 mm/h | 8.9% on above 0.1 mm/h |

WeatherNext temperature/wind are means; rain is the median. These are differences
between predictions, **not errors or independent weather events**, and only one
snapshot. Dry hours explain the zero typical rain difference. Evidence:
`work/forecast-comparison-2026-10-12/disagreement.json` (ignored local file).

At Trondheim the current capture had only 21 saved hours through collection +48 h,
from each provider. WeatherNext used two issue times (00:00/07:00 UTC); Yr used
12:29:44 UTC. The viewer therefore shows issue times and gaps rather than treating
this as one complete forecast run. Its window is the next 24/48 h from viewing,
so its displayed count can differ from the probe's collection-relative count.

Source/access: Google Earth Engine WeatherNext 3. Experimental-data notice and
licence: [Google terms](https://storage.googleapis.com/weathernext-public/terms-of-use.pdf).
Google permits internal use in section 2(a); the project's existing public
future-value restriction stays in place. Forecasts from MET Norway/Yr are CC BY 4.0.

## Ranked next steps

| Rank | Task | Value | Effort | Main risk / decision |
|---|---|---|---|---|
| 1 | Verify the scorecard deployment and review the private viewer | Correct numbers, readable phone page, immediately useful side-by-side predictions | S | Scorecard is on origin/main; verify next real deploy. Private viewer remains local |
| 2 | Complete the private 48-hour timeline with compact cloud capture | Fills gaps; enables meaningful rain onset, coldest hour and wind-peak comparisons | M | Owner chooses capture scope; encrypted state only, same stations, no collector restart |
| 3 | Retain a fixed daily forecast prospectively and verify daily/night outcomes | Useful high/low, below-freezing nights, wet/dry days and full-day amounts | M/L | Choose day/time convention and point estimates; cannot reconstruct lost full runs |
| 4 | Explain Yr rain probabilities using existing history | Answers “when it says 70%, how often is it wet?” | M | Verify Yr's amount threshold and interval first; show counts and uncertainty |
| 5 | Expose the already collected ECMWF IFS/AIFS temperature/wind results | Places Yr/WeatherNext in context without adding another collector | M | Common four-model hours only; disclose elevation/interpolation differences |
| 6 | Review another month and winter, then maintain the pipeline | More independent weather days and extremes; less temptation to invent winners | S ongoing | Stable scoring definitions, health checks, key recovery, runner/token deadlines |

S = small, M = medium, L = large; these are relative scope, not time promises.

## Proposed collection scope, before changing the cloud

Start with **the same 49 stations, three existing variables and the next 48 hours**.
Keep the newest delivered forecast in an encrypted, bounded state snapshot separate
from immutable scored history. At most 49 × 48 × 2 = 4,704 provider/station/hour
rows per complete snapshot, before field/metadata overhead. Do not keep every
hourly run forever, collect the full grid, or revive the old database.

Use the latest available forecasts as now, with original issue times retained;
WeatherNext may switch from an hourly run to a longer run. For daily **verification**,
retain a separately fixed forecast choice so a day's min/max does not stitch
unrelated issue times together. Check source availability and whole-interval
coverage before claiming a daily result.

Use Oslo time for the human forecast view, while existing accuracy rows keep UTC.
If local calendar-day/night scores are wanted, specify their boundaries and handle
23/25-hour daylight-saving days. Hourly-sampled observed extrema are not necessarily
the station's true daily extrema. Below-freezing air is not a road-ice forecast.

A sum of hourly ensemble medians is not an ensemble median of the daily total.
Likewise, p10/p50/p90 alone cannot provide exact event probabilities or a coherent
daily uncertainty range. Keep point estimates honestly labelled; full ensemble
collection is a later decision, not a prerequisite for the first forecast view.

Potential later additions: the alternative WeatherNext rain outputs, observation
quality flags and source/run provenance. Cloud cover/direction would help a broader
forecast product, but add verification work and are lower priority. Google lists
three rain outputs and other fields in its [model documentation](https://developers.google.com/weathernext/guides/models).

## Review choices

- Review the next live scorecard deployment and the local private viewer. Earlier scorecard commits are already on origin/main; any new viewer push remains separate.
- Confirm complete 48-hour capture, before any cloud collector change is deployed.
- Choose whether the daily feature means a calendar-day summary, an overnight
  freezing comparison, or both. Oslo dates are the proposed visitor-facing default.
- Prioritize rain-probability reliability or four-model comparisons; both already
  have useful retained data. No new station count is needed first.
- Confirm independent safe recovery of history/key, rather than relying on this PC.

Once the timeline and one useful daily/probability view are in place, the finish
line is a stable product: automated collection, short occasional reviews, and
small fixes when evidence warrants them. It is reasonable to let it run.

## Current checkpoint

`private_forecast/` is a loopback-only, read-only viewer of fetched cloud state.
It has station selection, 24/48 h, three variables, ranges, honest gaps, issue
ages, largest-gap selection, tables and both themes. This viewer is local, not
pushed or deployed. Earlier scorecard changes reached origin/main during this
task; CI passed, but the latest run skipped deployment and the 15:10 UTC live
check still showed the previous page. Start/check instructions: [PRIVATE_FORECAST.md](PRIVATE_FORECAST.md).
Private screenshots and browser evidence: `work/forecast-comparison-2026-10-12/`;
never publish these future-value screenshots.

## A few terms

Median = the middle value. A station-hour = one place at one time. Calibration = how often stated probabilities match outcomes. Ensemble = many model scenarios. ECMWF = the European forecast centre; IFS is its conventional model and AIFS its AI model. UTC = the shared reference clock.

Experimental-data notice (existing project wording):

© 2024-6 Google LLC, whose machine learning models were used to create the experimental data made available under the following licence terms https://storage.googleapis.com/weathernext-public/terms-of-use.pdf. This data is intended for experimental modelling only and is not intended, validated, or approved for real world use.
