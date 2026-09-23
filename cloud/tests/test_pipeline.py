import gzip, json, sqlite3, tempfile, unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from cloud import frost, score, summarize, weathernext, yr
from cloud.config import HORIZONS, PENDING_COLUMNS
from cloud.store import State, load_scored, write_scored
from cloud.timeutil import iso

UTC = timezone.utc
F0 = datetime(2026, 10, 1, 6, 10, tzinfo=UTC)


def yr_payload(fetched, hours=70):
    ts = []
    base = fetched.replace(minute=0)
    for h in range(0, hours):
        t = base + timedelta(hours=h)
        ts.append({"time": iso(t), "data": {
            "instant": {"details": {"air_temperature": 10 + h * 0.1, "air_temperature_percentile_10": 9,
                                    "air_temperature_percentile_90": 11, "wind_speed": 3.0,
                                    "wind_speed_percentile_10": 2, "wind_speed_percentile_90": 4}},
            "next_1_hours": {"details": {"precipitation_amount": 0.5, "precipitation_amount_min": 0,
                                         "precipitation_amount_max": 1, "probability_of_precipitation": 60}}}})
    return {"properties": {"meta": {"updated_at": iso(fetched - timedelta(minutes=40))}, "timeseries": ts}}


class YrTest(unittest.TestCase):
    def test_extract_windows_and_precip_end_keying(self):
        rows = yr.extract(yr_payload(F0), "SN1", F0)
        leads = sorted(r["lead_h"] for r in rows)
        self.assertTrue(all(any(abs(l - h) <= 3 for h in HORIZONS) for l in leads))
        self.assertFalse(any(r["target"] == iso(F0.replace(minute=0)) for r in rows))
        # precip from step 06:00 belongs to target 07:00 -> only if 07:00 in a window (lead ~0.8 -> no)
        by = {r["target"]: r for r in rows}
        t = iso(datetime(2026, 10, 1, 12, tzinfo=UTC))  # lead 5.8 -> H=6 window
        self.assertEqual(by[t]["t"], 10 + 6 * 0.1)
        self.assertEqual(by[t]["p"], 0.5)  # from step 11:00
        self.assertEqual(by[t]["p_prob"], 60)


class FrostTest(unittest.TestCase):
    def test_parse_main_series_on_the_hour(self):
        data = [
            {"sourceId": "SN18700:0", "referenceTime": "2026-10-01T06:00:00.000Z", "observations": [
                {"elementId": "air_temperature", "value": 5.1, "timeSeriesId": 0},
                {"elementId": "air_temperature", "value": 99, "timeSeriesId": 1},
                {"elementId": "wind_speed", "value": 2.0, "timeSeriesId": 0}]},
            {"sourceId": "SN18700:0", "referenceTime": "2026-10-01T06:10:00.000Z", "observations": [
                {"elementId": "air_temperature", "value": 7, "timeSeriesId": 0}]},
            {"sourceId": "SN18700:0", "referenceTime": "2026-10-01T06:00:00.000Z", "observations": [
                {"elementId": frost.PRECIP, "value": 0.4, "timeSeriesId": 0, "unit": "mm",
                 "timeOffset": "PT0H", "timeResolution": "PT1H"}]},
        ]
        rows = frost.parse_rows(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["t"], rows[0]["w"], rows[0]["p"]), (5.1, 2.0, 0.4))


class FakeEE:
    def __init__(self, latest_hourly, latest_syn):
        self.h, self.s = latest_hourly, latest_syn
    def hours(self, coll, init):
        if init == self.s: return set(range(1, 361))
        if init == self.h: return set(range(1, 49))
        return set()
    def sample(self, coll, bands, scale, init, hours, stations):
        out = []
        for h in hours:
            end = iso(datetime.fromisoformat(init.replace("Z", "+00:00")) + timedelta(hours=h))
            for s in stations:
                p = {"station": s["station_id"], "end_time": end, "forecast_hour": h}
                for b in bands:
                    p[b] = 283.15 if "temperature" in b else (0.0002 if "precip" in b else 4.0)
                out.append(p)
        return out


class WeatherNextTest(unittest.TestCase):
    def test_uses_hourly_for_short_and_synoptic_for_long(self):
        src = FakeEE("2026-10-01T04:00:00Z", "2026-09-30T18:00:00Z")
        rows, errors = weathernext.collect([{"station_id": "SN1", "latitude": 60, "longitude": 10}], F0, src)
        self.assertEqual(errors, [])
        inits = {r["issued_at"] for r in rows if r["lead_h"] < 10}
        self.assertEqual(inits, {"2026-10-01T04:00:00Z"})
        self.assertTrue(all(r["issued_at"] == "2026-09-30T18:00:00Z" for r in rows if r["lead_h"] > 60))
        r = rows[0]
        self.assertAlmostEqual(r["t"], 10.0)
        self.assertAlmostEqual(r["p"], 0.2)
        self.assertTrue(all(any(abs(x["lead_h"] - h) <= 3 for h in HORIZONS) for x in rows))


def pend(provider, fetched, target, t, **kw):
    lead = (target - fetched).total_seconds() / 3600
    r = dict(provider=provider, station="SN1", fetched_at=iso(fetched), issued_at=iso(fetched),
             target=iso(target), lead_h=lead, t=t)
    r.update(kw)
    return r


class ScoreTest(unittest.TestCase):
    def test_closest_same_fetch_pairing(self):
        target = datetime(2026, 10, 2, 12, tzinfo=UTC)
        f_a = target - timedelta(hours=26)   # lead 26 -> H=24 dist 2
        f_b = target - timedelta(hours=23.5)  # lead 23.5 -> dist 0.5 but only yr present
        f_c = target - timedelta(hours=22)   # lead 22 -> dist 2, both
        rows = [pend("yr", f_a, target, 1.0), pend("wn", f_a, target, 2.0),
                pend("yr", f_b, target, 5.0),
                pend("yr", f_c, target, 3.0), pend("wn", f_c, target, 4.0)]
        obs = pd.DataFrame([{"station": "SN1", "time": iso(target), "t": 0.0, "w": None, "p": None}])
        s = score.score_targets(pd.DataFrame(rows, columns=PENDING_COLUMNS), obs)
        r = s[s.h == 24].iloc[0]
        # both-present preferred over closer single; tie at dist 2 -> later fetch (f_c)
        self.assertEqual((r.yr_t, r.wn_t), (3.0, 4.0))
        self.assertEqual(r.fetched_at, iso(f_c))

    def test_precip_dropped_on_long_horizons(self):
        target = datetime(2026, 10, 5, 12, tzinfo=UTC)
        f = target - timedelta(hours=72)
        rows = [pend("yr", f, target, 1.0, p=2.0), pend("wn", f, target, 1.5, p=1.0)]
        obs = pd.DataFrame([{"station": "SN1", "time": iso(target), "t": 1.2, "w": 1, "p": 0.0}])
        s = score.score_targets(pd.DataFrame(rows, columns=PENDING_COLUMNS), obs)
        self.assertTrue(pd.isna(s.iloc[0].yr_p))

    def test_finalize_writes_once_and_prunes(self):
        with tempfile.TemporaryDirectory() as tmp:
            st = State(Path(tmp) / "state")
            day = date(2026, 10, 2)
            target = datetime(2026, 10, 2, 12, tzinfo=UTC)
            f = target - timedelta(hours=6)
            st.add_pending([pend("yr", f, target, 1.0), pend("wn", f, target, 2.0),
                            pend("yr", f, target + timedelta(days=2), 1.0)])
            st.add_obs([{"station": "SN1", "time": iso(target), "t": 1.5, "w": None, "p": None}])
            m = st.meta(); m["first_fetch"] = iso(f); st.save_meta(m)
            got = {}
            done = score.finalize(st, now=datetime(2026, 10, 3, 7, tzinfo=UTC),
                                  write=lambda d, df: got.setdefault(d, df))
            self.assertEqual(done, ["2026-10-02"])
            self.assertEqual(len(got[day]), 1)
            self.assertEqual(len(st.pending()), 1)  # future target kept
            self.assertEqual(score.finalize(st, now=datetime(2026, 10, 3, 8, tzinfo=UTC),
                                            write=lambda d, df: 1 / 0), [])


def synthetic_scored(days=20, stations=("SN1", "SN2", "SN3"), seed=0, wn_extra=0.0):
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(days):
        day_shift = rng.normal(0, 0.5)
        for hr in range(0, 24):
            t = datetime(2026, 9, 1, tzinfo=UTC) + timedelta(days=d, hours=hr)
            for s in stations:
                for h in HORIZONS:
                    if h > 48 and hr % 6:
                        continue
                    obs = 10 + 5 * np.sin(hr / 24 * 6.28) + rng.normal()
                    e = 0.5 + h / 100
                    y = obs + rng.normal(0, e) + day_shift
                    w = obs + rng.normal(0, e + wn_extra) + day_shift
                    p_obs = max(0, rng.normal(0, 0.5))
                    rows.append(dict(target=iso(t), station=s, h=h, lead_h=h, fetched_at="x",
                                     obs_t=obs, yr_t=y, wn_t=w, wn_t_p50=w, yr_t_p10=y - 1, yr_t_p90=y + 1,
                                     wn_t_p10=w - 1.5, wn_t_p90=w + 1.5,
                                     obs_w=3, yr_w=3.2, wn_w=2.9,
                                     obs_p=p_obs if h <= 48 else None,
                                     yr_p=max(0, p_obs + rng.normal(0, .3)) if h <= 48 else None,
                                     wn_p=max(0, p_obs + rng.normal(0, .3)) if h <= 48 else None))
    return pd.DataFrame(rows)


class SummarizeTest(unittest.TestCase):
    def test_build_and_verdicts(self):
        stations = [{"station_id": s, "name": s, "latitude": 60, "longitude": 10, "elevation_m": e}
                    for s, e in (("SN1", 10), ("SN2", 300), ("SN3", 900))]
        with tempfile.TemporaryDirectory() as tmp:
            summarize.build(synthetic_scored(wn_extra=1.0), Path(tmp), stations, publish_values=False)
            board = json.loads((Path(tmp) / "leaderboard.json").read_text())
            self.assertEqual(board["t"]["24"]["all"]["verdict"], "yr")
            self.assertEqual(board["w"]["24"]["all"]["diff"], -0.1)
            recent = json.loads((Path(tmp) / "recent" / "SN1.json").read_text())
            self.assertNotIn("wn_t", recent)
            cal = json.loads((Path(tmp) / "calibration.json").read_text())
            self.assertIn("yr", cal["t"]["24"])
            short = synthetic_scored(days=3)
            summarize.build(short, Path(tmp), stations)
            board = json.loads((Path(tmp) / "leaderboard.json").read_text())
            self.assertEqual(board["t"]["24"]["all"]["verdict"], "not_enough_data")


class MigrateTest(unittest.TestCase):
    def test_small_database(self):
        from cloud import migrate_sqlite
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
            INSERT INTO forecast_runs VALUES (1,'MET',1,'2026-09-20T05:30:00Z','2026-09-20T06:05:00Z');
            INSERT INTO forecast_runs VALUES (2,'WeatherNext3-mean',1,'2026-09-19T18:00:00Z','2026-09-19T20:00:00Z');
            INSERT INTO forecast_runs VALUES (3,'WeatherNext3-mean',1,'2026-09-20T00:00:00Z','2026-09-20T06:20:00Z');
            INSERT INTO forecast_runs VALUES (4,'WeatherNext3-mean',1,'2026-09-20T06:00:00Z','2026-09-20T12:00:00Z');
            """)
            for h in range(1, 60):
                v = f"2026-09-20T{6+h if 6+h<24 else 0:02d}:00:00Z" if 6 + h < 24 else None
                t = datetime(2026, 9, 20, 6, tzinfo=UTC) + timedelta(hours=h)
                con.execute("INSERT INTO forecasts VALUES (1,?,?,?,?,?)", (iso(t), h, 10.0, 3.0, 0.2))
                for run, val in ((2, 1.0), (3, 2.0), (4, 3.0)):
                    for m, x in (("air_temperature", val), ("wind_speed", 4.0), ("precipitation_1h", 0.1)):
                        con.execute("INSERT INTO weathernext_samples VALUES (?,?,?,?,?,?)",
                                    (run, iso(t), m, "mean", x, "2026-09-20T06:20:00Z" if run == 3 else
                                     ("2026-09-19T20:00:00Z" if run == 2 else "2026-09-20T12:00:00Z")))
                con.execute("INSERT INTO observations VALUES (1,'SN1',?,11.0,3.5,0.0)", (iso(t),))
            con.commit(); con.close()
            out = Path(tmp) / "scored"
            migrate_sqlite.migrate(db, date(2026, 9, 23), out, log=lambda *a: None)
            df = load_scored(out)
            r = df[(df.h == 6)].iloc[0]
            self.assertEqual(r.yr_t, 10.0)
            self.assertEqual(r.wn_t, 2.0)  # run 3: collected within grace; run 4 too late
            self.assertEqual(r.obs_t, 11.0)
            before = db.stat().st_mtime
            self.assertEqual(before, db.stat().st_mtime)


if __name__ == "__main__":
    unittest.main()
