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
