"""WeatherNext sampling method: bilinear on the native grid, recorded per row."""
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from cloud import score, weathernext
from cloud.config import LOCAL_BILINEAR_SINCE, PENDING_COLUMNS, WN_SAMPLING, WN_SAMPLING_OLD
from cloud.store import load_scored
from cloud.tests.test_pipeline import F0, FakeEE
from cloud.timeutil import iso

UTC = timezone.utc


class CollectorTest(unittest.TestCase):
    def test_rows_record_bilinear_and_point_scale(self):
        seen = []

        class Spy(FakeEE):
            def sample(self, coll, bands, scale, init, hours, stations):
                seen.append(scale)
                return super().sample(coll, bands, scale, init, hours, stations)

        rows, _ = weathernext.collect([{"station_id": "SN1", "latitude": 60, "longitude": 10}], F0,
                                      Spy("2026-10-01T04:00:00Z", "2026-09-30T18:00:00Z"))
        self.assertTrue(rows)
        self.assertEqual({r["sampling"] for r in rows}, {WN_SAMPLING})
        self.assertEqual(set(seen), {weathernext.POINT_SCALE_M})


class ScoreTest(unittest.TestCase):
    def test_sampling_carried_to_scored_rows(self):
        target = datetime(2026, 10, 2, 12, tzinfo=UTC)
        f = target - timedelta(hours=6)
        base = dict(station="SN1", fetched_at=iso(f), issued_at=iso(f), target=iso(target), lead_h=6.0)
        rows = [dict(base, provider="yr", t=1.0), dict(base, provider="wn", t=2.0, sampling=WN_SAMPLING)]
        obs = pd.DataFrame([{"station": "SN1", "time": iso(target), "t": 1.5, "w": None, "p": None}])
        s = score.score_targets(pd.DataFrame(rows, columns=PENDING_COLUMNS), obs)
        self.assertEqual(s.iloc[0].wn_sampling, WN_SAMPLING)
        self.assertEqual(list(s.columns), score.SCORED_COLUMNS)


class MigrateTest(unittest.TestCase):
    def test_runs_marked_by_retrieval_time(self):
        from cloud import migrate_sqlite
        cut = datetime.fromisoformat(LOCAL_BILINEAR_SINCE.replace("Z", "+00:00"))
        met_issue = cut + timedelta(hours=5)
        met_fetch = met_issue + timedelta(minutes=30)
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "w.db"
            con = sqlite3.connect(db)
            con.executescript("""
            CREATE TABLE locations(id INTEGER PRIMARY KEY, station_id TEXT, active INT);
            CREATE TABLE forecast_runs(id INTEGER PRIMARY KEY, provider TEXT, location_id INT, issued_at TEXT, retrieved_at TEXT);
            CREATE TABLE forecasts(run_id INT, valid_at TEXT, lead_hours REAL, air_temperature REAL, wind_speed REAL, precipitation_1h REAL);
            CREATE TABLE weathernext_samples(run_id INT, valid_at TEXT, metric TEXT, statistic TEXT, value REAL, retrieved_at TEXT);
            CREATE TABLE observations(location_id INT, source_id TEXT, observed_at TEXT, air_temperature REAL, wind_speed REAL, precipitation_1h REAL);
            INSERT INTO locations VALUES (1,'sn1',1);
            """)
            con.execute("INSERT INTO forecast_runs VALUES (1,'MET',1,?,?)", (iso(met_issue), iso(met_fetch)))
            # Run 2 was retrieved just before the switch, run 3 just after it.
            runs = {2: (cut - timedelta(hours=4), cut - timedelta(minutes=1)),
                    3: (cut - timedelta(hours=1), cut + timedelta(minutes=1))}
            for rid, (issued, got) in runs.items():
                con.execute("INSERT INTO forecast_runs VALUES (?,'WeatherNext3-mean',1,?,?)",
                            (rid, iso(issued), iso(got)))
            for h in range(1, 13):
                t = met_fetch.replace(minute=0) + timedelta(hours=h)
                con.execute("INSERT INTO forecasts VALUES (1,?,?,?,?,?)", (iso(t), h, 10.0, 3.0, 0.2))
                for rid, (_, got) in runs.items():
                    con.execute("INSERT INTO weathernext_samples VALUES (?,?,?,?,?,?)",
                                (rid, iso(t), "air_temperature", "mean", float(rid), iso(got)))
                con.execute("INSERT INTO observations VALUES (1,'SN1',?,11.0,3.5,0.0)", (iso(t),))
            con.commit(); con.close()
            pending = migrate_sqlite.station_pending(sqlite3.connect(db), 1, "SN1")
            wn = pending[pending.provider == "wn"]
            self.assertEqual(set(wn.sampling), {WN_SAMPLING})   # newest run 3 is chosen
            self.assertEqual(set(wn.t), {3.0})
            out = Path(tmp) / "scored"
            day = (met_fetch + timedelta(hours=6)).date()
            migrate_sqlite.migrate(db, day + timedelta(days=1), out, log=lambda *a: None, start=day)
            self.assertEqual(set(load_scored(out).wn_sampling.dropna()), {WN_SAMPLING})

    def test_old_run_marked_old(self):
        from cloud import migrate_sqlite
        cut = datetime.fromisoformat(LOCAL_BILINEAR_SINCE.replace("Z", "+00:00"))
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "w.db"
            con = sqlite3.connect(db)
            con.executescript("""
            CREATE TABLE forecast_runs(id INTEGER PRIMARY KEY, provider TEXT, location_id INT, issued_at TEXT, retrieved_at TEXT);
            CREATE TABLE forecasts(run_id INT, valid_at TEXT, lead_hours REAL, air_temperature REAL, wind_speed REAL, precipitation_1h REAL);
            CREATE TABLE weathernext_samples(run_id INT, valid_at TEXT, metric TEXT, statistic TEXT, value REAL, retrieved_at TEXT);
            """)
            fetch = cut - timedelta(hours=1)
            con.execute("INSERT INTO forecast_runs VALUES (1,'MET',1,?,?)", (iso(fetch), iso(fetch)))
            con.execute("INSERT INTO forecast_runs VALUES (2,'WeatherNext3-mean',1,?,?)",
                        (iso(fetch - timedelta(hours=6)), iso(fetch - timedelta(hours=2))))
            t = fetch.replace(minute=0) + timedelta(hours=6)
            con.execute("INSERT INTO forecasts VALUES (1,?,6,10.0,3.0,0.2)", (iso(t),))
            con.execute("INSERT INTO weathernext_samples VALUES (2,?,'air_temperature','mean',1.0,?)",
                        (iso(t), iso(fetch - timedelta(hours=2))))
            con.commit()
            pending = migrate_sqlite.station_pending(con, 1, "SN1")
            con.close()
            self.assertEqual(set(pending[pending.provider == "wn"].sampling), {WN_SAMPLING_OLD})


HEIGHTS = {"stations": {
    "LAND": {"elev": 100.0, "cell_nn5km": 400.0, "cell_bilinear": 200.0, "offshore": False},
    "SEA": {"elev": 60.0, "cell_nn5km": 0.0, "cell_bilinear": 0.0, "offshore": True},
    "NOTE": {"elev": 10.0, "cell_nn5km": 30.0, "cell_bilinear": 40.0, "offshore": False, "note": "Lake."},
}}


class HeightTest(unittest.TestCase):
    def test_adjustment_per_sampling_method(self):
        from cloud.heights import adjusted_t
        df = pd.DataFrame({"station": ["LAND", "LAND", "LAND", "SEA", "UNKNOWN"],
                           "wn_sampling": [None, WN_SAMPLING_OLD, WN_SAMPLING, None, None],
                           "wn_t": [5.0, 5.0, 5.0, 5.0, 5.0]})
        got = adjusted_t(df, HEIGHTS).round(3).tolist()
        # Empty marker = old method: 300 m -> +1.95 °C. Bilinear: 100 m -> +0.65 °C.
        self.assertEqual(got, [6.95, 6.95, 5.65, 5.0, 5.0])

    def test_flags_keep_every_station_and_explain(self):
        from cloud.heights import flags
        f = flags(HEIGHTS)
        self.assertEqual(f["LAND"], {"dz": 100, "expected": -0.7, "dz_old": 300})
        self.assertNotIn("SEA", f)
        self.assertEqual(f["NOTE"], {"note": "Lake."})

    def test_build_adds_secondary_line_and_flags(self):
        import json
        from cloud import summarize
        from cloud.tests.test_pipeline import synthetic_scored
        stations = [{"station_id": s, "name": s, "latitude": 60, "longitude": 10, "elevation_m": 100}
                    for s in ("LAND", "SEA", "NOTE")]
        scored = synthetic_scored(days=8, stations=("LAND", "SEA", "NOTE"))
        with tempfile.TemporaryDirectory() as tmp:
            summarize.build(scored, Path(tmp), stations, heights=HEIGHTS)
            board = json.loads((Path(tmp) / "leaderboard.json").read_text(encoding="utf-8"))
            meta = json.loads((Path(tmp) / "meta.json").read_text(encoding="utf-8"))
            per = json.loads((Path(tmp) / "stations.json").read_text(encoding="utf-8"))
        s = board["t"]["24"]["all"]
        self.assertIn("mae_wnh", s)
        self.assertIn(s["verdict_h"], ("yr", "weathernext", "too_close"))
        self.assertIn(s["verdict"], ("yr", "weathernext", "too_close"))  # primary verdict kept
        self.assertNotIn("mae_wnh", board["w"]["24"]["all"])
        self.assertEqual(per["t"]["24"]["SEA"]["wnh"], per["t"]["24"]["SEA"]["wn"])
        self.assertEqual({x["id"] for x in meta["stations"]}, {"LAND", "SEA", "NOTE"})  # none dropped
        self.assertEqual({x["id"] for x in meta["stations"] if "flag" in x}, {"LAND", "NOTE"})

    def test_build_without_heights_has_no_secondary_line(self):
        import json
        from cloud import summarize
        from cloud.tests.test_pipeline import synthetic_scored
        stations = [{"station_id": "SN1", "name": "A", "latitude": 60, "longitude": 10}]
        with tempfile.TemporaryDirectory() as tmp:
            summarize.build(synthetic_scored(days=2, stations=("SN1",)), Path(tmp), stations,
                            heights={"stations": {}})
            board = json.loads((Path(tmp) / "leaderboard.json").read_text(encoding="utf-8"))
        self.assertNotIn("mae_wnh", board["t"]["24"]["all"])


if __name__ == "__main__":
    unittest.main()
