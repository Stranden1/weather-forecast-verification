"""ECMWF IFS/AIFS via Open-Meteo: request, parsing (recorded response) and scoring."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

from cloud import openmeteo, score
from cloud.config import PENDING_COLUMNS
from cloud.timeutil import iso

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "openmeteo_ecmwf.json").read_text(encoding="utf-8"))
FETCHED = datetime.fromisoformat(FIXTURE["recorded_at"].replace("Z", "+00:00"))
UTC = timezone.utc


class FakeResponse:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Serves the recorded forecast and metadata; can fail the first forecast call."""
    def __init__(self, first_status=None):
        self.calls, self.first_status = [], first_status

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params))
        if url == openmeteo.URL:
            if self.first_status and sum(u == openmeteo.URL for u, _ in self.calls) == 1:
                return FakeResponse({}, self.first_status)
            return FakeResponse(FIXTURE["response"])
        model = url.split("/data/")[1].split("/")[0]
        return FakeResponse(FIXTURE["meta"][model])


class RequestTest(unittest.TestCase):
    def test_params_send_station_heights_and_both_models(self):
        p = openmeteo.request_params(FIXTURE["stations"])
        self.assertEqual(p, FIXTURE["params"])  # what the recording was made with
        self.assertEqual(p["models"], "ecmwf_ifs,ecmwf_aifs025_single")
        self.assertEqual(p["wind_speed_unit"], "ms")
        self.assertEqual(p["hourly"], "temperature_2m,wind_speed_10m,precipitation")
        heights = p["elevation"].split(",")
        for s, h in zip(FIXTURE["stations"], heights):
            self.assertEqual(h, "nan" if s["elevation_m"] is None else f"{s['elevation_m']:g}")
        self.assertIn("nan", heights)  # Troll B has no station height


class ParseTest(unittest.TestCase):
    def setUp(self):
        with mock.patch("time.sleep"):
            self.rows, self.errors = openmeteo.collect(FIXTURE["stations"], FETCHED, FakeSession())

    def test_rows_only_inside_horizon_windows(self):
        self.assertEqual(self.errors, [])
        self.assertEqual({r["provider"] for r in self.rows}, {"ifs", "aifs"})
        self.assertEqual({r["station"] for r in self.rows}, {s["station_id"] for s in FIXTURE["stations"]})
        for r in self.rows:
            self.assertTrue(openmeteo.in_window(r["lead_h"]), r)
            self.assertTrue(r["target"].endswith("Z"))
            self.assertEqual(r["fetched_at"], iso(FETCHED))

    def test_values_match_the_recording_at_the_same_hour(self):
        payload = FIXTURE["response"][0]
        station = FIXTURE["stations"][0]["station_id"]
        times = payload["hourly"]["time"]
        for r in [x for x in self.rows if x["station"] == station][:40]:
            i = times.index(r["target"][:16])
            model = openmeteo.MODELS[r["provider"]]
            self.assertEqual(r["t"], payload["hourly"][f"temperature_2m_{model}"][i])
            self.assertEqual(r["w"], payload["hourly"][f"wind_speed_10m_{model}"][i])
            # Preceding-hour sum: keyed by its own time, the interval end (no shift).
            self.assertEqual(r["p"], payload["hourly"][f"precipitation_{model}"][i])

    def test_issue_time_from_model_metadata(self):
        for name, model in openmeteo.MODELS.items():
            want = iso(datetime.fromtimestamp(FIXTURE["meta"][model]["last_run_initialisation_time"], UTC))
            self.assertEqual({r["issued_at"] for r in self.rows if r["provider"] == name}, {want})


class RobustnessTest(unittest.TestCase):
    def test_retries_after_rate_limit(self):
        s = FakeSession(first_status=429)
        with mock.patch("time.sleep") as sleep:
            rows, errors = openmeteo.collect(FIXTURE["stations"], FETCHED, s)
        self.assertEqual(errors, [])
        self.assertTrue(rows)
        sleep.assert_called()

    def test_wrong_location_count_is_an_error_not_a_crash(self):
        s = FakeSession()
        with mock.patch("time.sleep"):
            rows, errors = openmeteo.collect(FIXTURE["stations"] + FIXTURE["stations"][:1], FETCHED, s)
        self.assertEqual(rows, [])
        self.assertEqual(len(errors), 1)


def pend(provider, fetched, target, **kw):
    lead = (target - fetched).total_seconds() / 3600
    return dict(provider=provider, station="SN1", fetched_at=iso(fetched), issued_at=iso(fetched),
                target=iso(target), lead_h=lead, **kw)


class ScoreTest(unittest.TestCase):
    def test_ecmwf_rides_along_with_the_chosen_fetch(self):
        target = datetime(2026, 10, 2, 12, tzinfo=UTC)
        f_a = target - timedelta(hours=26)   # both Yr and WN: chosen for 24 h
        f_b = target - timedelta(hours=24)   # exact 24 h, but ECMWF only: must not be chosen
        rows = [pend("yr", f_a, target, t=1.0), pend("wn", f_a, target, t=2.0),
                pend("ifs", f_a, target, t=3.0, w=4.0, p=0.5), pend("aifs", f_a, target, t=5.0, p=0.7),
                pend("ifs", f_b, target, t=9.0), pend("aifs", f_b, target, t=9.0)]
        obs = pd.DataFrame([{"station": "SN1", "time": iso(target), "t": 0.0, "w": 1.0, "p": 0.0}])
        s = score.score_targets(pd.DataFrame(rows, columns=PENDING_COLUMNS), obs)
        r = s[s.h == 24].iloc[0]
        self.assertEqual(r.fetched_at, iso(f_a))
        self.assertEqual((r.yr_t, r.wn_t, r.ifs_t, r.ifs_w, r.ifs_p, r.aifs_t, r.aifs_p),
                         (1.0, 2.0, 3.0, 4.0, 0.5, 5.0, 0.7))
        self.assertEqual(r.ifs_issued, iso(f_a))
        self.assertEqual(list(s.columns), score.SCORED_COLUMNS)

    def test_rain_blanked_beyond_48h_and_missing_ecmwf_is_empty(self):
        target = datetime(2026, 10, 5, 12, tzinfo=UTC)
        f = target - timedelta(hours=72)
        rows = [pend("yr", f, target, t=1.0, p=2.0), pend("wn", f, target, t=1.5, p=1.0),
                pend("ifs", f, target, t=1.2, p=3.0)]
        obs = pd.DataFrame([{"station": "SN1", "time": iso(target), "t": 1.2, "w": 1, "p": 0.0}])
        r = score.score_targets(pd.DataFrame(rows, columns=PENDING_COLUMNS), obs).iloc[0]
        self.assertEqual(r.ifs_t, 1.2)
        self.assertTrue(pd.isna(r.ifs_p))
        self.assertTrue(pd.isna(r.aifs_t))  # no AIFS in that fetch


if __name__ == "__main__":
    unittest.main()
