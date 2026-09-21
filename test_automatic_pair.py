import sqlite3
import unittest
import pandas as pd
from database import SCHEMA
from collectors.weathernext import migrate
from dashboard_scores import automatic_run_pair, selected_run_pairs, load_shared_pairs
from forecast_comparison import load_timeline


class AutomaticPairTests(unittest.TestCase):
    def setUp(self):
        self.con=sqlite3.connect(':memory:')
        self.con.row_factory=sqlite3.Row
        self.con.executescript(SCHEMA)
        migrate(self.con)
        self.con.execute("INSERT INTO locations(id,name,station_id,latitude,longitude) VALUES(1,'Voll','SN68860',63,10)")
        self.now='2026-09-22T12:00:00Z'
        self.valid='2026-09-22T10:00:00Z'
        self.add_run(1,'MET','2026-09-22T00:30:00Z',9)
        self.add_run(2,'WeatherNext3-mean','2026-09-22T00:00:00Z',8)
        self.add_run(3,'MET','2026-09-22T09:30:00Z',12)
        self.con.execute('INSERT INTO observations(location_id,source_id,observed_at,air_temperature) VALUES(1,?,?,7)',('SN68860',self.valid))

    def tearDown(self):
        self.con.close()

    def add_run(self, run_id, provider, issue, value, valid=None, retrieved=None):
        valid=valid or self.valid
        self.con.execute('INSERT INTO forecast_runs VALUES(?,?,?,?,?)',(run_id,provider,1,issue,retrieved or issue))
        self.con.execute('INSERT INTO forecasts(run_id,valid_at,lead_hours,air_temperature) VALUES(?,?,?,?)',
                         (run_id,valid,(pd.Timestamp(valid)-pd.Timestamp(issue)).total_seconds()/3600,value))

    def select(self, **kwargs):
        return automatic_run_pair(self.con,1,now=self.now,**kwargs)

    def test_older_fair_pair_replaces_newest_independent_and_matches_manual_scores(self):
        before=load_shared_pairs(self.con,'air_temperature',days=None,now=self.now)
        selected=self.select()['pair']
        self.assertEqual((selected['met']['id'],selected['wn']['id']),(1,2))
        timeline=load_timeline(self.con,1,1,2)
        scored=selected_run_pairs(timeline,selected['met'],selected['wn'],self.now)
        self.assertEqual(len(scored),1)
        self.assertEqual(scored.met_abs_error.tolist(),[2])
        self.assertEqual(scored.wn_abs_error.tolist(),[1])
        runs={r['id']:dict(r) for r in self.con.execute('SELECT * FROM forecast_runs')}
        self.assertTrue(selected_run_pairs(load_timeline(self.con,1,3,2),runs[3],runs[2],self.now).empty)
        after=load_shared_pairs(self.con,'air_temperature',days=None,now=self.now)
        pd.testing.assert_frame_equal(before,after)

    def test_newest_qualifying_pair_not_smallest_error_or_closest_gap(self):
        self.add_run(4,'MET','2026-09-22T01:00:00Z',50)
        # The older MET run is closer in lead and has a smaller error.
        self.assertEqual(self.select()['pair']['met']['id'],4)

    def test_no_fair_pair_has_data_based_reason(self):
        self.con.execute('DELETE FROM forecasts WHERE run_id=1')
        self.con.execute('DELETE FROM forecast_runs WHERE id=1')
        result=self.select()
        self.assertIsNone(result['pair'])
        self.assertIn('9.5 h',result['reason'])
        self.assertIn('maximum 3 h',result['reason'])

    def test_variable_and_station_without_both_sources(self):
        self.assertIsNone(self.select(metric='wind_speed')['pair'])
        self.assertIn('Both sources',self.select(metric='wind_speed')['reason'])
        self.assertIsNone(automatic_run_pair(self.con,999,now=self.now)['pair'])

    def test_observed_pair_preferred_to_fair_future_pair(self):
        self.add_run(4,'MET','2026-09-22T11:00:00Z',30,valid='2026-09-22T13:00:00Z')
        self.add_run(5,'WeatherNext3-mean','2026-09-22T10:00:00Z',40,valid='2026-09-22T13:00:00Z')
        self.assertEqual(self.select()['pair']['met']['id'],1)
        self.con.execute('DELETE FROM observations')
        result=self.select()
        self.assertEqual(result['pair']['met']['id'],4)
        self.assertEqual(result['pair']['shared_samples'],0)
        self.assertIn('no shared exact-time Frost',result['reason'])

    def test_late_retrieval_and_bucket_mismatch_remain_excluded(self):
        self.con.execute("UPDATE forecast_runs SET retrieved_at='2026-09-22T11:00:00Z' WHERE id=2")
        self.assertIsNone(self.select()['pair'])
        self.con.execute('UPDATE forecast_runs SET retrieved_at=issued_at')
        # 17.5 and 18h are within 3h, but cross an existing bucket boundary.
        self.con.execute("UPDATE forecasts SET valid_at='2026-09-22T18:00:00Z',lead_hours=lead_hours+8")
        self.assertIsNone(self.select()['pair'])

    def test_exact_observations_and_chart_window(self):
        self.con.execute("UPDATE observations SET observed_at='2026-09-22T10:10:00Z'")
        result=self.select()
        self.assertEqual(result['pair']['shared_samples'],0)
        valid='2026-09-26T10:00:00Z'
        for run,lead in [(1,105.5),(2,106)]:
            self.con.execute('INSERT INTO forecasts(run_id,valid_at,lead_hours,air_temperature) VALUES(?,?,?,9)',(run,valid,lead))
        self.con.execute('INSERT INTO observations(location_id,source_id,observed_at,air_temperature) VALUES(1,?,?,7)',('SN68860',valid))
        self.now='2026-09-27T00:00:00Z'
        self.assertEqual(self.select(window='72 h')['pair']['shared_samples'],0)
        self.assertEqual(self.select(window='Full run')['pair']['shared_samples'],1)

    def test_conflicting_exact_observation_is_not_useful(self):
        self.con.execute('INSERT INTO observations(location_id,source_id,observed_at,air_temperature) VALUES(1,?,?,99)',('other',self.valid))
        self.assertEqual(self.select()['pair']['shared_samples'],0)
