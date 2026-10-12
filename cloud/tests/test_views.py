"""Shared rain cohorts and calendar periods across page views."""
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cloud.score import SCORED_COLUMNS
from cloud.summarize import build

STATIONS = [{"station_id": "SN1", "name": "Station", "latitude": 60, "longitude": 10, "elevation_m": 10}]


def history():
    rows = [dict(target=f"{day}T12:00:00Z", station="SN1", h=24,
                 obs_t=1, yr_t=2, wn_t=3, yr_t_p10=0, yr_t_p90=4,
                 wn_t_p10=0, wn_t_p50=3, wn_t_p90=4,
                 obs_w=1, yr_w=2, wn_w=3, obs_p=1, yr_p=1.2, wn_p=3, wn_p_p50=0.8)
            for day in ("2026-09-01", "2026-10-01", "2026-10-02", "2026-10-31")]
    return pd.DataFrame(rows).reindex(columns=SCORED_COLUMNS)


class ViewTest(unittest.TestCase):
    def export(self, frame, publish=True, now="2026-11-02T00:00:00Z"):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(frame, root, stations=STATIONS, heights={}, publish_values=publish, now=pd.Timestamp(now))
            return {p.relative_to(root).as_posix(): json.loads(p.read_text(encoding="utf-8"))
                    for p in root.rglob("*.json")}

    def test_last30_means_calendar_days_even_with_gaps(self):
        data = self.export(history())
        self.assertEqual(data["meta.json"]["periods"]["last30"], {"start": "2026-10-02", "end": "2026-10-31"})
        self.assertEqual(data["leaderboard.json"]["t"]["24"]["last30"]["n"], 2)
        views = data["views.json"]
        for v in ("t", "w", "p"):
            self.assertEqual(views["last30"]["stations"][v]["24"]["SN1"]["n"], 2)
            self.assertEqual(views["all"]["stations"][v]["24"]["SN1"]["n"], 4)
            self.assertEqual([r["day"] for r in views["last30"]["trend"][v]["24"]], ["2026-10-02", "2026-10-31"])

    def test_rain_views_use_median_on_shared_available_hours(self):
        frame = history()
        frame.loc[0, "wn_p_p50"] = None
        data = self.export(frame)
        view = data["views.json"]["all"]
        station = view["stations"]["p"]["24"]["SN1"]
        self.assertEqual((station["n"], station["yr"], station["wn"]), (3, 0.2, 0.2))
        self.assertEqual(len(view["trend"]["p"]["24"]), 3)
        wet = next(r for r in view["patterns"]["p"]["24"] if r["label"] == "Wet hours")
        self.assertEqual(wet["mae_wn"], 0.2)
        self.assertEqual(view["rain"]["24"]["wn"]["wet_mae"], 2.0)  # labelled mean alternative stays mean
        self.assertEqual(data["leaderboard.json"]["p"]["24"]["all"]["n"], 3)

    def test_missing_median_does_not_fall_back_to_mean(self):
        data = self.export(history().drop(columns="wn_p_p50"))
        self.assertEqual(data["views.json"]["all"]["stations"]["p"], {})

    def test_uncertainty_uses_common_provider_cohort(self):
        frame = history()
        frame.loc[0, "yr_t_p10"] = None
        view = self.export(frame)["views.json"]["all"]["calibration"]["t"]["24"]
        self.assertEqual([view[p]["n"] for p in ("yr", "wn")], [3, 3])
        self.assertEqual(view["q"]["n"], 3)

    def test_recent_series_uses_seven_calendar_days(self):
        series = self.export(history())["recent/SN1.json"]
        self.assertEqual(series["time"], ["2026-10-31T12:00:00Z"])
        self.assertEqual(series["wn_p_p50"], [0.8])

    def test_recent_median_obeys_publication_gate(self):
        frame = history()
        off = self.export(frame, publish=False)["recent/SN1.json"]
        self.assertNotIn("wn_p_p50", off)
        recent = self.export(frame, now="2026-10-31T12:30:00Z")["recent/SN1.json"]
        self.assertEqual(recent["wn_p_p50"], [None])

    def test_export_does_not_mutate_input(self):
        frame = history()
        before = frame.copy(deep=True)
        self.export(frame)
        pd.testing.assert_frame_equal(frame, before)

    def test_empty_history_exports_empty_views(self):
        data = self.export(pd.DataFrame())
        self.assertEqual(data["views.json"], {})


if __name__ == "__main__":
    unittest.main()
