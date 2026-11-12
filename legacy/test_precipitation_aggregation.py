"""Focused complete-period precipitation verification regressions."""
import sqlite3
import unittest

import pandas as pd

from collectors.weathernext import migrate
from dashboard_scores import load_shared_pairs
from database import SCHEMA
from scoring.precipitation import METRIC, WET_THRESHOLDS, metrics, summary


class AccumulatedPrecipitationTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(':memory:')
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        migrate(self.con)
        self.con.execute("INSERT INTO locations(id,name,station_id,latitude,longitude) VALUES(1,'Test','SN1',60,10)")
        self.start = pd.Timestamp('2026-09-20T00:00:00Z')
        self.now = self.start + pd.Timedelta(hours=25)
        self.add_run(1, 'MET', '2026-09-18T09:30:00Z')
        self.add_run(2, 'WeatherNext3-mean', '2026-09-18T12:00:00Z')
        for hour in range(1, 25):
            end = self.start + pd.Timedelta(hours=hour)
            actual = 1.1 if hour == 1 else 0.0
            self.point(1, end, 0.5 if hour == 1 else 0.0)
            self.point(2, end, 1.2 if hour == 1 else 0.0)
            self.con.execute(
                'INSERT INTO observations(location_id,source_id,observed_at,precipitation_1h) VALUES(1,?,?,?)',
                ('SN1', end.isoformat(), actual))

    def tearDown(self):
        self.con.close()

    def add_run(self, run_id, provider, issue):
        self.con.execute('INSERT INTO forecast_runs VALUES(?,?,?,?,?)',
                         (run_id, provider, 1, issue, issue))

    def point(self, run_id, end, amount):
        run = self.con.execute('SELECT * FROM forecast_runs WHERE id=?', (run_id,)).fetchone()
        stored = end - pd.Timedelta(hours=1) if run['provider'] == 'MET' else end
        lead = (stored - pd.Timestamp(run['issued_at'])).total_seconds() / 3600
        self.con.execute('INSERT INTO forecasts(run_id,valid_at,lead_hours,precipitation_1h) VALUES(?,?,?,?)',
                         (run_id, stored.isoformat(), lead, amount if run['provider'] == 'MET' else None))
        if run['provider'] != 'MET':
            self.con.execute('INSERT INTO weathernext_samples VALUES(?,?,?,?,?,?,?,?,?,?)',
                             (run_id, stored.isoformat(), METRIC, 'mean', amount, 'fixture',
                              60, 10, run['retrieved_at'], 'mm'))

    def pairs(self, hours):
        return load_shared_pairs(self.con, METRIC, days=None, now=self.now,
                                 accumulation_hours=hours)

    def test_exact_complete_six_hour_boundaries_and_day(self):
        six = self.pairs(6)
        day = self.pairs(24)
        self.assertEqual(len(six), 4)
        self.assertEqual(len(day), 1)
        self.assertEqual(len(load_shared_pairs(self.con, METRIC, days=1, now=self.now, accumulation_hours=24)), 1)
        self.assertEqual(six.period_start.tolist(),
                         [self.start + pd.Timedelta(hours=h) for h in (0, 6, 12, 18)])
        self.assertEqual(day.period_start.iloc[0], self.start)
        self.assertEqual(day.valid_at.iloc[0], self.start + pd.Timedelta(hours=24))
        self.assertEqual(six.met_component_count.tolist(), [6] * 4)
        self.assertEqual(day.wn_component_count.iloc[0], 24)
        self.assertEqual(six.actual_value.tolist(), [1.1, 0, 0, 0])
        self.assertAlmostEqual(day.actual_value.iloc[0], 1.1)
        self.assertAlmostEqual(day.met_value.iloc[0], 0.5)
        self.assertAlmostEqual(day.wn_value.iloc[0], 1.2)
        self.assertAlmostEqual(day.met_lead_hours.iloc[0], 38.5)
        self.assertAlmostEqual(day.wn_lead_hours.iloc[0], 36.0)
        self.assertTrue((day.lead_gap <= 3).all())
        self.assertEqual(WET_THRESHOLDS, {1: .1, 6: .5, 24: 1.0})

    def test_metrics_and_strict_thresholds(self):
        day = self.pairs(24)
        s = summary(day, 24).set_index(['horizon', 'provider'])
        yr = s.loc[('24–48h', 'Yr/MET')]
        wn = s.loc[('24–48h', 'WeatherNext')]
        self.assertAlmostEqual(yr.mae, .6)
        self.assertAlmostEqual(yr.bias, -.6)
        self.assertAlmostEqual(yr.wet_mae, .6)
        self.assertEqual([yr.hits, yr.misses, yr.false_alarms, yr.correct_dry], [0, 1, 0, 0])
        self.assertEqual([wn.hits, wn.misses, wn.false_alarms, wn.correct_dry], [1, 0, 0, 0])
        self.assertEqual(yr.POD, 0)
        self.assertEqual(wn.POD, 1)
        self.assertEqual(wn.CSI, 1)
        self.assertTrue(pd.isna(yr.FAR))
        edge = day.copy()
        edge['actual_value'] = 1.0
        edge['met_value'] = 1.0
        edge['wn_value'] = 1.0
        event = metrics(edge, WET_THRESHOLDS[24])
        self.assertTrue((event.hits == 0).all())
        self.assertTrue((event.correct_dry == 1).all())

    def test_missing_hour_mixed_runs_and_availability_exclude_period(self):
        self.con.execute("DELETE FROM weathernext_samples WHERE run_id=2 AND valid_at=?",
                         ((self.start + pd.Timedelta(hours=12)).isoformat(),))
        self.assertTrue(self.pairs(24).empty)
        # A second run filling the missing hour must not complete either run.
        self.add_run(3, 'WeatherNext3-mean', '2026-09-18T11:00:00Z')
        self.point(3, self.start + pd.Timedelta(hours=12), 0.0)
        self.assertTrue(self.pairs(24).empty)
        # Strict availability: equality to period start is too late.
        self.con.execute("UPDATE weathernext_samples SET retrieved_at=? WHERE run_id=2",
                         (self.start.isoformat(),))
        self.assertTrue(self.pairs(24).empty)

    def test_closest_lead_then_newest_not_error(self):
        self.add_run(4, 'MET', '2026-09-18T09:45:00Z')
        for hour in range(1, 25):
            self.point(4, self.start + pd.Timedelta(hours=hour), 99.0)
        day = self.pairs(24)
        self.assertEqual(day.met_run_id.tolist(), [4])
        self.assertAlmostEqual(day.met_value.iloc[0], 24 * 99.0)
        self.assertEqual(len(day.drop_duplicates(['location_id', 'period_start', 'horizon'])), 1)

    def test_fair_lead_and_read_only(self):
        before = list(self.con.iterdump())
        self.con.execute('PRAGMA query_only=ON')
        self.assertEqual(len(self.pairs(6)), 4)
        self.assertEqual(len(self.pairs(24)), 1)
        self.assertEqual(before, list(self.con.iterdump()))
        self.con.execute('PRAGMA query_only=OFF')
        self.con.execute("UPDATE forecast_runs SET issued_at='2026-09-18T06:00:00Z' WHERE id=2")
        # Stored native leads are now inconsistent and must fail closed.
        self.assertTrue(self.pairs(24).empty)


    def test_missing_frost_or_yr_hour_excludes_period(self):
        end = (self.start + pd.Timedelta(hours=12)).isoformat()
        self.con.execute('DELETE FROM observations WHERE location_id=1 AND observed_at=?', (end,))
        self.assertTrue(self.pairs(24).empty)
        self.assertEqual(len(self.pairs(6)), 3)
        self.con.execute('INSERT INTO observations(location_id,source_id,observed_at,precipitation_1h) VALUES(1,?,?,0)',
                         ('SN1', end))
        yr_stored = (self.start + pd.Timedelta(hours=11)).isoformat()
        self.con.execute('DELETE FROM forecasts WHERE run_id=1 AND valid_at=?', (yr_stored,))
        self.assertTrue(self.pairs(24).empty)

    def test_unfair_lead_gap_excludes_complete_runs(self):
        self.con.execute("UPDATE forecast_runs SET issued_at='2026-09-18T13:00:00Z', "
                         "retrieved_at='2026-09-18T13:00:00Z' WHERE id=2")
        self.con.execute('UPDATE forecasts SET lead_hours=lead_hours-1 WHERE run_id=2')
        self.assertTrue(self.pairs(24).empty)

if __name__ == '__main__':
    unittest.main()
