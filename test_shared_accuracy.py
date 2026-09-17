import sqlite3
import unittest
import pandas as pd
from database import SCHEMA
from collectors.weathernext import migrate
from forecast_comparison import load_timeline, past_rows
from dashboard_scores import load_shared_pairs, shared_accuracy, model_disagreement


class SharedAccuracyTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(':memory:')
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        migrate(self.con)
        self.con.execute("INSERT INTO locations(id,name,station_id,station_name,latitude,longitude) VALUES(1,'Voll','SN68860','Voll',63,10)")
        self.now = '2026-09-16T12:00:00Z'
        self.add_run(1, 'MET', '2026-09-15T20:00:00Z')
        self.add_run(2, 'WeatherNext3-mean', '2026-09-15T18:00:00Z')
        self.point(1, '2026-09-16T00:00:00Z', 4, 8)
        self.point(2, '2026-09-16T00:00:00Z', 6, 5)
        self.obs('2026-09-16T00:00:00.000Z', 6)
        self.obs('2026-09-16T00:10:00Z', 100)

    def tearDown(self):
        self.con.close()

    def add_run(self, run_id, provider, issued, retrieved=None):
        self.con.execute('INSERT INTO forecast_runs VALUES(?,?,?,?,?)', (run_id,provider,1,issued,retrieved or issued))

    def point(self, run, valid, lead, value):
        self.con.execute('INSERT INTO forecasts(run_id,valid_at,lead_hours,air_temperature,wind_speed) VALUES(?,?,?,?,?)', (run,valid,lead,value,value))

    def obs(self, valid, value, source='SN68860'):
        self.con.execute('INSERT INTO observations(location_id,source_id,observed_at,air_temperature,wind_speed) VALUES(1,?,?,?,?)', (source,valid,value,value))

    def test_shared_targets_units_bias_and_subhour_exclusion(self):
        for metric in ('air_temperature','wind_speed'):
            pairs=load_shared_pairs(self.con,metric,now=self.now)
            self.assertEqual(len(pairs),1)
            self.assertEqual(pairs.actual_value.iloc[0],6)
            board=shared_accuracy(pairs,metric).set_index('provider')
            self.assertEqual(board.samples.tolist(),[1,1])
            self.assertEqual(board.bias.to_dict(),{'MET':2,'WeatherNext3-mean':-1})
            mae='MAE_C' if metric=='air_temperature' else 'MAE_ms'
            self.assertEqual(board[mae].to_dict(),{'MET':2,'WeatherNext3-mean':1})

    def test_no_unshared_missing_or_future_targets(self):
        self.point(1,'2026-09-16T01:00:00Z',5,10)
        self.obs('2026-09-16T01:00:00Z',10)
        for valid, lead in [('2026-09-16T02:00:00Z',6),('2026-09-17T00:00:00Z',28)]:
            self.point(1,valid,lead,10)
            self.point(2,valid,lead+2,10)
        self.obs('2026-09-17T00:00:00Z',10)
        self.assertEqual(len(load_shared_pairs(self.con,'air_temperature',now=self.now)),1)

    def test_repeated_runs_do_not_overweight_and_pairing_ignores_error(self):
        self.add_run(3,'MET','2026-09-15T18:30:00Z')
        self.point(3,'2026-09-16T00:00:00Z',5.5,30)
        pairs=load_shared_pairs(self.con,'air_temperature',now=self.now)
        self.assertEqual(len(pairs),1)
        self.assertEqual(pairs.met_run_id.iloc[0],3)  # closest lead, even with worse error

    def test_excludes_mismatched_buckets_large_lead_gap_and_backfill(self):
        self.con.execute('UPDATE forecasts SET lead_hours=19 WHERE run_id=2')
        self.assertTrue(load_shared_pairs(self.con,'wind_speed',now=self.now).empty)
        self.con.execute('UPDATE forecasts SET lead_hours=9 WHERE run_id=2')
        self.assertTrue(load_shared_pairs(self.con,'wind_speed',now=self.now).empty)
        self.con.execute('UPDATE forecasts SET lead_hours=6 WHERE run_id=2')
        self.con.execute("UPDATE forecast_runs SET retrieved_at='2026-09-16T00:01:00Z' WHERE id=2")
        self.assertTrue(load_shared_pairs(self.con,'wind_speed',now=self.now).empty)

    def test_duplicate_observations_once_conflicting_observations_omitted(self):
        self.obs('2026-09-16T00:00:00Z',6,'other')
        self.assertEqual(len(load_shared_pairs(self.con,'wind_speed',now=self.now)),1)
        self.con.execute("UPDATE observations SET wind_speed=7 WHERE source_id='other'")
        self.assertTrue(load_shared_pairs(self.con,'wind_speed',now=self.now).empty)

    def test_period_and_station_filters(self):
        self.assertTrue(load_shared_pairs(self.con,'air_temperature',days=1,now='2026-09-18T00:00:00Z').empty)
        self.assertEqual(len(load_shared_pairs(self.con,'air_temperature',days=None,now='2026-09-18T00:00:00Z')),1)
        self.assertTrue(load_shared_pairs(self.con,'air_temperature',location_id=999,now=self.now).empty)

    def test_wind_timeline_percentiles_exact_actuals_and_future_mask(self):
        for stat,value in [('p10',3),('p90',9)]:
            self.con.execute('INSERT INTO weathernext_samples VALUES(?,?,?,?,?,?,?,?,?,?)',(2,'2026-09-16T00:00:00Z','wind_speed',stat,value,'test',63,10,self.now,'m/s'))
        timeline=load_timeline(self.con,1,1,2,'wind_speed')
        self.assertEqual(timeline.actual_value.tolist(),[6])
        self.assertEqual(timeline.wn_p10.tolist(),[3])
        self.assertEqual(timeline.wn_p90.tolist(),[9])
        self.assertTrue(past_rows(timeline,'2026-09-15T23:59:00Z').empty)
        self.assertEqual(past_rows(timeline,self.now).met_abs_error.tolist(),[2])

    def test_disagreement_latest_runs_future_only_and_no_observation_needed(self):
        self.add_run(3,'MET','2026-09-16T06:00:00Z')
        self.add_run(4,'WeatherNext3-mean','2026-09-16T06:00:00Z')
        for run,value in [(1,100),(2,-100),(3,9),(4,5)]:
            self.point(run,'2026-09-16T18:00:00Z',12 if run>2 else 22,value)
        pairs=model_disagreement(self.con,'wind_speed',now=self.now)
        self.assertEqual(len(pairs),1)
        self.assertEqual(pairs.difference.iloc[0],4)
        self.assertEqual(pairs.met_run_id.iloc[0],3)
        self.assertEqual(pairs.wn_run_id.iloc[0],4)

    def test_unvalidated_metric_rejected(self):
        with self.assertRaises(ValueError):
            load_shared_pairs(self.con,'precipitation_1h',now=self.now)
