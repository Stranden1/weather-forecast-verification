"""Naive baseline + skill, quantile (pinball) scoring, and the health status line."""
import json
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from cloud import health, score, summarize
from cloud.config import PENDING_COLUMNS
from cloud.store import State, load_scored
from cloud.timeutil import iso

UTC = timezone.utc


def pend(provider, fetched, target, t, **kw):
    r = dict(provider=provider, station="SN1", fetched_at=iso(fetched), issued_at=iso(fetched),
             target=iso(target), lead_h=(target - fetched).total_seconds() / 3600, t=t)
    r.update(kw)
    return r


def ob(time, t=None, w=None, p=None, station="SN1"):
    return {"station": station, "time": iso(time), "t": t, "w": w, "p": p}


class BaselineTest(unittest.TestCase):
    def test_offsets_round_up_to_whole_days(self):
        got = score.baseline_offset_hours([6, 12, 24, 48, 72, 120, 168, 240]).tolist()
        self.assertEqual(got, [24, 24, 24, 48, 72, 120, 168, 240])

    def test_score_targets_takes_observation_from_latest_known_day(self):
        target = datetime(2026, 10, 12, 12, tzinfo=UTC)
        rows = []
        for h in (6, 48, 72, 120, 240):
            f = target - timedelta(hours=h)
            rows += [pend("yr", f, target, 1.0, p=0.1), pend("wn", f, target, 2.0, p=0.2)]
        obs = pd.DataFrame([ob(target, 10.0, 3.0, 0.0),
                            ob(target - timedelta(hours=24), 5.0, 1.0, 0.4),
                            ob(target - timedelta(hours=48), 6.0, 2.0, 0.5),
                            ob(target - timedelta(hours=72), 7.0, 2.0, 0.6),
                            ob(target - timedelta(hours=240), 9.0, 4.0, 0.3)])
        s = score.score_targets(pd.DataFrame(rows, columns=PENDING_COLUMNS), obs).set_index("h")
        self.assertEqual(s.loc[6, "base_t"], 5.0)
        self.assertEqual(s.loc[6, "base_p"], 0.4)
        self.assertEqual(s.loc[48, "base_t"], 6.0)
        self.assertEqual(s.loc[72, "base_t"], 7.0)
        self.assertTrue(pd.isna(s.loc[72, "base_p"]))   # rain not scored beyond 48 h
        self.assertTrue(pd.isna(s.loc[120, "base_t"]))  # no observation 5 days back
        self.assertEqual(s.loc[240, "base_w"], 4.0)
        self.assertEqual(s.loc[6, "obs_t"], 10.0)       # scoring itself is unchanged
        self.assertEqual(len(s), 5)

    def test_finalize_uses_earlier_days_and_keeps_12_days_of_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            st = State(Path(tmp) / "state")
            target = datetime(2026, 10, 12, 12, tzinfo=UTC)
            f = target - timedelta(hours=6)
            st.add_pending([pend("yr", f, target, 1.0), pend("wn", f, target, 2.0)])
            now = datetime(2026, 10, 13, 7, tzinfo=UTC)
            st.add_obs([ob(target, 1.5), ob(target - timedelta(days=1), 0.5),
                        ob(now - timedelta(days=11), 3.0), ob(now - timedelta(days=13), 4.0)])
            m = st.meta(); m["first_fetch"] = iso(f); st.save_meta(m)
            got = {}
            score.finalize(st, now=now, write=lambda d, df: got.setdefault(d, df))
            self.assertEqual(got[date(2026, 10, 12)].iloc[0].base_t, 0.5)
            kept = set(st.obs().t)
            self.assertIn(3.0, kept)
            self.assertNotIn(4.0, kept)

    def test_migration_adds_the_same_baseline(self):
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
            INSERT INTO forecast_runs VALUES (1,'MET',1,'2026-09-20T05:30:00Z','2026-09-20T06:00:00Z');
            """)
            fetch = datetime(2026, 9, 20, 6, tzinfo=UTC)
            for h in range(1, 12):
                t = fetch + timedelta(hours=h)
                con.execute("INSERT INTO forecasts VALUES (1,?,?,?,?,?)", (iso(t), h, 10.0, 3.0, 0.2))
                con.execute("INSERT INTO observations VALUES (1,'SN1',?,11.0,3.5,0.0)", (iso(t),))
                con.execute("INSERT INTO observations VALUES (1,'SN1',?,?,2.0,0.1)",
                            (iso(t - timedelta(days=1)), 20.0 + h))
            con.commit(); con.close()
            out = Path(tmp) / "scored"
            migrate_sqlite.migrate(db, date(2026, 9, 21), out, log=lambda *a: None)
            r = load_scored(out).query("h == 6").iloc[0]
            back = pd.Timestamp(r.target) - pd.Timedelta(hours=24)
            self.assertEqual(r.base_t, 20.0 + (back - pd.Timestamp(fetch - timedelta(days=1))).seconds / 3600)
            self.assertEqual(r.base_w, 2.0)


def paired_rows(rows):
    d = pd.DataFrame(rows)
    d["target"] = "2026-10-01T12:00:00Z"
    return summarize.paired(d, "t")


class SkillTest(unittest.TestCase):
    def test_skill_uses_only_rows_with_a_baseline(self):
        d = paired_rows([
            dict(obs_t=0, yr_t=1, wn_t=2, base_t=4),       # yr 1, wn 2, naive 4
            dict(obs_t=0, yr_t=-1, wn_t=0, base_t=-2),     # yr 1, wn 0, naive 2
            dict(obs_t=0, yr_t=9, wn_t=9, base_t=np.nan),  # older row: left out
        ])
        b = summarize.stats(d, with_ci=False)["base"]
        self.assertEqual(b["n"], 2)
        self.assertEqual(b["mae"], 3.0)
        self.assertEqual(b["mae_yr"], 1.0)
        self.assertAlmostEqual(b["skill_yr"], 1 - 1 / 3, places=3)
        self.assertAlmostEqual(b["skill_wn"], 1 - 1 / 3, places=3)

    def test_no_baseline_column_means_no_skill(self):
        d = paired_rows([dict(obs_t=0, yr_t=1, wn_t=2)])
        self.assertNotIn("base", summarize.stats(d, with_ci=False))

    def test_zero_naive_error_gives_no_skill_value(self):
        d = paired_rows([dict(obs_t=0, yr_t=1, wn_t=2, base_t=0)])
        self.assertIsNone(summarize.stats(d, with_ci=False)["base"]["skill_yr"])


class QuantileTest(unittest.TestCase):
    def test_pinball_known_values(self):
        s = lambda *x: pd.Series(x, dtype=float)
        self.assertAlmostEqual(summarize.pinball(s(0), [s(-1), s(0), s(1)]), 0.2 / 3)
        # u = 2, 1, 0.5 -> 0.2, 0.5, 0.45
        self.assertAlmostEqual(summarize.pinball(s(2), [s(0), s(1), s(1.5)]), 1.15 / 3)
        # Too narrow and too wide both cost more than a well-placed range.
        good = summarize.pinball(s(0, 1, -1), [s(-1.5, -1.5, -1.5), s(0, 0, 0), s(1.5, 1.5, 1.5)])
        wide = summarize.pinball(s(0, 1, -1), [s(-9, -9, -9), s(0, 0, 0), s(9, 9, 9)])
        self.assertLess(good, wide)

    def test_coverage_scores_both_on_common_rows_with_yr_main_value_as_median(self):
        df = pd.DataFrame([
            dict(h=24, obs_t=0.0, yr_t=0.0, yr_t_p10=-1.0, yr_t_p90=1.0,
                 wn_t=5.0, wn_t_p10=-2.0, wn_t_p50=0.0, wn_t_p90=2.0),
            dict(h=24, obs_t=3.0, yr_t=0.0, yr_t_p10=-1.0, yr_t_p90=1.0,
                 wn_t=0.0, wn_t_p10=-2.0, wn_t_p50=np.nan, wn_t_p90=2.0),  # no wn p50
        ])
        c = summarize.coverage(df, "t", 24)
        self.assertEqual(c["yr"]["n"], 2)                 # hit rate still uses every row
        self.assertEqual(c["q"]["n"], 1)
        self.assertAlmostEqual(c["q"]["yr"]["pinball"], round(0.2 / 3, 3))
        self.assertAlmostEqual(c["q"]["wn"]["pinball"], round(0.4 / 3, 3))  # mean 5.0 is ignored
        self.assertEqual((c["q"]["yr"]["width"], c["q"]["wn"]["width"]), (2.0, 4.0))

    def test_build_writes_quantile_block(self):
        from cloud.tests.test_pipeline import synthetic_scored
        stations = [{"station_id": s, "name": s, "latitude": 60, "longitude": 10, "elevation_m": 10}
                    for s in ("SN1", "SN2", "SN3")]
        with tempfile.TemporaryDirectory() as tmp:
            summarize.build(synthetic_scored(days=8), Path(tmp), stations)
            cal = json.loads((Path(tmp) / "calibration.json").read_text())["t"]["24"]
            self.assertLess(cal["q"]["yr"]["width"], cal["q"]["wn"]["width"])  # ±1 vs ±1.5
            self.assertGreater(cal["q"]["n"], 0)


NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
NO_ACCESS = ("WeatherNext failed: ImageCollection.load: ImageCollection asset 'x' not found "
             "(does not exist or caller does not have access).")


def run(hours_ago, yr=1400, wn=0, frost=3500, wn_err=NO_ACCESS, yr_err=0):
    src = lambda rows, n, e=None: {"rows": rows, "errors": n, "error": e, "enabled": True}
    return {"fetched_at": iso(NOW - timedelta(hours=hours_ago)),
            "sources": {"yr": src(yr, yr_err, "Yr SN1: boom" if yr_err else None),
                        "wn": src(wn, 1 if wn_err else 0, wn_err),
                        "frost": src(frost, 0)}}


class HealthTest(unittest.TestCase):
    def test_statuses(self):
        self.assertEqual(health.status("wn", {"rows": 0, "errors": 1, "error": NO_ACCESS}), "no_access")
        perm = "WeatherNext failed: Caller does not have required permission to use project p."
        self.assertEqual(health.status("wn", {"rows": 0, "errors": 1, "error": perm}), "no_access")
        self.assertEqual(health.status("yr", {"rows": 0, "errors": 50, "error": "Yr SN1: x"}), "error")
        self.assertEqual(health.status("yr", {"rows": 10, "errors": 2}), "partial")
        self.assertEqual(health.status("frost", {"rows": 0, "errors": 0}), "no_data")
        self.assertEqual(health.status("wn", {"rows": 0, "errors": 0, "enabled": False}), "paused")

    def test_build_latest_run_and_counts(self):
        runs = [run(h) for h in (50, 42, 36, 30, 24, 18, 12, 6)] + [run(1, yr=0, frost=0, yr_err=50)]
        h = health.build({"first_fetch": runs[0]["fetched_at"], "runs": runs}, NOW)
        self.assertTrue(h["last_run_failed"])
        self.assertEqual(h["last_success"], iso(NOW - timedelta(hours=6)))
        self.assertEqual(h["sources"]["yr"]["status"], "error")
        self.assertEqual(h["sources"]["wn"]["status"], "no_access")
        self.assertEqual((h["runs_48h"], h["expected_48h"]), (8, 8))
        self.assertNotIn("error", h["sources"]["wn"])  # raw messages are never published

    def test_expected_runs_right_after_start(self):
        runs = [run(7), run(1)]
        h = health.build({"first_fetch": runs[0]["fetched_at"], "runs": runs}, NOW)
        self.assertEqual((h["runs_48h"], h["expected_48h"]), (2, 2))
        self.assertFalse(h["last_run_failed"])
        self.assertEqual(h["sources"]["yr"]["status"], "ok")

    def test_old_run_records_without_sources(self):
        old = {"fetched_at": iso(NOW), "yr_rows": 1400, "wn_rows": 0, "obs_rows": 3530,
               "errors": [NO_ACCESS]}
        h = health.build({"runs": [old]}, NOW)
        self.assertEqual({k: v["status"] for k, v in h["sources"].items()},
                         {"yr": "ok", "wn": "no_access", "frost": "ok"})

    def test_no_runs(self):
        self.assertIsNone(health.build({}, NOW)["last_run"])

    def test_collect_records_every_source_and_export_writes_health(self):
        from cloud import run as runmod
        stations = [{"station_id": "SN1", "latitude": 60, "longitude": 10}]
        many_yr = [f"Yr SN{i}: timeout" for i in range(30)]
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(runmod, "load_stations", return_value=stations), \
                mock.patch.object(runmod.yr, "collect", return_value=([], many_yr)), \
                mock.patch.object(runmod.weathernext, "collect", side_effect=RuntimeError("no access")), \
                mock.patch.object(runmod.frost, "collect",
                                  return_value=([ob(NOW, 1.0)], [])):
            st = State(Path(tmp) / "state")
            runmod.collect(st)
            src = st.meta()["runs"][-1]["sources"]
            self.assertEqual((src["yr"]["errors"], src["wn"]["errors"], src["frost"]["rows"]), (30, 1, 1))
            self.assertIn("no access", src["wn"]["error"])  # not lost behind 30 Yr errors
            h = health.write(st.meta(), Path(tmp) / "site")
            self.assertTrue((Path(tmp) / "site" / "health.json").exists())
            self.assertFalse(h["last_run_failed"])  # Frost still delivered
            self.assertEqual(h["sources"]["yr"]["status"], "error")


if __name__ == "__main__":
    unittest.main()
