"""Forecast steadiness: revision size, moving toward the truth and flip-flops."""
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cloud import replay, summarize
from cloud.score import SCORED_COLUMNS

STATIONS = [{"station_id": "SN1", "name": "A", "latitude": 60.0, "longitude": 10.0}]


def row(target, h, obs, yr, wn, station="SN1", var="t", yr_iss=None, wn_iss=None):
    """One scored history row. Issue times differ per horizon unless given."""
    r = {"target": target, "station": station, "h": h, "lead_h": float(h),
         "yr_issued": yr_iss or f"yr-{target}-{h}", "wn_issued": wn_iss or f"wn-{target}-{h}",
         f"obs_{var}": obs, f"yr_{var}": yr, f"wn_{var}": wn}
    return r


def frame(rows):
    return pd.DataFrame(rows).reindex(columns=SCORED_COLUMNS)


def step(res, frm, to):
    return next(s for s in res["steps"] if (s["from"], s["to"]) == (frm, to))


class SteadinessTest(unittest.TestCase):
    def test_revision_size_and_toward_truth(self):
        T = "2026-10-01T12:00:00Z"
        # Yr: 10 -> 12 (toward obs 13, revision 2). WeatherNext: 11 -> 10.5 (away, 0.5).
        res = replay.steadiness(frame([row(T, 48, 13, 10, 11), row(T, 24, 13, 12, 10.5)]), "t")
        s = step(res, 48, 24)
        self.assertEqual((s["n"], s["same_issue"]), (1, 0))
        self.assertEqual(s["yr"], {"rev": 2.0, "moved": 1, "toward": 1.0})
        self.assertEqual(s["wn"], {"rev": 0.5, "moved": 1, "toward": 0.0})
        self.assertEqual(s["diff"], -1.5)
        self.assertEqual(s["steadier"], "not_enough_data")  # one day only

    def test_tiny_revisions_do_not_count_as_moves(self):
        T = "2026-10-01T12:00:00Z"
        s = step(replay.steadiness(frame([row(T, 12, 5, 5.0, 5.0), row(T, 6, 5, 5.1, 5.0)]), "t"), 12, 6)
        self.assertEqual(s["yr"]["moved"], 0)
        self.assertIsNone(s["yr"]["toward"])

    def test_unchanged_issue_is_not_a_revision(self):
        T = "2026-10-01T12:00:00Z"
        rows = [row(T, 12, 5, 4, 6, wn_iss="run-A"), row(T, 6, 5, 5, 6, wn_iss="run-A")]
        res = replay.steadiness(frame(rows), "t")
        self.assertEqual(res["steps"], [])  # the only pair was left out for both services
        T2 = "2026-10-01T13:00:00Z"
        rows += [row(T2, 12, 5, 4, 6), row(T2, 6, 5, 5, 7)]
        s = step(replay.steadiness(frame(rows), "t"), 12, 6)
        self.assertEqual((s["n"], s["same_issue"]), (1, 1))

    def test_unknown_issue_counts_as_new_forecast(self):
        T = "2026-10-01T12:00:00Z"
        rows = [row(T, 12, 5, 4, 6), row(T, 6, 5, 5, 6)]
        for r in rows:
            r["yr_issued"] = r["wn_issued"] = None
        self.assertEqual(step(replay.steadiness(frame(rows), "t"), 12, 6)["n"], 1)

    def test_flip_flops_counted_on_same_targets(self):
        rows = []
        for i in range(4):
            T = f"2026-10-01T{i:02d}:00:00Z"
            yr = (5, 8, 5) if i == 0 else (5, 5.5, 6)   # one Yr flip-flop of 3 degrees
            wn = (5, 6, 7)                               # steady trend, no flip
            for h, y, w in zip((48, 24, 12), yr, wn):
                rows.append(row(T, h, 6, y, w))
        f = replay.steadiness(frame(rows), "t")["flip"]
        self.assertEqual(f["n"], 4)
        self.assertEqual((f["yr"], f["wn"]), (25.0, 0.0))

    def test_small_opposite_revisions_are_not_flip_flops(self):
        T = "2026-10-01T12:00:00Z"
        rows = [row(T, 48, 6, 5, 5), row(T, 24, 6, 5.8, 5), row(T, 12, 6, 5.2, 5)]
        self.assertEqual(replay.steadiness(frame(rows), "t")["flip"]["yr"], 0.0)

    def test_rain_uses_only_rain_horizons(self):
        T = "2026-10-01T12:00:00Z"
        rows = [row(T, h, 1.0, v, v, var="p") for h, v in ((72, 9.0), (48, 0.0), (24, 1.0))]
        res = replay.steadiness(frame(rows), "p")
        self.assertEqual([(s["from"], s["to"]) for s in res["steps"]], [(48, 24)])

    def test_verdict_after_enough_days(self):
        rows = []
        for d in range(1, 9):
            for hr in (0, 6, 12, 18):
                T = f"2026-10-{d:02d}T{hr:02d}:00:00Z"
                rows += [row(T, 24, 5, 3 + hr / 10, 5), row(T, 12, 5, 5 + d / 10, 5.1)]
        s = step(replay.steadiness(frame(rows), "t"), 24, 12)
        self.assertEqual(s["days"], 8)
        self.assertEqual(s["steadier"], "weathernext")
        self.assertLess(s["ci_hi"], 0)

    def test_empty_history(self):
        self.assertEqual(replay.steadiness(pd.DataFrame(), "t"), {"steps": [], "flip": {"n": 0}})
        self.assertEqual(replay.steadiness(frame([]), "w"), {"steps": [], "flip": {"n": 0}})

    def test_build_writes_steadiness_json(self):
        T = "2026-10-01T12:00:00Z"
        scored = frame([row(T, 48, 13, 10, 11), row(T, 24, 13, 12, 10.5)])
        with tempfile.TemporaryDirectory() as tmp:
            summarize.build(scored, Path(tmp), stations=STATIONS)
            data = json.loads((Path(tmp) / "steadiness.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data), {"t", "w", "p"})
        self.assertEqual(data["t"]["steps"][0]["yr"]["rev"], 2.0)
        self.assertEqual(data["w"]["steps"], [])


if __name__ == "__main__":
    unittest.main()


def storm_rows(day="2026-10-05", station="SN1", rain_mm=1.0, wind=5.0, temp=3.0, hs=(6, 12, 24, 48),
               yr=0.5, wn=0.8, hours=range(24)):
    """Scored rows for one station-day: every hour measured, forecasts at each horizon."""
    rows = []
    for hr in hours:
        T = f"{day}T{hr:02d}:00:00Z"
        for h in hs:
            r = {"target": T, "station": station, "h": h, "lead_h": float(h),
                 "obs_t": temp, "obs_w": wind, "obs_p": rain_mm,
                 "yr_t": temp + 1, "wn_t": temp - 1, "yr_w": wind - 2, "wn_w": wind - 1}
            if h in (6, 12, 24, 48):
                r.update(yr_p=yr, wn_p=wn, wn_p_p50=wn / 2)
            rows.append(r)
    return frame(rows)


class EventTest(unittest.TestCase):
    def test_triggers_and_grouping_per_day(self):
        df = pd.concat([storm_rows(station="A", rain_mm=1.0), storm_rows(station="B", rain_mm=1.5),
                        storm_rows(station="C", rain_mm=0.1, wind=16.0)], ignore_index=True)
        ev = {e["id"]: e for e in replay.find_events(df)}
        self.assertEqual(set(ev), {"2026-10-05-rain", "2026-10-05-wind"})
        rain = ev["2026-10-05-rain"]
        self.assertEqual([s["station"] for s in rain["stations"]], ["B", "A"])  # most extreme first
        self.assertEqual((rain["station"], rain["value"]), ("B", 36.0))
        self.assertEqual(ev["2026-10-05-wind"]["value"], 16.0)

    def test_cold_snap_picks_the_lowest(self):
        df = pd.concat([storm_rows(station="A", temp=-6.0), storm_rows(station="B", temp=-9.5)])
        e = [x for x in replay.find_events(df) if x["type"] == "cold"][0]
        self.assertEqual((e["station"], e["value"]), ("B", -9.5))

    def test_incomplete_rain_day_is_not_an_event(self):
        df = storm_rows(rain_mm=5.0, hours=range(23))  # 115 mm, but one hour unmeasured
        self.assertEqual(replay.find_events(df), [])

    def test_selection_never_depends_on_forecasts(self):
        df = pd.concat([storm_rows(station="A", rain_mm=1.0), storm_rows(station="B", wind=17.0)])
        changed = df.copy()
        for c in [c for c in df if c.startswith(("yr_", "wn_"))]:
            changed[c] = changed[c] * 3 + 7
        self.assertEqual(replay.find_events(df), replay.find_events(changed))

    def test_keeps_recent_and_most_extreme(self):
        events = [{"id": f"d{i:02d}-rain", "day": f"2026-08-{i:02d}", "type": "rain", "value": float(i)}
                  for i in range(1, 32)]
        events.append({"id": "d00-rain", "day": "2026-07-01", "type": "rain", "value": 99.0})
        kept = [e["id"] for e in replay.select_events(events)]
        self.assertEqual(len(kept), 31)          # 30 newest + the old record-breaker
        self.assertIn("d00-rain", kept)
        self.assertEqual(kept[0], "d31-rain")    # newest first


class ReplayTest(unittest.TestCase):
    NOW = pd.Timestamp("2026-10-10T00:00:00Z")

    def test_rain_day_total_per_horizon(self):
        df = storm_rows(rain_mm=1.0, yr=0.5, wn=0.8)
        idx, reps = replay.build_replays(df, publish_values=True, now=self.NOW)
        r = reps["2026-10-05-rain"]
        self.assertEqual([p["h"] for p in r["points"]], [48, 24, 12, 6])  # farthest first
        self.assertEqual(r["points"][0], {"h": 48, "yr": 12.0, "wn": 19.2, "wn50": 9.6})
        self.assertEqual(r["observed"], 24.0)
        self.assertTrue(r["wn_shown"])
        self.assertEqual(idx[0]["id"], "2026-10-05-rain")

    def test_rain_horizon_needs_all_24_hours(self):
        df = storm_rows(rain_mm=1.0)
        df.loc[(df.h == 48) & (df.target == "2026-10-05T03:00:00Z"), "wn_p"] = None
        r = replay.build_replays(df, True, self.NOW)[1]["2026-10-05-rain"]
        self.assertNotIn(48, [p["h"] for p in r["points"]])

    def test_wind_uses_one_hour_for_every_horizon(self):
        df = storm_rows(wind=10.0, hs=(6, 12, 24, 48, 72))
        df.loc[df.target == "2026-10-05T14:00:00Z", "obs_w"] = 18.0
        r = replay.build_replays(df, True, self.NOW)[1]["2026-10-05-wind"]
        self.assertEqual(r["target"], "2026-10-05T14:00:00Z")
        self.assertEqual(r["observed"], 18.0)
        self.assertEqual([p["h"] for p in r["points"]], [72, 48, 24, 12, 6])

    def test_weathernext_values_only_when_published(self):
        df = storm_rows(rain_mm=1.0)
        r = replay.build_replays(df, publish_values=False, now=self.NOW)[1]["2026-10-05-rain"]
        self.assertFalse(r["wn_shown"])
        self.assertTrue(all("wn" not in p and "wn50" not in p for p in r["points"]))
        self.assertTrue(all(p["yr"] is not None for p in r["points"]))

    def test_weathernext_values_never_for_the_last_hour_or_future(self):
        df = storm_rows(rain_mm=1.0)
        too_soon = pd.Timestamp("2026-10-05T23:30:00Z")  # the day's last hour is < 1 h ago
        r = replay.build_replays(df, True, too_soon)[1]["2026-10-05-rain"]
        self.assertFalse(r["wn_shown"])
        ok = pd.Timestamp("2026-10-06T00:00:00Z")         # 1 hour after 23:00
        self.assertTrue(replay.build_replays(df, True, ok)[1]["2026-10-05-rain"]["wn_shown"])

    def test_stable_ids_and_empty_history(self):
        df = storm_rows(rain_mm=1.0)
        self.assertEqual(replay.build_replays(df, True, self.NOW)[0], replay.build_replays(df, True, self.NOW)[0])
        self.assertEqual(replay.build_replays(pd.DataFrame(), True, self.NOW), ([], {}))


class PublishTest(unittest.TestCase):
    def build(self, publish, now):
        df = storm_rows(rain_mm=1.0)
        with tempfile.TemporaryDirectory() as tmp:
            summarize.build(df, Path(tmp), stations=[{"station_id": "SN1", "name": "A", "latitude": 60,
                                                       "longitude": 10}], publish_values=publish,
                            heights={"stations": {}}, now=pd.Timestamp(now))
            recent = json.loads((Path(tmp) / "recent" / "SN1.json").read_text(encoding="utf-8"))
            meta = json.loads((Path(tmp) / "meta.json").read_text(encoding="utf-8"))
            events = json.loads((Path(tmp) / "events.json").read_text(encoding="utf-8"))
            rep = json.loads((Path(tmp) / "events" / "2026-10-05-rain.json").read_text(encoding="utf-8"))
        return recent, meta, events, rep

    def test_off_means_no_weathernext_values_anywhere(self):
        recent, meta, events, rep = self.build(False, "2026-10-10")
        self.assertNotIn("wn_t", recent)
        self.assertFalse(rep["wn_shown"])
        self.assertFalse(meta["publish_forecast_values"])

    def test_on_publishes_only_hours_at_least_one_hour_old_with_notices(self):
        recent, meta, events, rep = self.build(True, "2026-10-05T12:30:00Z")
        shown = [t for t, v in zip(recent["time"], recent["wn_t"]) if v is not None]
        self.assertTrue(shown)
        self.assertLessEqual(max(shown), "2026-10-05T11:00:00Z")      # 11:30 cutoff
        self.assertIsNone(recent["wn_t"][recent["time"].index("2026-10-05T12:00:00Z")])
        self.assertFalse(rep["wn_shown"])                              # the day isn't over yet
        notes = " ".join(meta["wn_value_attribution"])
        self.assertIn("under CC BY 4.0 licence terms", notes)
        self.assertIn("https://storage.googleapis.com/weathernext-public/terms-of-use.pdf", notes)
        self.assertIn("accessed via Google Earth Engine", notes)


class EventChoiceTest(unittest.TestCase):
    def test_offshore_platforms_do_not_make_wind_events(self):
        df = pd.concat([storm_rows(station="SEA", wind=18.0), storm_rows(station="LAND", wind=16.0)])
        ev = [e for e in replay.find_events(df, offshore={"SEA"}) if e["type"] == "wind"]
        self.assertEqual([s["station"] for s in ev[0]["stations"]], ["LAND"])

    def test_wind_replay_prefers_an_hour_that_met_the_threshold(self):
        df = storm_rows(wind=10.0, hs=(6, 12, 24))
        long = storm_rows(wind=10.0, hs=(72, 120), hours=[12])          # 12 UTC has more horizons
        df = pd.concat([df, long], ignore_index=True)
        df.loc[df.target == "2026-10-05T15:00:00Z", "obs_w"] = 16.5     # the storm hour
        r = replay.build_replays(df, True, pd.Timestamp("2026-10-10T00:00:00Z"))[1]["2026-10-05-wind"]
        self.assertEqual((r["target"], r["observed"]), ("2026-10-05T15:00:00Z", 16.5))
