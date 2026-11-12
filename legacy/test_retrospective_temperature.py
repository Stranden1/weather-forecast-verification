"""Verification eligibility and read-only long-range scoring regressions."""
import copy
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import database
from collectors import weathernext as wn
from backfill_weathernext_temperature import backfill
from dashboard_scores import load_long_range_temperature, long_range_summary, load_shared_pairs
from test_weathernext_backfill import Source, metadata, ISSUED
from weathernext_history import register_verified_history


class RetrospectiveTemperatureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, 'DB_PATH', Path(self.tmp.name)/'test.db')
        self.db_patch.start()
        self.clock_patch = patch.object(wn, 'utc_now_iso', return_value='2026-09-17T00:00:00Z')
        self.clock_patch.start()
        database.init_db()
        database.seed_locations()
        self.hours = [72, 120, 168, 216]
        self.manifest = backfill({ISSUED:self.hours}, Source(), write=True, metadata_loader=metadata)
        with database.connect() as con:
            for location in con.execute('SELECT id,station_id FROM locations').fetchall():
                run = con.execute('INSERT INTO forecast_runs(provider,location_id,issued_at,retrieved_at) VALUES(?,?,?,?)',
                                  ('MET',location['id'],ISSUED,ISSUED)).lastrowid
                for hour in self.hours:
                    valid = wn.iso((wn.utc(ISSUED)+timedelta(hours=hour)).isoformat())
                    con.execute('INSERT INTO forecasts(run_id,valid_at,lead_hours,air_temperature) VALUES(?,?,?,?)',(run,valid,hour,8))
                    con.execute('INSERT INTO observations(location_id,source_id,observed_at,air_temperature) VALUES(?,?,?,?)',
                                (location['id'],location['station_id'],valid,6))
        self.now = '2026-09-16T23:00:00Z'

    def tearDown(self):
        self.clock_patch.stop()
        self.db_patch.stop()
        self.tmp.cleanup()

    def pairs(self, **kwargs):
        with database.connect() as con:
            return load_long_range_temperature(con, now=self.now, **kwargs)

    def test_verified_retrospective_scores_and_periods_without_writes(self):
        with database.connect() as con:
            before = list(con.iterdump())
            pairs = load_long_range_temperature(con, now=self.now)
            self.assertEqual(before, list(con.iterdump()))
            self.assertTrue(load_shared_pairs(con,'air_temperature',days=None,now=self.now).empty)
        summary = long_range_summary(pairs)
        self.assertEqual(summary.samples.tolist(),[5,5,5,5])
        self.assertEqual(summary.historical_samples.tolist(),[5,5,5,5])
        self.assertEqual(summary.yr_mae.tolist(),[2,2,2,2])
        self.assertTrue((summary.wn_mae-1).abs().lt(1e-8).all())
        self.assertEqual(str(summary.period_start.iloc[0]),'2026-09-08 12:00:00+00:00')
        self.assertFalse(pairs.duplicated(['location_id','valid_at','horizon']).any())

    def test_old_database_and_uncertified_late_retrieval_fail_closed(self):
        with database.connect() as con:
            con.execute('DROP TABLE weathernext_verified_history')  # disposable fixture only
        self.assertTrue(self.pairs().empty)
        with database.connect() as con:
            con.execute("UPDATE forecast_runs SET retrieved_at=issued_at WHERE provider='WeatherNext3-mean'")
        summary = long_range_summary(self.pairs())
        self.assertEqual(summary.samples.tolist(),[5,5,5,5])
        self.assertEqual(summary.historical_samples.tolist(),[0,0,0,0])

    def test_verified_identity_and_original_availability_are_rechecked(self):
        for field, value in [('original_available_at','2026-09-30T00:00:00Z'),
                             ('asset_id','wrong-asset'),('mean_value',99),('source_collection','wrong')]:
            with database.connect() as con:
                old = con.execute(f'SELECT {field} FROM weathernext_verified_history').fetchone()[0]
                # Use a transaction rolled back below to independently invalidate all evidence.
                con.execute(f'UPDATE weathernext_verified_history SET {field}=?',(value,))
                self.assertTrue(load_long_range_temperature(con,now=self.now).empty)
                con.rollback()
        self.assertEqual(len(self.pairs()),20)

    def test_registration_idempotency_invalid_manifest_and_conflict_rollback(self):
        with database.connect() as con: before = list(con.iterdump())
        self.assertEqual(register_verified_history(self.manifest)['added'],0)
        for kind in ['late','coordinates','conflict','incomplete']:
            bad = copy.deepcopy(self.manifest)
            if kind == 'late': bad['image_metadata'][ISSUED][0]['ingestion_time_utc'] += 1000000
            if kind == 'coordinates': bad['coordinates'][-1]['latitude'] += 1
            if kind == 'conflict': bad['image_metadata'][ISSUED][-1]['ingestion_time_utc'] += 1
            if kind == 'incomplete': bad['completed_runs'] = []
            with self.assertRaises(ValueError): register_verified_history(bad)
            with database.connect() as con: self.assertEqual(before,list(con.iterdump()))

    def test_filters_empty_summary_and_exact_observation_conflicts(self):
        self.assertEqual(len(self.pairs(location_id=1)),4)
        self.assertTrue(self.pairs(days=1).empty)
        summary = long_range_summary(self.pairs(location_id=999))
        self.assertEqual(summary.samples.tolist(),[0,0,0,0])
        self.assertTrue(summary.yr_mae.isna().all())
        self.assertTrue(summary.period_start.isna().all())
        with database.connect() as con:
            con.execute("INSERT INTO observations(location_id,source_id,observed_at,air_temperature) VALUES(1,'other','2026-09-08T12:00:00.000Z',6)")
            con.execute("INSERT INTO observations(location_id,source_id,observed_at,air_temperature) VALUES(1,'other','2026-09-08T12:10:00Z',100)")
        self.assertEqual(len(self.pairs()),20)
        with database.connect() as con:
            con.execute("UPDATE observations SET air_temperature=7 WHERE source_id='other'")
        self.assertEqual(len(self.pairs()),19)

    def test_malformed_stored_lead_and_future_targets_are_excluded(self):
        with database.connect() as con:
            con.execute("UPDATE forecasts SET lead_hours=71 WHERE run_id IN (SELECT id FROM forecast_runs WHERE provider='MET') AND lead_hours=72")
        self.assertEqual(len(self.pairs()),15)
        with database.connect() as con:
            pairs = load_long_range_temperature(con,now='2026-09-11T00:00:00Z')
        self.assertEqual(set(pairs.horizon),{120})
