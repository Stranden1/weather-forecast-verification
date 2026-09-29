"""Monthly summary: month split, verdict grouping, wording, and the rain median."""
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cloud import monthly, summarize
from cloud.config import PRECIP_HORIZONS
from cloud.monthly import SUMMARY_HORIZONS, describe, horizon_phrase

ALL = SUMMARY_HORIZONS


def days(first, last):
    """'2026-09-01'..'2026-09-10' as a list of date strings."""
    return [d.strftime("%Y-%m-%d") for d in pd.date_range(first, last)]


def frame(day_list, hs=ALL, yr=1.0, wn=1.0, wn50=None, adj=None):
    """Scored rows with a fixed error size per service (the sign alternates by station).

    Equal sizes give a difference of exactly zero every day, so the bootstrap says "too
    close to call"; different sizes give a clear winner once there are 7 days.
    """
    rows = []
    for day in day_list:
        for hour in (0, 12):
            for station, sign in (("A", 1), ("B", -1)):
                for h in hs:
                    r = dict(target=f"{day}T{hour:02d}:00:00Z", station=station, h=h,
                             obs_t=10.0, yr_t=10 + sign * yr, wn_t=10 + sign * wn,
                             obs_w=5.0, yr_w=5 + sign * yr, wn_w=5 + sign * wn)
                    if adj is not None:
                        r["wn_t_adj"] = 10 + sign * adj
                    if h in PRECIP_HORIZONS:
                        r.update(obs_p=1.0, yr_p=1 + sign * yr / 2, wn_p=1 + sign * wn / 2,
                                 wn_p_p50=1 + sign * (wn if wn50 is None else wn50) / 2)
                    rows.append(r)
    return pd.DataFrame(rows)


def verdicts(t=None, w=None, p=None, adj=None):
    same = lambda v: {h: v for h in ALL}
    rain = {h: {"mean": "too_close", "median": "too_close"} for h in PRECIP_HORIZONS}
    return {"t": t or same("too_close"), "w": w or same("too_close"), "p": p or rain,
            "t_adj": adj or {}}


class MonthSplitTest(unittest.TestCase):
    NOW = pd.Timestamp("2026-10-03T12:00:00Z")

    def setUp(self):
        self.df = pd.concat([
            frame(days("2026-08-20", "2026-08-31"), yr=1.0, wn=0.5),   # WeatherNext better
            frame(days("2026-09-01", "2026-09-10"), yr=0.5, wn=1.0),   # Yr better
            frame(days("2026-10-01", "2026-10-02")),                   # only 2 days so far
        ], ignore_index=True)
        self.s = monthly.build_summary(self.df, self.NOW)

    def test_this_month_first_then_completed_months_newest_first(self):
        self.assertEqual([m["month"] for m in self.s["months"]], ["2026-10", "2026-09", "2026-08"])
        self.assertEqual([m["in_progress"] for m in self.s["months"]], [True, False, False])

    def test_each_month_uses_only_its_own_days(self):
        _, sep, aug = self.s["months"]
        self.assertEqual((aug["first_day"], aug["last_day"], aug["days"]), ("2026-08-20", "2026-08-31", 12))
        self.assertEqual((sep["first_day"], sep["last_day"], sep["days"]), ("2026-09-01", "2026-09-10", 10))
        # The two months have opposite winners; neither is diluted by the other.
        self.assertEqual(aug["verdicts"]["t"]["24"], "weathernext")
        self.assertEqual(sep["verdicts"]["t"]["24"], "yr")

    def test_month_in_progress_is_marked_so_far_and_others_are_not(self):
        cur, sep, _ = self.s["months"]
        self.assertTrue(cur["text"].startswith("October so far (1–2 Oct; both models compared on 2 days)\n"))
        self.assertTrue(sep["text"].startswith("September (1–10 Sep; both models compared on 10 days)\n"))
        self.assertNotIn("so far", sep["text"])

    def test_header_counts_only_days_with_both_models(self):
        early = frame(days("2026-09-05", "2026-09-14")).assign(wn_t=None, wn_w=None, wn_p=None)
        df = pd.concat([early, frame(days("2026-09-15", "2026-09-27"))], ignore_index=True)
        head = monthly.build_summary(df, self.NOW)["months"][0]["text"].split("\n")[0]
        self.assertEqual(head, "September (5–27 Sep; both models compared from 15 Sep, 13 days)")
        none = monthly.build_summary(early, self.NOW)["months"][0]["text"].split("\n")[0]
        self.assertEqual(none, "September (5–14 Sep; no days with both models yet)")
        one = monthly.build_summary(frame(["2026-09-05"]), self.NOW)["months"][0]["text"].split("\n")[0]
        self.assertEqual(one, "September (5 Sep; both models compared on 1 day)")

    def test_boundary_is_midnight_utc_by_target_time(self):
        df = pd.concat([frame(["2026-08-31"]).assign(target="2026-08-31T23:00:00Z"),
                        frame(["2026-09-01"]).assign(target="2026-09-01T00:00:00Z")])
        s = monthly.build_summary(df, self.NOW)
        self.assertEqual([(m["month"], m["days"]) for m in s["months"]], [("2026-09", 1), ("2026-08", 1)])

    def test_future_months_and_empty_data_give_nothing(self):
        self.assertEqual(monthly.build_summary(frame(days("2026-11-01", "2026-11-09")), self.NOW)["months"], [])
        self.assertEqual(monthly.build_summary(pd.DataFrame(columns=["target", "station", "h"]),
                                               self.NOW)["months"], [])

    def test_build_writes_summary_json_without_forecast_values(self):
        from cloud.tests.test_pipeline import synthetic_scored
        stations = [{"station_id": s, "name": s, "latitude": 60, "longitude": 10, "elevation_m": 10}
                    for s in ("SN1", "SN2", "SN3")]
        with tempfile.TemporaryDirectory() as tmp:
            summarize.build(synthetic_scored(days=9), Path(tmp), stations, publish_values=False,
                            now=pd.Timestamp("2026-10-05"))
            raw = (Path(tmp) / "summary.json").read_text(encoding="utf-8")
        out = json.loads(raw)
        self.assertEqual([m["month"] for m in out["months"]], ["2026-09"])
        self.assertEqual(set(out["months"][0]),
                         {"month", "label", "in_progress", "first_day", "last_day", "days", "text", "verdicts"})
        for column in ("yr_t", "wn_t", "obs_t", "wn_w", "wn_p"):  # only verdicts, no values
            self.assertNotIn(column, raw)


class VerdictGroupingTest(unittest.TestCase):
    def test_neighbouring_horizons_form_one_range(self):
        self.assertEqual(horizon_phrase([24, 48], ALL), "1–2 days out")
        self.assertEqual(horizon_phrase([24, 48, 72], ALL), "1–3 days out")
        self.assertEqual(horizon_phrase([6, 24], ALL), "6 hours to 1 day out")
        self.assertEqual(horizon_phrase([48], ALL), "2 days out")
        self.assertEqual(horizon_phrase([6], ALL), "6 hours out")

    def test_range_reaching_the_last_horizon_reads_from(self):
        self.assertEqual(horizon_phrase([72, 120], ALL), "from 3 days")
        self.assertEqual(horizon_phrase([120], ALL), "5 days out")
        self.assertEqual(horizon_phrase(ALL, ALL), "at all horizons")

    def test_separate_horizons_are_listed_not_merged(self):
        self.assertEqual(horizon_phrase([24, 72], ALL), "1 day and 3 days out")
        self.assertEqual(horizon_phrase([6, 72, 120], ALL), "6 hours out and from 3 days")
        # Neighbours are neighbours in that variable's own horizon list (rain has only 3).
        self.assertEqual(horizon_phrase([24, 48], [6, 24, 48]), "from 1 day")

    CMP = days("2026-09-05", "2026-09-30")  # both models on every day

    def describe(self, v):
        return describe("September", False, "2026-09-05", "2026-09-30", self.CMP, v)

    def test_one_line_per_variable_winners_first_then_too_close(self):
        v = verdicts(t=dict(zip(ALL, ["yr", "yr", "too_close", "too_close", "too_close"])),
                     w=dict(zip(ALL, ["weathernext", "weathernext", "too_close", "too_close", "too_close"])))
        self.assertEqual(self.describe(v).split("\n"), [
            "September (5–30 Sep; both models compared on 26 days)",
            "Temperature: Yr ahead 6 hours to 1 day out; too close to call from 2 days.",
            "Wind: WeatherNext ahead 6 hours to 1 day out; too close to call from 2 days.",
            "Rain: WeatherNext's median too close to call at all horizons; too close to call against WeatherNext's average."])

    def test_both_winners_ordered_by_shortest_horizon(self):
        v = verdicts(t=dict(zip(ALL, ["too_close", "weathernext", "too_close", "yr", "yr"])))
        self.assertIn("Temperature: WeatherNext ahead 1 day out; Yr ahead from 3 days; "
                      "too close to call at 6 hours and 2 days out.", self.describe(v))

    def test_not_enough_days_go_in_one_final_line(self):
        v = verdicts(t=dict(zip(ALL, ["yr", "too_close", "too_close", "not_enough_data", "not_enough_data"])),
                     w=dict(zip(ALL, ["too_close", "too_close", "too_close", "not_enough_data", "not_enough_data"])))
        lines = self.describe(v).split("\n")
        self.assertEqual(lines[1], "Temperature: Yr ahead 6 hours out; too close to call at 1–2 days out.")
        self.assertEqual(lines[-1], "Not enough days yet from 3 days.")
        self.assertEqual(sum("not enough" in l.lower() for l in lines), 1)

    def test_not_enough_line_names_variables_when_they_differ(self):
        v = verdicts(t=dict(zip(ALL, ["yr", "yr", "yr", "yr", "not_enough_data"])),
                     w=dict(zip(ALL, ["yr", "yr", "yr", "not_enough_data", "not_enough_data"])))
        self.assertTrue(self.describe(v).endswith(
            "\nNot enough days yet: temperature at 5 days out; wind from 3 days."))

    def test_height_adjusted_sentence_only_when_it_differs(self):
        same = verdicts(adj={h: "too_close" for h in ALL})
        self.assertNotIn("Height-adjusted", self.describe(same))
        v = verdicts(adj=dict(zip(ALL, ["weathernext", "weathernext", "too_close", "too_close", "not_enough_data"])))
        self.assertIn("Temperature: too close to call at all horizons. "
                      "Height-adjusted: WeatherNext ahead 6 hours to 1 day out.\n", self.describe(v))

    def test_rain_leads_with_the_median_then_the_average(self):
        rain = {6: {"mean": "yr", "median": "too_close"}, 24: {"mean": "yr", "median": "too_close"},
                48: {"mean": "yr", "median": "weathernext"}}
        self.assertIn("\nRain: WeatherNext's median ahead 2 days out, too close to call at 6 hours to 1 day out; "
                      "Yr beats WeatherNext's average.", self.describe(verdicts(p=rain)))

    def test_rain_average_names_horizons_when_its_verdicts_differ(self):
        rain = {6: {"mean": "yr", "median": "yr"}, 24: {"mean": "too_close", "median": "too_close"},
                48: {"mean": "too_close", "median": "too_close"}}
        self.assertIn("Rain: WeatherNext's median behind Yr 6 hours out, too close to call from 1 day; "
                      "Yr beats WeatherNext's average 6 hours out; "
                      "too close to call against WeatherNext's average from 1 day.", self.describe(verdicts(p=rain)))


class WordingTest(unittest.TestCase):
    """Real bootstrap verdicts feeding the sentences."""

    def text(self, df, now="2026-10-20T00:00:00Z"):
        return monthly.build_summary(df, pd.Timestamp(now))["months"][0]["text"]

    def test_tie_says_too_close_to_call_and_names_no_winner(self):
        text = self.text(frame(days("2026-09-01", "2026-09-10"), yr=1.0, wn=1.0))
        self.assertEqual(text.split("\n"), [
            "September (1–10 Sep; both models compared on 10 days)",
            "Temperature: too close to call at all horizons.",
            "Wind: too close to call at all horizons.",
            "Rain: WeatherNext's median too close to call at all horizons; too close to call against WeatherNext's average."])
        self.assertNotIn("ahead", text)

    def test_fewer_than_seven_days_says_not_enough_days_yet_even_with_a_gap(self):
        text = self.text(frame(days("2026-09-01", "2026-09-05"), yr=1.0, wn=0.1))
        self.assertEqual(text, "September (1–5 Sep; both models compared on 5 days)\n"
                               "Not enough days yet at all horizons.")
        self.assertNotIn("ahead", text)

    def test_exactly_seven_days_is_enough(self):
        text = self.text(frame(days("2026-09-01", "2026-09-07"), yr=1.0, wn=0.1))
        self.assertIn("Temperature: WeatherNext ahead at all horizons.", text)
        self.assertNotIn("not enough", text.lower())

    def test_winner_is_named_only_when_the_verdict_says_so(self):
        text = self.text(frame(days("2026-09-01", "2026-09-10"), yr=0.5, wn=1.0))
        self.assertIn("Temperature: Yr ahead at all horizons.", text)
        self.assertIn("Wind: Yr ahead at all horizons.", text)
        self.assertNotIn("WeatherNext ahead", text)

    def test_only_some_horizons_have_enough_data(self):
        # 5 days of the 3-day and 5-day horizons only; the rest have 10 days.
        df = pd.concat([frame(days("2026-09-01", "2026-09-10"), hs=[6, 24, 48], yr=1.0, wn=1.0),
                        frame(days("2026-09-01", "2026-09-05"), hs=[72, 120], yr=1.0, wn=1.0)])
        text = self.text(df)
        self.assertIn("Temperature: too close to call at 6 hours to 2 days out.", text)
        self.assertTrue(text.endswith("\nNot enough days yet from 3 days."))

    def test_height_adjusted_sentence_appears_when_only_the_adjusted_line_wins(self):
        df = frame(days("2026-09-01", "2026-09-10"), yr=1.0, wn=1.0, adj=0.2)
        self.assertIn("Temperature: too close to call at all horizons. "
                      "Height-adjusted: WeatherNext ahead at all horizons.", self.text(df))

class RainMedianTest(unittest.TestCase):
    def rain(self, **kw):
        return summarize.paired(frame(days("2026-09-01", "2026-09-10"), hs=[24], **kw), "p")

    def test_median_gets_its_own_difference_and_verdict(self):
        # WeatherNext's average is worse than Yr's, its median better.
        s = summarize.stats(self.rain(yr=1.0, wn=2.0, wn50=0.2), median_ci=True)
        self.assertEqual(s["verdict"], "yr")
        self.assertEqual(s["verdict_50"], "weathernext")
        self.assertLess(s["diff_50"], 0)
        self.assertGreater(s["diff"], 0)

    def test_median_verdict_is_not_added_unless_asked_for(self):
        self.assertNotIn("verdict_50", summarize.stats(self.rain(yr=1.0, wn=2.0, wn50=0.2)))

    def test_monthly_rain_sentence_names_the_median_separately(self):
        df = frame(days("2026-09-01", "2026-09-10"), yr=1.0, wn=2.0, wn50=0.2)
        rain = monthly.build_summary(df, pd.Timestamp("2026-10-20T00:00:00Z"))["months"][0]["text"].split("Rain: ")[1].split("\n")[0]
        self.assertEqual(rain, "WeatherNext's median ahead at all horizons; Yr beats WeatherNext's average.")

    def test_wet_hour_scores_include_the_median_and_ignore_missing_medians(self):
        d = self.rain(yr=1.0, wn=1.0, wn50=1.0)
        d.loc[d.index[:10], "wn_p_p50"] = float("nan")
        ev = summarize.events(d)
        self.assertEqual(set(ev) - {"wet_hours", "dry_hours"}, {"yr", "wn", "wn50"})
        # A missing median is left out, never counted as "no rain forecast" (a miss).
        self.assertEqual(ev["wn50"]["pod"], 1.0)


if __name__ == "__main__":
    unittest.main()
